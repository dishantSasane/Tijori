# 04 — Market profiles, and why crypto breaks a "market hours" assumption

## What this is
A **market profile** is a small settings sheet, one per market (India
stocks, US stocks, crypto, ...), that says: when is this market open, what
timezone is it in, what does a trade cost here, and a few other knobs that
differ market to market. The code reads this sheet instead of having
`if market == "crypto"` checks sprinkled everywhere.

## Why it exists
India's stock exchange (NSE) is open 09:15-15:30 IST, Monday to Friday, with
holidays. Code that schedules "fetch the candle, check for a signal, maybe
place an order" can safely assume: there's a clock, and outside market hours
nothing happens. That assumption was built into this repo's candle
scheduler (`src/trading/candles/scheduler.py`) for good reason — it's the
first market we're building for.

Crypto doesn't have that. Bitcoin trades every second of every day, every
day of the year. There is no "market closed" state, no holiday, no 3:30pm
cutoff. If you plug crypto into a scheduler built around exchange sessions,
it will either never run (waiting for a "market open" event that never
fires) or run with a session-close assumption that's simply wrong (there's
no close to adjust for).

The market profile is how the code tells the difference without a special
case buried in business logic: `MarketProfile.is_24x7` is `True` for crypto
and `False` for India/US equities. Anything that currently assumes a
session (the scheduler, square-off logic) can check this flag and know not
to apply itself.

## Tiny example
```python
from pathlib import Path
from trading.core.enums import MarketId
from trading.core.market_profile import load_market_profile

crypto = load_market_profile(MarketId.CRYPTO, Path("config"))
print(crypto.is_24x7)  # True
print(crypto.session_open)  # None -- there isn't one

us = load_market_profile(MarketId.US_EQUITY, Path("config"))
print(us.is_24x7)  # False
print(us.calendar)  # "XNYS" -- an exchange-calendar id
```

## How to run it in this repo
```bash
python3 -m pytest tests/core/test_market_profile.py -v
```
Edit `config/markets.yaml` (copy from `config/markets.example.yaml` first)
to change a market's session, timezone, or costs — nothing in code needs to
change for that.

## Common mistakes
- Assuming "daily candle" means the same thing everywhere. For India/US it
  means "the exchange's closing bar." For crypto there's no exchange close,
  so the team picked an arbitrary but fixed cutoff (00:00 UTC) instead —
  see `config/markets.yaml`'s `daily_cutoff_utc`. Pick one and never let it
  silently drift, or your backtest and live system will disagree on what a
  "day" is.
- Writing a new strategy's math per market. The point of a market profile
  is that the *signal rule* (e.g. "breakout over the last 20 highs") stays
  identical everywhere; only the *configuration* (which symbols, which
  timeframe, what session to respect) changes per market. See
  `src/trading/strategies/instances.py` for how crypto/US reuse the same T1
  rule written for India.

## Check yourself
1. Why can't the India-equity candle scheduler be reused unmodified for crypto?
2. What field on `MarketProfile` tells you a market never closes?
3. If you wanted to add a Japan equities sleeve tomorrow, what two things
   would you add (and what would you *not* need to touch)?

## Words used in this lesson
- **market profile**: a per-market settings object (hours, timezone, costs) the rest of the code reads instead of hardcoding market-specific branches.
- **exchange calendar**: a library-provided table of a specific exchange's open days, holidays, and session times (e.g. `XNYS` for the NYSE/Nasdaq).
- **session**: the window during which a market is open for trading (e.g. 09:15-15:30 IST for NSE). Crypto has no session.
- **sleeve**: this repo's word for one market's slice of the portfolio (India equity, crypto, US equity, ...), each with its own capital allocation and risk limits.
