from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from providers.yahoo_provider import PriceSeries


HORIZONS = [1, 3, 5]
BASELINE_MODEL_VERSION = "stock_radar_baseline_v1"
CSV_FIELDS = [
    "forecast_id",
    "forecast_date",
    "model_version",
    "model_role",
    "rank",
    "ticker",
    "company_name",
    "sector",
    "candidate_type",
    "edge_status",
    "rating",
    "elasticity_score",
    "next_day_move_probability",
    "upside_momentum_score",
    "bounce_score",
    "downside_continuation_score",
    "squeeze_score",
    "squeeze_data_status",
    "confluence_score",
    "catalyst_score",
    "expectation_gap_score",
    "execution_quality_score",
    "payoff_quality_score",
    "risk_reward_ratio",
    "precision_gate",
    "risk_score",
    "last_close",
    "primary_scenario",
    "primary_probability",
    "secondary_scenario",
    "secondary_probability",
    "risk_scenario",
    "risk_probability",
    "expected_range",
    "scenario_prices",
    "trigger_levels",
    "market_context",
    "supporting_evidence",
    "conflicting_evidence",
    "missing_evidence",
    "risk_flags",
    "reason",
    "status",
    "actual_next_day_return",
    "actual_3d_return",
    "actual_5d_return",
    "next_day_open",
    "next_day_high",
    "next_day_low",
    "next_day_close",
    "next_day_high_gain",
    "next_day_close_gain",
    "next_day_max_drawdown",
    "range_hit",
    "primary_hit",
    "entry_triggered",
    "stop_triggered",
    "target_hit",
    "open_condition_return",
    "trigger_condition_return",
    "executable_result",
]


def update_forecast_ledger(
    *,
    baseline_ranking: dict[str, Any],
    challenger_ranking: dict[str, Any],
    market_context: dict[str, Any],
    series_by_symbol: dict[str, PriceSeries],
    records_path: Path,
) -> dict[str, Any]:
    records_path.parent.mkdir(parents=True, exist_ok=True)
    rows = _read_rows(records_path)
    by_id = {row["forecast_id"]: row for row in rows if row.get("forecast_id")}

    for row in list(by_id.values()):
        _backfill_row(row, series_by_symbol)

    for ranking in (baseline_ranking, challenger_ranking):
        for candidate in ranking.get("candidates", [])[:20]:
            row = _forecast_row(candidate, ranking, market_context)
            by_id.setdefault(row["forecast_id"], row)

    merged = list(by_id.values())
    merged.sort(key=lambda row: (row.get("forecast_date", ""), row.get("model_version", ""), int(row.get("rank") or 999), row.get("ticker", "")))
    _write_rows(records_path, merged)
    return build_validation_scorecard(merged)


def build_validation_scorecard(rows: list[dict[str, Any]]) -> dict[str, Any]:
    baseline = [row for row in rows if row.get("model_version") == BASELINE_MODEL_VERSION]
    challenger = [row for row in rows if row.get("model_role") == "challenger"]
    baseline_metrics = _metrics(baseline)
    challenger_metrics = _metrics(challenger)
    completed = baseline_metrics["completed_next_day_forecasts"]
    if completed >= 60 and baseline_metrics["high_confluence_beats_low_confluence"]:
        validation_status = "validated"
    elif completed >= 20:
        validation_status = "early_evidence"
    else:
        validation_status = "not_yet_validated"
    return {
        "version": "validation_scorecard_v2",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "validation_status": validation_status,
        "not_high_precision_warning": "Do not call this high precision until forward validation proves it.",
        "pending_forecasts": sum(1 for row in baseline if row.get("status") != "completed"),
        "completed_next_day_forecasts": completed,
        "baseline": baseline_metrics,
        "challenger": challenger_metrics,
        "baseline_vs_challenger": _compare(baseline_metrics, challenger_metrics),
        "by_market_state": _bucket_metrics(baseline, "market_context_market_state"),
        "by_sector": _bucket_metrics(baseline, "sector"),
        "by_candidate_type": _bucket_metrics(baseline, "candidate_type"),
        "by_edge_status": _bucket_metrics(baseline, "edge_status"),
        "guardrails": [
            "This is a forecast ledger, not a trading or PnL ledger.",
            "High gain alone is not enough; trigger-condition return and drawdown are tracked separately.",
            "Forecast fields are immutable; outcome backfill only updates realized fields.",
            "Challenger must remain shadow until future samples prove improvement.",
        ],
    }


