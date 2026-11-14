# MASTER PLAN

Version 1.0 · written 2026-11-14 from the owner's planning conversation · owner: Dishant

This is the one-page-ish truth of what we are building and why. Details live in the linked docs. If you change a decision here, record it in `decisions.md`.

## 1. Goal

Build a **diversified, multi-market trading system** the owner can trust and learn from:

- Markets: Indian stocks (NSE), US stocks/ETFs, crypto, MCX commodities, NSE currencies; later Nifty/BankNifty options and a small, capped memecoin sleeve.
- It **watches** markets, **finds** setups with tested strategies, **explains** every alert (what, why, entry, target, stop-loss), **paper-trades** to prove ideas, and only later **trades live**, with human approval first.
- It is also a **teaching project**: the owner is a trading beginner who is strong in Python. Every milestone produces a plain-language lesson.

Non-goals: HFT, handling other people's money, selling signals, guaranteed returns.

## 2. Constraints that shape everything

| Constraint | Consequence |
|---|---|
| Student, low budget | Free-first stack (`MARKETS.md`); start on a laptop; cheap cloud later |
| Beginner in trading | Paper by default; approval before auto; lessons per milestone |
| AI tooling: Claude Pro (ends ~2026-11-16) and ChatGPT Plus (ongoing) | Claude front-loads specs/contracts/tests; Codex models (Sol/Terra/Luna, Astra sparingly) implement after. See `MODEL_ROLES.md` |
| India SEBI retail algo rules (mandatory since 2026-04-01) | Static-IP-bound order APIs, order IDs, 2FA. Real orders must come from a fixed IP, i.e. a small cloud VM. Data + paper can run on a laptop. See `COMPLIANCE_INDIA.md` |
| Backtests overstate live results | Costs, slippage, out-of-sample, walk-forward, survivorship-free data, simplicity. See `STRATEGIES.md`, `TESTING.md` |
| LLM calls cost money and can leak the future in backtests | Brain is advisory, cheap, capped, and judged only in forward paper trading. See `BRAIN_AND_COSTS.md` |

## 3. Principles

1. **Paper first, small live later.** Backtest -> out-of-sample -> paper -> tiny live (approval) -> scale slowly.
2. **Fail closed.** Unknown or inconsistent = stop opening positions and alert.
3. **Code decides, Claude/GPT contextualises.** Rules produce signals; the LLM reads a short summary and may support, veto, or shrink; the risk engine has the last word.
4. **One code path** for backtest, paper, and live (same candles, same indicators, same signal code; only the broker adapter differs).
5. **Summarise, don't hoard.** Ticks -> candles -> indicators. Keep candles forever; keep raw ticks only a few days.
6. **Per-market profiles, shared templates.** A strategy *instance* = template + market profile; each has its own tests, version, and status. Nothing transfers between markets without re-proving.
7. **Author != reviewer.** Cross-model review; tests written blind from specs.
8. **Teach as you build.**

## 4. The system in one picture

```
 Market data (live + daily files)
        |
   [Eyes]        data adapters per market -> candles (closed bars)
        |
   [Calculator]  incremental indicators + strategies -> Signals (entry/target/stop, reason codes)
        |                          ^
        |                          | daily scanner (Tier B, whole market from bhavcopy etc.)
   [Brain]       OPTIONAL, cheap LLM: support / neutral / veto / size multiplier (schema-validated)
        |
   [Hands]       Risk engine (can veto anything) -> mode gate -> Paper broker OR real broker adapter
        |
   [Voice]       Telegram alerts + dashboard (Approve / Paper test / Reject), ledgers, news, usage page
```

Detail: `ARCHITECTURE.md`.

## 5. Markets and sleeves

Each market is a **sleeve** with its own budget cap, risk limits, hours, costs, universe, and strategy instances. Starting allocations are illustrative (`config/risk.example.yaml`); the owner decides. Per-market table: `MARKETS.md`.

**Two tiers per stock market:**

- **Tier A (live core, ~100 names):** streamed during market hours; intraday + swing strategies.
- **Tier B (whole market):** one daily file per market (NSE bhavcopy for India; daily bars for US; bulk candles for crypto). A daily scanner computes weekly/monthly performance and trend, applies liquidity filters (penny stocks configurable, not a separate feature), and produces a **shortlist** of ~20-50. Shortlisted names are promoted to live watch for the day; stale Tier A names can be demoted.

