from trading.core.enums import MarketId
from trading.strategies.instances import crypto_instances, us_equity_instances


def test_crypto_instances_cover_tier_a_with_both_rules() -> None:
    instances = crypto_instances()
    symbols = {i.symbol for i in instances}
    assert symbols == {"BTC/USDT", "ETH/USDT"}
    assert all(i.market == MarketId.CRYPTO for i in instances)
    assert {i.strategy_id for i in instances} == {"t1_donchian", "t4_rsi_pullback"}


def test_us_equity_instances_cover_tier_a_with_both_rules() -> None:
    instances = us_equity_instances()
    symbols = {i.symbol for i in instances}
    assert symbols == {"AAPL", "MSFT", "QQQ"}
    assert all(i.market == MarketId.US_EQUITY for i in instances)
    assert {i.strategy_id for i in instances} == {"t1_donchian", "t4_rsi_pullback"}
