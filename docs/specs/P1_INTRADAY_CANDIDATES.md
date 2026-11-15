# P1 intraday candidate catalog

Status: pre-registered, deterministic P1b candidate rules. These definitions
must be versioned and frozen before any intraday result is inspected. They
are hypotheses, not recommendations or evidence of profitability.

## Scope and shared assumptions

- Catalog version: `p1-intraday-v1`; market: NSE cash equities, long-only.
- Bars: Upstox 5-minute candles only. The 1-minute series is retained for
  coverage and future research but is not a second ORB trial family in this
  catalog. Provider history begins January 2022; no earlier data is assumed.
- Use only complete, exchange-calendar sessions with exactly the expected
  opening-range bars and valid OHLCV. Missing/duplicate/out-of-order bars,
  abnormal session dates, or an incomplete session invalidate that symbol-day;
  never forward-fill candles.
- Session clock: `Asia/Kolkata`, regular NSE session 09:15–15:30. Square off
  at 15:15 using the shared market profile. Holidays and special sessions come
  from the verified calendar; absent calendar coverage blocks the run.
- Signals use closed bars; fills occur at the next 5-minute bar open with the
  shared cost/slippage model. If the next bar is absent or begins at/after
  square-off, the signal expires unfilled. No same-bar entry/exit.
- One position maximum per symbol per session and one entry attempt per
  symbol-day, including after a stop-out. No overnight carry, pyramiding, or
  shorting. The comparison sizing assumption is 1% of the ₹1,00,000 research
  placeholder capital; this is not live sizing.

## T5 ORB exact event order

1. Opening range is the first three complete 5-minute bars, with open times
   09:15, 09:20 and 09:25. Set `range_high=max(high)` and
   `range_low=min(low)` from those bars only. The range freezes at 09:30.
2. Starting with the bar opened at 09:30, evaluate each bar only after its
   close. The first close at or before 11:30 strictly greater than
   `range_high * 1.0005` creates a buy signal. A close exactly equal to the
   threshold does not qualify. Do not use the current bar's high as a signal.
3. The order fills at the next bar's open plus buy-side costs/slippage. If
   entry cannot fill before square-off, drop it. Stop and target are fixed from
   the opening range and actual fill price: stop is the range low; target is
   `fill_price + m * (range_high - range_low)`. If the fill is at/below the
   stop, reject the trade as invalid rather than moving the stop.
4. Once filled, inspect each subsequent closed bar's high/low. If both stop and
   target are touched within one bar, assume stop first. Otherwise execute a
   touched stop/target at its level with the shared adverse slippage rule.
   If neither is touched, close at the 15:15 square-off using the last
   available bar close and corresponding costs. There is no re-entry that day.
5. If data ends before a valid exit, mark the position open and the session
   incomplete; it cannot count as a completed trade or a valid full-session
   comparison. Do not silently discard it.

## Frozen variant grid

Exactly three variants are included; only target multiple changes. All other
rules above, universe, dates, costs, calendar and sizing are identical.

| Candidate ID | Range | Buffer | Stop | Target multiple |
|---|---:|---:|---|---:|
| `t5-orb-m1-v1` | 15 min | 0.05% | range low | 1.0 × range size |
| `t5-orb-m15-v1` | 15 min | 0.05% | range low | 1.5 × range size |
| `t5-orb-m2-v1` | 15 min | 0.05% | range low | 2.0 × range size |

No midpoint-stop variant, 1-minute variant, alternate opening range, filter,
or free-form sweep is authorized in this study. Adding one requires a new
catalog version and increases the declared multiple-testing family before
results are accessed.

## Data, actions, and evaluation gates

- Require the P1a source, licensing, symbol-window coverage, and split-plan
  gates before any ranking. Corporate-action adjustments and position share
  replay must be valid for intraday data; otherwise exclude the affected
  instrument/window.
- Compare with cash and same-session buy-and-hold baselines using identical
  windows, sizing and costs. Report the P1c metrics and coverage denominator;
  do not rank by win rate or raw rupee P&L.
- All three variants count toward P1's predeclared multiple-testing family.
  The P1 evaluation spec currently specifies Bonferroni over 15 daily variants;
  it must be revised to include these three intraday variants (18 total) before
  any real ranking.
- Intraday promotion requires a longer forward paper period and more
  conservative sizing than daily. Numeric promotion thresholds remain an
  owner decision; this catalog does not invent them.
