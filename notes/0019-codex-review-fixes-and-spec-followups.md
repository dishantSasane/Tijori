# Handoff 0019 — review fixes and corrected-spec backtester follow-ups

**Status:** ready-for-review (owner must wait for CI and cross-model review)

## Existing PR branches updated

- PR #35 branch `codex/p1-condition-next-open-v2`: commit `12c8683` checks the condition exit's next-open fill bar for its own stop first, so a stop/gap takes precedence over the condition exit.
- PR #40 branch `codex/fix-exit-id`: commit `ee2df4f` wires I14 through `ExitRequest.apply_to_position` and `FakePaperBroker.apply_exit`, and permits only the derived ID during serialization round-trip. Focused tests pass.
- PR #41 branch `codex/fix-scorecard-adx-t1`: commit `7693477` adds a randomized 20–30-bar ADX equivalence property and a directional-movement tie-break sentinel; removes the vacuous fee test. Focused tests pass.
- PR #38 branch `codex/fix-runner-accounting`: commit `8bd95ae` fixes reference-runner fee accounting too, supports asymmetric entry/exit brokerage, and records mark/unrealized values for open trades. The accidental gap-risk commit was reverted from this branch (`1b8392f`).

PR #32 is a stray duplicate and should be closed without merge.

## Corrected-spec follow-ups now unblocked by merged PR #39

- Dedicated gap/primary branch `codex/fix-gap-risk-walkforward` has commits `2c2b9d9` and `2e4e5a4`: overnight gap-risk audit using the original `entry_ref`, embargo-aware walk-forward splitting, overlap audit records, and instrument-scoped overlap guards.
- Dedicated reference branch `codex/terra-reference` has commit `213da0c`, removing copied primary runner logic from PR #36. Its reference tests now call the actual primary runner rather than bundling a duplicate.
- Independent reference formula branch `codex/fix-reference-spec-equivalence` has commit `7d0b0d6`, with corrected all-bar gap-risk accounting and a nonzero-slippage known-answer (`realized_risk=10120`).

## Exact stopping point

All listed branches are pushed. The next action is CI/review polling and resolving any failures, followed by owner review/merge. PR #29/#30 corrected-spec follow-ups must be reviewed for formula independence and the nonzero-slippage gate; do not merge them automatically.
