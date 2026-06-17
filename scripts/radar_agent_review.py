from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any


AGENCY_SOURCE_REPO = "msitarzewski/agency-agents"
REVIEW_VERSION = "radar_agency_review_v1"


def build_radar_agent_review(dashboard: dict[str, Any]) -> dict[str, Any]:
    """Deterministic agency-style review over the generated radar payload.

    This is intentionally rule based. It borrows the agency-agents pattern of
    specialist roles, evidence, and quality gates without adding an LLM runtime
    or any frontend/API-key exposure.
    """

    candidates = list(dashboard.get("top_candidates") or [])
    top10 = candidates[:10]
    top5 = candidates[:5]
    market_context = dashboard.get("market_context") or {}
    validation = dashboard.get("validation") or {}
    provider_status = dashboard.get("provider_status") or {}
    data_quality = dashboard.get("data_quality") or {}

    metrics = _candidate_metrics(top10=top10, top5=top5)
    findings = [
        _market_path_agent(dashboard, market_context, metrics),
        _sector_theme_agent(dashboard, top10),
        _expectation_gap_agent(metrics),
        _execution_quality_agent(metrics, top5),
        _risk_reality_checker(dashboard, top10, metrics),
        _validation_agent(validation, dashboard.get("model_leaderboard") or {}),
        _data_quality_agent(data_quality, provider_status),
        _dashboard_guardrail_agent(dashboard),
    ]

    hard_warnings = _hard_warnings(dashboard, findings, metrics)
    quality_gate = _quality_gate(dashboard, findings, metrics)
    overall_decision = _overall_decision(dashboard, metrics, quality_gate)

    return {
        "version": REVIEW_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_framework": AGENCY_SOURCE_REPO,
        "source_method": "specialist_agents_quality_gates_evidence_review",
        "overall_decision": overall_decision,
        "agency_quality_gate": quality_gate,
        "market_permission": _market_permission(dashboard, overall_decision),
        "top10_metric_snapshot": metrics,
        "agent_findings": findings,
        "top_candidate_agent_notes": [_candidate_note(candidate) for candidate in top10],
        "hard_warnings": hard_warnings,
        "not_trading_advice": "这是次日高弹性概率雷达，不是投资建议、买卖指令或仓位建议。",
    }


def render_radar_agent_review_markdown(review: dict[str, Any]) -> str:
    lines = [
        "# Radar Agency Review",
        "",
        f"- version: `{review.get('version')}`",
        f"- source_framework: `{review.get('source_framework')}`",
        f"- generated_at: `{review.get('generated_at')}`",
        f"- overall_decision: `{review.get('overall_decision')}`",
        f"- agency_quality_gate: `{review.get('agency_quality_gate')}`",
        f"- market_permission: `{review.get('market_permission')}`",
        "",
        "## Hard Warnings",
        "",
    ]
    warnings = review.get("hard_warnings") or []
    if warnings:
        lines.extend(f"- {warning}" for warning in warnings)
    else:
        lines.append("- 无硬警告。")

    lines.extend(["", "## Agent Findings", ""])
    for finding in review.get("agent_findings") or []:
        lines.extend(
            [
                f"### {finding.get('agent_name')}",
                "",
                f"- status: `{finding.get('status')}`",
                f"- conclusion: {finding.get('conclusion')}",
                f"- evidence: {finding.get('evidence')}",
            ]
        )
        for warning in finding.get("warnings") or []:
            lines.append(f"- warning: {warning}")
        lines.append("")

    lines.extend(
        [
            "## Top Candidate Notes",
            "",
            "| Rank | Ticker | Verdict | Key Check | Warnings |",
            "| ---: | --- | --- | --- | --- |",
        ]
    )
    for note in review.get("top_candidate_agent_notes") or []:
        warnings_text = " / ".join(note.get("warnings") or []) or "-"
        lines.append(
            f"| {note.get('rank')} | {note.get('ticker')} | {note.get('agency_verdict')} | "
            f"{note.get('key_check')} | {warnings_text} |"
        )

    lines.extend(["", review.get("not_trading_advice") or ""])
    return "\n".join(lines)


