---
id: 0032
from: claude
to: both
date: 2026-11-15 14:30 IST
subject: Sleeve allocation test coverage + full non-India data ecosystem (crypto/US/NSE-currency/MCX)
status: open
refs: [claude/sleeve-allocation-and-adapters, docs/DATA_ECOSYSTEM_BUILD_PLAN.md, docs/BUILD_ORDER.md, docs/MARKETS.md]
---

## Context
Owner asked for (1) a per-sleeve allocation/risk-cap check in the RiskEngine
with a dedicated, tightly-capped memecoin sleeve distinct from general
crypto, and (2) data-only adapter scaffolds for US equities, crypto, MCX,
and NSE currencies, matching the depth already built for India/Upstox.
Built in a separate git worktree on `claude/sleeve-allocation-and-adapters`,
based on `claude/p2-implementation` (PR #50's RiskEngine), so as not to touch
`codex/p1-build`'s in-flight uncommitted work.

## What I did
1. **Sleeve allocation cap**: turned out to already exist — `RiskEngine`
   check 8 (`src/trading/risk/engine.py`) and `SleeveState.allocation_cap_pct`
   (`src/trading/risk/portfolio.py`) already enforce a per-sleeve cap,
   config-driven (`config/risk.example.yaml` already lists `memecoin` as a
   sleeve separate from `crypto` with a tighter cap: 5% vs 25%). Only test
   coverage was missing. Added `test_check_8_sleeve_allocation_exceeded` and
   `test_memecoin_allocation_cap_enforced_independently_of_crypto_cap` to
   `tests/risk/test_engine.py` — both pass, full risk suite green.
2. **Crypto** (commit e78f131): `BinanceHistoryClient` (free public REST, no
   key, stdlib urllib, same shape as `upstox_history.py`); a listing-registry
   module (`crypto_integrity.py`) detecting delists/rebrands/undeclared gaps
   as crypto's equivalent of the split-adjustment problem; mechanical
   universe rules for both the general crypto sleeve and memecoin sleeve
   (`crypto_universe.py` — liquidity floors + listing-age, no hand-picking);
   a resumable loader (`crypto_loader.py`). Verified live: no history-depth
   cutoff, 1,000 candles/request, self-throttled to 60 req/min under
   Binance's real limit.
3. **US equities** (commit 6c199ab): `AlpacaHistoryClient` (free Basic/IEX
   plan, requires a free-to-obtain key unlike Binance). **Correction to
   `docs/MARKETS.md`**: it claimed Alpaca bars are split/dividend-adjusted by
   default — live-verified this is false, Alpaca's default is `raw`; built
   `us_equity_corporate_actions.py` as an independent adjustment layer
   sourced from Alpaca's own free corporate-actions feed. Universe =
   liquidity-ranked top-100 (survivorship-safe) plus a Wikipedia-sourced
   S&P 500 membership manifest, **flagged benchmark-only, not an audited
   index feed**. Known-answer test uses Apple's real 2020-08-31 4:1 split.
4. **NSE currencies** (commit 91c504a): verified the existing
   `UpstoxHistoryClient` needs zero changes (instrument-key-agnostic; CDS_FO
   segment vs NSE_EQ is just a different string). No corporate-action
   equivalent. No roll-stitching attempted (each expiry queried separately,
   so no fake-jump bug exists yet). Confirmed session hours 09:00-17:00 IST,
   genuinely different from equities — resolves a previously-unverified
   `docs/MARKETS.md` note.
5. **MCX commodities** (commit 934d7eb): **did not hit the expected
   paywall** — Upstox's own instrument master has a free `MCX_FO` segment
   with lot size/expiry per contract, and the existing adapter works
   unmodified. Built real roll-adjustment logic this time
   (`mcx_roll.py`, ratio back-adjustment, explicitly flagged display/backtest
   -only — live signal code must still read the single current-expiry key,
   no look-ahead) plus a fixed 5-instrument universe. This roll logic is
   generic and reusable for NSE currencies later if a continuous FX series
   is ever wanted (per item 4's note).

All phases: full `pytest` suite green throughout, `ruff check`/`format
--check` clean, `mypy` clean on every new module. No order execution, no
strategy code touched anywhere. `codex/p1-build` and `main` untouched.

## Where I stopped (exact)
- Branch `claude/sleeve-allocation-and-adapters`, pushed to origin, 6 commits
  (c62ce47 plan+risk tests, e78f131 crypto, 6c199ab US equities, 91c504a NSE
  currency, 934d7eb MCX). No PR opened yet.
- `docs/DATA_ECOSYSTEM_BUILD_PLAN.md` status log fully checked off.
- `docs/BUILD_ORDER.md` has new coverage sections for all four markets;
  `docs/MARKETS.md` §5 updated with confirmed (not "verify") facts.

## What you need to do
1. Cross-model review before merge (risk/adapters are critical per AGENTS.md
   §5) — this touches `RiskEngine`-adjacent tests only (no engine logic
   changed) plus four new, isolated adapter/storage modules; low blast
   radius, but still needs the review.
2. Open the PR into `main` from `claude/sleeve-allocation-and-adapters`
   (I did not open one myself).
3. Owner decision (not urgent, not a dead end): the Wikipedia S&P 500
   membership list is free but community-maintained — fine for
   benchmark-only use as scoped, confirm before relying on it further. Also:
   if Alpaca's corporate-actions feed ever becomes unavailable/paywalled,
   there's currently no verified free full-coverage replacement for US
   equity splits/dividends.
4. MCX session hours ("approx 09:00-23:30, or 23:55 seasonally") remain
   unconfirmed against a primary source — needs checking before this sleeve
   goes to paper.

## Decisions made (+ ADR ids)
- No ADR needed — all choices (Binance over ccxt for a single exchange,
  Alpaca Basic/IEX, reuse of UpstoxHistoryClient for CDS_FO/MCX_FO) follow
  already-decided sources in `docs/MARKETS.md` §6 proposed stack; none
  changed the proposed stack itself.

## Open questions
- Which exchange to actually trade/execute crypto on (pre-existing AGENTS.md
  §2 open item, unchanged by this work — this PR is data-only).
- Whether a continuous NSE-currency series is ever wanted (if so, reuse
  `mcx_roll.py`'s `build_continuous_series` rather than duplicating it).

## Model/usage notes
Implementation by Claude (orchestrator + 4 subagents, one per market phase,
run sequentially with build-test-report-move-on between each). All work
done in a separate git worktree at `/home/dishant/Desktop/Tijori-sleeve` to
avoid touching `codex/p1-build`'s uncommitted working-tree state.

## Reply
