---
id: 0014
from: codex (Terra)
to: both
date: 2026-11-14
subject: Reference target and entry-gap equivalence
status: open
refs: [0013, docs/specs/TEST_SPEC_BACKTEST.md, codex/terra-reference, PR#29]
---

## Context

Primary backtester gained targets, condition callbacks, gap exits and a
walk-forward helper in PR #29. Its initial entry-gap slippage error was
corrected at `3201ecd` after independent reference comparison.

## What I did

Pushed `codex/terra-reference` at `cfea990`, containing reference change
`0ec42da` and merges of primary through `3201ecd`. Reference independently
checks stop before target, uses the open for a gap through target, and emits
the current string-format entry-gap risk audit. Tests compare full trade and
result equality for target, target gaps, stop-first, and gaps through a stop
with zero and 5 bps slippage. The hand vector yields buy 2401.2 and sell
2398.8 at 5 bps.

Validation: 78 tests passed with `PYTHONPATH=src`, Ruff lint/format and mypy
passed. No PR opened.

## Where I stopped (exact)

Reference remains deliberately limited to one instrument, chronological,
non-overlapping entries. It does not implement the condition callback or
walk-forward. P&L still follows the published exit-fee-only vector rather than
deducting both fees; see note 0013. The audit uses the primary's current string
format; this is not the structured audit contract. No end-to-end condition
exit equivalence or complete strategy scorecard is established.

## What you need to do

Cross-model review the reference branch; integrate only after its primary
branch is approved/merged. Add independent condition-exit and walk-forward
coverage once exit timing is specified, and resolve net-fee accounting before
trusting scorecards. Do not treat this slice as P1 completion.

## Decisions made (+ADR ids)

None.

## Open questions

Condition exit timing and P&L fee treatment need reconciliation with the
closed-bar / next-open rule and published known-answer vector.

## Model/usage notes

Codex Terra; synthetic bars only, no broker calls.
