---
id: 0040
from: codex
to: owner
date: 2026-11-16 IST
subject: P1 implementation closeout — only real-data decisions remain
status: needs-human
refs: [codex/p1-build, bb6bf1d, docs/specs/P1_REJECTION_RULE.md, docs/specs/ACTION_REGISTER.md]
---

## Context

P1's source-independent implementation is now complete and pushed. This does
not mean that a strategy has been backtested or is eligible to trade.

## What I did

- Pushed `codex/p1-build` commit `bb6bf1d`.
- Added a fail-closed offline corporate-action register contract and example.
- Sealed a P1d shortlist to its exact candidate IDs, versions, parameters and
  catalog; a holdout result requires a real one-shot authorization and only one
  durable result per sealed candidate.
- Recorded P1d decision reasons append-only, added the pre-registered rejection
  rule, bound data/cost/split hashes into holdout identity, and added activation
  frequency to the scorecard.
- Reconciled P1 evaluation documentation and completed an independent review.
- Verified `pytest` (entire suite), `ruff check src tests`, targeted formatting,
  `mypy src`, and `git diff --check` all pass.

## Where I stopped (exact)

- Branch: `codex/p1-build`
- Last commit: `bb6bf1d feat(p1): seal holdout decisions and action evidence`
- No real-data P1 evaluation was run.

## What you need to do

1. Decide/obtain an authorized, complete corporate-action ledger for the five
   pilot symbols and exact candle windows. It must cover complex/unknown events
   and establish the volume basis; the present register deliberately verifies
   none of these.
2. Once that is complete, approve fresh unread development/validation/holdout
   boundaries. The already inspected 2016-2026 data is burned and cannot be the
   holdout.
3. Freeze the forward-paper promotion policy: observation duration, minimum
   sample and sizing for daily and intraday candidates. This is not an order
   permission and does not change paper-by-default behavior.

## Decisions made (+ ADR ids)

- No owner decision was inferred. `P1_REJECTION_RULE.md` is authoritative for
  P1d backtest rejection thresholds; forward-paper policy remains separate.

## Open questions

- Which permitted source/ledger will establish full action coverage? Recommend a
  manually reviewed, archived ledger if no provider can document historical
  completeness, rather than weakening the action gate.
- What forward-paper duration/sample/sizing policy do you approve for daily and
  intraday candidates? Recommend deciding it before any holdout is consumed.

## Model/usage notes

- Several bounded tasks were delegated and then independently reviewed. No real
  broker, exchange, or market-data query was made in this closeout.