def _candidate_metrics(*, top10: list[dict[str, Any]], top5: list[dict[str, Any]]) -> dict[str, Any]:
    sectors = Counter(candidate.get("sector") or "unknown" for candidate in top10)
    types = Counter(candidate.get("candidate_type") or "unknown" for candidate in top10)
    top5_risk_flags = [flag for candidate in top5 for flag in candidate.get("risk_flags") or []]
    top10_risk_flags = [flag for candidate in top10 for flag in candidate.get("risk_flags") or []]
    low_sample_count = sum(1 for candidate in top10 if (candidate.get("historical_analog") or {}).get("low_sample_warning"))
    proxy_squeeze_count = sum(
        1
        for candidate in top10
        if "proxy" in set((candidate.get("squeeze_data_status") or {}).values())
        or (candidate.get("squeeze_data_status") or {}).get("short_interest") == "proxy"
    )
    strong_edge_count = sum(1 for candidate in top10 if candidate.get("edge_status") == "STRONG_EDGE")
    moderate_edge_count = sum(1 for candidate in top10 if candidate.get("edge_status") == "MODERATE_EDGE")

    return {
        "top10_count": len(top10),
        "top5_count": len(top5),
        "strong_edge_count": strong_edge_count,
        "moderate_edge_count": moderate_edge_count,
        "avg_top5_elasticity_score": _avg(candidate.get("elasticity_score") for candidate in top5),
        "avg_top5_confluence_score": _avg(candidate.get("confluence_score") for candidate in top5),
        "avg_top5_expectation_gap_score": _avg(candidate.get("expectation_gap_score") for candidate in top5),
        "avg_top5_payoff_quality_score": _avg(candidate.get("payoff_quality_score") for candidate in top5),
        "avg_top5_execution_quality_score": _avg(candidate.get("execution_quality_score") for candidate in top5),
        "avg_top5_risk_score": _avg(candidate.get("risk_score") for candidate in top5),
        "min_top5_confluence_score": _min(candidate.get("confluence_score") for candidate in top5),
        "min_top5_expectation_gap_score": _min(candidate.get("expectation_gap_score") for candidate in top5),
        "top_sector": sectors.most_common(1)[0][0] if sectors else "unknown",
        "top_sector_count": sectors.most_common(1)[0][1] if sectors else 0,
        "top_candidate_type": types.most_common(1)[0][0] if types else "unknown",
        "top_candidate_type_count": types.most_common(1)[0][1] if types else 0,
        "top5_high_liquidity_risk_count": top5_risk_flags.count("high_liquidity_risk"),
        "top10_high_liquidity_risk_count": top10_risk_flags.count("high_liquidity_risk"),
        "top10_high_volatility_risk_count": top10_risk_flags.count("high_risk_high_volatility"),
        "top10_low_sample_warning_count": low_sample_count,
        "top10_proxy_squeeze_count": proxy_squeeze_count,
    }


def _market_path_agent(dashboard: dict[str, Any], market_context: dict[str, Any], metrics: dict[str, Any]) -> dict[str, Any]:
    market_state = market_context.get("market_state") or "unknown"
    freshness = dashboard.get("data_freshness_status") or "missing"
    warnings = []
    status = "pass"

    if freshness in {"missing", "fallback_only"}:
        status = "fail"
        warnings.append("数据缺失或全部降级，不能当作今日雷达。")
    elif dashboard.get("stale_warning"):
        status = "warn"
        warnings.append("存在数据新鲜度或降级警告，需要盘前再次刷新确认。")

    if market_state == "defense":
        status = "fail" if status == "fail" else "warn"
        warnings.append("市场路径偏防守，个股信号必须降级处理。")
    elif metrics.get("strong_edge_count", 0) < 2:
        status = "warn" if status == "pass" else status
        warnings.append("强优势候选数量不足，不能强行进攻。")

    return _finding(
        "市场路径代理",
        status,
        "检查 SPY/QQQ/IWM/VIX 与数据新鲜度是否支持次日机会筛选。",
        f"market_state={market_state}; freshness={freshness}; strong_edge_count={metrics.get('strong_edge_count')}",
        warnings,
    )


