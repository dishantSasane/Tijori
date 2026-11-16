---
id: 0056
from: codex
to: owner
date: 2026-11-16 00:00 IST
subject: Nifty 50 scheduled-only reconstruction dependency audit
status: needs-human
refs: ["docs/specs/INDEX_MEMBERSHIP.md", "docs/specs/DATA_SOURCES.md", "docs/decisions.md#ADR-0044", "PR #71"]
---

## Context

The owner supplied an October 2026 Nifty 50 anchor and a scheduled March-2021--September-2026 delta chain, and requested exact monthly Nifty 50 snapshots for 2021-01--2024-12, a deduplicated ISIN universe, then corporate-action coverage work. Nifty 100 is deferred.

## What I did

- Ran the existing authorised Upstox complete-instrument-master loader locally. The response contained 2,763 NSE EQ entries. It resolved 58 of the 60 supplied constituent identities directly, including the former members GAIL, IOC, SHREECEM, DIVISLAB, BPCL, BRITANNIA, INDUSINDBK, HEROMOTOCO, and WIPRO.
- Confirmed the supplied chain reverses cleanly: the anchor and every reverse boundary contains exactly 50 members. Its 2021-2024 scheduled-only union is 60 constituent identities.
- Audited all prerequisites together before writing any snapshot, ledger, ADR, split spec, or PR #71 change.

## Where I stopped (exact)

- Branch: `codex/freeze-p1a-historical-splits` (no changes made for this work).
- Current full master has no `LTIM` or `LTIMINDTREE` EQ row, so the historical LTIM identity/ISIN cannot be derived from it.
- `ZOMATO` is absent under that historical symbol; the owner-supplied rename maps it to current `ETERNAL` (`INE758T01015`), but that identity mapping has not yet been captured as independently reviewed evidence.
- More importantly, the 2026 anchor uses `TMPV` (`INE155A01022`). A 2021-2024 Nifty 50 interval instead needs the historical Tata Motors identity/ISIN. That non-scheduled identity/corporate restructuring event is absent from the scheduled delta chain. Treating TMPV as its 2021 identity would manufacture a false historical ISIN interval.
- The repository's existing membership contract explicitly forbids loading a real complete manifest before delisted-name/identifier coverage and intended research/backtesting licence are confirmed (`docs/specs/INDEX_MEMBERSHIP.md`, `docs/specs/DATA_SOURCES.md`). The owner-approved scheduled-only simplification accepts missed membership events, but does not authorize inventing missing identity mappings.
- Existing stored daily data and corporate-action responses cover only the five-symbol pilot. Upstox's corporate-action endpoint was already empirically shown to return only 2025-2026 events and cannot supply the requested 2021-2024 ledger (ADR-0044). Thus a full-register normalization, independent event verification, and meaningful preflight cannot yet run.

## What you need to do

1. Supply or approve an authoritative, locally retained identity mapping for `LTIM` and the Tata Motors historical constituent identity/ISIN used during 2021-2024. The rename mapping `ZOMATO` -> `ETERNAL` should be recorded in that same evidence package.
2. Decide whether the project source gate in `INDEX_MEMBERSHIP.md` is to remain applicable. Recommendation: keep it; mark the eventual scheduled-only manifest partial/unreviewed unless the owner supplies evidence sufficient for the missing identities and permits its research use.
3. Provide a permitted, historical corporate-action evidence route for 2021-2024 (manual company/official filing packets are suitable if individually retained). Upstox cannot fill this gap. Until then, coverage must remain `0 verified`, not zero-filled.

## Decisions made (+ ADR ids)

- None. No ADR was written because the required inputs are incomplete and the owner instructed not to touch `RESEARCH_SPLITS.md` or PR #71.

## Open questions

- Should the owner supply the three identity mappings as an auditable local CSV/PDF packet, or approve a specifically documented permitted primary-source lookup? Recommendation: local evidence packet, then create a partial scheduled-only manifest with `complete: false` until its source/licence gate is resolved.

## Model/usage notes

- No secrets were printed or persisted. The public Upstox master request required no credential.

## Reply

