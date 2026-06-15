# Data Sources

## Provider Boundary

All provider calls run in Python scripts during GitHub Actions. The frontend reads only generated static JSON.

## Supported Secrets

- `FINNHUB_API_KEY`
- `FRED_API_KEY`

## Providers

### Yahoo Chart API

Used for public OHLCV price data, relative volume, price structure, support/resistance, and benchmark context.

### Finnhub

Used when `FINNHUB_API_KEY` is configured:

- company profile
- company news
- quote snapshots
- basic financial metrics when available

### FRED

Used when `FRED_API_KEY` is configured:

- interest-rate and macro-risk context

### Fallback Data

Fallback data is allowed only for local smoke tests and must be labeled. Fallback data cannot be presented as a fresh validated forecast.

## Data Freshness Fields

Every run exports:

- `latest_data_date`
- `expected_latest_trading_date`
- `data_freshness_status`
- `stale_warning`
- `provider_status`
- `candidate_count`
- `validation_status`

## Point-In-Time Rule

Features must only use information available at or before the forecast timestamp.

Outcome fields must be backfilled only after the relevant horizon has matured.
