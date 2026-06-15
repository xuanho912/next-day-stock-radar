# Wardley Strategy

## User Need

The user needs a small number of next-day speculative candidates that are:

- timely
- explainable
- executable as probability paths
- validated over time
- honest about stale, proxy, or missing data

## Value Chain

```text
Data sources -> Feature snapshots -> Market context -> Sector themes -> Candidate scoring -> Probability path -> Forecast ledger -> Dashboard -> Validation feedback
```

## Five-Step Principle

1. Question the need: every module must improve next-day high-elasticity candidate identification.
2. Delete redundancy: do not keep indicators that do not influence candidate ranking, risk, trigger, invalidation, or validation.
3. Simplify: first screen only shows candidate, direction, elasticity, risk, trigger, invalidation, and freshness.
4. Accelerate: daily after-close generation plus manual premarket refresh.
5. Automate: collect data, rank candidates, record forecasts, backfill outcomes, validate models. Do not automate trading.

## Doctrine

- Keep secrets out of the browser.
- Prefer static deployment.
- Make stale data visible.
- Keep the first screen conclusion-first.
- Validate forecasts before upgrading models.
- Remove weak signals instead of adding more noise.
- Never present proxy data as real data.

## Borrowed Strength From `market-predictor`

The stock radar keeps the broad-market project's best ideas but changes the target from index path prediction to individual-stock opportunity ranking:

- regime first, candidate second
- forward-only validation before promotion
- immutable forecast ledger
- historical analogs as evidence, not proof
- explicit missing / proxy / stale data states
- private core plus optional public static dashboard

## Wardley Boundary

Self-build core:

- candidate scoring
- market and path judgment
- trigger levels
- invalidation levels
- historical analogs
- forecast ledger
- validation framework

Outsource / integrate:

- market data
- news
- event calendars
- fundamentals
- deployment
- chart libraries

Do not self-build commodity infrastructure.

## Evolution

Early stage:

- rules-based scoring
- small watchlist
- static dashboard
- GitHub Actions schedule

Next stage:

- better news event classification
- richer short interest and options data
- historical analog candidates
- sector-relative universe expansion

Later stage:

- model registry
- challenger scorecards by regime
- separate public dashboard repo if core repo becomes private
