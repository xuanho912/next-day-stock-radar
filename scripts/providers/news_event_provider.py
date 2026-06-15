from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


POSITIVE_KEYWORDS = {
    "earnings": 12,
    "beat": 10,
    "raises": 12,
    "guidance": 10,
    "approval": 14,
    "contract": 14,
    "order": 12,
    "partnership": 8,
    "upgrade": 10,
    "launch": 8,
    "fda": 10,
    "ai": 6,
}

RISK_KEYWORDS = {
    "offering": 18,
    "dilution": 20,
    "investigation": 16,
    "downgrade": 12,
    "miss": 10,
    "delay": 10,
    "sec": 10,
    "lawsuit": 14,
}


def build_news_events(symbols: list[str], finnhub_bundle: dict[str, Any]) -> dict[str, Any]:
    news_by_symbol = finnhub_bundle.get("news") or {}
    events: dict[str, Any] = {}
    for symbol in symbols:
        rows = news_by_symbol.get(symbol) or []
        events[symbol] = _score_symbol_news(symbol, rows[:12])
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provider_available": bool(finnhub_bundle.get("available")),
        "provider_source": finnhub_bundle.get("source"),
        "symbols": events,
    }


def _score_symbol_news(symbol: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "symbol": symbol,
            "catalyst_score": 35,
            "risk_event_score": 0,
            "headline_count": 0,
            "primary_headline": "",
            "catalyst_type": "no_recent_confirmed_news",
            "supporting_headlines": [],
            "conflicting_headlines": [],
        }
    support: list[str] = []
    conflict: list[str] = []
    score = 38
    risk = 0
    for item in rows:
        headline = str(item.get("headline") or item.get("summary") or "")[:220]
        text = headline.lower()
        for keyword, weight in POSITIVE_KEYWORDS.items():
            if keyword in text:
                score += weight
                support.append(headline)
                break
        for keyword, weight in RISK_KEYWORDS.items():
            if keyword in text:
                risk += weight
                conflict.append(headline)
                break
    return {
        "symbol": symbol,
        "catalyst_score": max(0, min(100, score - risk * 0.35)),
        "risk_event_score": max(0, min(100, risk)),
        "headline_count": len(rows),
        "primary_headline": support[0] if support else str(rows[0].get("headline") or "")[:220],
        "catalyst_type": _catalyst_type(support[0] if support else ""),
        "supporting_headlines": support[:5],
        "conflicting_headlines": conflict[:5],
    }


def _catalyst_type(headline: str) -> str:
    text = headline.lower()
    if "earnings" in text or "guidance" in text:
        return "earnings_momentum"
    if "contract" in text or "order" in text or "partnership" in text:
        return "confirmed_business_catalyst"
    if "approval" in text or "fda" in text:
        return "regulatory_catalyst"
    if "upgrade" in text:
        return "analyst_upgrade"
    return "news_catalyst"
