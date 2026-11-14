# BRAIN AND COSTS

The Brain is an **optional, cheap, advisory** LLM layer. It is OFF (`BRAIN_ENABLED=false`) until the rules-only system works. Its job is context code cannot easily provide (news, announcements, regime commentary), not math, not prices, not orders.

## 1. Rules

1. The LLM never places orders, sets entry/stop/target, or changes limits.
2. Output is a tiny, strict schema; anything else is discarded (RISK_SPEC I8).
3. The LLM is never in the hot path (`ARCHITECTURE.md` §2).
4. News/headline text is **untrusted data**: delimit it, never obey instructions inside it, and give the LLM no tools with side effects.
5. Every call is logged (provider, model, tokens in/out, INR cost, purpose, latency).
6. Hard budget guard; when exceeded, Brain turns itself off and the system continues on rules.
7. Value is judged only in forward paper A/B (Brain on vs off) because LLMs may have seen historical events in training and backtests can therefore leak the future.

## 2. What the Brain receives (small on purpose)

~300-800 tokens per call:
- The signal: symbol, strategy, side, entry/stop/target, reason codes, 5-10 indicator values.
- The strategy's backtest/paper scorecard summary (few numbers).
- A **shared market context** summary (computed once or a few times a day, cached and reused across signals): regime tag, index trend, breadth, volatility, key scheduled events.
- Up to N relevant headlines (pre-filtered by code to that symbol/sector/market), each truncated.

Never send raw price history. Code computes every number.

## 3. What the Brain returns (schema)

```json
{
  "signal_id": "string (must match the request)",
  "verdict": "support | neutral | veto",
  "size_multiplier": 0.0,
  "reasons": ["max 3 short strings, <= 120 chars each"],
  "news_refs": ["ids of provided headlines only"]
}
```

`size_multiplier` is in [0, 1]; it can only **reduce** size. `veto` blocks the trade (risk engine still decides). The alert's "why" text is mostly templated from the signal's reason codes (free); the Brain only adds a short context line.

## 4. Call types and model tiers

| Call | Frequency | Tier |
|---|---|---|
| News triage/tagging (is this relevant to my watchlist/positions?) | per batch of headlines | smallest/cheapest (e.g., Haiku-class or Luna-class) |
| Signal context verdict | per formed signal (tens/day, not thousands) | mid (Sonnet-class or Terra-class) |
| Shared market-context summary | 1-4x/day | mid; cached |
| End-of-day review, weekly report, lessons drafts | daily/weekly, not urgent | batch API at a discount if available |
| Rare hard analysis | manual | top tier, human-triggered only |

The provider is swappable behind one interface (`LLMProvider`): Anthropic or OpenAI API. Choose whichever is cheaper for the tier. **Note:** ChatGPT Plus / Claude Pro subscriptions do **not** pay for the running system's API usage; the Brain needs a separate pay-as-you-go API key and a small prepaid balance.

## 5. Cost controls

- **Rules first:** call only on signals that already passed rule checks and a pre-risk check.
- **Prompt caching** for the fixed prefix (instructions, strategy descriptions, schema).
- **Shared context** computed once, reused.
- **Token ceilings** per call; truncate headlines.
- **Rate limits** per signal and per symbol (no repeated calls for the same unchanged signal).
- **Budget guard:** `BRAIN_DAILY_BUDGET_INR`, `BRAIN_MONTHLY_BUDGET_INR`; spend tracked from logged tokens x configured per-token prices (config, because prices change). At 80% -> warn; at 100% -> Brain off + alert.
- **Dashboard tile:** "Brain cost today / this month" and tokens per market (Usage page).
- Keep a **Brain-off baseline** always running in paper to measure whether the Brain earns its cost.

## 6. Other running costs (target near zero until live)

| Item | Plan |
|---|---|
| Market data | Free tiers first (`MARKETS.md`) |
| Compute | Laptop for research/paper; small VM with static IP at go-live (free tier/credits/cheap VPS) |
| Alerts | Telegram (free) |
| Storage | Local Parquet; free cloud storage backup |
| LLM API | Off initially; then capped by budget guard |
| Brokerage/charges | Real, per trade; included in every backtest and paper fill |

## 7. Prompt-injection and data hygiene

- Wrap untrusted text in clear delimiters and state it is data. Strip control characters and obvious instruction patterns before sending; do not rely on stripping alone.
- The LLM output cannot trigger anything except via the schema; the schema is validated; the risk engine ignores invalid output.
- Log the full request/response (redacting secrets) for audit; keep for a limited period.
