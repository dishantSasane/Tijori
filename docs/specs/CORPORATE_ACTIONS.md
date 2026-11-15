# Corporate-action price adjustment

Status: P1a implementation slice; source and coverage gates remain open. The
pure split/bonus transformation and synthetic known-answer tests exist. A real
Upstox V3 daily response for
NESTLEIND around its NSE 10:1 split (ex-date 2024-01-05) shows already adjusted
prices: ₹1,355.80 on 2024-01-04 and ₹1,333.20 on 2024-01-05. The prior close is
already continuous with the ex-date close, indicating that this series has
removed the split discontinuity; applying the 10:1 transform again would
double-adjust it. The absolute historical scale may reflect later actions too,
so do not derive an unadjusted close by dividing these values by ten. See
`tests/fixtures/upstox/upstox_nestle_2024_split.json`
and the known-answer test. This one event does not establish behavior for all
symbols/actions or validate the completeness, rights, or point-in-time
correctness of an NSE action ledger.

## Supported events

`trading.storage.corporate_actions.ShareAdjustment` supports only splits and
bonus issues. The action records the market, symbol, publication date,
effective exchange-local date, stable event ID, revision number, source
reference, and `new_shares_per_old_share` ratio. Revisions for an event must
have increasing publication dates; each as-of replay selects only the latest
revision published by that date. A 2-for-1 split uses `2`; a 1-for-1 bonus
issue also uses `2` because each old share becomes two shares. A reverse split
may use a ratio below one; a bonus issue must add shares and therefore uses a
ratio above one. Dividends, rights, mergers, demergers, and other events are
not converted into guessed factors. NSE row normalization classifies demerger,
rights, dividend, and unknown-purpose events as review-only notices; it never
constructs a share factor for them.

For an event that is effective by the requested replay date, earlier bars are
scaled by:

```text
adjusted OHLC = original OHLC / new_shares_per_old_share
adjusted volume = original volume * new_shares_per_old_share
```

Adjustment arithmetic uses a fixed Decimal precision and rounding mode so it
does not change with the caller's process-wide Decimal context. Before DuckDB
storage, candle values are rounded half up to the store's 18 decimal places;
repeat ingestion compares those same canonical values.

Bars on the effective date and later retain their recorded OHLCV. A historical
replay must call the transform with that replay's own `as_of` date; future
actions and actions not yet published by that date are ignored. This avoids
using a later split to rewrite what the system would have observed before that
split was effective. The transform accepts daily and intraday bars and compares
each bar's timestamp in India local time to the effective date. Every intraday
bar on the ex-date or later is left at its traded value; earlier sessions are
adjusted. Daily and intraday ingestion use
`trading.storage.adjusted_ingestion.append_adjusted_candles`, which invokes the
transform before storage when given a verified action ledger. The intraday
loader requires callers to attest that
the ledger is complete and authorized, but cannot independently establish
either property. An empty ledger does not prove there were no actions.

## Backtest-window action screening

`UpstoxCorporateActionsClient` fetches the documented authenticated corporate-
actions endpoint by ISIN. It preserves the provider's event name, date, raw
ratio text, amount, detail fields, and endpoint reference. It deliberately does
not infer share factors from the ratio text. The shared classifier recognizes
split, bonus, demerger, rights, dividend, and unknown purposes;
unrecognized descriptions are retained as `other` so they cannot silently
disappear. The legacy `parse_nse_corporate_action_row` is a pure row
normalizer only; it is not an NSE downloader and must not be wired to automated
NSE site collection. `inspect_unhandled_actions` selects notices whose ex-date is
inclusive within the backtest window and whose symbol is in the candidate
universe. A split or bonus is considered handled only when its exact
`(symbol, ex_date)` is listed in the verified handled-action keys. A key can
mean that the provider already adjusted the event or that the approved
transform did. Demergers,
rights issues, dividends, and unknown action types always produce review
flags.

