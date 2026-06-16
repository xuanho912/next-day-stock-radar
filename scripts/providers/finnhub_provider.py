from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any


BASE_URL = "https://finnhub.io/api/v1"


def fetch_finnhub_bundle(symbols: list[str], *, offline: bool = False) -> dict[str, Any]:
    api_key = os.getenv("FINNHUB_API_KEY", "").strip()
    if offline:
        return _missing_bundle("offline_mode")
    if not api_key:
        return _missing_bundle("missing_secret")

    to_date = datetime.now(timezone.utc).date()
    from_date = to_date - timedelta(days=7)
    candle_from = int(time.mktime((to_date - timedelta(days=220)).timetuple()))
    candle_to = int(time.mktime(to_date.timetuple()))
    profiles: dict[str, Any] = {}
    quotes: dict[str, Any] = {}
    candles: dict[str, Any] = {}
    news: dict[str, Any] = {}
    sentiment: dict[str, Any] = {}
    errors: dict[str, str] = {}

    for symbol in symbols:
        profile, profile_error = _get_json("/stock/profile2", {"symbol": symbol, "token": api_key})
        profiles[symbol] = profile or {}
        if profile_error:
            errors[f"profile:{symbol}"] = profile_error

        quote, quote_error = _get_json("/quote", {"symbol": symbol, "token": api_key})
        quotes[symbol] = quote or {}
        if quote_error:
            errors[f"quote:{symbol}"] = quote_error

        candle, candle_error = _get_json(
            "/stock/candle",
            {"symbol": symbol, "resolution": "D", "from": str(candle_from), "to": str(candle_to), "token": api_key},
        )
        candles[symbol] = candle or {"status": "missing"}
        if candle_error:
            errors[f"candle:{symbol}"] = candle_error

        news_payload, news_error = _get_json(
            "/company-news",
            {"symbol": symbol, "from": from_date.isoformat(), "to": to_date.isoformat(), "token": api_key},
        )
        news[symbol] = news_payload if isinstance(news_payload, list) else []
        if news_error:
            errors[f"news:{symbol}"] = news_error

        sentiment_payload, sentiment_error = _get_json("/news-sentiment", {"symbol": symbol, "token": api_key})
        sentiment[symbol] = sentiment_payload or {}
        if sentiment_error:
            errors[f"sentiment:{symbol}"] = sentiment_error

    market_news, market_news_error = _get_json("/news", {"category": "general", "token": api_key})
    earnings_calendar, earnings_error = _get_json(
        "/calendar/earnings",
        {"from": to_date.isoformat(), "to": (to_date + timedelta(days=7)).isoformat(), "token": api_key},
    )
    economic_calendar, economic_error = _get_json("/calendar/economic", {"token": api_key})
    if market_news_error:
        errors["market_news"] = market_news_error
    if earnings_error:
        errors["earnings_calendar"] = earnings_error
    if economic_error:
        errors["economic_calendar"] = economic_error

    optional_data_status = {
        "quote": "available" if _symbol_endpoint_available(errors, "quote", symbols) else "missing",
        "ohlcv_candle_fallback": "available" if _symbol_endpoint_available(errors, "candle", symbols) else "missing",
        "company_news": "available" if _symbol_endpoint_available(errors, "news", symbols) else "missing",
        "market_news": "available" if isinstance(market_news, list) else "missing",
        "earnings_calendar": "available" if earnings_calendar else "missing",
        "economic_calendar": "available" if economic_calendar else "missing",
        "sentiment": "available" if _symbol_endpoint_available(errors, "sentiment", symbols) else "missing",
    }
    core_available = optional_data_status["quote"] == "available" and any(
        optional_data_status[key] == "available"
        for key in ("company_news", "market_news", "earnings_calendar", "sentiment")
    )
    availability_status = "available" if core_available and not errors else "partial" if core_available else "missing"

    return {
        "configured": True,
        "available": core_available,
        "core_available": core_available,
        "availability_status": availability_status,
        "source": "finnhub",
        "profiles": profiles,
        "quotes": quotes,
        "candles": candles,
        "news": news,
        "market_news": market_news if isinstance(market_news, list) else [],
        "earnings_calendar": earnings_calendar or {},
        "economic_calendar": economic_calendar or {},
        "sentiment": sentiment,
        "optional_data_status": optional_data_status,
        "errors": errors,
    }


def _get_json(path: str, params: dict[str, str], timeout: int = 15) -> tuple[Any, str | None]:
    url = f"{BASE_URL}{path}?{urllib.parse.urlencode(params)}"
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8")), None
    except Exception as exc:
        return None, str(exc)[:180]


def _symbol_endpoint_available(errors: dict[str, str], prefix: str, symbols: list[str]) -> bool:
    if not symbols:
        return False
    return any(f"{prefix}:{symbol}" not in errors for symbol in symbols)


def _missing_bundle(reason: str) -> dict[str, Any]:
    return {
        "configured": False,
        "available": False,
        "core_available": False,
        "availability_status": "missing",
        "source": reason,
        "profiles": {},
        "quotes": {},
        "candles": {},
        "news": {},
        "market_news": [],
        "earnings_calendar": {},
        "economic_calendar": {},
        "sentiment": {},
        "optional_data_status": {
            "quote": "missing",
            "ohlcv_candle_fallback": "missing",
            "company_news": "missing",
            "market_news": "missing",
            "earnings_calendar": "missing",
            "economic_calendar": "missing",
            "sentiment": "missing",
        },
        "errors": {},
    }
