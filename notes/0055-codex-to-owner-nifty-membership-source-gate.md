---
id: 0055
from: codex
to: owner
date: 2026-11-16 20:00 IST
subject: Nifty 50/100 historical-membership collection blocked by official terms and missing baseline
status: needs-human
refs: ["docs/specs/RESEARCH_UNIVERSE.md", "ADR-0026", "https://www.niftyindices.com/terms-of-use", "https://niftyindices.com/resources/index-rebalancing-schedule"]
---

## Context

The owner proposed replacing the custom historical turnover universe with
point-in-time Nifty 50/100 membership reconstructed from 2021–2024
reconstitution circulars.

## What I did

- Checked NSE Indices' official reconstitution calendar: Nifty 50 and Nifty
  100 are normally reconstituted semi-annually, at the last working day of
  March and September.
- Checked NSE Indices' official Terms of Use before collecting any circulars.
- Did not download/parse circulars, materialize snapshots, fetch actions, run
  a backtest, or change `RESEARCH_SPLITS.md` / PR #71.

## Where I stopped (exact)

- The official Terms prohibit systematic or automated collection, scraping,
  mining, extraction, and harvesting without express written consent.
- A series of 2021–2024 change circulars is not by itself sufficient to
  reconstruct January 2021 membership: it needs a complete point-in-time
  Nifty 50 and Nifty 100 baseline immediately before 2021-01-01, plus any
  ad-hoc replacement notices between scheduled reviews.

## What you need to do

1. Choose one:
   - provide written permission/licence from NSE Indices for this bounded
     archival/research collection; or
   - manually provide the circular PDFs and the two pre-2021 constituent
     baselines (including all ad-hoc replacement notices), which the project
     may then parse locally; or
   - choose another authorized dataset/source.
2. Confirm whether the intended universe is the Nifty 100 alone (which
   already contains Nifty 50) or the union is merely an audit view. The union
   normally equals Nifty 100, so keeping both needs a stated purpose.

## Decisions made (+ ADR ids)

- None. This is a source/definition gate, not a silent methodology change.

## Open questions

- Does the owner have written permission for the bounded automated collection?
- What authoritative pre-2021 Nifty 50/100 constituent baseline will seed
  the reconstruction?
- Should the research universe be Nifty 100 rather than a redundant Nifty
  50-plus-Nifty-100 union?

## Model/usage notes

- No external collection occurred. Official pages were read only to verify
  source terms and the documented reconstitution schedule.