`screen_backtest_symbols` excludes every flagged symbol by default. A caller
may allow a symbol only by supplying an explicit reviewed key for that exact
`(symbol, ex_date, kind)`; the flag remains in the result for audit. This is a
screen over normalized feed rows, not evidence that the Upstox response is
complete. Its current endpoint documentation does not explicitly promise
demerger coverage or declare the event list exhaustive. The backtest
orchestrator must run this screen before invoking
either primary or reference replay, and record the flags and chosen exclusions
or reviews in its experiment record.

In particular, NSE demerger and rights issues alter company/shareholder value
through mechanics that differ from splits and bonus issues. They are detected
and blocked for review; no price, volume, quantity, or return adjustment is
attempted.

## Safety and provenance boundary

- Input to the transformer must be verified raw/unadjusted candles. The
  captured NESTLEIND event is evidence that Upstox V3 daily candles are already
  split-adjusted across that event; do not apply that event to those candles or
  generalize the observation to every adjustment type, interval, or symbol.
  Provider-adjusted event keys must be omitted from the transform ledger to
  avoid double adjustment; `prepare_candles_for_storage` supports this exact
  exclusion. Upstox's
  [historical candle contract](https://upstox.com/developer/api-documentation/v3/get-historical-candle-data/)
  documents OHLCV fields but not adjustment behavior.
- Applying an action to candles already marked with a non-null `adj_factor`
  fails closed even if the requested as-of date would otherwise produce no
  adjustment; a previously transformed series cannot be reused as raw history.
- Preserve the original raw Parquet dataset. Store the complete action ledger,
  immutable source evidence, publication dates, event IDs, revisions, and a
  version/hash alongside every adjusted research export; `adj_factor` alone
  does not identify the source event. Corrected notices must be retained as
  separately versioned source records rather than silently replacing earlier
  evidence. The implemented sidecar currently stores the Parquet content hash,
  as-of date, and per-series ledger/basis hashes, not the full event ledger or
  source evidence; packaging those records and preserving a parallel raw archive
  remain P1a gates. The transform selects one revision per event as of the replay
  date and rejects duplicate or incorrectly ordered revisions.
- The current backtest runner does not model share-count changes on an open
  position. Therefore split/bonus-adjusted candles are not yet valid promotion
  evidence for trades spanning an effective date. That requires a separately
  tested position/action replay contract and independent reference-runner
  equivalence.
- The Upstox API is the selected P1 action source. Its documented endpoint is
  implemented as an authenticated adapter, but a live request on 2026-11-15
  was denied by Cloudflare with `browser_signature_banned` and an instruction
  not to retry. No response ledger has been fetched or saved. Do not claim
  source coverage until live access and completeness are verified. The API docs
  do not explicitly list demergers; these require separately reviewed,
  permitted records. The synthetic 1:1 bonus case validates the formula, but
  is not evidence of provider bonus parsing or completeness. Do not claim
  the current six-symbol sample is fully adjusted or survivorship-free.
- This branch has an intraday loader but no daily Upstox loader to retrofit.
  Daily history already held locally has not been rewritten. The daily and
  intraday adjustment function is available to ingestion code, but P1a cannot
  claim all stored history was adjusted until a permitted, complete ledger and
  verified provider adjustment basis are available.

## Validation completed and remaining

Known-answer tests cover the Upstox NESTLEIND 10:1 provider-adjusted event, a
synthetic 10-for-1 and 2-for-1 split calculations, a synthetic 1-for-1 bonus issue,
multiple events, effective-date boundaries, as-of filtering, revision
selection, market/symbol scoping, provider-adjusted event exclusion, unsupported event types, invalid
ratios, and double-adjustment rejection. Synthetic NSE-row tests cover event
classification and backtest-window screening for demergers, rights issues,
splits, bonuses, dividends, and unknown action purposes. Before P1a can exit,
obtain an action-source permission/coverage decision, validate additional event types,
and extend both primary and reference backtesters for positions crossing share
adjustments. The NESTLEIND real-event probe closes the price-basis unknown for
this 10:1 split only.
