---
id: 0028
from: codex
to: owner
date: 2026-11-15 08:08 IST
subject: P1a split/bonus adjustment slice implemented and reviewed
status: needs-human
refs: ["codex/p1-restructure-spec", "1a31c8e", "docs/specs/CORPORATE_ACTIONS.md", "docs/BUILD_ORDER.md", "ADR-0023", "ADR-0024", "ADR-0025", "note-0027"]
---

## Context

Continuing P1 in phases under the owner's instruction to complete work that
does not need an owner decision. Note 0027 records the historical membership
source research and remaining owner questions.

## What I did

- Implemented `trading.storage.corporate_actions` as a pure, point-in-time
  adjustment for daily split/bonus candles, with Decimal arithmetic and
  original candle immutability.
- Added event identity and numbered revisions with publication dates. Each
  replay selects the latest version published by its as-of date; ambiguous
  revision order fails closed.
- Added synthetic known-answer coverage for ordinary/reverse splits, bonus
  issues, compounding, session-date timezone conversion, publication/effective
  boundaries, corrections, invalid actions, and double adjustment.
- Documented the upstream data and position-replay limitations. The transform
  is not wired into the Upstox dataset or treated as promotion evidence.
- Cross-model review by GPT-6.1 Terra found no blocking issues in the corrected
  version.

## Where I stopped (exact)

- Branch: `codex/p1-restructure-spec`
- Last commit: `1a31c8e` (pushed to origin; PR creation unavailable because `gh`
  is not installed in this environment)
- Tests/checks: 137 pytest tests pass; Ruff lint and format pass; mypy passes;
  `git diff --check` passes
- Files: `src/trading/storage/corporate_actions.py`,
  `tests/storage/test_corporate_actions.py`,
  `docs/specs/CORPORATE_ACTIONS.md`, `docs/specs/DATA_SOURCES.md`,
  `docs/BUILD_ORDER.md`
- Working tree: clean at the time of handoff

## What you need to do

The same decisions from note 0027 remain open:

1. Choose whether to authorize an NSE Indices quote/terms inquiry for full
   point-in-time membership, or accept only a clearly provisional sample with
   a survivorship-bias caveat. No inquiry was sent and no purchase made.
2. Set starting capital and per-trade risk for comparable research sizing.
3. Confirm daily swing horizon or specify another target.

The next non-owner work can continue on independent P1a pieces, but real Upstox
adjustment must wait until its raw-vs-adjusted price basis is established. The
authorized corporate-action ledger and split-position handling in both
backtesters also remain necessary before adjusted-data promotion evidence.

## Decisions made (+ ADR ids)

- Upstox remains the sole P1 India candle source (ADR-0023); P3 live provider is
  still undecided.
- P1 keeps the pre-registered discovery/validation/holdout structure
  (ADR-0024). Do not read the holdout before P1d.
- The transform only implements explicit split/bonus share ratios; dividends,
  rights, and other events are not guessed.
- No new paid provider or external message was initiated.

## Open questions

- See notes 0027 and ADR-0025 for membership, sizing, and horizon decisions.
- What authorized action source and Upstox adjustment-basis statement can be
  obtained for the six-symbol set and expanded Tier A universe?

## Model/usage notes

- Implementation authored by Codex; independent code review by GPT-6.1 Terra.
- No live order path or runtime data ingestion was added.

## Reply

(Owner appends the decision here.)
