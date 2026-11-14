# PAGES (dashboard and alerts)

The dashboard is a **window** onto the engine via the internal API; the engine runs without it. First implementation: Streamlit + FastAPI. Telegram carries alerts and the three buttons so the owner can act from a phone.

## 1. Page list

| Page | Purpose | Key content |
|---|---|---|
| **Home** | Whole picture in one glance | Tile per market (Open/Closed + next open), total equity/P&L, per-sleeve P&L, risk status, kill-switch button, mode per sleeve, Brain cost today |
| **Market page** (one each: India, US, Crypto, Commodities, Memecoin) | Work in a market | Live watchlist (Tier A + promoted Tier B), pending signals, open positions, strategy performance for that market, Approve/Paper test/Reject buttons, session status |
| **Stocks (India, US)** | Ideas beyond trades | Shortlist cards from the scanner: why it is trending, suggested "consider exiting near" and "reconsider below" levels, Add to watchlist, Paper track |
| **News** | Live headlines | RSS/official announcements, tags (market, symbol, sentiment), filter to watchlist/positions; Brain reads only matching items |
| **Paper ledger** | Simulated trading | Paper trades and P&L by strategy/market; `source` = user_paper or shadow; rejected-signal outcomes ("would have made +x%") |
| **Strategies** | Registry and trust | Per instance: version, status, scorecard, backtest vs live/paper comparison, pause/resume, promotion history |
| **Usage and accounts** | Costs and balances | Brain tokens and INR per market/day/month vs budget; broker balances and open positions (read-only); connection health and token expiry; brokerage, statutory charges and estimated tax per market (labelled estimates) |
| **Settings and risk** | Control | Limits (from config), modes (paper/approval/auto), kill switch, auto-paper shadow toggle, universe filters |

## 2. Alert card (Telegram and dashboard)

```
BUY signal: HDFC Bank (NSE)            [Strategy: Breakout + Trend v1.0.0]
Why: broke 20-day high, volume 1.8x average, index trend up
Entry 1650 | Target 1683 (+2.0%) | Stop 1634 (-1.0%) | Suggested qty 12 (risk 0.5%)
Similar setups (this strategy, last 30): 19 hit target, 11 hit stop, avg +1.4%
Yours: you rejected 7 of 10; 5 of those 7 would have worked
Context (optional Brain): results season; sector news neutral
[Approve]  [Paper test]  [Reject]
```

- Approve is enabled only if the sleeve mode is `approval` (or the owner is manually promoting a paper idea). In `paper` sleeves only Paper test/Reject show.
- "Why" text is templated from reason codes (free); the Brain adds only a short optional context line.
- "Similar setups" shows statistics over many signals, not a single anecdote.

## 3. Internal API (names to be fixed in specs)

`GET /home`, `GET /markets/{id}`, `GET /signals?state=pending`, `POST /signals/{id}/decision {approve|paper|reject}`, `GET /ledger/{live|paper}`, `GET /strategies`, `POST /strategies/{id}/pause`, `GET /usage`, `GET /accounts`, `POST /killswitch {scope, engage|release}`, `GET /news`. Authentication required even locally; bind to localhost by default.

## 4. Behaviour rules

- The dashboard never talks to brokers directly; only the engine/API does.
- Every action that changes mode or releases a kill switch requires explicit confirmation and is audit-logged.
- Closed markets show "Closed" and the post-market report instead of a live view.
