from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from trading.backtest.fills import BacktestProfile
from trading.backtest.universe_evaluation import run_p1_daily_candidate_across_universe
from trading.core.enums import MarketId, Timeframe
from trading.core.models import Candle
from trading.storage.research_universe import (
    RawFileProvenance,
    ResearchInstrument,
    TurnoverObservation,
    UniverseProvenance,
    build_snapshot,
)

ISIN_A = "INE002A01018"
ISIN_B = "INE009A01021"
ISIN_MISSING = "INE467B01029"


def _exchange_sessions() -> list[date]:
    # Synthetic calendar: weekdays are sessions; July 1 2024 is a Monday.
    start, end = date(2024, 3, 1), date(2024, 7, 2)
    return [
        start + timedelta(days=i)
        for i in range((end - start).days + 1)
        if (start + timedelta(days=i)).weekday() < 5
    ]


SESSIONS = tuple(_exchange_sessions())
EFFECTIVE_DATE = date(2024, 7, 1)
AS_OF = date(2024, 6, 28)
LOOKBACK = [day for day in SESSIONS if day <= AS_OF][-60:]


def _snapshot():
    instruments = [
        ResearchInstrument(
            isin=isin, active_as_of=True, eligible=True, verified_history_start=LOOKBACK[0]
        )
        for isin in (ISIN_A, ISIN_B, ISIN_MISSING)
    ]
    observations = [
        TurnoverObservation(
            session_date=day, isin=isin, turnover_inr=Decimal(amount), explicit_zero=False
        )
        for isin, amount in ((ISIN_A, 1000), (ISIN_B, 500), (ISIN_MISSING, 100))
        for day in LOOKBACK
    ]
    provenance = UniverseProvenance(
        universe_version="test-universe-v1",
        eligible_set_rule_version="test-rule-v1",
        source_reference="test-source",
        licence_reference="test-licence",
        raw_files=(RawFileProvenance(identifier="test-file", checksum="sha256:test"),),
        parser_version="1",
    )
    return build_snapshot(list(SESSIONS), EFFECTIVE_DATE, instruments, observations, provenance, 3)


def _candles(start: datetime) -> list[Candle]:
    return [
        Candle(
            market=MarketId.IN_EQUITY,
            symbol="TEST",
            timeframe=Timeframe.D1,
            ts_open_utc=start + timedelta(days=index),
            open=Decimal(100 + index * 2),
            high=Decimal(101 + index * 2),
            low=Decimal(99 + index * 2),
            close=Decimal(100 + index * 2),
            volume=Decimal("1000"),
            source="test",
            ingest_ts=start,
        )
        for index in range(45)
    ]


def test_replays_every_selected_isin_not_a_fixed_symbol_list() -> None:
    snapshot = _snapshot()
    assert set(snapshot.selected_isins) == {ISIN_A, ISIN_B, ISIN_MISSING}

    start = datetime(2020, 1, 1, tzinfo=UTC)
    candles_by_isin = {ISIN_A: _candles(start), ISIN_B: _candles(start)}
    # ISIN_MISSING deliberately has no candles supplied.

    result = run_p1_daily_candidate_across_universe(
        "t1-donchian-n20-m10-k2-v1",
        snapshot,
        candles_by_isin,
        created_ts=start,
        quantity=Decimal("1"),
        profile=BacktestProfile(),
    )

    assert result.universe_version == "test-universe-v1"
    assert result.effective_date == EFFECTIVE_DATE
    assert set(result.results_by_isin) == {ISIN_A, ISIN_B}
    assert result.missing_isins == (ISIN_MISSING,)
    # Both real replays ran through the same shared engine as the pilot path.
    for replay in result.results_by_isin.values():
        assert replay.open_positions == 1


def test_missing_isin_is_reported_not_silently_dropped_or_zeroed() -> None:
    snapshot = _snapshot()
    start = datetime(2020, 1, 1, tzinfo=UTC)
    result = run_p1_daily_candidate_across_universe(
        "t1-donchian-n20-m10-k2-v1",
        snapshot,
        {},  # no candles supplied for anything
        created_ts=start,
        quantity=Decimal("1"),
        profile=BacktestProfile(),
    )
    assert result.results_by_isin == {}
    assert set(result.missing_isins) == {ISIN_A, ISIN_B, ISIN_MISSING}
