# ADAPTERS — `src/trading/adapters/`

Status: P0 deliverable. Protocols + fakes only; real adapters (Kite Connect,
Angel One/Fyers, Alpaca, CCXT) are P1+ work (docs/BUILD_ORDER.md), built
against these interfaces. Depends only on `trading.core` (docs/ARCHITECTURE.md
§1): "adding a market = adding adapters + a market profile, not editing core."

## 1. `DataFeed` (`adapters/data_feed.py`)

`subscribe`, `poll_closed_candles() -> list[Candle]`, `last_tick`, `is_stale`.
Deliberately has **no "current forming bar" accessor** — only closed candles
exist in this interface, matching `Candle`'s own invariant and AGENTS.md
§4.5's no-look-ahead rule. `is_stale` returns `True` (fail closed) if nothing
has arrived yet, backing `docs/RISK_SPEC.md` check #4.

`FakeDataFeed`: candles/ticks are pushed manually (`push_closed_candle`,
`push_tick`); nothing happens on a timer. Good for strategy/risk unit tests;
real freshness/latency behavior is only provable against a real adapter.

## 2. `Broker` (`adapters/broker.py`)

`is_paper() -> bool` (backs invariant I1: in `paper` mode the real-broker
adapter must never even be constructed, let alone called — the risk
engine/mode gate check this flag, not a config string, so there's one place
that can be wrong instead of two), `place_order`, `cancel_order`, `get_order`,
`positions`.

`transition(order, new_status)` is the **only** sanctioned way to change an
`Order.status`; it looks up `ORDER_STATUS_TRANSITIONS` and raises
`IllegalOrderTransitionError` on anything else — this is the fail-closed state
machine from `docs/RISK_SPEC.md` §6, enforced in code rather than left to each
adapter to reimplement correctly (or not).

`FakePaperBroker`: fills immediately at `limit_price` (or a placeholder price
for market orders) with zero slippage and zero fees. It exists to exercise the
`Broker` Protocol and the idempotency/state-machine invariants, not to model
real paper-trading costs — that's `docs/BUILD_ORDER.md` P2's "Paper broker
with cost/slippage models."

## 3. `NewsFeed` (`adapters/news_feed.py`)

`fetch_since(datetime) -> list[NewsItem]`. `NewsItem` is untrusted input the
moment it leaves this adapter (AGENTS.md §4.6, prompt-injection risk) — it is
plain data, never fed to an LLM without going through the Brain's
context-building/sanitization step, which doesn't exist yet (P6).

## 4. `LLMProvider` (`adapters/llm_provider.py`)

`get_verdict(signal, context) -> BrainVerdict | None`. **`None` means
exactly the same thing as a valid `NEUTRAL` verdict with `size_multiplier=1`**
— a failed call, a timeout, invalid output, or a budget-guard block must never
be silently treated as "no signal fired" or, worse, as support. The risk
engine's own handling is in `docs/specs/RISK_ENGINE_SPEC.md`
(invariant I8); `default_absent_verdict()` here is the canonical value to
substitute. `FakeLLMProvider` returns a fixed verdict or `None`, so both the
"Brain present" and "Brain absent/invalid" code paths are testable without a
real API key.

## 5. Contract-test suites

`tests/adapters/contract_broker.py` defines `BrokerContractTests`, a mixin
asserting the invariants every `Broker` implementation must satisfy
regardless of venue (filled qty never exceeds requested qty, duplicate
request ids are idempotent, `get_order` round-trips). A real adapter's test
file subclasses it with a `broker` fixture; see
`tests/adapters/test_fake_paper_broker.py` for the pattern. `DataFeed`,
`NewsFeed`, and `LLMProvider` don't have enough implementations yet to justify
a shared mixin (YAGNI) — add one the day a second real implementation of any
of them exists.
