from datetime import UTC, datetime

from trading.adapters.upstox_history import UpstoxHistoryClient
from trading.core.enums import MarketId, Timeframe
from trading.storage.nse_currency_universe import CURRENCY_UNIVERSE, symbols


def test_universe_is_the_four_fixed_tenors() -> None:
    assert symbols() == ("USDINR", "EURINR", "GBPINR", "JPYINR")
    assert all(pair.market is MarketId.NSE_CURRENCY for pair in CURRENCY_UNIVERSE)


def test_existing_upstox_client_accepts_a_currency_instrument_key() -> None:
    """Proves no new adapter/HTTP client is needed: the same UpstoxHistoryClient
    round-trips a CDS_FO currency instrument key exactly like an NSE_EQ key --
    it only URL-encodes whatever key it is given."""
    calls: list[str] = []

    def fake_request(url: str, headers: dict[str, str]) -> bytes:
        calls.append(url)
        return (
            b'{"status":"success","data":{"candles":'
            b'[["2025-01-02T00:00:00+05:30",83.1,83.4,82.9,83.2,1000]]}}'
        )

    instrument_key = CURRENCY_UNIVERSE[0].instrument_key_prefix + "26JAN25FUT"
    candles = UpstoxHistoryClient(requester=fake_request).fetch(
        instrument_key,
        symbol="USDINR",
        market=MarketId.NSE_CURRENCY,
        timeframe=Timeframe.D1,
        to_date="2025-01-02",
        ingest_ts=datetime(2025, 1, 3, tzinfo=UTC),
    )
    assert len(candles) == 1
    assert candles[0].market is MarketId.NSE_CURRENCY
    assert "CDS_FO%7CUSDINR26JAN25FUT" in calls[0]
