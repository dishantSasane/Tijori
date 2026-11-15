# STATUS (living board — update every session)

Last updated: 2026-11-16 by Claude (P1a pilot data foundation closed — see note 0034; P2 re-assignment collided with already-merged PR #50, duplicate PR #55 closed without merge — see note 0035, needs-human on whether PR #50 has had its required cross-model review; P3 daily report + dashboard shipped PR #56, live adapter/ORB-wiring blocked on owner decision — see note 0036; P4 scanner + Stocks page shipped PR #57, placeholder ranking pending PR #53, dashboard/_data.py duplicate pending PR #56 — see note 0037)

## Phase tracker (see docs/BUILD_ORDER.md on main)

| Phase | Owner | State | Notes |
|---|---|---|---|
| P0 Foundation sprint | Claude Code | **DONE** | all BUILD_ORDER items 1-9 merged to `main`; `pytest`/`ruff`/`mypy` all clean on current `main` (41 tests). See note 0009 for the full list and known gaps. |
| P1a Data foundation (5-symbol pilot) | Claude (owner-redirected) | **pilot-complete, pending one cross-model item** — full daily (2010-2026) + intraday M1/M5 (Jan 2022-2026) collection for the 5 pilot symbols, candle-snapshot hashes computed, session-coverage audit fully resolved (no unexplained dates), price adjustment basis empirically confirmed provider-adjusted. Only item 6 (combined manifest needing Codex's action-register hash) remains open. See `docs/specs/P1A_EVIDENCE_CHECKLIST.md` and note 0034. |
| P1b Executable candidate library | Codex | **implementation-complete, Claude-reviewed, approved** — T1/T2/T4/T6/T5 ORB match frozen specs exactly, no look-ahead found, tests are real not circular. PR #53. See note 0034 and `communication/2026-11-16-claude-p1b-review-result.md`. |
| P1c Evaluation/reporting | Claude built, Codex integrating | **ranking report/metrics/registry/bootstrap complete against synthetic data**, 15-variant family (12 daily + 3 intraday, T3 deferred for pilot) reconciled. Pending Codex's integration onto `codex/p1-build`. |
| P1d Holdout policy | both | **source-independent safeguards (one-shot guard, rejection rule) can proceed; holdout consumption remains gated** until P1a/P1b/P1c are jointly sealed. 2016-2026 window stays burned. |
| P1e Activation | Codex | waiting on P1b/P1c closure per sequencing. |
| P1 (legacy row, superseded by P1a-e above) | Codex | superseded — see notes 0027-0034. |
| P2 Paper broker + risk engine + minimal alerts | Claude (owner override) | **implemented, under review** — PR #50 (RiskEngine/PaperBroker), #52 (candle builder/scheduler); sleeve allocation cap test coverage added on `claude/sleeve-allocation-and-adapters`. See note 0032. | |
| P3 India Tier A paper end-to-end + dashboard | Claude (picked up; author=Claude) | **partial** — daily report + read-only Streamlit dashboard (Home/India/Paper ledger/Strategies) shipped, PR #56; cross-model review still needed per AGENTS.md §5. Auto-paper-shadow confirmed already done (PR #50's `Mode.PAPER`/`ModeGate`). Live NSE data adapter and ORB/breakout live-paper wiring **blocked on owner decisions** (no live data source selected yet; PR #53 strategies not merged) — see note 0036. | |
| P4 Tier B scanner + Stocks page | Claude (picked up; author=Claude) | **implemented, under review** — daily scanner, shortlist persistence (new `scanner_shortlist` table), no-look-ahead scanner backtest, and a read-only Stocks page shipped, PR #57; cross-model review welcome (not AGENTS.md §5 mandatory — no risk/execution/broker code touched). Ranking is a placeholder momentum score pending PR #53's real strategy library; `dashboard/_data.py` duplicates the same file on unmerged PR #56. See note 0037. | |
| P5 Crypto + US sleeves (paper) | Claude (data layer only) | **data adapters/integrity/universe/loaders built, data-only, no execution** — crypto (Binance, free), US equities (Alpaca, free, raw-by-default corrected), on `claude/sleeve-allocation-and-adapters`, not yet merged. Strategy/execution work for this phase remains open. See note 0032. | |
| P6 Brain + News | Codex | waiting | |
| P7 Go-live readiness | both + owner | waiting | needs Claude audit before first live money |
| P8 Expansion (MCX, NSE currency) | Claude (data layer only) | **data verified, data-only** — MCX found a free source after all (Upstox's own MCX_FO segment); NSE currency confirmed to need no new adapter. Roll-adjustment logic built for MCX, reusable for NSE currency later. On `claude/sleeve-allocation-and-adapters`, not merged. See note 0032. | |

## Next 3 actions
1. Codex: resume Upstox action API acquisition only after Cloudflare access is restored externally; do not retry or bypass the current block.
2. Codex: persist per-ISIN action responses/provenance and establish coverage, including a reviewed source for demergers/unknown events.
3. Codex: after source gates pass, wire screening into both runners, implement position replay, rebuild datasets, and freeze splits; do not read the holdout before P1d.

## Blockers / needs-human
- P1 research-universe turnover source and historical membership data are not implemented/acquired; automated NSE/NSE Indices collection is prohibited by source policy.
- Upstox action endpoint live access and historical completeness are unverified; demerger coverage is not documented.
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

## Codex P1 Upstox probe checkpoint (2026-11-15, note 0030)
- The live Upstox token probe confirms M1 and M5 data for Nifty 50 plus five local Tier A sample names at 2026-11-13, 2026-10-15, and 2026-05-15; none at 2024-11-15. Provider docs state minute availability from Jan 2022 and one-month max requests for 1–15m; Jan 2022 returned candles, Dec 2021 did not. This is not proof of uninterrupted symbol coverage.
- NESTLEIND 10:1 split (2024-01-05, NSE circular FAOP60123) shows raw Upstox daily prices: ₹1,355.80 before vs ₹1,333.20 ex-date. Fixture/test added. Raw history requires separate action adjustment for research.
- P1 intraday loader, resumable/idempotent via CandleStore, month chunked with runtime-injected token and Parquet export; tests pass. Auto OAuth refresh remains unavailable pending OAuth app config/flow.
- P1 now targets daily and intraday from the start; exact intraday candidate catalog still outstanding. Branch `codex/p1-build` has uncommitted work, no PR, and requires cross-model review. Full checks last passed: pytest, ruff, format, mypy, diff-check.

## Codex P1 corporate-action screening checkpoint (2026-11-15, note 0031)
- **Correction to note 0030:** NESTLEIND Upstox daily close on 2024-01-04 is ₹1,355.80 (not ₹13,558); 2024-01-05 ex-date close is ₹1,333.20. For NSE's 10:1 split, the history is already on the post-split scale (case a) for this observed event. The known-answer test and docs were corrected; do not double-adjust it. Other symbols/action types remain unverified.
- NSE row parser recognizes demerger, rights, split, bonus, dividend, and unknown events without guessing a factor. In-window unhandled actions are reported; affected symbols are excluded unless exact `(symbol, date, kind)` review is recorded. Orchestrator still must invoke screening and persist it before running primary/reference replay.
- P1c note added: intraday promotion requires longer forward paper observation and more conservative sizing; freeze numeric gates before evaluation.
- Current `codex/p1-build` changes remain uncommitted/no PR; full pytest, Ruff/format, mypy, diff-check passed at checkpoint.
