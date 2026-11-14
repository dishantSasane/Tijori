---
id: 0007
from: codex (GPT-6.1 Sol)
to: both
date: 2026-11-14
subject: P1 candle store completed and follow-up opened
status: open
refs: [0006, PR#10, PR#13, docs/BUILD_ORDER.md, docs/specs/CONTRACTS.md]
---

# P1 candle store checkpoint

## Context

Note 0006 gave Codex a safe-to-start P1 slice: candle storage and validation. Strategy and backtester work remains gated on `STRATEGY_SPEC.md` and `TEST_SPEC_BACKTEST.md`.

## Completed and merged

- Added `CandleStore` and `DuplicateCandleError` in `src/trading/storage/candles.py`.
- Added the DuckDB dependency and storage package.
- Validated closed `Candle` contracts; the storage key is market, symbol, timeframe, and open time. Exact duplicates are idempotent; conflicting duplicates fail with `DuplicateCandleError`.
- Added range queries and Parquet export.
- Kept the public API UTC-aware while storing UTC-naive DuckDB `TIMESTAMP` values at the database boundary; reads restore UTC-aware timestamps.
- Focused storage tests are included.

The implementation commit was `41c8a0a` on `codex/p1-candle-store`, merged by PR #10 as `18310fd`.

## Follow-up currently awaiting review

Codex added transactional batch append behavior so a conflicting row cannot leave earlier rows in the same batch persisted. Commit `ccbaf3d` is on `codex/p1-candle-store`; PR #13 (`fix(storage): make candle batches atomic`) is open against `main` and must not be merged by an agent. Its CI `test` check is green.

## Exact stopping point

- Working branch: `codex/p1-candle-store`.
- Merged baseline: `main` at `18310fd`.
- Follow-up under review: PR #13 at `ccbaf3d`.
- PR #10 and PR #13 CI `test` checks are green.
- Local validation for the merged candle store passed: `pytest -q` (36 passed), `ruff check .`, `ruff format --check .`, and `mypy src`.
- No provider downloader, indicators, strategies, or backtester were started.
- No real broker or exchange path was added.

## Next actions

1. Claude or the owner should review PR #13 and wait for its CI result; the owner approves and merges.
2. Codex may continue only the safe P1 storage/validation slice until the strategy and backtester specs arrive.
3. Claude should finish `STRATEGY_SPEC.md` and `TEST_SPEC_BACKTEST.md` before strategy/backtester implementation begins.

## Decisions and open questions

No ADR was needed: DuckDB and Parquet are already the proposed stack. Parquet partition layout and future schema migration policy can wait until the ingestion shape is specified.

## Reply

Reply on the handoffs branch with review findings, CI status, and any changed gate.

## Subsequent P1 increment: indicators (2026-11-14)

- Added pure, validated SMA/EMA helpers in `src/trading/indicators/moving_averages.py`, package exports, and focused tests.
- Commit: `d73088a` on `codex/p1-indicators`.
- PR: #16, `feat(indicators): add tested moving averages`, open against `main`.
- PR #16 CI `test` was pending when queried; the author reports local checks are green.
- Exact current stopping point: branch pushed, PR #16 open, no merge performed. Strategies and backtester remain gated by their specs.

## Subsequent P1 increment: full indicator suite (2026-11-14)

- Added Wilder RSI/ATR/ADX, Bollinger Bands, Donchian channels, and rolling/cumulative VWAP with tests.
- Commit: `9900b30` on `codex/p1-indicator-suite`.
- PR: #19, `feat(indicators): add Wilder and channel indicators`, open against `main`.
- PR #19 CI `test` was pending when queried; no merge was performed.
- Exact current stopping point: branch pushed and PR #19 awaiting review/CI; backtester work is next per the now-merged P0 specs.

## PR #19 incremental-state follow-up (2026-11-14)

- Added incremental SMA/EMA state and incremental Wilder state with equivalence coverage.
- PR #19 now contains `9900b30`, `6d8c61f`, and `79509ee`; latest head is `79509ee` on `codex/p1-indicator-suite`.
- PR #19 remains open against `main`; CI `test` was pending at the latest query. No merge performed.

## P1 T1/T4 strategy slice (2026-11-14)

- Implemented the T1 and T4 signal rules on top of the indicator suite, with tests.
- Commit: `72b9332` on `codex/p1-t1-t4`; the branch includes PR #19's indicator commits through `79509ee`.
- PR: #20, `feat(strategies): implement T1 and T4 signal rules`, open against `main`.
- PR #20 CI `test` was pending when queried; no merge performed.
- Exact current stopping point: PR #20 is open for cross-model review; no execution, broker, or live-order path was added.

## P1 backtester fill slice (2026-11-14)

- Added pure Decimal fill simulation: next-open fills, adverse slippage, profile brokerage, stop-first ordering, and gap-through-stop handling.
- PR #21, `feat(backtest): add deterministic fill simulation`, is open against `main`.
- Commits included: `e50bcc9` and `3eedbb6`; latest head is `3eedbb6` on `codex/p1-backtester`.
- The gap-exit correction applies adverse slippage to gap exits as well.
- PR #21 CI `test` was pending at the latest query; the author reports 57 total tests green locally. No merge performed.
- Exact current stopping point: fill slice is ready for cross-model review; no real broker path was added.

## Terra look-ahead handoff reference

Note `0011-codex-terra-to-both-lookahead.md` records Terra's independent look-ahead prefix tests on `codex/terra-lookahead` at `eb96cbd`. No separate PR was opened. The branch is based on the backtester work and should be reviewed alongside PR #21; owner approval remains required for any merge.

## Updated backtester stopping point (2026-11-14)

- PR #21 now includes `e50bcc9`, `3eedbb6`, and runner/formatting commit `faad076`; latest head is `faad076`.
- PR #21 remains open against `main`; CI `test` was pending at the latest query.

## P1 risk ExitRequest contract (2026-11-14)

- Owner-approved ExitRequest design implemented with ADR-0021, risk/spec and contract documentation updates, `ExitReason`, Pydantic `ExitRequest`, and tests.
- Commit: `e3ecc45` on `codex/risk-exit-contract`.
- PR #24 is open against `main`: `feat(risk): define position-reducing exit contract`.
- PR #24 CI `test` was pending at the latest query.
- Claude cross-model review is explicitly required before human merge; no merge performed.
- Exact stopping point: contract is pushed and awaiting Claude review plus CI.

## Terra ExitRequest property tests (2026-11-14)

- Independent property tests are on `codex/terra-exit-properties` at `ef7558d`, based on the ExitRequest contract commit `e3ecc45`.
- PR #25 is open against `main`: `test(risk): add ExitRequest property coverage`.
- PR #25 CI `test` was pending at the latest query; no merge performed.
- Review of both PR #24 and PR #25 must include Claude cross-model review before owner merge.
