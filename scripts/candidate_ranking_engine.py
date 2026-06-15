from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


BASELINE_MODEL_VERSION = "stock_radar_baseline_v1"
CHALLENGER_MODEL_VERSION = "stock_radar_challenger_strict_v1"


def rank_candidates(prediction_payload: dict[str, Any], market_context: dict[str, Any], *, model_version: str = BASELINE_MODEL_VERSION) -> dict[str, Any]:
    strict = model_version != BASELINE_MODEL_VERSION
    ranked = []
    for candidate in prediction_payload.get("candidates", []):
        ranked.append(_score_candidate(candidate, market_context, strict=strict, model_version=model_version))
    ranked.sort(key=lambda item: (edge_rank(item["edge_status"]), item["elasticity_score"], item["confluence_score"]), reverse=True)
    for index, candidate in enumerate(ranked, start=1):
        candidate["rank"] = index
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model_version": model_version,
        "model_role": "challenger" if strict else "baseline",
        "candidates": ranked,
        "top_candidates": [candidate for candidate in ranked if candidate["edge_status"] in {"STRONG_EDGE", "MODERATE_EDGE", "HIGH_RISK_HIGH_REWARD"}][:20],
    }


def edge_rank(edge_status: str) -> int:
    return {
        "AVOID": 0,
        "NO_EDGE": 1,
        "WATCH": 2,
        "HIGH_RISK_HIGH_REWARD": 3,
        "MODERATE_EDGE": 4,
        "STRONG_EDGE": 5,
    }.get(edge_status, 0)


def _score_candidate(candidate: dict[str, Any], market_context: dict[str, Any], *, strict: bool, model_version: str) -> dict[str, Any]:
    support_count = len(candidate.get("supporting_evidence") or [])
    conflict_count = len(candidate.get("conflicting_evidence") or [])
    risk_flags = candidate.get("risk_flags") or []
    confluence_score = float(candidate.get("confluence_score") or 0)
    elasticity_score = float(candidate.get("elasticity_score") or 0)
    risk_score = float(candidate.get("risk_score") or 0)
    catalyst_score = float(candidate.get("catalyst_score") or 0)

    if strict:
        confluence_score = confluence_score - risk_score * 0.08
        if support_count < 4:
            confluence_score = min(confluence_score, 64)
        if catalyst_score < 55:
            confluence_score = min(confluence_score, 58)
        if "high_liquidity_risk" in risk_flags:
            confluence_score = min(confluence_score, 52)
    if market_context.get("data_freshness_status") != "fresh":
        confluence_score = min(confluence_score, 68 if not strict else 60)
    if candidate.get("pool_filter", {}).get("hard_excluded"):
        confluence_score = min(confluence_score, 30)

    confluence_score = round(max(0, min(100, confluence_score)), 2)
    elasticity_score = round(max(0, min(100, elasticity_score + min(float(candidate["features"].get("relative_volume") or 1), 5) * 1.5 - max(risk_score - 65, 0) * 0.15)), 2)
    edge_status = _edge_status(candidate, confluence_score, elasticity_score, support_count, conflict_count, strict)
    rating = _rating(edge_status, confluence_score, risk_score)
    trade_plan = _trade_plan(candidate, rating, edge_status)
    reason = _reason(candidate, edge_status)

    enriched = {
        **candidate,
        "model_version": model_version,
        "confluence_score": confluence_score,
        "elasticity_score": elasticity_score,
        "edge_status": edge_status,
        "rating": rating,
        "reason": reason,
        "trade_plan": trade_plan,
        "validation_status": "not_yet_validated",
    }
    enriched["upside_trigger_level"] = trade_plan["upside_trigger_level"]
    enriched["downside_risk_level"] = trade_plan["downside_risk_level"]
    enriched["invalidation_level"] = trade_plan["invalidation_level"]
    return enriched


def _edge_status(candidate: dict[str, Any], confluence: float, elasticity: float, support_count: int, conflict_count: int, strict: bool) -> str:
    risk_score = float(candidate.get("risk_score") or 0)
    risk_flags = candidate.get("risk_flags") or []
    if candidate.get("candidate_type") == "no_edge" or candidate.get("pool_filter", {}).get("hard_excluded"):
        return "AVOID"
    if risk_score >= 72 or ("high_liquidity_risk" in risk_flags and confluence < 58):
        return "AVOID"
    if elasticity >= 76 and confluence >= 60 and risk_score >= 50:
        return "HIGH_RISK_HIGH_REWARD"
    if confluence >= (80 if strict else 76) and support_count >= 4 and conflict_count <= 2:
        return "STRONG_EDGE"
    if confluence >= (69 if strict else 66) and support_count >= 3:
        return "MODERATE_EDGE"
    if confluence >= 52:
        return "WATCH"
    return "NO_EDGE"


def _rating(edge_status: str, confluence: float, risk_score: float) -> str:
    if edge_status == "STRONG_EDGE" and risk_score <= 42 and confluence >= 80:
        return "A+"
    if edge_status in {"STRONG_EDGE", "MODERATE_EDGE"} and risk_score <= 55:
        return "A"
    if edge_status in {"WATCH", "HIGH_RISK_HIGH_REWARD"}:
        return "B"
    return "C"


def _trade_plan(candidate: dict[str, Any], rating: str, edge_status: str) -> dict[str, Any]:
    levels = candidate.get("trigger_levels") or {}
    expected = candidate.get("next_day_expected_range") or {}
    return {
        "actionable": edge_status in {"STRONG_EDGE", "MODERATE_EDGE"} and rating in {"A+", "A"},
        "edge_status_note": "edge_status is a forecast-advantage label, not a trade recommendation.",
        "entry_condition": "No active trade / no edge" if rating == "C" else f"Upside path starts confirming only above {levels.get('upside_trigger_level'):.2f}",
        "upside_trigger_level": levels.get("upside_trigger_level"),
        "downside_risk_level": levels.get("downside_risk_level"),
        "invalidation_level": levels.get("invalidation_level"),
        "gap_fill_level": levels.get("gap_fill_level"),
        "breakout_level": levels.get("breakout_level"),
        "breakdown_level": levels.get("breakdown_level"),
        "nearest_support": levels.get("nearest_support"),
        "nearest_resistance": levels.get("nearest_resistance"),
        "stop_condition": "No trade" if rating == "C" else f"Upside/bounce path invalidates below {levels.get('invalidation_level'):.2f}",
        "target_low_price": expected.get("expected_mid"),
        "target_high_price": expected.get("expected_high"),
        "next_day_expected_range": expected,
        "overnight_or_intraday": "intraday_confirm_only" if rating != "A+" else "small_overnight_or_intraday_confirm",
        "not_trading_advice": "These are probabilistic path levels, not buy/sell advice.",
    }


def _reason(candidate: dict[str, Any], edge_status: str) -> str:
    supports = [item["name"] for item in candidate.get("supporting_evidence", [])[:3]]
    conflicts = [item["name"] for item in candidate.get("conflicting_evidence", [])[:2]]
    if edge_status in {"STRONG_EDGE", "MODERATE_EDGE", "HIGH_RISK_HIGH_REWARD"}:
        return " + ".join(supports) if supports else "multi-source confluence"
    if conflicts:
        return "Capped: " + " / ".join(conflicts)
    return "No edge; confluence not strong enough."
