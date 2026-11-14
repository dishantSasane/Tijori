# STRATEGIES

Everything here is a **candidate** to be tested, not a proven edge. Backtests decide what survives; expect to drop many. Rules below are precise enough to code. Parameter defaults are starting points to sweep, not recommendations.

## 1. Vocabulary

- **Template**: reusable strategy logic, coded once (`trading.strategies.<template>`).
- **Market profile**: per-market settings (hours, costs, filters, parameter ranges).
- **Strategy instance** = template + market profile + timeframe + parameters. Each instance has its own id, version, status, scorecard. A pass in one market gives **no** credit in another.
- **Sleeve**: a market's capital bucket.
- **Signal**: output of a strategy: `{id, instance_id, version, market, symbol, side, bar_ts, entry_ref, stop, target, risk_pct, reason_codes[], features{}}`.

## 2. Execution semantics (apply to every template and the backtester)

1. Evaluate on **closed bars** only. Signal at bar `t` close -> order fills at bar `t+1` **open**, plus slippage and costs from the market profile.
2. Stops/targets are checked intrabar using that bar's high/low; if both are touched in one bar, **assume the stop hit first**.
3. Position size from risk: `qty = floor((equity_sleeve * risk_per_trade_pct) / |entry - stop|)` capped by sleeve limits (`RISK_SPEC.md`).
4. Long-only unless a spec says otherwise (shorting out of scope, `AGENTS.md` §10).
5. Time stop: optional max bars held per template.
6. Intraday templates are flat by the market's square-off time.

## 3. Phase-1 templates (exact rules)

Notation: `H(n)` highest high of the previous n bars (excluding current), `L(n)` lowest low, `ATR(n)` Wilder ATR, `SMA/EMA`, `RSI(n)` Wilder RSI, `ADX(n)`.

**T1 Donchian breakout (trend following)**
- Entry: `close > H(N)` (default N=20; sweep 10-55).
- Exit: `close < L(M)` (default M=10) or stop.
- Stop: `entry - k*ATR(14)` (default k=2).
- Filters (optional): `close > SMA(200)`.

**T2 MA trend + ADX**
- Entry: `EMA(F) > EMA(S)` just crossed up (defaults F=20, S=50) and `ADX(14) > A` (default 25).
- Exit: `EMA(F) < EMA(S)` or stop `entry - k*ATR(14)` (k=2).

**T3 Cross-sectional momentum (Tier B friendly)**
- Universe: after liquidity filters, closed daily bars.
- Score: return over lookback `L` days skipping the most recent `S` days (defaults L=126, S=21; sweep L 63-252).
- Select top `K` (default 20) with `close > SMA(200)`; equal weight (or inverse-volatility as a variant).
- Rebalance every `R` trading days (default 21). Exit on drop out of top `2K` or stop.
- Notes: needs survivorship-free, corporate-action-adjusted history.

**T4 RSI(2) pullback in an uptrend (short-term mean reversion)**
- Entry: `close > SMA(200)` and `RSI(2) < r` (default r=10; sweep 5-15).
- Exit: `close > SMA(5)` or `RSI(2) > 70`; time stop 5 bars; stop `entry - k*ATR(14)` (k=2.5).

**T5 Opening range breakout (intraday)**
- Opening range: high/low of the first `R` minutes after open (default 15; sweep 5-30), using closed bars of the intraday timeframe (default 5-min).
- Entry: first close above range high plus buffer `b` (default 0.05%) before a cut-off time (default 11:30 local).
- Stop: range low (variant: range midpoint). Target: entry + `m * range_size` (default m=1.5; sweep 1-3). Flat at square-off time.
- At most one trade per symbol per day.

**T6 Bollinger mean reversion (range regimes)**
- Entry: `close < lowerBand(N, k)` (defaults N=20, k=2) and `ADX(14) < 20`.
- Exit: `close >= middleBand` or stop `entry - 1.5*ATR(14)`; time stop 10 bars.

**Filter module F1 Candlestick confirmation** (never standalone; configurable thresholds)
Let `body=|close-open|`, `range=high-low`, `upper=high-max(open,close)`, `lower=min(open,close)-low`.
- Hammer: `lower >= 2*body`, `upper <= 0.3*body` (or <= 10% of range), body in the upper third of range; require preceding downtrend (e.g. close below SMA(20)).
- Bullish engulfing: previous candle bearish, current bullish, current body fully covers previous body.
- Doji: `body <= 0.1*range` (context only).
- Morning star: bearish candle, small-body candle gapping/closing lower, then bullish candle closing above the midpoint of the first.
- Use: allowed as a confirmation (e.g., T4 entry only if a bullish engulfing/hammer printed at support). Whether any pattern adds value is decided by backtest.

