from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

from providers.yahoo_provider import PriceSeries


def build_stock_predictions(
    *,
    symbols: list[str],
    sector_map: dict[str, Any],
    benchmark_map: dict[str, Any],
    series_by_symbol: dict[str, PriceSeries],
    news_events: dict[str, Any],
    fundamentals: dict[str, Any],
    market_context: dict[str, Any],
) -> dict[str, Any]:
    candidates = []
    sector_strength = _build_sector_strength(sector_map, benchmark_map, series_by_symbol)
    for symbol in symbols:
        stock = sector_map.get(symbol, {})
        features = _stock_features(symbol, series_by_symbol.get(symbol), stock, benchmark_map, series_by_symbol)
        news = (news_events.get("symbols") or {}).get(symbol, {})
        fundamental = (fundamentals.get("symbols") or {}).get(symbol, {})
        candidate = _build_candidate(symbol, stock, features, news, fundamental, sector_strength, market_context)
        candidates.append(candidate)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sector_strength": sector_strength,
        "candidates": candidates,
    }


def _build_candidate(
    symbol: str,
    stock: dict[str, Any],
    features: dict[str, Any],
    news: dict[str, Any],
    fundamental: dict[str, Any],
    sector_strength: dict[str, Any],
    market_context: dict[str, Any],
) -> dict[str, Any]:
    sector = stock.get("sector") or "Unknown"
    sector_payload = sector_strength.get(sector, {"score": 40, "level": "weak"})
    support: list[dict[str, Any]] = []
    conflict: list[dict[str, Any]] = []

    if news.get("catalyst_score", 0) >= 60:
        support.append(_ev("catalyst", news.get("catalyst_type"), news.get("catalyst_score"), news.get("primary_headline")))
    else:
        conflict.append(_ev("catalyst", "weak_or_missing_catalyst", 100 - news.get("catalyst_score", 35), "No strong confirmed recent catalyst."))

    if features["technical_score"] >= 64:
        support.append(_ev("technical", "price_structure_confirmed", features["technical_score"], "Breakout/reclaim/high-close structure is constructive."))
    else:
        conflict.append(_ev("technical", "price_structure_unconfirmed", 100 - features["technical_score"], "Price structure has not confirmed a high-quality setup."))

    if features["volume_score"] >= 62:
        support.append(_ev("volume", "relative_volume_confirmed", features["volume_score"], "Relative volume and dollar liquidity are sufficient."))
    else:
        conflict.append(_ev("volume", "volume_or_liquidity_weak", 100 - features["volume_score"], "Volume confirmation or liquidity is weak."))

    if sector_payload["score"] >= 62:
        support.append(_ev("sector", "sector_theme_confirmed", sector_payload["score"], f"{sector} is showing relative strength."))
    else:
        conflict.append(_ev("sector", "sector_theme_weak", 100 - sector_payload["score"], f"{sector} is not a confirmed capital-flow theme."))

    risk_score = _risk_score(features, news, market_context)
    if risk_score >= 55:
        conflict.append(_ev("risk", "risk_penalty_high", risk_score, "Gap, liquidity, stale data, or event risk is elevated."))

    candidate_type = _candidate_type(stock, features, news, risk_score)
    primary = _primary_scenario(market_context, candidate_type, features)
    secondary = "open_drive_then_pullback" if features["gap_pct"] > 0.035 else "range_extension_after_trigger"
    risk = "failed_breakout_or_gap_fade"

    last_close = features["last_close"]
    atr_pct = features["atr_pct"] or 0.055
    upside_trigger = features["recent_resistance"] or last_close * 1.025
    invalidation = min(features["vwap_proxy"], features["recent_support"] or last_close * 0.96)
    expected_low = max(-0.045, -atr_pct * 0.65)
    expected_high = min(0.22, atr_pct * (1.5 if candidate_type != "avoid_low_liquidity" else 0.8))

    return {
        "ticker": symbol,
        "company_name": fundamental.get("company_name") or stock.get("company_name") or symbol,
        "sector": sector,
        "candidate_type": candidate_type,
        "last_close": round(last_close, 4),
        "features": features,
        "news": news,
        "fundamental": fundamental,
        "sector_theme": sector_payload,
        "risk_score": round(risk_score, 2),
        "primary_scenario": primary,
        "secondary_scenario": secondary,
        "risk_scenario": risk,
        "next_day_expected_range": {
            "low_pct": round(expected_low, 4),
            "high_pct": round(expected_high, 4),
            "label": f"{expected_low * 100:.1f}% to +{expected_high * 100:.1f}%",
        },
        "upside_trigger_level": round(upside_trigger, 4),
        "invalidation_level": round(invalidation, 4),
        "gap_fill_level": round(features["gap_fill_level"], 4),
        "recent_support": round(features["recent_support"], 4),
        "recent_resistance": round(features["recent_resistance"], 4),
        "supporting_evidence": support,
        "conflicting_evidence": conflict,
        "historical_similar_samples": _historical_similar_samples(features),
    }


