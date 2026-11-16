from concurrent.futures import ThreadPoolExecutor
from datetime import date
from hashlib import sha256
from pathlib import Path
from threading import Barrier

import pytest

from trading.backtest.holdout import (
    HoldoutAlreadyConsumedError,
    HoldoutEvaluator,
    HoldoutPlan,
    holdout_plan_from_split,
    holdout_window_id,
)
from trading.backtest.splits import create_split_plan


def digest(label: str) -> str:
    return sha256(label.encode()).hexdigest()


def plan(**overrides: object) -> HoldoutPlan:
    window_fields = {
        "holdout_start": date(2023, 1, 1),
        "holdout_end": date(2024, 1, 1),
        "dataset_manifest_hash": digest("dataset"),
        "source_snapshot_id": "synthetic-source",
        "universe_version": "synthetic-universe",
        "calendar_version": "synthetic-calendar",
        "corporate_action_version": "synthetic-actions",
    }
    values: dict[str, object] = {
        "plan_id": "synthetic-plan-v1",
        **window_fields,
        "data_window_id": holdout_window_id(**window_fields),
        "cost_model_hash": digest("costs"),
        "split_plan_hash": digest("split"),
        "shortlist_hash": digest("shortlist"),
        "rejection_rule_hash": digest("rejection"),
        "metrics_hash": digest("metrics"),
        "family_hash": digest("family"),
    }
    values.update(overrides)
    identity_fields = {
        key: values[key]
        for key in (
            "holdout_start",
            "holdout_end",
            "dataset_manifest_hash",
            "source_snapshot_id",
            "universe_version",
            "calendar_version",
            "corporate_action_version",
        )
    }
    values["data_window_id"] = holdout_window_id(**identity_fields)  # type: ignore[arg-type]
    return HoldoutPlan.model_validate(values)


def test_holdout_is_marked_consumed_before_result_is_returned(tmp_path: Path) -> None:
    with HoldoutEvaluator(tmp_path / "holdout.duckdb") as guard:
        result = guard.evaluate_once(plan(), lambda: {"synthetic": 1})
        assert result == {"synthetic": 1}
        assert guard.is_consumed("synthetic-plan-v1")


def test_holdout_plan_cannot_be_evaluated_twice(tmp_path: Path) -> None:
    with HoldoutEvaluator(tmp_path / "holdout.duckdb") as guard:
        guard.evaluate_once(plan(), lambda: "first")
        with pytest.raises(HoldoutAlreadyConsumedError):
            guard.evaluate_once(plan(), lambda: pytest.fail("must not run"))


def test_renaming_plan_cannot_reuse_consumed_data_window(tmp_path: Path) -> None:
    with HoldoutEvaluator(tmp_path / "holdout.duckdb") as guard:
        guard.evaluate_once(plan(), lambda: "first")
        renamed = plan(plan_id="different-plan-id")
        with pytest.raises(HoldoutAlreadyConsumedError):
            guard.evaluate_once(renamed, lambda: pytest.fail("same window must not run twice"))


def test_failure_during_evaluation_does_not_unconsume_holdout(tmp_path: Path) -> None:
    with HoldoutEvaluator(tmp_path / "holdout.duckdb") as guard:
        with pytest.raises(RuntimeError, match="synthetic"):
            guard.evaluate_once(plan(), lambda: (_ for _ in ()).throw(RuntimeError("synthetic")))
        assert guard.is_consumed("synthetic-plan-v1")


def test_plan_id_is_required() -> None:
    with pytest.raises(ValueError):
        plan(plan_id="")


def test_holdout_plan_requires_sha256_seals() -> None:
    with pytest.raises(ValueError, match="shortlist_hash"):
        plan(shortlist_hash="human-label-is-not-a-seal")


def frozen_split(**overrides: object):
    values: dict[str, object] = {
        "plan_id": "p1a-v1",
        "version": "1",
        "data_window_id": "full-window-sha",
        "source_snapshot_id": "source-sha",
        "universe_version": "universe-v1",
        "calendar_version": "xnse-v1",
        "corporate_action_version": "actions-v1",
        "development": {"start": date(2018, 1, 1), "end": date(2020, 1, 1)},
        "validation": {"start": date(2020, 1, 1), "end": date(2022, 1, 1)},
        "holdout": {"start": date(2022, 1, 1), "end": date(2024, 1, 1)},
        "embargo_bars": 1,
        "holdout_unread": True,
    }
    values.update(overrides)
    return create_split_plan(**values)


