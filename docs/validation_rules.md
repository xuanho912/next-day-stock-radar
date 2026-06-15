# Validation Rules

## Forecast Ledger

Forecast records are immutable by `forecast_id`.

Allowed after creation:

- backfill next-day OHLC
- backfill 3-day and 5-day returns
- update outcome status
- update hit / drawdown / executable result fields

Not allowed after creation:

- changing rank
- changing score
- changing rating
- changing reason
- changing trigger or invalidation level

## Required Metrics

- pending forecasts
- completed next-day forecasts
- Top 5 hit rate
- Top 10 hit rate
- average next-day high gain
- average next-day close gain
- average maximum drawdown
- open-buy return
- trigger-buy return
- profit factor
- by market regime
- by sector
- by candidate type
- baseline vs challenger

## Hit Definition

A next-day candidate is a hit when:

- entry was triggered, and
- target low bound was reached before invalidation, or
- next-day high gain exceeded the candidate target low bound.

The dashboard must not judge only by theoretical high gain.

## Evidence Levels

- `not_yet_validated`: fewer than 20 completed samples
- `early_evidence`: 20-59 completed samples
- `validated`: 60+ samples and high-confluence buckets outperform ordinary buckets

## Anti-Overfitting

Do not promote any model based on historical backtests alone. Future-sample shadow validation is required.
