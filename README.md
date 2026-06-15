# next-day-stock-radar

中文定位：次日高弹性股票投机机会雷达。

这是一个次日高弹性概率雷达，不是投资建议或交易指令。它不是长期投资系统，不是自动交易机器人，也不是券商下单工具。项目目标是每天在大盘背景下筛选“明天可能出现高弹性行情”的候选股票，并给出概率路径、触发价、失效价、支持证据、冲突证据和验证状态。

## Pipeline

1. GitHub Actions 在美股收盘后运行，也支持手动刷新。
2. Python 脚本收集市场、个股、新闻、事件、成交量和相对强弱数据。
3. 引擎生成市场路径、板块背景、候选评分和候选排序。
4. 每天写入 forecast ledger，后续回填次日 / 3 日 / 5 日真实表现。
5. 输出静态 JSON 到 `frontend/public`。
6. 静态 Dashboard 只读取本地 JSON，可部署到 GitHub Pages 或 Cloudflare Pages。

## Difference From `market-predictor`

- `market-predictor`: 判断 SPY / QQQ / IWM / DIA 的大盘概率路径。
- `next-day-stock-radar`: 在大盘背景下筛选次日高弹性个股候选。

## Reused Lessons From `market-predictor`

- Use broad-market regime first: SPY / QQQ / IWM / DIA, VIX, rates, credit and risk-on/risk-off proxies.
- Keep fallback and proxy data visibly labeled.
- Record forecasts before outcomes mature; only backfill realized fields later.
- Treat historical analogs as support evidence, not proof.
- Keep Baseline frozen while Challenger runs forward-only in shadow mode.
- Prefer a static GitHub Pages style dashboard with no frontend API keys.
- If the core repo is private, publish only sanitized static dashboard files to a separate public repo.

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

Offline smoke test:

```powershell
python scripts\run_daily_radar.py --offline
python scripts\export_static_dashboard.py
```

Offline output is deterministic fallback data. It must remain labeled as fallback / not fully validated.

## GitHub Secrets

Configure these repository secrets:

```text
FINNHUB_API_KEY
FRED_API_KEY
```

Do not put API keys in code, README files, `.env`, frontend JSON, or `NEXT_PUBLIC_*` variables. The frontend never calls Finnhub or FRED directly.

## GitHub Actions

Workflow:

```text
.github/workflows/daily-stock-radar.yml
```

Triggers:

- `schedule`: after US market close.
- `workflow_dispatch`: manual refresh, including premarket checks.

Required output fields include:

- `latest_data_date`
- `expected_latest_trading_date`
- `data_freshness_status`
- stale warning
- provider status
- candidate count
- top candidates
- validation status

If the data is stale, missing, or fallback-only, the page must show a warning and cannot pretend it is a fresh forecast.

## GitHub Pages

The workflow builds a static site and deploys it to GitHub Pages.

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

## Safety Boundary

Forbidden:

- no automated trading
- no order placement
- no directional order wording as an instruction
- no position sizing advice
- no guaranteed rise/fall claims
- no low-liquidity junk-stock promotion
- no fake data
- no treating proxy data as real data
- no API keys in frontend or repo files
- no “confirmed alpha” language before forward validation

All trigger levels are probability path markers, not trade instructions.

## Validation Discipline

The dashboard must distinguish:

- theoretical high gain
- open-entry return
- trigger-condition return
- close return
- maximum drawdown

Baseline is the official model. Challenger runs in shadow mode only and cannot affect the displayed official candidates until it proves itself on future samples.

Frozen first baseline:

```text
stock_radar_baseline_v1
```

Any new logic must run as a Challenger for 30-60 future trading days before promotion.