## 6. Modes

Per sleeve: `paper` -> `approval` -> `auto`. Each alert has **Approve** (live, only if sleeve mode allows), **Paper test**, **Reject**. `auto_paper_shadow` (setting) silently paper-trades every signal and tracks outcomes of rejected ones, so each strategy gets a larger honest sample and the owner can see whether rejections were wise. Alerts show historical stats of similar signals (win rate over many), not single anecdotes.

## 7. Data policy

- Keep downloaded raw candles/files (they are small: years of 1-min candles for ~100 stocks is hundreds of MB as Parquet; daily is tiny). Delete only regenerable derived files.
- Rolling raw tick buffer (default 3 days) for debugging, then delete.
- History must include **delisted** instruments; adjust daily history for splits/bonuses via corporate-actions data.
- Candles stored in Parquet, queried with DuckDB; state in SQLite. Backups to free cloud storage.

## 8. Strategy lifecycle (summary)

Idea -> written hypothesis -> coded rules -> in-sample backtest (costs included) -> out-of-sample + walk-forward -> robustness (parameter perturbation, regimes) -> paper (weeks) -> tiny live in approval -> scale. Live versions are frozen; changes = new version; challenger runs in paper beside champion. Review cadence: daily monitoring, weekly review, monthly/quarterly scheduled retune/retrain, early review on triggers. Full text: `STRATEGIES.md`.

Phase-1 templates: Donchian breakout, MA trend + ADX, cross-sectional momentum, RSI(2) pullback, opening range breakout, Bollinger mean reversion, plus a candlestick confirmation filter. Later: VWAP, squeeze, volume-surge, funding-rate carry, pairs, options spreads, event/news, ML ranker.

## 9. The Brain (LLM)

Optional and OFF until the rules-only system runs well. Called only on already-formed signals with a ~500-token summary plus cached shared market context. Output schema is tiny (`support|neutral|veto`, size multiplier 0..1, reasons). Hard INR budget guard; fallback to rules-only. Evaluated only in forward A/B (Brain on vs off). `BRAIN_AND_COSTS.md`.

## 10. Where it runs

| Stage | Runs on | Why |
|---|---|---|
| Research, backtests, paper | Owner's laptop | Free; data/paper calls are not blocked by the static-IP rule |
| Live approval/auto (India) | Small cloud VM with **reserved static IP** registered with the order broker | SEBI/broker rule; 24/7 uptime for crypto |
| Dashboard | Streamlit (first), later optional static hosting | Keep it simple |

## 11. Roadmap (detail in `BUILD_ORDER.md`)

P0 Foundation sprint (Claude, time-boxed) -> P1 Data + backtester -> P2 Paper broker + risk engine + minimal alerts -> P3 India Tier A paper end-to-end + dashboard -> P4 Tier B scanner -> P5 Crypto + US sleeves (paper) -> P6 Brain + news -> P7 Go-live readiness (VM, static IP, audit, tiny live) -> P8 Expansion (commodities/currency, ML, options, memecoin).

## 12. Success criteria

- A beginner can open the dashboard and understand why each alert fired.
- Strategies in the registry have honest scorecards, with costs, out-of-sample results, and live-vs-backtest comparison.
- No path to a real order exists without the gates in `AGENTS.md` §4.
- Monthly running cost stays within what the owner sets (target: near zero until live, then small VM + API credits).

## 13. Open questions for the owner (do not guess; ask via handoff `needs-human`)

1. Starting capital per sleeve (paper and live).
2. Which broker for free Indian market data (Angel One SmartAPI, Fyers) vs paying for Kite Connect data (Rs 500/mo, verify).
3. Order broker for India (Zerodha Kite Connect Personal assumed) and US route (Alpaca paper first; LRS/IBKR later).
4. Crypto exchange choice and legal/tax approach.
5. Cloud VM provider (Oracle free tier / student credits / cheap VPS) and static IP plan.
6. Repo name and GitHub owner; CODEOWNERS for critical folders.
7. Final sleeve allocations and risk limits (`config/risk.example.yaml` values are proposals).
