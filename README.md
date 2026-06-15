# next-day-stock-radar

中文定位：次日高弹性股票投机机会雷达。

This is a next-day speculative stock radar. It is not a long-term investing system, not an automated trading robot, and not a broker execution tool. It generates buy/sell decision support candidates for high-elasticity next-session opportunities under the current market context.

The project runs as a static pipeline:

1. GitHub Actions runs after the US market close.
2. Python scripts collect market, stock, news, event, volume and relative-strength data.
3. The engine scores candidates and records forecasts.
4. Matured forecasts are backfilled with next-day, 3-day and 5-day realized performance.
5. Static JSON is exported to `frontend/public`.
6. The static dashboard reads only local JSON files and can be deployed with GitHub Pages.

## Difference From `market-predictor`

- `market-predictor`: estimates probability paths for SPY / QQQ / IWM / DIA.
- `next-day-stock-radar`: uses the market background to rank next-day high-elasticity individual stock candidates.

## Local Run

```powershell
cd D:\Codex\next-day-stock-radar
python scripts\run_daily_radar.py
python scripts\export_static_dashboard.py
```

Open:

```text
frontend/app/index.html
```

For a local static server:

```powershell
python -m http.server 5174 -d frontend/app
```

Then open:

```text
http://127.0.0.1:5174
```

## GitHub Secrets

Configure these repository secrets:

```text
FINNHUB_API_KEY
FRED_API_KEY
```

Do not put API keys in code, README files, `.env`, frontend JSON, or `NEXT_PUBLIC_*` variables. The frontend never calls Finnhub or FRED directly.

## GitHub Pages

The workflow `.github/workflows/daily-stock-radar.yml` builds a static site and deploys it to GitHub Pages.

If the repository is private and GitHub Pages is unavailable on your plan, use one of these alternatives:

- Keep the workflow that generates `frontend/public/*.json` and download the artifact.
- Deploy the generated static site to Cloudflare Pages.
- Use a separate public dashboard repository that receives only sanitized static files.

## Main Outputs

- `frontend/public/stock-radar-dashboard.json`
- `frontend/public/top-candidates.json`
- `frontend/public/stock-forecast-records.json`
- `frontend/public/validation-scorecard.json`
- `frontend/public/stock-model-leaderboard.json`
- `outputs/daily_stock_radar_report.md`
- `outputs/stock_forecast_records.csv`
- `outputs/candidate_validation_report.md`
- `outputs/data_quality_report.md`
- `outputs/stock_model_leaderboard.md`

## Validation Discipline

The dashboard must distinguish:

- theoretical high gain
- open-buy return
- trigger-buy return
- close return
- maximum drawdown

Baseline is the official model. Challenger runs in shadow mode only and cannot affect the displayed official candidates until it proves itself on future samples.

Frozen first baseline:

```text
stock_radar_baseline_v1
```

Any new logic must run as a Challenger before it can be considered for promotion.
