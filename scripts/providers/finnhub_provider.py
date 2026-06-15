from __future__ import annotations

import json
import os
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
    profiles: dict[str, Any] = {}
    news: dict[str, Any] = {}
    errors: dict[str, str] = {}

    for symbol in symbols:
        profile, profile_error = _get_json("/stock/profile2", {"symbol": symbol, "token": api_key})
        if profile_error:
            errors[f"profile:{symbol}"] = profile_error
        profiles[symbol] = profile or {}

        news_payload, news_error = _get_json(
            "/company-news",
            {"symbol": symbol, "from": from_date.isoformat(), "to": to_date.isoformat(), "token": api_key},
        )
        if news_error:
            errors[f"news:{symbol}"] = news_error
        news[symbol] = news_payload if isinstance(news_payload, list) else []

    return {
        "configured": True,
        "available": not errors,
        "source": "finnhub",
        "profiles": profiles,
        "news": news,
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


def _missing_bundle(reason: str) -> dict[str, Any]:
    return {
        "configured": False,
        "available": False,
        "source": reason,
        "profiles": {},
        "news": {},
        "errors": {},
    }