def _stock_features(
    symbol: str,
    series: PriceSeries | None,
    stock: dict[str, Any],
    benchmark_map: dict[str, Any],
    series_by_symbol: dict[str, PriceSeries],
) -> dict[str, Any]:
    rows = series.rows if series else []
    if len(rows) < 60:
        rows = []
    closes = [row["close"] for row in rows]
    highs = [row["high"] for row in rows]
    lows = [row["low"] for row in rows]
    volumes = [row["volume"] for row in rows]
    last = closes[-1] if closes else 0.0
    previous = closes[-2] if len(closes) >= 2 else last
    recent_high_20 = max(highs[-21:-1]) if len(highs) >= 21 else last * 1.03
    recent_low_20 = min(lows[-21:-1]) if len(lows) >= 21 else last * 0.96
    ma20 = _mean(closes[-20:])
    ma50 = _mean(closes[-50:])
    volume_avg20 = _mean(volumes[-21:-1])
    relative_volume = volumes[-1] / volume_avg20 if volume_avg20 else 1.0
    dollar_volume_m = last * volumes[-1] / 1_000_000 if volumes else 0.0
    close_position = (last - lows[-1]) / max(highs[-1] - lows[-1], 0.0001) if lows else 0.5
    atr = _atr(rows, 14)
    atr_pct = atr / last if last else 0.0
    benchmark_return = _benchmark_return(stock.get("sector"), benchmark_map, series_by_symbol)
    return_5d = _return(closes, 5)
    return_20d = _return(closes, 20)
    relative_strength_5d = return_5d - benchmark_return

    technical_score = _clamp(
        36
        + (12 if last > recent_high_20 else 0)
        + (9 if last > ma20 else -6)
        + (9 if last > ma50 else -6)
        + (12 if close_position >= 0.72 else -3)
        + (8 if return_5d > 0 else -4)
        + (7 if relative_strength_5d > 0.015 else 0)
    )
    volume_score = _clamp(
        34
        + min(relative_volume, 4.0) * 9
        + min(dollar_volume_m / 40, 4.0) * 5
        + (8 if relative_volume >= 1.8 and close_position >= 0.62 else 0)
        - (20 if dollar_volume_m < 8 else 0)
    )
    squeeze_score = _clamp(25 + min(relative_volume, 6) * 6 + max(0, return_5d) * 260 + (10 if dollar_volume_m >= 15 else -12))

    return {
        "source": series.source if series else "missing",
        "real_data": bool(series and series.real_data),
        "latest_date": rows[-1]["date"] if rows else None,
        "last_close": last,
        "previous_close": previous,
        "gap_pct": last / previous - 1 if previous else 0.0,
        "return_5d": round(return_5d, 5),
        "return_20d": round(return_20d, 5),
        "benchmark_return_5d": round(benchmark_return, 5),
        "relative_strength_5d": round(relative_strength_5d, 5),
        "relative_volume": round(relative_volume, 3),
        "dollar_volume_m": round(dollar_volume_m, 3),
        "close_position": round(close_position, 3),
        "above_20d_ma": last > ma20,
        "above_50d_ma": last > ma50,
        "new_20d_high": last > recent_high_20,
        "recent_support": recent_low_20,
        "recent_resistance": recent_high_20,
        "gap_fill_level": previous,
        "vwap_proxy": (highs[-1] + lows[-1] + last) / 3 if highs else last,
        "atr": round(atr, 4),
        "atr_pct": round(atr_pct, 5),
        "technical_score": round(technical_score, 2),
        "volume_score": round(volume_score, 2),
        "squeeze_score": round(squeeze_score, 2),
        "price_history": [{"date": row["date"], "close": row["close"], "volume": row["volume"]} for row in rows[-80:]],
    }


def _build_sector_strength(sector_map: dict[str, Any], benchmark_map: dict[str, Any], series_by_symbol: dict[str, PriceSeries]) -> dict[str, Any]:
    sectors = sorted({payload.get("sector") for payload in sector_map.values() if payload.get("sector")})
    result: dict[str, Any] = {}
    for sector in sectors:
        benchmarks = (benchmark_map.get("sector_benchmarks") or {}).get(sector, [])
        returns = []
        volume_scores = []
        for symbol in benchmarks:
            series = series_by_symbol.get(symbol)
            if not series or len(series.rows) < 30:
                continue
            closes = [row["close"] for row in series.rows]
            volumes = [row["volume"] for row in series.rows]
            returns.append(_return(closes, 5))
            avg_volume = _mean(volumes[-21:-1])
            volume_scores.append(volumes[-1] / avg_volume if avg_volume else 1.0)
        score = _clamp(45 + _mean(returns) * 700 + min(_mean(volume_scores), 3) * 8)
        result[sector] = {
            "sector": sector,
            "score": round(score, 2),
            "level": "mainline" if score >= 68 else "watch" if score >= 55 else "weak",
            "benchmarks": benchmarks,
        }
    return result


