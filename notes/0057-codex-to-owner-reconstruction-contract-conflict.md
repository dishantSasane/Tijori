---
id: 0057
from: codex
to: owner
date: 2026-11-16 00:00 IST
subject: Identity gaps resolved; reverse-anchor reconstruction conflicts with membership contract
status: needs-human
refs: ["0056", "docs/specs/INDEX_MEMBERSHIP.md", "docs/specs/DATA_SOURCES.md", "PR #71"]
---

## Context

The owner resolved the three historical identity gaps with primary-source facts: LTIM is `INE214T01019`; historical Tata Motors maps to the continuous original identity now symbolled TMPV (`INE155A01022`), not the 2025 commercial-vehicles entity; ZOMATO/ETERNAL is the same `INE758T01015` identity.

## What I did

- Re-ran the master-resolution validation with the owner-supplied mappings.
- Result: all 60 scheduled-chain constituent identities resolve; all 60 ISINs are checksum-valid and unique. There are zero unresolved symbols.
- Reconfirmed that the supplied reverse delta chain has exactly 50 members at every boundary.

## Where I stopped (exact)

- No snapshots, corporate-action fetches, register entries, reconciliation, ADR, split-spec change, or PR #71 change were made.
- The requested construction remains in direct conflict with the checked-in membership contract. `docs/specs/INDEX_MEMBERSHIP.md` states that a current constituent list is never used to fill earlier history and that a source notice must be dated no later than its interval's effective start. An October-2026 anchor walked backward to 2021-2024 fails both provenance rules even when the arithmetic is exact.
- `docs/specs/DATA_SOURCES.md` also says not to load a real manifest before historical coverage, identifier mapping, and research/backtesting licence are confirmed and recorded. The identifier mapping is now solved; the other two requirements are not recorded.

## What you need to do

1. Choose one of these explicit paths:
   - **Recommended:** retain the contract and supply/authorize contemporaneous source notices or a licensed historical constituent dataset for each represented interval. Then I can create a complete, reviewed manifest and snapshots.
   - **Methodology change:** approve an ADR/spec change that permits an owner-supplied later-anchor reverse reconstruction, labels it `complete: false` / non-authoritative, records all known limitations, and prohibits using it for claimed real/backtest results. This can support mechanical development only, not P1a closure.
2. Separately, identify the permitted historical corporate-action evidence route for 2021-2024. ADR-0044 records that Upstox's endpoint does not cover these years. A ledger cannot be asserted complete from empty/partial responses.

## Decisions made (+ ADR ids)

- None. The owner supplied valid identity mappings, but the requested use conflicts with the currently accepted data contract, so no silent exception was made.

## Open questions

- Does the owner approve the limited non-authoritative reconstruction path, or prefer an authoritative historical membership dataset? Recommendation: authoritative evidence for any result-bearing use.

## Model/usage notes

- Validation used the existing Upstox complete master only; no secret was read, printed, or saved.

## Reply

