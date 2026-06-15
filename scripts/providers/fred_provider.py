from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from typing import Any


FRED_URL = "https://api.stlouisfed.org/fred/series/observations"
DEFAULT_SERIES = {
    "DGS10": "ten_year_yield",
    "DGS2": "two_year_yield",
    "DGS3MO": "three_month_yield",
    "BAMLH0A0HYM2": "high_yield_oas",
}


def fetch_fred_bundle(*, offline: bool = False) -> dict[str, Any]:
    api_key = os.getenv("FRED_API_KEY", "").strip()
    if offline:
        return _missing_bundle("offline_mode")
    if not api_key:
        return _missing_bundle("missing_secret")
    observation_start = (datetime.utcnow().date() - timedelta(days=520)).isoformat()
    series: dict[str, Any] = {}
    errors: dict[str, str] = {}
    for series_id, name in DEFAULT_SERIES.items():
        payload, error = _fetch_series(series_id, api_key, observation_start)
        if error:
            errors[series_id] = error
        series[name] = payload
    return {
        "configured": True,
        "available": not errors,
        "source": "fred-api",
        "series": series,
        "errors": errors,
    }


def _fetch_series(series_id: str, api_key: str, observation_start: str) -> tuple[list[dict[str, Any]], str | None]:
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "observation_start": observation_start,
    }
    try:
        request = urllib.request.Request(f"{FRED_URL}?{urllib.parse.urlencode(params)}", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
        rows = []
        for row in payload.get("observations", []):
            value = row.get("value")
            if value in (None, "."):
                continue
            rows.append({"date": row.get("date"), "value": float(value)})
        return rows, None
    except Exception as exc:
        return [], str(exc)[:180]


def _missing_bundle(reason: str) -> dict[str, Any]:
    return {
        "configured": False,
        "available": False,
        "source": reason,
        "series": {},
        "errors": {},
    }