def build_model_leaderboard(rows: list[dict[str, Any]]) -> dict[str, Any]:
    versions = sorted({row.get("model_version") for row in rows if row.get("model_version")})
    models = []
    for version in versions:
        model_rows = [row for row in rows if row.get("model_version") == version]
        metrics = _metrics(model_rows)
        role = "baseline" if version == BASELINE_MODEL_VERSION else "challenger"
        models.append(
            {
                "model_version": version,
                "role": role,
                "status": "active" if role == "baseline" else "shadow",
                "metrics": metrics,
                "promotion_status": _promotion_status(role, metrics),
            }
        )
    return {
        "version": "stock_model_leaderboard_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "active_baseline": BASELINE_MODEL_VERSION,
        "validation_status": "not_yet_validated" if not models else _overall_validation_status(models),
        "models": models,
        "comparison_metrics": [
            "top_10_avg_next_day_volatility",
            "top_10_next_day_direction_hit_rate",
            "range_hit_rate",
            "primary_scenario_hit_rate",
            "high_confluence_beats_low_confluence",
            "catalyst_candidates_beat_no_catalyst",
            "high_risk_candidates_more_volatile",
        ],
        "guardrails": [
            "No model can be promoted without forward validation.",
            "not_yet_validated must remain visible when sample size is insufficient.",
        ],
    }


