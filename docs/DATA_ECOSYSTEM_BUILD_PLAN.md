# Data ecosystem build plan — US equities, crypto, MCX, NSE currencies

Branch: `claude/sleeve-allocation-and-adapters` (separate worktree, never touches
`codex/p1-build` or any India strategy/universe work). Data-only: no order
execution, no strategy work, in any phase below.

Goal: give each non-India market the same depth that India equities already
has via Upstox — adapter, corporate-action/contract-event integrity handling,
point-in-time universe, idempotent resumable loaders, known-answer tests,
and documented coverage limits in `docs/BUILD_ORDER.md`.

## Order (sequential — build, test, report, move on; not parallel)

1. **Crypto** (general sleeve + memecoin sleeve) — most free tooling available.
2. **US equities**
3. **NSE currencies** — verify it's genuinely simpler before assuming so.
4. **MCX commodities** — most likely to hit a paywall. If no viable free
   source exists for history or point-in-time contract data: stop, report,
   do not keep searching. This becomes an owner decision (pay, or drop the sleeve).

## Per-market checklist (same shape every time)

1. Data adapter, same `Protocol`/class shape as `adapters/upstox_history.py`.
   State explicitly what's free / free-tier / paid / unavailable for daily
   and intraday candles — don't quietly settle for a worse source unflagged.
2. Corporate-action / contract-event integrity handling (split/dividend for
   equities, delist/rebrand detection for crypto, contract-roll logic for
   MCX futures, verify-don't-assume for NSE currencies).
3. Point-in-time universe definition where relevant: rule-based (liquidity/
   market-cap, computed over time, survivorship-safe by construction) plus,
   for benchmarking only, a reconstructed index-membership manifest from free
   sources. Memecoin sleeve: objective mechanical inclusion criteria, no
   hand-picked tokens.
4. Idempotent, resumable historical loader (daily + intraday), matched to
   that API's actual rate/request-size limits — verified, not assumed from
   Upstox's numbers.
5. Known-answer test(s) proving the adjustment/integrity logic, same pattern
   as the India split/bonus known-answer test in `tests/storage/test_corporate_actions.py`.
6. `docs/BUILD_ORDER.md` updated with that market's empirically-verified
   coverage limits (history depth, intraday window, rate limits) — verify
   each one before writing it down, same as the Jan-2022 India intraday note.

## Status log

- [x] Crypto
- [x] US equities
- [ ] NSE currencies
- [ ] MCX commodities
