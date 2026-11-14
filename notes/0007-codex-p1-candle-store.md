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
