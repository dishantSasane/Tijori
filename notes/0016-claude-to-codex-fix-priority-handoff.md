---
id: 0016
from: claude (Sonnet 5, orchestrating; reviews by Opus 5, spec fixes by Fable 5.1)
date: 2026-11-14 21:10 IST
to: codex
date-detail: see refs
subject: Fix-priority handoff — bugs found in cross-model review of #21, #24-#30
status: open
refs: [PR#21, PR#22, PR#24, PR#25, PR#26, PR#27, PR#28, PR#29, PR#30, PR#37, docs/specs/*, docs/RISK_SPEC.md]
---

## Context

Owner asked for a full cross-model review of every P1 PR (oldest first) against `RISK_SPEC.md`'s invariants (including the new §3A/I14 exit-contract rule), `TESTING.md` §6/§8, and the look-ahead/equivalence requirements. All nine PRs were already merged by review time, so every finding below is a fast-follow fix, not a merge block — but **the owner has posted a "Known issues" banner on README.md (PR #37) saying backtest P&L/risk numbers must not be trusted until this batch is fixed**, so this is not low priority.

Each PR comment with full detail is linked below. This note is the priority-ordered punch list with exact acceptance tests, per the owner's explicit sequencing.

## Group 1 — start now (no dependency on the spec-fix PR)

1. **PR #21 (backtester fill engine) — 3 fixes:**
   - Remove the fee double-counting: `pnl` currently charges only exit-side brokerage while recording both entry and exit fees in the `fees` field — every trade is silently optimistic by one brokerage fee. **Acceptance test:** a known-answer trade with entry brokerage=20, exit brokerage=20 must show `fees=40` in the result AND `pnl` must reflect both fees being charged, not just one.
   - Reject SELL signals outright (this engine is long-only) instead of silently trading them as a BUY (`side="buy"` is currently hardcoded). **Acceptance test:** a `Signal(side=SELL, ...)` fed to the backtester must raise or produce an explicit rejection/reason code, never a silent long fill.
   - Include still-open positions at the end of the data window in the result (currently they vanish entirely instead of being reported as "open" or "unrealized"). **Acceptance test:** a position opened on the second-to-last bar with no exit condition met by the final bar must appear in the result set tagged as still-open, with its unrealized P&L at the last close, not be absent from the trade list.
   - Also still outstanding from the original review: a missing `signal.stop` is dropped with a bare `continue` instead of an auditable rejection (`ReasonCode.SIGNAL_MISSING_STOP` per `RISK_ENGINE_SPEC.md` §2 check 5) — fix this in the same PR if convenient, separate PR if not.

2. **PR #24/#25 (ExitRequest contract + property tests) — 2 fixes:**
   - Enforce invariant **I14** ("an exit request never opens or increases a position") in actual executable code, not just `Field(gt=0)` on quantity. The check needs to compare the requested exit quantity against the matching open position's quantity and reject (fail closed) if it would exceed it. **Acceptance test:** a hypothesis/property test generating random `(open_position_qty, exit_request_qty)` pairs must prove: for every pair where `exit_request_qty > open_position_qty`, the exit is rejected; the resulting position after a valid exit is never negative and never larger than before the exit.
   - Make `exit_id` **deterministic**, derived from `(position_id, reason_code, bar_ts_utc)` (not `default_factory=_new_id` producing a random UUID) — the random default means two identical exit requests currently get different ids and neither dedupes against the other, which breaks idempotency entirely. **Acceptance test:** submitting the same `(position_id, reason_code, bar_ts_utc)` twice must produce the same `exit_id` both times, and the second submission must be a no-op (idempotent), not a second exit.

3. **PR #26-#28 (strategy tests, scorecard, indicators) — 3 fixes:**
   - T1's boundary test (`close==H(N)` must not fire) is currently vacuous — it would still pass if the `<` it's supposed to be testing were flipped to `<=`. **Acceptance test: use mutation testing to prove it** — flip the boundary operator in `phase1.py` and confirm the existing test suite (with your fix) now fails. Don't just eyeball a new fixture; prove it catches the mutation.
   - Add `expectancy`, `avg_win`, `avg_loss` to the scorecard (named in the original PR description, absent from the actual code). **Acceptance test:** the known-answer scorecard example from `docs/learn/02-what-is-a-backtest.md` (two trades, +80/-40) must reproduce `expectancy=+20`, `avg_win=+80`, `avg_loss=-40` exactly.
   - Replace the ADX incremental==batch equivalence test's flat input series (`[10]*12`, which makes every true-range/directional-movement value zero and the test pass against a stub returning zeros) with a real, non-flat series that actually exercises ADX's directional-movement and double-Wilder-smoothing logic. **Acceptance test:** use (or adapt) the property-test harness pattern already used for SMA/EMA/RSI/ATR in the same PR — a randomized series of length >= 3x warmup, not a fixed flat one.

4. **PR #22 fast-follow:** fix `ruff format` so CI is actually green on `main` (the look-ahead tests in this PR were merged while CI was red — pytest never ran before merge). Also: drop the byte-for-byte duplicated `fills.py` this PR introduced (it duplicates PR #21's file despite the PR description claiming no production code changed), fix the ~20 of 29 vacuous prefix-iteration test cases that compare `[]==[]`, add a non-flat fixture, and implement the warm-up-boundary case from `TEST_SPEC_CANDLES.md` §3.9.

## Group 2 — wait for the spec-fix PR to merge first

The spec-fix PR (Fable, in progress as of this note — will post its PR number in a reply here once open) resolves three ambiguities that PR #29/#30's bugs trace back to: the gap-risk rule only covering entry-bar gaps (not overnight), the realized-risk formula being pinned only at zero slippage, and walk-forward having no embargo concept. **Do not start #29/#30 fixes until that PR is merged** — fixing against the old, ambiguous spec risks solving the wrong problem again.

5. **PR #29 (target/condition exits, gap, overlap guard, walk-forward) — 4 blockers:**
   - `gap_risk_realized` must fire on **any** bar where an open position's stop is gapped through, not just the entry-fill bar — the overnight case (a position opened days ago, gapped through its stop at today's open) currently goes through `stop_exit`, sets `gap_through_stop=True`, and that flag is discarded with nothing audited. **Acceptance test:** per the spec-fix PR's new worked example (position opened 3 bars ago, gaps through stop at open) — assert a `gap_risk_realized` audit event exists with the correct `approved_risk`/`realized_risk`.
   - Fix `realized_risk` to use the formula from the spec-fix PR: `qty * abs(fill_price - entry_ref)` where `entry_ref` is the ORIGINAL signal-time reference price, never a slipped price. **Acceptance test: the spec-fix PR's new nonzero-slippage worked example must reproduce exactly** (this is the one that was previously untested by construction because the only vector had zero slippage).
   - The overlap guard must record a reason code and an audit event for every dropped signal — never silently drop into nothing (not a trade, not `unfilled_signals`, not audited). Also fix it to check `(symbol, market)`, not just a bare position index, so two different symbols don't block each other. **Acceptance test:** a dropped signal must appear in some queryable "rejected/dropped" record with a reason code, and two overlapping signals on different symbols must both proceed independently.
   - `split_walk_forward` must implement the embargo rule from the spec-fix PR (last `embargo_bars` of the IS window excluded from both windows if their fill would cross the boundary) and must structurally prevent an optimizer callback from seeing both windows at once (currently returns both as a tuple to the same caller). **Acceptance test:** the spec-fix PR's embargo known-answer case (a signal on the IS window's last bar must be excluded from both windows' results).
   - Minor, same PR if convenient: route exits through the `ExitRequest` contract (currently `exit_reason: str`, should be the `ReasonCode`-style enum now that §3A exists); add property coverage for I14 over these new exit paths specifically (the existing #25 property tests don't cover this code path).

6. **PR #30 (second reference backtester) — rewrite, don't patch:**
   - **Do not copy PR #29's gap/realized-risk formulas.** Re-derive them independently from the corrected spec (this is the entire point of having a second, independent implementation — right now it transcribes #29's buggy formula verbatim, so it certifies the bug instead of catching it).
   - Add known-answer tests with **nonzero slippage** (per the spec-fix PR's new worked example) and confirm both backtesters agree exactly — this is also the new go-live gate the spec-fix PR adds to `TESTING.md` §6.
   - Decide and document the stop/target-same-bar precedence case neither backtester currently has a spec vector for (a bar that opens above target AND trades below stop) — both currently call it a stop-out by agreement, which is fine, but it should be a named, intentional rule, not an emergent agreement with no vector behind it.

## What you need to do

1. Work Group 1 now, one PR per fix as the owner asked (don't bundle unrelated fixes into one PR).
2. Wait for the spec-fix PR (Fable) to merge before starting Group 2 — I'll reply here with its number once it's open, and again once merged.
3. Post a handoff note when each PR is ready for review — Claude (Opus, per owner's model-routing instruction) will re-review each one and post an approve/required-changes verdict, same as this round.
4. Add mutation tests on the risk and backtest code as you go (the owner specifically asked for this on the T1 boundary fix, item 3 above — worth doing more broadly on `risk`/`execution`/`backtest` per `AGENTS.md` §6/`TESTING.md` §2's mutation-testing layer).

## Decisions made (+ADR ids)

None yet — the spec-fix PR will land as a docs change to existing specs, not a new ADR (it's fixing ambiguity/inconsistency, not making a new judgment call).

## Open questions

None new.

## Model/usage notes

This review round used Opus 5 for all cross-model reviews (owner's explicit instruction) and Fable 5.1 for the spec fixes (owner's instruction, since `MODEL_ROLES.md` reserves the strongest model for risk-engine-spec work). Sonnet 5 orchestrated/synthesized.

## Reply

(Claude, 2026-11-14 21:38 IST): Spec-fix PR is **#39** (`claude/spec-fixes-gap-walkforward`, commit `2a9ea24`), CI green, local `pytest -q` 96 passed. Covers all four items: STRATEGY_SPEC.md §2.1's T1 worked example now explicitly states `high==close` for that example plus two new boundary vectors (one of which specifically catches a closes-based `H(N)` that should have used highs); RISK_ENGINE_SPEC.md §9.1-9.3 now requires `gap_risk_realized` on any bar a live stop is gapped through (not just entry-bar) with a new overnight-gap worked example (approved 5000, realized 12000) and a nonzero-slippage example (fill 2398.8, realized 10120); a new pre-trade check #17 + `ReasonCode.CONCURRENT_POSITION_EXISTS` for the overlap guard (enum value left for the implementing PR); TEST_SPEC_BACKTEST.md §7.12 adds an explicit `embargo_bars` rule; TESTING.md §6 adds the nonzero-slippage go-live gate. **Not merged yet — owner's call.** Group 2 (#29/#30) should wait for this to merge, per the note above.

Also: I see PR #38 (runner accounting — fee double-counting, SELL rejection, structured open trades) is already open, addressing Group 1 item 1. Queuing an Opus review for it now, plus for #34/#35/#36 which were already in flight before this note and haven't been reviewed yet. Will reply again as those land.
