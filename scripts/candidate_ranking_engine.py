from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def rank_candidates(prediction_payload: dict[str, Any], market_context: dict[str, Any], *, model_version: str = "baseline_v1") -> dict[str, Any]:
    strict = model_version.startswith("challenger")
    ranked = []
    for candidate in prediction_payload.get("candidates", []):
        ranked.append(_score_candidate(candidate, market_context, strict=strict, model_version=model_version))
    ranked.sort(key=lambda item: item["elasticity_score"], reverse=True)
    for index, candidate in enumerate(ranked, start=1):
        candidate["rank"] = index
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model_version": model_version,
        "model_role": "challenger" if strict else "baseline",
        "candidates": ranked,
        "top_candidates": [candidate for candidate in ranked if candidate["rating"] in {"A+", "A"}][:20],
    }


def _score_candidate(candidate: dict[str, Any], market_context: dict[str, Any], *, strict: bool, model_version: str) -> dict[str, Any]:
    features = candidate["features"]
    catalyst_score = float((candidate.get("news") or {}).get("catalyst_score") or 35)
    technical_score = float(features.get("technical_score") or 0)
    volume_score = float(features.get("volume_score") or 0)
    sector_score = float((candidate.get("sector_theme") or {}).get("score") or 40)
    squeeze_score = float(features.get("squeeze_score") or 0)
    risk_score = float(candidate.get("risk_score") or 0)
    market_adjust = {"attack": 7, "neutral": 0, "defense": -14}.get(market_context.get("market_state"), 0)

    confluence_score = (
        catalyst_score * (0.24 if strict else 0.22)
        + technical_score * 0.22
        + volume_score * 0.21
        + sector_score * (0.22 if strict else 0.18)
        + squeeze_score * (0.06 if strict else 0.11)
        - risk_score * (0.43 if strict else 0.34)
        + market_adjust
    )
    support_count = len(candidate.get("supporting_evidence") or [])
    conflict_count = len(candidate.get("conflicting_evidence") or [])

    if support_count < 3:
        confluence_score = min(confluence_score, 62 if not strict else 56)
    if sector_score < 55:
        confluence_score = min(confluence_score, 64)
    if risk_score >= 55:
        confluence_score = min(confluence_score, 58)
    if candidate["candidate_type"].startswith("avoid"):
        confluence_score = min(confluence_score, 44)
    if market_context.get("data_freshness_status") != "fresh":
        confluence_score = min(confluence_score, 70 if not strict else 62)
    if not features.get("real_data"):
        confluence_score = min(confluence_score, 60 if not strict else 52)

    confluence_score = round(max(0, min(100, confluence_score)), 2)
    elasticity_score = round(max(0, min(100, confluence_score + min(features.get("atr_pct", 0) * 180, 12) + min(features.get("relative_volume", 1), 4) * 2)), 2)
    rating = _rating(confluence_score, elasticity_score, market_context, risk_score, support_count, candidate["candidate_type"])
    trade_plan = _trade_plan(candidate, rating)
    reason = _reason(candidate, rating)
    enriched = {
        **candidate,
        "model_version": model_version,
        "confluence_score": confluence_score,
        "elasticity_score": elasticity_score,
        "catalyst_score": round(catalyst_score, 2),
        "risk_score": round(risk_score, 2),
        "rating": rating,
        "reason": reason,
        "trade_plan": trade_plan,
        "validation_status": "not_yet_validated",
    }
    enriched["upside_trigger_level"] = trade_plan["upside_trigger_level"]
    enriched["invalidation_level"] = trade_plan["invalidation_level"]
    return enriched


def _rating(confluence: float, elasticity: float, market_context: dict[str, Any], risk_score: float, support_count: int, candidate_type: str) -> str:
    if candidate_type.startswith("avoid") or confluence < 52 or risk_score >= 68:
        return "C"
    if confluence >= 82 and elasticity >= 86 and market_context.get("market_state") != "defense" and support_count >= 4 and risk_score <= 34:
        return "A+"
    if confluence >= 72 and elasticity >= 76 and support_count >= 3 and risk_score <= 48:
        return "A"
    if confluence >= 58:
        return "B"
    return "C"


def _trade_plan(candidate: dict[str, Any], rating: str) -> dict[str, Any]:
    features = candidate["features"]
    last_close = candidate["last_close"]
    trigger = max(candidate.get("upside_trigger_level") or last_close * 1.025, last_close * 1.012)
    invalidation = min(candidate.get("invalidation_level") or last_close * 0.96, last_close * 0.985)
    atr_pct = features.get("atr_pct") or 0.055
    target_low = 0.05 if rating == "A" else 0.08 if rating == "A+" else 0.03
    target_high = min(0.22, max(target_low + 0.04, atr_pct * 1.9))
    return {
        "actionable": rating in {"A+", "A"},
        "entry_condition": "Reject / no active trade" if rating == "C" else f"Only above {trigger:.2f} with volume confirmation",
        "upside_trigger_level": round(trigger, 4),
        "invalidation_level": round(invalidation, 4),
        "stop_condition": "No trade" if rating == "C" else f"Fail below {invalidation:.2f} or VWAP loss after trigger",
        "target_low_pct": round(target_low, 4),
        "target_high_pct": round(target_high, 4),
        "next_day_expected_range": candidate["next_day_expected_range"],
        "overnight_or_intraday": "intraday_confirm_only" if rating != "A+" else "small_overnight_or_intraday_confirm",
    }


def _reason(candidate: dict[str, Any], rating: str) -> str:
    supports = [item["name"] for item in candidate.get("supporting_evidence", [])[:3]]
    conflicts = [item["name"] for item in candidate.get("conflicting_evidence", [])[:2]]
    if rating in {"A+", "A"}:
        return " + ".join(supports) if supports else "multi-source confluence"
    if conflicts:
        return "Capped: " + " / ".join(conflicts)
    return "Watch only; confluence not strong enough."