## 4. Later templates (Phase 2/3; not specified yet)

VWAP intraday (reversion/trend); volatility squeeze breakout (Bollinger inside Keltner); volume-surge breakout and 52-week-high proximity (Tier B); crypto funding-rate carry (delta-neutral); pairs/relative value (e.g., two banks); options defined-risk premium selling / directional spreads; event/news via Brain; ML ranker over the same features. Add exact specs here before coding.

## 5. Candidate matrix (starting set)

| Market | Start with | Add later |
|---|---|---|
| India Tier A | T5 ORB, T1 breakout, T4 RSI(2) | VWAP, squeeze, pairs |
| India Tier B | T3 momentum, volume-surge breakout, 52-week-high | ML ranker |
| US | T3 momentum / sector rotation, 200-day trend filter, T4 | ORB, pairs |
| Crypto | T1, T2, momentum across top coins | funding carry, T6 in ranges |
| Memecoins | paper-only: volume+momentum rules with strict safety checks | live only if forward paper justifies |
| MCX | T1, T2 | seasonality |
| NSE currencies | T6, slow trend filter | none |
| Options | none in P1 | defined-risk spreads |
| Gold/bond ETFs | simple trend filter for when to hold | none |

Pair strategies that fail in opposite conditions (trend vs mean reversion).

## 6. Lifecycle and promotion gates

Status values: `idea -> coded -> in_sample -> out_of_sample -> robust -> paper -> approval -> auto -> retired`.

| Gate | Requirement (initial defaults; adjust with evidence via ADR) |
|---|---|
| Hypothesis | One paragraph: why should this work and when should it fail? |
| Coded | Rules match this document; unit tests; no look-ahead tests pass |
| In-sample | Costs and slippage included; <= 5 free parameters |
| Out-of-sample | Design period vs untouched hold-out; plus walk-forward windows; results not collapsing out-of-sample |
| Robust | Edge survives ±10% perturbation of each parameter; positive across regimes (bull/bear/sideways) or clearly regime-labelled; enough trades (target >= 100 total, or >= 5 years for slow strategies) |
| Paper | Weeks of live paper; live-vs-backtest comparison within expected range; no data/execution surprises |
| Approval | Tiny real size, human approves each signal |
| Auto | Only after sustained approval-mode record; kill switches verified |

Overfitting rules: count every decision made while developing; every tweak after seeing results counts. Prefer parameter *plateaus* over peaks. Do not tune on the hold-out.

## 7. Scorecard (stored per instance and per version)

`period, trades, win_rate, avg_win, avg_loss, expectancy, profit_factor, total_return, CAGR, max_drawdown, longest_drawdown_days, Sharpe/Sortino (labelled as estimates), exposure_pct, turnover, avg_bars_held, cost_drag_pct, in_sample vs out_of_sample columns, live/paper columns when available`.

## 8. Registry

`config/strategies.yaml` (committed example in P0; real file git-ignored if it contains private sizing) with one row per instance:

```yaml
- id: t1_donchian__india_equity__1d
  template: t1_donchian
  market: india_equity
  timeframe: 1d
  version: 1.0.0
  params: {N: 20, M: 10, k: 2.0, trend_filter: true}
  status: idea
  frozen_at: null
  scorecard_ref: null
  notes: ""
```

Live versions are **immutable**. Changing parameters = new version + new run through the gates. Champion/challenger: a candidate version runs in paper beside the live one and replaces it only if it beats it over a fair period.

## 9. Monitoring and review cadence

- Daily: log live/paper vs backtest-expected (no re-tuning).
- Weekly: short review for trouble signs.
- Monthly/quarterly: scheduled review; ML models retrained with walk-forward validation, challenger in paper first.
- Early review triggers: drawdown beyond backtest worst case, win rate/avg profit outside backtest range over a meaningful trade count, clear regime change. The risk engine auto-pauses an instance that breaks its configured limits.

## 10. Tier B scanner (how whole-market coverage works)

1. Download daily file (India: NSE bhavcopy; US: daily bars; crypto: bulk daily candles), append to the daily candle store.
2. Apply universe filters (config).
3. Score per stock: 1/4/12-week and 1/3/6-month returns, distance from 52-week high, volume surge vs average, trend structure (higher highs/lows, above MAs).
4. Run strategy conditions (T3 etc.) -> shortlist (top 20-50) with reason codes.
5. Shortlist feeds the Stocks page and next session's live watch. Backtest the scanner like any strategy: replay history day by day; measure forward 5-10 day outcomes of each day's shortlist.
