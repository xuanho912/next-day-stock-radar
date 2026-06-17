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
- Do not label fallback, proxy, missing, or stale data as fresh.
- Do not promote Challenger models without future-sample validation.
- Do not rank a stock highly only because of social-media heat.
- Do not hide conflicting evidence.
- Do not implement automated trading.
- Do not place orders.
- Do not write directional order instructions.
- Do not write position-size advice.
- Do not claim guaranteed rise or fall.
- Do not present historical backtests as confirmed alpha.

Required public disclaimer:

```text
这是次日高弹性概率雷达，不是投资建议或交易指令。
```

## Architecture

- `scripts/providers/`: data collection only.
- `scripts/market_context_provider.py`: broad market path and risk context.
- `scripts/stock_prediction_engine.py`: candidate feature and scenario construction.
- `scripts/candidate_ranking_engine.py`: scoring, rating, and path-plan generation.
- `scripts/forecast_validation_engine.py`: immutable forecast ledger and outcome validation.
- `scripts/radar_agent_review.py`: agency-style specialist review and quality gates.
- `scripts/export_static_dashboard.py`: writes frontend-readable JSON and static files.
- `frontend/app`: static dashboard.
- `frontend/public`: generated JSON snapshots.

## Agency Review Layer

The project adapts `msitarzewski/agency-agents` as a local review method, not as a runtime dependency.

- Agent roles are defined in `config/radar_agents.json`.
- The workflow is documented in `docs/agent_agency_workflow.md`.
- Every daily run writes `frontend/public/radar-agent-review.json` and `outputs/radar_agent_review.md`.
- The agency review must stay deterministic, auditable, and free of API keys.
- The review layer may downgrade or warn; it must not produce buy/sell/position instructions.

## Output Style

The first screen is a radar cockpit, not a research log. It must show:

- Command Center summary
- strongest candidate
- strongest direction
- market background
- screening suitability
- risk warning
- data freshness
- Top Candidates table

Detailed reasoning, data quality, historical analogs, and validation live lower on the page.

## Wardley Boundary

Self-build:

- candidate scoring
- market/path judgment
- trigger and invalidation levels
- historical analogs
- forecast ledger
- validation framework

Use providers or libraries for:

- market data
- news
- calendars
- fundamentals
- deployment
- charts

Do not self-build commodity infrastructure.
