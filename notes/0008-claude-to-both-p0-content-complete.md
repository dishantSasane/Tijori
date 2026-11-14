---
id: 0008
from: claude (Sonnet 5)
date: 2026-11-14 19:30 IST
to: both
subject: P0 content-complete — remaining BUILD_ORDER items now have PRs open
status: open
refs: [0006, 0007, PR#11, PR#12, PR#13, PR#14, PR#15, docs/specs/STRATEGY_SPEC.md, docs/specs/RED_TEAM.md, docs/specs/TEST_SPEC_CANDLES.md, docs/specs/TEST_SPEC_BACKTEST.md, docs/learn/01, docs/learn/02, docs/learn/03]
---

## Context

Continuation of note 0006 (final P0 handoff, written when real gaps still
existed). This note records that every remaining BUILD_ORDER.md P0 item now
has written content, open as a PR. **This is a progress update, not a
replacement for note 0006's role** — the formal item-10 close-out still
happens once these PRs are reviewed and merged.

## What I did

1. `docs/specs/STRATEGY_SPEC.md` (item 8) — **PR #11**, CI green. Exact
   pseudo-code for T1-T6/F1, shared semantics (warm-up table, Wilder seed/
   recursion, zero-denominator rules, same-bar stop-first precedence,
   final-bar-unfilled handling — resolves note 0003 Q6), optional-vs-
   mandatory-target table (resolves Q5). Full known-answer vectors for T1/T4
   only (BUILD_ORDER's named first scorecard); T2/T3/T5/T6/F1 get pseudo-code
   without hand-derived vectors (flagged as a deliberate choice — a rushed
   hand-calculation would be worse than none). Flags an open gap: condition-
   based exits need an `ExitRequest` contract + reduced exit-only risk checks
   that `RISK_ENGINE_SPEC.md` doesn't have yet.
2. `docs/specs/RED_TEAM.md` (item 6) — **PR #12**, CI green. Prompt-injection
   scenarios (Brain/news), malformed/adversarial numeric inputs, replay/
   duplication/ordering attacks, config tampering, adapter-boundary
   scenarios (future P1+ surface). Each scenario says whether it's already
   covered by `TEST_SPEC_RISK.md` or flagged as a requirement for code that
   doesn't exist yet.
3. `docs/specs/TEST_SPEC_CANDLES.md` + `docs/specs/TEST_SPEC_BACKTEST.md`
   (item 7, remaining slices) — **PR #14**, CI green. Candle builder
   boundary/ordering/only-closed-bars tests, incremental==batch indicator
   equivalence with known-answer vectors (SMA/EMA/RSI/ATR/Bollinger),
   look-ahead truncated-data tests; backtester fill-at-next-open known-
   answer vector extending STRATEGY_SPEC's T1 case, stop-first precedence
   vectors, gap-handling vectors reusing RISK_ENGINE_SPEC §9's numbers,
   final-bar-unfilled exclusion, second-reference-backtester equivalence
   requirement. `TEST_SPEC_ADAPTERS.md`/`TEST_SPEC_STRATEGIES.md` still NOT
   written — genuinely lower priority (ADAPTERS.md already has a contract-
   test pattern via `BrokerContractTests`; STRATEGIES needs T2/T3/T5/T6/F1
   vectors that don't exist yet either).
4. `docs/learn/01-03` (item 9) — **PR #15**, CI was still running at last
   check (verify before relying on this). Candles/ticks, what a backtest is,
   why backtests lie — each with a tiny worked numeric example, following
   `docs/learn/TEMPLATE.md`.
5. Reviewed Codex's **PR #13** (atomic candle-batch inserts, follow-up to the
   merged candle store) — posted a comment recommending merge: real
   BEGIN/COMMIT/ROLLBACK transaction (not cosmetic), edge cases (empty
   batch, size-1, same-batch duplicate, partial overlap with existing rows)
   checked, meaningful test added, CI green.

## Where I stopped (exact)

- Five open PRs awaiting owner merge: #11, #12, #13 (Codex's), #14, #15.
- Worktree: `/home/dishant/Desktop/tijori-claude`, each item was its own
  short-lived branch off `main` (`claude/p0-strategy-spec`,
  `claude/p0-red-team`, `claude/p0-test-spec-backtest-candles`,
  `claude/p0-lessons-01-03`), all pushed.
- PR creation and CI verification for #12/#14 were delegated to background
  sub-agents (forked from this session) using the GitHub token the owner
  provided; PR #13's review was also delegated the same way. I did not
  personally watch every CI run complete in real time for all of them —
  the delegated reports say green, but a human glance before merging is
  still worth it given the volume.

## What you need to do

1. **Owner:** review and merge #11, #12, #13, #14, #15 (or ask a question on
   any of them first — none claim to need a decision, but you're the one who
   actually reads the content before it becomes "the spec").
2. **Codex:** once #11 (STRATEGY_SPEC) and #14 (TEST_SPEC_BACKTEST/CANDLES)
   merge, T1/T4 implementation (indicators, candle-level signal generation,
   backtester fills) has everything it needs, including hand-verified
   known-answer numbers to test against. T2/T3/T5/T6/F1 still need their own
   vectors before implementing — don't invent them from the pseudo-code
   alone; ask for them or derive them carefully, same reasoning as why I
   didn't rush them here.
3. **Next Claude session:** `TEST_SPEC_ADAPTERS.md` and
   `TEST_SPEC_STRATEGIES.md` (the two remaining item-7 slices) are the last
   real content gap. After that, item 10 (the actual final handoff) can be
   written for real, once this round of PRs has settled.

## Decisions made (+ADR ids)

None new.

## Open questions

Unchanged from notes 0003/0006.

## Model/usage notes

Claude Sonnet 5. Used forked sub-agents for PR-creation/CI-polling and one
cross-model PR review, per the owner's instruction to parallelize GitHub
busywork rather than block on it serially.

## Reply
(Receiver appends here; do not rewrite the sections above.)
