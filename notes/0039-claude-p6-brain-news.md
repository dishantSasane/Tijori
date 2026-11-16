# 0039 — Claude: P6 Brain/News implemented (PR #59), needs cross-model review before merge

Status: needs-review (cross-model, mandatory per AGENTS.md §5), one needs-human item (budget/model pick)

## What shipped

Branch `claude/p6-brain-news`, PR #59 (https://github.com/dishantSasane/Tijori/pull/59)
against `main`. Implements `docs/BUILD_ORDER.md` P6 (News/LLM provider/budget
guard/schema validation/shared cache/Brain A/B in paper) against the P0
`NewsFeed`/`LLMProvider` Protocols and `BrainVerdict` contract that already
existed in `src/trading/adapters/` and `src/trading/core/models.py` — this
phase did **not** touch those Protocols or the risk engine's existing
Brain-verdict handling (`src/trading/risk/engine.py`/`sizing.py`), only added
the real implementations behind them, in a new `src/trading/brain/` package:

- `news_rss.py`: real `NewsFeed` — RSS 2.0 via stdlib `urllib`+`xml.etree`
  (no new dependency), skips a broken feed rather than raising.
- `budget_guard.py`: `BudgetGuard` sums today's/this-month's spend straight
  out of the existing `audit_log` table (no second ledger); `allow()` fails
  closed — refuses a new call outright at/over the cap, never makes the
  call and discards the result.
- `schema.py`: `parse_verdict` strictly parses raw LLM JSON into
  `BrainVerdict`; any mismatch (bad JSON, wrong `signal_id`, too many/too
  long `reasons`) returns `None`, which the risk engine already treats as
  "Brain absent" (neutral, full size).
- `prompt.py`: builds the Brain's context, explicitly delimiting headlines
  as untrusted data, capped to 8 headlines / 200 chars each
  (`docs/specs/RED_TEAM.md` scenario 4).
- `context_cache.py`: in-process, content-hash-keyed TTL cache, no
  persistence (ponytail/YAGNI per the task instructions).
- `anthropic_provider.py`: real `LLMProvider` against the Anthropic API;
  lazily imports `anthropic` (new optional `brain` extra in
  `pyproject.toml`) so nothing else needs it installed — tests use a fake
  module injected into `sys.modules`, never a real network call.
- `ab_harness.py`: runs one signal through `RiskEngine.check()` twice (real
  Brain verdict vs. forced neutral baseline) and logs both decisions under
  one `brain_ab_comparison` audit event. The off-arm needed its own
  throwaway `DecisionStore` (fresh `:memory:` connection) — reusing the real
  engine's `DecisionStore` for both arms trips check 14's duplicate-signal
  guard (I7) on the second call, since from that store's point of view it's
  the same `signal_id` delivered twice. Documented as ADR-0029 in
  `docs/decisions.md` along with the `news_refs`-field gap (in
  `docs/BRAIN_AND_COSTS.md`'s wire schema, not in the P0 `BrainVerdict`
  contract — popped before validation rather than widening a P0 core
  contract for a field nothing downstream reads).

Full suite: `pytest` (294 tests, all green, including new `tests/brain/`),
`ruff check .` and `ruff format --check .` clean, `mypy src` clean (the two
`anthropic`-import/`bytes`-return mypy complaints are resolved — see
`pyproject.toml`'s new `ignore_missing_imports` override for `anthropic.*`
and an explicit `bytes(...)` cast in `news_rss.py`).

## What's deferred, with reasons

- **No property/invariant tests for the budget guard.** Example-based tests
  cover the exact-cap boundary, cross-day reset, and cross-month
  accumulation; a `hypothesis` property test (e.g. "spend is monotonic,
  never double-counted") would strengthen this but wasn't required to meet
  P6 scope and the task's explicit "no speculative engineering" instruction
  for this phase.
- **No production call site for `ab_harness.run_ab`.** It's a harness
  function, correct and tested against the real `RiskEngine`, but nothing
  in the repo yet generates live paper signals and calls it per-signal —
  that's the paper-trading signal-generation loop, which doesn't exist yet
  (P2's risk engine and P3's dashboard exist; the loop that turns a closed
  candle into a `Signal` and calls `RiskEngine.check` + `run_ab` together in
  a running process is a separate piece of work, out of P6's scope as
  written).
- **No Usage dashboard tile** ("Brain cost today/this month" per
  BRAIN_AND_COSTS.md §5) — `BudgetGuard.status()` already returns everything
  a tile would need (`spent_today_inr`, `spent_month_inr` vs. caps); wiring
  it into the Streamlit dashboard from P3 is a small follow-up for whoever
  owns that page next.
- **Default RSS feed list is my best-effort pick** (NSE's own announcements
  RSS + a general financial RSS), not independently verified for uptime or
  that scraping is permitted — both are configurable without a code change
  (`RSSNewsFeed(feed_urls=(...))`), and AGENTS.md §10's "no scraping sites
  whose terms forbid it" applies here same as everywhere else; worth a
  second look before relying on it for real trading decisions.

## Needs human decision (see PR #59 body for the full version)

1. **Which Anthropic model, and current per-token INR pricing** —
   `anthropic_provider.py`'s price constants are placeholder estimates, not
   sourced from a live pricing page. Recommended default: the cheapest
   Haiku-class model for the "signal context verdict" tier per
   `docs/BRAIN_AND_COSTS.md` §4. Confirm before `BRAIN_ENABLED=true`.
2. **Daily/monthly INR cap** — `.env.example` already has
   `BRAIN_DAILY_BUDGET_INR=50` / `BRAIN_MONTHLY_BUDGET_INR=500` as a
   previously-set placeholder (not changed by this PR); flagging again here
   since this is the first phase that actually spends against it.

If no response, defaults above stand and the Brain simply stays off
(`BRAIN_ENABLED=false`) until the owner flips it, which is the safe default
either way.

## Cross-model review required

Per AGENTS.md §5, `risk`-adjacent modules always need the other company's
model to review before the owner merges. This phase's `brain/schema.py` and
`brain/ab_harness.py` feed directly into `RiskEngine.check()`'s sizing path
(`BrainVerdict` -> `compute_qty`) — a schema-validation bug here (e.g. a
missed field that lets `size_multiplier` exceed 1, or a malformed verdict
slipping through as valid) is a safety-relevant bug even though the Brain
itself still cannot place an order. **Codex: please review PR #59 before
the owner merges**, with particular attention to:
- `schema.py`'s `parse_verdict` — is there any JSON shape that validates but
  shouldn't (the `news_refs`-pop decision especially)?
- `ab_harness.py`'s shadow-`DecisionStore` approach — does it correctly
  avoid polluting the real engine's dedup state while still exercising the
  same calendar/freshness/kill-switch checks?
- `budget_guard.py`'s day/month boundary math (`now.replace(day=1)` etc.) —
  any UTC-vs-local edge case I'm missing?

## Next 3 actions (for whoever picks this up)

1. Codex: cross-model review of PR #59, per above.
2. Owner: confirm Anthropic model + pricing + budget caps (needs-human item
   above) before `BRAIN_ENABLED=true` is ever set for real.
3. Whoever builds the live paper-trading signal loop next: wire
   `brain/ab_harness.run_ab` into it per-signal, and add the Usage dashboard
   tile reading `BudgetGuard.status()`.
