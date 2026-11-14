# Handoff 0021 — rebase conflict resolution

- `main` is now `db2e4b4` (#38, #40, and #41 merged).
- Corrected primary follow-up branch `codex/fix-gap-risk-walkforward` was rebased and repaired at `7e94c01`; full pytest, Ruff, and mypy pass.
- Corrected reference follow-up branch `codex/fix-reference-spec-equivalence` was rebased at `f69b165`; its nonzero-slippage known-answer remains, and full pytest, Ruff, and mypy pass.
- The earlier conflict resolution accidentally risked dropping merged runner contracts; the branch was restored from current `main` before reapplying only overlap/embargo changes.

Exact stopping point: #42 and #43 are pushed on current-main bases and awaiting fresh GitHub CI. Handoffs itself is clean at this note; any PR targeting the notes branch must be rebased against `origin/handoffs` rather than `main`.
