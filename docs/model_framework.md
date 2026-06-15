# Model Framework

## Baseline Model

`baseline_v1` is the official output model.

Score components:

- market context adjustment
- sector theme strength
- catalyst score
- price/volume structure score
- liquidity and relative volume score
- options/short squeeze score
- risk penalty

## Challenger Model

`challenger_strict_v1` runs in shadow mode. It applies stricter confluence caps:

- lower tolerance for stale data
- stronger penalty for weak sector confirmation
- stronger penalty for low liquidity
- social-only candidates are capped lower

It does not affect official Top Candidates.

## Promotion Rule

A Challenger cannot become Baseline unless it proves itself on future samples for 30-60 trading days and improves:

- Top candidate hit rate
- executable trigger-buy return
- average maximum drawdown
- performance across market regimes
- performance across sectors and candidate types

Backtest-only improvement is not enough.

## Scoring Discipline

Strong ratings are capped when:

- market is defense
- sector is weak
- catalyst is unconfirmed
- support evidence count is low
- data freshness is stale
- liquidity is weak
- social heat exists without real catalyst
- risk penalty is high

## Candidate Types

- catalyst_breakout
- earnings_momentum
- sector_leader_pull
- squeeze_setup
- gap_and_go
- reversal_reclaim
- avoid_social_only
- avoid_low_liquidity

## Scenario Fields

Each candidate has:

- primary_scenario
- secondary_scenario
- risk_scenario
- next_day_expected_range
- upside_trigger_level
- invalidation_level
- gap_fill_level
- recent_support
- recent_resistance