def _sector_theme_agent(dashboard: dict[str, Any], top10: list[dict[str, Any]]) -> dict[str, Any]:
    sector_strength = dashboard.get("sector_strength") or {}
    sectors = Counter(candidate.get("sector") or "unknown" for candidate in top10)
    types = Counter(candidate.get("candidate_type") or "unknown" for candidate in top10)
    top_sector, top_sector_count = sectors.most_common(1)[0] if sectors else ("unknown", 0)
    top_type, top_type_count = types.most_common(1)[0] if types else ("unknown", 0)
    warnings = []
    status = "pass"

    if not top10:
        status = "fail"
        warnings.append("没有候选，无法形成主线。")
    elif top_sector_count < 2 and top_type_count < 2:
        status = "warn"
        warnings.append("Top 10 主线集中度偏低，更多是离散机会。")
    if not sector_strength:
        status = "warn" if status == "pass" else status
        warnings.append("板块强弱数据缺失，板块共振只能用候选分布代理。")

    return _finding(
        "板块主线代理",
        status,
        "先判断资金主线，再允许个股进入高等级机会。",
        f"top_sector={top_sector}({top_sector_count}); top_type={top_type}({top_type_count})",
        warnings,
    )


def _expectation_gap_agent(metrics: dict[str, Any]) -> dict[str, Any]:
    avg_gap = metrics.get("avg_top5_expectation_gap_score") or 0
    min_gap = metrics.get("min_top5_expectation_gap_score") or 0
    warnings = []
    if avg_gap >= 70 and min_gap >= 45:
        status = "pass"
    elif avg_gap >= 55:
        status = "warn"
        warnings.append("Top 5 平均预期差尚可，但最低预期差偏弱。")
    else:
        status = "fail"
        warnings.append("预期差不足，容易变成表面热闹但没有交易价值。")

    return _finding(
        "预期差代理",
        status,
        "验证催化、成交和价格是否真的形成超预期，而不是只靠热度。",
        f"avg_top5_gap={avg_gap}; min_top5_gap={min_gap}",
        warnings,
    )


def _execution_quality_agent(metrics: dict[str, Any], top5: list[dict[str, Any]]) -> dict[str, Any]:
    avg_payoff = metrics.get("avg_top5_payoff_quality_score") or 0
    avg_execution = metrics.get("avg_top5_execution_quality_score") or 0
    avg_risk = metrics.get("avg_top5_risk_score") or 0
    warnings = []
    status = "pass"

    if avg_payoff < 50 or avg_execution < 45:
        status = "warn"
        warnings.append("赔率或执行质量不足，触发价没有确认前不应把它当成强机会。")
    if avg_risk > 45:
        status = "warn"
        warnings.append("Top 5 平均风险过高，容易冲高回落。")
    if metrics.get("top5_high_liquidity_risk_count", 0):
        status = "fail"
        warnings.append("Top 5 存在高流动性风险标的，不能通过执行质量闸门。")
    if not top5:
        status = "fail"
        warnings.append("没有 Top 5 候选。")

    return _finding(
        "执行质量代理",
        status,
        "检查触发价、失效价、赔率质量和流动性是否可执行。",
        f"avg_payoff={avg_payoff}; avg_execution={avg_execution}; avg_risk={avg_risk}",
        warnings,
    )


def _risk_reality_checker(dashboard: dict[str, Any], top10: list[dict[str, Any]], metrics: dict[str, Any]) -> dict[str, Any]:
    warnings = []
    status = "pass"

    if dashboard.get("stale_warning"):
        warnings.append("页面必须显示 stale warning；不能把降级数据伪装成今日预测。")
    if metrics.get("top10_proxy_squeeze_count", 0):
        warnings.append("部分逼空/期权信号仍是 proxy，不能当成真实空头或期权数据。")
    if metrics.get("top10_low_sample_warning_count", 0):
        warnings.append("部分历史相似样本不足，不能把相似样本结论当作验证。")
    if metrics.get("top10_high_volatility_risk_count", 0):
        warnings.append("Top 10 中存在高波动小票风险，需要显式标记。")
    if metrics.get("top10_high_liquidity_risk_count", 0):
        warnings.append("Top 10 中存在高流动性风险，必须压低等级。")

    if metrics.get("top10_high_liquidity_risk_count", 0):
        status = "fail"
    elif warnings:
        status = "warn"
    if not top10:
        status = "fail"
        warnings.append("没有候选可供现实校验。")

    return _finding(
        "风险现实校验代理",
        status,
        "默认怀疑一切表面强势，专查旧数据、proxy、流动性、小样本和冲高回落风险。",
        (
            f"proxy_squeeze={metrics.get('top10_proxy_squeeze_count')}; "
            f"low_sample={metrics.get('top10_low_sample_warning_count')}; "
            f"liquidity_risk={metrics.get('top10_high_liquidity_risk_count')}"
        ),
        warnings,
    )


