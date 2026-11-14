# Handoff 0020 — self-verification after review feedback

Claude declined to review further, so Codex reproduced and fixed the remaining issues directly.

- PR #39 is merged at `003a604`; all review branches were rebased onto that main.
- PR #40 branch is now `29b5055`; its stale-doc problem is resolved by rebasing, I14 is exercised through `FakePaperBroker.apply_exit`, serialization round-trip is covered, and `pytest`, Ruff, and mypy pass locally.
- PR #41 branch is now `02d2613`; randomized ADX and tie-break mutation coverage remains green after rebase.
- PR #38 branch is now `c8170c9`; runner/reference fee accounting and open-trade marks pass the full local suite after rebase.
- PR #35 branch is now `ac256d8`; condition fill-bar stop precedence plus all-bar/overnight gap-risk audit are covered. Full pytest, Ruff, and mypy pass.
- PR #36 branch is now `6fe040c`; copied `runner.py` was removed. It intentionally depends on the actual #35 runner behavior; run CI after #35 is merged before merging #36.
- Corrected-spec #29 follow-up remains on `codex/fix-gap-risk-walkforward` (`2e4e5a4`): overnight gap risk, realized-risk reference price, overlap audit/instrument scope, and embargo split. Full local suite passes.
- Corrected-spec #30 follow-up remains on `codex/fix-reference-spec-equivalence` (`7d0b0d6`): independent reference formula and nonzero-slippage 10120 known-answer. Its existing equivalence tests require the fee-corrected runner from #38, so merge/order is #38 before #30.

Exact stopping point: branches are pushed and locally verified; GitHub CI must be rerun on the rebased heads. Merge order is #35 → #36, #38 → #30, and #40/#41 after green checks; owner performs merges.

## CI update

- PR #35 head `0bb5739`: GitHub `test` passed.
- PR #36 head `dad92fc`: GitHub `test` passed after rebasing onto #35.
- PR #38 head `c8170c9`: GitHub `test` passed.
- PR #40 head `29b5055`: GitHub `test` passed.
- PR #41 head `02d2613`: GitHub `test` passed.
