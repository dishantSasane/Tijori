"""Blind contract tests for docs/specs/RESEARCH_UNIVERSE.md.

The spec names build_snapshot and MonthlyUniverseSnapshot but does not name
the input models. These tests propose ResearchInstrument, TurnoverObservation,
and UniverseProvenance for the normalized Pydantic inputs. No source-specific
file fields are assumed.
"""

from datetime import date, timedelta
from decimal import Decimal, localcontext

import pytest

from trading.storage.research_universe import (
    MonthlyUniverseSnapshot,
    ResearchInstrument,
    TurnoverObservation,
    UniverseProvenance,
    build_snapshot,
)


def isin(number: int) -> str:
    """Generate synthetic, checksum-valid Indian ISINs."""
    base = f"IN{number:09d}"
    digits = "".join(str(ord(c) - 55) if c.isalpha() else c for c in base)
    for check in range(10):
        full = digits + str(check)
        total = sum(
            sum(divmod(int(char) * (2 if offset % 2 else 1), 10))
            for offset, char in enumerate(reversed(full))
        )
        if total % 10 == 0:
            return base + str(check)
    raise AssertionError("no check digit")


def exchange_sessions() -> list[date]:
    # Synthetic calendar: weekdays are sessions; July 1 is a Monday.
    start, end = date(2024, 3, 1), date(2024, 7, 2)
    return [
        start + timedelta(days=i)
        for i in range((end - start).days + 1)
        if (start + timedelta(days=i)).weekday() < 5
    ]


EFFECTIVE = date(2024, 7, 1)
SESSIONS = exchange_sessions()
AS_OF = date(2024, 6, 28)
LOOKBACK = [day for day in SESSIONS if day <= AS_OF][-60:]
PROVENANCE = {
    "universe_version": "synthetic-v1",
    "eligible_set_rule_version": "synthetic-rule-v1",
    "source_reference": "synthetic-source",
    "licence_reference": "synthetic-licence",
    "raw_files": [{"identifier": "synthetic-file", "checksum": "sha256:synthetic"}],
    "parser_version": "synthetic-parser-v1",
}


def instrument(number: int, **changes: object) -> dict:
    return {
        "isin": isin(number),
        "active_as_of": True,
        "eligible": True,
        "verified_history_start": LOOKBACK[0],
        **changes,
    }


def rows(number: int, values: list[int] | None = None) -> list[dict]:
    values = values if values is not None else [100] * 60
    return [
        {
            "session_date": day,
            "isin": isin(number),
            "turnover_inr": Decimal(value),
            "explicit_zero": value == 0,
        }
        for day, value in zip(LOOKBACK, values, strict=True)
    ]


def snapshot(
    instruments: list[dict], observations: list[dict], *, pad: bool = True, **changes: object
) -> dict:
    # The ordinary examples have enough eligible instruments to satisfy K=50.
    # Give fillers zero turnover so they cannot displace a positive candidate.
    if pad:
        instruments = instruments + [instrument(n) for n in range(1000, 1049)]
        observations = observations + [row for n in range(1000, 1049) for row in rows(n, [0] * 60)]
    arguments = {
        "sessions": SESSIONS,
        "effective_date": EFFECTIVE,
        "instruments": [ResearchInstrument.model_validate(item) for item in instruments],
        "observations": [TurnoverObservation.model_validate(item) for item in observations],
        "provenance": UniverseProvenance.model_validate(PROVENANCE),
        "k": 50,
        **changes,
    }
    result = build_snapshot(**arguments)
    assert isinstance(result, MonthlyUniverseSnapshot)
    return result.model_dump(mode="python")


def test_trailing_sessions_and_even_sample_median() -> None:
    observations = rows(1, list(range(1, 61)))
    observations += [
        {**observations[0], "session_date": SESSIONS[0], "turnover_inr": Decimal(99999)},
        {**observations[0], "session_date": EFFECTIVE, "turnover_inr": Decimal(99999)},
    ]
    result = snapshot([instrument(1)], observations)
    assert list(result["lookback_sessions"]) == LOOKBACK
    assert result["ranked_candidates"][0] == {
        "isin": isin(1),
        "median_turnover_inr": Decimal("30.5"),
    }


