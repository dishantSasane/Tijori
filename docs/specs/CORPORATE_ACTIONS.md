# Corporate-action price adjustment

Status: P1a implementation slice. The pure split/bonus transformation and
synthetic known-answer tests exist. It is **not yet approved for the Upstox
dataset**: the provider's documented candle fields do not establish whether
prices are raw or already adjusted, and no authorized point-in-time action
ledger has been acquired and validated.

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
not converted into guessed factors.

For an event that is effective by the requested replay date, earlier bars are
scaled by:

```text
adjusted OHLC = original OHLC / new_shares_per_old_share
adjusted volume = original volume * new_shares_per_old_share
```

Bars on the effective date and later retain their recorded OHLCV. A historical
replay must call the transform with that replay's own `as_of` date; future
actions and actions not yet published by that date are ignored. This avoids
using a later split to rewrite what the system would have observed before that
split was effective. The current function accepts daily bars only, so an
intraday or weekly candle that could straddle the effective date is rejected.

## Safety and provenance boundary

- Input must be verified raw/unadjusted candles. The Upstox V3 API describes
  OHLCV fields but does not document their corporate-action adjustment basis in
  the [historical candle contract](https://upstox.com/developer/api-documentation/v3/get-historical-candle-data/).
  Verify this with Upstox before applying the transform to provider data.
- Applying an action to candles already marked with a non-null `adj_factor`
  fails closed even if the requested as-of date would otherwise produce no
  adjustment; a previously transformed series cannot be reused as raw history.
- Preserve the original raw Parquet dataset. Store the complete action ledger,
  immutable source evidence, publication dates, event IDs, revisions, and a
  version/hash alongside every adjusted research export; `adj_factor` alone
  does not identify the source event. Corrected notices must be retained as
  separately versioned source records rather than silently replacing earlier
  evidence. The transform selects one revision per event as of the replay date
  and rejects duplicate or incorrectly ordered revisions.
- The current backtest runner does not model share-count changes on an open
  position. Therefore split/bonus-adjusted candles are not yet valid promotion
  evidence for trades spanning an effective date. That requires a separately
  tested position/action replay contract and independent reference-runner
  equivalence.
- No action source, licence, or corporate-action price adjustment has been
  accepted by the owner. Do not claim the current six-symbol sample is fully
  adjusted or survivorship-free.

## Validation completed and remaining

Synthetic known-answer tests cover a 2-for-1 split, a 1-for-1 bonus issue,
multiple events, effective-date boundaries, as-of filtering, revision
selection, market/symbol scoping, unsupported event types/timeframes, invalid
ratios, and double-adjustment rejection. Before P1a can exit, obtain an
authorized action source, confirm
Upstox price basis, validate real event records against dated official notices,
and extend both primary and reference backtesters for positions crossing share
adjustments.
