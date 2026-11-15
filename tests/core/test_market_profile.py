from pathlib import Path

import pytest

from trading.core.enums import MarketId
from trading.core.market_profile import load_market_profile

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


def test_crypto_is_24x7() -> None:
    profile = load_market_profile(MarketId.CRYPTO, CONFIG_DIR)
    assert profile.is_24x7 is True
    assert profile.session_open is None


def test_us_equity_has_a_session() -> None:
    profile = load_market_profile(MarketId.US_EQUITY, CONFIG_DIR)
    assert profile.is_24x7 is False
    assert profile.session_open == "09:30"
    assert profile.calendar == "XNYS"


def test_india_equity_has_a_session() -> None:
    profile = load_market_profile(MarketId.IN_EQUITY, CONFIG_DIR)
    assert profile.is_24x7 is False
    assert profile.timezone == "Asia/Kolkata"


def test_unknown_market_raises() -> None:
    with pytest.raises(KeyError):
        load_market_profile(MarketId.IN_OPTIONS, CONFIG_DIR)
