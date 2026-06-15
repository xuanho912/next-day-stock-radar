# Wardley Strategy

## User Need

The user needs a small number of next-day speculative opportunities that are:

- timely
- explainable
- executable
- validated over time
- honest about stale or missing data

## Value Chain

```text
Data sources -> Feature snapshots -> Market context -> Sector themes -> Candidate scoring -> Trade plan -> Forecast ledger -> Dashboard -> Validation feedback
```

## Doctrine

- Keep secrets out of the browser.
- Prefer static deployment.
- Make stale data visible.
- Keep the first screen conclusion-first.
- Validate forecasts before upgrading models.
- Remove weak signals instead of adding more noise.

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
