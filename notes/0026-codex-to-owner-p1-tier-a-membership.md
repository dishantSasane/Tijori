---
id: 0026
from: codex
to: owner
date: 2026-11-15 00:30 IST
subject: P1 historical Tier A membership decision
status: needs-human
refs: ["codex/p1-kickoff", "docs/P1_RESEARCH_PROTOCOL.md", "docs/P1_STATISTICAL_VALIDATION.md", "docs/specs/DATA_SOURCES.md"]
---

## Context

P1 now uses Upstox historical candles only. The current versioned manifest is
explicitly provisional: NIFTY 50 plus five representative equities. It is not
the complete historical Nifty 50 + Next 50 universe.

## What I did

- Collected and archived reproducible Upstox daily history for the six-member
  representative sample.
- Ran T1 and T4 full-window scorecards and retrospective walk-forward reports.
- Added deterministic per-instrument block-bootstrap expectancy intervals.
- Documented the statistical validation protocol and the Upstox data boundary.
- Verified official Upstox instruments and instrument-search documentation. They
  resolve current instrument keys but do not establish point-in-time index
  constituents or historical membership.

## Where I stopped (exact)

- Branch: `codex/p1-kickoff`
- Last commit: `1197ecb`
- Worktree: clean
- Checks: pytest, Ruff lint/format, and mypy pass
- Next file/function: `config/india_tier_a.example.yaml` membership manifest

## What you need to do

Choose one of these options:

1. Provide or approve an authorized point-in-time historical mapping for Nifty
   50 + Next 50 members, including symbols and Upstox instrument keys. This is
   recommended for a complete Tier A P1 claim.
2. Explicitly accept that P1 will remain a provisional representative-sample
   research milestone, with full Tier A collection deferred until a permitted
   membership source is available.

Recommendation: choose option 1 before using any result to select a champion;
do not infer historical membership from today's Upstox instrument catalogue.

## Decisions made (+ ADR ids)

- Upstox is the only P1 historical data provider.
- The P3 live-data provider remains undecided.
- T1/T4 current defaults are frozen baseline versions and are not promotion
  candidates.

## Open questions

- Which authorized point-in-time membership source or owner-supplied mapping
  should populate the complete Tier A manifest?
- Should the historical mapping include only the Nifty 50 + Next 50 names, or
  also a separate index series for benchmark comparison?

## Model/usage notes

- Work was performed on the Codex P1 branch; no live-order path was added.

## Reply

(Owner appends the decision here.)
