---
id: 0030
from: codex
to: both
date: 2026-11-15 19:10 IST
subject: Upstox adjustment probe and intraday retention
status: open
refs: [codex/p1-build, docs/BUILD_ORDER.md, docs/specs/CORPORATE_ACTIONS.md]
---

## Context
P1 is active on `codex/p1-build`. Owner requested two independent probes: verify Upstox adjustment basis against a dated NSE split/bonus and probe authenticated intraday data, then add a resumable intraday loader and update P1 scope to include intraday from the start.

## What I did
- Used NSE circular `https://nsearchives.nseindia.com/content/circulars/FAOP60123.pdf`: NESTLEIND 10:1 split, effective 2024-01-05.
- Upstox V3 daily API returned previous-session close ₹1,355.80 (2024-01-04) and ex-date close ₹1,333.20 (2024-01-05). The unadjusted previous close is ~98.3% of ex-date close; the split-equivalent previous close would be ₹135.58. This is evidence Upstox daily values are raw across this event.
- Captured sanitized candle response in `tests/fixtures/upstox/upstox_nestle_2024_split.json`; added a real known-answer test, including the 10x volume adjustment calculation.
- With current `.env` token and browser-like User-Agent, received full sessions for Nifty 50 and five locally available Tier A symbols (RELIANCE, INFY, TCS, HDFCBANK, ICICIBANK): 375 M1 bars and 75 M5 bars on 2026-11-13, 2026-10-15, and 2026-05-15. Both intervals returned empty on 2024-11-15. Nifty M1/M5 returned data in Jan 2022 and no candles for Dec 2021. Provider docs state minute history starts Jan 2022.
- A 44-day request at M1 and M5 was rejected with `UDAPI1148`, confirming max range is one month for minute intervals <=15. Official docs say 50 req/s, 500/min, 2000/30min for standard APIs; this low-rate probe saw no 429.
- Implemented `trading.storage.intraday_loader`: one-month chunks, idempotent append to existing DuckDB CandleStore, Parquet export, request pacing, fresh runtime token required, no `.env` read/fallback. Tests cover chunking, idempotency, export, and stale `.env` rejection.
- Updated `BUILD_ORDER.md` and P1 candidate/evaluation docs: daily swing and intraday start together; ORB needs a separate exact intraday catalog before results.
- Fixed existing P1 math/router/test issues found by full suite (fixed precision mean, missing rounding import, invalid holdout auth assertion).
- Checks: `pytest -q` all passed; `ruff check .`, `ruff format --check .`, `mypy src/trading`, and `git diff --check` passed at checkpoint.

## Where I stopped (exact)
- Branch: `codex/p1-build`
- Last commit: `87bf195`; work remains uncommitted.
- No PR opened. Cross-model review is still required before review-ready status.
- Intraday history results are point probes, not exhaustive per-instrument coverage proof. Documented historical availability is from Jan 2022, but no claim of uninterrupted data for every instrument.
- Loader expects an operator-supplied daily token in the process environment. Automatic OAuth refresh is not implemented because OAuth app/client credentials and login flow are absent. The token from `.env` was used only for this probe and was not written into source or fixture.
- The loader supports storing raw M1/M5 candles. The corporate-action transformer currently accepts daily candles only; intraday action treatment is still required before split-spanning intraday results are trusted.

## What you need to do
1. Cross-model review the new fixture/test, adapter changes, loader, docs, and accumulated P1 code.
2. Decide/implement Upstox OAuth token refresh only after OAuth client configuration and documented redirect/login flow are available; continue requiring fresh runtime injection until then.
3. Add an exact, pre-registered intraday candidate catalog (including ORB event ordering and session rules) before any intraday ranking.
4. Do not start real rankings/holdout until source rights/coverage, P1a universe, action ledger, split window, allocation/replay and owner viability gates are resolved.

## Decisions made (+ ADR ids)
- User explicitly directed P1 to target daily swing and intraday from the start.
- One real Upstox event is sufficient to classify that observed series as raw/unadjusted; it does not prove all adjustment types/instruments.
- Runtime loader does not consume `UPSTOX_ACCESS_TOKEN` from `.env`; a daily token is not a renewable credential.

## Open questions
- This probe does not resolve source-rights/coverage for the bulk NSE corporate-action or historical membership dataset.
- Existing open P1 owner decisions still include promotion horizon, untouched holdout boundary, viability thresholds, position share-count treatment, and portfolio allocation/replay.

## Model/usage notes
- Codex implemented; upstream docs and live Upstox/NSE requests were used as evidence. No token or account profile data is recorded.

## Reply
