from __future__ import annotations

from typing import Any


def build_fundamental_snapshot(symbols: list[str], finnhub_bundle: dict[str, Any]) -> dict[str, Any]:
    profiles = finnhub_bundle.get("profiles") or {}
    snapshot: dict[str, Any] = {}
    for symbol in symbols:
        profile = profiles.get(symbol) or {}
        snapshot[symbol] = {
            "symbol": symbol,
            "company_name": profile.get("name") or "",
            "market_cap": profile.get("marketCapitalization"),
            "share_outstanding": profile.get("shareOutstanding"),
            "exchange": profile.get("exchange") or "",
            "industry": profile.get("finnhubIndustry") or "",
            "provider_available": bool(profile),
        }
    return {
        "provider_available": bool(finnhub_bundle.get("available")),
        "symbols": snapshot,
    }
