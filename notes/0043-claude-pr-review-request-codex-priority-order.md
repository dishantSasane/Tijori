# 0043 — Claude: cross-model review requested on every open PR, priority order by risk

Status: needs-codex-review (not needs-human — this is a request to the other
agent, not an owner decision).

## Why this note exists

Owner ran a 4-stage audit of this repo (PR review, merge, phase audit, owner-
decision inventory; full writeup in `docs/STATUS_AUDIT.md` on `main`, PR #62).
Finding: **every open PR is Claude-authored**, so per AGENTS.md §5 ("Author
!= reviewer... critical modules always need a cross-model review") none of
them can be self-approved by Claude. Only #53 (Codex-authored, Claude-
reviewed) was mergeable and has been merged.

Before asking for review, I fixed the one PR with *known, already-identified*
bugs (#54) rather than handing Codex something to re-discover, and got CI
actually running on two PRs that had never had a CI run at all (#58, #61 —
stacked on non-`main` branches, so `pull_request: branches: [main]` never
fired). **All 8 PRs below are now CI-green.**

## What changed since note 0042

- **#54** (`claude/sleeve-allocation-and-adapters`): the independent review
  that found 3 HIGH blockers (see PR comments) is fixed at commit `4dd905b`
  (+ later commits). Specifically:
  1. `us_equity_corporate_actions.py`'s dividend price factor was computed
     from each adjusted candle's own close instead of one fixed factor from
     the close immediately before the ex-date — every pre-dividend bar got
     a different, wrong factor. Fixed to compute one factor per dividend
     action from the correct reference close, with a new known-answer test
     (`test_dividend_factor_is_uniform_across_all_pre_ex_date_bars`).
  2. `us_equity_loader.load_history` defaulted to `adjustment="raw"` and
     wrote bars straight to storage with no adjustment step, so normal
     output was unadjusted. Default flipped to `adjustment="all"` (Alpaca's
     own server-side adjustment); `"raw"` stays available for an explicit
     cross-check pass.
  3. `risk/engine.py`'s sleeve-allocation check (check 8/9) only rejected
     when the sleeve was *already* over cap, not when the proposed order's
     post-trade allocation would cross it. Now computes
     `proposed_allocation_pct = allocation_used_pct + this_order_pct` and
     rejects on that, with a new regression test
     (`test_check_8_rejects_order_that_would_cross_cap_post_trade`).
  Full suite passes (all tests), ruff check/format clean, mypy clean on all
  three touched modules. **Please re-run your independent review against the
  new head before this merges — don't take my word that the fix is correct.**
- **#58, #61**: base retargeted from a stacked feature branch to `main` (via
  REST API, since `gh pr edit --base` was hitting an unrelated GraphQL
  Projects-classic deprecation error) so the CI workflow's
  `pull_request: branches: [main]` trigger actually fires — it never had on
  either PR before. This surfaced one real, pre-existing `ruff format`
  violation in a lesson doc's embedded code block (same file, inherited
  through the stack), now fixed on both branches. Both are CI-green.
  **Note the base retarget is cosmetic for CI purposes only** — it doesn't
  change the real dependency order below; #58 still logically depends on
  #54's content and #61 on #58's.

## Priority order for your review (risk-ordered, not request-ordered)

1. **#54** — `claude/sleeve-allocation-and-adapters` → `main`. Highest
   priority: touches `risk/engine.py` (allocation cap check) and the
   corporate-action adjustment layer that feeds every backtest's price
   series. This is exactly the kind of correctness bug your last review
   caught — please verify the fix, not just that tests pass.
2. **#58** — `claude/p5-crypto-us-sleeves` → `main` (base retargeted;
   logically stacks on #54). Adds crypto/US strategy instances and an
   Accounts page. Touches strategy wiring, not the risk engine itself, but
   depends on #54's adjustment-layer fix being correct.
3. **#61** — `claude/p8-expansion-sleeves` → `main` (base retargeted;
   logically stacks on #58). Adds MCX/NSE-currency/memecoin sleeves and the
   ML ranker. Worth a careful look at `risk/engine.py`'s new
   `ModeGate.PAPER_ONLY_SLEEVES` gate (new risk-path code) and the ML
   ranker's scope boundary (ADR-0034) — same two items flagged in note 0042.
4. **#56** — `claude/p3-live-paper-dashboard` → `main`. Display/reporting
   only (`dashboard/`, `src/trading/reporting/`) — no risk, execution, or
   broker code. Lower priority than 1-3.
5. **#57** — `claude/p4-scanner-stocks-page` → `main`. Scanner/shortlist
   generation and a Stocks page (`src/trading/scanner/`, `dashboard/`) — also
   no risk/execution code, but produces candidates a human reads, not an
   automated decision path. Similar priority to #56. **Known conflict**:
   both #56 and #57 touch `dashboard/_data.py` independently (flagged in
   note 0037) — whichever merges second will need to reconcile that file.
6. **#59** — `claude/p6-brain-news` → `main`. Brain/News: LLM-advisory code
   (never in the hot path per AGENTS.md §4.6) plus a budget guard. Not risk
   or execution code, but explicitly flagged mandatory for review in note
   0039 since it's LLM-boundary code — `BudgetGuard.allow()` fail-closed
   behavior and `parse_verdict`'s schema strictness are the two things worth
   a close look.
7. **#60** — `claude/p7-go-live-readiness` → `main`. Reconciliation module
   and go-live checklists — execution-adjacent (kill-switch engagement on
   mismatch) but tested only against a fake broker (correctly, per AGENTS.md
   §4.4) and places no real order. Review the kill-switch trigger condition
   in `src/trading/reconciliation/`.

(`#53` already merged; `#62`, the status-audit doc itself, is docs-only and
doesn't need cross-model review — nothing in AGENTS.md §5 requires it for a
PR touching no code.)

## For the next session (either agent)

- Please leave your review as PR comments (per existing convention on #53/
  #54) rather than only in a handoff note, so the owner can see it attached
  to the diff.
- Merge order, once reviews land, should follow the dependency chain:
  #54 → #58 → #61 (one at a time, confirming `main` CI stays green after
  each), then #56/#57/#59/#60 in any order (independent of that chain and of
  each other), resolving the `dashboard/_data.py` conflict whichever of
  #56/#57 merges second.
- Owner-decision inventory (17 items, not for either agent to decide) is in
  `docs/STATUS_AUDIT.md` on `main`.

Agent: claude (sonnet-5)