def render_model_leaderboard_markdown(leaderboard: dict[str, Any]) -> str:
    lines = [
        "# Stock Model Leaderboard",
        "",
        f"- active_baseline: `{leaderboard.get('active_baseline')}`",
        f"- validation_status: `{leaderboard.get('validation_status')}`",
        "",
        "| Model | Role | Status | Completed | Top10 Volatility | Direction Hit | Range Hit | Primary Hit | Promotion |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for model in leaderboard.get("models", []):
        metrics = model.get("metrics") or {}
        lines.append(
            f"| {model.get('model_version')} | {model.get('role')} | {model.get('status')} | "
            f"{metrics.get('completed_next_day_forecasts')} | {metrics.get('top_10_avg_next_day_volatility')} | "
            f"{metrics.get('top_10_next_day_direction_hit_rate')} | {metrics.get('range_hit_rate')} | "
            f"{metrics.get('primary_scenario_hit_rate')} | {model.get('promotion_status')} |"
        )
    lines.append("")
    return "\n".join(lines)


def public_records(records_path: Path, limit: int = 500) -> dict[str, Any]:
    rows = _read_rows(records_path)
    return {
        "version": "stock_forecast_records_public_v2",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "records": rows[-limit:],
        "summary": {
            "total_records": len(rows),
            "pending": sum(1 for row in rows if row.get("status") != "completed"),
            "completed": sum(1 for row in rows if row.get("status") == "completed"),
        },
        "not_trading_note": "This is a forecast ledger, not a trading record or PnL ledger.",
    }


def _forecast_row(candidate: dict[str, Any], ranking: dict[str, Any], market_context: dict[str, Any]) -> dict[str, str]:
    forecast_date = market_context.get("latest_data_date") or datetime.now(timezone.utc).date().isoformat()
    model_version = ranking["model_version"]
    ticker = candidate["ticker"]
    forecast_id = _forecast_id(forecast_date, model_version, ticker)
    row = {field: "" for field in CSV_FIELDS}
    row.update(
        {
            "forecast_id": forecast_id,
            "forecast_date": forecast_date,
            "model_version": model_version,
            "model_role": ranking["model_role"],
            "rank": str(candidate.get("rank")),
            "ticker": ticker,
            "company_name": candidate.get("company_name", ""),
            "sector": candidate.get("sector", ""),
            "candidate_type": candidate.get("candidate_type", ""),
            "edge_status": candidate.get("edge_status", ""),
            "rating": candidate.get("rating", ""),
            "elasticity_score": _fmt(candidate.get("elasticity_score")),
            "next_day_move_probability": _fmt(candidate.get("next_day_move_probability")),
            "upside_momentum_score": _fmt(candidate.get("upside_momentum_score")),
            "bounce_score": _fmt(candidate.get("bounce_score")),
            "downside_continuation_score": _fmt(candidate.get("downside_continuation_score")),
            "squeeze_score": _fmt(candidate.get("squeeze_score")),
            "squeeze_data_status": _json(candidate.get("squeeze_data_status")),
            "confluence_score": _fmt(candidate.get("confluence_score")),
            "catalyst_score": _fmt(candidate.get("catalyst_score")),
            "expectation_gap_score": _fmt(candidate.get("expectation_gap_score")),
            "execution_quality_score": _fmt(candidate.get("execution_quality_score")),
            "payoff_quality_score": _fmt(candidate.get("payoff_quality_score")),
            "risk_reward_ratio": _fmt(candidate.get("risk_reward_ratio")),
            "precision_gate": _json(candidate.get("precision_gate")),
            "risk_score": _fmt(candidate.get("risk_score")),
            "last_close": _fmt(candidate.get("last_close")),
            "primary_scenario": candidate.get("primary_scenario", ""),
            "primary_probability": _fmt(candidate.get("primary_probability")),
            "secondary_scenario": candidate.get("secondary_scenario", ""),
            "secondary_probability": _fmt(candidate.get("secondary_probability")),
            "risk_scenario": candidate.get("risk_scenario", ""),
            "risk_probability": _fmt(candidate.get("risk_probability")),
            "expected_range": _json(candidate.get("next_day_expected_range")),
            "scenario_prices": _json(candidate.get("scenario_prices")),
            "trigger_levels": _json(candidate.get("trigger_levels")),
            "market_context": _json(
                {
                    "market_state": market_context.get("market_state"),
                    "market_score": market_context.get("market_score"),
                    "risk_level": market_context.get("risk_level"),
                    "data_freshness_status": market_context.get("data_freshness_status"),
                }
            ),
            "supporting_evidence": _json(candidate.get("supporting_evidence")),
            "conflicting_evidence": _json(candidate.get("conflicting_evidence")),
            "missing_evidence": _json(candidate.get("missing_evidence")),
            "risk_flags": _json(candidate.get("risk_flags")),
            "reason": candidate.get("reason", ""),
            "status": "pending",
        }
    )
    return row


def _backfill_row(row: dict[str, Any], series_by_symbol: dict[str, PriceSeries]) -> None:
    ticker = row.get("ticker")
    series = series_by_symbol.get(ticker)
    if not series or not series.rows:
        return
    rows = series.rows
    index = next((idx for idx, item in enumerate(rows) if item["date"] == row.get("forecast_date")), None)
    if index is None:
        return
    base_close = _float(row.get("last_close"))
    if not base_close:
        return
    levels = _loads(row.get("trigger_levels"))
    expected = _loads(row.get("expected_range"))
    trigger = _float(levels.get("upside_trigger_level")) or base_close * 1.02
    invalidation = _float(levels.get("invalidation_level")) or base_close * 0.96
    expected_low = _float(expected.get("expected_low")) or base_close * 0.95
    expected_high = _float(expected.get("expected_high")) or base_close * 1.05
    primary_scenario = row.get("primary_scenario") or ""

    if index + 1 < len(rows):
        next_row = rows[index + 1]
        next_day_return = next_row["close"] / base_close - 1
        entry_triggered = next_row["high"] >= trigger
        stop_triggered = next_row["low"] <= invalidation
        range_hit = next_row["low"] <= expected_high and next_row["high"] >= expected_low
        primary_hit = _primary_hit(primary_scenario, next_row, base_close, trigger, invalidation)
        target_hit = entry_triggered and next_row["high"] >= expected_high
        row.update(
            {
                "actual_next_day_return": _fmt(next_day_return),
                "next_day_open": _fmt(next_row["open"]),
                "next_day_high": _fmt(next_row["high"]),
                "next_day_low": _fmt(next_row["low"]),
                "next_day_close": _fmt(next_row["close"]),
                "next_day_high_gain": _fmt(next_row["high"] / base_close - 1),
                "next_day_close_gain": _fmt(next_day_return),
                "next_day_max_drawdown": _fmt(next_row["low"] / (trigger if entry_triggered else next_row["open"]) - 1),
                "range_hit": str(range_hit).lower(),
                "primary_hit": str(primary_hit).lower(),
                "entry_triggered": str(entry_triggered).lower(),
                "stop_triggered": str(stop_triggered).lower(),
                "target_hit": str(target_hit).lower(),
                "open_condition_return": _fmt(next_row["close"] / next_row["open"] - 1),
                "trigger_condition_return": _fmt(next_row["close"] / trigger - 1) if entry_triggered else "",
                "executable_result": "target_hit" if target_hit else "stopped" if stop_triggered else "triggered_no_target" if entry_triggered else "not_triggered",
                "status": "completed",
            }
        )
    if index + 3 < len(rows):
        row["actual_3d_return"] = _fmt(rows[index + 3]["close"] / base_close - 1)
    if index + 5 < len(rows):
        row["actual_5d_return"] = _fmt(rows[index + 5]["close"] / base_close - 1)


def _metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    completed = [row for row in rows if row.get("status") == "completed"]
    top10 = [row for row in completed if int(row.get("rank") or 999) <= 10]
    high_confluence = [row for row in completed if (_float(row.get("confluence_score")) or 0) >= 72]
    low_confluence = [row for row in completed if (_float(row.get("confluence_score")) or 0) < 72]
    catalyst = [row for row in completed if (_float(row.get("catalyst_score")) or 0) >= 60]
    no_catalyst = [row for row in completed if (_float(row.get("catalyst_score")) or 0) < 60]
    high_expectation_gap = [row for row in completed if (_float(row.get("expectation_gap_score")) or 0) >= 58]
    low_expectation_gap = [row for row in completed if (_float(row.get("expectation_gap_score")) or 0) < 58]
    high_payoff_quality = [row for row in completed if (_float(row.get("payoff_quality_score")) or 0) >= 52]
    low_payoff_quality = [row for row in completed if (_float(row.get("payoff_quality_score")) or 0) < 52]
    high_risk = [row for row in completed if (_float(row.get("risk_score")) or 0) >= 55]
    lower_risk = [row for row in completed if (_float(row.get("risk_score")) or 0) < 55]
    all_trigger_returns = [_float(row.get("trigger_condition_return")) for row in completed if _float(row.get("trigger_condition_return")) is not None]
    wins = [value for value in all_trigger_returns if value and value > 0]
    losses = [value for value in all_trigger_returns if value and value < 0]
    return {
        "total_forecasts": len(rows),
        "pending_forecasts": sum(1 for row in rows if row.get("status") != "completed"),
        "completed_next_day_forecasts": len(completed),
        "top_10_avg_next_day_volatility": _avg_next_day_volatility(top10),
        "top_10_next_day_direction_hit_rate": _direction_hit_rate(top10),
        "top5_hit_rate": _hit_rate([row for row in completed if int(row.get("rank") or 999) <= 5]),
        "top10_hit_rate": _hit_rate(top10),
        "range_hit_rate": _bool_rate(completed, "range_hit"),
        "primary_scenario_hit_rate": _bool_rate(completed, "primary_hit"),
        "avg_next_day_high_gain": _avg_float(completed, "next_day_high_gain"),
        "avg_next_day_close_gain": _avg_float(completed, "next_day_close_gain"),
        "avg_max_drawdown": _avg_float(completed, "next_day_max_drawdown"),
        "avg_open_condition_return": _avg_float(completed, "open_condition_return"),
        "avg_trigger_condition_return": _avg_values(all_trigger_returns),
        "profit_factor": abs(sum(wins) / sum(losses)) if losses else None,
        "high_confluence_avg_next_day_return": _avg_float(high_confluence, "actual_next_day_return"),
        "low_confluence_avg_next_day_return": _avg_float(low_confluence, "actual_next_day_return"),
        "high_confluence_beats_low_confluence": _none_safe(_avg_float(high_confluence, "actual_next_day_return")) > _none_safe(_avg_float(low_confluence, "actual_next_day_return")),
        "catalyst_candidates_avg_return": _avg_float(catalyst, "actual_next_day_return"),
        "no_catalyst_avg_return": _avg_float(no_catalyst, "actual_next_day_return"),
        "catalyst_candidates_beat_no_catalyst": _none_safe(_avg_float(catalyst, "actual_next_day_return")) > _none_safe(_avg_float(no_catalyst, "actual_next_day_return")),
        "high_expectation_gap_avg_return": _avg_float(high_expectation_gap, "actual_next_day_return"),
        "low_expectation_gap_avg_return": _avg_float(low_expectation_gap, "actual_next_day_return"),
        "high_expectation_gap_beats_low": _none_safe(_avg_float(high_expectation_gap, "actual_next_day_return")) > _none_safe(_avg_float(low_expectation_gap, "actual_next_day_return")),
        "high_payoff_quality_avg_return": _avg_float(high_payoff_quality, "actual_next_day_return"),
        "low_payoff_quality_avg_return": _avg_float(low_payoff_quality, "actual_next_day_return"),
        "high_payoff_quality_beats_low": _none_safe(_avg_float(high_payoff_quality, "actual_next_day_return")) > _none_safe(_avg_float(low_payoff_quality, "actual_next_day_return")),
        "high_risk_avg_volatility": _avg_next_day_volatility(high_risk),
        "lower_risk_avg_volatility": _avg_next_day_volatility(lower_risk),
        "high_risk_candidates_more_volatile": _none_safe(_avg_next_day_volatility(high_risk)) > _none_safe(_avg_next_day_volatility(lower_risk)),
    }


def _bucket_metrics(rows: list[dict[str, Any]], field: str) -> dict[str, Any]:
    if field == "market_context_market_state":
        bucket_value = lambda row: (_loads(row.get("market_context")).get("market_state") or "unknown")
    else:
        bucket_value = lambda row: row.get(field) or "unknown"
    buckets = sorted({bucket_value(row) for row in rows})
    return {bucket: _metrics([row for row in rows if bucket_value(row) == bucket]) for bucket in buckets[:30]}


def _compare(baseline: dict[str, Any], challenger: dict[str, Any]) -> dict[str, Any]:
    return {
        "challenger_shadow_only": True,
        "completed_sample_gap": (challenger.get("completed_next_day_forecasts") or 0) - (baseline.get("completed_next_day_forecasts") or 0),
        "trigger_return_delta": _none_safe(challenger.get("avg_trigger_condition_return")) - _none_safe(baseline.get("avg_trigger_condition_return")),
        "top5_hit_rate_delta": _none_safe(challenger.get("top5_hit_rate")) - _none_safe(baseline.get("top5_hit_rate")),
        "range_hit_rate_delta": _none_safe(challenger.get("range_hit_rate")) - _none_safe(baseline.get("range_hit_rate")),
        "primary_scenario_hit_rate_delta": _none_safe(challenger.get("primary_scenario_hit_rate")) - _none_safe(baseline.get("primary_scenario_hit_rate")),
        "promotion_status": "not_yet_validated",
    }


def _promotion_status(role: str, metrics: dict[str, Any]) -> str:
    if role == "baseline":
        return "active_baseline"
    if (metrics.get("completed_next_day_forecasts") or 0) < 30:
        return "sample_insufficient"
    return "shadow_observation_required"


def _overall_validation_status(models: list[dict[str, Any]]) -> str:
    baseline = next((model for model in models if model["role"] == "baseline"), None)
    completed = ((baseline or {}).get("metrics") or {}).get("completed_next_day_forecasts") or 0
    if completed >= 60:
        return "validated"
    if completed >= 20:
        return "early_evidence"
    return "not_yet_validated"


def _read_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return [{field: row.get(field, "") for field in CSV_FIELDS} for row in rows]


def _write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in CSV_FIELDS})


