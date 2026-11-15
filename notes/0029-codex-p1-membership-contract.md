---
id: 0029
from: codex
to: owner
date: 2026-11-15 08:18 IST
subject: P1a point-in-time membership manifest contract implemented
status: needs-human
refs: ["codex/p1-restructure-spec", "6a24c30", "docs/specs/INDEX_MEMBERSHIP.md", "docs/specs/DATA_SOURCES.md", "docs/BUILD_ORDER.md", "ADR-0024", "ADR-0025", "note-0027"]
---

## Context

The official NSE Indices subscription route is the likely source for historical
membership, but coverage, licence terms, and cost are not public. P1 needs a
schema that can validate an authorized dataset without treating a partial
sample as complete.

## What I did

- Added `MembershipInterval` and `MembershipManifest` in
  `trading.storage.membership`.
- Added half-open coverage and membership semantics, Indian ISIN format and
  checksum checks, source notice provenance, interval overlap checks,
  cross-index disjointness, and deterministic point-in-time lookup.
- Complete manifests require verified intervals and exactly 50 constituents
  in both indexes at every membership boundary. Partial manifests may have
  fewer than 50, never more than 50, and remain explicitly `complete=False`.
- Added blind contract tests authored by GPT-6.1 Terra, plus boundary tests
  for the partial-manifest member cap. Independent Terra review found no
  blocking findings after the cap fix.
- Documented that the contract validates supplied records; it does not verify
  a vendor's licence, coverage, or completeness claim. No source data is loaded.

## Where I stopped (exact)

- Branch: `codex/p1-restructure-spec`
- Last commit: `6a24c30` (pushed to origin; PR creation unavailable because `gh`
  is not installed)
- Tests/checks: full pytest suite passes; Ruff lint/format pass; mypy passes;
  `git diff --check` passes
- Working tree: clean at the time of handoff

## What you need to do

Please answer note 0027's three P1 decisions:

1. Authorize an NSE Indices coverage/licence/price inquiry (no purchase), or
   keep work limited to an explicitly provisional sample with survivorship
   caveat.
2. Set capital and per-trade risk, authorize a research-only assumption, or
   defer rupee sizing.
3. Confirm daily swing horizon or specify another horizon.

Once membership data is authorized, compare its coverage and source identifiers
against the manifest contract before ingestion. Do not use partial membership
as a survivorship-free universe.

## Decisions made (+ ADR ids)

- P1 candles remain Upstox-only (ADR-0023); the P3 live provider remains
  undecided.
- Membership interval semantics and validator are implemented, but no source,
  licence, universe scope, or survivorship-bias caveat is selected (ADR-0025
  remains proposed).
- The 2016-2026 sample already examined cannot serve as the unseen holdout under
  ADR-0024; a new unread range must be selected after the data window is known.

## Open questions

- See note 0027 for membership, sizing, and horizon decisions.
- What covered historical range does the authorized membership source offer?
- Which new chronological interval can be reserved as genuinely unread holdout?

## Model/usage notes

- Blind tests: GPT-6.1 Terra; implementation: Codex; final review: GPT-6.1 Terra.
- No data subscription, external inquiry, real-order path, or provider change.

## Reply

(Owner appends the decision here.)
