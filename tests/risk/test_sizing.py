from datetime import UTC, datetime
from decimal import Decimal

from trading.core.enums import BrainLabel
from trading.core.models import BrainVerdict
from trading.risk.sizing import compute_qty, floor_to_lot_size

TS = datetime(2026, 1, 1, tzinfo=UTC)


def _verdict(label: BrainLabel, multiplier: str) -> BrainVerdict:
    return BrainVerdict(
        signal_id="s1", label=label, size_multiplier=Decimal(multiplier), created_ts=TS
    )


def test_s1_baseline() -> None:
    qty = compute_qty(
        sleeve_equity=Decimal(1_000_000),
        risk_per_trade_pct=Decimal("0.5"),
        entry_ref=Decimal(2500),
        stop=Decimal(2450),
        max_position_value_pct=Decimal(100),
    )
    assert qty == Decimal(100)


def test_s2_brain_shrinks() -> None:
    qty = compute_qty(
        sleeve_equity=Decimal(1_000_000),
        risk_per_trade_pct=Decimal("0.5"),
        entry_ref=Decimal(2500),
        stop=Decimal(2450),
        max_position_value_pct=Decimal(100),
        brain_verdict=_verdict(BrainLabel.NEUTRAL, "0.6"),
    )
    assert qty == Decimal(60)


def test_s3_lot_rounding_down() -> None:
    qty = compute_qty(
        sleeve_equity=Decimal(1_000_000),
        risk_per_trade_pct=Decimal("0.5"),
        entry_ref=Decimal(2500),
        stop=Decimal(2450),
        max_position_value_pct=Decimal(100),
        lot_size=Decimal(7),
    )
    assert qty == Decimal(98)


def test_s4_rounds_to_zero() -> None:
    # TEST_SPEC_RISK.md's own S4 numbers (equity=10,000) give risk_budget=50,
    # distance=50 -> floor(50/50)=1, not 0 as that table states -- a
    # pre-existing arithmetic error in the P0 spec (flagged separately, see
    # ADR), not reproduced here. equity=9,000 gives budget=45 < distance=50,
    # which is the case the row is actually testing for ("rounds to zero").
    qty = compute_qty(
        sleeve_equity=Decimal(9_000),
        risk_per_trade_pct=Decimal("0.5"),
        entry_ref=Decimal(2500),
        stop=Decimal(2450),
        max_position_value_pct=Decimal(100),
    )
    assert qty == Decimal(0)


def test_s5_liquidity_cap_binds() -> None:
    qty = compute_qty(
        sleeve_equity=Decimal(1_000_000),
        risk_per_trade_pct=Decimal("0.5"),
        entry_ref=Decimal(2500),
        stop=Decimal(2450),
        max_position_value_pct=Decimal(100),
        liquidity_cap_qty=Decimal(40),
    )
    assert qty == Decimal(40)


def test_s6_never_rounds_up() -> None:
    qty = compute_qty(
        sleeve_equity=Decimal(999_000),
        risk_per_trade_pct=Decimal("0.1"),
        entry_ref=Decimal(100),
        stop=Decimal(50),
        max_position_value_pct=Decimal(100),
    )
    # risk_budget = 999, distance = 50 -> raw 19.98 -> must floor to 19, never 20.
    assert qty == Decimal(19)


def test_brain_veto_never_reaches_sizing_with_qty() -> None:
    # Veto is handled by the engine before sizing (see test_engine.py); this
    # module only guarantees never-round-up/never-negative given any multiplier.
    qty = compute_qty(
        sleeve_equity=Decimal(1_000_000),
        risk_per_trade_pct=Decimal("0.5"),
        entry_ref=Decimal(2500),
        stop=Decimal(2450),
        max_position_value_pct=Decimal(100),
        brain_verdict=_verdict(BrainLabel.VETO, "0"),
    )
    assert qty == Decimal(0)


def test_floor_to_lot_size_rejects_nonpositive_lot() -> None:
    import pytest

    with pytest.raises(ValueError):
        floor_to_lot_size(Decimal(10), Decimal(0))
