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
    ranked.sort(
        key=lambda item: (
            edge_rank(item["edge_status"]),
            1 if (item.get("precision_gate") or {}).get("passed") else 0,
            float(item.get("confluence_score") or 0),
            float(item.get("payoff_quality_score") or 0),
            float(item.get("elasticity_score") or 0),
        ),
        reverse=True,
    )
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
    expectation_gap_score = float(candidate.get("expectation_gap_score") or 50)
    payoff_quality_score = float(candidate.get("payoff_quality_score") or 50)
    execution_quality_score = float(candidate.get("execution_quality_score") or 50)
    elasticity_confirmation_factor = float(candidate.get("elasticity_confirmation_factor") or 0.50)
    signal_quality_gate = _signal_quality_gate(candidate)

    if strict:
        confluence_score = (
            confluence_score
            - risk_score * 0.08
            + max(expectation_gap_score - 55, 0) * 0.07
            + max(payoff_quality_score - 50, 0) * 0.06
            + max(execution_quality_score - 55, 0) * 0.04
        )
        if support_count < 4:
            confluence_score = min(confluence_score, 64)
        if catalyst_score < 55:
            confluence_score = min(confluence_score, 58)
        if expectation_gap_score < 50:
            confluence_score = min(confluence_score, 58)
        if payoff_quality_score < 45:
            confluence_score = min(confluence_score, 56)
        if "high_liquidity_risk" in risk_flags:
            confluence_score = min(confluence_score, 52)
    else:
        confluence_score = (
            confluence_score
            + max(expectation_gap_score - 58, 0) * 0.03
            + max(payoff_quality_score - 52, 0) * 0.03
            + max(execution_quality_score - 58, 0) * 0.02
        )
        if expectation_gap_score < 45 and catalyst_score < 55:
            confluence_score = min(confluence_score, 62)
        if payoff_quality_score < 42:
            confluence_score = min(confluence_score, 60)
    if market_context.get("data_freshness_status") != "fresh":
        confluence_score = min(confluence_score, 68 if not strict else 60)
    if candidate.get("pool_filter", {}).get("hard_excluded"):
        confluence_score = min(confluence_score, 30)
    confluence_score = min(confluence_score, signal_quality_gate["confluence_cap"])

    confluence_score = round(max(0, min(100, confluence_score)), 2)
    elasticity_score = round(
        max(
            0,
            min(
                100,
                elasticity_score
                + min(float(candidate["features"].get("relative_volume") or 1), 5) * 0.8
                + max(elasticity_confirmation_factor - 0.55, 0) * 12
                - max(risk_score - 60, 0) * 0.22
                - len(signal_quality_gate["critical_failures"]) * 4,
            ),
        ),
        2,
    )
    if elasticity_confirmation_factor < 0.46:
        elasticity_score = min(elasticity_score, 58)
    elif elasticity_confirmation_factor < 0.54:
        elasticity_score = min(elasticity_score, 66)
    if signal_quality_gate["level"] == "blocked":
        elasticity_score = min(elasticity_score, 62 if signal_quality_gate["critical_failures"] else 68)
    elif signal_quality_gate["level"] == "incomplete":
        elasticity_score = min(elasticity_score, 74)
    edge_status = _edge_status(candidate, confluence_score, elasticity_score, support_count, conflict_count, strict, signal_quality_gate)
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
        "signal_quality_gate": signal_quality_gate,
        "validation_status": "not_yet_validated",
    }
    enriched["upside_trigger_level"] = trade_plan["upside_trigger_level"]
    enriched["downside_risk_level"] = trade_plan["downside_risk_level"]
    enriched["invalidation_level"] = trade_plan["invalidation_level"]
    return enriched


def _edge_status(
    candidate: dict[str, Any],
    confluence: float,
    elasticity: float,
    support_count: int,
    conflict_count: int,
    strict: bool,
    signal_quality_gate: dict[str, Any],
) -> str:
    risk_score = float(candidate.get("risk_score") or 0)
    risk_flags = candidate.get("risk_flags") or []
    expectation_gap_score = float(candidate.get("expectation_gap_score") or 50)
    payoff_quality_score = float(candidate.get("payoff_quality_score") or 50)
    if candidate.get("candidate_type") == "no_edge" or candidate.get("pool_filter", {}).get("hard_excluded"):
        return "AVOID"
    if signal_quality_gate["level"] == "blocked":
        return "NO_EDGE"
    if signal_quality_gate["level"] == "incomplete" and confluence < 74:
        return "WATCH"
    if risk_score >= 72 or ("high_liquidity_risk" in risk_flags and confluence < 58):
        return "AVOID"
    if expectation_gap_score < 45 and confluence < 66:
        return "NO_EDGE"
    if payoff_quality_score < 42:
        return "WATCH" if confluence >= 64 else "NO_EDGE"
    if elasticity >= 76 and confluence >= 60 and risk_score >= 50:
        return "HIGH_RISK_HIGH_REWARD"
    if (
        signal_quality_gate["level"] == "confirmed"
        and confluence >= (82 if strict else 78)
        and expectation_gap_score >= 55
        and payoff_quality_score >= 52
        and support_count >= 5
        and conflict_count <= 2
    ):
        return "STRONG_EDGE"
    if signal_quality_gate["level"] in {"confirmed", "partial"} and confluence >= (72 if strict else 69) and support_count >= 4:
        return "MODERATE_EDGE"
    if confluence >= 52:
        return "WATCH"
    return "NO_EDGE"