def _candidate_type(stock: dict[str, Any], features: dict[str, Any], news: dict[str, Any], risk_score: float) -> str:
    base_types = stock.get("candidate_types") or []
    if risk_score >= 68 and "avoid_low_liquidity" in base_types:
        return "avoid_low_liquidity"
    if news.get("catalyst_score", 0) < 45 and "avoid_social_only" in base_types:
        return "avoid_social_only"
    if features["squeeze_score"] >= 68 and "squeeze_setup" in base_types:
        return "squeeze_setup"
    if news.get("catalyst_score", 0) >= 65:
        return news.get("catalyst_type") or "catalyst_breakout"
    if features["new_20d_high"] and features["relative_volume"] >= 1.6:
        return "gap_and_go"
    if features["above_20d_ma"] and features["relative_strength_5d"] > 0:
        return "reversal_reclaim"
    return base_types[0] if base_types else "watch_only"


def _primary_scenario(market_context: dict[str, Any], candidate_type: str, features: dict[str, Any]) -> str:
    if candidate_type.startswith("avoid"):
        return "reject_or_no_trade"
    if market_context.get("market_state") == "defense":
        return "only_if_market_reclaims_risk_on"
    if features["new_20d_high"] and features["relative_volume"] >= 1.7:
        return "next_day_momentum_extension"
    return "trigger_confirmed_upside_attempt"


def _risk_score(features: dict[str, Any], news: dict[str, Any], market_context: dict[str, Any]) -> float:
    return _clamp(
        (18 if not features["real_data"] else 0)
        + (18 if features["dollar_volume_m"] < 8 else 0)
        + (12 if features["gap_pct"] > 0.08 else 0)
        + (news.get("risk_event_score", 0) * 0.55)
        + (12 if market_context.get("market_state") == "defense" else 0)
        + (10 if features["atr_pct"] > 0.14 else 0)
    )


def _historical_similar_samples(features: dict[str, Any]) -> list[dict[str, Any]]:
    history = features.get("price_history") or []
    if len(history) < 35:
        return []
    closes = [row["close"] for row in history]
    samples = []
    current_return = features["return_5d"]
    for index in range(20, len(history) - 5):
        prior = closes[index] / closes[index - 5] - 1 if closes[index - 5] else 0
        if abs(prior - current_return) <= 0.025:
            future = closes[index + 1 : index + 6]
            samples.append(
                {
                    "date": history[index]["date"],
                    "similarity_note": "5d return and recent structure roughly matched",
                    "forward_5d_return": round(future[-1] / closes[index] - 1, 4) if future and closes[index] else 0,
                }
            )
    return samples[-5:]


def _benchmark_return(sector: str | None, benchmark_map: dict[str, Any], series_by_symbol: dict[str, PriceSeries]) -> float:
    benchmarks = (benchmark_map.get("sector_benchmarks") or {}).get(sector or "", ["SPY"])
    values = []
    for symbol in benchmarks[:2]:
        series = series_by_symbol.get(symbol)
        if series and len(series.rows) >= 8:
            values.append(_return([row["close"] for row in series.rows], 5))
    return _mean(values)


def _ev(source: str, name: str, score: float, detail: str = "") -> dict[str, Any]:
    return {"source": source, "name": name or source, "score": round(float(score or 0), 2), "detail": detail or ""}


def _return(values: list[float], days: int) -> float:
    if len(values) <= days or values[-days - 1] == 0:
        return 0.0
    return values[-1] / values[-days - 1] - 1


def _atr(rows: list[dict[str, Any]], days: int) -> float:
    if len(rows) < days + 1:
        return 0.0
    ranges = []
    for index in range(len(rows) - days, len(rows)):
        high = rows[index]["high"]
        low = rows[index]["low"]
        previous_close = rows[index - 1]["close"]
        ranges.append(max(high - low, abs(high - previous_close), abs(low - previous_close)))
    return _mean(ranges)


def _mean(values: list[float]) -> float:
    clean = [value for value in values if value is not None and not math.isnan(value)]
    return sum(clean) / len(clean) if clean else 0.0


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return min(high, max(low, value))
