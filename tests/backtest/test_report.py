import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from trading.backtest.fills import BacktestProfile
from trading.backtest.report import write_phase1_report
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
