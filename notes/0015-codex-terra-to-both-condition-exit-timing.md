---
id: 0015
from: codex (Terra)
to: both
date: 2026-11-14
subject: Condition-exit same-close timing conflicts with no-look-ahead rule
status: needs-human
refs: [AGENTS.md, docs/specs/STRATEGY_SPEC.md, 0014, codex/terra-reference]
---

## Context

A request to complete reference T1/T4/T6 condition exits instructed the
reference to evaluate a condition on a closed candle and fill at that same
candle's close, matching the primary runner. AGENTS.md section 4.5 says:
"Signals are computed on closed bars only. Fills happen at the next bar's
open plus costs and slippage." Its preamble requires a handoff rather than
guessing when chat conflicts with the file. A condition known only after a
close cannot generally be executed at that already-observed close without
future information.

## What I did

Inspected the rule and notified the coordinating agent. No code changed in
response to the conflicting instruction; prior reference branch remains
pushed at `cfea990` (see note 0014).

## Where I stopped (exact)

Reference condition-exit implementation and equivalence tests remain undone.
The primary currently fills the condition on its signal candle's close; do not
use that result as proof of no look-ahead.

## What you need to do

Owner decision: (A, recommended) apply the existing next-open rule to
condition exits, specifying pending final-bar exits, stop precedence before
the next open, and adverse sell slippage; then fix the primary and write
independent reference equivalence tests; or (B) explicitly change the
repository's authoritative rule and specs through review, explaining how a
same-close fill is causally executable and its costs. A chat instruction
alone conflicts with the current rule and cannot resolve it under AGENTS.md.

## Decisions made (+ADR ids)

None.

## Open questions

For option A, clarify treatment of protective stop gaps and pending exits when
there is no next bar. The reference will follow the reviewed decision.

## Model/usage notes

Codex Terra; no broker activity.
