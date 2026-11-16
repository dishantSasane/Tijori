---
id: 0048
from: codex
to: both
date: 2026-11-16 13:45 IST
subject: independent P1 review blockers and isolated remediation PRs
status: open
refs: ["PR #63", "PR #64", "PR #66", "PR #67", "PR #68", "PR #69", "PR #70"]
---

## Context

Owner requested an independent safety review of #63/#64/#66 and fixes for
the confirmed #56/#57/#60/#62 defects without editing Claude-owned branches.

## What I did

- Posted independent blocking review comments on:
  - #63: raw master/candle evidence is neither persisted nor hashed (`n/a-live-api`),
    so a universe snapshot is not reproducible/frozen; its 0.15-second throttle
    violates the stated strict 2,000/30-minute provider cap.
  - #64: non-null `Candle.adj_factor` is insufficient proof that a specific
    split/bonus is adjusted; it can bypass unimplemented position replay.
  - #66: panel-return keys can differ from cumulative-return keys, allowing
    corrupted profitable-instrument counts to reach the binomial gate; non-finite
    values are not rejected.
- Created separate Codex-owned follow-up PRs, targeting their parents rather
  than editing Claude worktrees:
  - #67 -> #56: remove unsupported percentage-sum P&L claim.
  - #68 -> #57: require a complete scan attestation before shortlist mutation.
  - #69 -> #60: treat duplicate local/broker position rows as mismatches.
  - #70 -> #62: make the status audit clearly point-in-time.
- Targeted tests/Ruff passed for #67–#69; #70 passed `git diff --check`.

## Where I stopped (exact)

- Branch ownership remains isolated. Do not edit Codex branches #67–#70 from
  a Claude worktree; do not edit Claude parent branches from a Codex worktree.
- #58/#61 stacking and #59 hard-budget design remain with their original owner.

## What you need to do

1. Claude independently reviews #67–#70, then the human may merge each into
   its corresponding parent branch before the parent returns for review.
2. Claude fixes #63/#64/#66 blockers and opens new/follow-up commits for a
   fresh Codex review.

## Decisions made (+ ADR ids)

- No critical P1 PR is approved: all three currently have correctness blockers.

## Open questions

- None. The merge order is governed by parent dependencies and fresh review,
  not by CI-green status alone.

## Model/usage notes

- No real broker orders or paid API calls were made.

## Reply

(Receiver appends here; do not rewrite the sections above.)
