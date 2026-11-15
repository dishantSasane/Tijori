---
id: 0033
from: codex
to: both
date: 2026-11-15 20:00 IST
subject: Select Upstox corporate-actions API; audit NSE collection
status: open
refs: [codex/p1-build, ADR-0028, docs/specs/DATA_SOURCES.md, docs/specs/CORPORATE_ACTIONS.md]
---

## Context
Owner directed that P1 must not automate collection from nseindia.com or
niftyindices.com and selected the Upstox corporate-actions API if it exists.
Owner also requested an audit of research-universe and Nifty 50 membership
collection methods.

## What I did
- Confirmed Upstox's official developer documentation for authenticated
  `GET /v2/fundamentals/{isin}/corporate-actions`, which documents event names,
  dates, ratios, amounts, and detail fields for dividend, bonus, split, and
  rights events.
- Added a client and fixture tests which preserve the raw ratio/details and do
  not infer factor direction. Independent review found and I fixed three
  issues: authenticated redirects are now rejected; snapshots retain original
  response bytes/hash/parser version/retrieval time; and ordered detail pairs
  preserve duplicate labels. Regression tests cover each behavior. The
  endpoint documentation does not explicitly promise demerger coverage or
  historical completeness.
- Made one token-authenticated probe for NESTLEIND. Cloudflare returned 403
  `browser_signature_banned` and explicitly instructed not to retry. No token
  was printed. No response data was fetched or saved; no workaround was tried.
- Audited `research_universe.py` and `membership.py`: pure normalized-input
  selector and manifest validator only. There is no NSE bhavcopy or Nifty
  Indices press-release downloader in `src/`.
- Updated P1 source docs/decision: don't automate NSE/Nifty site collection;
  Upstox is the selected action API candidate; manual reviewed records or a
  permitted source are still needed for demergers/unknown events.
- After those fixes: full pytest, Ruff lint/format, mypy, and diff checks passed.
  The independent reviewer approved through `68d7b5e`; GitHub CI passed on the
  same commit.

## Where I stopped (exact)
- Branch: `codex/p1-build`.
- Base/latest committed change: `9802fc7` (PR #53). Existing unrelated local
  edit to `src/trading/backtest/runner.py` was present at pickup and remains
  unstaged/untouched.
- Client/docs commits `9a6cd8c`, `5e9b84a`, and `68d7b5e` are pushed to PR #53.
  The PR description is updated; owner review/merge remains required.
- No daily dataset rebuild, raw action-response archive, bonus-provider case,
  demerger manual ledger, or open-position replay was completed because no live
  response could be acquired and coverage is undocumented.

## What you need to do
1. On a future session, only retry the API after an external change resolves
   the provider's explicit Cloudflare block; do not cycle user agents or bypass
   the access control.
2. Once successful, save immutable response JSON/provenance for every pinned
   Tier A ISIN and verify completeness/history dates. Treat demerger coverage
   as unknown until tested; add a human-maintained reviewed record for events
   absent from the API.
3. Then apply split/bonus adjustments only after per-event provider-basis and
   ratio semantics are verified; wire action screening to both backtesters,
   implement open-position replay, rebuild daily/intraday datasets, and freeze
   split boundaries only after all P1a gates pass.
4. Keep NSE bhavcopy and NSE Indices press-release collection manual or use an
   independently authorized source; current source package has no automated
   scraper to remove.

## Decisions made (+ADR ids)
- ADR-0028 records the Upstox API as P1's selected corporate-action source and
  explicitly prohibits automated NSE/NSE Indices website collection.
- Upstox API docs establish an endpoint and schema, not live access or complete
  event history. An empty response is not evidence that no action occurred.

## Open questions
- Does the owner's Upstox app/account allow this endpoint when the provider's
  Cloudflare block is resolved?
- What independent/manual process establishes demerger and unknown-action
  coverage for each Tier A symbol and research window?

## Model/usage notes
- No secrets copied or emitted. Probe failure is a source-access blocker, not a
  reason to bypass provider controls.

## Reply
