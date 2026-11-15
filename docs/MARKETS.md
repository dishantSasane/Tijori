# MARKETS

Per-market profiles. Facts marked **(verified 2026-11-14)** came from web research on that date; everything else is a design choice or must be verified before relying on it. Prices and rules change: re-check before spending money.

## 1. Summary

| Market | Tier A (live) | Tier B (daily whole-market) | Data (free-first) | Orders | Phase |
|---|---|---|---|---|---|
| India equities (NSE) | Nifty 50 + Next 50 (~100) | NSE bhavcopy + corporate actions | Angel One SmartAPI or Fyers free data; or Kite Connect data | Zerodha Kite Connect Personal (orders only) | P1-P4 |
| US stocks/ETFs | Nasdaq 100 (+ key ETFs) | Daily bars for all US stocks via Alpaca | Alpaca free plan | Alpaca paper first; live route (LRS/IBKR) later | P5 |
| Crypto | BTC, ETH, top ~20 by volume | Daily candles for all pairs on the chosen exchange via CCXT | CCXT public endpoints | Exchange via CCXT (withdrawals disabled) | P5 |
| MCX commodities | all relevant contracts (few) | not needed | via Indian broker API | Kite | P8 |
| NSE currencies | USDINR, EURINR, GBPINR, JPYINR | not needed | via Indian broker API | Kite | P8 |
| Nifty/BankNifty options | chain for the index | not needed | via Indian broker API | Kite | P8, gated |
| Memecoins (DEX) | none | new/trending pairs from a DEX data API | public DEX data (verify terms) | wallet via a DEX aggregator | P8, paper-only until proven |
| Gold/bond ETFs | few ETFs | not needed | via Indian broker API | Kite | P8 |

## 2. India equities

**Hours:** 09:15-15:30 IST, weekdays, excluding NSE holidays (use a calendar library).
**Universe:** Tier A `nifty50_plus_next50`; Tier B all NSE equity (`EQ` series) after filters (config): price floor, minimum average daily traded value, optional surveillance-list exclusion. The bhavcopy contains per-stock OHLC, previous close, volume, traded value, number of trades; a companion file has delivery quantity. NSE keeps archives, so download history first rather than waiting to accumulate.
**Corporate actions:** adjust daily history for splits/bonuses/rights using NSE corporate-actions data, else backtests see fake crashes. Keep delisted stocks in history (survivorship).
**Data/API costs (verified 2026-11-14):**
- Zerodha Kite Connect **Personal: Rs 0**, orders/GTT/alerts/positions only; **no live or historical data**. **Connect: Rs 500/month** adds WebSocket live data and historical candles.
- Angel One SmartAPI: API and historical data **free**; brokerage about Rs 20 per executed intraday/F&O order.
- Fyers: API free, states historical/quotes/market data free.
- Upstox: APIs free; Rs 10 per executed API order stated until 31 Dec 2026.
- Dhan: trading API free; data API about Rs 499 per 30 days.
- Recommended zero-cost split: free data from Angel One or Fyers account; orders via Zerodha Personal. Adapters keep data and execution separate.
**Order rules:** SEBI static-IP rule, see `COMPLIANCE_INDIA.md`.
**Paper-fill assumptions (placeholders):** brokerage Rs 20/order, slippage 5 bps for large caps, wider for small/illiquid; add statutory charges from the broker's contract note.
**Intraday:** square off before cut-off (default 15:15 IST) for intraday strategies.

## 3. US equities

**Hours:** regular 09:30-16:00 America/New_York = 19:00-01:30 IST in US daylight time, 20:00-02:30 IST in standard time. Use `XNYS` calendar.
**Data (verified 2026-11-14):** Alpaca's free data plan is included with paper and live accounts; free plan reported at 200 requests/min and 1 WebSocket, IEX feed; paper keys have no daily data cap per Alpaca forum. Alpaca provides split/dividend-adjusted bars.
**Universe:** Tier A Nasdaq 100 + a few sector/market ETFs; Tier B all US stocks from Alpaca's asset list with price/liquidity filters (exclude OTC).
**Costs:** commissions 0 on Alpaca; slippage ~5 bps for large caps; FX/remittance and tax considerations are the owner's with a CA (`COMPLIANCE_INDIA.md`).
**Phase:** paper only first (Alpaca paper). Live route (LRS via a broker such as IBKR) is a later decision.

## 4. Crypto

**Hours:** 24/7. Define a **daily cutoff** (default 00:00 UTC = 05:30 IST) for daily candles.
**Data:** CCXT public endpoints for candles/tickers; bulk daily candles for all pairs give the Tier B scan. Perp funding rates for carry strategies.
**Orders:** exchange via CCXT; **withdrawal permission disabled**, IP-restricted keys if offered. Exchange choice is an open question (legality/tax/compliance for an Indian resident: owner decides with a CA).
**Universe:** Tier A BTC, ETH + top ~20 by volume with a spread/liquidity filter. Survivorship: store delisted pairs.
**Costs placeholders:** taker fee 10 bps, slippage 10 bps (higher for small caps).

## 5. MCX commodities and NSE currencies

Few instruments, all Tier A. Same broker adapter as India equities (Upstox's
historical-candle client is instrument-key-agnostic; currency derivatives use
Upstox's `CDS` segment / `CDS_FO|<token>` keys, equities use `NSE_EQ` — same
client, different key string; verified in `docs/BUILD_ORDER.md`, "NSE
currencies coverage"). MCX hours are per-instrument (approx 09:00 to 23:30,
or 23:55 in some seasons; verify). NSE currency derivatives hours: confirmed
09:00-17:00 IST Monday-Friday, different from equities' 09:15-15:30
(verified; no longer open). Contracts expire monthly: for NSE currencies,
each expiry is queried as a separate instrument, no continuous-series
stitching is attempted (no roll-adjustment layer needed). MCX still needs its
own roll/continuous-series spec (P8) and NSE currencies should reuse it if a
continuous series is ever wanted here.

## 6. Options (Nifty/BankNifty)

Gated to P8 after everything else is proven. SEBI data shows most retail F&O traders lose money; treat as a high-risk sleeve with defined-risk structures only, small caps, and a dedicated learning phase. Needs expiry/lot-size/greeks handling and expired-contract data; not specified yet.

## 7. Memecoins

Paper-only until a forward paper record justifies more. Requires: minimum pool liquidity, token-safety checks, maximum position as % of pool, pessimistic slippage (100 bps+ placeholder), wallet isolation (separate wallet with a small funded balance), no auto-approve of unknown tokens. Data source TBD (public DEX data API; check terms). Sleeve cap tiny (illustrative 5%).

## 8. Profile fields (shared by all markets)

`calendar, timezone, session, intraday_square_off, tier_a_universe, tier_b{enabled, source, filters}, data{live_provider, history_provider}, costs{brokerage, slippage_bps, taxes}, extra_checks`. See `config/markets.example.yaml`.

## 9. Sources used (re-verify before relying)

- Zerodha Kite API charges: https://support.zerodha.com/category/trading-and-markets/general-kite/kite-api/articles/what-are-the-charges-for-kite-apis
- Zerodha Personal API announcement: https://zerodha.com/z-connect/?p=411859
- Broker API cost comparison (checked Oct 2026): https://onetradejournal.com/trading-apis
- Angel One SmartAPI: https://angelone.in/knowledge-center/smartapi/detailed-introduction-to-smartapi
- Alpaca market data plans: https://alpaca.markets/docs/market-data
