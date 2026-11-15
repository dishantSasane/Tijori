from datetime import date
from decimal import Decimal

from trading.storage.crypto_universe import (
    SymbolSnapshot,
    crypto_sleeve_members,
    memecoin_sleeve_members,
)

AS_OF = date(2026, 1, 1)


def _snap(symbol: str, volume: str, listed_since: date, memecoin: bool = False) -> SymbolSnapshot:
    return SymbolSnapshot(
        symbol=symbol,
        quote_volume_24h_usd=Decimal(volume),
        listed_since=listed_since,
        is_memecoin_tagged=memecoin,
    )


def test_btc_eth_always_included_even_if_below_floor() -> None:
    snapshots = [
        _snap("BTCUSDT", "1", date(2017, 1, 1)),
        _snap("ETHUSDT", "1", date(2017, 1, 1)),
    ]
    members = crypto_sleeve_members(snapshots, as_of=AS_OF)
    assert members == ["BTCUSDT", "ETHUSDT"]


def test_low_liquidity_altcoin_excluded() -> None:
    snapshots = [
        _snap("BTCUSDT", "1", date(2017, 1, 1)),
        _snap("TINYUSDT", "100", date(2024, 1, 1)),
    ]
    members = crypto_sleeve_members(snapshots, as_of=AS_OF)
    assert "TINYUSDT" not in members


def test_memecoin_tagged_symbol_excluded_from_general_sleeve() -> None:
    snapshots = [
        _snap("DOGEUSDT", "10000000", date(2020, 1, 1), memecoin=True),
    ]
    assert crypto_sleeve_members(snapshots, as_of=AS_OF) == []


def test_memecoin_sleeve_excludes_too_young_listing() -> None:
    snapshots = [
        _snap("NEWMEMEUSDT", "5000000", AS_OF, memecoin=True),
    ]
    assert memecoin_sleeve_members(snapshots, as_of=AS_OF) == []


def test_memecoin_sleeve_includes_old_liquid_tagged_symbol() -> None:
    snapshots = [
        _snap("OLDMEMEUSDT", "5000000", date(2020, 1, 1), memecoin=True),
    ]
    assert memecoin_sleeve_members(snapshots, as_of=AS_OF) == ["OLDMEMEUSDT"]


def test_top_n_cap_applied() -> None:
    snapshots = [_snap("BTCUSDT", "1", date(2017, 1, 1))]
    for i in range(30):
        snapshots.append(_snap(f"A{i}USDT", str(100_000_000 - i), date(2020, 1, 1)))
    members = crypto_sleeve_members(snapshots, as_of=AS_OF)
    # BTC always-include + top 20 by volume
    assert len(members) == 21
    assert "BTCUSDT" in members
