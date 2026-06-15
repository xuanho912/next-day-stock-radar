# Product Definition

## Positioning

`next-day-stock-radar` is a buy/sell decision-support dashboard for next-session high-elasticity speculative stock opportunities.

It is not:

- a normal stock recommendation list
- a long-term investment system
- an automated trading robot
- a broker integration
- a page full of indicators for professional appearance

## Core User Question

When the user opens the dashboard after market close, they should immediately know:

- should tomorrow be attack, observe, or defend?
- where is short-term capital most likely to attack?
- which stocks deserve attention?
- what condition makes each stock actionable?
- where is the invalidation level?
- which hot stocks should be avoided because data does not confirm them?

## Product Principle

Precision is greater than professional feeling.

High rank requires multi-source confluence. Missing evidence and conflicting evidence must cap ratings.

## Layers

1. Market path: attack / neutral / defense.
2. Sector theme: where capital is flowing.
3. Candidate scoring: catalyst, technical, volume/flow, sector, options/short, risk.
4. Trade plan: trigger, invalidation, target range, risk.
5. Validation: forecast records, outcome backfill, model scorecard.

## Candidate Ratings

- A+: strong confluence, primary focus.
- A: actionable only after trigger confirmation.
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

## First Screen

The first screen must include:

- radar summary
- high-elasticity opportunity status
- market speculation background
- strongest candidates
- strongest candidate type
- risk level
- data freshness
- model validation status
