---
id: 0006
from: claude (Sonnet 5)
date: 2026-11-14 19:15 IST
to: both
subject: P0 final handoff — merged deliverables, open PRs, real remaining gaps, first P1 task
status: open
refs: [0004, 0003, PR#4, PR#5, PR#7, PR#8, PR#9, docs/specs/CONTRACTS.md, docs/specs/ADAPTERS.md, docs/specs/RISK_ENGINE_SPEC.md, docs/specs/TEST_SPEC_RISK.md]
---

## Context

This is the final P0 handoff Codex is waiting on. **P0 is not 100% done against
BUILD_ORDER.md's own exit criteria** (item 7, test specs, is only partially
written) — this note says exactly what's merged, what's open, and what's
still missing, so Codex can start on the part of P1 that doesn't depend on
the gap, instead of either guessing it's all done or waiting on everything.

## What I did (this session, in order)

1. Fixed repo bootstrap (no `main` existed; `handoffs` had code nested in it) —
   see note 0004 for detail. `main` and `handoffs` now have the right layout.
2. P0 items 1/3/4: core contracts + adapter Protocols/fakes. **Merged to
   `main`** via PR #5 (merge commit in `main`'s history) — but merged at a
   commit that still had the two bugs below; see item 4.
3. P0 item 5: wrote `docs/specs/RISK_ENGINE_SPEC.md` (exact check order, Brain
   validation boundary, paper/shadow semantics, gap-at-fill rule,
   session-aware staleness — resolves note 0003's Q1-Q4). **Merged to `main`**
   via PR #7.
4. Codex's cross-model review on PR #5 found two real bugs before it merged:
   (a) `Contract` fields defaulted to `datetime.now(UTC)`, violating the
   injected-clock rule (AGENTS.md §6); (b) the UTC validator accepted any
   tz-aware datetime, not just true UTC (e.g. IST `+05:30` passed). **I fixed
   both**, but the fix landed *after* PR #5 had already been merged by the
   owner at the old commit — so the bugs are currently live on `main`. The fix
   is in **open PR #8** (`claude/p0-fix-clock-utc` → `main`), cherry-picked
   cleanly onto current `main`, CI green, replied to Codex's review comments
   on PR #5 with the fix commit hash.
5. P0 item 7 (risk slice only): wrote `docs/specs/TEST_SPEC_RISK.md` — known-
   answer sizing cases, one test per check-order row, Brain-verdict suite,
   mode-gate/shadow suite, gap/resize suite, order state-machine exhaustive
   test, fail-closed suite. **Open PR #9** (`claude/p0-test-spec-risk` →
   `main`), CI green.
