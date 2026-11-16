# 04 — Daily reports and shadow mode

## What this is
A **daily report** is a one-page summary of what the trading system did
today: how many trades it made, how many signals the risk engine turned
down (and why), and how much money those closed trades made or lost.
**Shadow mode** (also called "auto-paper") means the system approves its
own paper trades with no human tapping a button — useful for testing a
strategy continuously without you sitting at your phone.

## Why it exists
Without a daily report you'd have to open the database and write SQL by
hand to answer "did anything break today?" That doesn't scale to a system
meant to run unattended for a week (P3's exit criterion). Without shadow
mode, every single paper signal needs your Telegram tap, which defeats the
point of testing a strategy overnight or during a busy week at college.

## Tiny example
If the risk engine rejected 3 signals today because the kill switch was
engaged, and 1 trade closed as a win worth +2.5% after costs, the report
looks like:
```
# Daily report — 2026-11-16
- Fills: 1
- Signals rejected by risk engine: 3
- Realized P&L (closed positions, after costs): 2.5

## Rejection reasons
- kill_switch_engaged: 3

## Signal outcomes
- win: 1
```

## How to run it in this repo
```bash
python -m trading.reporting.daily_report data/state.db 2026-11-16
# or, for the dashboard version with totals as metric tiles:
streamlit run dashboard/Home.py
```

Shadow mode is not new code — it already exists. Set a sleeve's mode to
`paper` (`src/trading/core/enums.py::Mode.PAPER`); the risk engine's
`ModeGate.route()` sends every allowed signal straight to the paper broker
with no human action needed (`src/trading/risk/engine.py`). `approval` mode
is the one that waits for your Telegram tap; `auto` sends real orders.

## Common mistakes
- Reading "today" as your local time instead of UTC. The report takes a
  UTC date because every timestamp in the database is UTC (AGENTS.md §6).
  If it's past midnight IST but still before 18:30 UTC the previous day,
  "today" in the report is still yesterday in UTC.
- Confusing `paper` mode (shadow, no approval needed) with `approval` mode
  with every signal auto-clicked "approve" — they look similar from the
  outside but `approval` mode without a human is a stuck pending queue,
  not a shadow run.

## Check yourself
1. If the risk engine rejects a signal, which table does the daily report
   read to find out why? (`decisions`, via its `reason_codes` field.)
2. Which sleeve mode lets signals become paper trades with zero human taps?
3. Why does the report match timestamps with `LIKE '2026-11-16%'` instead
   of parsing them into real datetimes? (Every writer already stores a
   fixed UTC format, so a string prefix match is correct and cheap — see
   ADR-0029 in `docs/decisions.md` for when that stops being true.)

## Words used in this lesson
- **daily report**: an end-of-day summary of trades, P&L, and rejections.
- **shadow mode / auto-paper**: signals auto-approve straight to the paper
  broker, no human approval step.
- **kill switch**: an emergency stop that blocks new trades across a scope
  (a sleeve or the whole system) until a human releases it.
