# STATUS (living board — update every session)

Last updated: 2026-11-16 by Codex (PR #71 is draft because it was pilot-bound. Nifty 50 scheduled-only chain now has all 60 identities resolved, but reverse reconstruction from a 2026 anchor conflicts with the accepted membership provenance contract; note 0057.)

## Phase tracker (see docs/BUILD_ORDER.md on main)

| Phase | Owner | State | Notes |
|---|---|---|---|
| P0 Foundation sprint | Claude Code | **DONE** | all BUILD_ORDER items 1-9 merged to `main`; `pytest`/`ruff`/`mypy` all clean on current `main` (41 tests). See note 0009 for the full list and known gaps. |
| P1a Data foundation (5-symbol pilot) | Claude/Codex | **historical boundaries frozen; real replay remains gated** — PR #71 locks the daily/intraday development, validation, and unread 2026 holdout plans to the frozen evidence hashes. Historical action coverage remains unverified, so the plans cannot authorize real-data replay. See note 0054. |
| P1b Executable candidate library | Codex | **implementation-complete, Claude-reviewed, approved** — T1/T2/T4/T6/T5 ORB match frozen specs exactly, no look-ahead found, tests are real not circular. PR #53. See note 0034 and `communication/2026-11-16-claude-p1b-review-result.md`. |
| P1c Evaluation/reporting | Claude/Codex | **implementation-complete and independently reviewed** — synthetic-only ranking, metrics, bootstrap, append-only registry and 15-variant correction are integrated in `bb6bf1d`. No real ranking has run. |
| P1d Holdout policy | Claude/Codex | **implementation-complete, real consumption gated** — sealed shortlist membership, valid one-shot authorization, durable one-result-per-candidate enforcement and pre-registered outcome/reason logging are in `bb6bf1d`. PR #71 reserves the unread 2026 historical holdout; only strategy-outcome exposure consumes it (ADR-0048). |
| P1e Activation | Codex | **implementation-complete** — fixed rule spec/router, abstention/overlap tests, and activation-frequency reporting exist; empirical validation is gated on P1a-P1d real-data prerequisites. |
| P1 (legacy row, superseded by P1a-e above) | Codex | superseded — see notes 0027-0034. |
| P2 Paper broker + risk engine + minimal alerts | Claude (owner override) | **implemented, under review** — PR #50 (RiskEngine/PaperBroker), #52 (candle builder/scheduler); sleeve allocation cap test coverage added on `claude/sleeve-allocation-and-adapters`. See note 0032. | |
| P3 India Tier A paper end-to-end + dashboard | Claude (picked up; author=Claude) | **partial** — daily report + read-only Streamlit dashboard (Home/India/Paper ledger/Strategies) shipped, PR #56; cross-model review still needed per AGENTS.md §5. Auto-paper-shadow confirmed already done (PR #50's `Mode.PAPER`/`ModeGate`). Live NSE data adapter and ORB/breakout live-paper wiring **blocked on owner decisions** (no live data source selected yet; PR #53 strategies not merged) — see note 0036. | |
| P4 Tier B scanner + Stocks page | Claude (picked up; author=Claude) | **implemented, under review** — daily scanner, shortlist persistence (new `scanner_shortlist` table), no-look-ahead scanner backtest, and a read-only Stocks page shipped, PR #57; cross-model review welcome (not AGENTS.md §5 mandatory — no risk/execution/broker code touched). Ranking is a placeholder momentum score pending PR #53's real strategy library; `dashboard/_data.py` duplicates the same file on unmerged PR #56. See note 0037. | |
| P5 Crypto + US sleeves (paper) | Claude | **data adapters done (note 0032); market profiles + T1/T4 strategy instances + Accounts page v1 added** — PR #58 on `claude/p5-crypto-us-sleeves`, based on `claude/sleeve-allocation-and-adapters` (PR #54), not yet merged. T2/momentum deferred (PR #53 strategy library unmerged); funding data deferred (spot-only sleeve, nothing consumes it yet); live-paper execution wiring (candle feed -> signal -> risk -> broker) still open. See note 0038. | needs-human: which crypto exchange/account for paper trading (data picked Binance; order routing unsettled) |
| P6 Brain + News | Codex (picked up by Claude; author=Claude) | **implemented, under mandatory cross-model review** — real `RSSNewsFeed`, `AnthropicBrainProvider` (lazy-imported, new `brain` extra), `BudgetGuard` (fails closed, sums spend from existing `audit_log`), strict `parse_verdict` schema validation, in-process `ContextCache`, and `run_ab` Brain A/B harness shipped in `src/trading/brain/`, PR #59 on `claude/p6-brain-news`. No production call site for the A/B harness yet (no live paper signal-generation loop exists); Usage dashboard tile deferred. See note 0039. | needs-human: confirm Anthropic model + current per-token INR pricing + daily/monthly budget cap before `BRAIN_ENABLED=true` |
| P7 Go-live readiness | both + owner | **checklists + reconciliation drill implemented, under mandatory cross-model review** — `docs/GO_LIVE_CHECKLIST.md` (ordered owner walkthrough: VM/static IP, broker KYC/key scoping, secrets review, kill-switch drill, reconciliation drill, mode/risk dry run, audit, first live order), `docs/LIVE_AUDIT_CHECKLIST.md` (prep for the dedicated audit pass), and `src/trading/reconciliation/` (compares local vs. broker positions, engages kill switch on any mismatch, tested only against a fake broker). PR #60 on `claude/p7-go-live-readiness`. Approval-mode gate confirmed already enforced in `src/trading/risk/engine.py` (not the Telegram UI), already tested. **No code in this PR places a real order or requires a real secret; going live is still a manual owner action, gated behind this checklist and a separate audit pass.** See note 0041. | needs-human: cloud VM provider choice (ADR-0030) and broker/exchange for the first live sleeve |
| P8 Expansion (MCX, NSE currency, ML ranker, memecoin, gold/bond ETFs, options) | Claude | **implementation-complete except options (deliberately deferred), under mandatory cross-model review — LAST PHASE of BUILD_ORDER.md** — MCX/NSE-currency strategy instances (reusing PR #54's data layer and existing T1/T4 rules), `GLD`/`BND` added to US Tier A (the "gold/bond ETF filter" turned out to be a one-line addition), an experimental advisory-only walk-forward champion/challenger `ml_ranker.py` scoped to rank only already-pre-registered P1 candidates (never a new search), and a memecoin sleeve with a hard code-level paper-only gate (`risk/engine.py`'s `ModeGate.PAPER_ONLY_SLEEVES`, proven by test across every Mode x human_action combination). Options trading code was explicitly NOT written — `docs/specs/OPTIONS_LEARNING_PLAN.md` gates it behind owner learning + a future ADR, per BUILD_ORDER's own "after dedicated learning" instruction. PR #61 on `claude/p8-expansion-sleeves`, based on `claude/p5-crypto-us-sleeves` (#58) based on `claude/sleeve-allocation-and-adapters` (#54); not merged. 139 tests pass, ruff/mypy clean. See note 0042 for the full open-PR merge-order table across #53/#54/#56-#61. | needs-human: options sleeve gate (owner must do the OPTIONS_LEARNING_PLAN.md reading + record a go-ahead ADR); PR merge order across the whole P2-P8 sweep (note 0042) |

## Next 3 actions
1. Owner: decide whether to retain the membership provenance contract or approve a limited non-authoritative reverse reconstruction (note 0057).
2. After permitted historical membership evidence exists, materialize/audit the monthly snapshots and then enumerate the exact action-ledger scope.
3. Owner: freeze the forward-paper promotion policy (daily/intraday observation duration, sample requirements and sizing); P1d's backtest rejection rule is already fixed.

## Blockers / needs-human
- P1 cannot be formally closed or run on real data until a complete authorized corporate-action ledger/coverage exists; automated NSE/NSE Indices collection remains prohibited.
- PR #71 is draft: its evidence binding is the stale five-symbol pilot, not the real research universe. Do not merge it as the real split freeze.
- Nifty 50 reconstruction is blocked on an owner choice between contemporaneous/licensed evidence and a clearly non-authoritative reverse reconstruction (note 0057). All 60 identity mappings now resolve. Nifty 100 is deferred.
- Forward-paper policy for daily versus intraday candidates is an owner decision. It is separate from and not satisfied by P1d's fixed backtest rejection rule.

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
