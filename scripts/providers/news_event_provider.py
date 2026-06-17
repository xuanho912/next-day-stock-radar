from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


EVENT_RULES: list[dict[str, Any]] = [
    {
        "event_type": "earnings_momentum",
        "keywords": ("earnings", "results", "eps", "revenue", "guidance", "outlook", "raises forecast", "raises guidance"),
        "weight": 18,
        "strong": True,
    },
    {
        "event_type": "regulatory_catalyst",
        "keywords": ("fda", "approval", "approved", "clearance", "phase 3", "clinical trial", "trial data"),
        "weight": 18,
        "strong": True,
    },
    {
        "event_type": "confirmed_business_catalyst",
        "keywords": ("contract", "order", "award", "deal", "partnership", "strategic collaboration", "supply agreement"),
        "weight": 15,
        "strong": True,
    },
    {
        "event_type": "mna_or_strategic_review",
        "keywords": ("acquire", "acquisition", "merger", "buyout", "takeover", "strategic review"),
        "weight": 16,
        "strong": True,
    },
    {
        "event_type": "analyst_upgrade",
        "keywords": ("upgrade", "upgrades", "price target raised", "raises price target", "initiates at buy"),
        "weight": 10,
        "strong": False,
    },
    {
        "event_type": "product_or_launch",
        "keywords": ("launch", "unveils", "announces availability", "new product"),
        "weight": 8,
        "strong": False,
    },
    {
        "event_type": "theme_buzz",
        "keywords": ("ai", "artificial intelligence", "nuclear", "crypto", "quantum", "space"),
        "weight": 4,
        "strong": False,
    },
]

RISK_RULES: list[dict[str, Any]] = [
    {"risk_type": "dilution_or_offering", "keywords": ("offering", "share sale", "registered direct", "atm program", "dilution"), "weight": 24},
    {"risk_type": "investigation_or_lawsuit", "keywords": ("investigation", "lawsuit", "class action", "subpoena", "sec charges"), "weight": 18},
    {"risk_type": "downgrade_or_miss", "keywords": ("downgrade", "misses", "missed estimates", "cuts guidance", "lowered guidance"), "weight": 16},
    {"risk_type": "delay_or_rejection", "keywords": ("delay", "delayed", "rejected", "complete response letter", "halt"), "weight": 16},
    {"risk_type": "bankruptcy_or_delisting", "keywords": ("bankruptcy", "chapter 11", "delisting", "going concern"), "weight": 28},
]


def build_news_events(symbols: list[str], finnhub_bundle: dict[str, Any]) -> dict[str, Any]:
    news_by_symbol = finnhub_bundle.get("news") or {}
    earnings_by_symbol = _earnings_by_symbol(finnhub_bundle.get("earnings_calendar") or {})
    sentiment_by_symbol = finnhub_bundle.get("sentiment") or {}
    events: dict[str, Any] = {}
    for symbol in symbols:
        rows = news_by_symbol.get(symbol) or []
        events[symbol] = _score_symbol_news(
            symbol,
            rows[:18],
            earnings_by_symbol.get(symbol) or [],
            sentiment_by_symbol.get(symbol) or {},
        )
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provider_available": bool(finnhub_bundle.get("available")),
        "provider_source": finnhub_bundle.get("source"),
        "symbols": events,
    }


