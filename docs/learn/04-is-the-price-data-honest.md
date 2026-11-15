# 04 — Is the price data honest? (raw vs. adjusted, and how to check)

## What this is
When a company does a stock split or gives out free "bonus" shares, its
share price drops overnight to match — a 1-for-1 bonus roughly halves the
price, even though nothing about the company changed. Historical price data
either shows that overnight drop (**raw**) or has already been corrected for
it (**adjusted**). If you don't know which one you have, a backtest can
mistake "the company gave out bonus shares" for "the stock crashed 50% in a
day" and draw a completely wrong conclusion from it.

## Why it exists
This isn't a hypothetical: it already happened once in this project. An
early check of NESTLEIND's 10:1 stock split (handoff note 0031) found that
Upstox's price history was *already* adjusted — treating it as raw and
applying a second adjustment would have corrupted the numbers. Before using
any new data source for real analysis, you have to find out which kind of
price it's giving you, the same way, every time.

## Tiny example
TCS did a real 1-for-1 bonus issue, record date 2 June 2018. If the data is
**raw**, the closing price should roughly halve overnight around that date.
Here's what Upstox's daily data actually shows for TCS across that date:

| Date | Close (₹) |
|---|---:|
| 2018-05-28 | 1751.03 |
| 2018-05-31 | 1741.05 |
| 2018-06-01 | 1732.45 |
| 2018-06-04 | 1744.25 |

No halving anywhere. The price is continuous. That's the signature of
**provider-adjusted** data — Upstox already corrected it, so you don't
have to (and must not apply a second correction, or you'd double-adjust it).

## How to run it in this repo
```bash
# Scan a symbol's full daily history for suspicious overnight price jumps
# (the same check, generalized, as src/trading/storage/p1_pilot_coverage.py
# and the manual TCS/NESTLEIND checks above).
PYTHONPATH=src .venv/bin/python -m pytest tests/storage/test_p1_pilot_coverage.py -q
```
The real finding for the five P1 pilot symbols is written up in full in
`docs/specs/P1A_PILOT_DATASET_MANIFEST.md` §5.

## Common mistakes
- Assuming every source from the same broker behaves the same way. Always
  verify per symbol, per action — one confirmed case (NESTLEIND, or TCS
  here) tells you about *that* case, not every other stock or every other
  provider.
- Treating "no big price jump found" as proof nothing happened. It's only
  proof once you've checked it against a day you *know* a real action
  occurred (like TCS's 2018 bonus here) — otherwise "no jump" could just
  mean "no action happened in this window," which is a weaker and different
  claim.
- Mixing up a real crash with a corporate action. A ~20% overnight drop
  from bad news (a results miss, a scandal) looks similar to an unadjusted
  split at first glance. Check the specific date against public news before
  concluding either way — three such drops were found and ruled out this
  way while building this check (Infosys's 2013 results crash, Infosys's
  2019 whistleblower crash, and the March 2020 COVID market crash).
- Confusing price adjustment with volume adjustment. They're adjusted
  independently by a provider and must be checked separately — confirming
  price is adjusted says nothing about whether volume is too.

## Check yourself
1. If a stock does a 2-for-1 split and the raw closing price was ₹1,000 the
   day before, what price would you expect the *raw* data to show the day
   after (ignoring any real price movement)? What would *adjusted* data
   show instead?
2. Why doesn't "the price didn't jump around this specific date" alone
   prove the data is adjusted — what extra fact makes it proof instead of
   a coincidence?
3. If you found a huge overnight price jump with no known corporate action
   on that date, what would you check before assuming it was a split?

## Words used in this lesson
- **raw price data**: history exactly as traded, with the overnight drop
  from a split/bonus still visible.
- **adjusted (provider-adjusted) price data**: history where the provider
  has already mathematically corrected for every split/bonus, so the price
  series looks continuous through the event.
- **bonus issue**: free extra shares given to existing shareholders (e.g.
  "1-for-1" doubles your share count); economically similar to a split.
