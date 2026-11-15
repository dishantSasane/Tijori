"""Blind contract tests for docs/specs/INDEX_MEMBERSHIP.md.

All identifiers and source notices are synthetic.
"""

from datetime import date, timedelta

import pytest

from trading.storage.membership import MembershipInterval, MembershipManifest

START = date(2024, 1, 1)
CHANGE = date(2024, 4, 1)
END = date(2025, 1, 1)


def isin(number: int) -> str:
    """Generate a synthetic, checksum-valid ISIN for a test fixture."""
    prefix = f"IN{number:09d}"
    digits = "".join(str(int(char, 36)) for char in prefix) + "0"
    total = sum(
        sum(divmod(int(char) * (2 if position % 2 else 1), 10))
        for position, char in enumerate(reversed(digits))
    )
    return prefix + str((-total) % 10)


def interval(**overrides: object) -> MembershipInterval:
    fields: dict[str, object] = {
        "index_id": "NIFTY50",
        "isin": isin(1),
        "symbol_at_time": "EXAMPLE",
        "company_name_at_time": "Example Limited",
        "effective_from": START,
        "effective_to": None,
        "source_notice_url": "https://example.test/notice/1",
        "source_notice_date": date(2023, 12, 1),
        "review_status": "verified",
        "notes": "Synthetic notice for testing",
    }
    fields.update(overrides)
    return MembershipInterval.model_validate(fields)


def manifest(intervals: list[MembershipInterval], *, complete: bool = False) -> MembershipManifest:
    return MembershipManifest.model_validate(
        {
            "intervals": intervals,
            "coverage_start": START,
            "coverage_end": END,
            "complete": complete,
            "source": "Synthetic dataset",
            "source_ref": "https://example.test/dataset",
            "licence_ref": "https://example.test/licence",
            "version": "test-v1",
        }
    )


def full_membership() -> list[MembershipInterval]:
    return [
        interval(index_id=index_id, isin=isin(number))
        for index_id, numbers in (("NIFTY50", range(1, 51)), ("NIFTYNEXT50", range(51, 101)))
        for number in numbers
    ]


def test_partial_manifest_and_provenance_are_preserved() -> None:
    member = interval()
    dataset = manifest([member])

    assert dataset.complete is False
    assert dataset.source == "Synthetic dataset"
    assert str(dataset.source_ref) == "https://example.test/dataset"
    assert str(dataset.licence_ref) == "https://example.test/licence"
    assert dataset.version == "test-v1"
    assert member.symbol_at_time == "EXAMPLE"
    assert member.company_name_at_time == "Example Limited"
    assert str(member.source_notice_url) == "https://example.test/notice/1"
    assert member.source_notice_date == date(2023, 12, 1)
    assert member.review_status == "verified"
    assert member.notes == "Synthetic notice for testing"
    assert list(dataset.members_on("NIFTY50", START)) == [member]
    assert list(dataset.members_on("NIFTYNEXT50", START)) == []


def test_complete_manifest_has_50_members_per_index_across_boundary() -> None:
    members = full_membership()
    members[0] = interval(isin=isin(1), effective_to=CHANGE)
    members.append(interval(isin=isin(101), effective_from=CHANGE))
    dataset = manifest(members, complete=True)

    for session in (START, CHANGE - timedelta(days=1), CHANGE, END - timedelta(days=1)):
        assert len(dataset.members_on("NIFTY50", session)) == 50
        assert len(dataset.members_on("NIFTYNEXT50", session)) == 50
    before = {member.isin for member in dataset.members_on("NIFTY50", START)}
    after = {member.isin for member in dataset.members_on("NIFTY50", CHANGE)}
    assert before - after == {isin(1)}
    assert after - before == {isin(101)}


def test_half_open_intervals_allow_adjacent_index_transfer() -> None:
    old = interval(effective_to=CHANGE)
    new = interval(index_id="NIFTYNEXT50", effective_from=CHANGE)
    dataset = manifest([old, new])

    assert list(dataset.members_on("NIFTY50", CHANGE - timedelta(days=1))) == [old]
    assert list(dataset.members_on("NIFTY50", CHANGE)) == []
    assert list(dataset.members_on("NIFTYNEXT50", CHANGE)) == [new]
    assert list(dataset.members_on("NIFTYNEXT50", END - timedelta(days=1))) == [new]


