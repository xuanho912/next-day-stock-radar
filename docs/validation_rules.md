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

## Required Forecast Fields

Each daily candidate record must include:

- `forecast_id`
- `forecast_date`
- `model_version`
- `ticker`
- `candidate_type`
- `edge_status`
- `elasticity_score`
- `confluence_score`
- `catalyst_score`
- `risk_score`
- `primary_scenario`
- `primary_probability`
- `expected_range`
- `trigger_levels`
- `market_context`
- `supporting_evidence`
- `conflicting_evidence`
- `actual_next_day_return`
- `actual_3d_return`
- `actual_5d_return`
- `range_hit`
- `primary_hit`
- `status`

This is not a trade record and not a PnL ledger.

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
- top 10 candidates average next-day volatility
- top 10 candidates next-day direction hit rate
- range hit rate
- primary scenario hit rate
- high confluence vs low confluence
- catalyst candidates vs no-catalyst candidates
- high-risk candidates realized volatility

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

## Model Leaderboard

The project exports:

- `outputs/stock_model_leaderboard.md`
- `frontend/public/stock-model-leaderboard.json`

The first baseline is `stock_radar_baseline_v1`.

Sample-insufficient models must display `not_yet_validated`. No model may be called high precision without forward validation.
