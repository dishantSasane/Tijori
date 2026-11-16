from decimal import Decimal

from trading.reporting.accounts import sleeve_balances
from trading.storage.state_db import connect


def test_sleeve_balances_computes_cost_basis_and_available_capital() -> None:
    conn = connect(":memory:")
    conn.execute(
        "INSERT INTO positions (market, symbol, sleeve, signal_id, qty, avg_price, opened_ts, "
        "stop_price, target_price, entry_ref, approved_risk, ledger_source) VALUES "
        "('crypto', 'BTC/USDT', 'crypto', 'sig1', '0.1', '60000', '2026-01-01T00:00:00+00:00', "
        "'58000', NULL, '60000', '200', 'live')"
    )
    conn.commit()

    balances = sleeve_balances(
        conn,
        sleeve_capital={"crypto": Decimal("250000"), "us_equity": Decimal("200000")},
    )

    by_sleeve = {b.sleeve: b for b in balances}
    crypto = by_sleeve["crypto"]
    assert crypto.open_position_count == 1
    assert crypto.cost_basis_in_open_positions == Decimal("6000.0")
    assert crypto.capital_available == Decimal("244000.0")

    us = by_sleeve["us_equity"]
    assert us.open_position_count == 0
    assert us.capital_available == Decimal("200000")
