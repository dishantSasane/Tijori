"""Immutable chronological train/validation/holdout split-plan contract."""

from __future__ import annotations

import json
from datetime import date
from hashlib import sha256
from typing import Any

from pydantic import Field, model_validator

from trading.core.models import Contract


class DateRange(Contract):
    """Half-open date interval [start, end)."""

    start: date
    end: date

    @model_validator(mode="after")
    def _positive_duration(self) -> DateRange:
        if self.end <= self.start:
            raise ValueError("date range must have positive duration")
        return self


class ResearchSplitPlan(Contract):
    plan_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    data_window_id: str = Field(min_length=1)
    source_snapshot_id: str = Field(min_length=1)
    universe_version: str = Field(min_length=1)
    calendar_version: str = Field(min_length=1)
    corporate_action_version: str = Field(min_length=1)
    development: DateRange
    validation: DateRange
    holdout: DateRange
    embargo_bars: int = Field(gt=0)
    holdout_unread: bool
    content_hash: str = Field(min_length=64, max_length=64)

    @model_validator(mode="after")
    def _validate_partition(self) -> ResearchSplitPlan:
        fields = self.model_dump(mode="python", exclude={"content_hash"})
        expected_hash = split_plan_hash(fields)
        if self.content_hash != expected_hash:
            raise ValueError("split plan content_hash does not match plan fields")
        if self.development.end != self.validation.start:
            raise ValueError("development and validation must be adjacent and non-overlapping")
        if self.validation.end != self.holdout.start:
            raise ValueError("validation and holdout must be adjacent and non-overlapping")
        return self


def split_plan_hash(fields: dict[str, Any]) -> str:
    """Hash a canonical JSON representation excluding the hash field itself."""
    payload = {key: value for key, value in fields.items() if key != "content_hash"}
    normalized = _json_normalize(payload)
    canonical = json.dumps(normalized, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return sha256(canonical.encode("utf-8")).hexdigest()


def _json_normalize(value: Any) -> Any:
    if isinstance(value, Contract):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {key: _json_normalize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_normalize(item) for item in value]
    if isinstance(value, date):
        return value.isoformat()
    return value


def create_split_plan(**fields: Any) -> ResearchSplitPlan:
    """Create a validated split plan with a computed canonical content hash."""
    fields["content_hash"] = split_plan_hash(fields)
    return ResearchSplitPlan.model_validate(fields)
