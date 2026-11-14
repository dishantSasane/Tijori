# Handoff 0016 — Codex P1 known-fix PRs

**Status:** needs-human (merge/review gate)

## Completed

- PR #38 / `codex/fix-runner-accounting` (`970903d`): fee accounting is single-counted, SELL signals are rejected by the long-only runner, and end-of-data open positions are returned.
- `codex/fix-exit-id` (`a83bca4`): `ExitRequest.exit_id` is deterministic from position ID, reason, and bar timestamp; caller-supplied IDs are rejected; `apply_exit_quantity` and property tests enforce I14.
- `codex/fix-scorecard-adx-t1` (`a41e88c`): scorecard now reports average win/loss and expectancy; ADX equivalence uses a non-flat series; mutation sentinels cover the strict T1 boundary and fee double-counting.

Focused tests and the full suite pass on the latter two branches; Ruff formatting and lint are clean.

## Exact stopping point

The two new branches are pushed and awaiting PR/CI bookkeeping. Claude’s spec-fix PR #39 is open and CI-green but not merged. Do **not** start the gated #29/#30 work until #39 is merged. After merge, implement #29 (gap risk, realized-risk reference price, overlap audit, walk-forward leakage/embargo), then independently rewrite #30 formulas and add nonzero-slippage known-answer tests, plus broader risk/backtest mutation coverage.

The owner must review/merge the open PRs; agents must not push or merge `main`.
