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
from decimal import Decimal

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
) -> tuple[ResearchInstrument, list[TurnoverObservation], tuple[date, ...]]:
    """Fetch one instrument's daily candles for the exact lookback window and
    derive its turnover observations.

    `sessions` is the caller-verified trading-day calendar (per
    `research_universe.build_snapshot`'s own contract: "the caller is
    responsible for its completeness") -- every date in it is already a
    confirmed genuine trading day, so a session missing from this
    instrument's response is never a calendar question, only an instrument
    question.

    Upstox omits the row entirely for an illiquid instrument's no-trade day
    (confirmed empirically: e.g. SONAL/INE321M01017 has no row at all for
    2026-08-12, an ordinary trading day) rather than returning an explicit
    zero-volume candle. A missing session is decoded as a confirmed
    no-trade day -- recorded as an explicit, labeled zero-turnover
    observation, auditable via the returned `decoded_no_trade_days` -- only
    when it is *sandwiched*: this exact instrument has a real candle on
    both the nearest earlier and the nearest later session in `sessions`.
    That pattern (isolated single-session gaps between real activity) is
    Upstox's confirmed no-trade-day convention, not a data outage or a
    listing/delisting boundary. A leading/trailing gap, or a multi-session
    run of missing dates, is never decoded this way -- it remains a hard
    error in `build_snapshot`, same as before this change: those shapes
    could mean the instrument wasn't listed yet, was delisted, was
    suspended, or the provider had an outage, and none of those may be
    silently assumed to mean zero turnover.
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

    decoded_no_trade_days: list[date] = []
    observations: list[TurnoverObservation] = []
    for index, session in enumerate(sessions):
        if session in candles_by_date:
            candle = candles_by_date[session]
            observations.append(
                TurnoverObservation(
                    session_date=session,
                    isin=entry.isin,
                    turnover_inr=candle.close * candle.volume,
                    explicit_zero=candle.volume == 0,
                )
            )
            continue
        # Immediate neighbors only -- an isolated single-session gap, not a
        # multi-session run (a run means every day in it would otherwise
        # pass an "any earlier/any later" test too, wrongly decoding a
        # suspension as a string of no-trade days).
        immediate_earlier_present = index > 0 and sessions[index - 1] in candles_by_date
        immediate_later_present = (
            index + 1 < len(sessions) and sessions[index + 1] in candles_by_date
        )
        if immediate_earlier_present and immediate_later_present:
            decoded_no_trade_days.append(session)
            observations.append(
                TurnoverObservation(
                    session_date=session,
                    isin=entry.isin,
                    turnover_inr=Decimal(0),
                    explicit_zero=True,
                )
            )
        # else: leading/trailing or multi-session gap -- leave unobserved,
        # letting build_snapshot's existing hard-error-on-missing fire.

    return instrument, observations, tuple(decoded_no_trade_days)


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
    on_decoded_no_trade_day: Callable[[str, date], None] | None = None,
) -> MonthlyUniverseSnapshot:
    """Fetch real Upstox daily candles for every instrument in
    `master_entries` over `sessions`' 60-session lookback and rank them with
    the existing pure `build_snapshot` selector -- unchanged ranking logic,
    real data instead of synthetic. Does not cache/resume across process
    restarts; callers running this unattended should persist partial results
    themselves (same pattern as `intraday_loader`'s `CandleStore`-backed
    resumability) if a run is interrupted.

    `on_decoded_no_trade_day(isin, session_date)` fires once per isolated
    missing-session gap decoded as a confirmed no-trade day (see
    `fetch_turnover_observations_for_instrument`'s docstring) -- an audit
    trail of exactly which (isin, date) pairs were filled this way, since
    that decoding is a real assumption about provider behavior, not a
    directly observed fact, and must stay inspectable.
    """
    instruments: list[ResearchInstrument] = []
    observations: list[TurnoverObservation] = []
    for index, entry in enumerate(master_entries):
        if index:
            sleeper(minimum_request_interval_seconds)
        instrument, entry_observations, decoded_no_trade_days = (
            fetch_turnover_observations_for_instrument(
                client, entry, sessions=sessions, access_token=access_token, clock=clock
            )
        )
        instruments.append(instrument)
        observations.extend(entry_observations)
        if on_decoded_no_trade_day is not None:
            for session in decoded_no_trade_days:
                on_decoded_no_trade_day(entry.isin, session)
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
