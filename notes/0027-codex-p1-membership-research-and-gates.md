---
id: 0027
from: codex
to: owner
date: 2026-11-15  (IST)
subject: P1 membership route researched; remaining owner gates
status: needs-human
refs: ["codex/p1-restructure-spec", "5f170c5", "docs/specs/DATA_SOURCES.md", "docs/decisions.md", "docs/BUILD_ORDER.md", "ADR-0023", "ADR-0024", "ADR-0025"]
---

## Context

The owner asked Codex to continue P1 autonomously except where an owner decision
is required. P1 now follows the five-stage plan in BUILD_ORDER.md. Historical
candles use Upstox only under ADR-0023; the live provider remains undecided.

## What I did

- Checked the official NSE Indices data-subscription page. It advertises
  historical constituent data for quantitative research and directs end-of-day
  constituent enquiries to `indices@nseids.co.in`.
- Checked the official reconstitution calendar, methodology, and press-release
  archive. These can support event-by-event reconstruction, but are not a
  ready-made, completeness-guaranteed membership series.
- Recorded the exact data, coverage, license, and price questions for an NSE
  Indices inquiry in `docs/specs/DATA_SOURCES.md`. The inquiry was not sent.
- Clarified that Upstox is the sole P1 candle source and is separate from the
  still-unresolved membership/corporate-action metadata sources.
- Added proposed ADR-0025 to state the owner gates explicitly.
- Updated the handoff status board to reflect the P1 restructure and blockers.

## Where I stopped (exact)

- Code/docs branch: `codex/p1-restructure-spec`
- Last commit: `5f170c5` (local; not pushed or opened as a PR)
- Files changed: `docs/specs/DATA_SOURCES.md`, `docs/decisions.md`
- Verification: `git diff --check` passed; documentation-only change
- Handoff branch: this note and STATUS.md update are being recorded separately.

## What you need to do

1. Choose the membership path: authorize requesting a quote and written terms
   from NSE Indices (recommended for a defensible full-universe study), or
   accept only a clearly labeled representative-sample/provisional study with
   survivorship caveat. No request or purchase has been made.
2. Choose the common research sizing assumptions: starting capital and
   per-trade risk percentage. These make rupee results comparable; metrics will
   still include percentage returns and risk-adjusted measures.
3. Confirm daily swing trading as the target horizon, or specify the horizon
   that P1 should evaluate.

Recommendation: prefer the licensed point-in-time dataset if its coverage and
terms are suitable. Keep any current-membership-only results explicitly
provisional. Do not use previously examined 2016-2026 data as the untouched
holdout; reserve a genuinely unread future or otherwise unexamined chronological
range before running the pre-registered candidate library.

## Decisions made (+ ADR ids)

- Upstox is the only P1 historical candle source (ADR-0023); P3 live provider
  remains undecided.
- P1 is structured as frozen data foundation, pre-registered candidates,
  corrected evaluation/registry, one-shot holdout, and regime-gated activation
  (ADR-0024).
- No membership source has been purchased, no license accepted, and no
  survivorship-bias caveat waived (proposed ADR-0025).

## Open questions

- Will the owner authorize an NSE Indices quote/terms inquiry and later decide
  on any fee, or accept a provisional representative sample?
- What starting capital and per-trade risk should comparisons use?
- Is daily swing trading the intended target horizon?

## Model/usage notes

- No external message was sent and no paid service was started.
- No code, downloader, or strategy run was added in this slice.

## Reply

(Owner appends the decision here.)