def test_missing_observation_is_an_error_not_a_zero() -> None:
    with pytest.raises(ValueError):
        snapshot([instrument(1)], rows(1)[:-1])


def test_instrument_with_unresolved_gap_is_excluded_not_a_whole_snapshot_failure() -> None:
    """A gap on one otherwise-eligible instrument must exclude only that
    instrument -- not abort every other instrument's ranking. This is the
    real-world case (an illiquid name's genuine multi-session trading halt)
    that made a full ~2,763-instrument run impossible before this fix.
    """
    result = snapshot(
        [instrument(1), instrument(2)],
        rows(1)[:-1] + rows(2),  # instrument 1 is missing its last session
    )
    assert isin(1) not in result["selected_isins"]
    assert isin(2) in result["selected_isins"]
    gap_exclusions = [item for item in result["exclusions"] if item["isin"] == isin(1)]
    assert len(gap_exclusions) == 1
    assert gap_exclusions[0]["reason"] == "unresolved_data_gap_in_lookback_window"


def test_verified_short_history_is_excluded_with_reason() -> None:
    result = snapshot(
        [instrument(1, verified_history_start=LOOKBACK[1]), instrument(2)],
        rows(1)[1:] + rows(2),
    )
    assert isin(1) not in result["selected_isins"]
    assert any(item["isin"] == isin(1) and item["reason"] for item in result["exclusions"])


def test_explicit_zero_is_a_real_observation_in_the_median() -> None:
    result = snapshot([instrument(1)], rows(1, [0] * 31 + [100] * 29))
    assert result["ranked_candidates"][0]["median_turnover_inr"] == 0


def test_median_ranking_is_independent_of_decimal_context_precision() -> None:
    instruments = [instrument(1), instrument(2)]
    observations = rows(1, [100000000000000001] * 60) + rows(2, [100000000000000000] * 60)
    with localcontext() as context:
        context.prec = 3
        result = snapshot(instruments, observations)
    assert result["selected_isins"][:2] == (isin(1), isin(2))


def test_unconfirmed_zero_is_not_silently_accepted() -> None:
    observations = rows(1, [0] + [100] * 59)
    observations[0]["explicit_zero"] = False
    with pytest.raises(ValueError):
        snapshot([instrument(1)], observations)


def test_only_active_eligible_isins_are_selected() -> None:
    result = snapshot(
        [instrument(1), instrument(2, active_as_of=False), instrument(3, eligible=False)],
        rows(1) + rows(2) + rows(3),
    )
    assert result["selected_isins"][0] == isin(1)
    assert isin(2) not in result["selected_isins"]
    assert isin(3) not in result["selected_isins"]
    assert {item["isin"] for item in result["exclusions"]} >= {isin(2), isin(3)}


def test_monthly_dates_use_previous_session_and_ignore_future_values() -> None:
    observations = rows(1) + rows(2, [99] * 60)
    observations += [
        {**rows(2)[0], "session_date": EFFECTIVE, "turnover_inr": Decimal(100000)},
        {**rows(2)[0], "session_date": date(2024, 7, 2), "turnover_inr": Decimal(100000)},
    ]
    result = snapshot([instrument(1), instrument(2)], observations)
    assert result["as_of_date"] == AS_OF
    assert result["effective_date"] == EFFECTIVE
    assert list(result["selected_isins"][:2]) == [isin(1), isin(2)]


def test_nonfirst_monthly_session_is_rejected() -> None:
    with pytest.raises(ValueError):
        snapshot([instrument(1)], rows(1), effective_date=date(2024, 7, 2))


@pytest.mark.parametrize("bad_k", [True, 50.0, 0, -1])
def test_k_must_be_a_positive_integer(bad_k: object) -> None:
    with pytest.raises(ValueError):
        snapshot([instrument(1)], rows(1), k=bad_k)  # type: ignore[arg-type]


