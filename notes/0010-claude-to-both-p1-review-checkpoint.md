---
id: 0010
from: claude (Sonnet 5)
date: 2026-11-14 19:45 IST
to: both
subject: P1 cross-model review checkpoint (PR #19, #20) — no blocking issues
status: open
refs: [0009, PR#19, PR#20, docs/specs/STRATEGY_SPEC.md, docs/specs/TEST_SPEC_STRATEGIES.md]
---

## Context

Owner asked me to stop delegating GitHub review work to background sub-agents
and do the review directly for this round. Reviewing Codex's P1 work
(indicator suite PR #19, T1/T4 signals PR #20) per AGENTS.md §9 — both
already merged by the time I reviewed, so these are retroactive/record-
keeping reviews, not merge gates.

## What I did

1. Pulled current `main`, ran the full suite fresh: `pytest` → 53 passed,
   `ruff check .` → clean, `mypy src` → clean (19 source files). Everything
   Codex has shipped integrates cleanly with the P0 foundation.
2. Read `src/trading/indicators/` (PR #19) directly and hand-verified the
   Wilder ATR known-answer vector from `STRATEGY_SPEC.md` §1.3 against the
   actual recursion logic — matches exactly. Posted a comment on PR #19:
   non-blocking gaps are (a) ADX/Bollinger/Donchian/VWAP still lack
   incremental versions (only SMA/EMA/RSI/ATR do), (b) still `float` not
   `Decimal`, worth a second look for `ATRState` specifically since its
   output sizes stops that feed `RiskDecision.qty`.
3. Read `src/trading/strategies/phase1.py` (PR #20) directly and hand-
   verified T1's Donchian logic (correct `H(N)` exclusion of the current
   bar, strict `>` on the breakout, correct warm-up) and T4's AND-logic
   against `STRATEGY_SPEC.md` §2.1/§2.4. Posted a comment on PR #20:
   non-blocking gaps are (a) no test for T1's `close==H(N)` boundary (must
   not fire), (b) no test for T4's three exit triggers — this PR is
   entries-only, consistent with the still-open `ExitRequest` gap
   (ADR-0020), not an oversight.

## Where I stopped (exact)

- No open PRs remaining as of this note; `main` is clean and green.
- I did not write any backtester code — that's Codex's lane per
  `MODEL_ROLES.md` §5 (Sol as author), and duplicating it would waste effort.

## What you need to do

1. **Codex:** next BUILD_ORDER.md P1 item is the backtester engine
   (next-open fills, costs/slippage, stop-first rule) against
   `docs/specs/TEST_SPEC_BACKTEST.md`'s known-answer vectors, plus the
   second reference backtester in parallel (§5 of that spec — they must
   agree on every vector before either is trusted). The two test gaps
   flagged above (T1 boundary, T4 exits) are good fast-follow tests, not
   blockers to starting the backtester.
2. **Owner:** nothing blocking.

## Decisions made (+ADR ids)

None new.

## Open questions

Unchanged.

## Model/usage notes

Claude Sonnet 5, reviewing directly this round (no forked sub-agents) per
owner instruction.

## Reply
(Receiver appends here; do not rewrite the sections above.)
