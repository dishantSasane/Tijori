import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import duckdb
import pytest

from trading.backtest.experiment_registry import ExperimentRecord, ExperimentRegistry
from trading.backtest.holdout import ConsumedHoldout, HoldoutEvaluator, HoldoutPlan


def record(**overrides: object) -> ExperimentRecord:
    values: dict[str, object] = {
        "recorded_at_utc": datetime(2026, 11, 15, tzinfo=UTC),
        "status": "failed",
        "error": "synthetic failure",
        "candidate_id": "candidate-a",
        "candidate_version": "1.0.0",
        "parameters_json": '{"lookback":20}',
        "catalog_hash": "catalog-sha256",
        "data_snapshot_id": "synthetic-data",
        "universe_version": "synthetic-universe",
        "calendar_version": "synthetic-calendar",
        "corporate_action_version": "synthetic-actions",
        "cost_model_version": "synthetic-costs",
        "sizing_version": "synthetic-sizing",
        "split_plan_id": "synthetic-split",
        "data_window_id": "synthetic-window",
        "partition": "development",
        "code_revision": "abc123",
        "environment_version": "python-3.12",
        "parser_version": "synthetic-parser-v1",
        "sample_start": "2020-01-01",
        "sample_end": "2021-01-01",
        "instrument_count": 50,
        "time_block_count": 12,
        "test_family_size": 15,
        "metrics_json": '{"total_return":0.0,"max_drawdown":null}',
    }
    values.update(overrides)
    if "recorded_at_utc" not in overrides:
        values["recorded_at_utc"] = datetime(2026, 11, 15, tzinfo=UTC) + timedelta(
            seconds=len(values)
        )
    return ExperimentRecord.model_validate(values)


def holdout_plan() -> HoldoutPlan:
    from trading.backtest.holdout import holdout_window_id

    window = {
        "holdout_start": date(2023, 1, 1),
        "holdout_end": date(2024, 1, 1),
        "source_snapshot_id": "synthetic-source",
        "universe_version": "synthetic-universe",
        "calendar_version": "synthetic-calendar",
        "corporate_action_version": "synthetic-actions",
    }
    return HoldoutPlan(
        plan_id="synthetic-split",
        **window,
        data_window_id=holdout_window_id(**window),
        shortlist_hash="sha-shortlist",
        rejection_rule_hash="sha-rejection",
        metrics_hash="sha-metrics",
        family_hash="sha-family",
    )


def test_registry_selection_read_hides_holdout_rows(tmp_path: Path) -> None:
    with ExperimentRegistry(tmp_path / "runs.duckdb") as registry:
        failed = record(partition="development")
        succeeded = record(
            status="completed",
            error=None,
            partition="validation",
            metrics_json=(
                '{"trade_count":10,"net_return":0.1,"max_drawdown":0.05,'
                '"cost_drag":0.01,"positive_instrument_fraction":0.6,'
                '"uncertainty":null,"uncertainty_reason":"synthetic fixture"}'
            ),
        )
        holdout = record(partition="holdout")
        registry.append(failed)
        registry.append(succeeded)
        registry.append(holdout)

        assert registry.records_for_selection() == [failed, succeeded]
        with pytest.raises(PermissionError):
            registry.holdout_records(
                authorization=object(),
                holdout_guard=HoldoutEvaluator(tmp_path / "guard.duckdb"),  # type: ignore[arg-type]
            )


def test_holdout_access_requires_sealed_authorization_and_consumed_plan(tmp_path: Path) -> None:
    database = tmp_path / "runs.duckdb"
    plan = holdout_plan()
    with ExperimentRegistry(database) as registry, HoldoutEvaluator(database) as guard:
        holdout = record(
            partition="holdout",
            split_plan_id=plan.plan_id,
            data_window_id=plan.data_window_id,
        )
        registry.append(holdout)
        with pytest.raises(PermissionError):
            registry.holdout_records(
                authorization=ConsumedHoldout(
                    plan_id=plan.plan_id,
                    data_window_id=plan.data_window_id,
                    shortlist_hash=plan.shortlist_hash,
                    rejection_rule_hash=plan.rejection_rule_hash,
                    metrics_hash=plan.metrics_hash,
                    family_hash=plan.family_hash,
                    authorization_hash="forged",
                ),
                holdout_guard=guard,
            )
        authorization = guard.reserve_once(plan)
        assert registry.holdout_records(authorization=authorization, holdout_guard=guard) == [
            holdout
        ]


def test_holdout_authorization_must_come_from_registry_database(tmp_path: Path) -> None:
    plan = holdout_plan()
    with (
        ExperimentRegistry(tmp_path / "runs.duckdb") as registry,
        HoldoutEvaluator(tmp_path / "runs.duckdb") as authoritative_guard,
        HoldoutEvaluator(tmp_path / "attacker.duckdb") as unrelated_guard,
    ):
        registry.append(
            record(
                partition="holdout",
                split_plan_id=plan.plan_id,
                data_window_id=plan.data_window_id,
            )
        )
        forged_authorization = unrelated_guard.reserve_once(plan)
        with pytest.raises(PermissionError, match="same authoritative database"):
            registry.holdout_records(
                authorization=forged_authorization,
                holdout_guard=unrelated_guard,
            )
        assert authoritative_guard.is_consumed(plan.plan_id) is False


def test_registry_rejects_duplicate_run_id_instead_of_overwriting(tmp_path: Path) -> None:
    with ExperimentRegistry(tmp_path / "runs.duckdb") as registry:
        first = record()
        registry.append(first)
        with pytest.raises(duckdb.ConstraintException):
            registry.append(first)
        assert registry.records_for_selection() == [first]


@pytest.mark.parametrize("payload", ["[]", "null", "not-json"])
def test_registry_payloads_must_be_json_objects(payload: str) -> None:
    with pytest.raises(ValueError):
        record(metrics_json=payload)


def test_registry_rejects_non_finite_metric_constants() -> None:
    with pytest.raises(ValueError):
        record(metrics_json='{"sharpe":NaN}')
    with pytest.raises(ValueError):
        record(metrics_json='{"return":Infinity}')
    with pytest.raises(ValueError):
        record(metrics_json='{"nested":{"return":1e999}}')


def test_completed_run_requires_metrics() -> None:
    with pytest.raises(ValueError):
        record(status="completed", error=None, metrics_json="{}")


def test_completed_run_requires_metric_evidence_and_null_reasons() -> None:
    required = {
        "trade_count": 10,
        "net_return": 0.1,
        "max_drawdown": 0.05,
        "cost_drag": 0.01,
        "positive_instrument_fraction": 0.6,
        "uncertainty": None,
    }
    with pytest.raises(ValueError, match="reason"):
        record(status="completed", error=None, metrics_json=json.dumps(required))
    required["uncertainty_reason"] = "too few observations"
    assert record(status="completed", error=None, metrics_json=json.dumps(required))


def test_correction_records_can_link_to_prior_experiment(tmp_path: Path) -> None:
    with ExperimentRegistry(tmp_path / "runs.duckdb") as registry:
        original = record()
        correction = record(supersedes_experiment_id=original.experiment_id)
        registry.append(original)
        registry.append(correction)
        corrected = registry.records_for_selection()[1]
        assert corrected.supersedes_experiment_id == original.experiment_id
