from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from providers.yahoo_provider import PriceSeries, expected_latest_trading_date, latest_available_date


CORE_MARKET_SYMBOLS = ["SPY", "QQQ", "IWM", "DIA"]
RISK_SYMBOLS = ["^VIX", "^TNX", "TLT", "UUP", "HYG", "LQD"]


def build_market_context(series_by_symbol: dict[str, PriceSeries]) -> dict[str, Any]:
    latest_date = latest_available_date(series_by_symbol, CORE_MARKET_SYMBOLS)
    expected_date = expected_latest_trading_date(datetime.now(timezone.utc))
    data_freshness_status = "fresh" if latest_date == expected_date else "stale"

    spy = _features(series_by_symbol.get("SPY"))
    qqq = _features(series_by_symbol.get("QQQ"))
    iwm = _features(series_by_symbol.get("IWM"))
    dia = _features(series_by_symbol.get("DIA"))
    vix = _features(series_by_symbol.get("^VIX"))
    tnx = _features(series_by_symbol.get("^TNX"))
    hyg = _features(series_by_symbol.get("HYG"))
    lqd = _features(series_by_symbol.get("LQD"))

    index_trend = _mean([spy["trend_score"], qqq["trend_score"], iwm["trend_score"], dia["trend_score"]])
    vix_score = _clamp(70 - (vix["last_close"] or 18) * 0.9 - max(vix["return_5d"], 0) * 160 + max(-vix["return_5d"], 0) * 80)
    rates_score = _clamp(55 - max(tnx["change_5d"], 0) * 4 + max(-tnx["change_5d"], 0) * 3)
    credit_score = _clamp(55 + (hyg["return_5d"] - lqd["return_5d"]) * 600)
    small_cap_score = _clamp(50 + (iwm["return_5d"] - spy["return_5d"]) * 700)

    market_score = round(index_trend * 0.34 + vix_score * 0.18 + rates_score * 0.12 + credit_score * 0.14 + small_cap_score * 0.12 + qqq["trend_score"] * 0.10, 2)
    if market_score >= 68:
        market_state = "attack"
    elif market_score >= 48:
        market_state = "neutral"
    else:
        market_state = "defense"

    risk_level = "low" if market_state == "attack" and vix_score >= 55 else "medium" if market_state != "defense" else "high"
    stale_warning = data_freshness_status != "fresh"

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "latest_data_date": latest_date,
        "expected_latest_trading_date": expected_date,
        "data_freshness_status": data_freshness_status,
        "stale_warning": stale_warning,
        "market_state": market_state,
        "market_score": market_score,
        "risk_level": risk_level,
        "speculation_background": _background_text(market_state, risk_level),
        "factors": {
            "index_trend": round(index_trend, 2),
            "vix_score": round(vix_score, 2),
            "rates_score": round(rates_score, 2),
            "credit_score": round(credit_score, 2),
            "small_cap_score": round(small_cap_score, 2),
            "spy": spy,
            "qqq": qqq,
            "iwm": iwm,
            "dia": dia,
            "vix": vix,
            "tnx": tnx,
        },
    }


def _features(series: PriceSeries | None) -> dict[str, Any]:
    rows = series.rows if series else []
    closes = [row["close"] for row in rows]
    if len(closes) < 30:
        return {"last_close": None, "return_5d": 0.0, "return_20d": 0.0, "change_5d": 0.0, "trend_score": 35.0}
    last = closes[-1]
    return_5d = _return(closes, 5)
    return_20d = _return(closes, 20)
    ma20 = _mean(closes[-20:])
    ma50 = _mean(closes[-50:]) if len(closes) >= 50 else ma20
    trend_score = _clamp(45 + return_20d * 420 + return_5d * 260 + (8 if last > ma20 else -8) + (8 if last > ma50 else -8))
    return {
        "last_close": round(last, 4),
        "return_5d": round(return_5d, 5),
        "return_20d": round(return_20d, 5),
        "change_5d": round(last - closes[-6], 5) if len(closes) > 6 else 0.0,
        "above_20d_ma": last > ma20,
        "above_50d_ma": last > ma50,
        "trend_score": round(trend_score, 2),
    }


def _background_text(market_state: str, risk_level: str) -> str:
    if market_state == "attack":
        return "Market context allows selective speculation; focus only on strong confluence candidates."
    if market_state == "defense":
        return "Market context is defensive; downgrade candidates and avoid weak liquidity."
    return "Market context is mixed; wait for trigger confirmation rather than chasing gaps."


def _return(values: list[float], days: int) -> float:
    if len(values) <= days or values[-days - 1] == 0:
        return 0.0
    return values[-1] / values[-days - 1] - 1


def _mean(values: list[float]) -> float:
    clean = [value for value in values if value is not None]
    return sum(clean) / len(clean) if clean else 0.0


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return min(high, max(low, value))
