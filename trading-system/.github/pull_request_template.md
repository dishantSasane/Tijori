## Plain-language summary
<!-- For a smart beginner: what does this do and why does it exist? -->

## What changed
<!-- Bullet list. Link specs: docs/... -->

## Spec / phase
<!-- e.g. docs/BUILD_ORDER.md P1 — backtester engine -->

## Author model / reviewer model
- Author: <!-- e.g. Codex GPT-6.1 Sol -->
- Reviewer (must be a different model; other company for critical modules): <!-- -->

## Safety checklist (AGENTS.md §4)
- [ ] No real-order path reachable in paper mode or from tests
- [ ] No secrets, keys, or personal data
- [ ] Fails closed on bad/missing/stale data
- [ ] No look-ahead; signals on closed bars, fills next open + costs
- [ ] LLM output (if any) is schema-validated and advisory only

## Tests
- [ ] Unit tests
- [ ] Property/invariant tests (critical modules)
- [ ] Blind tests written from the spec by a different model (critical modules)
- [ ] CI green

## Lesson
- [ ] `docs/learn/NN-*.md` added (milestones only) / N/A

## Needs human decision
<!-- "none" or a precise question for the owner -->

## Handoff
- [ ] Handoff note written/updated on the `handoffs` branch (if another agent must act)
