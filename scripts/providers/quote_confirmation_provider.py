from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def build_quote_snapshots(symbols: list[str], finnhub_bundle: dict[str, Any]) -> dict[str, Any]:
    quotes = finnhub_bundle.get("quotes") or {}
    snapshots: dict[str, Any] = {}
    available_count = 0
    for symbol in symbols:
        snapshot = _quote_snapshot(symbol, quotes.get(symbol) or {})
        snapshots[symbol] = snapshot
        if snapshot["provider_status"] == "available":
            available_count += 1
    return {
        "version": "quote_snapshots_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provider": "finnhub",
        "provider_available": bool(finnhub_bundle.get("available")),
        "available_count": available_count,
        "missing_count": max(0, len(symbols) - available_count),
        "symbols": snapshots,
    }


def _quote_snapshot(symbol: str, quote: dict[str, Any]) -> dict[str, Any]:
    current = _number(quote.get("c"))
    previous_close = _number(quote.get("pc"))
    timestamp = _timestamp(quote.get("t"))
    change_pct = _number(quote.get("dp"))
    provider_status = "available" if current and current > 0 and previous_close and previous_close > 0 else "missing"
    if change_pct is None and current and previous_close:
        change_pct = (current / previous_close - 1) * 100
    return {
        "symbol": symbol,
        "provider_status": provider_status,
        "current_price": round(current, 4) if current is not None else None,
        "previous_close": round(previous_close, 4) if previous_close is not None else None,
        "day_open": _rounded(quote.get("o")),
        "day_high": _rounded(quote.get("h")),
        "day_low": _rounded(quote.get("l")),
        "absolute_change": _rounded(quote.get("d")),
        "change_pct": round(change_pct / 100, 5) if change_pct is not None else None,
        "quote_timestamp": timestamp,
        "source": "finnhub_quote" if provider_status == "available" else "missing",
        "note": "Finnhub quote is collected in backend Actions and exported as static JSON; no frontend API key is used.",
    }


def _timestamp(value: Any) -> str | None:
    number = _number(value)
    if not number or number <= 0:
        return None
    return datetime.fromtimestamp(number, timezone.utc).isoformat()


def _rounded(value: Any) -> float | None:
    number = _number(value)
    return round(number, 4) if number is not None else None


def _number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number
