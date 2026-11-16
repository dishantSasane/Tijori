# Manually curated pilot action register

This offline register is a bounded evidence input, not a corporate-action feed
or proof that a backtest is safe. It supports RELIANCE, INFY, TCS, HDFCBANK and
ICICIBANK only. The example has **zero events and no verified coverage**; its
dates are illustrative review windows, not claims about data availability.
ISIN (the instrument's international identifier) must be independently checked.

## Schema and review

`load_action_register(Path(...)) -> ActionRegister` reads YAML locally. Version
2 allows at most 256 KiB, 1,000 events and 100 coverage windows. Unknown fields,
YAML aliases, duplicate keys/IDs/event identities, conflicting ISIN mappings,
and overlapping coverage windows fail closed. Models are immutable.

Each event records `event_id`, `isin`, `symbol`, exchange-local `ex_date`,
`publication_date` (null if unknown), `action_type`, `original_ratio`, optional
`verified_factor`, `source_url`, `reviewer`, `review_date`, `price_basis` and
`volume_basis`. Bases independently default to `unknown`; the other values are
`raw` and `provider_adjusted`. Publication dates describe source publication,
not retrieval dates. A review cannot predate publication. Source URLs must be
HTTP(S); the loader never fetches them or establishes their truth.

The factor is a quoted Decimal expressing **new total shares per old share**:
a synthetic 1-for-1 bonus has factor `"2"`, not `"1"`. Original ratio text is
preserved and never parsed or used to guess a factor. Splits can reduce shares;
bonuses must increase them. Non-finite, zero and unchanged-share factors fail.
Demergers, rights, dividends and `other` cannot carry factors and always block.
Mergers or any unsupported action must be recorded as `other`, never omitted.

Coverage rows specify `symbol`, optional `isin`, inclusive `start`/`end`, and
`verified` (default false). Verification requires ISIN, source URL, reviewer,
and a review date on or after the window end. Coverage is scoped to one exact
candle timeframe and one exact candle-snapshot SHA-256; daily evidence cannot
authorize an intraday replay, and one snapshot cannot attest another.
`covers(symbol, timeframe, start, end, candle_snapshot_sha256)` is
true only when one explicitly verified row contains the entire requested
window. It does not infer coverage from event presence, concatenate windows,
or imply that identified events are handled. Missing rows and empty event
lists prove nothing. Coverage is a retrospective human attestation, not a
point-in-time market signal.

## Small consumer API

- `notices()` retains every event as a `CorporateActionNotice`, including
  unknown publication dates and unsupported actions. No review bypass keys
  are emitted.
- `approved_adjustments(as_of=...)` emits `ShareAdjustment` only for supported
  split/bonus events with explicit factors, original ratio evidence, source,
  reviewer, and publication/review dates no later than `as_of`. Both price and
  volume must be explicitly raw. The existing transformer checks ex-date
  effectiveness; this method can include announced future-effective events.
- `provider_adjusted_events(as_of=...)` returns reviewed supported records with
  both bases provider-adjusted, separately from the transform ledger. It does
  not require a guessed factor. These records must never be transformed again.
- `blocked_events(as_of=...)` retains everything not in either approved group.
  Mixed bases remain blocked because the current transform changes both price
  and volume. Even reviewed complex actions remain blocked.

The caller must select relevant symbols and inclusive ex-date windows from
blockers/notices, require explicit coverage, and establish that each basis
applies to the exact dataset/provider/interval being used. Keep separate
register snapshots for different datasets/bases; do not generalize a daily
price observation to intraday volume. Preserve the original register alongside
source evidence and research artifacts. This loader does not archive evidence,
verify source permissions/completeness, validate ISIN checksums, or integrate
runners; those responsibilities stay with archive, adapter and preflight owners.

Version 1 contains one record per event, no in-file revision history. Preserve
corrected registers as new immutable snapshots; never mix their generated
revision-1 adjustments or silently overwrite earlier research evidence.
Cross-event duplicate detection uses symbol/ex-date/type as an additional
conservative guard against applying an event twice under different IDs.

Run local synthetic checks with:

```sh
.venv/bin/pytest tests/storage/test_action_register.py
```

These fixtures demonstrate validation and approval rules only. They assert no
real action, real ISIN mapping, source completeness or verified pilot coverage.
