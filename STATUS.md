# STATUS (living board — update every session)

Last updated: 2026-11-14 19:15 IST by Claude Code (final P0 handoff — see note 0006)

## Phase tracker (see docs/BUILD_ORDER.md on main)

| Phase | Owner | State | Notes |
|---|---|---|---|
| P0 Foundation sprint | Claude Code | mostly done, NOT 100% | contracts/adapters/RISK_ENGINE_SPEC/TEST_SPEC_RISK merged-or-PR-open (#5 merged, #7 merged, #8 open, #9 open); RED_TEAM.md, STRATEGY_SPEC.md, TEST_SPEC_{BACKTEST,CANDLES,ADAPTERS,STRATEGIES}.md, lessons 01-03 NOT written — see note 0006 |
| P1 Data layer + backtester | Codex | **partially unblocked** — see note 0006's safe-to-start list | |
| P2 Paper broker + risk engine + minimal alerts | Codex | waiting | |
| P3 India Tier A paper end-to-end + dashboard | Codex | waiting | |
| P4 Tier B scanner + Stocks page | Codex | waiting | |
| P5 Crypto + US sleeves (paper) | Codex | waiting | |
| P6 Brain + News | Codex | waiting | |
| P7 Go-live readiness | both + owner | waiting | needs Claude audit before first live money |
| P8 Expansion | both | waiting | gated |

## Next 3 actions
1. Owner: merge PR #8 (clock/UTC bugfix — CI green; should merge before any P1 code touches `core.models`) and PR #9 (TEST_SPEC_RISK — CI green).
2. Codex: start the P1 work note 0006 lists as safe (candle store, candle validation) once #8 is merged; wait on STRATEGY_SPEC.md/TEST_SPEC_BACKTEST.md for strategy/backtester work.
3. Claude (next session): STRATEGY_SPEC.md first (unblocks the most P1 work), then remaining TEST_SPEC_*, then RED_TEAM.md, then lessons 01-03 — see note 0006.

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
- P1 waiting on P0. NSE website ingestion is blocked pending authorized source/use; free live universe sizes need reconciliation (note 0003).

## Claude P0 checkpoint (2026-11-14 19:35 IST)
- Fixed repo bootstrap: `main` created (commit `2839936`), `handoffs` flattened
  (commit `e058593`) — see note 0004 for why `main` didn't exist before this.
- Branch `claude/p0-scaffold-verify`: P0 items 1 (verify, no fixes needed), 3
  (`trading/core/` contracts), 4 (`trading/adapters/` Protocols+fakes). 31
  tests, ruff/mypy clean. PR not opened (no gh/API token available); link in
  note 0004.
- Items 2, 5 (continuation), 6, 7, 8, 9, 10 of BUILD_ORDER P0 are NOT done yet.

- Publication checkpoint: PR #4 contains research and PR #5 contains Claude's foundation. Both are open, clean, and CI `test` passed. Codex review comments are posted; PR #5 has two blocking contract findings. P1 remains waiting.

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