def test_holdout_plan_is_derived_from_frozen_split_contents() -> None:
    derived = holdout_plan_from_split(
        frozen_split(),
        shortlist_hash=digest("shortlist"),
        rejection_rule_hash=digest("rejection"),
        metrics_hash=digest("metrics"),
        family_hash=digest("family"),
        dataset_manifest_hash=digest("dataset"),
        cost_model_hash=digest("costs"),
    )
    changed_plan_label = holdout_plan_from_split(
        frozen_split(plan_id="renamed"),
        shortlist_hash=digest("shortlist"),
        rejection_rule_hash=digest("rejection"),
        metrics_hash=digest("metrics"),
        family_hash=digest("family"),
        dataset_manifest_hash=digest("dataset"),
        cost_model_hash=digest("costs"),
    )
    assert derived.plan_id != changed_plan_label.plan_id
    assert derived.data_window_id == changed_plan_label.data_window_id


def test_overlapping_holdout_range_cannot_be_reintroduced_by_new_split_id(tmp_path: Path) -> None:
    with HoldoutEvaluator(tmp_path / "holdout.duckdb") as guard:
        original_split = frozen_split()
        original = holdout_plan_from_split(
            original_split,
            shortlist_hash=digest("shortlist"),
            rejection_rule_hash=digest("rejection"),
            metrics_hash=digest("metrics"),
            family_hash=digest("family"),
            dataset_manifest_hash=digest("dataset"),
            cost_model_hash=digest("costs"),
        )
        guard.reserve_once(original)
        overlapping_split = frozen_split(plan_id="different-split", version="2")
        overlapping = holdout_plan_from_split(
            overlapping_split,
            shortlist_hash=digest("new-shortlist"),
            rejection_rule_hash=digest("new-rejection"),
            metrics_hash=digest("new-metrics"),
            family_hash=digest("new-family"),
            dataset_manifest_hash=digest("dataset"),
            cost_model_hash=digest("costs"),
        )
        with pytest.raises(HoldoutAlreadyConsumedError):
            guard.reserve_once(overlapping)


def test_holdout_cannot_be_replayed_after_data_version_labels_change(tmp_path: Path) -> None:
    with HoldoutEvaluator(tmp_path / "holdout.duckdb") as guard:
        guard.reserve_once(plan())
        relabeled = plan(
            plan_id="new-plan",
            source_snapshot_id="new-source",
            universe_version="new-universe",
            calendar_version="new-calendar",
            corporate_action_version="new-actions",
        )
        with pytest.raises(HoldoutAlreadyConsumedError):
            guard.reserve_once(relabeled)


def test_concurrent_attempts_for_same_window_allow_only_one_evaluator(tmp_path: Path) -> None:
    with HoldoutEvaluator(tmp_path / "holdout.duckdb") as guard:
        barrier = Barrier(2)

        def evaluate(plan_id: str) -> str:
            barrier.wait()
            try:
                return guard.evaluate_once(plan(plan_id=plan_id), lambda: f"evaluated:{plan_id}")
            except HoldoutAlreadyConsumedError:
                return "rejected"

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(evaluate, ("plan-a", "plan-b")))
        assert sum(result.startswith("evaluated:") for result in results) == 1
        assert results.count("rejected") == 1


def test_reserve_once_mints_an_unguessable_token_and_rejects_self_minted_ones(
    tmp_path: Path,
) -> None:
    with HoldoutEvaluator(tmp_path / "holdout.duckdb") as guard:
        authorization = guard.reserve_once(plan())
        assert authorization.authorization_token
        # the token is independent of the plan's own public fields -- an
        # attacker who only knows the plan (pre-registered, not secret)
        # cannot derive it.
        forged = authorization.model_copy(update={"authorization_token": "guessed"})
        assert guard.validate_authorization(authorization) is True
        assert guard.validate_authorization(forged) is False


def test_concurrent_connections_cannot_reserve_overlapping_windows(tmp_path: Path) -> None:
    database = tmp_path / "multi-connection.duckdb"
    with HoldoutEvaluator(database) as first_guard, HoldoutEvaluator(database) as second_guard:
        barrier = Barrier(2)

        def reserve(guard: HoldoutEvaluator, candidate: HoldoutPlan) -> str:
            barrier.wait()
            try:
                guard.reserve_once(candidate)
                return "accepted"
            except HoldoutAlreadyConsumedError:
                return "rejected"

        plans = [
            plan(plan_id="window-a"),
            plan(
                plan_id="window-b",
                holdout_start=date(2023, 6, 1),
                holdout_end=date(2024, 6, 1),
            ),
        ]
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(
                executor.map(
                    lambda pair: reserve(*pair),
                    [(first_guard, plans[0]), (second_guard, plans[1])],
                )
            )

    assert results.count("accepted") == 1
    assert results.count("rejected") == 1
