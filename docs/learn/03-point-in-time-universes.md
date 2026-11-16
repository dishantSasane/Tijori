# 03 — Point-in-time stock universes

## What this is

A research universe is the set of stocks a strategy is allowed to consider at
each date. A point-in-time universe rebuilds that set using only information
that was available then. Tijori's proposed rule ranks NSE cash equities each
month by the median of their previous 60 sessions' traded value.

## Why it exists

Testing today's largest companies over old dates quietly removes companies
that later shrank or disappeared. That is survivorship bias. Ranking at each
historical month avoids that particular shortcut, provided the dated source
also covers securities that later delisted. A formula alone cannot repair an
incomplete or unauthorized dataset.

## Tiny example

Suppose an eligible stock's 60 daily traded values are sorted. The median is
the average of values 30 and 31. If those are ₹8 crore and ₹10 crore, its score
is ₹9 crore. Sort stocks by that score from high to low; break exact ties by
ISIN so the result is repeatable. A stock with only 59 verified sessions is
excluded, not given invented zeros.

## How to run it in this repo

The selector accepts normalized synthetic records and produces a reproducible
snapshot:

```bash
.venv/bin/python -m pytest tests/storage/test_research_universe.py -q
```

The module does not fetch source files. Real NSE collection and backtest use
remain gated on documented rights, schema, and historical coverage.

## Common mistakes

- Treating a public download link as permission for automated collection or
  simulation.
- Treating a missing row as zero turnover. A zero needs explicit evidence.
- Assuming a historical ranking is survivorship-free without later-delisted
  securities in the dated source.
- Using today's ticker as identity. Symbols can change; use verified ISINs.
- Including this month's or future observations in a snapshot effective at
  the start of the month.

## Check yourself

1. Why can a missing observation not safely be replaced by zero?
2. Which 60 observations determine a snapshot effective on the first session
   of a month?
3. What additional evidence is needed before calling the result
   survivorship-free?

## Words used in this lesson

- **Universe**: securities a strategy may consider.
- **Point-in-time**: using only data available by the historical decision date.
- **Median**: the middle value after sorting; for an even count, the mean of
  the two middle values.
- **Survivorship bias**: distortion caused by retaining only entities that
  survived until the present.
