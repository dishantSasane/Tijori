# Learning from open-source trading projects for Tijori

## Problem statement

How might Tijori learn from open-source trading research and automation projects
without confusing sophisticated tooling, attractive backtests, or social-media
claims with evidence of a durable trading edge?

## Recommended direction

Treat these repositories as a research and engineering reading list. First
classify what each project actually contributes: market-data access, backtest
engine, strategy examples, predictive model, agent workflow, or execution
adapter. Reuse ideas and well-tested components only after checking their
license, maintenance, dependencies, market assumptions, and fit with Tijori's
contracts. Keep P1 historical research on Upstox and keep P3's live provider
undecided.

For strategy discovery, describe hypotheses in plain language, make them
deterministic and versioned, then run them through Tijori's existing candle,
fill, cost, and reference-backtester path. AI may help propose hypotheses,
features, tests, or explanations. It must not be treated as evidence of edge,
set prices or limits, or enter the order path. Every candidate and attempted
variant must be recorded to reduce selection bias.

## What these projects may offer

| Project | Likely useful contribution | What it does not prove | Relevance to Tijori |
|---|---|---|---|
| [Kronos](https://github.com/shiyu-coder/Kronos) | Research reference for pretrained financial-candle sequence models and tokenization | A model forecast is not a profitable strategy; cross-exchange training does not establish NSE performance | Low near-term. Could inform a later forecasting experiment after a simple baseline and clean India dataset exist |
| [TradingAgents](https://github.com/TauricResearch/TradingAgents) | Example of role-based LLM research and debate orchestration | Multiple agents agreeing is not independent market evidence and does not prove returns | Some workflow inspiration for offline research briefs; not a P1 signal generator or execution design |
| [day-trader-skill](https://github.com/Jakeschincariol/day-trader-skill) | Human-facing research/checklist and journaling workflow examples | A Claude skill or chart scan is not validated alpha; inspect any order/broker integration carefully | Potential later learning-interface ideas; built around different markets and assumptions |
| [Vibe-Trading](https://github.com/ooandychen/vibe-trading) | Natural-language interface that turns ideas into runnable research and reports | Generated code can be wrong, leak future data, or silently change the tested rule | Useful product/workflow inspiration, only if generated rules are frozen, reviewed, and replayed deterministically |
| [Awesome Systematic Trading](https://github.com/wangzhe3224/awesome-systematic-trading) | Directory for discovering libraries, books, and research resources | A curated list is not a quality or profitability guarantee | Useful as a map; evaluate each dependency individually |
| [Claude Trading Skills](https://github.com/tradermonty/claude-trading-skills) | Examples of structured research, checklists, and trader workflows | Prompt instructions do not validate forecasts or provide a trading edge | Possible later research-assistant UX inspiration; keep LLM advisory |
| [Freqtrade](https://github.com/freqtrade/freqtrade) | Mature crypto bot, strategy backtesting, optimization, and exchange-operation patterns | Crypto results and exchange execution do not transfer to NSE equities | Engineering reference for later crypto sleeve only; not a P1 dependency |
| [CCXT](https://github.com/ccxt/ccxt) | Unified crypto exchange API interface | It is not a strategy engine and does not provide a unified equity-data solution | Later crypto adapter reference; out of P1 scope |
| [trading-ig](https://github.com/ig-python/trading-ig) | Python wrapper for IG Markets APIs | It is not relevant to Upstox historical NSE research | No P1 use; do not add the dependency |

Repository names and descriptions above were checked against the linked public
repositories or project documentation on 2026-11-15. Links can change; recheck
license, maintenance, and behavior before adopting anything.

## A useful research loop

1. Write a falsifiable market hypothesis before coding. Example: “After a
   market-wide selloff, stocks that fall less than their sector peers recover
   differently from stocks with company-specific weakness.”
2. Specify exactly what is known at decision time, the entry time, exit rule,
   sizing, cost model, and benchmark.
3. Build a small feature set from available candles. Start with understandable
   quantities such as market return, stock return relative to the index,
   volatility, range, and volume surprise.
4. Compare simple baselines first: cash/no-trade, buy-and-hold, T1, T4, and one
   small conditional rule. Add a predictive model only if it beats these under
   the same splits and costs.
5. Rank by risk-adjusted net results, uncertainty, drawdown, capital usage,
   turnover, and consistency across instruments and time windows. Do not rank
   by win rate or raw rupee P&L alone.
6. Freeze the shortlist and evaluate on later untouched dates. Record every
   experiment, including failures, so the “winner” is not merely the best of
   many attempts.

## Candidate original hypothesis to investigate

**Market-relative recovery after an abnormal decline:** estimate whether a
stock's short-term move relative to the Nifty 50, combined with market
volatility and volume surprise, predicts its forward return over a fixed
horizon. The rule may go long, stay flat, or reject the setup when expected net
return is too uncertain. This combines relative strength and conditional
mean-reversion ideas, but it is only a hypothesis. The sign, horizon, and
features must be selected on development data and confirmed later; do not assume
that a decline will bounce.

## Key assumptions to validate

- [ ] The Upstox history and price-adjustment treatment are suitable for the
      tested instruments and horizon.
- [ ] Point-in-time universe membership is available before claiming a
      survivorship-aware Tier A result.
- [ ] Costs and fills approximate the intended India equity product, order
      size, and holding period.
- [ ] Any detected relationship persists across later periods and multiple
      instruments after accounting for repeated experiments.
- [ ] Any external project is compatible with the repo license and security
      constraints before code or data is reused.

## MVP scope

- Read and classify the listed repositories; do not install or integrate them
  as a bundle.
- Select at most one engineering reference for each concrete gap.
- Define a small, pre-registered family of candidate hypotheses and one
  untouched chronological holdout.
- Keep P1 data sourced from Upstox only. Keep live data provider undecided.
- Keep all strategy evaluation offline and paper-only.

## Not doing

- Treating stars, social-media popularity, AI labels, or a claimed win rate as
  evidence of profitability.
- Running an unrestricted parameter sweep and reporting only its winner.
- Importing a crypto exchange connector or IG/CFD adapter into the India P1
  path.
- Allowing an LLM to place orders, set prices, bypass risk checks, or make
  unreviewed code changes to a frozen strategy.
- Claiming a new strategy is profitable before untouched validation and paper
  evidence.

## Claude review prompt

Review this idea against the current Tijori repository, `AGENTS.md`, P1
protocols, strategy specs, and data-source constraints. Do not modify code.
For every listed project, verify its actual purpose, license, current
maintenance, dependencies, and whether it provides a component we truly lack.
Correct any inaccurate project descriptions. Then challenge the proposed
research loop for leakage, multiple testing, survivorship, corporate actions,
cost assumptions, and sample dependence. Recommend a small, mathematically
defensible candidate library and chronological evaluation plan that fits the
available Upstox daily data. Treat all strategy ideas as hypotheses. Return
findings, risks, and a revised recommendation in plain English; do not claim
profitability from a repository's popularity or authors' backtest screenshots.

## Open questions

- Does the owner want the first discovery target to be daily swing trading or
  another holding horizon? The currently collected P1 data is daily.
- Which authorized point-in-time Nifty 50 + Next 50 membership source will be
  used before calling the universe complete?
- Which explicit capital and per-trade risk assumptions should candidate
  strategies use for fair comparison?

