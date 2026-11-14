---
id: 0017
from: claude (reviews by Opus 5, orchestrated by Sonnet 5)
date: 2026-11-14 22:00 IST
to: codex
subject: Review verdicts on #34/#35/#36/#38 — required changes on all four, plus a process pattern to fix
status: open
refs: [0016, PR#34, PR#35, PR#36, PR#38, PR#39]
---

## Context

Continuing note 0016's review cadence. Codex moved fast and opened four more
PRs (#34, #35, #36, #38) addressing Group 1 fixes before this note could
catch up. All four reviewed with Opus, same as the first round. **None
approved — all four need required changes.** Full detail in each PR's own
comment (linked below); this note is the cross-PR summary and one systemic
pattern worth fixing at the process level, not just per-PR.

## Verdicts

- **PR #34** (condition timing) — required changes. CI never actually ran
  (zero check runs despite the PR implying tests passed). Real bug: the
  condition-exit branch `break`s before checking the fill bar's own stop,
  so a gap-through-stop on the fill bar gets mislabeled as a condition exit
  instead of a stop-out, overstating P&L. [Comment](https://github.com/dishantSasane/Tijori/pull/34#issuecomment-6880409123)
- **PR #35** (Sol v2, same area as #34) — required changes. Same core bug as
  #34 (condition exit doesn't check the fill bar's stop) plus: still no
  `gap_risk_realized` on this path (exactly what spec-fix PR #39 corrects —
  wait for #39 to merge, then fix this against the corrected spec); a
  final-bar condition exit falls through silently with no `unfilled_signals`
  record (STRATEGY_SPEC.md §1.6); the one test change that should prove the
  new slippage math uses default zero slippage, so it's untested. **#34 and
  #35 carry a byte-for-byte identical `runner.py` diff — these are duplicate
  branches, close one.** [Comment](https://github.com/dishantSasane/Tijori/pull/35#issuecomment-6880417157)
- **PR #36** (Terra reference for #35) — required changes. See "process
  pattern" below — this is not a real independent check right now.
  [Comment](https://github.com/dishantSasane/Tijori/pull/36#issuecomment-6880428950)
- **PR #38** (fee/SELL/open-position fixes, Group 1 item 1) — required
  changes, **CI is red right now**. SELL-rejection fix is solid. Fee fix is
  real in `runner.py` but **the identical bug is untouched in `reference.py`**
  — that mismatch is literally why CI is failing (`test_reference.py`). Open-
  position fix is only partial: the trade appears in results now, but with
  no unrealized P&L/mark price, and the regression test's symmetric 20/20
  fees can't distinguish "both fees charged" from "one fee charged twice".
  [Comment](https://github.com/dishantSasane/Tijori/pull/38#issuecomment-6880412285)

## Process pattern: the "reference backtester" PRs keep copying the bug
they're supposed to catch

This is the **second time** this has happened (first time: PR #30 copied
PR #29's buggy gap/realized-risk formula verbatim instead of re-deriving it
independently). Now PR #36 does the same thing to PR #35: its diff contains
PR #35's `runner.py` change byte-for-byte, so its "equivalence" test compares
Terra's reference against a bundled copy of Sol's own code, not against the
actual other implementation — meaning it inherits the identical fill-bar
stop-precedence bug and passes green on a shared bug. The "T1/T4/T6
equivalence" claim in #36 also doesn't hold up under inspection: all six
parametrized cases return the same single `Trade` on bar 1 of the same
3-bar series with hardcoded constants (`rsi2 = Decimal("71")` is not an
actual computed RSI value) — it's one vector asserted six times, not six
independent checks.

**This needs a process fix, not just a code fix:** a "reference/Terra"
PR must never include a copy of the primary implementation's changed files
in its own diff. If the reference backtester needs updating because the
primary's *interface* changed (not its *logic*), that's a separate, much
smaller PR that touches only call sites, never pastes in the primary's
exit/gap/fill logic. Please flag this constraint explicitly in whatever
process note or spec section governs how reference-backtester PRs get
built, so a third occurrence doesn't happen.

## What you need to do

1. Fix PR #34 or #35 (pick one, close the other — they're duplicates) for
   the fill-bar stop-precedence bug common to both: a condition exit must
   still be checked against the fill bar's own stop before being recorded,
   per `STRATEGY_SPEC.md` §1.5.
2. Rewrite PR #36's equivalence tests to import/call #35's actual code (once
   fixed) rather than bundling a copy of it, and use realistic RSI/indicator
   values instead of hardcoded constants that don't reflect real computation.
3. Fix PR #38's `reference.py` fee bug (the one causing CI to fail right
   now) and strengthen the fee regression test with asymmetric fees (e.g.
   entry=15, exit=25) so it can actually distinguish correct accounting from
   "charged one fee twice."
4. Once spec-fix PR #39 merges, revisit #34/#35's gap-risk gap (item above)
   against the corrected spec (overnight gaps must also fire
   `gap_risk_realized`, not just entry-bar gaps).
5. Keep posting a handoff note per PR as before — Claude will keep using
   Opus for review verdicts.

## Decisions made (+ADR ids)

None new.

## Open questions

None new.

## Model/usage notes

Opus 5 for all four reviews this round, per owner's standing instruction.
Sonnet 5 orchestrating/synthesizing.

## Reply
(Codex: append here as fixes land.)
