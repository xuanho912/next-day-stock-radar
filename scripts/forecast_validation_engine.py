from __future__ import annotations

import csv
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from providers.yahoo_provider import PriceSeries


HORIZONS = [1, 3, 5]
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
    "rating",
    "elasticity_score",
    "confluence_score",
    "catalyst_score",
    "risk_score",
    "last_close",
    "primary_scenario",
    "secondary_scenario",
    "risk_scenario",
    "next_day_expected_range",
    "upside_trigger_level",
    "invalidation_level",
    "reason",
    "market_state",
    "data_freshness_status",
    "status",
    "next_day_open",
    "next_day_high",
    "next_day_low",
    "next_day_close",
    "next_day_high_gain",
    "next_day_close_gain",
    "next_day_max_drawdown",
    "entry_triggered",
    "stop_triggered",
    "target_hit",
    "open_buy_return",
    "trigger_buy_return",
    "return_3d",
    "return_5d",
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
    baseline = [row for row in rows if row.get("model_role") == "baseline"]
    challenger = [row for row in rows if row.get("model_role") == "challenger"]
    baseline_metrics = _metrics(baseline)
    challenger_metrics = _metrics(challenger)
    completed = baseline_metrics["completed_next_day_forecasts"]
    if completed >= 60 and baseline_metrics["high_confluence_beats_all"]:
        validation_status = "validated"
    elif completed >= 20:
        validation_status = "early_evidence"
    else:
        validation_status = "not_yet_validated"
    return {
        "version": "validation_scorecard_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "validation_status": validation_status,
        "pending_forecasts": sum(1 for row in baseline if row.get("status") != "completed"),
        "completed_next_day_forecasts": completed,
        "baseline": baseline_metrics,
        "challenger": challenger_metrics,
        "baseline_vs_challenger": _compare(baseline_metrics, challenger_metrics),
        "by_market_state": _bucket_metrics(baseline, "market_state"),
        "by_sector": _bucket_metrics(baseline, "sector"),
        "by_candidate_type": _bucket_metrics(baseline, "candidate_type"),
        "guardrails": [
            "High gain alone is not enough; trigger-buy and drawdown are tracked separately.",
            "Forecast fields are immutable; outcome backfill only updates realized fields.",
            "Challenger must remain shadow until future samples prove improvement.",
        ],
    }


def public_records(records_path: Path, limit: int = 500) -> dict[str, Any]:
    rows = _read_rows(records_path)
    return {
        "version": "stock_forecast_records_public_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "records": rows[-limit:],
        "summary": {
            "total_records": len(rows),
            "pending": sum(1 for row in rows if row.get("status") != "completed"),
            "completed": sum(1 for row in rows if row.get("status") == "completed"),
        },
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
            "rating": candidate.get("rating", ""),
            "elasticity_score": _fmt(candidate.get("elasticity_score")),
            "confluence_score": _fmt(candidate.get("confluence_score")),
            "catalyst_score": _fmt(candidate.get("catalyst_score")),
            "risk_score": _fmt(candidate.get("risk_score")),
            "last_close": _fmt(candidate.get("last_close")),
            "primary_scenario": candidate.get("primary_scenario", ""),
            "secondary_scenario": candidate.get("secondary_scenario", ""),
            "risk_scenario": candidate.get("risk_scenario", ""),
            "next_day_expected_range": (candidate.get("next_day_expected_range") or {}).get("label", ""),
            "upside_trigger_level": _fmt(candidate.get("upside_trigger_level")),
            "invalidation_level": _fmt(candidate.get("invalidation_level")),
            "reason": candidate.get("reason", ""),
            "market_state": market_context.get("market_state", ""),
            "data_freshness_status": market_context.get("data_freshness_status", ""),
            "status": "pending",
        }
    )
    return row


