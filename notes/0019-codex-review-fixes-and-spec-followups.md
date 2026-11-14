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

## CI/status poll (2026-11-14)

- PR #35: latest requested branch ref `12c8683`; CI `test` passed.
- PR #36: latest requested ref `213da0c`; no checks reported for the branch at poll time.
- PR #38: latest requested ref `8bd95ae`; CI `test` passed.
- PR #40: latest requested ref `ee2df4f`; no checks reported for the branch at poll time. The earlier failed run was lint-only: `tests/core/test_exit_properties.py:63:101` violated Ruff E501 (104 > 100 characters); the current branch ref must be rechecked after that fix.
- PR #41: latest requested ref `7693477`; CI `test` passed.
- PR #39 is merged at main commit `003a604`.
- PR #32 was a stray duplicate and is now closed without merge.

## Corrected follow-up PR bookkeeping (2026-11-14)

- PR #36 remains open at `dad92fc`; CI `test` passed.
- PR #42 (`codex/fix-gap-risk-walkforward`) is open at `2e4e5a4`; CI `test` pending.
- PR #43 (`codex/fix-reference-spec-equivalence`) is open at `7d0b0d6`; CI `test` pending.
- Original PR #29 and #30 are already merged; these corrected follow-ups are separate and must receive cross-model review before owner merge.
- PR #44 was the accidental `handoffs` → `main` PR; it was closed without merge because `handoffs` is the agent message board. Its README conflict was therefore intentionally not resolved.
- PR #43 was retriggered at `861e44b`; CI is pending.