@pytest.mark.parametrize("invalid_isin", ["", "IN123", "IN12345678901"])
def test_invalid_isin_length_is_rejected(invalid_isin: str) -> None:
    with pytest.raises(ValueError):
        interval(isin=invalid_isin)


def test_known_indian_isin_and_check_digit_are_accepted() -> None:
    assert interval(isin="INE002A01018").isin == "INE002A01018"


def test_invalid_isin_check_digit_is_rejected() -> None:
    with pytest.raises(ValueError, match="check digit"):
        interval(isin="INE002A01019")


def test_non_indian_isin_is_rejected_for_india_indices() -> None:
    with pytest.raises(ValueError):
        interval(isin="US0378331005")


@pytest.mark.parametrize("end", [START, START - timedelta(days=1)])
def test_non_positive_interval_is_rejected(end: date) -> None:
    with pytest.raises(ValueError):
        interval(effective_to=end)


def test_source_notice_cannot_postdate_membership_start() -> None:
    with pytest.raises(ValueError, match="published by"):
        interval(source_notice_date=START + timedelta(days=1))


@pytest.mark.parametrize("field", ["index_id", "symbol_at_time", "company_name_at_time"])
def test_empty_identity_fields_are_rejected(field: str) -> None:
    with pytest.raises(ValueError):
        interval(**{field: ""})


@pytest.mark.parametrize(
    "member",
    [
        interval(effective_from=START - timedelta(days=1)),
        interval(effective_to=END + timedelta(days=1)),
        interval(effective_from=END),
    ],
)
def test_interval_outside_coverage_is_rejected(member: MembershipInterval) -> None:
    with pytest.raises(ValueError):
        manifest([member])


def test_duplicate_and_overlapping_intervals_are_rejected() -> None:
    member = interval(effective_to=CHANGE)
    for other in (member, interval(effective_from=CHANGE - timedelta(days=1))):
        with pytest.raises(ValueError):
            manifest([member, other])


def test_cross_index_overlap_is_rejected() -> None:
    with pytest.raises(ValueError):
        manifest(
            [
                interval(effective_to=CHANGE),
                interval(index_id="NIFTYNEXT50", effective_from=CHANGE - timedelta(days=1)),
            ]
        )


def test_complete_manifest_rejects_missing_member_at_coverage_start() -> None:
    with pytest.raises(ValueError):
        manifest(full_membership()[:-1], complete=True)


def test_partial_manifest_cannot_exceed_index_member_count() -> None:
    members = [interval(isin=isin(number)) for number in range(1, 52)]

    with pytest.raises(ValueError, match="cannot exceed 50"):
        manifest(members)


def test_partial_manifest_cannot_exceed_member_count_at_later_boundary() -> None:
    members = [interval(isin=isin(number)) for number in range(1, 51)]
    members.append(interval(isin=isin(51), effective_from=CHANGE))

    with pytest.raises(ValueError, match="cannot exceed 50"):
        manifest(members)


def test_complete_manifest_requires_verified_intervals() -> None:
    members = full_membership()
    members[0] = interval(isin=isin(1), review_status="pending")

    with pytest.raises(ValueError, match="verified"):
        manifest(members, complete=True)


def test_complete_manifest_rejects_temporary_gap_between_events() -> None:
    members = full_membership()
    members[0] = interval(effective_to=CHANGE)
    members.append(interval(isin=isin(101), effective_from=CHANGE + timedelta(days=1)))
    with pytest.raises(ValueError):
        manifest(members, complete=True)


@pytest.mark.parametrize("session", [START - timedelta(days=1), END])
def test_lookup_outside_half_open_coverage_is_rejected(session: date) -> None:
    with pytest.raises(ValueError):
        manifest([interval()]).members_on("NIFTY50", session)


def test_lookup_rejects_unknown_index_id() -> None:
    with pytest.raises(ValueError, match="unsupported index ID"):
        manifest([interval()]).members_on("NIFTY100", START)


def test_lookup_is_ordered_by_isin_not_input_or_display_name() -> None:
    members = [
        interval(isin=isin(3), symbol_at_time="AAA"),
        interval(isin=isin(1), symbol_at_time="ZZZ"),
        interval(isin=isin(2), symbol_at_time="MMM"),
    ]
    dataset = manifest(members)

    assert [member.isin for member in dataset.members_on("NIFTY50", START)] == [
        isin(1),
        isin(2),
        isin(3),
    ]
