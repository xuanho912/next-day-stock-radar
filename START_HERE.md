# START HERE

## What This Project Does

`next-day-stock-radar` answers one question:

```text
Under today's market context, which stocks are most likely to attract short-term speculative capital tomorrow, and under what conditions does the probability path become confirmed or invalidated?
```

It should not output a long list just to look professional. A stock must have true confluence across market context, sector theme, catalyst, price/volume structure, liquidity, and risk.

The page must always show:

```text
这是次日高弹性概率雷达，不是投资建议或交易指令。
```

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

- tomorrow high-elasticity opportunity status
- strongest candidate
- strongest direction
- market speculation background
- whether the environment is suitable for speculative screening
- risk level and warning
- data freshness
- model validation status
- Top Candidates table

## Five-Step Product Rule

1. Question the need: every module must improve next-day high-elasticity candidate identification.
2. Delete redundancy: remove indicators that do not affect ranking, risk, trigger, invalidation, or validation.
3. Simplify: first screen only shows candidate, direction, elasticity, risk, trigger, invalidation, and freshness.
4. Accelerate: daily after-close run plus manual premarket refresh.
5. Automate: collect data, rank candidates, record forecasts, backfill results, validate models. Do not automate trading.

## Upgrade Rule

Do not upgrade a new model because a backtest looks good. New models must run as Challenger for 30-60 future trading days and beat Baseline on hit rate, executable return, and drawdown.
