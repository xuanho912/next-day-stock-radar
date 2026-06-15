# Cloud Deployment

## Goal

The radar must work like an always-available static dashboard:

```text
GitHub Actions pulls real data -> scripts generate JSON -> GitHub Pages serves the dashboard
```

The user should not need to run scripts manually each day.

## Core Repo GitHub Pages

1. Create `xuanho912/next-day-stock-radar`.
2. Push this project to the repo.
3. Add repository secrets:
   - `FINNHUB_API_KEY`
   - `FRED_API_KEY`
4. Enable Pages:
   - Source: GitHub Actions
5. Run:
   - Actions -> Daily Stock Radar -> Run workflow

Expected URL:

```text
https://xuanho912.github.io/next-day-stock-radar/
```

## Real Data vs Offline Data

Production Actions run:

```text
python scripts/run_daily_radar.py
python scripts/export_static_dashboard.py
```

That is the real-data path. It uses Yahoo chart data and optional Finnhub / FRED secrets.

Local smoke tests may run:

```text
python scripts/run_daily_radar.py --offline
```

Offline output is never treated as fresh. The dashboard must show `fallback_only` and stale warning.

## Public Dashboard Repo Pattern

If the core repository is private, publish only sanitized static files to:

```text
xuanho912/next-day-stock-radar-dashboard
```

Expected URL:

```text
https://xuanho912.github.io/next-day-stock-radar-dashboard/
```

Configure the core repository:

Variables:

```text
PUBLIC_DASHBOARD_REPO=xuanho912/next-day-stock-radar-dashboard
PUBLIC_DASHBOARD_BRANCH=main
```

Secret:

```text
DASHBOARD_DEPLOY_TOKEN
```

The token should be fine-grained and limited to `Contents: read/write` on the public dashboard repository only.

## Manual Refresh

Use `workflow_dispatch` when you need a premarket or intraday refresh. The page should still show the latest data date and provider status, so a failed refresh cannot masquerade as a fresh forecast.

## Important Boundary

This dashboard is for next-day probability paths and candidate monitoring. It is not an order system and does not place trades.
