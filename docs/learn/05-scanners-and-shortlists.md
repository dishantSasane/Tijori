# 05 — Scanners, shortlists, and why their backtest is different

## What this is
A **scanner** is a program that looks at every stock in a list ("the
universe") once a day and asks "does this one pass some simple rules?" The
ones that pass become a **shortlist** — a short, ranked list of ideas worth
a human's attention. Nothing here buys or sells anything; it is a sorting
step before a strategy or a human decides to act.

## Why it exists
You can't watch 100+ stocks by hand every day. The scanner does the
mechanical filtering (is this stock traded enough to actually buy/sell
without moving the price? is its data fresh?) and the mechanical ranking
(which of the survivors look most interesting right now?), so you only
spend attention on a handful of names instead of all of them.

## Tiny example
Say the universe is `{INFY, TCS, PENNYSTOCK}`.
- `PENNYSTOCK` trades Rs 2 lakh/day on average → fails the **liquidity
  filter** (too thin — you might not be able to sell it when you want to).
- `INFY`'s last candle is from three weeks ago → fails the **data-quality
  filter** (stale data; AGENTS.md's "fail closed" rule says: when in doubt,
  leave it out).
- `TCS` passes both, and its close is above its own 20-day average → it
  gets a `rank_score > 0` and lands on the shortlist, with a rough
  **target** (+8%) and **reconsider level** (-5%, "if it drops this far,
  re-check whether the idea still makes sense" — not a stop-loss order,
  just a flag for a human).

The next day, if `TCS` no longer passes, it's marked `removed` in the
shortlist table (not deleted — so you can look back and ask "how long did
that idea stay on the list?").

## How a scanner backtest differs from a strategy backtest
`src/trading/backtest/` already answers "if I had traded every signal from
a strategy, what would my P&L have been, with real fees and slippage?"

The scanner backtest (`src/trading/scanner/backtest.py`) answers a smaller,
cheaper question: "on each day the scanner would have shortlisted this
stock, what happened to its price N days later?" There's no simulated
order, no fees, no position sizing — just "did the price go up or down."
This is a sanity check on the *filtering and ranking logic*, not a claim
about trading profit. If the scanner has a 70% "hit rate" in this backtest,
that does **not** mean a strategy trading it would make money after real
costs — it only means the shortlist tends to point at stocks that went up.

Just like a real strategy backtest, this must not look into the future to
make its decision: on day T, the filters only see candles from before day
T. The *measurement* of the outcome is the one place we deliberately look
forward (that's what "forward outcome" means) — but the decision itself
never does.

## How to run it in this repo
```bash
pytest tests/scanner -q          # unit tests for filters, scanner, backtest, shortlist
mypy src/trading/scanner         # type-check
streamlit run dashboard/Home.py  # see the Stocks page (needs TIJORI_STATE_DB set)
```

## Common mistakes
- Treating the scanner backtest's "hit rate" as a trading edge — it isn't;
  it has no costs, slippage, or position sizing in it.
- Confusing shortlist "promotion" (a symbol joining today's scan results)
  with **strategy-version promotion** (`docs/STRATEGIES.md` §6/§8, a
  completely different process for approving a new strategy version for
  live trading). They share a word, not a mechanism.
- Letting the filter window include the as-of day itself — that's a
  look-ahead bug. The filters in this phase always use `< as_of`, never `<=`.

## Check yourself
1. Why does the data-quality filter reject a stock whose last candle is
   three weeks old, even if its 20-day average volume looks fine?
2. If the scanner's forward-outcome backtest shows a 65% hit rate, is that
   evidence you should trade every shortlisted idea automatically? Why not?
3. A symbol is `active` on the shortlist Monday and `removed` Tuesday. Did
   anything get deleted from the database? What is still there, and why
   does that matter for debugging later?

## Words used in this lesson
- **universe**: the full list of symbols the scanner is allowed to look at.
- **shortlist**: the subset of the universe that passed today's filters,
  ranked best first.
- **liquidity filter**: rejects a stock that doesn't trade enough money per
  day to safely buy or sell without moving its price.
- **reconsider level**: a rough price level where the original idea looks
  wrong and a human should re-check it — not an automatic stop-loss order.
- **forward outcome**: what happened to a price some fixed number of days
  *after* a decision was made, used only to measure, never to decide.
