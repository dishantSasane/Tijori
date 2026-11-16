# 0045 — Claude: P1 switched from fixed five-symbol pilot to real selector output; one owner decision still blocking a real broad-universe evaluation — PR #63/#64/#66

Status: needs-human (one specific decision named below) + needs-codex-review
(add #63/#64/#66 to the review queue from notes 0043/0044).

## What happened, in order

1. **Real corporate-actions fetch run** (PR #64) with the owner's fresh
   Upstox token. Hard finding: the endpoint has no date-range parameter and
   only returns 2025-2026 events for all five Tier A symbols — it cannot
   supply 2010-2015 history by its own documented design. Fixed two real
   gaps found while doing this: `run_p1_daily_candidate` never exposed
   `action_register`/etc. at all (real candles could only hard-fail, no
   way to ever pass), and the share-action block now bypasses correctly
   when candles are already adjusted (`adj_factor` set).
2. **Full-universe selector run twice more against real data** (PR #63),
   surfacing two genuine at-scale-only failures the owner decided on each
   time: (a) Upstox omits the row entirely for an illiquid instrument's
   no-trade day — decoded as a confirmed zero only when isolated (immediate
   neighbors present); (b) a genuine multi-day gap on one instrument used
   to abort the *entire* snapshot — now excludes only that instrument
   (`unresolved_data_gap_in_lookback_window`). **The full real
   2,763-instrument run now completes cleanly: 50 selected, 238 excluded,
   206 isolated no-trade days decoded, 0 fetch errors.**
3. **P1 switched from the fixed five-symbol pilot to the real selector
   output** (PR #63 + #66). Audited exactly how deep the five-symbol
   constraint ran first: the backtest/ranking core was already
   symbol-agnostic; only three places were locked — `action_register.
   PilotSymbol` (now `NseEquitySymbol`, broadened), `evaluation_manifest`'s
   exact-set check (now accepts a broader set with a `universe_reference`),
   and `promotion.py`'s rejection threshold.

## The one thing still blocking a real broad-universe P1 evaluation

**`docs/specs/P1_REJECTION_RULE.md`'s "3 of 5 profitable instruments / 2 of
3 time blocks" threshold is the pre-registered-before-any-holdout-result
P1d decision rule** — the spec itself says "Do not change the candidate,
costs, universe, or boundaries after this result." Since no real holdout
has ever been read yet, widening the universe now is procedurally fine,
but scaling "3 of 5" into a new fraction for a ~50-instrument universe is
a numeric methodology choice, not a mechanical rescale — I did not make
that choice.

**Owner decision needed:** pick and pre-register (frozen, written before
any broader-universe holdout is read) a new majority threshold — e.g. what
fraction of ~50 instruments must be profitable, and whether the time-block
count/size (currently 3 blocks) should also change — as a properly
versioned successor to `P1_REJECTION_RULE.md`. Until this exists, the
broader-universe mechanics (PR #63/#66) are real and tested, but nothing
can actually be evaluated pass/fail against the broad universe.

## For the next session (either agent)

- Add PR #63, #64, #66 to the cross-model review queue (notes 0043/0044),
  in that dependency order (#64 and #63 are independent of each other;
  #66 depends on #64 only, not #63).
- `docs/decisions.md` ADR-0030 through ADR-0034 (on PR #63) record every
  decision above in full, including the Upstox-endpoint hard finding and
  the explicit "did not touch the rejection threshold" boundary.
- Once the owner picks the new threshold, it should land as a new,
  separately versioned rejection-rule doc, not an edit to the existing
  frozen `P1_REJECTION_RULE.md` — same immutable-version discipline as
  `STRATEGIES.md` §6.

Agent: claude (sonnet-5)
