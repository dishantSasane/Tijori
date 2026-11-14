---
id: 0013
from: codex (Terra)
to: both
date: 2026-11-14
subject: Stop-only reference backtester and primary runner gaps
status: open
refs: [docs/specs/TEST_SPEC_BACKTEST.md, docs/specs/STRATEGY_SPEC.md, codex/terra-reference]
---

## Context

P1 needs an independent slow backtester, exact equivalence and known-answer
tests. Primary `run_long_only` exists on main; its supported behavior is only
a subset of the specification.

## What I did

Pushed `codex/terra-reference` at `63f2d1f`, based on main `79d3f2f`.
`src/trading/backtest/reference.py` independently scans bars and calculates
stop fills without using the primary fill or stop functions. Exact trade-list
and complete-result equivalence tests cover T1/T4 entries, same-bar stops,
subsequent stops, non-entry gaps, profile costs and slippage, open positions,
last-bar signals, and generated variations. A hand-calculated gap-on-entry
case tests the reference separately. The reference rejects unsupported target
signals, overlapping entries and non-chronological signals.

Validation: `PYTHONPATH=src /home/dishant/Desktop/Tijori/.venv/bin/pytest`
68 passed; Ruff lint/format and `mypy src` passed. PYTHONPATH selects this
worktree because the existing shared virtualenv is editable against another.
No PR opened.

## Where I stopped (exact)

Full P1 equivalence is not established. Primary constructs `Position` with
`stop < entry_price`, so a fill gapping below its stop raises rather than
immediately exiting (spec §3). Its per-signal loop opens overlapping positions
although its docstring claims one at a time. It has no target or condition exit,
exit-reason field, gap-risk audit event, or walk-forward runner. Reference
implements only the explicit stop-only subset and cannot prove those features.

Both current runners follow the known-answer vector's P&L calculation, which
deducts the exit brokerage alone, while reporting both entry and exit fees.
This is not net-of-both-fees P&L; resolve the spec/accounting discrepancy
before using any scorecard for decisions.

## What you need to do

Cross-model review the reference; review and integrate after owner approval.
Fix primary gaps in a separate reviewed change, then extend the reference and
compare gap-on-entry, overlapping-entry policy, stop-versus-target precedence,
condition exits and exit reasons, and gap-risk audit events. Reconcile the
known-answer P&L with total transaction costs before producing a scorecard;
include the entry fee exactly once. Implement and test walk-forward and
end-to-end no-look-ahead coverage. Do not treat these tests as proof that P1 is
complete.

## Decisions made (+ADR ids)

None; unsupported cases are explicit errors in the reference.

## Open questions

How to reconcile the exit-only-fee known answer with net P&L and total fees.

## Model/usage notes

Codex Terra. Tests use synthetic candles and no broker.
