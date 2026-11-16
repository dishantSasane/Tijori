from datetime import date
from decimal import Decimal

from trading.storage.us_equity_universe import (
    SP500MembershipInterval,
    USEquitySnapshot,
    sp500_benchmark_members,
    us_equity_universe_members,
)


def snapshot(symbol: str, dollar_volume: str, *, is_otc: bool = False) -> USEquitySnapshot:
    return USEquitySnapshot(
        symbol=symbol,
        trailing_dollar_volume_usd=Decimal(dollar_volume),
        is_otc=is_otc,
        listed_since=date(2010, 1, 1),
    )


def test_universe_ranks_by_dollar_volume_and_excludes_otc() -> None:
    snapshots = [
        snapshot("AAPL", "50000000"),
        snapshot("MSFT", "40000000"),
        snapshot("PNKSHEET", "100000000", is_otc=True),
        snapshot("THIN", "1000"),  # below liquidity floor
    ]
    members = us_equity_universe_members(snapshots, as_of=date(2024, 1, 1))
    assert members == sorted(["AAPL", "MSFT"])


def test_universe_excludes_not_yet_listed_symbol() -> None:
    future_listed = USEquitySnapshot(
        symbol="NEWCO",
        trailing_dollar_volume_usd=Decimal("50000000"),
        is_otc=False,
        listed_since=date(2030, 1, 1),
    )
    members = us_equity_universe_members([future_listed], as_of=date(2024, 1, 1))
    assert members == []


def test_sp500_benchmark_membership_is_point_in_time() -> None:
    intervals = [
        SP500MembershipInterval(
            symbol="AAPL",
            company_name_at_time="Apple Inc.",
            effective_from=date(1982, 11, 30),
            effective_to=None,
            source_ref="wikipedia-list-of-sp500-companies",
        ),
        SP500MembershipInterval(
            symbol="GONE",
            company_name_at_time="Removed Co",
            effective_from=date(2000, 1, 1),
            effective_to=date(2020, 1, 1),
            source_ref="wikipedia-list-of-sp500-companies",
        ),
    ]
    assert sp500_benchmark_members(intervals, as_of=date(2024, 1, 1)) == ["AAPL"]
    assert sp500_benchmark_members(intervals, as_of=date(2010, 1, 1)) == ["AAPL", "GONE"]
