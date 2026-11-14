# 01 — Candles, ticks, and why we summarise

## What this is
A **tick** is one trade: "RELIANCE traded at ₹2,501.20, 10 shares, at
10:03:14.221." A busy stock can have thousands of these a minute. A
**candle** (also called a bar) squashes a time window of ticks into five
numbers: the price when the window opened, the highest and lowest price
during it, the price when it closed, and the total volume traded.

## Why it exists
No strategy needs to know about every individual trade — it needs to know
"did the price go up or down over the last 5 minutes, and by how much."
Candles are that answer, at a fixed, predictable size. Keeping every tick
forever would also be a lot of storage for very little extra insight once
you have the candle; keeping candles forever is cheap (years of 1-minute
candles for ~100 stocks is a few hundred MB), so that's what we keep.

## Tiny example
Ticks arriving in a 5-minute window for one stock:

| Time | Price |
|---|---|
| 10:00:05 | 2500 |
| 10:01:40 | 2505 |
| 10:02:10 | 2498 |
| 10:03:14 | 2501 |
| 10:04:50 | 2503 |

That window becomes one candle: `open=2500, high=2505, low=2498, close=2503,
volume=<sum of the trade sizes>`. The candle is only final — "closed" —
once the 5-minute window has fully passed. We never use a candle before it
closes, because that would mean peeking at information from the future
relative to when a strategy is supposed to be deciding (see lesson 03's
"look-ahead" trap).

## How to run it in this repo
There's no live feed yet (that's a later build phase), but you can see the
shape of a candle today:

```bash
python3 -c "
from decimal import Decimal
from datetime import datetime, timezone
from trading.core.models import Candle
from trading.core.enums import MarketId, Timeframe

c = Candle(
    market=MarketId.IN_EQUITY, symbol='RELIANCE', timeframe=Timeframe.M5,
    ts_open_utc=datetime(2026, 1, 1, 4, 30, tzinfo=timezone.utc),
    open=Decimal('2500'), high=Decimal('2505'), low=Decimal('2498'),
    close=Decimal('2503'), volume=Decimal('12000'), source='fake',
    ingest_ts=datetime(2026, 1, 1, 4, 35, tzinfo=timezone.utc),
)
print(c)
"
```

Try changing `high` to something less than `low` — it will refuse to
construct the candle. That's not an accident: a candle where the high is
below the low describes something that cannot physically happen, so the
code won't let it exist, rather than silently storing garbage.

## Common mistakes
- Thinking a 5-minute candle is "live" the instant the 5 minutes starts — it
  isn't usable until the full window has passed.
- Keeping raw ticks forever "just in case." We keep them for a few days only
  (for debugging a specific problem), then delete them — the candles are
  the permanent record.
- Mixing up a stock's local time (IST for NSE) with UTC. The system stores
  everything in UTC internally and only converts to IST for what you
  actually read on a screen — this avoids a whole category of bugs around
  daylight saving and "which midnight did you mean."

## Check yourself
1. Why can't a strategy use a candle before its time window has fully closed?
2. If you kept every tick forever instead of candles, what would you be
   trading off (think: storage, and whether it actually changes what a
   strategy decides)?
3. A candle has `high=100, low=105` — why does the system reject this
   instead of just storing it?

## Words used in this lesson
- **Tick:** one individual trade (price, size, time).
- **Candle / bar:** a time window's open, high, low, close, and volume.
- **Closed bar:** a candle whose time window has fully finished — the only
  kind a strategy is allowed to look at.
- **UTC:** Coordinated Universal Time — the one time zone the system uses
  internally so "what time is it" never depends on where you are.
