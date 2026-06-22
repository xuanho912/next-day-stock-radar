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
            float(item.get("trust_score") or 0),
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
    setup_quality_score = float(candidate.get("setup_quality_score") or 0)
    extension_risk_score = float(candidate.get("extension_risk_score") or 0)
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
            + max(setup_quality_score - 62, 0) * 0.10
            - max(extension_risk_score - 64, 0) * 0.18
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
    if candidate.get("candidate_type") in {"next_day_upside_momentum", "gap_continuation"} and extension_risk_score >= 72:
        confluence_score = min(confluence_score, 62)
    if candidate.get("candidate_type") in {"pullback_reversal_setup", "accumulation_breakout_setup"} and setup_quality_score >= 70 and extension_risk_score < 62:
        confluence_score = min(78, confluence_score + 4)

    confluence_score = round(max(0, min(100, confluence_score)), 2)
    elasticity_score = round(
        max(
            0,
            min(
                100,
                elasticity_score
                + min(float(candidate["features"].get("relative_volume") or 1), 5) * 0.8
                + max(elasticity_confirmation_factor - 0.55, 0) * 12
                + max(setup_quality_score - 68, 0) * 0.10
                - max(risk_score - 60, 0) * 0.22
                - max(extension_risk_score - 70, 0) * 0.18
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
    capital_readiness = _capital_readiness_audit(
        candidate,
        market_context,
        signal_quality_gate,
        edge_status,
        rating,
        confluence_score,
        elasticity_score,
    )

    if capital_readiness["readiness_status"] == "NOT_TRUSTED_FOR_REAL_MONEY":
        edge_status = "NO_EDGE"
        rating = "C"
    elif capital_readiness["trust_score"] < 70 and edge_status in {"STRONG_EDGE", "MODERATE_EDGE"}:
        edge_status = "WATCH"
        rating = "B"

    capital_readiness = _capital_readiness_audit(
        candidate,
        market_context,
        signal_quality_gate,
        edge_status,
        rating,
        confluence_score,
        elasticity_score,
    )
    scenario_overrides = _scenario_overrides(candidate, edge_status, signal_quality_gate)
    trade_plan = _trade_plan(candidate, rating, edge_status)
    reason = _reason(candidate, edge_status)
    if capital_readiness["readiness_status"] == "NOT_TRUSTED_FOR_REAL_MONEY":
        audit_reasons = capital_readiness["blockers"] or capital_readiness["warnings"] or ["信任分低于最低门槛"]
        reason = "真钱审计未通过：" + " / ".join(audit_reasons[:2])
    elif capital_readiness["warnings"] and edge_status == "WATCH":
        reason = "只适合观察：" + " / ".join(capital_readiness["warnings"][:2])

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
        "capital_readiness": capital_readiness,
        "trust_score": capital_readiness["trust_score"],
        "readiness_status": capital_readiness["readiness_status"],
        "readiness_label": capital_readiness["readiness_label"],
        "validation_status": "not_yet_validated",
        **scenario_overrides,
    }
    enriched["upside_trigger_level"] = trade_plan["upside_trigger_level"]
    enriched["downside_risk_level"] = trade_plan["downside_risk_level"]
    enriched["invalidation_level"] = trade_plan["invalidation_level"]
    return enriched


def _scenario_overrides(candidate: dict[str, Any], edge_status: str, signal_quality_gate: dict[str, Any]) -> dict[str, Any]:
    if edge_status not in {"NO_EDGE", "AVOID"} and signal_quality_gate.get("level") != "blocked":
        return {}
    return {
        "raw_candidate_type": candidate.get("candidate_type"),
        "candidate_type": "no_edge",
        "primary_scenario": "no_edge",
        "secondary_scenario": "no_edge",
        "primary_probability": min(float(candidate.get("primary_probability") or 0), 0.15),
        "secondary_probability": min(float(candidate.get("secondary_probability") or 0), 0.20),
    }


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
    setup_quality_score = float(candidate.get("setup_quality_score") or 0)
    extension_risk_score = float(candidate.get("extension_risk_score") or 0)
    setup_type = candidate.get("candidate_type") in {"pullback_reversal_setup", "accumulation_breakout_setup"}
    chase_type = candidate.get("candidate_type") in {"next_day_upside_momentum", "gap_continuation"}
    if candidate.get("candidate_type") == "no_edge" or candidate.get("pool_filter", {}).get("hard_excluded"):
        return "AVOID"
    if signal_quality_gate["level"] == "blocked":
        return "NO_EDGE"
    if signal_quality_gate["level"] == "incomplete" and confluence < 74:
        return "WATCH"
    if risk_score >= 72 or ("high_liquidity_risk" in risk_flags and confluence < 58):
        return "AVOID"
    if chase_type and extension_risk_score >= 76:
        return "NO_EDGE" if confluence < 72 else "WATCH"
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
    if (
        setup_type
        and signal_quality_gate["level"] in {"confirmed", "partial"}
        and setup_quality_score >= 72
        and extension_risk_score < 62
        and confluence >= (70 if strict else 66)
        and support_count >= 3
    ):
        return "MODERATE_EDGE"
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
    setup_quality_score = float(candidate.get("setup_quality_score") or 0)
    extension_risk_score = float(candidate.get("extension_risk_score") or 0)
    quote_status = (candidate.get("quote_confirmation") or {}).get("status")
    catalyst_type = news.get("catalyst_type")
    catalyst_quality = news.get("catalyst_quality")
    setup_type = candidate.get("candidate_type") in {"pullback_reversal_setup", "accumulation_breakout_setup"}

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

    if catalyst_quality in {"missing", "unconfirmed", "conflicted"} and technical < 65 and not (setup_type and setup_quality_score >= 68):
        critical.append("催化质量未确认")
    if catalyst < 45 and technical < 65 and not (setup_type and setup_quality_score >= 70):
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
    elif (
        len(failures) <= (3 if setup_type else 2)
        and (catalyst >= 50 or setup_quality_score >= 68)
        and technical >= 50
        and volume >= (50 if setup_type else 55)
        and payoff >= 45
        and extension_risk_score < 72
    ):
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


def _capital_readiness_audit(
    candidate: dict[str, Any],
    market_context: dict[str, Any],
    signal_quality_gate: dict[str, Any],
    edge_status: str,
    rating: str,
    confluence_score: float,
    elasticity_score: float,
) -> dict[str, Any]:
    features = candidate.get("features") or {}
    quote = candidate.get("quote_confirmation") or features.get("quote_confirmation") or {}
    matrix = candidate.get("confluence_matrix") or {}
    analog = candidate.get("historical_analog") or {}
    news = candidate.get("news") or {}
    risk_flags = candidate.get("risk_flags") or []
    pool_filter = candidate.get("pool_filter") or {}
    squeeze_status = candidate.get("squeeze_data_status") or {}
    candidate_type = candidate.get("candidate_type")
    setup_type = candidate_type in {"pullback_reversal_setup", "accumulation_breakout_setup", "oversold_bounce"}

    score = 100.0
    caps: list[float] = []
    blockers: list[str] = []
    warnings: list[str] = []
    positives: list[str] = []

    def penalize(points: float, message: str, *, critical: bool = False, cap: float | None = None) -> None:
        nonlocal score
        score -= points
        if critical:
            blockers.append(message)
        else:
            warnings.append(message)
        if cap is not None:
            caps.append(cap)

    if features.get("real_data"):
        positives.append("真实 OHLCV 行情可用")
    else:
        penalize(45, "真实行情缺失或降级", critical=True, cap=42)

    freshness = market_context.get("data_freshness_status")
    if freshness == "fresh":
        positives.append("市场数据为最新交易日")
    elif freshness == "partial_fallback":
        penalize(18, "部分行情或市场数据降级", cap=68)
    else:
        penalize(32, "市场数据不是最新交易日", critical=True, cap=48)

    quote_status = quote.get("status")
    if quote_status == "confirming":
        positives.append("当前价没有否定路径")
    elif quote_status == "failed":
        penalize(35, "当前价已经否定触发路径", critical=True, cap=45)
    elif quote_status == "missing":
        penalize(14, "当前价确认缺失，触发价需刷新", cap=72)
    else:
        penalize(8, "当前价状态不明确")

    gate_level = signal_quality_gate.get("level")
    if gate_level == "confirmed":
        positives.append("催化、价格、成交、赔率闸门确认")
    elif gate_level == "partial":
        penalize(8, "信号闸门只有部分确认")
    elif gate_level == "incomplete":
        penalize(22, "信号闸门不完整", cap=64)
    else:
        penalize(35, "信号闸门阻断", critical=True, cap=46)

    matrix_overall = matrix.get("overall")
    if matrix_overall == "confirmed":
        positives.append("多维共振确认")
    elif matrix_overall == "partial":
        penalize(8, "共振只有部分成立")
    elif matrix_overall == "blocked":
        penalize(32, "共振矩阵存在硬阻断", critical=True, cap=50)
    else:
        penalize(10, "共振矩阵状态缺失")

    sample_size = int(analog.get("sample_size") or 0)
    hit_rate = analog.get("next_day_hit_rate")
    analog_avg = analog.get("next_day_return_avg")
    if sample_size >= 20 and not analog.get("low_sample_warning"):
        positives.append("历史相似样本数量可用")
    elif sample_size:
        penalize(10, "历史相似样本偏少", cap=78)
    else:
        penalize(16, "没有可用历史相似样本", cap=74)
    if sample_size >= 8 and hit_rate is not None and float(hit_rate) < 0.45:
        penalize(8, "历史相似样本次日命中率偏弱")
    if sample_size >= 8 and analog_avg is not None and float(analog_avg) < 0:
        penalize(8, "历史相似样本次日均值为负")

    payoff = float(candidate.get("payoff_quality_score") or 0)
    risk_reward = float(candidate.get("risk_reward_ratio") or 0)
    if payoff >= 55 and risk_reward >= 1.0:
        positives.append("上行空间相对失效风险有赔率")
    elif payoff < 45 or risk_reward < 0.7:
        penalize(16, "赔率不足，预期上行不够覆盖失效风险", cap=68)
    else:
        penalize(7, "赔率一般")

    setup_quality = float(candidate.get("setup_quality_score") or 0)
    extension_risk = float(candidate.get("extension_risk_score") or 0)
    if setup_type and setup_quality >= 72:
        positives.append("低吸/蓄势结构质量较好")
    elif setup_type and setup_quality < 62:
        penalize(12, "低吸/蓄势结构不够干净")
    if extension_risk >= 82:
        penalize(24, "追涨过热风险过高", critical=True, cap=50)
    elif extension_risk >= 72:
        penalize(14, "已经明显延伸，容易冲高回落", cap=66)
    elif extension_risk < 55:
        positives.append("没有明显追涨过热")

    risk_score = float(candidate.get("risk_score") or 0)
    if risk_score >= 75:
        penalize(24, "综合风险过高", critical=True, cap=52)
    elif risk_score >= 62:
        penalize(12, "风险偏高")

    if "high_liquidity_risk" in risk_flags:
        penalize(26, "流动性风险高", critical=True, cap=48)
    if "fallback_or_missing_price_data" in risk_flags:
        penalize(26, "价格数据缺失或降级", critical=True, cap=46)
    if "high_risk_high_volatility" in risk_flags:
        penalize(10, "高波动小票风险")
    if "gap_fade_risk" in risk_flags:
        penalize(10, "存在跳空回落风险")
    if pool_filter.get("hard_excluded"):
        penalize(40, "候选池硬过滤未通过", critical=True, cap=35)

    catalyst = float(candidate.get("catalyst_score") or 0)
    news_status = news.get("news_data_status")
    if catalyst >= 62:
        positives.append("催化分支持")
    elif setup_type and setup_quality >= 70:
        warnings.append("催化偏弱，但结构型候选可继续观察")
        score -= 5
    else:
        penalize(12, "催化不足，不能按强事件票处理", cap=72)
    if news_status == "missing" and candidate_type in {"event_driven_volatility", "next_day_upside_momentum", "short_squeeze_candidate"}:
        penalize(12, "新闻催化数据缺失")

    if candidate_type == "short_squeeze_candidate" and squeeze_status.get("short_interest") == "proxy":
        penalize(16, "逼空逻辑只有 proxy，缺少真实 short/options 数据", cap=66)

    if market_context.get("market_state") == "defense":
        penalize(12, "市场背景偏防守，个股信号需要降级")
    elif market_context.get("market_state") == "attack":
        positives.append("市场背景支持进攻")

    if confluence_score >= 72 and elasticity_score >= 60:
        positives.append("共振和弹性分达到候选区间")
    elif confluence_score < 58:
        penalize(12, "共振分不足")

    if edge_status in {"STRONG_EDGE", "MODERATE_EDGE"} and rating in {"A+", "A"}:
        positives.append("模型优势等级达到重点观察")
    elif edge_status == "WATCH":
        penalize(6, "优势等级仍是观察")

    if caps:
        score = min(score, min(caps))
    score = round(max(0, min(100, score)), 2)

    if blockers or score < 55:
        status = "NOT_TRUSTED_FOR_REAL_MONEY"
        label = "真钱审计未通过"
    elif score < 70:
        status = "WATCHLIST_ONLY"
        label = "只适合观察"
    elif score < 82:
        status = "TRIGGER_READY_WATCH"
        label = "触发后重点观察"
    else:
        status = "HIGH_CONFIDENCE_AFTER_TRIGGER"
        label = "触发后可信度较高"

    return {
        "version": "capital_readiness_audit_v1",
        "trust_score": score,
        "readiness_status": status,
        "readiness_label": label,
        "blockers": blockers[:8],
        "warnings": warnings[:10],
        "positive_factors": positives[:10],
        "not_trading_advice": "这是候选可信度审计，不是买卖建议或交易指令。",
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
