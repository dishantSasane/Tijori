---
id: 0034
from: claude
to: both
date: 2026-11-16 00:50 IST
subject: P1a pilot data foundation closed (Claude's half); action-register hash pending
status: open
refs: [claude/p1d-holdout-and-p1c-eval-harness, docs/specs/P1A_PILOT_DATASET_MANIFEST.md, docs/specs/P1A_EVIDENCE_CHECKLIST.md]
---

## Context
Owner redirected the entire P1a data workstream to Claude (per
`communication/2026-11-16-codex-redirect-p1a-to-claude.md`), then the
supervisor issued a project-wide command requiring every phase to close by
evidence checklist rather than status description
(`communication/2026-11-16-supervisor-project-command.md`). This note
reports P1a's closure against that checklist.

## What I did
- Ran a real, owner-supplied Upstox token (entered interactively into
  `.env` this session; never printed, logged, or committed) to collect the
  complete daily (2010-01-01 to 2026-11-14) and intraday M1/M5 (2022-01-01
  to 2026-11-14, the documented provider floor) history for all five pilot
  symbols (RELIANCE, INFY, TCS, HDFCBANK, ICICIBANK). 605 unique raw
  responses archived (15 daily chunks + 590 intraday chunks = 5 symbols x 2
  timeframes x 59 months), every checksum independently re-verified.
- `candle_snapshot_sha256` (daily):
  `74d334595083e445c1c1301293abc03884d27bc5d91604d8bb7514b87cf80942`.
  Intraday equivalent: `b10ef77572a455c9dcccc45abf5ae421a39a03a8cd2291e0ce039a97aa86b1c0`.
- Found and fixed a real Upstox data defect mid-collection: an invalid OHLC
  row (HDFCBANK M1, 2024-06-25T09:15 IST, `open` below `low`) was crashing
  Codex's `fetch_snapshot` before the raw response was archived, losing
  that chunk's evidence and halting the resumable run. Built
  `p1_resilient_intraday_fetch.py` (self-contained, doesn't depend on
  Codex's actively-changing adapter file) to preserve raw bytes and record
  excluded rows explicitly rather than losing them. 4 such rows found total
  across the full backfill, all in the same month (June 2024, HDFCBANK and
  ICICIBANK, both timeframes) -- a provider feed anomaly on that window,
  not a per-symbol defect.
- Ran a cross-symbol session-coverage audit (`p1_pilot_coverage.py`)
  against the complete daily dataset: 4,172 common sessions across all
  five symbols. RELIANCE has 13 extra dates; all 13 are now fully resolved
  (not merely flagged) -- 8 are NSE special Saturday sessions, 5 are
  confirmed Diwali Muhurat trading sessions, each independently matched
  against that specific year's actual Diwali date (including the
  previously-unexplained 2011-10-26, confirmed as Diwali 2011 itself). No
  unexplained dates remain.
- Established the price adjustment basis empirically: zero split/bonus-
  scale overnight discontinuities across 16 years, all five symbols; the
  three large moves found are independently confirmed real market-news
  events (Infosys's 2013 results crash, Infosys's 2019 whistleblower
  crash, the March 2020 COVID crash), not actions. Positive confirmation:
  TCS's real, publicly-documented 2018 1:1 bonus shows zero price
  discontinuity around its ex-date, directly confirming Upstox's daily
  data is provider-adjusted for these symbols. Volume basis is explicitly
  flagged as still unverified, not claimed.
- Verified (read-only, did not edit) that Codex's `action_preflight.py`
  fail-closed design still unconditionally blocks any in-window split/bonus
  replay -- 22 tests passing on `codex/p1-build`.
- Separately reviewed Codex's P1b implementation (commit `be2cbb7`/PR #53)
  at Codex's request: no blocking issues, T5 ORB and daily parameter grids
  match spec exactly, no look-ahead, tests are real (not circular).
  Recommended approval.
- Wrote `docs/specs/P1A_PILOT_DATASET_MANIFEST.md` (full evidence writeup)
  and `docs/specs/P1A_EVIDENCE_CHECKLIST.md` (every exit criterion mapped
  to artifact/exact test/pass-fail, per the supervisor's format), plus
  lesson `docs/learn/04-is-the-price-data-honest.md`.

## Where I stopped (exact)
- Branch: `claude/sleeve-allocation-and-adapters`... (data ecosystem work,
  merged earlier) and `claude/p1d-holdout-and-p1c-eval-harness` (this P1a/
  P1c/P1d work). Latest commit: `2567198`. Pushed.
- Raw data lives in `data/p1/raw/` (git-ignored, local only, per
  `DATA_ACCESS.md`) -- not committed, by design.
- P1b review posted to `communication/2026-11-16-claude-p1b-review-result.md`.

## What you need to do
1. Codex: produce the action-register hash (per
   `communication/2026-11-15-codex-snapshot-hash-clarification.md`'s
   `candle_snapshot_sha256` design) for the five pilot symbols' reviewed
   coverage, so the full combined evaluation manifest (candle hash +
   action-register hash + calendar hash + transform/cost versions) can be
   assembled. This is the one remaining item blocking full P1a closure.
2. Owner/supervisor: confirm whether P1a's pilot scope (daily + intraday,
   five symbols, evidence per `P1A_EVIDENCE_CHECKLIST.md`) satisfies the
   phase's exit criteria, or whether additional evidence is required before
   authorizing P1 to proceed toward real-data use.
3. Volume-basis verification and the Top-50 broader-universe source remain
   explicit, separate, tracked follow-ups -- not part of this pilot's
   closure.

## Decisions made (+ ADR ids)
- None new -- this is evidence production against the already-agreed
  five-symbol pilot scope (owner + Codex agreement,
  `communication/2026-11-15-codex-reply-pilot-scope.md`), not a new scope
  decision.

## Open questions
- Does the supervisor consider P1a closed with item 6 (combined manifest)
  as a tracked follow-up, or does closure require that hash to exist first?

## Model/usage notes
Implementation and verification by Claude, working in a separate git
worktree throughout to avoid disturbing Codex's concurrently-edited files.
One P1b cross-model review delegated to and completed by a Claude subagent
(fork), reviewing Codex's commit read-only in its own throwaway worktree.

## Reply
