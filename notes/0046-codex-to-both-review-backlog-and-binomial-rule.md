---
id: 0046
from: codex
to: both
date: 2026-11-16 13:15 IST
subject: review backlog blockers and dynamic binomial P1d gate
status: open
refs: ["PR #54", "PR #56", "PR #57", "PR #58", "PR #59", "PR #60", "PR #61", "PR #62", "PR #63", "PR #64", "PR #66", "e3ecba2"]
---

## Context

The owner requested review of Claude PRs #54 and #56–#62, replacement of
the P1d fixed profitable-instrument rule with a dynamic one-sided binomial
test, and P1b/RPF catalog finalization only after the review backlog and
Claude review of #63/#64/#66 clear.

## What I did

- Reviewed #54 and #56–#62 against their current heads. GitHub prevents the
  workspace identity from submitting a formal review because it is recorded
  as a co-author, so the findings are posted as explicit `BLOCKER` PR
  comments instead.
- #54: no new blocker found in its current head.
- #56: reported invalid aggregation of per-signal percentage returns labelled
  as realised P&L.
- #57: reported that an incomplete/empty scan silently removes active
  shortlist entries instead of failing closed.
- #58/#61: reported stale stacked branches that can reintroduce #54's fixed
  corporate-action/risk-allocation code; rebase after #54/main is required.
- #59: reported that existing-spend-only budget checking can exceed the hard
  cap, and provider exceptions are not audited.
- #60: reported duplicate positions being hidden by dictionary overwrites in
  reconciliation.
- #62: reported stale factual claims about PR/CI status.
- Implemented the P1d cross-instrument gate in `e3ecba2` on #66. It now
  computes `P(X >= K | X ~ Binomial(N, 0.5)) < 0.05` from the frozen
  snapshot's actual complete `N`; incomplete coverage remains inconclusive.
  The rejection spec, evaluator, audit reason, and regression tests changed
  together. Backtest tests, Ruff, format, and mypy passed.
- Important correction to the owner's approximate example: 31/50 has
  one-sided upper-tail probability 5.946%, so it does **not** pass a strict
  `< 5%` test. The minimum passing count is 32/50 (3.245%). This is documented
  as the auditable worked example, rather than weakening the stated rule.

## Where I stopped (exact)

- Branch: `claude/universe-evaluation-orchestration-v2` (PR #66)
- Last relevant commit: `e3ecba2` (followed by Claude's `a099e2e`)
- Next file/function: do not change `P1_CANDIDATES.md` or add RPF until the
  sequencing condition below is satisfied.

## What you need to do

1. Claude: address the blocker comments on #56–#62 and re-request review;
   rebase stacked #58/#61 rather than resolving safety conflicts ad hoc.
2. Claude: review #63, #64, and #66 before the catalog is reopened.
3. Codex: after the above review backlog is clear, create a new catalog
   version for the existing 15 variants plus one fully mechanical RPF
   hypothesis. Do not amend the already frozen catalog in place.

## Decisions made (+ ADR ids)

- No holdout result has been read, so the owner-authorized replacement of the
  `3 of 5` condition was recorded as a locked pre-result rule. It is still
  protected from post-result changes by `P1_REJECTION_RULE.md`.
- The strict mathematical rule, not the approximate “around 31/50” wording,
  governs the test boundary.

## Open questions

- None for the binomial rule. P1b/RPF finalization is deliberately pending
  the owner-specified review sequencing condition.

## Model/usage notes

- Codex review completed; no external paid services or live order paths used.

## Reply

(Receiver appends here; do not rewrite the sections above.)
