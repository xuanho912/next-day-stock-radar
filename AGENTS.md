# AGENTS

## Project Role

This project is a next-day speculative stock candidate radar. Agents working on it should protect the core product principle:

```text
Precision and validation matter more than professional-looking complexity.
```

## Non-Negotiable Rules

- Do not expose API keys.
- Do not commit `.env`.
- Do not make frontend code call Finnhub, FRED, or paid data providers directly.
- Do not label fallback or stale data as fresh.
- Do not promote Challenger models without future-sample validation.
- Do not rank a stock highly only because of social-media heat.
- Do not hide conflicting evidence.

## Architecture

- `scripts/providers/`: data collection only.
- `scripts/market_context_provider.py`: broad market path and risk context.
- `scripts/stock_prediction_engine.py`: candidate feature and scenario construction.
- `scripts/candidate_ranking_engine.py`: scoring, rating, and trade-plan generation.
- `scripts/forecast_validation_engine.py`: immutable forecast ledger and outcome validation.
- `scripts/export_static_dashboard.py`: writes frontend-readable JSON and static files.
- `frontend/app`: static dashboard.
- `frontend/public`: generated JSON snapshots.

## Output Style

The first screen must show conclusions before details. Detailed reasoning, data quality, and validation live lower on the page.
