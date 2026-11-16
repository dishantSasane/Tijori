from datetime import date

import pytest

from trading.backtest.splits import DateRange, ResearchSplitPlan, create_split_plan


def fields(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "plan_id": "synthetic-plan-v1",
        "version": "1",
        "data_window_id": "synthetic-window-v1",
        "source_snapshot_id": "synthetic-source-v1",
        "universe_version": "synthetic-universe-v1",
        "calendar_version": "synthetic-calendar-v1",
        "corporate_action_version": "synthetic-actions-v1",
        "development": {"start": date(2020, 1, 1), "end": date(2022, 1, 1)},
        "validation": {"start": date(2022, 1, 1), "end": date(2023, 1, 1)},
        "holdout": {"start": date(2023, 1, 1), "end": date(2024, 1, 1)},
        "embargo_bars": 1,
        "holdout_unread": True,
    }
    values.update(overrides)
    return values


def test_plan_builds_hash_and_exact_adjacent_partition() -> None:
    plan = create_split_plan(**fields())
    assert isinstance(plan, ResearchSplitPlan)
    assert len(plan.content_hash) == 64
    assert plan.development.end == plan.validation.start
    assert plan.validation.end == plan.holdout.start


def test_plan_rejects_gaps_and_overlaps() -> None:
    with pytest.raises(ValueError, match="adjacent"):
        create_split_plan(**fields(validation={"start": date(2022, 2, 1), "end": date(2023, 1, 1)}))
    with pytest.raises(ValueError, match="adjacent"):
        create_split_plan(
            **fields(validation={"start": date(2021, 12, 1), "end": date(2023, 1, 1)})
        )


def test_plan_hash_detects_field_tampering() -> None:
    plan = create_split_plan(**fields())
    changed = plan.model_dump(mode="python")
    changed["universe_version"] = "different-universe"
    with pytest.raises(ValueError, match="content_hash"):
        ResearchSplitPlan.model_validate(changed)


def test_plan_hash_is_canonical_for_equivalent_input_models() -> None:
    first = create_split_plan(**fields())
    nested = fields(
        development=DateRange(start=date(2020, 1, 1), end=date(2022, 1, 1)),
        validation=DateRange(start=date(2022, 1, 1), end=date(2023, 1, 1)),
        holdout=DateRange(start=date(2023, 1, 1), end=date(2024, 1, 1)),
    )
    second = create_split_plan(**nested)
    assert first.content_hash == second.content_hash


def test_date_ranges_must_have_positive_duration() -> None:
    with pytest.raises(ValueError):
        DateRange(start=date(2024, 1, 1), end=date(2024, 1, 1))
