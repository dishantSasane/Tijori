from datetime import date

import pytest

from trading.core.enums import MarketId
from trading.storage.crypto_integrity import ListingEvent, ListingRegistry


def _event(event_id: str, symbol: str, kind: str, day: date, **kwargs: object) -> ListingEvent:
    return ListingEvent(
        event_id=event_id,
        market=MarketId.CRYPTO,
        exchange="binance",
        symbol=symbol,
        kind=kind,  # type: ignore[arg-type]
        effective_date=day,
        source_ref="https://example.test/notice",
        **kwargs,  # type: ignore[arg-type]
    )


def test_known_answer_delisted_symbol_is_not_tradeable_after() -> None:
    registry = ListingRegistry(
        exchange="binance",
        events=(
            _event("e1", "LUNAUSDT", "listed", date(2021, 1, 1)),
            _event("e2", "LUNAUSDT", "delisted", date(2022, 5, 30)),
        ),
    )
    assert registry.is_tradeable("LUNAUSDT", date(2022, 1, 1)) is True
    assert registry.is_tradeable("LUNAUSDT", date(2022, 6, 1)) is False


def test_rebrand_requires_successor_symbol() -> None:
    with pytest.raises(ValueError, match="successor_symbol"):
        _event("e1", "OLDUSDT", "rebranded", date(2022, 1, 1))


def test_duplicate_listed_without_close_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate 'listed'"):
        ListingRegistry(
            exchange="binance",
            events=(
                _event("e1", "XUSDT", "listed", date(2021, 1, 1)),
                _event("e2", "XUSDT", "listed", date(2021, 6, 1)),
            ),
        )


def test_flags_undeclared_gap_as_possible_silent_delist() -> None:
    registry = ListingRegistry(
        exchange="binance",
        events=(_event("e1", "YUSDT", "listed", date(2021, 1, 1)),),
    )
    gaps = registry.flag_undeclared_gaps(
        "YUSDT", [date(2022, 1, 1), date(2022, 1, 2), date(2022, 2, 1)]
    )
    assert gaps == [(date(2022, 1, 2), date(2022, 2, 1))]


def test_declared_delist_gap_is_not_flagged() -> None:
    registry = ListingRegistry(
        exchange="binance",
        events=(
            _event("e1", "ZUSDT", "listed", date(2021, 1, 1)),
            _event("e2", "ZUSDT", "delisted", date(2022, 1, 2)),
        ),
    )
    gaps = registry.flag_undeclared_gaps(
        "ZUSDT", [date(2022, 1, 1), date(2022, 1, 2), date(2022, 2, 1)]
    )
    assert gaps == []
