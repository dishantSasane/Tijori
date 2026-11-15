import json
from datetime import date
from pathlib import Path

import pytest

from trading.storage.p1_pilot_coverage import (
    RawUpstoxArchiveError,
    audit_session_coverage,
    load_raw_upstox_daily_dates,
)


def test_common_sessions_is_the_intersection_across_all_symbols() -> None:
    audit = audit_session_coverage(
        {
            "A": frozenset({date(2020, 1, 1), date(2020, 1, 2), date(2020, 1, 3)}),
            "B": frozenset({date(2020, 1, 1), date(2020, 1, 2)}),
            "C": frozenset({date(2020, 1, 1), date(2020, 1, 2), date(2020, 1, 4)}),
        }
    )
    assert audit.common_sessions == frozenset({date(2020, 1, 1), date(2020, 1, 2)})


def test_symbol_only_dates_are_flagged_per_symbol_not_merged() -> None:
    audit = audit_session_coverage(
        {
            "A": frozenset({date(2020, 1, 1), date(2020, 1, 3)}),  # extra: 1/3
            "B": frozenset({date(2020, 1, 1)}),
        }
    )
    assert audit.symbol_only_dates["A"] == frozenset({date(2020, 1, 3)})
    assert audit.symbol_only_dates["B"] == frozenset()
    assert audit.has_discrepancies is True


def test_no_discrepancies_when_every_symbol_matches() -> None:
    same = frozenset({date(2020, 1, 1), date(2020, 1, 2)})
    audit = audit_session_coverage({"A": same, "B": same})
    assert audit.common_sessions == same
    assert audit.has_discrepancies is False
    assert all(not dates for dates in audit.symbol_only_dates.values())


def test_rejects_fewer_than_two_symbols() -> None:
    with pytest.raises(ValueError, match="at least two"):
        audit_session_coverage({"A": frozenset({date(2020, 1, 1)})})


def test_rejects_a_symbol_with_no_sessions() -> None:
    with pytest.raises(ValueError, match="at least one session"):
        audit_session_coverage({"A": frozenset({date(2020, 1, 1)}), "B": frozenset()})


def test_load_raw_upstox_daily_dates_known_answer(tmp_path: Path) -> None:
    payload = {
        "status": "success",
        "data": {
            "candles": [
                ["2015-12-31T00:00:00+05:30", 1, 2, 1, 1.5, 100, 0],
                ["2015-12-30T00:00:00+05:30", 1, 2, 1, 1.5, 100, 0],
            ]
        },
    }
    path = tmp_path / "sample.json"
    path.write_text(json.dumps(payload))
    assert load_raw_upstox_daily_dates(path) == frozenset({date(2015, 12, 31), date(2015, 12, 30)})


def test_load_raw_upstox_daily_dates_rejects_non_success(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"status": "error", "data": {}}))
    with pytest.raises(RawUpstoxArchiveError):
        load_raw_upstox_daily_dates(path)


def test_load_raw_upstox_daily_dates_rejects_empty_candles(tmp_path: Path) -> None:
    path = tmp_path / "empty.json"
    path.write_text(json.dumps({"status": "success", "data": {"candles": []}}))
    with pytest.raises(RawUpstoxArchiveError):
        load_raw_upstox_daily_dates(path)
