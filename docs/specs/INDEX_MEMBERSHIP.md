# Point-in-time index membership manifest

Status: P1a data-contract design. This defines how an authorized membership
dataset will be represented and checked; it does not select a provider, grant a
licence, or assert that historical records have been acquired.

## Time and identity semantics

- Membership intervals are half-open: `effective_from <= session_date <
  effective_to`. `effective_to = null` means the member remains in the index
  through the manifest's exclusive `coverage_end`.
- Dates are exchange-local NSE session dates. The membership recorded for a
  date is the set effective on that date; a current constituent list is never
  used to fill earlier history.
- Stable identity is the ISIN. `symbol_at_time` and `company_name_at_time`
  preserve the historical display names; they are not identity keys.
- Every interval cites its official source notice, notice date, review status,
  and notes. Unverified or guessed intervals cannot be marked reviewed.
- The manifest records the dataset source, source reference, licence reference,
  version, declared coverage, and whether the dataset claims complete index
  coverage. These fields make provenance explicit; they do not themselves
  prove that a licence is valid.

## Validation contract

`MembershipInterval` requires an index ID (`NIFTY50` or `NIFTYNEXT50`), a
12-character Indian ISIN with valid format and check digit, historical symbol/name,
start and optional exclusive end,
source notice URL/date, `review_status` (`pending`, `verified`, or `rejected`),
and notes. It rejects malformed ISINs, empty identity fields, and
non-positive intervals. The source notice must be dated no later than the
interval's effective start, preventing a later source record from being used to
claim the composition was known earlier. A manifest marked complete requires
every interval to be `verified`.

`MembershipManifest` contains the intervals plus `coverage_start` and exclusive
`coverage_end`. It rejects:

- intervals outside declared coverage;
- duplicate or overlapping intervals for the same index and ISIN;
- the same ISIN being in Nifty 50 and Nifty Next 50 at the same time;
- any manifest with more than 50 active distinct members in either index at a
  represented boundary;
- a claimed-complete manifest that does not contain exactly 50 distinct
  members in each index at every interval boundary in the declared coverage.

Partial manifests may contain fewer than 50 members, but never more than 50;
their `complete` flag must remain false. They are useful for development and
schema validation only;
they cannot support a full-universe or survivorship-free result. Querying a
date outside the manifest's half-open coverage fails closed. A membership
lookup returns only intervals active on the requested date, ordered by ISIN.

The completeness count is checked at the coverage start and at every
`effective_from`/`effective_to` boundary within coverage. Since the membership
set is constant between those boundaries, this validates every represented
interval without iterating over all calendar days.

## Source gate

The official NSE Indices subscription route is documented in
[`DATA_SOURCES.md`](DATA_SOURCES.md#point-in-time-nifty-50--next-50-membership).
Do not load a real manifest until historical coverage, delisted-name coverage,
identifier mapping, and the intended research/backtesting licence have been
confirmed and recorded. Community reconstructions may only be cross-checks.
