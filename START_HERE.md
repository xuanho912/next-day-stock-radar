# START HERE

## What This Project Does

`next-day-stock-radar` answers one question:

```text
Under today's market context, which stocks are most likely to attract short-term speculative capital tomorrow, and under what conditions are they actionable?
```

It should not output a long list just to look professional. A stock must have true confluence across market context, sector theme, catalyst, price/volume structure, liquidity, and risk.

## First Setup

1. Create a GitHub repository named `next-day-stock-radar`.
2. Add GitHub Secrets:
   - `FINNHUB_API_KEY`
   - `FRED_API_KEY`
3. Enable GitHub Pages:
   - Source: GitHub Actions
4. Run the workflow manually once:
   - Actions -> Daily Stock Radar -> Run workflow

## Local Smoke Test

```powershell
python scripts\run_daily_radar.py --offline
python scripts\export_static_dashboard.py
```

The offline mode uses deterministic fallback data. It is only for smoke tests and must be labeled as fallback / not fully validated.

## Daily Use

Open the generated dashboard after the workflow finishes. First screen should show:

- whether tomorrow has high-elasticity opportunity
- current market speculation background
- strongest candidates
- strongest candidate type
- risk level
- data freshness
- model validation status

## Upgrade Rule

Do not upgrade a new model because a backtest looks good. New models must run as Challenger for 30-60 future trading days and beat Baseline on hit rate, executable return, and drawdown.
