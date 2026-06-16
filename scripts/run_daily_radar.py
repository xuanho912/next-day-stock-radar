from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from candidate_ranking_engine import BASELINE_MODEL_VERSION, CHALLENGER_MODEL_VERSION, rank_candidates
from forecast_validation_engine import (
    build_model_leaderboard,
    public_records,
    render_model_leaderboard_markdown,
    update_forecast_ledger,
)
from providers.finnhub_provider import fetch_finnhub_bundle
from providers.fred_provider import fetch_fred_bundle
from providers.market_context_provider import CORE_MARKET_SYMBOLS, RISK_SYMBOLS, build_market_context
from providers.news_event_provider import build_news_events
from providers.stock_fundamental_provider import build_fundamental_snapshot
from providers.yahoo_provider import fetch_price_series
from stock_prediction_engine import build_stock_predictions


OUTPUTS_DIR = PROJECT_ROOT / "outputs"
PUBLIC_DIR = PROJECT_ROOT / "frontend" / "public"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the daily next-day stock radar pipeline.")
    parser.add_argument("--offline", action="store_true", help="Use deterministic fallback data for smoke tests.")
    parser.add_argument("--limit", type=int, default=0, help="Optional watchlist limit for local debugging.")
    args = parser.parse_args(argv)

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)

    watchlist = _read_json(PROJECT_ROOT / "config" / "watchlist.json")
    sector_map = _read_json(PROJECT_ROOT / "config" / "sector_map.json")
    benchmark_map = _read_json(PROJECT_ROOT / "config" / "benchmark_map.json")

    symbols = list(watchlist["symbols"])
    if args.limit:
        symbols = symbols[: args.limit]
    benchmark_symbols = sorted(set(CORE_MARKET_SYMBOLS + RISK_SYMBOLS + _benchmark_symbols(benchmark_map) + symbols))

    series_by_symbol = fetch_price_series(benchmark_symbols, offline=args.offline)
    market_context = build_market_context(series_by_symbol)
    finnhub_bundle = fetch_finnhub_bundle(symbols, offline=args.offline)
    fred_bundle = fetch_fred_bundle(offline=args.offline)
    news_events = build_news_events(symbols, finnhub_bundle)
    fundamentals = build_fundamental_snapshot(symbols, finnhub_bundle)
    prediction_payload = build_stock_predictions(
        symbols=symbols,
        sector_map=sector_map,
        benchmark_map=benchmark_map,
        series_by_symbol=series_by_symbol,
        news_events=news_events,
        fundamentals=fundamentals,
        market_context=market_context,
    )
    baseline = rank_candidates(prediction_payload, market_context, model_version=BASELINE_MODEL_VERSION)
    challenger = rank_candidates(prediction_payload, market_context, model_version=CHALLENGER_MODEL_VERSION)
    validation = update_forecast_ledger(
        baseline_ranking=baseline,
        challenger_ranking=challenger,
        market_context=market_context,
        series_by_symbol=series_by_symbol,
        records_path=OUTPUTS_DIR / "stock_forecast_records.csv",
    )
    records_payload = public_records(OUTPUTS_DIR / "stock_forecast_records.csv")
    leaderboard = build_model_leaderboard(records_payload["records"])

    provider_status = _provider_status(series_by_symbol, finnhub_bundle, fred_bundle)
    data_quality = _data_quality_report(market_context, provider_status, len(baseline["candidates"]))
    dashboard = _dashboard_payload(
        market_context=market_context,
        provider_status=provider_status,
        baseline=baseline,
        challenger=challenger,
        validation=validation,
        leaderboard=leaderboard,
        prediction_payload=prediction_payload,
        data_quality=data_quality,
    )
    top_candidates = {
        "version": "top_candidates_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model_version": baseline["model_version"],
        "candidates": _public_candidates(baseline["candidates"][:20]),
    }
    _write_json(PUBLIC_DIR / "stock-radar-dashboard.json", dashboard)
    _write_json(PUBLIC_DIR / "top-candidates.json", top_candidates)
    _write_json(PUBLIC_DIR / "stock-forecast-records.json", records_payload)
    _write_json(PUBLIC_DIR / "validation-scorecard.json", validation)
    _write_json(PUBLIC_DIR / "stock-model-leaderboard.json", leaderboard)
    _write_json(OUTPUTS_DIR / "stock_radar_dashboard.json", dashboard)
    _write_json(OUTPUTS_DIR / "validation_scorecard.json", validation)
    _write_json(OUTPUTS_DIR / "stock_model_leaderboard.json", leaderboard)
    _write_text(OUTPUTS_DIR / "daily_stock_radar_report.md", _render_daily_report(dashboard))
    _write_text(OUTPUTS_DIR / "candidate_validation_report.md", _render_validation_report(validation))
    _write_text(OUTPUTS_DIR / "data_quality_report.md", _render_data_quality_report(data_quality))
    _write_text(OUTPUTS_DIR / "stock_model_leaderboard.md", render_model_leaderboard_markdown(leaderboard))

    print(
        json.dumps(
            {
                "latest_data_date": market_context.get("latest_data_date"),
                "expected_latest_trading_date": market_context.get("expected_latest_trading_date"),
                "data_freshness_status": dashboard.get("data_freshness_status"),
                "candidate_count": len(baseline["candidates"]),
                "top_candidates": [candidate["ticker"] for candidate in baseline["candidates"][:10]],
                "validation_status": validation.get("validation_status"),
                "leaderboard_status": leaderboard.get("validation_status"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _dashboard_payload(
    *,
    market_context: dict[str, Any],
    provider_status: dict[str, Any],
    baseline: dict[str, Any],
    challenger: dict[str, Any],
    validation: dict[str, Any],
    leaderboard: dict[str, Any],
    prediction_payload: dict[str, Any],
    data_quality: dict[str, Any],
) -> dict[str, Any]:
    official = baseline["candidates"]
    actionable = [candidate for candidate in official if candidate["edge_status"] in {"STRONG_EDGE", "MODERATE_EDGE"}]
    strongest_type = actionable[0]["candidate_type"] if actionable else official[0]["candidate_type"] if official else "none"
    effective_freshness = _effective_data_freshness(market_context, provider_status)
    stale_warning = market_context.get("stale_warning") or effective_freshness != "fresh"
    high_elasticity_opportunity = bool(actionable) and market_context.get("market_state") != "defense" and effective_freshness in {"fresh", "partial_fallback"}
    return {
        "version": "stock_radar_dashboard_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "latest_data_date": market_context.get("latest_data_date"),
        "expected_latest_trading_date": market_context.get("expected_latest_trading_date"),
        "data_freshness_status": effective_freshness,
        "stale_warning": stale_warning,
        "provider_status": provider_status,
        "candidate_count": len(official),
        "top_candidate_count": len(actionable),
        "high_elasticity_opportunity": high_elasticity_opportunity,
        "radar_summary": _radar_summary(market_context, actionable, validation, effective_freshness),
        "market_context": market_context,
        "strongest_candidate_type": strongest_type,
        "current_risk_level": market_context.get("risk_level"),
        "model_validation_status": validation.get("validation_status"),
        "top_candidates": _public_candidates(official[:20]),
        "avoid_candidates": _public_candidates([candidate for candidate in official if candidate["rating"] == "C"][:12]),
        "excluded_candidates": _public_candidates(prediction_payload.get("excluded_candidates", [])[:20]),
        "sector_strength": prediction_payload.get("sector_strength", {}),
        "validation": validation,
        "model_leaderboard": leaderboard,
        "models": {
            "baseline": {"model_version": baseline["model_version"], "role": "official"},
            "challenger": {"model_version": challenger["model_version"], "role": "shadow_only"},
        },
        "data_quality": data_quality,
    }


def _public_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for candidate in candidates:
        rows.append(
            {
                "rank": candidate.get("rank"),
                "ticker": candidate.get("ticker"),
                "company_name": candidate.get("company_name"),
                "sector": candidate.get("sector"),
                "last_close": candidate.get("last_close"),
                "candidate_type": candidate.get("candidate_type"),
                "edge_status": candidate.get("edge_status"),
                "rating": candidate.get("rating"),
                "elasticity_score": candidate.get("elasticity_score"),
                "next_day_move_probability": candidate.get("next_day_move_probability"),
                "upside_momentum_score": candidate.get("upside_momentum_score"),
                "bounce_score": candidate.get("bounce_score"),
                "downside_continuation_score": candidate.get("downside_continuation_score"),
                "squeeze_score": candidate.get("squeeze_score"),
                "squeeze_data_status": candidate.get("squeeze_data_status"),
                "confluence_score": candidate.get("confluence_score"),
                "catalyst_score": candidate.get("catalyst_score"),
                "expectation_gap_score": candidate.get("expectation_gap_score"),
                "execution_quality_score": candidate.get("execution_quality_score"),
                "payoff_quality_score": candidate.get("payoff_quality_score"),
                "risk_reward_ratio": candidate.get("risk_reward_ratio"),
                "expected_upside_pct": candidate.get("expected_upside_pct"),
                "expected_downside_pct": candidate.get("expected_downside_pct"),
                "precision_gate": candidate.get("precision_gate"),
                "risk_score": candidate.get("risk_score"),
                "risk_flags": candidate.get("risk_flags"),
                "pool_filter": candidate.get("pool_filter"),
                "primary_scenario": candidate.get("primary_scenario"),
                "primary_probability": candidate.get("primary_probability"),
                "secondary_scenario": candidate.get("secondary_scenario"),
                "secondary_probability": candidate.get("secondary_probability"),
                "risk_scenario": candidate.get("risk_scenario"),
                "risk_probability": candidate.get("risk_probability"),
                "next_day_expected_range": candidate.get("next_day_expected_range"),
                "scenario_prices": candidate.get("scenario_prices"),
                "trigger_levels": candidate.get("trigger_levels"),
                "upside_trigger_level": candidate.get("upside_trigger_level"),
                "downside_risk_level": candidate.get("downside_risk_level"),
                "invalidation_level": candidate.get("invalidation_level"),
                "gap_fill_level": candidate.get("gap_fill_level"),
                "breakout_level": candidate.get("breakout_level"),
                "breakdown_level": candidate.get("breakdown_level"),
                "nearest_support": candidate.get("nearest_support"),
                "nearest_resistance": candidate.get("nearest_resistance"),
                "trigger_meaning": candidate.get("trigger_meaning"),
                "reason": candidate.get("reason"),
                "trade_plan": candidate.get("trade_plan"),
                "news": candidate.get("news"),
                "relative_strength": (candidate.get("features") or {}).get("relative_strength_5d"),
                "relative_volume": (candidate.get("features") or {}).get("relative_volume"),
                "dollar_volume_m": (candidate.get("features") or {}).get("dollar_volume_m"),
                "avg_dollar_volume_m": (candidate.get("features") or {}).get("avg_dollar_volume_m"),
                "atr_pct": (candidate.get("features") or {}).get("atr_pct"),
                "realized_volatility_20d": (candidate.get("features") or {}).get("realized_volatility_20d"),
                "volume_z_score": (candidate.get("features") or {}).get("volume_z_score"),
                "price_history": (candidate.get("features") or {}).get("price_history"),
                "historical_analog": candidate.get("historical_analog"),
                "historical_similar_samples": candidate.get("historical_similar_samples"),
                "supporting_evidence": candidate.get("supporting_evidence"),
                "conflicting_evidence": candidate.get("conflicting_evidence"),
                "missing_evidence": candidate.get("missing_evidence"),
                "validation_status": candidate.get("validation_status"),
                "not_trading_advice_note": candidate.get("not_trading_advice_note"),
            }
        )
    return rows


def _data_quality_report(market_context: dict[str, Any], provider_status: dict[str, Any], candidate_count: int) -> dict[str, Any]:
    effective_freshness = _effective_data_freshness(market_context, provider_status)
    score = 100
    if effective_freshness != "fresh":
        score -= 28
    if provider_status["yahoo"].get("fallback_count", 0) > 0:
        score -= min(35, provider_status["yahoo"]["fallback_count"] * 2)
    finnhub_status = provider_status["finnhub"]
    if not finnhub_status.get("available"):
        score -= 12
    elif finnhub_status.get("availability_status") == "partial":
        score -= 4
    if candidate_count < 10:
        score -= 10
    return {
        "version": "data_quality_report_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "score": max(0, score),
        "latest_data_date": market_context.get("latest_data_date"),
        "expected_latest_trading_date": market_context.get("expected_latest_trading_date"),
        "data_freshness_status": effective_freshness,
        "stale_warning": bool(market_context.get("stale_warning") or effective_freshness != "fresh"),
        "provider_status": provider_status,
        "candidate_count": candidate_count,
    }


def _provider_status(series_by_symbol: dict[str, Any], finnhub_bundle: dict[str, Any], fred_bundle: dict[str, Any]) -> dict[str, Any]:
    fallback_count = sum(1 for series in series_by_symbol.values() if not series.real_data)
    fallback_symbols = sorted(symbol for symbol, series in series_by_symbol.items() if not series.real_data)
    return {
        "yahoo": {
            "available": fallback_count < len(series_by_symbol),
            "total_symbols": len(series_by_symbol),
            "fallback_count": fallback_count,
            "fallback_symbols": fallback_symbols,
            "sources": sorted({series.source for series in series_by_symbol.values()}),
        },
        "finnhub": {
            "configured": bool(finnhub_bundle.get("configured")),
            "available": bool(finnhub_bundle.get("available")),
            "core_available": bool(finnhub_bundle.get("core_available")),
            "availability_status": finnhub_bundle.get("availability_status", "missing"),
            "source": finnhub_bundle.get("source"),
            "optional_data_status": finnhub_bundle.get("optional_data_status", {}),
            "error_count": len(finnhub_bundle.get("errors") or {}),
        },
        "fred": {
            "configured": bool(fred_bundle.get("configured")),
            "available": bool(fred_bundle.get("available")),
            "source": fred_bundle.get("source"),
            "error_count": len(fred_bundle.get("errors") or {}),
        },
    }


def _effective_data_freshness(market_context: dict[str, Any], provider_status: dict[str, Any]) -> str:
    yahoo = provider_status.get("yahoo") or {}
    total = int(yahoo.get("total_symbols") or 0)
    fallback_count = int(yahoo.get("fallback_count") or 0)
    if total and fallback_count >= total:
        return "fallback_only"
    if fallback_count:
        return "partial_fallback"
    return market_context.get("data_freshness_status") or "missing"


def _radar_summary(market_context: dict[str, Any], actionable: list[dict[str, Any]], validation: dict[str, Any], data_freshness_status: str) -> str:
    validation_status = _zh_validation_status(validation.get("validation_status"))
    if data_freshness_status in {"fallback_only", "missing"}:
        return "数据陈旧或不完整；本页只能当作观察面板，不能当作今日雷达。"
    if data_freshness_status == "partial_fallback":
        return f"部分标的行情缺失或降级，系统已剔除或压制；当前剩余 {len(actionable)} 只真实数据候选。验证状态：{validation_status}。"
    if market_context.get("market_state") == "defense":
        return "市场背景偏防守；即使有个股信号，也必须降低等级并等待触发确认。"
    if actionable:
        return f"{len(actionable)} 只候选通过市场、板块、催化、技术、成交、赔率和风险闸门；验证状态：{validation_status}。"
    return "今天没有高共振候选；少给比乱给更重要。"


def _zh_validation_status(value: Any) -> str:
    return {
        "not_yet_validated": "样本不足",
        "early_evidence": "早期证据",
        "validated": "已验证",
    }.get(str(value), str(value or "未知"))


def _benchmark_symbols(benchmark_map: dict[str, Any]) -> list[str]:
    symbols = set(benchmark_map.get("market_benchmarks", []))
    symbols.update(benchmark_map.get("risk_benchmarks", []))
    for values in (benchmark_map.get("sector_benchmarks") or {}).values():
        symbols.update(values)
    return list(symbols)


def _render_daily_report(dashboard: dict[str, Any]) -> str:
    lines = [
        "# 次日高弹性股票雷达日报",
        "",
        f"- generated_at: `{dashboard.get('generated_at')}`",
        f"- latest_data_date: `{dashboard.get('latest_data_date')}`",
        f"- expected_latest_trading_date: `{dashboard.get('expected_latest_trading_date')}`",
        f"- data_freshness_status: `{dashboard.get('data_freshness_status')}`",
        f"- market_state: `{(dashboard.get('market_context') or {}).get('market_state')}`",
        f"- high_elasticity_opportunity: `{dashboard.get('high_elasticity_opportunity')}`",
        f"- validation_status: `{dashboard.get('model_validation_status')}`",
        "",
        "## 候选榜",
        "",
        "| 排名 | 股票 | 等级 | 弹性 | 共振 | 触发价 | 失效价 | 原因 |",
        "| ---: | --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for candidate in dashboard.get("top_candidates", [])[:20]:
        lines.append(
            f"| {candidate.get('rank')} | {candidate.get('ticker')} | {candidate.get('rating')} | "
            f"{candidate.get('elasticity_score')} | {candidate.get('confluence_score')} | "
            f"{candidate.get('upside_trigger_level')} | {candidate.get('invalidation_level')} | {candidate.get('reason')} |"
        )
    lines.append("")
    return "\n".join(lines)


def _render_validation_report(validation: dict[str, Any]) -> str:
    baseline = validation.get("baseline") or {}
    return "\n".join(
        [
            "# 候选验证报告",
            "",
            f"- validation_status: `{validation.get('validation_status')}`",
            f"- pending_forecasts: `{validation.get('pending_forecasts')}`",
            f"- completed_next_day_forecasts: `{validation.get('completed_next_day_forecasts')}`",
            f"- top5_hit_rate: `{baseline.get('top5_hit_rate')}`",
            f"- avg_trigger_condition_return: `{baseline.get('avg_trigger_condition_return')}`",
            f"- avg_max_drawdown: `{baseline.get('avg_max_drawdown')}`",
            "",
        ]
    )


def _render_data_quality_report(data_quality: dict[str, Any]) -> str:
    lines = ["# 数据质量报告", ""]
    for key in ("score", "latest_data_date", "expected_latest_trading_date", "data_freshness_status", "stale_warning", "candidate_count"):
        lines.append(f"- {key}: `{data_quality.get(key)}`")
    lines.append("")
    lines.append("## 数据源状态")
    lines.append("")
    for name, status in (data_quality.get("provider_status") or {}).items():
        lines.append(f"- {name}: `{status}`")
    lines.append("")
    return "\n".join(lines)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
