# TEST SPEC — Adapters

Status: P0 deliverable (BUILD_ORDER.md item 7, adapters slice — the last
remaining piece). Each real adapter (Kite Connect, Angel One/Fyers, Alpaca,
CCXT — P1+) must pass the test list below in addition to whatever is
specific to its own API. `ADAPTERS.md` §5 already has `BrokerContractTests`
as a runnable mixin; this spec adds the equivalent test *lists* (not yet
mixins — see §5's YAGNI note, unchanged) for `DataFeed`, `NewsFeed`, and
`LLMProvider`, plus what's specific to each market's real `Broker`.

## 1. `Broker` (extends `ADAPTERS.md` §5's `BrokerContractTests`)

The existing mixin (`tests/adapters/contract_broker.py`) covers: filled qty
never exceeds requested qty, duplicate request ids are idempotent,
`get_order` round-trips. A **real** adapter's test file subclasses it
(`ADAPTERS.md` §5's pattern) and additionally needs:

1. **Reconciliation on connect:** on startup, the adapter's reported open
   positions/orders match what the system's own state (SQLite) believes, or
   the system refuses to start trading (invariant I12). Test with a fake
   HTTP layer returning a deliberately mismatched position — assert startup
   is refused, not silently reconciled by trusting the broker over local
   state (or vice versa) without a human seeing it.
2. **Rate-limit / 429 handling:** the adapter backs off and retries (or
   surfaces a clear "paused, rate-limited" state) rather than either
   crashing or silently dropping the order. Needed because `MARKETS.md`
   lists real per-provider rate limits (e.g. SmartAPI's
   `getCandleData` at 3 req/s).
3. **Token expiry mid-session:** a real broker session token expires
   (common for Indian broker APIs, which require a daily login). The
   adapter must surface this as a health-check failure (ARCHITECTURE.md
   §11) and pause the sleeve, not retry forever or place an order with a
   stale/rejected auth header.
4. **Idempotency survives a network timeout, not just an in-process retry:**
   `FakePaperBroker`'s dedup is an in-memory dict keyed by request id — a
   real adapter must prove the *broker's own* API is idempotent on retry
   (most order-placement APIs accept a client order id for exactly this
   reason) or that the adapter itself persists "I already submitted this
   request id" durably enough to survive a process restart before retrying
   after a timeout of unknown outcome (did the order actually go through?).
   This is the single most dangerous gap between a fake and a real broker —
   flag it loudly in any real adapter's PR description, don't just assume
   the fake's test coverage transfers.
5. **`is_paper()` cannot be flipped by config alone for a live-money
   adapter class:** a live `Broker` implementation (e.g. `KiteBroker`)
   should hardcode `is_paper() -> False` in code, not read it from
   `config/risk.yaml`'s `mode` — the whole point of invariant I1 is that a
   paper-mode system literally cannot construct a live broker object in the
   first place (the mode gate decides *whether* to call a broker, never
   *which class* to call based on a flag that could be fat-fingered).

## 2. `DataFeed`

6. **Freshness reflects the real feed, not the fake's manual push:** a real
   adapter's `is_stale()` must be driven by the actual last-received-tick
   timestamp from the provider connection, and a test should simulate the
   underlying WebSocket/poll going silent (no new ticks) and assert
   `is_stale()` flips to `True` after `stale_data_seconds`, without any
   candle ever needing to be force-closed to make that happen — staleness
   detection is independent of candle-closing.
7. **Reconnect does not duplicate or skip bars:** kill the underlying
   connection mid-session (simulated), let the adapter reconnect, and assert
   the candle sequence it produces has no gap (missing bar silently
   dropped) and no duplicate (same bar emitted twice) across the
   reconnection boundary — reuse `TEST_SPEC_CANDLES.md` §1's "zero-tick bar
   still closes" logic to tell a genuine market gap (holiday, halt) apart
   from a feed-side data loss.
8. **Provider-specific rate/subscription limits are enforced client-side
   before hitting the API, not discovered via a 429:** e.g. FYERS' 100-symbol
   WebSocket cap (`MARKETS.md` §2) — `subscribe()` should refuse (or queue)
   a 101st symbol rather than silently dropping one already-subscribed
   symbol's data to make room, which would be a silent coverage loss.

## 3. `NewsFeed`

9. **`fetch_since` never returns an item twice across consecutive calls**
   with overlapping time windows (most providers' "since" semantics are
   inclusive on one end) — test with a deliberately overlapping `since`
   boundary.
10. **A provider response with missing/malformed fields does not crash the
    whole poll:** one bad `NewsItem` in a batch of 50 should be dropped and
    logged, not take down the other 49 — relevant because `NewsItem` isn't
    validated as strictly as `Contract` subclasses (it allows
    `body=""`/`symbols=()` defaults deliberately, since not every provider
    gives every field).

## 4. `LLMProvider`

11. **Timeout produces `None`, not an exception that propagates into the
    risk engine:** the Brain is never in the hot path (AGENTS.md §4.6) —
    a slow/hanging API call must be bounded by a timeout at the adapter
    level, after which it returns `None` (RISK_ENGINE_SPEC.md §5's "treated
    as absent"), never block the signal pipeline indefinitely.
12. **Budget guard rejection also produces `None`, with its own audit
    event type** (`"brain_call_budget_exceeded"`, distinct from
    `"brain_call_invalid"` and `"brain_call_absent"` — see
    `RISK_ENGINE_SPEC.md` §5 and ADR-0018) — not yet built
    (`BRAIN_AND_COSTS.md`'s budget guard is P6), recorded here so the
    adapter's test suite grows the right shape when that code lands.
13. **Already covered by `TEST_SPEC_RISK.md` §3** (invalid JSON, veto,
    support-doesn't-increase-size, size-multiplier monotonicity) — this
    spec doesn't repeat those, just cross-references them so a reader
    looking for "the LLMProvider test list" finds both halves.

## 5. What this spec does NOT do

- Convert any of the above into `pytest` fixtures/mixins today — per
  `ADAPTERS.md` §5, that happens once a second real implementation of each
  Protocol exists, not speculatively now.
- Specify provider-specific request/response shapes (API payload fields) —
  that's each real adapter's own implementation detail, reviewed in its PR.
