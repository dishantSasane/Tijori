# Monthly turnover research universe

Status: P1a algorithm contract. The primary research universe is the top 50
eligible NSE cash-equity ISINs by trailing 60-session median traded value,
recomputed monthly. A separate top-100 snapshot is reserved for later
Tier-B-adjacent research; it is not a parameter sweep. Daily candles remain
Upstox-only under ADR-0023.

## Selection rule

For each monthly snapshot:

1. Let `effective_date` be the first NSE trading session of the month.
2. Let `as_of_date` be the previous NSE trading session. Use only completed
   market files dated on or before `as_of_date`.
3. The source normalizer supplies eligible ISINs that were listed and eligible
   throughout the 60-session window and remain active at `as_of_date`. It must
   record newer listings and other excluded instruments with explicit reasons.
4. For each eligible ISIN, collect one turnover value in INR for each of the
   preceding 60 NSE trading sessions, including explicit zero-turnover
   observations where the source confirms no trade. Missing or corrupt source
   data is an error; it is never silently converted to zero.
5. Compute the ordinary median of the 60 values (the arithmetic mean of the
   30th and 31st sorted values). Rank by median descending, then ISIN
   lexicographically ascending to break exact ties.
6. Select the first 50 ISINs for the primary Tier A universe. The later
   Tier-B-adjacent view may select the first 100 from the same ranked list.
   The snapshot is effective on `effective_date` and remains in force until the
   next monthly snapshot.

ISIN is the stable identity. Historical symbol and company name are metadata;
they must not merge, split, or reorder identity histories. The eligible
instrument-class filter must be versioned and recorded with each snapshot;
unknown series/instrument classes fail closed instead of being silently
included or excluded.

The pure API is `build_snapshot(sessions, effective_date, instruments,
observations, provenance, k)`. Inputs and output are immutable Pydantic models
in `trading.storage.research_universe`: `ResearchInstrument`,
`TurnoverObservation`, `UniverseProvenance`, and
`MonthlyUniverseSnapshot`. `sessions` is the verified ordered exchange
calendar; the caller is responsible for its completeness, as ordering checks
cannot identify omitted exchange sessions. Each instrument has an ISIN,
`active_as_of`, known `eligible` status, and `verified_history_start`.
Eligibility and activity are point-in-time facts verified as of the snapshot
date; eligibility must hold throughout the lookback. Current classifications
or instrument masters alone are insufficient for historical snapshots. Each
observation has a session date, ISIN,
non-negative INR turnover, and `explicit_zero`; a zero is valid only when the
source explicitly confirms it. Provenance includes universe and eligible-set
rule versions, source and licence references, raw-file identifiers and
checksums, and parser version. The builder returns the output model; persisted
or compared representations use Pydantic's Python-mode dump so dates and
decimals retain their types.

The output `MonthlyUniverseSnapshot` records the provenance, `K`, lookback
dates, as-of/effective dates, exclusions, all ranked eligible candidates, and
the selected ISINs. Unknown eligibility fails closed. Inactive, ineligible,
or less-than-60-session-history instruments are excluded with reasons.
An otherwise-eligible instrument with any unresolved missing observation in
the requested 60-session window is excluded with reason
`unresolved_data_gap_in_lookback_window` -- this excludes only that
instrument from that month's ranking; it never zeroes the gap and never
aborts the other eligible instruments' ranking. Duplicate instrument
identities, duplicate observations, unknown ISINs, or fewer than `K`
eligible candidates remaining after exclusions still fail the snapshot. The
calendar must be
strictly ordered and unique; `effective_date` must be its first session of a
calendar month and the supplied history must include the preceding session.
Source rows outside the lookback may be present but cannot affect the ranking.
This function does not fetch data, interpret raw CSV fields, or claim source
permission.

## Data completeness and provenance

The selection function consumes normalized observations, not raw provider
files. Its input must identify the session date, ISIN, turnover in INR, and
whether zero turnover is an explicit source observation. For each eligible
ISIN, the input must cover exactly the 60 session dates in the lookback, with
no duplicate `(session_date, ISIN)` rows. A source file failure, missing
session, ambiguous identifier, or unclassified instrument blocks that monthly
snapshot.

Every saved snapshot records: universe version, `K`, lookback length, ordered
lookback session dates, `as_of_date`, `effective_date`, eligible-set rule
version, source and licence references, raw file identifiers/checksums,
parser version, ranked candidates with median turnover, and explicit
exclusions. This provides a reproducible point-in-time universe. It is
survivorship-free only to the extent that the authorized dated source is
complete for all eligible securities, including securities later delisted; the
ranking formula alone cannot establish data completeness or usage rights.

## Source gate

ADR-0026 selects the turnover-ranking method and proposes NSE
`sec_bhavdata_full` for the observations; it does not grant source rights.
Official terms and the archived-file schema have not established permission
for systematic collection, storage, derived datasets, or simulation/backtest
use, nor stable identifiers and complete historical coverage. Keep real NSE
data out of automated ingestion and backtests until applicable rights and
schema/coverage are documented. Public download availability does not prove
permission. Upstox stays the sole P1 candle source; this gate does not change
the P3 live-provider decision.