def _backfill_row(row: dict[str, Any], series_by_symbol: dict[str, PriceSeries]) -> None:
    if row.get("status") == "completed" and row.get("return_5d"):
        return
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
    if index + 1 < len(rows):
        next_row = rows[index + 1]
        trigger = _float(row.get("upside_trigger_level")) or base_close * 1.02
        invalidation = _float(row.get("invalidation_level")) or base_close * 0.96
        target_low = _target_low(row.get("next_day_expected_range"))
        entry_triggered = next_row["high"] >= trigger
        stop_triggered = next_row["low"] <= invalidation
        target_hit = entry_triggered and ((next_row["high"] / trigger - 1) >= target_low)
        row.update(
            {
                "next_day_open": _fmt(next_row["open"]),
                "next_day_high": _fmt(next_row["high"]),
                "next_day_low": _fmt(next_row["low"]),
                "next_day_close": _fmt(next_row["close"]),
                "next_day_high_gain": _fmt(next_row["high"] / base_close - 1),
                "next_day_close_gain": _fmt(next_row["close"] / base_close - 1),
                "next_day_max_drawdown": _fmt(next_row["low"] / (trigger if entry_triggered else next_row["open"]) - 1),
                "entry_triggered": str(entry_triggered).lower(),
                "stop_triggered": str(stop_triggered).lower(),
                "target_hit": str(target_hit).lower(),
                "open_buy_return": _fmt(next_row["close"] / next_row["open"] - 1),
                "trigger_buy_return": _fmt(next_row["close"] / trigger - 1) if entry_triggered else "",
                "executable_result": "target_hit" if target_hit else "stopped" if stop_triggered else "triggered_no_target" if entry_triggered else "not_triggered",
                "status": "completed",
            }
        )
    if index + 3 < len(rows):
        row["return_3d"] = _fmt(rows[index + 3]["close"] / base_close - 1)
    if index + 5 < len(rows):
        row["return_5d"] = _fmt(rows[index + 5]["close"] / base_close - 1)


def _metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    completed = [row for row in rows if row.get("status") == "completed"]
    top5 = [row for row in completed if int(row.get("rank") or 999) <= 5]
    top10 = [row for row in completed if int(row.get("rank") or 999) <= 10]
    high_confluence = [row for row in completed if (_float(row.get("confluence_score")) or 0) >= 72]
    all_trigger_returns = [_float(row.get("trigger_buy_return")) for row in completed if _float(row.get("trigger_buy_return")) is not None]
    high_conf_trigger = [_float(row.get("trigger_buy_return")) for row in high_confluence if _float(row.get("trigger_buy_return")) is not None]
    wins = [value for value in all_trigger_returns if value and value > 0]
    losses = [value for value in all_trigger_returns if value and value < 0]
    return {
        "total_forecasts": len(rows),
        "pending_forecasts": sum(1 for row in rows if row.get("status") != "completed"),
        "completed_next_day_forecasts": len(completed),
        "top5_hit_rate": _hit_rate(top5),
        "top10_hit_rate": _hit_rate(top10),
        "avg_next_day_high_gain": _avg_float(completed, "next_day_high_gain"),
        "avg_next_day_close_gain": _avg_float(completed, "next_day_close_gain"),
        "avg_max_drawdown": _avg_float(completed, "next_day_max_drawdown"),
        "avg_open_buy_return": _avg_float(completed, "open_buy_return"),
        "avg_trigger_buy_return": _avg_values(all_trigger_returns),
        "profit_factor": abs(sum(wins) / sum(losses)) if losses else None,
        "high_confluence_avg_trigger_return": _avg_values(high_conf_trigger),
        "high_confluence_beats_all": (_avg_values(high_conf_trigger) or -999) > (_avg_values(all_trigger_returns) or 999),
    }


def _bucket_metrics(rows: list[dict[str, Any]], field: str) -> dict[str, Any]:
    buckets = sorted({row.get(field) or "unknown" for row in rows})
    return {bucket: _metrics([row for row in rows if (row.get(field) or "unknown") == bucket]) for bucket in buckets[:20]}


def _compare(baseline: dict[str, Any], challenger: dict[str, Any]) -> dict[str, Any]:
    return {
        "challenger_shadow_only": True,
        "completed_sample_gap": (challenger.get("completed_next_day_forecasts") or 0) - (baseline.get("completed_next_day_forecasts") or 0),
        "trigger_return_delta": _none_safe(challenger.get("avg_trigger_buy_return")) - _none_safe(baseline.get("avg_trigger_buy_return")),
        "top5_hit_rate_delta": _none_safe(challenger.get("top5_hit_rate")) - _none_safe(baseline.get("top5_hit_rate")),
        "promotion_status": "sample_insufficient_or_not_proven",
    }


def _read_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in CSV_FIELDS})


def _forecast_id(date_value: str, model_version: str, ticker: str) -> str:
    digest = hashlib.sha1(f"{date_value}|{model_version}|{ticker}".encode("utf-8")).hexdigest()[:12]
    return f"{date_value}-{model_version}-{ticker}-{digest}"


def _hit_rate(rows: list[dict[str, Any]]) -> float | None:
    if not rows:
        return None
    hits = sum(1 for row in rows if row.get("target_hit") == "true")
    return round(hits / len(rows), 6)


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


def _target_low(label: str | None) -> float:
    if not label:
        return 0.04
    return 0.05
