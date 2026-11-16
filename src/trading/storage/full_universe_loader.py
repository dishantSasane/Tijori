"""Build a real monthly turnover `MonthlyUniverseSnapshot` from Upstox's own
official historical-candle API, looped across the full NSE cash-equity list
from `upstox_instrument_master` -- the same licensed endpoint Tier A already
uses, just at full-universe scope. This sidesteps the NSE-site/bhavcopy ToU
question entirely (docs/specs/RESEARCH_UNIVERSE.md "Source gate"): every
request here is an Upstox API call under ADR-0023, not an NSE scrape.

Turnover-proxy methodology note (record alongside ADR-0026): Upstox's basic
candle payload has no official "value traded" field, only OHLCV. This loader
uses `close * volume` as the turnover_inr proxy -- the standard approximation
when true traded value isn't directly available. This is a real methodology
choice, not free of assumptions, and should be named as such wherever the
resulting universe is used; it is not identical to NSE's own reported traded
value.

Rate limiting: Upstox's documented budget is 50 req/sec, 500/min, 2000/30min
(same figures the P1 intraday loader already verified live). A full-universe
daily pull is ~2,000 requests for one 60-session lookback; this loader
self-throttles well under the documented minute budget and is resumable by
simply skipping instruments whose full window is already in `results`.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import UTC, date, datetime

from trading.adapters.upstox_history import UpstoxHistoryClient
from trading.core.enums import MarketId, Timeframe
from trading.storage.research_universe import (
    MonthlyUniverseSnapshot,
    RawFileProvenance,
    ResearchInstrument,
    TurnoverObservation,
    UniverseProvenance,
    build_snapshot,
)
from trading.storage.upstox_instrument_master import EquityMasterEntry

#: Conservative self-throttle, well under Upstox's documented 500/min budget.
DEFAULT_MINIMUM_REQUEST_INTERVAL_SECONDS = 0.15


def _daily_window_strings(sessions: tuple[date, ...]) -> tuple[str, str]:
    return sessions[0].isoformat(), sessions[-1].isoformat()


def fetch_turnover_observations_for_instrument(
    client: UpstoxHistoryClient,
    entry: EquityMasterEntry,
    *,
    sessions: tuple[date, ...],
    access_token: str,
    clock: Callable[[], datetime],
) -> tuple[ResearchInstrument, list[TurnoverObservation]]:
    """Fetch one instrument's daily candles for the exact lookback window and
    derive its turnover observations. `sessions` must be the verified
    calendar slice this instrument is being scored against -- a missing
    session in the response fails closed in `build_snapshot`, not here.
    """
    from_date, to_date = _daily_window_strings(sessions)
    candles = client.fetch(
        entry.instrument_key,
        symbol=entry.trading_symbol,
        market=MarketId.IN_EQUITY,
        timeframe=Timeframe.D1,
        from_date=from_date,
        to_date=to_date,
        ingest_ts=clock(),
        access_token=access_token,
    )
    candles_by_date = {candle.ts_open_utc.date(): candle for candle in candles}
    instrument = ResearchInstrument(
        isin=entry.isin,
        active_as_of=True,
        eligible=True,
        verified_history_start=min(candles_by_date, default=sessions[-1]),
    )
    observations = [
        TurnoverObservation(
            session_date=session,
            isin=entry.isin,
            turnover_inr=(candle := candles_by_date[session]).close * candle.volume,
            explicit_zero=candle.volume == 0,
        )
        for session in sessions
        if session in candles_by_date
    ]
    return instrument, observations


def build_full_universe_snapshot(
    *,
    client: UpstoxHistoryClient,
    access_token: str,
    master_entries: list[EquityMasterEntry],
    sessions: tuple[date, ...],
    effective_date: date,
    k: int = 50,
    minimum_request_interval_seconds: float = DEFAULT_MINIMUM_REQUEST_INTERVAL_SECONDS,
    sleeper: Callable[[float], None] = time.sleep,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    on_progress: Callable[[int, int, str], None] | None = None,
) -> MonthlyUniverseSnapshot:
    """Fetch real Upstox daily candles for every instrument in
    `master_entries` over `sessions`' 60-session lookback and rank them with
    the existing pure `build_snapshot` selector -- unchanged ranking logic,
    real data instead of synthetic. Does not cache/resume across process
    restarts; callers running this unattended should persist partial results
    themselves (same pattern as `intraday_loader`'s `CandleStore`-backed
    resumability) if a run is interrupted.
    """
    instruments: list[ResearchInstrument] = []
    observations: list[TurnoverObservation] = []
    for index, entry in enumerate(master_entries):
        if index:
            sleeper(minimum_request_interval_seconds)
        instrument, entry_observations = fetch_turnover_observations_for_instrument(
            client, entry, sessions=sessions, access_token=access_token, clock=clock
        )
        instruments.append(instrument)
        observations.extend(entry_observations)
        if on_progress is not None:
            on_progress(index + 1, len(master_entries), entry.trading_symbol)

    provenance = UniverseProvenance(
        universe_version="full-nse-eq-v1",
        eligible_set_rule_version="nse-eq-series-only-v1",
        source_reference="upstox-v3-historical-candle+instrument-master",
        licence_reference="upstox-api-terms-adr-0023",
        raw_files=(
            RawFileProvenance(identifier="upstox-complete-master", checksum="n/a-live-api"),
        ),
        parser_version="1",
    )
    return build_snapshot(list(sessions), effective_date, instruments, observations, provenance, k)
