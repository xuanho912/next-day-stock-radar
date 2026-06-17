# Model Framework

## Baseline Model

`stock_radar_baseline_v1` is the frozen first official output model.

Score components:

- market context adjustment
- sector theme strength
- catalyst score
- price/volume structure score
- liquidity and relative volume score
- options/short squeeze score
- risk penalty

## Challenger Model

`stock_radar_challenger_strict_v1` runs in shadow mode. It applies stricter confluence caps:

- lower tolerance for stale data
- stronger penalty for weak sector confirmation
- stronger penalty for low liquidity
- social-only candidates are capped lower

It does not affect official Top Candidates.

## Promotion Rule

A Challenger cannot become Baseline unless it proves itself on future samples for 30-60 trading days and improves:

- Top candidate hit rate
- executable trigger-condition return
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

## Hard Confluence Gate

High ratings cannot be created by a weighted average alone. `signal_quality_gate` must check independent evidence sources:

- confirmed catalyst
- price structure
- volume confirmation
- sector/mainline support
- payoff quality
- current quote not failed

If catalyst, price, volume, or payoff evidence is missing, the candidate is capped at observation level even when volatility is high. High volatility is not the same as high-quality opportunity.

## Candidate Types

- next_day_upside_momentum
- oversold_bounce
- short_squeeze_candidate
- gap_continuation
- event_driven_volatility
- failed_bounce_risk
- downside_continuation
- no_edge

## Edge Status

`edge_status` is a forecast-advantage label, not a trading recommendation:

- NO_EDGE
- WATCH
- MODERATE_EDGE
- STRONG_EDGE
- HIGH_RISK_HIGH_REWARD
- AVOID

## Required Scores

Each candidate must emit:

- `elasticity_score`
- `next_day_move_probability`
- `upside_momentum_score`
- `bounce_score`
- `downside_continuation_score`
- `squeeze_score`
- `catalyst_score`
- `risk_score`
- `confluence_score`
- `quote_confirmation_score`

If real short interest or options data is missing, squeeze-related fields must be marked `proxy`.

`quote_confirmation_score` is a backend-only Finnhub quote confirmation layer. It can support or warn on an existing candidate path, but it must not replace OHLCV structure or become a standalone buy/sell signal.

## Scenario Fields

Each candidate has:

- primary_scenario
- secondary_scenario
- risk_scenario
- next_day_expected_range
- primary_probability
- secondary_probability
- risk_probability
- expected_low / expected_mid / expected_high
- base_case_price
- upside_case_price
- downside_case_price
- bounce_target_price
- failed_bounce_price
- upside_trigger_level
- downside_risk_level
- invalidation_level
- gap_fill_level
- breakout_level
- breakdown_level
- nearest_support
- nearest_resistance

These are probabilistic path points, not investment advice or trading instructions.

## User Logic Adaptation

The user-provided stock logic document is reviewed in `docs/user_logic_review.md`.

The project adopts its expectation-gap, payoff, risk-control, and invalidation-condition ideas, but does not adopt its buy/sell wording, position-sizing layer, or 20/60 day alpha target as the baseline objective. Any medium-term alpha model must run as a separate Challenger first.
