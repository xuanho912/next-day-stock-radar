from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

from providers.yahoo_provider import PriceSeries


MIN_PRICE = 2.0
MIN_AVG_DOLLAR_VOLUME_M = 10.0
HIGH_VOL_ATR_PCT = 0.12
LOW_LIQUIDITY_DOLLAR_VOLUME_M = 12.0
OTC_MARKERS = ("OTC", "PINK", "GREY", "GREY MARKET", "EXPERT MARKET")


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
    excluded = []
    sector_strength = _build_sector_strength(sector_map, benchmark_map, series_by_symbol)
    for symbol in symbols:
        stock = sector_map.get(symbol, {})
        fundamental = (fundamentals.get("symbols") or {}).get(symbol, {})
        features = _stock_features(symbol, series_by_symbol.get(symbol), stock, benchmark_map, series_by_symbol)
        pool_filter = _pool_filter(symbol, features, fundamental)
        news = (news_events.get("symbols") or {}).get(symbol, {})
        candidate = _build_candidate(symbol, stock, features, news, fundamental, sector_strength, market_context, pool_filter)
        if pool_filter["hard_excluded"]:
            excluded.append(candidate)
        else:
            candidates.append(candidate)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sector_strength": sector_strength,
        "candidates": candidates,
        "excluded_candidates": excluded,
        "pool_filter_rules": {
            "min_price": MIN_PRICE,
            "min_average_dollar_volume_m": MIN_AVG_DOLLAR_VOLUME_M,
            "exclude_otc_pink_by_default": True,
            "low_liquidity_flag": "high_liquidity_risk",
            "high_volatility_flag": "high_risk_high_volatility",
        },
    }