def _validation_agent(validation: dict[str, Any], leaderboard: dict[str, Any]) -> dict[str, Any]:
    validation_status = validation.get("validation_status") or "not_yet_validated"
    completed = int(validation.get("completed_next_day_forecasts") or 0)
    leaderboard_status = leaderboard.get("validation_status") or validation_status
    warnings = []

    if validation_status == "validated" and completed >= 60:
        status = "pass"
    elif completed >= 10:
        status = "warn"
        warnings.append("已有早期样本，但还没有达到 30-60 个交易日前向验证标准。")
    else:
        status = "warn"
        warnings.append("样本仍不足，只能称为 early evidence / not yet validated。")

    return _finding(
        "验证代理",
        status,
        "检查 Forecast Ledger、Baseline/Challenger 和前向样本是否支持模型升级。",
        f"validation={validation_status}; completed={completed}; leaderboard={leaderboard_status}",
        warnings,
    )


def _data_quality_agent(data_quality: dict[str, Any], provider_status: dict[str, Any]) -> dict[str, Any]:
    score = data_quality.get("score")
    freshness = data_quality.get("data_freshness_status") or "missing"
    finnhub = (provider_status.get("finnhub") or {}).get("availability_status")
    yahoo_fallback = int((provider_status.get("yahoo") or {}).get("fallback_count") or 0)
    warnings = []

    if score is None or score < 55 or freshness in {"missing", "fallback_only"}:
        status = "fail"
        warnings.append("数据质量不足，不能生成可信雷达。")
    elif score < 80 or yahoo_fallback:
        status = "warn"
        warnings.append("存在数据源降级，候选已被过滤或压制，但仍需人工确认。")
    else:
        status = "pass"

    if finnhub in {"missing", "partial"}:
        warnings.append("Finnhub 非完全可用，新闻/事件催化可能不完整。")

    return _finding(
        "数据质量代理",
        status,
        "检查 provider 状态、降级数量、最新交易日和数据质量分。",
        f"score={score}; freshness={freshness}; yahoo_fallback={yahoo_fallback}; finnhub={finnhub}",
        warnings,
    )


def _dashboard_guardrail_agent(dashboard: dict[str, Any]) -> dict[str, Any]:
    has_static_payload = bool(dashboard.get("top_candidates") is not None and dashboard.get("provider_status") is not None)
    has_disclaimer = bool(dashboard.get("radar_summary") is not None)
    warnings = []
    status = "pass"

    if not has_static_payload:
        status = "fail"
        warnings.append("缺少静态 Dashboard payload。")
    if not has_disclaimer:
        status = "warn" if status == "pass" else status
        warnings.append("缺少中文摘要，用户第一屏无法直接判断。")

    return _finding(
        "中文仪表盘代理",
        status,
        "确认前端只读取静态 JSON，并把复杂推理放到后面。",
        f"static_payload={has_static_payload}; candidate_count={dashboard.get('candidate_count')}",
        warnings,
    )


def _candidate_note(candidate: dict[str, Any]) -> dict[str, Any]:
    warnings = []
    risk_flags = candidate.get("risk_flags") or []
    analog = candidate.get("historical_analog") or {}
    if risk_flags:
        warnings.append("风险标记：" + " / ".join(risk_flags))
    if analog.get("low_sample_warning"):
        warnings.append("历史相似样本不足")
    if "proxy" in set((candidate.get("squeeze_data_status") or {}).values()):
        warnings.append("逼空/期权相关数据为 proxy")
    if (candidate.get("precision_gate") or {}).get("passed") is False:
        warnings.append("精准闸门未通过")

    confluence = candidate.get("confluence_score") or 0
    gap = candidate.get("expectation_gap_score") or 0
    payoff = candidate.get("payoff_quality_score") or 0
    risk = candidate.get("risk_score") or 0
    edge = candidate.get("edge_status")
    if edge == "STRONG_EDGE" and confluence >= 80 and gap >= 70 and payoff >= 55 and risk <= 35:
        verdict = "强共振候选"
    elif edge in {"STRONG_EDGE", "MODERATE_EDGE"}:
        verdict = "可观察候选"
    else:
        verdict = "共振不足"

    return {
        "rank": candidate.get("rank"),
        "ticker": candidate.get("ticker"),
        "candidate_type": candidate.get("candidate_type"),
        "agency_verdict": verdict,
        "key_check": (
            f"共振 {confluence}; 预期差 {gap}; 赔率 {payoff}; 风险 {risk}; "
            f"闸门 {(candidate.get('precision_gate') or {}).get('level', '-')}"
        ),
        "trigger": candidate.get("upside_trigger_level") or (candidate.get("trigger_levels") or {}).get("upside_trigger_level"),
        "invalidation": candidate.get("invalidation_level") or (candidate.get("trigger_levels") or {}).get("invalidation_level"),
        "warnings": warnings,
    }


