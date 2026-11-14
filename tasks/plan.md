# Implementation Plan: P1 strategy and backtester validation

## Overview

Validate the Phase-1 T1/T4 strategy rules on stored daily candles and prove the
primary and slow reference backtesters agree on fills, exits, costs, and final
scorecards. Data acquisition and Parquet loading are already complete. This
work does not select a live provider, scrape NSE, or place orders.

## Architecture decisions

- Keep strategy functions pure: they receive closed candles and indicator
  values and return validated signals; they never fetch data or place orders.
- Use exact `Decimal` comparisons at the signal/backtest boundary. Research
  indicators may use floats internally, but a strategy must not convert a
  candle price to float to decide whether to trade.
- Treat the existing reference runner as an independent oracle. Equivalence
  tests must compare actual trade lists and audit outcomes, not duplicate logic.
- Keep validation offline and deterministic with committed tiny fixtures.

## Task list

### Phase 1: strategy contract

- [x] Remove float-based price decisions from T1/T4 and add exact Decimal tests.
- [x] Add end-to-end T1/T4 vectors using indicators and closed-bar timestamps.
- [x] Strengthen look-ahead and warm-up boundary tests.

### Phase 2: P1 validation path

- [x] Add deterministic strategy/backtester validation using both runners and
      scorecard output.
- [x] Add known-answer tests for signal/backtester/reference equivalence and
      scorecard reconciliation, including no-look-ahead truncation.
- [x] Add the P1 lesson explaining strategies and how to read the
      first honest scorecard.

### Checkpoint: P1 slice

- [x] Full pytest, Ruff, and mypy pass.
- [x] No test performs network I/O or accesses a broker.
- [ ] `STATUS.md`/handoff records the exact stopping point and any provider
      decision still owned by the human.

## Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Float conversion hides a price boundary | Wrong signal | Test fractional Decimal values that differ after float conversion and keep comparisons exact |
| Primary and reference share a bug | False confidence | Keep the reference implementation independent and use hand-traced vectors |
| Survivorship/overfitting | Misleading scorecard | Treat results as hypotheses and do not promote strategy versions from this slice |

## Open questions

- Which historical Tier A membership and corporate-action source is authorized?
