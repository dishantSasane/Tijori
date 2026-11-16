from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from trading.core.enums import MarketId, Timeframe
from trading.core.models import Candle
from trading.strategies.p1_candidates import generate_p1_daily_signals
from trading.strategies.p1_catalog import P1_CANDIDATES, P1_CATALOG_VERSION, get_p1_candidate


def make_candles(closes: list[int]) -> list[Candle]:
    start = datetime(2020, 1, 1, tzinfo=UTC)
    return [
        Candle(
            market=MarketId.IN_EQUITY,
            symbol="TEST",
            timeframe=Timeframe.D1,
            ts_open_utc=start + timedelta(days=index),
            open=Decimal(value),
            high=Decimal(value + 1),
            low=Decimal(value - 1),
            close=Decimal(value),
            volume=Decimal("1000"),
            source="test",
            ingest_ts=start,
        )
        for index, value in enumerate(closes)
    ]


def test_p1_catalog_is_the_frozen_15_candidate_family() -> None:
    assert P1_CATALOG_VERSION == "p1-catalog-v3"
    assert len(P1_CANDIDATES) == 15
    assert sum(candidate.timeframe == "1d" for candidate in P1_CANDIDATES.values()) == 12
    assert sum(candidate.timeframe == "5m" for candidate in P1_CANDIDATES.values()) == 3
    assert {candidate.family for candidate in P1_CANDIDATES.values()} == {
        "T1",
        "T2",
        "T4",
        "T5",
        "T6",
    }
    specification = Path("docs/specs/P1_CANDIDATES.md").read_text()
    assert all(candidate_id in specification for candidate_id in P1_CANDIDATES)


def test_p1_catalog_freezes_each_variant_and_parameter_set() -> None:
    assert get_p1_candidate("t1-donchian-n20-m10-k2-v1").parameters == (
        ("entry_n", 20),
        ("exit_m", 10),
        ("atr_k", 2),
    )
    assert get_p1_candidate("t2-ema20-100-adx25-v1").parameters == (
        ("fast_ema", 20),
        ("slow_ema", 100),
        ("adx_threshold", 25),
        ("atr_k", 2),
    )
    assert get_p1_candidate("t5-orb-m15-v1").parameters[-1] == ("target_multiple", 1.5)
    assert get_p1_candidate("t6-bollinger20-25-v1").parameters[1] == ("band_width", 2.5)


def test_p1_catalog_rejects_unknown_candidate_id() -> None:
    with pytest.raises(ValueError, match="unknown P1 candidate"):
        get_p1_candidate("unregistered-candidate")


def test_every_daily_candidate_id_generates_signals_from_its_frozen_parameters() -> None:
    bars = make_candles([100] * 220)
    for candidate in P1_CANDIDATES.values():
        if candidate.timeframe == "1d":
            assert (
                generate_p1_daily_signals(
                    candidate.candidate_id,
                    bars,
                    created_ts=bars[-1].ingest_ts,
                )
                == []
            )


def test_daily_candidate_dispatch_uses_variant_lookback() -> None:
    bars = make_candles([100 + 2 * index for index in range(50)])
    signals = generate_p1_daily_signals(
        "t1-donchian-n20-m10-k2-v1",
        bars,
        created_ts=bars[0].ingest_ts,
    )
    assert signals
    assert signals[0].bar_ts_utc == bars[20].ts_open_utc
    assert signals[0].strategy_version == "t1-donchian-n20-m10-k2-v1"


def test_daily_dispatch_rejects_intraday_candidate() -> None:
    bars = make_candles([100, 101])
    with pytest.raises(ValueError, match="daily P1 candidate"):
        generate_p1_daily_signals(
            "t5-orb-m1-v1",
            bars,
            created_ts=bars[0].ingest_ts,
        )


def test_daily_candidate_dispatch_known_answers_for_t2_t4_and_t6() -> None:
    start = datetime(2020, 1, 1, tzinfo=UTC)
    t2_bars = make_candles([200 - index for index in range(60)] + [140 + 3 * i for i in range(80)])
    t2 = generate_p1_daily_signals("t2-ema20-50-adx25-v1", t2_bars, created_ts=start)
    assert t2
    assert all(signal.strategy_version == "t2-ema20-50-adx25-v1" for signal in t2)

    t4_bars = make_candles([100] * 205 + [120] * 10 + [115, 110])
    t4 = generate_p1_daily_signals("t4-rsi2-10-atr25-v1", t4_bars, created_ts=start)
    assert t4
    assert t4[-1].bar_ts_utc == t4_bars[-1].ts_open_utc

    t6_bars = make_candles([100] * 205 + [99])
    t6 = generate_p1_daily_signals("t6-bollinger20-2-v1", t6_bars, created_ts=start)
    assert t6
    assert t6[-1].bar_ts_utc == t6_bars[-1].ts_open_utc


@pytest.mark.parametrize("duplicate", [False, True])
def test_daily_dispatch_rejects_nonincreasing_or_duplicate_timestamps(duplicate: bool) -> None:
    bars = make_candles([100, 101, 102])
    if duplicate:
        bars[1] = bars[1].model_copy(update={"ts_open_utc": bars[0].ts_open_utc})
    else:
        bars[1], bars[2] = bars[2], bars[1]
    with pytest.raises(ValueError, match="strictly increasing and unique"):
        generate_p1_daily_signals(
            "t6-bollinger20-2-v1",
            bars,
            created_ts=bars[0].ingest_ts,
        )