def _hard_warnings(dashboard: dict[str, Any], findings: list[dict[str, Any]], metrics: dict[str, Any]) -> list[str]:
    warnings = []
    if dashboard.get("stale_warning"):
        warnings.append("存在 stale warning 或数据源降级，页面不得假装是完全新鲜数据。")
    if dashboard.get("data_freshness_status") in {"missing", "fallback_only"}:
        warnings.append("数据缺失或全部降级时，雷达只能观察，不能进攻。")
    if (dashboard.get("market_context") or {}).get("market_state") == "defense":
        warnings.append("市场路径偏防守，所有个股等级应自动压低。")
    if metrics.get("top10_high_liquidity_risk_count", 0):
        warnings.append("Top 候选存在高流动性风险，执行前必须剔除或降级。")
    if metrics.get("top10_proxy_squeeze_count", 0):
        warnings.append("逼空/期权相关评分包含 proxy，不是真实 short interest / options 数据。")
    for finding in findings:
        for warning in finding.get("warnings") or []:
            if warning not in warnings and ("不能" in warning or "必须" in warning):
                warnings.append(warning)
    return warnings[:12]


def _quality_gate(dashboard: dict[str, Any], findings: list[dict[str, Any]], metrics: dict[str, Any]) -> str:
    statuses = [finding.get("status") for finding in findings]
    if "fail" in statuses or not metrics.get("top10_count"):
        return "不通过"
    if (
        dashboard.get("data_freshness_status") == "fresh"
        and not dashboard.get("stale_warning")
        and metrics.get("strong_edge_count", 0) >= 3
        and (metrics.get("avg_top5_confluence_score") or 0) >= 75
        and (metrics.get("avg_top5_expectation_gap_score") or 0) >= 65
        and (metrics.get("avg_top5_payoff_quality_score") or 0) >= 50
        and "warn" not in statuses[:5]
    ):
        return "通过"
    return "谨慎通过"


def _overall_decision(dashboard: dict[str, Any], metrics: dict[str, Any], quality_gate: str) -> str:
    market_state = (dashboard.get("market_context") or {}).get("market_state")
    if quality_gate == "不通过" or market_state == "defense":
        return "防守"
    if (
        dashboard.get("high_elasticity_opportunity")
        and metrics.get("strong_edge_count", 0) >= 3
        and (metrics.get("avg_top5_confluence_score") or 0) >= 75
        and (metrics.get("avg_top5_expectation_gap_score") or 0) >= 65
    ):
        return "进攻"
    return "观察"


def _market_permission(dashboard: dict[str, Any], overall_decision: str) -> str:
    if overall_decision == "进攻":
        return "允许筛选高弹性机会，但只能按触发价和失效价确认。"
    if overall_decision == "观察":
        return "只观察候选，不强行追逐；等待盘前刷新和触发确认。"
    return "防守优先；候选降级，避免把弱信号当成机会。"


def _finding(
    agent_name: str,
    status: str,
    conclusion: str,
    evidence: str,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "agent_name": agent_name,
        "status": status,
        "conclusion": conclusion,
        "evidence": evidence,
        "warnings": warnings or [],
    }


def _avg(values: Any) -> float | None:
    numbers = [float(value) for value in values if _is_number(value)]
    if not numbers:
        return None
    return round(sum(numbers) / len(numbers), 2)


def _min(values: Any) -> float | None:
    numbers = [float(value) for value in values if _is_number(value)]
    if not numbers:
        return None
    return round(min(numbers), 2)


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)
