---
id: 0011
from: codex (Terra)
to: both
date: 2026-11-14
subject: T1 and T4 look-ahead prefix test and backtester prerequisite
status: open
refs: [docs/specs/TEST_SPEC_BACKTEST.md, docs/specs/STRATEGY_SPEC.md, ADR-0020]
---

## Context

P1 requires independent backtester equivalence and look-ahead tests.

## What I did

Pushed `codex/terra-lookahead` at `eb96cbd`, based on backtester branch
`3eedbb6`. The test recomputes ATR, SMA and RSI from each input prefix,
then compares T1/T4 signals through that point with full-series signals,
excluding randomly generated IDs. Both fixtures produce signals. It checks
entry signal causality; it does not prove execution or full-system causality.

`pytest`: 58 passed; `ruff check .` and `mypy src`: passed. `ruff format
--check .` flags existing `src/trading/backtest/fills.py:80` from the base;
no production code was modified. Sol was notified.

## Where I stopped (exact)

The branch is pushed; no PR was opened. The primary backtester currently
contains only fill primitives, no trade-list runner. Condition-based exit
contracts remain undefined (ADR-0020). A reference runner and T1/T4 trade
list equivalence would require inventing missing behavior; neither is done.

## What you need to do

Review the test with a different model, integrate after its base branch, and
fix the existing formatting in the base branch. Once the primary engine and
exit semantics exist, independently implement the slow reference backtester,
run both on the spec's known-answer cases, and compare T1/T4 trade lists and
look-ahead behavior end to end. Owner approval is required for any merge.

## Decisions made (+ADR ids)

None.

## Open questions

The condition-exit gap in ADR-0020 remains unresolved.

## Model/usage notes

Codex Terra. No broker or network calls in the test.
