"""Known-answer test for MCX roll adjustment.

Prices are illustrative (not fetched live data) but shaped like a real MCX
gold-futures roll: the far contract trades at a premium to the near
contract (normal contango from cost-of-carry), so naively concatenating raw
closes across the roll date would show a fake multi-hundred-rupee jump.
This test proves the back-adjusted continuous series has none.
"""

from datetime import UTC, datetime
from decimal import Decimal

from trading.adapters.mcx_roll import ContractLeg, MCXRollError, build_continuous_series
from trading.core.enums import MarketId, Timeframe
from trading.core.models import Candle


def _candle(day: int, close: Decimal) -> Candle:
    return Candle(
        market=MarketId.MCX_COMMODITY,
        symbol="GOLD",
        timeframe=Timeframe.D1,
        ts_open_utc=datetime(2025, 1, day, tzinfo=UTC),
        open=close,
        high=close,
        low=close,
        close=close,
        volume=Decimal("100"),
        source="upstox",
        ingest_ts=datetime(2025, 1, day, tzinfo=UTC),
    )


def test_continuous_series_has_no_fake_jump_at_the_roll() -> None:
    # Near-month (JAN) contract: closes 62000 -> 62200 -> 62300 (expiring).
    near = ContractLeg(
        instrument_key="MCX_FO|GOLD25JANFUT",
        candles=(
            _candle(1, Decimal("62000")),
            _candle(2, Decimal("62200")),
            _candle(3, Decimal("62300")),
        ),
    )
    # Far-month (FEB) contract trades at a real contango premium: its first
    # printed close (62600) is ~300 higher than JAN's last close (62300) on
    # the very next session -- a real price difference, not noise.
    far = ContractLeg(
        instrument_key="MCX_FO|GOLD25FEBFUT",
        candles=(_candle(4, Decimal("62600")), _candle(5, Decimal("62900"))),
    )

    # Sanity check: naive concatenation of raw closes WOULD jump by 300.
    raw_closes = [c.close for c in near.candles] + [c.close for c in far.candles]
    assert raw_closes[3] - raw_closes[2] == Decimal("300")

    continuous = build_continuous_series([near, far])

    assert [c.close for c in continuous[-2:]] == [Decimal("62600"), Decimal("62900")]
    # The far leg is unadjusted (most recent); the near leg is scaled up so
    # its last close lines up with the far leg's first close (division
    # rounding means "equal to many decimal places", not bit-exact).
    roll_gap = abs(continuous[3].close - continuous[2].close)
    assert roll_gap < Decimal("0.001")
    # No jump anywhere across the whole stitched series.
    jumps = [continuous[i + 1].close - continuous[i].close for i in range(len(continuous) - 1)]
    assert all(j >= Decimal("-0.001") for j in jumps)
    # Original per-leg raw data is untouched (immutability, no silent mutation).
    assert near.candles[-1].close == Decimal("62300")


def test_rejects_empty_legs() -> None:
    try:
        build_continuous_series([])
    except MCXRollError:
        pass
    else:
        raise AssertionError("expected MCXRollError")


if __name__ == "__main__":
    test_continuous_series_has_no_fake_jump_at_the_roll()
    test_rejects_empty_legs()
    print("ok")
