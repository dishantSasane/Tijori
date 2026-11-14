# 03 — Why backtests lie: costs, slippage, overfitting, survivorship, look-ahead

## What this is
A backtest number is always better than what you would have actually gotten
live, unless you specifically design it not to be. This lesson is the list
of the ways a backtest quietly flatters itself, and what this project does
about each one.

## Why it exists
Every one of these traps has the same shape: something subtly lets the
backtest "know" more than a real trader, in real time, would have known. If
you don't close these gaps, you end up trusting a number that has no
relationship to what would actually happen with your money.

## The traps, one at a time

**1. Look-ahead.** The backtest accidentally uses information from the
future — e.g. deciding to buy at a day's close using that same day's high,
which you couldn't know yet when the day started. **Fix used here:** a
signal only ever reads *closed* bars, and it fills on the *next* bar's open,
never its own bar's close (lesson 02). This is tested directly — the system
re-runs every strategy on a truncated version of history and checks the
earlier signals come out identical, which would catch a hidden leak.

**2. Costs and slippage.** Real trading has brokerage fees, and your actual
fill price is usually a little worse than the price you saw on screen
(other people are trading too, and prices move between "I decided" and "my
order executed"). A backtest that ignores both will always look better than
reality. **Fix used here:** every fill in the backtester includes a
brokerage fee and a slippage adjustment that always makes the fill price a
little worse for you, never better, by default.

**3. Overfitting.** If you try enough parameter combinations (RSI below 8?
9? 10? 11?...) on the same data, *something* will look great by chance alone
— that doesn't mean it will keep working. **Fix used here:** every tweak
made after seeing results counts against the strategy (`docs/STRATEGIES.md`
§6); a strategy must survive a ±10% change to each of its parameters without
falling apart (a real edge shouldn't depend on one exact magic number); and
final testing happens on a hold-out period the strategy was never tuned on.

**4. Survivorship bias.** If your historical stock list only includes
companies that are *still listed today*, you've silently deleted every
company that went bankrupt or got delisted — which makes the past look
artificially rosy, since you've excluded all the losers. **Fix used here:**
history must include delisted stocks, and the India NSE Tier-B universe is
built from the actual historical membership, not today's Nifty 50 list
(this is explicitly flagged in the project's specs as something to prove
before trusting any whole-market scorecard, not assumed).

**5. "It worked once, in one market regime."** A trend-following rule looks
brilliant during a strong trend and terrible when prices just chop
sideways — and vice versa for a mean-reversion rule. **Fix used here:**
strategies are tested across different regimes (trending/sideways/volatile),
and the project deliberately pairs opposite-style strategies
(`docs/STRATEGIES.md` §5) so the whole system isn't betting on only one kind
of market showing up.

## Tiny example
Two versions of "the same" backtest for one trade: enter at ₹2,500.

| | No-cost version | Realistic version |
|---|---|---|
| Fill price | 2500.00 | 2501.25 (0.05% slippage, against you) |
| Exit price | 2580.00 | 2578.70 |
| Gross P&L | +80.00 | +77.45 |
| Brokerage (both sides) | 0 | -40 |
| **Net P&L** | **+80.00** | **+37.45** |

Same trade, less than half the profit once costs and slippage are counted
honestly. Over hundreds of trades this difference is the entire gap between
"looks like a great strategy on paper" and "actually works."

## How to run it in this repo
Not runnable yet — the backtester is a later build phase. The exact numeric
rule for slippage/costs is in `docs/specs/TEST_SPEC_BACKTEST.md` §1 once that
spec lands; the look-ahead test rule is in `docs/specs/TEST_SPEC_CANDLES.md`
§3.

## Common mistakes
- Comparing a strategy's backtest return to a friend's or a forum post's
  without checking whether *their* backtest included costs and slippage —
  it's an apples-to-oranges comparison if one did and the other didn't.
- Treating "it survived out-of-sample" as proof instead of "slightly less
  weak evidence." The next step after a good backtest is paper trading for
  real, in real time, with real (if simulated) money — not going live.

## Check yourself
1. Why does entering at a bar's own close (instead of the next bar's open)
   quietly cheat?
2. If a historical stock universe only includes companies still trading
   today, what kind of companies has it silently excluded, and why does
   that matter?
3. You backtest a rule with 15 parameters and it has a beautiful equity
   curve. Should you trust it more or less than a rule with 2 parameters and
   a similar curve? Why?

## Words used in this lesson
- **Look-ahead bias:** a backtest accidentally using future information it
  wouldn't have had in real time.
- **Slippage:** the gap between the price you see and the price you actually
  get filled at.
- **Overfitting:** tuning a rule so closely to one dataset that it stops
  working on new data.
- **Survivorship bias:** a historical dataset that's missing the things that
  failed or got delisted, making the past look better than it was.
- **Out-of-sample:** data the strategy's parameters were never tuned on,
  used only to check if the edge is real.