6. Reviewed Codex's PR #4 (`docs/specs/DATA_SOURCES.md`) — posted an approving
   comment (not a formal GitHub "approve," since both agents push through the
   owner's one account and GitHub blocks self-approval); recommended merge.
   **It has since been merged** by the owner.
7. Replied to note 0003 with partial answers; full answers are now in
   `RISK_ENGINE_SPEC.md` §5, §7, §9, §6 (Q1-Q4). Q5-Q8 still open, see below.

## Completed P0 deliverables (merged or PR-open, with links)

| Item | Deliverable | State |
|---|---|---|
| 1 | Scaffold verified (pytest/ruff/mypy/format) | Done, no PR needed (no fixes required) |
| 3 | `src/trading/core/` contracts, clock, config loader | **Merged** (PR #5), but see the clock/UTC bugfix below — **open PR #8** must merge before this item is actually correct on `main` |
| 4 | `src/trading/adapters/` Protocols + fakes + contract-test mixin | **Merged** (PR #5), same caveat as item 3 |
| 5 | `docs/specs/RISK_ENGINE_SPEC.md` | **Merged** (PR #7) |
| 7 (risk slice) | `docs/specs/TEST_SPEC_RISK.md` | **Open PR #9** |
| — | Codex's `docs/specs/DATA_SOURCES.md` reviewed and merged (PR #4) | Merged |

## Real remaining gaps (BUILD_ORDER.md P0 items NOT done)

- **PR #8 and #9 are not merged yet.** Until #8 merges, `main`'s
  `core/models.py` has the two bugs Codex found (wall-clock defaults, loose
  UTC check) — do not build P1 code against current `main` without that fix,
  or you'll inherit non-deterministic timestamps.
- **Item 2/5:** `docs/specs/RED_TEAM.md` — not written (RISK_ENGINE_SPEC.md §10
  has an "edge cases" section that's a start, but not the full adversarial
  scenario list the kickoff asked for).
- **Item 7:** `TEST_SPEC_{BACKTEST,CANDLES,ADAPTERS,STRATEGIES}.md` — none
  written. Only the risk slice exists (PR #9). This is the biggest real gap.
- **Item 8:** `docs/specs/STRATEGY_SPEC.md` — not written. Note 0003's Q5/Q6
  (optional vs. mandatory target, bar timestamp/warm-up/Wilder-seed semantics)
  are unresolved and block writing correct known-answer backtester cases.
- **Item 9:** lessons 01-03 in `docs/learn/` — not written (00 exists from the
  planning chat).
- Note 0003's Q7 (survivorship/point-in-time universe) and Q8 (P0-exit vs.
  P1-start sequencing) are still open too.

## What you need to do

1. **Owner:** merge PR #8 (clock/UTC fix) and PR #9 (TEST_SPEC_RISK) after
   checking CI (both green as of this note). #8 should merge before any P1
   code is written against `core.models`.
2. **Codex:** you do **not** need to wait for `RED_TEAM.md`,
   `TEST_SPEC_{BACKTEST,CANDLES,...}`, `STRATEGY_SPEC.md`, or lessons 01-03 to
   start the part of P1 that has no dependency on them:
   - **Safe to start now** (once #8 is merged): candle store (Parquet+DuckDB),
     candle validation, the bhavcopy/corporate-actions research you already
     did in PR #4 can move toward an actual adapter *once the owner resolves
     the NSE-terms access question* — still gated by that, not by missing
     Claude specs.
   - **Wait for `STRATEGY_SPEC.md`** before implementing T1-T6/F1 — Q5/Q6 are
     real ambiguities (mandatory vs. optional target, Wilder seeding) that
     would otherwise get silently guessed into the implementation.
   - **Wait for `TEST_SPEC_BACKTEST.md`** before writing the backtester's
     known-answer fill tests — same reason, plus it needs the bar-timestamp/
     closed-bar semantics from STRATEGY_SPEC resolved first.
   - The risk engine itself (P2) can be implemented against
     `RISK_ENGINE_SPEC.md` + `TEST_SPEC_RISK.md` now — those are complete.
3. **Next Claude session (if one happens before the Pro plan ends
   ~2026-11-16):** priority order — `STRATEGY_SPEC.md` (unblocks the most
   P1 work), then `TEST_SPEC_BACKTEST.md`/`TEST_SPEC_CANDLES.md`, then
   `RED_TEAM.md`, then lessons, in that order if time runs out.

## Decisions made (+ADR ids)

None new. No ADR changed this session.

## Open questions

- Same as note 0003's, plus: should `RED_TEAM.md`/`STRATEGY_SPEC.md`/
  remaining `TEST_SPEC_*` be finished before Codex starts *any* P1 code, or is
  the split above (safe-to-start vs. must-wait) good enough? My recommendation
  is the split above — waiting for 100% of P0 when most of the remaining gap
  doesn't block the highest-value P1 work (candle store, risk engine P2) would
  waste the Claude-Pro window for no safety benefit.

## Model/usage notes

Claude Sonnet 5, this session only (not Fable — the model-routing table in
MODEL_ROLES.md §4 was not followed; flagged previously in note 0004 too).

## Reply
(Receiver appends here; do not rewrite the sections above.)
