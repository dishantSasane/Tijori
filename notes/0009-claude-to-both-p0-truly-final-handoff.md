---
id: 0009
from: claude (Sonnet 5)
date: 2026-11-14 20:00 IST
to: both
subject: P0 truly final handoff — everything merged, verified together, known gaps for P1
status: open
refs: [0006, 0008, PR#4-#18, docs/specs/*, docs/learn/*]
---

## Context

This supersedes notes 0006 and 0008 as the real item-10 close-out. Every
PR from this session (#4, #5, #7-#9, #11, #12, #14, #17, #18, plus Codex's
#10, #13, #16) is now **merged into `main`**. I re-verified the whole repo
together after all the parallel merges, not just each PR individually.

## What exists now (BUILD_ORDER.md P0, item by item)

| Item | Status |
|---|---|
| 1. Scaffold verified | Done |
| 2. Gaps/contradictions logged | Done via ADR-0018/0019/0020 in `docs/decisions.md` (all `proposed`, awaiting owner read) |
| 3. Core contracts | Done, merged, clock/UTC bugfix included |
| 4. Adapter Protocols + fakes | Done, merged |
| 5. RISK_ENGINE_SPEC.md | Done, merged |
| 6. RED_TEAM.md | Done, merged |
| 7. TEST_SPEC_{RISK,CANDLES,BACKTEST,ADAPTERS,STRATEGIES}.md | **All five done, merged** |
| 8. STRATEGY_SPEC.md | Done, merged |
| 9. Lessons 00-03 | Done, merged |
| 10. This handoff | Done (this note) |

**Full repo verification after all merges** (not just per-PR CI):
`pytest` → 41 passed, `ruff check .` → clean, `ruff format --check .` →
clean, `mypy src` → clean (15 source files now: `core/`, `adapters/`,
`storage/` from Codex, `indicators/` from Codex). Contracts, adapters,
candle storage, and the new indicators module all integrate without
conflict.

## Known gaps for P1 (read before building on top of these)

1. **Indicators (PR #16, merged) have batch implementations only — no
   incremental implementation, no incremental==batch equivalence test
   yet.** `TEST_SPEC_CANDLES.md` §2 requires both, Decimal-exact. Flagged in
   a cross-model review comment on PR #16: do **not** wire these into the
   live hot path or the backtester until the incremental half + equivalence
   test exist — ARCHITECTURE.md §4's "one code path for backtest and live"
   guarantee depends on it, and its absence is exactly the kind of thing
   that looks fine in a backtest and silently diverges live.
2. **Indicators use `float` internally with `pytest.approx` in tests**,
   where `TEST_SPEC_CANDLES.md` calls for Decimal-exact comparison.
   AGENTS.md §6 allows float in vectorized research code as long as results
   convert at the boundary — judge case-by-case whether this indicator
   module counts as "research" or "hot path" before deciding if this needs
   fixing now or can wait.
3. **Condition-based exits (T1/T2/T4/T6) have no contract yet** —
   `STRATEGY_SPEC.md` §1.7 / ADR-0020 flags this; needs an `ExitRequest`-
   shaped contract and a reduced exit-only risk-check list before those
   templates' exits can be implemented correctly.
4. **`DecisionStore` atomicity under concurrent signal delivery** is an open
   design question (RISK_ENGINE_SPEC.md §10, ADR-0020) — needed before
   invariant I7 can be proven under real concurrency, not just sequential
   retry.
5. **T2/T3/T5/T6/F1 have no hand-calculated known-answer vectors** — only
   exact pseudo-code and a test-case list (`TEST_SPEC_STRATEGIES.md`).
   Derive vectors carefully (spreadsheet or reference calc) when
   implementing each, per that spec's own stated reasoning.
6. **ADR-0018/0019/0020 are `proposed`, not `accepted`** — owner should read
   and either accept or push back on the clarifying decisions made while
   writing the risk/strategy specs (paper-rejection-vs-shadow semantics,
   gap-handling rule, Wilder seeding, Bollinger population-stdev default).

## First P1 task, concretely

With `STRATEGY_SPEC.md` + `TEST_SPEC_BACKTEST.md`/`TEST_SPEC_CANDLES.md`
merged, Codex can now build toward the "first honest scorecard" BUILD_ORDER
names (T1 Donchian + T4 RSI(2) on Nifty 50 daily):

1. Finish indicators properly (gap #1/#2 above) — incremental + equivalence
   test, before anything depends on them being correct live.
2. Candle-level signal generation for T1 and T4 against
   `STRATEGY_SPEC.md` §2.1/§2.4's exact pseudo-code, tested against
   `TEST_SPEC_STRATEGIES.md` §2's test list (boundary/AND-logic/warm-up) —
   the specific numeric vectors already exist for these two templates in
   `STRATEGY_SPEC.md` itself.
3. Backtester fill engine against `TEST_SPEC_BACKTEST.md`'s known-answer
   vectors (next-open fill, slippage/costs, stop-first precedence, gap
   handling, final-bar-unfilled exclusion).
4. Second reference backtester (slow/simple) in parallel, per
   `TEST_SPEC_BACKTEST.md` §5 — both must agree on every known-answer
   vector before either is trusted.

## What you need to do

1. **Owner:** read ADR-0018/0019/0020 in `docs/decisions.md` and
   accept/dispute each. Nothing blocks on this, but it shouldn't sit
   `proposed` forever.
2. **Codex:** the gaps above (especially #1/#2, indicators) are yours to
   close before building further on them — not a blocker to *starting*
   P1, but a blocker to trusting results once the backtester exists.
3. **Next Claude session** (if the Pro plan allows one before ~2026-11-16):
   nothing P0-mandatory remains. Good uses of remaining time, in order of
   value: (a) resolve the `ExitRequest`/exit-risk-check gap (#3) since it
   blocks 4 of 7 strategy templates' exits, (b) the `DecisionStore`
   concurrency design (#4), (c) T2/T3/T5/T6/F1 known-answer vectors (#5) as
   each gets implemented.

## Decisions made (+ADR ids)

ADR-0018, ADR-0019, ADR-0020 (all `proposed`).

## Open questions

Unchanged from notes 0003/0006 — `MASTER_PLAN.md` §13's capital/broker/
exchange/VM/allocation decisions remain the owner's, not blocking.

## Model/usage notes

Claude Sonnet 5, this session throughout. Heavy use of forked sub-agents for
GitHub PR-creation/CI-polling/cross-model-review busywork in parallel with
continued spec writing, per the owner's explicit instruction mid-session.

## Reply
(Receiver appends here; do not rewrite the sections above.)
