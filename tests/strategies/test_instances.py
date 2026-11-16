from datetime import UTC, datetime
from decimal import Decimal

from trading.core.enums import MarketId, Mode, ReasonCode, Route
from trading.core.models import RiskDecision
from trading.risk.engine import ModeGate
from trading.storage.mcx_universe import symbols as mcx_symbols
from trading.storage.nse_currency_universe import symbols as currency_symbols
from trading.strategies.instances import (
    MEMECOIN_TIER_A,
    crypto_instances,
    mcx_instances,
    memecoin_instances,
    nse_currency_instances,
    us_equity_instances,
)


def test_crypto_instances_cover_tier_a_with_both_rules() -> None:
    instances = crypto_instances()
    symbols = {i.symbol for i in instances}
    assert symbols == {"BTC/USDT", "ETH/USDT"}
    assert all(i.market == MarketId.CRYPTO for i in instances)
    assert {i.strategy_id for i in instances} == {"t1_donchian", "t4_rsi_pullback"}


def test_us_equity_instances_cover_tier_a_with_both_rules() -> None:
    instances = us_equity_instances()
    symbols = {i.symbol for i in instances}
    # GLD/BND are P8's "gold/bond ETF filter" item -- just two more Tier-A
    # symbols for the same existing rules (ADR-0034).
    assert symbols == {"AAPL", "MSFT", "QQQ", "GLD", "BND"}
    assert all(i.market == MarketId.US_EQUITY for i in instances)
    assert {i.strategy_id for i in instances} == {"t1_donchian", "t4_rsi_pullback"}


def test_mcx_instances_cover_fixed_universe_with_both_rules() -> None:
    instances = mcx_instances()
    symbols = {i.symbol for i in instances}
    assert symbols == set(mcx_symbols())
    assert all(i.market == MarketId.MCX_COMMODITY for i in instances)
    assert all(i.sleeve == "commodities" for i in instances)
    assert {i.strategy_id for i in instances} == {"t1_donchian", "t4_rsi_pullback"}


def test_nse_currency_instances_cover_fixed_universe_with_both_rules() -> None:
    instances = nse_currency_instances()
    symbols = {i.symbol for i in instances}
    assert symbols == set(currency_symbols())
    assert all(i.market == MarketId.NSE_CURRENCY for i in instances)
    assert {i.strategy_id for i in instances} == {"t1_donchian", "t4_rsi_pullback"}


def test_memecoin_instances_cover_tier_a_with_both_rules() -> None:
    instances = memecoin_instances()
    symbols = {i.symbol for i in instances}
    assert symbols == set(MEMECOIN_TIER_A)
    assert all(i.market == MarketId.MEMECOIN for i in instances)
    assert all(i.sleeve == "memecoin" for i in instances)


def test_memecoin_sleeve_cannot_go_live_even_with_auto_mode_and_approval() -> None:
    """The hard gate from ADR-0034: no config/human-action combination can
    route a memecoin order anywhere but paper. This is the test the task
    brief asked for 'proving this gate holds'.
    """
    allowed = RiskDecision(
        signal_id="s1",
        allowed=True,
        qty=Decimal(10),
        reason_codes=(ReasonCode.OK,),
        created_ts=datetime(2026, 1, 1, tzinfo=UTC),
    )
    for mode in (Mode.PAPER, Mode.APPROVAL, Mode.AUTO):
        for human_action in (None, "approve", "paper_test", "reject"):
            route = ModeGate.route(allowed, mode, human_action, sleeve="memecoin")
            assert route == Route.PAPER, (mode, human_action, route)
