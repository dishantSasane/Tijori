from datetime import UTC, datetime

from trading.adapters.upstox_history import UpstoxHistoryClient
from trading.core.enums import MarketId, Timeframe
from trading.storage.mcx_universe import MCX_UNIVERSE, symbols


def test_universe_is_the_five_fixed_commodities() -> None:
    assert symbols() == ("GOLD", "SILVER", "CRUDEOIL", "NATURALGAS", "COPPER")
    assert all(c.market is MarketId.MCX_COMMODITY for c in MCX_UNIVERSE)


def test_existing_upstox_client_accepts_an_mcx_instrument_key() -> None:
    """Proves no new adapter/HTTP client is needed: the same UpstoxHistoryClient
    round-trips an MCX_FO instrument key exactly like NSE_EQ/CDS_FO keys -- it
    only URL-encodes whatever key it is given."""
    calls: list[str] = []

    def fake_request(url: str, headers: dict[str, str]) -> bytes:
        calls.append(url)
        return (
            b'{"status":"success","data":{"candles":'
            b'[["2025-01-02T00:00:00+05:30",62000,62500,61800,62300,1000]]}}'
        )

    instrument_key = MCX_UNIVERSE[0].instrument_key_prefix + "25FEB25FUT"
    candles = UpstoxHistoryClient(requester=fake_request).fetch(
        instrument_key,
        symbol="GOLD",
        market=MarketId.MCX_COMMODITY,
        timeframe=Timeframe.D1,
        to_date="2025-01-02",
        ingest_ts=datetime(2025, 1, 3, tzinfo=UTC),
    )
    assert len(candles) == 1
    assert candles[0].market is MarketId.MCX_COMMODITY
    assert "MCX_FO%7CGOLD25FEB25FUT" in calls[0]