def _score_symbol_news(
    symbol: str,
    rows: list[dict[str, Any]],
    earnings_events: list[dict[str, Any]],
    sentiment: dict[str, Any],
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    support_events: list[dict[str, Any]] = []
    risk_events: list[dict[str, Any]] = []
    score = 38.0
    risk = 0.0
    strong_event_count = 0
    concrete_event_types: set[str] = set()

    for item in rows:
        headline = str(item.get("headline") or "")[:260]
        summary = str(item.get("summary") or "")[:500]
        text = f"{headline} {summary}".lower()
        published_at = _published_at(item)
        age_hours = _age_hours(now, published_at)
        recency = _recency_multiplier(age_hours)
        best_event = _best_event(text)
        if best_event:
            event_score = round(float(best_event["weight"]) * recency, 2)
            score += event_score
            if best_event["strong"]:
                strong_event_count += 1
                concrete_event_types.add(best_event["event_type"])
            support_events.append(
                {
                    "event_type": best_event["event_type"],
                    "headline": headline,
                    "source": item.get("source") or "",
                    "url": item.get("url") or "",
                    "published_at": published_at.isoformat() if published_at else None,
                    "age_hours": round(age_hours, 2) if age_hours is not None else None,
                    "score_contribution": event_score,
                    "strong": bool(best_event["strong"]),
                }
            )
        best_risk = _best_risk(text)
        if best_risk:
            risk_score = round(float(best_risk["weight"]) * recency, 2)
            risk += risk_score
            risk_events.append(
                {
                    "risk_type": best_risk["risk_type"],
                    "headline": headline,
                    "source": item.get("source") or "",
                    "url": item.get("url") or "",
                    "published_at": published_at.isoformat() if published_at else None,
                    "age_hours": round(age_hours, 2) if age_hours is not None else None,
                    "score_contribution": risk_score,
                }
            )

    earnings_boost, earnings_risk, earnings_details = _earnings_calendar_signal(earnings_events)
    score += earnings_boost
    risk += earnings_risk
    support_events.extend(earnings_details.get("supporting_events", []))
    risk_events.extend(earnings_details.get("risk_events", []))

    sentiment_boost, sentiment_detail = _sentiment_signal(sentiment)
    score += sentiment_boost

    if support_events and not strong_event_count:
        score = min(score, 54)
    if not support_events:
        score = min(score, 42)
    if risk_events and not strong_event_count:
        score = min(score, 48)

    catalyst_score = max(0, min(100, score - risk * 0.42))
    risk_event_score = max(0, min(100, risk))
    primary_support = _primary_support_event(support_events)
    catalyst_type = primary_support.get("event_type") if primary_support else "no_recent_confirmed_news"
    catalyst_quality = _catalyst_quality(catalyst_score, support_events, risk_events, strong_event_count)

    return {
        "symbol": symbol,
        "catalyst_score": round(catalyst_score, 2),
        "risk_event_score": round(risk_event_score, 2),
        "headline_count": len(rows),
        "primary_headline": primary_support.get("headline", "") if primary_support else (str(rows[0].get("headline") or "")[:220] if rows else ""),
        "primary_event_type": catalyst_type,
        "primary_event_source": primary_support.get("source", "") if primary_support else "",
        "primary_event_age_hours": primary_support.get("age_hours") if primary_support else None,
        "catalyst_type": catalyst_type,
        "catalyst_quality": catalyst_quality,
        "recent_confirmed_catalyst": catalyst_quality in {"confirmed", "strong"},
        "strong_event_count": strong_event_count,
        "concrete_event_types": sorted(concrete_event_types),
        "supporting_events": support_events[:8],
        "risk_events": risk_events[:8],
        "sentiment_signal": sentiment_detail,
        "supporting_headlines": [event.get("headline", "") for event in support_events[:5]],
        "conflicting_headlines": [event.get("headline", "") for event in risk_events[:5]],
        "news_data_status": "available" if rows else "missing",
    }


def _best_event(text: str) -> dict[str, Any] | None:
    matches = []
    for rule in EVENT_RULES:
        if any(keyword in text for keyword in rule["keywords"]):
            matches.append(rule)
    if not matches:
        return None
    return max(matches, key=lambda item: (bool(item["strong"]), int(item["weight"])))


def _best_risk(text: str) -> dict[str, Any] | None:
    matches = []
    for rule in RISK_RULES:
        if any(keyword in text for keyword in rule["keywords"]):
            matches.append(rule)
    if not matches:
        return None
    return max(matches, key=lambda item: int(item["weight"]))


def _published_at(item: dict[str, Any]) -> datetime | None:
    raw = item.get("datetime")
    try:
        if raw:
            return datetime.fromtimestamp(float(raw), tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None
    return None


def _age_hours(now: datetime, published_at: datetime | None) -> float | None:
    if not published_at:
        return None
    return max(0.0, (now - published_at).total_seconds() / 3600)


def _recency_multiplier(age_hours: float | None) -> float:
    if age_hours is None:
        return 0.72
    if age_hours <= 24:
        return 1.25
    if age_hours <= 72:
        return 1.0
    if age_hours <= 168:
        return 0.68
    return 0.40


def _earnings_by_symbol(calendar: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    rows = calendar.get("earningsCalendar") if isinstance(calendar, dict) else []
    result: dict[str, list[dict[str, Any]]] = {}
    if not isinstance(rows, list):
        return result
    for item in rows:
        symbol = str(item.get("symbol") or "").upper()
        if not symbol:
            continue
        result.setdefault(symbol, []).append(item)
    return result


def _earnings_calendar_signal(events: list[dict[str, Any]]) -> tuple[float, float, dict[str, list[dict[str, Any]]]]:
    if not events:
        return 0.0, 0.0, {"supporting_events": [], "risk_events": []}
    support: list[dict[str, Any]] = []
    risk: list[dict[str, Any]] = []
    boost = 0.0
    risk_score = 0.0
    today = datetime.now(timezone.utc).date()
    for event in events[:3]:
        date_text = str(event.get("date") or "")
        try:
            event_date = datetime.fromisoformat(date_text).date()
        except ValueError:
            event_date = today
        days_until = (event_date - today).days
        if -1 <= days_until <= 2:
            boost += 8
            risk_score += 8
            payload = {
                "event_type": "earnings_calendar",
                "headline": f"Earnings calendar event on {date_text}",
                "source": "finnhub_earnings_calendar",
                "url": "",
                "published_at": None,
                "age_hours": None,
                "score_contribution": 8,
                "strong": False,
                "days_until": days_until,
            }
            support.append(payload)
            risk.append({**payload, "risk_type": "earnings_gap_risk"})
    return boost, risk_score, {"supporting_events": support, "risk_events": risk}


def _sentiment_signal(sentiment: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    if not sentiment:
        return 0.0, {"status": "missing"}
    company_score = _number(sentiment.get("companyNewsScore"))
    bullish = _number(sentiment.get("bullishPercent"))
    bearish = _number(sentiment.get("bearishPercent"))
    boost = 0.0
    if company_score is not None and company_score >= 0.65:
        boost += 4
    if bullish is not None and bearish is not None and bullish - bearish >= 0.18:
        boost += 3
    return boost, {
        "status": "available",
        "company_news_score": company_score,
        "bullish_percent": bullish,
        "bearish_percent": bearish,
        "score_contribution": round(boost, 2),
    }


def _primary_support_event(events: list[dict[str, Any]]) -> dict[str, Any]:
    if not events:
        return {}
    return max(
        events,
        key=lambda item: (
            1 if item.get("strong") else 0,
            float(item.get("score_contribution") or 0),
            -float(item.get("age_hours") or 9999),
        ),
    )


def _catalyst_quality(score: float, support_events: list[dict[str, Any]], risk_events: list[dict[str, Any]], strong_count: int) -> str:
    if not support_events:
        return "missing"
    if risk_events and score < 58:
        return "conflicted"
    if strong_count >= 1 and score >= 72:
        return "strong"
    if strong_count >= 1 and score >= 60:
        return "confirmed"
    if score >= 52:
        return "weak"
    return "unconfirmed"


def _number(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
