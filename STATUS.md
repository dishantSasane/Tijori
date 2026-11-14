# STATUS (living board — update every session)

Last updated: 2026-11-14 by Codex (P1 backtester PR #21 open — see note 0007)

## Phase tracker (see docs/BUILD_ORDER.md on main)

| Phase | Owner | State | Notes |
|---|---|---|---|
| P0 Foundation sprint | Claude Code | **DONE** | all BUILD_ORDER items 1-9 merged to `main`; `pytest`/`ruff`/`mypy` all clean on current `main` (41 tests). See note 0009 for the full list and known gaps. |
| P1 Data layer + backtester | Codex | **in progress** — candle store, indicators, T1/T4 signals, and deterministic fill simulation implemented; PR #21 is open for review | |
| P2 Paper broker + risk engine + minimal alerts | Codex | waiting | |
| P3 India Tier A paper end-to-end + dashboard | Codex | waiting | |
| P4 Tier B scanner + Stocks page | Codex | waiting | |
| P5 Crypto + US sleeves (paper) | Codex | waiting | |
| P6 Brain + News | Codex | waiting | |
| P7 Go-live readiness | both + owner | waiting | needs Claude audit before first live money |
| P8 Expansion | both | waiting | gated |

## Next 3 actions
1. Owner/Claude: review PR #21, wait for CI, and decide whether to merge it.
2. Codex (fast-follow, non-blocking): T1's boundary test (`close==H(N)` must not fire) and T4's exit-trigger tests are missing — flagged in PR #20's review comment, not required before starting the backtester.
3. Owner: nothing blocking. MASTER_PLAN.md §13's open questions remain yours whenever convenient.

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

- Publication checkpoint: PRs #4, #5, #7, #8, and #9 are merged. PR #10 (candle store) is merged at `18310fd`; its CI is green. PR #13 is open at `ccbaf3d` with green CI; PR #16 is open at `d73088a`; PR #19 is open at latest head `79509ee` with CI pending at latest query.

## Codex P1 indicators checkpoint (2026-11-14, note 0007)
- SMA/EMA implementation and tests are on `codex/p1-indicators` at `d73088a`.
- PR #16 is open against `main`; no merge performed.
- Local checks are reported green; GitHub CI was pending at the latest query.

## Codex P1 indicator suite checkpoint (2026-11-14, note 0007)
- Wilder RSI/ATR/ADX, Bollinger, Donchian, and rolling/cumulative VWAP are on `codex/p1-indicator-suite` at `9900b30`.
- PR #19 is open against `main`; no merge performed.
- CI `test` was pending at the latest query.

## Codex incremental indicator checkpoint (2026-11-14, note 0007)
- PR #19 includes `9900b30`, `6d8c61f`, and `79509ee`; latest head is `79509ee`.
- Incremental SMA/EMA/Wilder state and batch-equivalence tests are included.
- PR #19 remains open; CI `test` was pending at the latest query.

## Codex P1 T1/T4 checkpoint (2026-11-14, note 0007)
- T1/T4 signal rules are on `codex/p1-t1-t4` at `72b9332`.
- PR #20 is open against `main`; its CI `test` was pending at the latest query.
- No execution or live-order path was added.

## Codex P1 backtester checkpoint (2026-11-14, note 0007)
- Deterministic fill simulation is on `codex/p1-backtester` at latest head `3eedbb6` (`e50bcc9` + `3eedbb6`).
- PR #21 is open against `main`; CI `test` was pending at the latest query.
- Local report: 57 total tests green; no real broker path added.

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
