# Lessons for the owner

You are learning trading systems while they are built. Every milestone produces one short lesson here, written for a smart beginner. Use `TEMPLATE.md`.

## Planned lessons (create them as the milestones land; the P0 sprint writes 00-03)

| # | Lesson | Written during |
|---|---|---|
| 00 | How the whole system works (one page) | P0 |
| 01 | Candles, ticks, and why we summarise | P0 |
| 02 | What is a backtest, and how to read one (return, drawdown, win rate, profit factor) | P0 / P1 |
| 03 | Why backtests lie: costs, slippage, overfitting, survivorship, look-ahead | P0 / P1 |
| 04a | Strategies and the first honest scorecard | P1 |
| 04 | Stop-loss, position sizing, and risk per trade | P2 |
| 05 | The risk engine and the kill switch (why it can say no to everything) | P2 |
| 06 | Paper trading and auto-paper shadow: learning from trades you did not take | P2-P3 |
| 07 | Trend following vs mean reversion (and why we run both) | P3 |
| 08 | Out-of-sample and walk-forward testing | P3 |
| 09 | How we cover thousands of stocks: the daily scanner and Tier A/B | P4 |
| 10 | Crypto and US markets: what is different | P5 |
| 11 | How and why the LLM "Brain" is kept cheap, small, and advisory | P6 |
| 12 | Static IPs, SEBI rules, and going live safely | P7 |
| 13 | Options: why they are last | P8 |

## Style rules for lesson writers

- Plain language; define every term the first time (use the glossary in lesson 00 as it grows).
- One small example with numbers beats a paragraph of theory.
- Always include: "What this is", "Why it exists", "Tiny example", "How to run it in this repo", "Common mistakes", "Check yourself" (3 questions).
- Be honest about uncertainty: results are hypotheses until proven.
- Keep it under ~2 pages.
