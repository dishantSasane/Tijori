# STATUS (living board — update every session)

Last updated: 2026-11-15 by Codex (P1 restructure and membership research — see note 0027)

## Phase tracker (see docs/BUILD_ORDER.md on main)

| Phase | Owner | State | Notes |
|---|---|---|---|
| P0 Foundation sprint | Claude Code | **DONE** | all BUILD_ORDER items 1-9 merged to `main`; `pytest`/`ruff`/`mypy` all clean on current `main` (41 tests). See note 0009 for the full list and known gaps. |
| P1 Data layer, strategy discovery, regime-gated activation | Codex | **ACTIVE; P1a gated on owner decisions** — existing backtester/indicators and six-symbol Upstox Parquet sample exist; P1 is now split into P1a-e by ADR-0024. See note 0027. | |
| P2 Paper broker + risk engine + minimal alerts | Codex | waiting | |
| P3 India Tier A paper end-to-end + dashboard | Codex | waiting | |
| P4 Tier B scanner + Stocks page | Codex | waiting | |
| P5 Crypto + US sleeves (paper) | Codex | waiting | |
| P6 Brain + News | Codex | waiting | |
| P7 Go-live readiness | both + owner | waiting | needs Claude audit before first live money |
| P8 Expansion | both | waiting | gated |

## Next 3 actions
1. Owner: decide whether to obtain NSE Indices' point-in-time constituent data after coverage/licence/quote details, or accept only a clearly scoped provisional sample with survivorship caveat.
2. Owner: set research comparison capital/per-trade risk assumption and confirm daily swing horizon.
3. Codex: after decisions, finish P1a with corporate-action known answers and frozen chronological splits; do not read the holdout before P1d.

## Blockers / needs-human
- P1 historical membership source/terms or explicit scoped survivorship-bias caveat.
- P1 comparison sizing (capital and per-trade risk) and holding horizon.
- New untouched holdout boundaries: the previously reviewed 2016-2026 sample cannot be reused as an unseen holdout under ADR-0024.

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
- Deterministic fill simulation is on `codex/p1-backtester` at latest head `faad076` (`e50bcc9` + `3eedbb6` + `faad076`).
- PR #21 is merged into `main`; its CI passed.
- Local report: 57 total tests green; no real broker path added.
- Terra look-ahead tests are on `codex/terra-lookahead` at `eb96cbd`; PR #22 is merged into `main`.

## Codex P1 ExitRequest checkpoint (2026-11-14, note 0007)
- Owner-approved ExitRequest contract is on `codex/risk-exit-contract` at `e3ecc45`.
- PR #24 is open against `main`; CI `test` was pending at the latest query.
- Claude cross-model review is required before human merge; no merge performed.

## Codex Terra ExitRequest property checkpoint (2026-11-14, note 0007)
- Property tests are on `codex/terra-exit-properties` at `ef7558d`, based on `e3ecc45`.
- PR #25 is open against `main`; CI `test` was pending at the latest query.
- Claude cross-model review is required for PR #24 and PR #25 before human merge.

## Codex P1 strategy test checkpoint (2026-11-14, note 0007)
- T1 equality-boundary and T4 exit-trigger tests are on `codex/p1-strategy-tests` at `9da4bc0`.
- PR #26 is open against `main`; CI `test` was pending at the latest query.
- No production execution path changed.

## Codex P1 incremental/exit/reference checkpoint (2026-11-14, note 0007)
- Incremental indicator completion: `477ab7d`, PR #28, CI no checks reported at latest query.
- Target/condition exits, gap handling, overlap guard, audit, walk-forward split, and P3 condition-exit equivalence gate: PR #29 branch latest `4f19c52` (starts at `ef0072d`), CI green on the last reported run.
- Terra reference backtester: PR #30 latest head `cfea990` (includes `63f2d1f` and `3201ecd`), CI pending; 78 tests reported.
- Claude cross-model review is required before owner merges.

## Upstox history checkpoint (2026-11-14, note 0007)
- Adapter commits `c77f028` + `7a1a5ef` merged through PR #31, main merge `b65c06c`.
- Daily no-token V3 historical probes returned candles for Nifty 50 and representative Tier A symbols.
- Intraday no-token probes returned empty candles with HTTP 200; authenticated/provider policy remains a human decision before ingestion wiring.

## Codex condition timing checkpoint (2026-11-14, note 0007)
- PR #34 is open at `1c8987b`; close-based condition exits evaluate on closed bars and fill at next open with sell slippage.
- No CI checks were reported at latest query; Terra conflict handoff is `0015` (`d7bee4c`).

## Codex next-open condition checkpoint (2026-11-14, note 0007)
- Sol v2: PR #35, latest `ff9aaae` (`11d4f27` + `ff9aaae`), CI pending.
- Terra reference: PR #36, latest `a26e0e8`, no checks reported; 86 tests reported.
- Both require cross-model review; no merge performed.

## Codex runner accounting checkpoint (2026-11-14, note 0007)
- PR #38 is open at `970903d`; total fees are counted once, SELL signals are rejected, and end-of-data open trades are structured.
- CI `test` pending at latest query; cross-model review required.

## Codex Group 1 fix PR checkpoint (2026-11-14, note 0007)
- PR #40: `a83bca4`, CI `test` failed; blocked pending diagnosis.
- PR #41: `a41e88c`, CI `test` passed; Claude cross-model review required.
- PR #35, #36, and #39 remain open; no owner merges were performed by this check.

## Corrected follow-up PR checkpoint (2026-11-14)
- PR #36: `dad92fc`, CI passed.
- PR #42: `2e4e5a4`, CI pending — gap-risk audit/embargo/overlap fixes.
- PR #43: `7d0b0d6`, CI pending — independent reference formula equivalence.
- PR #29/#30 are merged originals; #42/#43 are the corrected follow-up PRs.
- PR #44 is closed without merge; `handoffs` remains a message board only.

## Codex P1 scorecard checkpoint (2026-11-14, note 0007)
- Deterministic scorecards are on `codex/p1-scorecard` at `aa1c183`.
- PR #27 is open against `main`; CI `test` was pending at the latest query.
- No production execution path changed.

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