def test_verified_history_may_start_before_supplied_calendar() -> None:
    result = snapshot([instrument(1, verified_history_start=date(2000, 1, 1))], rows(1))
    assert result["selected_isins"][0] == isin(1)


def test_first_session_after_a_month_start_holiday_uses_previous_session() -> None:
    calendar = [day for day in SESSIONS if day != EFFECTIVE]
    result = snapshot([instrument(1)], rows(1), sessions=calendar, effective_date=date(2024, 7, 2))
    assert result["effective_date"] == date(2024, 7, 2)
    assert result["as_of_date"] == AS_OF
    assert list(result["lookback_sessions"]) == LOOKBACK


def test_effective_date_must_be_a_session() -> None:
    with pytest.raises(ValueError):
        snapshot([instrument(1)], rows(1), effective_date=date(2024, 7, 6))


def test_ties_are_ordered_by_isin_independently_of_input_order() -> None:
    instruments = [instrument(3), instrument(1), instrument(2)]
    observations = rows(3) + rows(1) + rows(2)
    expected = sorted([isin(1), isin(2), isin(3)])
    assert list(snapshot(instruments, observations)["selected_isins"][:3]) == expected
    assert list(snapshot(instruments[::-1], observations[::-1])["selected_isins"][:3]) == expected


@pytest.mark.parametrize("k", [50, 100])
def test_top_k_bounds_and_rank_order(k: int) -> None:
    instruments = [instrument(n) for n in range(1, 106)]
    observations = [row for n in range(1, 106) for row in rows(n, [n] * 60)]
    result = snapshot(instruments, observations, k=k, pad=False)
    assert list(result["selected_isins"]) == [isin(n) for n in range(105, 105 - k, -1)]
    assert len(result["ranked_candidates"]) == 105


@pytest.mark.parametrize("k", [50, 100])
def test_fewer_than_k_candidates_blocks_snapshot(k: int) -> None:
    instruments = [instrument(n) for n in range(1, k)]
    observations = [row for n in range(1, k) for row in rows(n)]
    with pytest.raises(ValueError):
        snapshot(instruments, observations, k=k, pad=False)


def test_unknown_instrument_class_blocks_snapshot() -> None:
    with pytest.raises(ValueError):
        snapshot([instrument(1, eligible=None)], rows(1))


def test_observation_for_unknown_isin_blocks_snapshot() -> None:
    with pytest.raises(ValueError):
        snapshot([instrument(1)], rows(1) + rows(2))


def test_duplicate_session_isin_blocks_snapshot() -> None:
    observations = rows(1)
    with pytest.raises(ValueError):
        snapshot([instrument(1)], observations + [observations[0].copy()])


def test_duplicate_instrument_identity_blocks_snapshot() -> None:
    with pytest.raises(ValueError):
        snapshot([instrument(1), instrument(1)], rows(1))


@pytest.mark.parametrize("bad_isin", ["NOT-AN-ISIN", "IN0000000010", ""])
def test_malformed_isin_blocks_snapshot(bad_isin: str) -> None:
    with pytest.raises(ValueError):
        snapshot([instrument(1, isin=bad_isin)], rows(1))


def test_snapshot_preserves_reproducibility_provenance() -> None:
    result = snapshot([instrument(1)], rows(1), k=50)
    for field, value in PROVENANCE.items():
        if field == "raw_files":
            assert list(result[field]) == value
        else:
            assert result[field] == value
    assert result["k"] == 50
    assert result["lookback_length"] == 60
    assert list(result["lookback_sessions"]) == LOOKBACK
    assert result["as_of_date"] == AS_OF
    assert result["effective_date"] == EFFECTIVE
    assert result["ranked_candidates"][0] == {"isin": isin(1), "median_turnover_inr": Decimal(100)}
    assert list(result["exclusions"]) == []
