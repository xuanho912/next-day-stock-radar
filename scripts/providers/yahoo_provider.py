from __future__ import annotations

import json
import math
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo


YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range={range}&interval=1d&includePrePost=false"
US_MARKET_TIMEZONE = ZoneInfo("America/New_York")
DAILY_BAR_COMPLETE_HOUR = 16
DAILY_BAR_COMPLETE_MINUTE = 15


@dataclass
class PriceSeries:
    symbol: str
    rows: list[dict[str, Any]]
    source: str
    real_data: bool
    error: str = ""

    @property
    def latest_date(self) -> str | None:
        return self.rows[-1]["date"] if self.rows else None


def fetch_price_series(symbols: list[str], *, range_: str = "8mo", offline: bool = False) -> dict[str, PriceSeries]:
    series: dict[str, PriceSeries] = {}
    for symbol in symbols:
        if offline:
            series[symbol] = fallback_series(symbol)
            continue
        series[symbol] = fetch_yahoo_chart(symbol, range_=range_)
    return series


def fetch_yahoo_chart(symbol: str, *, range_: str = "8mo", timeout: int = 15) -> PriceSeries:
    url = YAHOO_CHART_URL.format(symbol=urllib.parse.quote(symbol), range=range_)
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        rows = _parse_yahoo_payload(payload)
        if len(rows) >= 20:
            return PriceSeries(symbol=symbol, rows=rows, source="yahoo-chart", real_data=True)
        return PriceSeries(symbol=symbol, rows=fallback_series(symbol).rows, source="fallback-too-few-yahoo-rows", real_data=False)
    except Exception as exc:  # network providers should fail closed into labeled fallback
        fallback = fallback_series(symbol)
        fallback.source = "fallback-yahoo-error"
        fallback.error = str(exc)[:180]
        return fallback


def fallback_series(symbol: str, days: int = 180) -> PriceSeries:
    seed = sum(ord(character) for character in symbol)
    start_price = 8 + (seed % 90)
    today = _date_from_iso(expected_latest_trading_date(datetime.now(timezone.utc)))
    trading_dates: list[date] = []
    current = today
    while len(trading_dates) < days:
        if current.weekday() < 5:
            trading_dates.append(current)
        current -= timedelta(days=1)
    trading_dates.reverse()
    rows: list[dict[str, Any]] = []
    price = float(start_price)
    for index, current in enumerate(trading_dates):
        drift = 0.001 + math.sin((index + seed) / 18.0) * 0.012
        shock = 0.035 if index == days - 1 and seed % 5 == 0 else 0.0
        price = max(1.2, price * (1 + drift + shock))
        span = price * (0.018 + abs(math.sin((index + seed) / 9.0)) * 0.02)
        open_ = price * (1 - drift / 2)
        high = max(open_, price) + span * 0.55
        low = min(open_, price) - span * 0.45
        volume = 1_000_000 + (seed % 17) * 230_000 + index * 9000
        if index == days - 1:
            volume *= 1.6 + (seed % 7) / 8
        rows.append(
            {
                "date": current.isoformat(),
                "open": round(open_, 4),
                "high": round(high, 4),
                "low": round(max(0.1, low), 4),
                "close": round(price, 4),
                "volume": int(volume),
            }
        )
    return PriceSeries(symbol=symbol, rows=rows, source="deterministic-fallback", real_data=False)


def expected_latest_trading_date(now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    market_now = now.astimezone(US_MARKET_TIMEZONE)
    current = market_now.date()
    daily_bar_complete = (market_now.hour, market_now.minute) >= (DAILY_BAR_COMPLETE_HOUR, DAILY_BAR_COMPLETE_MINUTE)
    if not daily_bar_complete:
        current -= timedelta(days=1)
    while current.weekday() >= 5:
        current -= timedelta(days=1)
    return current.isoformat()


def latest_available_date(series_by_symbol: dict[str, PriceSeries], symbols: list[str]) -> str | None:
    dates = [series_by_symbol[symbol].latest_date for symbol in symbols if symbol in series_by_symbol and series_by_symbol[symbol].latest_date]
    return max(dates) if dates else None


def _parse_yahoo_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    result = (payload.get("chart") or {}).get("result") or []
    if not result:
        return []
    item = result[0]
    timestamps = item.get("timestamp") or []
    quote = ((item.get("indicators") or {}).get("quote") or [{}])[0]
    rows: list[dict[str, Any]] = []
    for index, ts in enumerate(timestamps):
        try:
            open_ = quote.get("open", [])[index]
            high = quote.get("high", [])[index]
            low = quote.get("low", [])[index]
            close = quote.get("close", [])[index]
            volume = quote.get("volume", [])[index]
        except IndexError:
            continue
        if None in (open_, high, low, close):
            continue
        rows.append(
            {
                "date": datetime.fromtimestamp(ts, timezone.utc).date().isoformat(),
                "open": float(open_),
                "high": float(high),
                "low": float(low),
                "close": float(close),
                "volume": int(volume or 0),
            }
        )
    return rows


def _date_from_iso(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()
