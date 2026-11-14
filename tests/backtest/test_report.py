import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from trading.backtest.fills import BacktestProfile
from trading.backtest.report import write_phase1_report, write_phase1_walk_forward_report
from trading.core.enums import MarketId, Timeframe
from trading.core.models import Candle


def test_phase1_report_is_reproducible_and_decimal_safe(tmp_path: Path) -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    candles = [
        Candle(
            market=MarketId.IN_EQUITY,
            symbol="TEST",
            timeframe=Timeframe.D1,
            ts_open_utc=start + timedelta(days=index),
            open=Decimal(value),
            high=Decimal(value) + Decimal("1"),
            low=Decimal(value) - Decimal("1"),
            close=Decimal(value),
            volume=Decimal("1000"),
            source="fixture",
            ingest_ts=start,
        )
        for index, value in enumerate(([10] * 20) + [20, 20, 5, 5])
    ]
    output = write_phase1_report(
        candles,
        output=tmp_path / "report.json",
        quantity=Decimal("1"),
        profile=BacktestProfile(),
        universe_id="fixture",
        data_status="synthetic_fixture",
    )
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["status"] == "research_only"
    assert report["coverage"]["bars"] == 24
    assert report["strategies"]["t1_donchian"]["equivalence_checked"] is True
    assert report["strategies"]["t1_donchian"]["trades"] == 1
    assert isinstance(report["strategies"]["t1_donchian"]["scorecard"]["total_pnl"], str)
    assert (
        report["strategies"]["t1_donchian"]["scorecard"]["expectancy_interval"]["block_size"] == 5
    )


def test_walk_forward_report_records_windows_and_equivalence(tmp_path: Path) -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    candles = [
        Candle(
            market=MarketId.IN_EQUITY,
            symbol="TEST",
            timeframe=Timeframe.D1,
            ts_open_utc=start + timedelta(days=index),
            open=Decimal("10"),
            high=Decimal("11"),
            low=Decimal("9"),
            close=Decimal("10"),
            volume=Decimal("1000"),
            source="fixture",
            ingest_ts=start,
        )
        for index in range(12)
    ]
    output = write_phase1_walk_forward_report(
        candles,
        output=tmp_path / "walk-forward.json",
        quantity=Decimal("1"),
        profile=BacktestProfile(),
        universe_id="fixture",
        data_status="synthetic_fixture",
        train_bars=4,
        test_bars=2,
        embargo_bars=1,
    )
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["validation"]["window_count"] == 3
    assert len(report["strategies"]["t1_donchian"]) == 3
    assert all(item["equivalence_checked"] for item in report["strategies"]["t1_donchian"])
    assert report["validation"]["label"] == "retrospective_walk_forward"
    assert report["validation"]["boundary_policy"] == "censor_open_positions_at_test_end"


def test_walk_forward_report_allows_a_test_window_ending_at_last_bar(tmp_path: Path) -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    candles = [
        Candle(
            market=MarketId.IN_EQUITY,
            symbol="TEST",
            timeframe=Timeframe.D1,
            ts_open_utc=start + timedelta(days=index),
            open=Decimal("10"),
            high=Decimal("11"),
            low=Decimal("9"),
            close=Decimal("10"),
            volume=Decimal("1000"),
            source="fixture",
            ingest_ts=start,
        )
        for index in range(6)
    ]
    output = write_phase1_walk_forward_report(
        candles,
        output=tmp_path / "exact-fit.json",
        quantity=Decimal("1"),
        profile=BacktestProfile(),
        universe_id="fixture",
        data_status="synthetic_fixture",
        train_bars=3,
        test_bars=2,
    )
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["validation"]["window_count"] == 1


def test_walk_forward_censors_open_trade_at_boundary(tmp_path: Path) -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)

    def make_candles(length: int) -> list[Candle]:
        closes = [10] * 21 + [13] * (length - 21)
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
                source="fixture",
                ingest_ts=start,
            )
            for index, value in enumerate(closes)
        ]

    def write_report(path: Path, length: int) -> dict[str, object]:
        output = write_phase1_walk_forward_report(
            make_candles(length),
            output=path,
            quantity=Decimal("1"),
            profile=BacktestProfile(),
            universe_id="fixture",
            data_status="synthetic_fixture",
            train_bars=20,
            test_bars=2,
        )
        return json.loads(output.read_text(encoding="utf-8"))

    short = write_report(tmp_path / "short.json", 23)
    extended = write_report(tmp_path / "extended.json", 25)
    short_t1 = short["strategies"]["t1_donchian"][0]
    extended_t1 = extended["strategies"]["t1_donchian"][0]
    assert short_t1["open_positions"] == 1
    assert short_t1["trades"] == 0
    assert short_t1["scorecard"]["total_pnl"] == "0"
    assert extended_t1["open_positions"] == short_t1["open_positions"]
    assert extended_t1["scorecard"] == short_t1["scorecard"]
