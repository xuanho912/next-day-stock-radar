# Product Definition

## Positioning

`next-day-stock-radar` is a probability dashboard for next-session high-elasticity speculative stock candidates.

It is not:

- a normal stock recommendation list
- a long-term investment system
- an automated trading robot
- a broker integration
- a page full of indicators for professional appearance
- an order instruction or position-sizing instruction

Required public disclaimer:

```text
这是次日高弹性概率雷达，不是投资建议或交易指令。
```

## Core User Question

When the user opens the dashboard after market close, they should immediately know:

- should tomorrow be attack, observe, or defend?
- where is short-term capital most likely to attack?
- which stocks deserve attention?
- what condition confirms the probability path?
- where is the invalidation level?
- which hot stocks should be avoided because data does not confirm them?

## Product Principle

Precision is greater than professional feeling.

High rank requires multi-source confluence. Missing evidence and conflicting evidence must cap ratings.

## Layers

1. Market path: attack / neutral / defense.
2. Sector theme: where capital is flowing.
3. Candidate scoring: catalyst, technical, volume/flow, sector, options/short proxy, risk.
4. Probability path plan: trigger, invalidation, target range, risk.
5. Validation: forecast records, outcome backfill, model scorecard.

## Candidate Ratings

- A+: strong confluence, primary focus.
- A: candidate requires trigger confirmation.
- B: observe, do not chase.
- C: reject.

## Candidate Pool Discipline

The radar must not become a low-quality penny-stock list.

Default pool rules:

- price greater than 2
- sufficient average dollar volume
- OTC / Pink Sheet names excluded by default
- low-liquidity names flagged `high_liquidity_risk`
- volatile small caps flagged `high_risk_high_volatility`

Risk flags must be visible in the candidate detail view.

## First Screen Hierarchy

The first screen must look like a radar cockpit, not a research log.

Order:

1. Command Center:
   - next-day high-elasticity opportunity overview
   - strongest candidate
   - strongest direction
   - current market background
   - whether the environment is suitable for speculative screening
   - risk warning
   - data freshness
   - model validation status
2. Top Candidates table:
   - rank
   - ticker
   - candidate_type
   - elasticity_score
   - confluence_score
   - catalyst_score
   - risk_score
   - primary_scenario
   - next_day_expected_range
   - upside_trigger_level
   - invalidation_level
   - one-line reason
3. Candidate Detail:
   - price chart
   - volume chart
   - primary path / risk path
   - next-day range
   - trigger and invalidation levels
   - news catalyst
   - historical analog
   - supporting evidence
   - conflicting evidence
4. Validation Section:
   - completed forecasts
   - whether top candidates were more elastic
   - whether high confluence was more accurate
   - baseline / challenger status