def _signal_quality_gate(candidate: dict[str, Any]) -> dict[str, Any]:
    features = candidate.get("features") or {}
    news = candidate.get("news") or {}
    sector_theme = candidate.get("sector_theme") or {}
    supporting = candidate.get("supporting_evidence") or []
    conflicting = candidate.get("conflicting_evidence") or []
    support_sources = {item.get("source") for item in supporting}

    catalyst = float(candidate.get("catalyst_score") or 0)
    technical = float(features.get("technical_score") or 0)
    volume = float(features.get("volume_score") or 0)
    relative_volume = float(features.get("relative_volume") or 0)
    sector = float(sector_theme.get("score") or 0)
    payoff = float(candidate.get("payoff_quality_score") or 0)
    expectation_gap = float(candidate.get("expectation_gap_score") or 0)
    quote_status = (candidate.get("quote_confirmation") or {}).get("status")
    catalyst_type = news.get("catalyst_type")
    catalyst_quality = news.get("catalyst_quality")

    failures: list[str] = []
    critical: list[str] = []

    if catalyst < 58 or catalyst_type == "no_recent_confirmed_news" or catalyst_quality not in {"confirmed", "strong"} or "catalyst" not in support_sources:
        failures.append("催化不足或没有确认新闻")
    if technical < 55 or "price" not in support_sources:
        failures.append("技术结构未确认")
    if volume < 60 or relative_volume < 1.15 or "volume" not in support_sources:
        failures.append("成交量没有形成确认")
    if sector < 55:
        failures.append("板块主线不够强")
    if payoff < 52 or "payoff" not in support_sources:
        failures.append("赔率质量不足")
    if expectation_gap < 58:
        failures.append("预期差不足")
    if quote_status == "failed":
        failures.append("当前价确认失败")
        critical.append("当前价确认失败")
    if candidate.get("squeeze_data_status", {}).get("short_interest") == "proxy" and candidate.get("candidate_type") == "short_squeeze_candidate":
        failures.append("逼空逻辑只有 proxy，不能作为强共振")

    if catalyst_quality in {"missing", "unconfirmed", "conflicted"} and technical < 65:
        critical.append("催化质量未确认")
    if catalyst < 45 and technical < 65:
        critical.append("缺催化且技术不强")
    if volume < 52:
        critical.append("成交量弱")
    if technical < 42:
        critical.append("技术结构弱")

    if critical:
        level = "blocked"
        cap = 58
    elif not failures:
        level = "confirmed"
        cap = 100
    elif len(failures) <= 2 and catalyst >= 50 and technical >= 50 and volume >= 55 and payoff >= 48:
        level = "partial"
        cap = 74
    else:
        level = "incomplete"
        cap = 66

    return {
        "level": level,
        "passed": level == "confirmed",
        "failures": failures[:8],
        "critical_failures": critical[:5],
        "confluence_cap": cap,
        "required_sources": ["catalyst", "price", "volume", "payoff", "sector_or_market"],
        "support_sources": sorted(source for source in support_sources if source),
    }


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
        "edge_status_note": "edge_status 是预测优势等级，不是交易建议。",
        "entry_condition": "无主动优势，仅观察" if rating == "C" else f"只有站上并维持在 {levels.get('upside_trigger_level'):.2f} 上方，上冲路径才开始确认",
        "upside_trigger_level": levels.get("upside_trigger_level"),
        "downside_risk_level": levels.get("downside_risk_level"),
        "invalidation_level": levels.get("invalidation_level"),
        "gap_fill_level": levels.get("gap_fill_level"),
        "breakout_level": levels.get("breakout_level"),
        "breakdown_level": levels.get("breakdown_level"),
        "nearest_support": levels.get("nearest_support"),
        "nearest_resistance": levels.get("nearest_resistance"),
        "stop_condition": "无主动优势" if rating == "C" else f"跌破 {levels.get('invalidation_level'):.2f}，当前上冲/反抽路径失效",
        "target_low_price": expected.get("expected_mid"),
        "target_high_price": expected.get("expected_high"),
        "next_day_expected_range": expected,
        "overnight_or_intraday": "只适合盘中确认" if rating != "A+" else "可观察隔夜延续，但仍需盘中确认",
        "not_trading_advice": "这些是概率路径点位，不是投资建议、买卖指令或仓位建议。",
    }


def _reason(candidate: dict[str, Any], edge_status: str) -> str:
    supports = [item.get("detail") or item.get("name") for item in candidate.get("supporting_evidence", [])[:3]]
    conflicts = [item.get("detail") or item.get("name") for item in candidate.get("conflicting_evidence", [])[:2]]
    if edge_status in {"STRONG_EDGE", "MODERATE_EDGE", "HIGH_RISK_HIGH_REWARD"}:
        return " / ".join(supports[:2]) if supports else "多源共振"
    if conflicts:
        return "压制：" + " / ".join(conflicts[:2])
    return "没有明显优势，共振不足。"