def _build_candidate(
    symbol: str,
    stock: dict[str, Any],
    features: dict[str, Any],
    news: dict[str, Any],
    fundamental: dict[str, Any],
    sector_strength: dict[str, Any],
    market_context: dict[str, Any],
    pool_filter: dict[str, Any],
) -> dict[str, Any]:
    sector = stock.get("sector") or "Unknown"
    sector_payload = sector_strength.get(sector, {"score": 40, "level": "weak"})
    raw_scores = _raw_scores(features, news, sector_payload, market_context, pool_filter)
    support, conflict, missing = _evidence(symbol, sector, features, news, sector_payload, market_context, pool_filter, raw_scores)
    risk_flags = _risk_flags(features, news, pool_filter)
    candidate_type = _candidate_type(stock, features, news, raw_scores, pool_filter)
    edge_status = _edge_status(raw_scores, support, conflict, risk_flags, market_context, pool_filter)
    price_path = _price_path(features, raw_scores, candidate_type)
    analog = _historical_analog(features, market_context, news)

    return {
        "ticker": symbol,
        "company_name": fundamental.get("company_name") or stock.get("company_name") or symbol,
        "sector": sector,
        "pool_filter": pool_filter,
        "risk_flags": risk_flags,
        "candidate_type": candidate_type,
        "edge_status": edge_status,
        "last_close": round(features["last_close"], 4),
        "features": features,
        "news": news,
        "fundamental": fundamental,
        "sector_theme": sector_payload,
        "elasticity_score": raw_scores["elasticity_score"],
        "next_day_move_probability": raw_scores["next_day_move_probability"],
        "upside_momentum_score": raw_scores["upside_momentum_score"],
        "bounce_score": raw_scores["bounce_score"],
        "downside_continuation_score": raw_scores["downside_continuation_score"],
        "squeeze_score": raw_scores["squeeze_score"],
        "squeeze_data_status": raw_scores["squeeze_data_status"],
        "catalyst_score": raw_scores["catalyst_score"],
        "risk_score": raw_scores["risk_score"],
        "confluence_score": raw_scores["confluence_score"],
        "primary_scenario": _primary_scenario(market_context, candidate_type, raw_scores),
        "primary_probability": raw_scores["primary_probability"],
        "secondary_scenario": _secondary_scenario(candidate_type, features),
        "secondary_probability": raw_scores["secondary_probability"],
        "risk_scenario": _risk_scenario(candidate_type, raw_scores),
        "risk_probability": raw_scores["risk_probability"],
        "next_day_expected_range": price_path["next_day_expected_range"],
        "scenario_prices": price_path["scenario_prices"],
        "trigger_levels": price_path["trigger_levels"],
        "upside_trigger_level": price_path["trigger_levels"]["upside_trigger_level"],
        "downside_risk_level": price_path["trigger_levels"]["downside_risk_level"],
        "invalidation_level": price_path["trigger_levels"]["invalidation_level"],
        "gap_fill_level": price_path["trigger_levels"]["gap_fill_level"],
        "breakout_level": price_path["trigger_levels"]["breakout_level"],
        "breakdown_level": price_path["trigger_levels"]["breakdown_level"],
        "nearest_support": price_path["trigger_levels"]["nearest_support"],
        "nearest_resistance": price_path["trigger_levels"]["nearest_resistance"],
        "trigger_meaning": price_path["trigger_meaning"],
        "supporting_evidence": support,
        "conflicting_evidence": conflict,
        "missing_evidence": missing,
        "historical_analog": analog,
        "historical_similar_samples": analog["top_similar_dates"],
        "not_trading_advice_note": "These are probabilistic path levels, not buy/sell advice or execution instructions.",
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
    opens = [row["open"] for row in rows]
    volumes = [row["volume"] for row in rows]
    last = closes[-1] if closes else 0.0
    previous = closes[-2] if len(closes) >= 2 else last
    recent_high_20 = max(highs[-21:-1]) if len(highs) >= 21 else last * 1.03
    recent_low_20 = min(lows[-21:-1]) if len(lows) >= 21 else last * 0.96
    recent_high_50 = max(highs[-51:-1]) if len(highs) >= 51 else recent_high_20
    recent_low_50 = min(lows[-51:-1]) if len(lows) >= 51 else recent_low_20
    ma20 = _mean(closes[-20:])
    ma50 = _mean(closes[-50:])
    volume_avg20 = _mean(volumes[-21:-1])
    volume_std20 = _std(volumes[-21:-1])
    relative_volume = volumes[-1] / volume_avg20 if volume_avg20 else 1.0
    volume_z_score = (volumes[-1] - volume_avg20) / volume_std20 if volume_std20 else 0.0
    dollar_volume_m = last * volumes[-1] / 1_000_000 if volumes else 0.0
    avg_dollar_volume_m = _mean([row["close"] * row["volume"] / 1_000_000 for row in rows[-21:-1]]) if rows else 0.0
    close_position = (last - lows[-1]) / max(highs[-1] - lows[-1], 0.0001) if lows else 0.5
    intraday_range_pct = (highs[-1] - lows[-1]) / last if last else 0.0
    gap_pct = opens[-1] / previous - 1 if previous and opens else 0.0
    atr = _atr(rows, 14)
    atr_pct = atr / last if last else 0.0
    realized_volatility_20d = _realized_volatility(closes, 20)
    rsi_14 = _rsi(closes, 14)
    benchmark_return = _benchmark_return(stock.get("sector"), benchmark_map, series_by_symbol)
    return_1d = _return(closes, 1)
    return_5d = _return(closes, 5)
    return_20d = _return(closes, 20)
    relative_strength_5d = return_5d - benchmark_return
    beta_proxy = _beta_proxy(closes, series_by_symbol.get("SPY"))

    technical_score = _clamp(
        34
        + (13 if last > recent_high_20 else 0)
        + (8 if last > recent_high_50 else 0)
        + (9 if last > ma20 else -7)
        + (9 if last > ma50 else -7)
        + (12 if close_position >= 0.72 else -4)
        + (8 if return_5d > 0 else -5)
        + (8 if relative_strength_5d > 0.015 else 0)
        + (6 if gap_pct > 0.02 and close_position >= 0.6 else 0)
    )
    volume_score = _clamp(
        32
        + min(relative_volume, 4.0) * 9
        + min(max(volume_z_score, 0), 4.0) * 5
        + min(avg_dollar_volume_m / 40, 4.0) * 5
        + (8 if relative_volume >= 1.8 and close_position >= 0.62 else 0)
        - (24 if avg_dollar_volume_m < MIN_AVG_DOLLAR_VOLUME_M else 0)
    )

    return {
        "source": series.source if series else "missing",
        "source_status": "available" if series and series.real_data else "fallback_or_missing",
        "real_data": bool(series and series.real_data),
        "latest_date": rows[-1]["date"] if rows else None,
        "last_close": last,
        "previous_close": previous,
        "open": opens[-1] if opens else last,
        "gap_pct": round(gap_pct, 5),
        "return_1d": round(return_1d, 5),
        "return_5d": round(return_5d, 5),
        "return_20d": round(return_20d, 5),
        "benchmark_return_5d": round(benchmark_return, 5),
        "relative_strength_5d": round(relative_strength_5d, 5),
        "relative_volume": round(relative_volume, 3),
        "volume_z_score": round(volume_z_score, 3),
        "dollar_volume_m": round(dollar_volume_m, 3),
        "avg_dollar_volume_m": round(avg_dollar_volume_m, 3),
        "close_position": round(close_position, 3),
        "intraday_range_pct": round(intraday_range_pct, 5),
        "above_20d_ma": last > ma20,
        "above_50d_ma": last > ma50,
        "new_20d_high": last > recent_high_20,
        "new_50d_high": last > recent_high_50,
        "recent_support": recent_low_20,
        "recent_resistance": recent_high_20,
        "recent_support_50d": recent_low_50,
        "recent_resistance_50d": recent_high_50,
        "gap_fill_level": previous,
        "vwap_proxy": (highs[-1] + lows[-1] + last) / 3 if highs else last,
        "atr": round(atr, 4),
        "atr_pct": round(atr_pct, 5),
        "realized_volatility_20d": round(realized_volatility_20d, 5),
        "rsi_14": round(rsi_14, 2) if rsi_14 is not None else None,
        "beta_proxy": round(beta_proxy, 3),
        "technical_score": round(technical_score, 2),
        "volume_score": round(volume_score, 2),
        "price_history": [
            {
                "date": row["date"],
                "open": row["open"],
                "high": row["high"],
                "low": row["low"],
                "close": row["close"],
                "volume": row["volume"],
            }
            for row in rows[-120:]
        ],
    }


def _raw_scores(
    features: dict[str, Any],
    news: dict[str, Any],
    sector_payload: dict[str, Any],
    market_context: dict[str, Any],
    pool_filter: dict[str, Any],
) -> dict[str, Any]:
    catalyst_score = float(news.get("catalyst_score") or 35)
    technical = float(features["technical_score"])
    volume = float(features["volume_score"])
    sector = float(sector_payload.get("score") or 40)
    risk_score = _risk_score(features, news, market_context, pool_filter)
    elasticity_score = _clamp(
        features["atr_pct"] * 260
        + features["realized_volatility_20d"] * 620
        + features["intraday_range_pct"] * 160
        + min(max(features["volume_z_score"], 0), 5) * 7
        + abs(features["gap_pct"]) * 180
        + max(features["beta_proxy"] - 1, 0) * 12
        + catalyst_score * 0.18
        + volume * 0.18
        + 18
    )
    upside_momentum_score = _clamp(
        30
        + technical * 0.32
        + volume * 0.22
        + sector * 0.18
        + max(features["relative_strength_5d"], 0) * 550
        + (9 if features["new_20d_high"] else 0)
        + (8 if features["close_position"] >= 0.72 else 0)
    )
    bounce_score = _clamp(
        28
        + (18 if features["rsi_14"] is not None and features["rsi_14"] <= 38 else 0)
        + max(-features["return_5d"], 0) * 420
        + (10 if features["close_position"] >= 0.6 and features["return_1d"] > 0 else 0)
        + sector * 0.12
        - risk_score * 0.12
    )
    downside_continuation_score = _clamp(
        25
        + max(-features["return_5d"], 0) * 530
        + (14 if not features["above_20d_ma"] else 0)
        + (12 if features["close_position"] <= 0.28 else 0)
        + risk_score * 0.18
    )
    squeeze_score = _clamp(
        26
        + min(features["relative_volume"], 6) * 6
        + max(features["atr_pct"] - 0.05, 0) * 260
        + max(features["return_5d"], 0) * 240
        + (8 if catalyst_score >= 60 else 0)
        - (18 if pool_filter["flags"].get("high_liquidity_risk") else 0)
    )
    confluence_score = _clamp(
        catalyst_score * 0.22
        + technical * 0.22
        + volume * 0.20
        + sector * 0.16
        + upside_momentum_score * 0.10
        + bounce_score * 0.04
        + elasticity_score * 0.06
        - risk_score * 0.32
        + _market_adjustment(market_context)
    )
    next_day_move_probability = _clamp((elasticity_score * 0.62 + confluence_score * 0.28 + catalyst_score * 0.10) / 100, 0, 1)
    primary_probability = _clamp((confluence_score * 0.52 + max(upside_momentum_score, bounce_score) * 0.28 + sector * 0.20) / 100, 0.05, 0.82)
    risk_probability = _clamp((risk_score * 0.58 + downside_continuation_score * 0.34) / 100, 0.03, 0.86)
    secondary_probability = _clamp(1.0 - primary_probability - risk_probability, 0.05, 0.55)

    return {
        "elasticity_score": round(elasticity_score, 2),
        "next_day_move_probability": round(next_day_move_probability, 4),
        "upside_momentum_score": round(upside_momentum_score, 2),
        "bounce_score": round(bounce_score, 2),
        "downside_continuation_score": round(downside_continuation_score, 2),
        "squeeze_score": round(squeeze_score, 2),
        "squeeze_data_status": {
            "short_interest": "proxy",
            "options_flow": "proxy",
            "borrow_fee": "missing",
            "note": "Squeeze score uses volatility, relative volume and momentum proxies until real short/options data is connected.",
        },
        "catalyst_score": round(catalyst_score, 2),
        "risk_score": round(risk_score, 2),
        "confluence_score": round(confluence_score, 2),
        "primary_probability": round(primary_probability, 4),
        "secondary_probability": round(secondary_probability, 4),
        "risk_probability": round(risk_probability, 4),
    }


def _pool_filter(symbol: str, features: dict[str, Any], fundamental: dict[str, Any]) -> dict[str, Any]:
    exchange = str(fundamental.get("exchange") or "").upper()
    flags = {
        "price_below_minimum": features["last_close"] <= MIN_PRICE,
        "high_liquidity_risk": features["avg_dollar_volume_m"] < MIN_AVG_DOLLAR_VOLUME_M,
        "otc_or_pink": any(marker in exchange for marker in OTC_MARKERS),
        "high_risk_high_volatility": features["atr_pct"] >= HIGH_VOL_ATR_PCT and features["avg_dollar_volume_m"] < 40,
        "fallback_or_missing_price_data": not features["real_data"],
    }
    hard_excluded = flags["price_below_minimum"] or flags["otc_or_pink"]
    reason = []
    if flags["price_below_minimum"]:
        reason.append(f"price <= {MIN_PRICE}")
    if flags["otc_or_pink"]:
        reason.append("OTC/Pink exchange")
    if flags["high_liquidity_risk"]:
        reason.append("average dollar volume below threshold")
    if flags["high_risk_high_volatility"]:
        reason.append("high volatility small-cap risk")
    if flags["fallback_or_missing_price_data"]:
        reason.append("price data fallback or missing")
    return {
        "symbol": symbol,
        "passes_price_filter": not flags["price_below_minimum"],
        "passes_liquidity_filter": not flags["high_liquidity_risk"],
        "passes_exchange_filter": not flags["otc_or_pink"],
        "hard_excluded": hard_excluded,
        "flags": flags,
        "reason": reason,
    }


def _risk_flags(features: dict[str, Any], news: dict[str, Any], pool_filter: dict[str, Any]) -> list[str]:
    flags = [name for name, enabled in pool_filter["flags"].items() if enabled]
    if news.get("risk_event_score", 0) >= 35:
        flags.append("news_reversal_or_event_risk")
    if features["gap_pct"] > 0.08:
        flags.append("gap_fade_risk")
    if features["close_position"] <= 0.28:
        flags.append("weak_close_distribution_risk")
    return flags


def _candidate_type(stock: dict[str, Any], features: dict[str, Any], news: dict[str, Any], scores: dict[str, Any], pool_filter: dict[str, Any]) -> str:
    if pool_filter["hard_excluded"] or scores["confluence_score"] < 42:
        return "no_edge"
    if scores["downside_continuation_score"] >= 68 and scores["upside_momentum_score"] < 55:
        return "downside_continuation"
    if scores["risk_score"] >= 62 and scores["bounce_score"] >= 55:
        return "failed_bounce_risk"
    if scores["squeeze_score"] >= 68 and scores["squeeze_data_status"]["short_interest"] == "proxy":
        return "short_squeeze_candidate"
    if scores["catalyst_score"] >= 68 and news.get("headline_count", 0) > 0:
        return "event_driven_volatility"
    if features["gap_pct"] >= 0.025 and features["close_position"] >= 0.62:
        return "gap_continuation"
    if scores["bounce_score"] >= 64 and scores["upside_momentum_score"] < 70:
        return "oversold_bounce"
    if scores["upside_momentum_score"] >= 64:
        return "next_day_upside_momentum"
    return "no_edge"


def _edge_status(
    scores: dict[str, Any],
    support: list[dict[str, Any]],
    conflict: list[dict[str, Any]],
    risk_flags: list[str],
    market_context: dict[str, Any],
    pool_filter: dict[str, Any],
) -> str:
    if pool_filter["hard_excluded"] or "high_liquidity_risk" in risk_flags and scores["confluence_score"] < 58:
        return "AVOID"
    if scores["risk_score"] >= 70:
        return "AVOID"
    if scores["elasticity_score"] >= 75 and scores["confluence_score"] >= 62 and scores["risk_score"] >= 50:
        return "HIGH_RISK_HIGH_REWARD"
    if scores["confluence_score"] >= 78 and len(support) >= 4 and len(conflict) <= 2 and market_context.get("market_state") != "defense":
        return "STRONG_EDGE"
    if scores["confluence_score"] >= 66 and len(support) >= 3:
        return "MODERATE_EDGE"
    if scores["confluence_score"] >= 52:
        return "WATCH"
    return "NO_EDGE"


def _price_path(features: dict[str, Any], scores: dict[str, Any], candidate_type: str) -> dict[str, Any]:
    last = features["last_close"]
    atr_pct = max(features["atr_pct"], 0.035)
    move_probability = scores["next_day_move_probability"]
    range_pct = min(0.24, max(0.035, atr_pct * (1.15 + move_probability)))
    expected_low_price = last * (1 - range_pct * (0.72 if scores["risk_score"] < 55 else 0.95))
    expected_high_price = last * (1 + range_pct * (1.15 if candidate_type in {"short_squeeze_candidate", "event_driven_volatility"} else 0.92))
    expected_mid = (expected_low_price + expected_high_price) / 2
    breakout = max(features["recent_resistance"], last * 1.018)
    breakdown = min(features["recent_support"], last * 0.982)
    upside_trigger = max(breakout, last * (1.012 + min(features["atr_pct"], 0.08) * 0.18))
    downside_risk = min(features["vwap_proxy"], last * (1 - min(features["atr_pct"], 0.09) * 0.38))
    invalidation = min(downside_risk, breakdown)
    bounce_target = last * (1 + max(0.035, min(range_pct * 0.75, 0.16)))
    failed_bounce = min(invalidation, last * (1 - range_pct * 0.55))
    return {
        "next_day_expected_range": {
            "expected_low": round(expected_low_price, 4),
            "expected_high": round(expected_high_price, 4),
            "expected_mid": round(expected_mid, 4),
            "expected_low_pct": round(expected_low_price / last - 1, 5) if last else 0,
            "expected_high_pct": round(expected_high_price / last - 1, 5) if last else 0,
            "volatility_adjusted_range": round(range_pct, 5),
            "label": f"{expected_low_price:.2f} to {expected_high_price:.2f}",
        },
        "scenario_prices": {
            "base_case_price": round(expected_mid, 4),
            "upside_case_price": round(expected_high_price, 4),
            "downside_case_price": round(expected_low_price, 4),
            "bounce_target_price": round(bounce_target, 4),
            "failed_bounce_price": round(failed_bounce, 4),
        },
        "trigger_levels": {
            "upside_trigger_level": round(upside_trigger, 4),
            "downside_risk_level": round(downside_risk, 4),
            "invalidation_level": round(invalidation, 4),
            "gap_fill_level": round(features["gap_fill_level"], 4),
            "breakout_level": round(breakout, 4),
            "breakdown_level": round(breakdown, 4),
            "nearest_support": round(features["recent_support"], 4),
            "nearest_resistance": round(features["recent_resistance"], 4),
        },
        "trigger_meaning": {
            "upside_trigger_level": "Standing above this level starts to confirm the upside path.",
            "invalidation_level": "Breaking below this level invalidates the bounce/upside path.",
            "downside_risk_level": "Breaking below this level means the risk path is taking control.",
            "gap_fill_level": "Filling this gap suggests gap continuation has failed.",
            "note": "These are probabilistic path levels, not buy/sell advice.",
        },
    }


def _historical_analog(features: dict[str, Any], market_context: dict[str, Any], news: dict[str, Any]) -> dict[str, Any]:
    history = features.get("price_history") or []
    if len(history) < 45:
        return _empty_analog()
    closes = [row["close"] for row in history]
    volumes = [row["volume"] for row in history]
    current_signature = {
        "return_5d": features["return_5d"],
        "volume_z": features["volume_z_score"],
        "gap": features["gap_pct"],
        "rsi": features["rsi_14"] or 50,
        "relative_strength": features["relative_strength_5d"],
        "volatility": features["atr_pct"],
    }
    samples = []
    for index in range(25, len(history) - 6):
        window = closes[: index + 1]
        vol_window = volumes[max(0, index - 21) : index]
        avg_volume = _mean(vol_window)
        std_volume = _std(vol_window)
        signature = {
            "return_5d": _return(window, 5),
            "volume_z": (volumes[index] - avg_volume) / std_volume if std_volume else 0,
            "gap": history[index]["open"] / closes[index - 1] - 1 if closes[index - 1] else 0,
            "rsi": _rsi(window, 14) or 50,
            "relative_strength": _return(window, 5),
            "volatility": _atr(history[: index + 1], 14) / closes[index] if closes[index] else 0,
        }
        distance = _analog_distance(current_signature, signature)
        future = history[index + 1 : index + 6]
        next_row = history[index + 1]
        mfe = max(row["high"] for row in future) / closes[index] - 1
        mae = min(row["low"] for row in future) / closes[index] - 1
        samples.append(
            {
                "date": history[index]["date"],
                "distance": round(distance, 4),
                "market_state": market_context.get("market_state"),
                "news_catalyst_proxy": bool(news.get("headline_count")),
                "next_day_return": round(next_row["close"] / closes[index] - 1, 5),
                "return_3d": round(future[2]["close"] / closes[index] - 1, 5) if len(future) >= 3 else None,
                "return_5d": round(future[4]["close"] / closes[index] - 1, 5) if len(future) >= 5 else None,
                "max_favorable_excursion": round(mfe, 5),
                "max_adverse_excursion": round(mae, 5),
            }
        )
    top = sorted(samples, key=lambda item: item["distance"])[:12]
    sample_size = len(top)
    next_returns = [item["next_day_return"] for item in top]
    hit_rate = sum(1 for value in next_returns if value and value > 0.03) / sample_size if sample_size else None
    return {
        "top_similar_dates": top[:8],
        "next_day_return_avg": round(_mean(next_returns), 5) if top else None,
        "next_day_hit_rate": round(hit_rate, 5) if hit_rate is not None else None,
        "forward_return_3d_avg": round(_mean([item["return_3d"] for item in top if item["return_3d"] is not None]), 5) if top else None,
        "forward_return_5d_avg": round(_mean([item["return_5d"] for item in top if item["return_5d"] is not None]), 5) if top else None,
        "max_favorable_excursion_avg": round(_mean([item["max_favorable_excursion"] for item in top]), 5) if top else None,
        "max_adverse_excursion_avg": round(_mean([item["max_adverse_excursion"] for item in top]), 5) if top else None,
        "worst_case": min(next_returns) if next_returns else None,
        "best_case": max(next_returns) if next_returns else None,
        "sample_size": sample_size,
        "low_sample_warning": sample_size < 20,
    }


def _empty_analog() -> dict[str, Any]:
    return {
        "top_similar_dates": [],
        "next_day_return_avg": None,
        "next_day_hit_rate": None,
        "forward_return_3d_avg": None,
        "forward_return_5d_avg": None,
        "max_favorable_excursion_avg": None,
        "max_adverse_excursion_avg": None,
        "worst_case": None,
        "best_case": None,
        "sample_size": 0,
        "low_sample_warning": True,
    }


def _evidence(
    symbol: str,
    sector: str,
    features: dict[str, Any],
    news: dict[str, Any],
    sector_payload: dict[str, Any],
    market_context: dict[str, Any],
    pool_filter: dict[str, Any],
    scores: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    support: list[dict[str, Any]] = []
    conflict: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []

    if news.get("catalyst_score", 0) >= 60:
        support.append(_ev("catalyst", news.get("catalyst_type"), news.get("catalyst_score"), news.get("primary_headline")))
    else:
        conflict.append(_ev("catalyst", "weak_or_missing_catalyst", 100 - news.get("catalyst_score", 35), "No strong confirmed recent catalyst."))
    if features["technical_score"] >= 64:
        support.append(_ev("price", "price_structure_confirmed", features["technical_score"], "Breakout/reclaim/high-close structure is constructive."))
    else:
        conflict.append(_ev("price", "price_structure_unconfirmed", 100 - features["technical_score"], "Price structure has not confirmed a high-quality setup."))
    if features["volume_score"] >= 62:
        support.append(_ev("volume", "volume_anomaly_confirmed", features["volume_score"], "Relative volume and dollar liquidity are sufficient."))
    else:
        conflict.append(_ev("volume", "volume_or_liquidity_weak", 100 - features["volume_score"], "Volume confirmation or liquidity is weak."))
    if sector_payload["score"] >= 62:
        support.append(_ev("sector", "sector_context_confirmed", sector_payload["score"], f"{sector} is showing relative strength."))
    else:
        conflict.append(_ev("sector", "sector_context_weak", 100 - sector_payload["score"], f"{sector} is not a confirmed capital-flow theme."))
    if market_context.get("market_state") == "attack":
        support.append(_ev("market", "risk_on_market_context", market_context.get("market_score", 50), "Market context allows selective speculation."))
    elif market_context.get("market_state") == "defense":
        conflict.append(_ev("market", "defensive_market_context", 70, "Market context is defensive; ratings must be capped."))
    if scores["squeeze_data_status"]["short_interest"] == "proxy":
        missing.append(_ev("short_interest", "real_short_interest_missing", 0, "Squeeze score is proxy-only until real short interest/options data is connected."))
    if not features["real_data"]:
        missing.append(_ev("price_data", "real_price_data_missing", 0, "OHLCV uses fallback; do not present as fully validated."))
    for flag, enabled in pool_filter["flags"].items():
        if enabled:
            conflict.append(_ev("pool_filter", flag, 75 if flag in {"high_liquidity_risk", "high_risk_high_volatility"} else 90, flag))
    return support, conflict, missing


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
        score = _clamp(43 + _mean(returns) * 680 + min(_mean(volume_scores), 3) * 8)
        result[sector] = {
            "sector": sector,
            "score": round(score, 2),
            "level": "mainline" if score >= 68 else "watch" if score >= 55 else "weak",
            "benchmarks": benchmarks,
            "source_status": "proxy" if not returns else "available",
        }
    return result


def _primary_scenario(market_context: dict[str, Any], candidate_type: str, scores: dict[str, Any]) -> str:
    if candidate_type == "no_edge":
        return "no_edge"
    if candidate_type in {"failed_bounce_risk", "downside_continuation"}:
        return "risk_path_continuation"
    if market_context.get("market_state") == "defense":
        return "only_if_market_reclaims_risk_on"
    if candidate_type == "oversold_bounce":
        return "bounce_attempt_after_trigger"
    return "upside_path_after_trigger"


def _secondary_scenario(candidate_type: str, features: dict[str, Any]) -> str:
    if candidate_type in {"failed_bounce_risk", "downside_continuation"}:
        return "failed_risk_path_relief_bounce"
    if features["gap_pct"] > 0.035:
        return "open_drive_then_gap_fill"
    return "range_extension_after_trigger"


def _risk_scenario(candidate_type: str, scores: dict[str, Any]) -> str:
    if candidate_type == "downside_continuation":
        return "downside_continuation"
    if candidate_type == "failed_bounce_risk":
        return "failed_bounce_follow_through"
    return "failed_breakout_or_gap_fade"


def _risk_score(features: dict[str, Any], news: dict[str, Any], market_context: dict[str, Any], pool_filter: dict[str, Any]) -> float:
    return _clamp(
        (14 if not features["real_data"] else 0)
        + (22 if pool_filter["flags"].get("high_liquidity_risk") else 0)
        + (20 if pool_filter["flags"].get("high_risk_high_volatility") else 0)
        + (16 if features["gap_pct"] > 0.08 else 0)
        + (news.get("risk_event_score", 0) * 0.55)
        + (12 if market_context.get("market_state") == "defense" else 0)
        + (10 if features["atr_pct"] > 0.14 else 0)
        + (8 if features["close_position"] <= 0.28 else 0)
    )


def _market_adjustment(market_context: dict[str, Any]) -> float:
    return {"attack": 7, "neutral": 0, "defense": -14}.get(market_context.get("market_state"), 0)


def _benchmark_return(sector: str | None, benchmark_map: dict[str, Any], series_by_symbol: dict[str, PriceSeries]) -> float:
    benchmarks = (benchmark_map.get("sector_benchmarks") or {}).get(sector or "", ["SPY"])
    values = []
    for symbol in benchmarks[:2]:
        series = series_by_symbol.get(symbol)
        if series and len(series.rows) >= 8:
            values.append(_return([row["close"] for row in series.rows], 5))
    return _mean(values)


def _beta_proxy(closes: list[float], benchmark: PriceSeries | None) -> float:
    if not benchmark or len(closes) < 45 or len(benchmark.rows) < 45:
        return 1.0
    stock_returns = _daily_returns(closes[-45:])
    market_returns = _daily_returns([row["close"] for row in benchmark.rows[-45:]])
    variance = _variance(market_returns)
    if variance <= 0:
        return 1.0
    covariance = _covariance(stock_returns, market_returns)
    return max(0.2, min(3.5, covariance / variance))


def _analog_distance(current: dict[str, float], candidate: dict[str, float]) -> float:
    weights = {
        "return_5d": 8.0,
        "volume_z": 0.45,
        "gap": 7.0,
        "rsi": 0.025,
        "relative_strength": 5.0,
        "volatility": 5.5,
    }
    return math.sqrt(sum(((current[key] - candidate[key]) * weight) ** 2 for key, weight in weights.items()))


def _ev(source: str, name: str | None, score: float | None, detail: str = "") -> dict[str, Any]:
    return {"source": source, "name": name or source, "score": round(float(score or 0), 2), "detail": detail or ""}


def _return(values: list[float], days: int) -> float:
    if len(values) <= days or values[-days - 1] == 0:
        return 0.0
    return values[-1] / values[-days - 1] - 1


def _daily_returns(values: list[float]) -> list[float]:
    return [values[index] / values[index - 1] - 1 for index in range(1, len(values)) if values[index - 1]]


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


def _realized_volatility(values: list[float], days: int) -> float:
    returns = _daily_returns(values[-days - 1 :])
    if len(returns) < 2:
        return 0.0
    return _std(returns) * math.sqrt(252)


def _rsi(values: list[float], days: int) -> float | None:
    if len(values) < days + 1:
        return None
    gains = []
    losses = []
    for index in range(len(values) - days, len(values)):
        change = values[index] - values[index - 1]
        if change >= 0:
            gains.append(change)
        else:
            losses.append(abs(change))
    avg_gain = _mean(gains)
    avg_loss = _mean(losses)
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def _mean(values: list[float | None]) -> float:
    clean = [value for value in values if value is not None and not math.isnan(value)]
    return sum(clean) / len(clean) if clean else 0.0


def _std(values: list[float | None]) -> float:
    clean = [value for value in values if value is not None and not math.isnan(value)]
    if len(clean) < 2:
        return 0.0
    mean = _mean(clean)
    return math.sqrt(sum((value - mean) ** 2 for value in clean) / (len(clean) - 1))


def _variance(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = _mean(values)
    return sum((value - mean) ** 2 for value in values) / (len(values) - 1)


def _covariance(left: list[float], right: list[float]) -> float:
    count = min(len(left), len(right))
    if count < 2:
        return 0.0
    left = left[-count:]
    right = right[-count:]
    left_mean = _mean(left)
    right_mean = _mean(right)
    return sum((left[index] - left_mean) * (right[index] - right_mean) for index in range(count)) / (count - 1)


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return min(high, max(low, value))
