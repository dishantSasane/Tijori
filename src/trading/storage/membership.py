"""Validated point-in-time Nifty 50 / Nifty Next 50 membership manifests."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from enum import StrEnum
from typing import Literal

from pydantic import AnyUrl, Field, field_validator, model_validator

from trading.core.models import Contract


class IndexId(StrEnum):
    NIFTY50 = "NIFTY50"
    NIFTYNEXT50 = "NIFTYNEXT50"


ReviewStatus = Literal["pending", "verified", "rejected"]


def _interval_end(interval: MembershipInterval, coverage_end: date) -> date:
    return interval.effective_to or coverage_end


def _isin_checksum_is_valid(value: str) -> bool:
    expanded = "".join(str(ord(char) - 55) if char.isalpha() else char for char in value)
    checksum_total = 0
    for position, digit in enumerate(reversed(expanded)):
        number = int(digit) * (2 if position % 2 else 1)
        checksum_total += number // 10 + number % 10
    return checksum_total % 10 == 0


class MembershipInterval(Contract):
    """One historical membership span for one index constituent identity."""

    index_id: IndexId
    isin: str = Field(min_length=12, max_length=12, pattern=r"^IN[A-Z0-9]{9}[0-9]$")
    symbol_at_time: str = Field(min_length=1)
    company_name_at_time: str = Field(min_length=1)
    effective_from: date
    effective_to: date | None = None
    source_notice_url: AnyUrl
    source_notice_date: date
    review_status: ReviewStatus
    notes: str = Field(min_length=1)

    @field_validator("isin")
    @classmethod
    def _validate_isin_checksum(cls, value: str) -> str:
        if not _isin_checksum_is_valid(value):
            raise ValueError("ISIN check digit is invalid")
        return value

    @field_validator("symbol_at_time", "company_name_at_time", "notes")
    @classmethod
    def _reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text fields must not be blank")
        return value

    @model_validator(mode="after")
    def _check_interval_dates(self) -> MembershipInterval:
        if self.effective_to is not None and self.effective_to <= self.effective_from:
            raise ValueError("membership intervals must have positive duration")
        if self.source_notice_date > self.effective_from:
            raise ValueError("source notice must be published by the membership effective date")
        return self


class MembershipManifest(Contract):
    """Versioned coverage declaration and constituent intervals for two indexes."""

    intervals: tuple[MembershipInterval, ...] = Field(min_length=1)
    coverage_start: date
    coverage_end: date
    complete: bool
    source: str = Field(min_length=1)
    source_ref: AnyUrl
    licence_ref: str = Field(min_length=1)
    version: str = Field(min_length=1)

    @field_validator("source", "licence_ref", "version")
    @classmethod
    def _reject_blank_provenance(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("provenance fields must not be blank")
        return value

    @model_validator(mode="after")
    def _validate_membership_intervals(self) -> MembershipManifest:
        if self.coverage_end <= self.coverage_start:
            raise ValueError("manifest coverage must have positive duration")

        intervals_by_identity: dict[tuple[IndexId, str], list[MembershipInterval]] = defaultdict(
            list
        )
        intervals_by_isin: dict[str, list[MembershipInterval]] = defaultdict(list)
        boundaries = {self.coverage_start}
        for interval in self.intervals:
            interval_end = _interval_end(interval, self.coverage_end)
            if (
                interval.effective_from < self.coverage_start
                or interval.effective_from >= self.coverage_end
                or interval_end > self.coverage_end
            ):
                raise ValueError("membership interval falls outside manifest coverage")
            intervals_by_identity[(interval.index_id, interval.isin)].append(interval)
            intervals_by_isin[interval.isin].append(interval)
            boundaries.add(interval.effective_from)
            if interval.effective_to is not None:
                boundaries.add(interval.effective_to)

        for key, spans in intervals_by_identity.items():
            ordered_spans = sorted(spans, key=lambda item: item.effective_from)
            for earlier, later in zip(ordered_spans, ordered_spans[1:], strict=False):
                if _interval_end(earlier, self.coverage_end) > later.effective_from:
                    raise ValueError(f"overlapping membership intervals for {key[0]} / {key[1]}")

        for isin, spans in intervals_by_isin.items():
            for position, first in enumerate(spans):
                for second in spans[position + 1 :]:
                    if first.index_id == second.index_id:
                        continue
                    overlaps = first.effective_from < _interval_end(
                        second, self.coverage_end
                    ) and second.effective_from < _interval_end(first, self.coverage_end)
                    if overlaps:
                        raise ValueError(f"ISIN belongs to both indexes at once: {isin}")

        if self.complete and any(
            interval.review_status != "verified" for interval in self.intervals
        ):
            raise ValueError("complete manifests require every interval to be verified")

        check_dates = sorted(boundary for boundary in boundaries if boundary < self.coverage_end)
        for session_date in check_dates:
            for index_id in IndexId:
                active_isins = {
                    interval.isin
                    for interval in self.intervals
                    if interval.index_id == index_id
                    and interval.effective_from <= session_date
                    and _interval_end(interval, self.coverage_end) > session_date
                }
                member_count = len(active_isins)
                if member_count > 50:
                    raise ValueError(
                        f"{index_id.value} membership cannot exceed 50 members "
                        f"on {session_date}, found {member_count}"
                    )
                if self.complete and member_count != 50:
                    raise ValueError(
                        f"complete {index_id.value} membership must have 50 members "
                        f"on {session_date}, found {member_count}"
                    )
        return self

    def members_on(
        self, index_id: IndexId | str, session_date: date
    ) -> tuple[MembershipInterval, ...]:
        """Return active members for a covered NSE session, ordered by ISIN."""
        try:
            selected_index = IndexId(index_id)
        except ValueError as error:
            raise ValueError(f"unsupported index ID: {index_id}") from error
        if not self.coverage_start <= session_date < self.coverage_end:
            raise ValueError("membership lookup is outside manifest coverage")
        return tuple(
            sorted(
                (
                    interval
                    for interval in self.intervals
                    if interval.index_id == selected_index
                    and interval.effective_from <= session_date
                    and _interval_end(interval, self.coverage_end) > session_date
                ),
                key=lambda interval: interval.isin,
            )
        )