def _forecast_id(date_value: str, model_version: str, ticker: str) -> str:
    digest = hashlib.sha1(f"{date_value}|{model_version}|{ticker}".encode("utf-8")).hexdigest()[:12]
    return f"{date_value}-{model_version}-{ticker}-{digest}"


def _primary_hit(primary_scenario: str, row: dict[str, Any], base_close: float, trigger: float, invalidation: float) -> bool:
    if primary_scenario in {"upside_path_after_trigger", "bounce_attempt_after_trigger", "only_if_market_reclaims_risk_on"}:
        return row["high"] >= trigger and row["close"] >= base_close
    if primary_scenario == "risk_path_continuation":
        return row["low"] <= invalidation and row["close"] < base_close
    return False


def _hit_rate(rows: list[dict[str, Any]]) -> float | None:
    if not rows:
        return None
    hits = sum(1 for row in rows if row.get("target_hit") == "true" or row.get("primary_hit") == "true")
    return round(hits / len(rows), 6)


def _bool_rate(rows: list[dict[str, Any]], field: str) -> float | None:
    if not rows:
        return None
    return round(sum(1 for row in rows if row.get(field) == "true") / len(rows), 6)


def _direction_hit_rate(rows: list[dict[str, Any]]) -> float | None:
    if not rows:
        return None
    hits = 0
    for row in rows:
        primary = row.get("primary_scenario", "")
        ret = _float(row.get("actual_next_day_return")) or 0
        if primary == "risk_path_continuation":
            hits += ret < 0
        elif primary != "no_edge":
            hits += ret > 0
    return round(hits / len(rows), 6)


def _avg_next_day_volatility(rows: list[dict[str, Any]]) -> float | None:
    values = []
    for row in rows:
        high_gain = _float(row.get("next_day_high_gain"))
        drawdown = _float(row.get("next_day_max_drawdown"))
        if high_gain is not None and drawdown is not None:
            values.append(abs(high_gain) + abs(drawdown))
    return _avg_values(values)


def _avg_float(rows: list[dict[str, Any]], field: str) -> float | None:
    return _avg_values([_float(row.get(field)) for row in rows])


def _avg_values(values: list[float | None]) -> float | None:
    clean = [value for value in values if value is not None]
    return round(sum(clean) / len(clean), 6) if clean else None


def _float(value: Any) -> float | None:
    try:
        if value in ("", None):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _fmt(value: Any) -> str:
    numeric = _float(value)
    return "" if numeric is None else f"{numeric:.6f}"


def _none_safe(value: Any) -> float:
    numeric = _float(value)
    return numeric if numeric is not None else 0.0


def _json(value: Any) -> str:
    return json.dumps(value or {}, ensure_ascii=False, separators=(",", ":"))


def _loads(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    try:
        return json.loads(value or "{}")
    except (TypeError, json.JSONDecodeError):
        return {}
