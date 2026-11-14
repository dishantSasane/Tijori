# STATUS (living board — update every session)

Last updated: 2026-11-14 19:30 IST by Claude Code (all BUILD_ORDER P0 items now have content — see note 0008)

## Phase tracker (see docs/BUILD_ORDER.md on main)

| Phase | Owner | State | Notes |
|---|---|---|---|
| P0 Foundation sprint | Claude Code | **content-complete, PRs open** | every BUILD_ORDER item (1-9) now has merged-or-open-PR content; item 10 (this handoff) in progress. Owner still needs to merge PRs #11 (STRATEGY_SPEC), #12 (RED_TEAM), #14 (TEST_SPEC_CANDLES+BACKTEST), #15 (lessons 01-03) — see note 0008 |
| P1 Data layer + backtester | Codex | **in progress** — candle store + atomic batches (PR #13) merged; STRATEGY_SPEC.md/TEST_SPEC_BACKTEST.md now exist (PR #11/#14, pending merge) to unblock strategy/backtester work | |
| P2 Paper broker + risk engine + minimal alerts | Codex | waiting | |
| P3 India Tier A paper end-to-end + dashboard | Codex | waiting | |
| P4 Tier B scanner + Stocks page | Codex | waiting | |
| P5 Crypto + US sleeves (paper) | Codex | waiting | |
| P6 Brain + News | Codex | waiting | |
| P7 Go-live readiness | both + owner | waiting | needs Claude audit before first live money |
| P8 Expansion | both | waiting | gated |

## Next 3 actions
1. Owner: merge PRs #11 (STRATEGY_SPEC.md), #12 (RED_TEAM.md), #14 (TEST_SPEC_CANDLES+BACKTEST), #15 (lessons 01-03) — all CI green except #15 (was still running at last check). PR #13 (Codex, atomic candle batches) reviewed and recommended for merge too.
2. Codex: once #11/#14 merge, T1/T4 strategy + backtester implementation is unblocked (STRATEGY_SPEC.md + TEST_SPEC_BACKTEST.md/CANDLES.md exist with known-answer vectors). `TEST_SPEC_ADAPTERS.md`/`TEST_SPEC_STRATEGIES.md` and T2/T3/T5/T6/F1 vectors are still a gap — flagged, not blocking T1/T4.
3. Claude: write the real final P0 handoff (item 10) once the above PRs are merged — note 0008 is a progress note, not yet item 10's formal close-out.

## Blockers / needs-human
- Open questions listed in `docs/MASTER_PLAN.md` §13 (capital, brokers, exchange, VM, repo name, allocations).

## Environment facts (update when they change)
- Owner plans: Claude Pro (ends ~2026-11-16), ChatGPT Plus (ongoing).
- Static-IP rule applies to real India orders; research/paper can run on the laptop.

## Codex pre-P0 checkpoint
- Research: `codex/data-sources` at `b3400e3` (pushed); note 0003 has findings and exact stopping point.
- CLI 0.166.0; Python 3.12.3; ChatGPT Plus confirmed through read-only app-server calls.
- Available: GPT-6.1 Sol, GPT-6 Astra, GPT-6.1 Terra, GPT-6 Luna (plus legacy models).
- Usage snapshot: five-hour window 12% used; weekly window 5% used. Recheck next session.
- Local ruff lint/format, mypy, pytest pass (one smoke test).
- Main/root layout and handoffs/root layout repaired; worktrees operational.
- NSE website ingestion is blocked pending an authorized source/use; free live universe sizes need reconciliation (note 0003).

## Claude P0 checkpoint (2026-11-14 19:35 IST)
- Fixed repo bootstrap: `main` created (commit `2839936`), `handoffs` flattened
  (commit `e058593`) — see note 0004 for why `main` didn't exist before this.
- Branch `claude/p0-scaffold-verify`: P0 items 1 (verify, no fixes needed), 3
  (`trading/core/` contracts), 4 (`trading/adapters/` Protocols+fakes). 31
  tests, ruff/mypy clean. PR not opened (no gh/API token available); link in
  note 0004.
- Items 2, 5 (continuation), 6, 7, 8, 9, 10 of BUILD_ORDER P0 are NOT done yet.

- Publication checkpoint: PRs #4, #5, #7, #8, and #9 are merged. PR #10 (candle store) is merged at `18310fd`; its CI is green. PR #13 (atomic candle batches) is open at `ccbaf3d`; its CI `test` check is green.

## Claude final P0 handoff (2026-11-14 19:15 IST, note 0006)
- PR #4 (data sources) and #5 (contracts/adapters) **merged** to `main`.
- PR #5 merged *before* Codex's two blocking findings (wall-clock defaults,
  loose UTC check) were fixed — fix is **open PR #8**, cherry-picked onto
  current `main`, CI green. Merge this before building P1 code on `core`.
- PR #7 (`docs/specs/RISK_ENGINE_SPEC.md`) **merged**.
- PR #9 (`docs/specs/TEST_SPEC_RISK.md`) **open**, CI green.
- Real gaps: `RED_TEAM.md`, `STRATEGY_SPEC.md`,
  `TEST_SPEC_{BACKTEST,CANDLES,ADAPTERS,STRATEGIES}.md`, lessons 01-03 — none
  written. Note 0006 has a safe-to-start-now vs. must-wait split for Codex.
