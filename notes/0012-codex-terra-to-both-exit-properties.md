---
id: 0012
from: codex (Terra)
to: both
date: 2026-11-14
subject: Exit contract property tests and remaining I14 checks
status: open
refs: [docs/RISK_SPEC.md, docs/specs/CONTRACTS.md, codex/risk-exit-contract]
---

## Context

The owner approved the exit request design. I14 requires exits to reduce,
never increase, a position; STOP/KILL exits must not be vetoed by the Brain.

## What I did

Pushed `codex/terra-exit-properties` at `ef7558d`, based on exit-contract
commit `e3ecc45`. Hypothesis tests exercise non-positive quantities and
positive quantities across all reasons; tests also reject caller-supplied buy
and sell sides. These check the request boundary, not execution.

Validation: 67 pytest tests pass, Ruff lint and format checks pass, and
`mypy src` passes.

## Where I stopped (exact)

No exit execution/risk implementation exists on the base branch. Therefore
these tests cannot establish broker-position matching, quantity <= open
quantity, deriving the actual order side, post-fill position reduction, or the
Brain veto bypass. No PR was opened.

## What you need to do

Review this branch independently and integrate after its base. When exit
execution and risk behavior exist, write property tests against the public
entry point: generate long and short positions, missing/mismatched positions,
zero and oversized requests, partial and full exits, repeated events and
STOP/KILL with a vetoing Brain; verify executed quantity and broker position
never increase and verify side derives from broker truth. Use fake brokers.

## Decisions made (+ADR ids)

None.

## Open questions

None added; execution reconciliation semantics must be implemented according
to the approved contract.

## Model/usage notes

Codex Terra. No real broker is used.
