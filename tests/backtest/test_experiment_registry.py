import json
from datetime import UTC, date, datetime, timedelta
from hashlib import sha256
from pathlib import Path

import duckdb
import pytest

from trading.backtest.experiment_registry import ExperimentRecord, ExperimentRegistry
from trading.backtest.holdout import ConsumedHoldout, HoldoutEvaluator, HoldoutPlan
from trading.backtest.holdout_seals import SealedShortlist
from trading.backtest.promotion import HoldoutDecision


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


def sealed_shortlist() -> SealedShortlist:
    return SealedShortlist(
        candidates=(
            {
                "candidate_id": "candidate-a",
                "candidate_version": "1.0.0",
                "parameters": {"lookback": 20},
            },
        ),
        catalog_hash=sha256(b"catalog").hexdigest(),
        rejection_rule_hash=sha256(b"rejection").hexdigest(),
        metrics_hash=sha256(b"metrics").hexdigest(),
        family_hash=sha256(b"family").hexdigest(),
        dataset_manifest_hash=sha256(b"dataset").hexdigest(),
    )


def holdout_plan(shortlist: SealedShortlist | None = None) -> HoldoutPlan:
    from trading.backtest.holdout import holdout_window_id

    window = {
        "holdout_start": date(2023, 1, 1),
        "holdout_end": date(2024, 1, 1),
        "dataset_manifest_hash": sha256(b"dataset").hexdigest(),
        "source_snapshot_id": "synthetic-source",
        "universe_version": "synthetic-universe",
        "calendar_version": "synthetic-calendar",
        "corporate_action_version": "synthetic-actions",
    }
    sealed = shortlist or sealed_shortlist()
    return HoldoutPlan(
        plan_id="synthetic-split",
        **window,
        data_window_id=holdout_window_id(**window),
        cost_model_hash=sha256(b"costs").hexdigest(),
        split_plan_hash=sha256(b"split").hexdigest(),
        shortlist_hash=sealed.shortlist_hash,
        rejection_rule_hash=sealed.rejection_rule_hash,
        metrics_hash=sealed.metrics_hash,
        family_hash=sealed.family_hash,
    )


def completed_holdout_record(plan: HoldoutPlan) -> ExperimentRecord:
    return record(
        status="completed",
        error=None,
        partition="holdout",
        split_plan_id=plan.plan_id,
        data_window_id=plan.data_window_id,
        catalog_hash=sealed_shortlist().catalog_hash,
        metrics_json=(
            '{"trade_count":30,"net_return":0.1,"max_drawdown":0.05,'
            '"cost_drag":0.01,"positive_instrument_fraction":0.6,'
            '"uncertainty":null,"uncertainty_reason":"synthetic fixture"}'
        ),
    )


def test_registry_selection_read_hides_holdout_rows(tmp_path: Path) -> None:
    database = tmp_path / "runs.duckdb"
    plan = holdout_plan()
    with ExperimentRegistry(database) as registry, HoldoutEvaluator(database) as guard:
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
        registry.append(failed)
        registry.append(succeeded)
        registry.append_holdout_decision(
            completed_holdout_record(plan),
            decision=HoldoutDecision("inconclusive", ("incomplete_data",)),
            authorization=guard.reserve_once(plan),
            holdout_guard=guard,
            shortlist=sealed_shortlist(),
        )

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
        with pytest.raises(PermissionError):
            registry.holdout_records(
                authorization=ConsumedHoldout(
                    plan_id=plan.plan_id,
                    data_window_id=plan.data_window_id,
                    dataset_manifest_hash=plan.dataset_manifest_hash,
                    cost_model_hash=plan.cost_model_hash,
                    split_plan_hash=plan.split_plan_hash,
                    shortlist_hash=plan.shortlist_hash,
                    rejection_rule_hash=plan.rejection_rule_hash,
                    metrics_hash=plan.metrics_hash,
                    family_hash=plan.family_hash,
                    authorization_token="forged",
                ),
                holdout_guard=guard,
            )
        authorization = guard.reserve_once(plan)
        stored = registry.append_holdout_decision(
            completed_holdout_record(plan),
            decision=HoldoutDecision("inconclusive", ("incomplete_data",)),
            authorization=authorization,
            holdout_guard=guard,
            shortlist=sealed_shortlist(),
        )
        assert registry.holdout_records(authorization=authorization, holdout_guard=guard) == [
            stored
        ]


def test_holdout_decision_is_append_only_audit_evidence_with_valid_authorization(
    tmp_path: Path,
) -> None:
    database = tmp_path / "runs.duckdb"
    plan = holdout_plan()
    prepared = completed_holdout_record(plan)
    decision = HoldoutDecision(
        "rejected", ("profitable_instruments_binomial_p_value_not_below_0.05",)
    )
    with ExperimentRegistry(database) as registry, HoldoutEvaluator(database) as guard:
        with pytest.raises(PermissionError, match="authorization"):
            registry.append_holdout_decision(
                prepared,
                decision=decision,
                authorization=ConsumedHoldout(
                    plan_id=plan.plan_id,
                    data_window_id=plan.data_window_id,
                    dataset_manifest_hash=plan.dataset_manifest_hash,
                    cost_model_hash=plan.cost_model_hash,
                    split_plan_hash=plan.split_plan_hash,
                    shortlist_hash=plan.shortlist_hash,
                    rejection_rule_hash=plan.rejection_rule_hash,
                    metrics_hash=plan.metrics_hash,
                    family_hash=plan.family_hash,
                    authorization_token="forged",
                ),
                holdout_guard=guard,
                shortlist=sealed_shortlist(),
            )

        authorization = guard.reserve_once(plan)
        stored = registry.append_holdout_decision(
            prepared,
            decision=decision,
            authorization=authorization,
            holdout_guard=guard,
            shortlist=sealed_shortlist(),
        )

        assert stored.status == "rejected"
        assert stored.error == (
            '{"holdout_reasons":["profitable_instruments_binomial_p_value_not_below_0.05"]}'
        )
        assert registry.holdout_records(authorization=authorization, holdout_guard=guard) == [
            stored
        ]


def test_registry_refuses_direct_holdout_append(tmp_path: Path) -> None:
    with ExperimentRegistry(tmp_path / "runs.duckdb") as registry:
        with pytest.raises(PermissionError, match="append_holdout_decision"):
            registry.append(record(partition="holdout"))


@pytest.mark.parametrize(
    "record_changes",
    [
        {"parameters_json": '{"lookback":21}'},
        {"catalog_hash": "f" * 64},
        {"candidate_id": "candidate-not-shortlisted"},
    ],
)
def test_holdout_decision_requires_exact_candidate_from_sealed_shortlist(
    tmp_path: Path, record_changes: dict[str, str]
) -> None:
    database = tmp_path / "runs.duckdb"
    shortlist = sealed_shortlist()
    plan = holdout_plan(shortlist)
    with ExperimentRegistry(database) as registry, HoldoutEvaluator(database) as guard:
        authorization = guard.reserve_once(plan)
        with pytest.raises(ValueError, match="sealed shortlist"):
            registry.append_holdout_decision(
                completed_holdout_record(plan).model_copy(update=record_changes),
                decision=HoldoutDecision("rejected", ("incomplete_data",)),
                authorization=authorization,
                holdout_guard=guard,
                shortlist=shortlist,
            )


def test_holdout_decision_can_only_be_recorded_once_per_sealed_candidate(tmp_path: Path) -> None:
    database = tmp_path / "runs.duckdb"
    shortlist = sealed_shortlist()
    plan = holdout_plan(shortlist)
    with ExperimentRegistry(database) as registry, HoldoutEvaluator(database) as guard:
        authorization = guard.reserve_once(plan)
        record = completed_holdout_record(plan)
        registry.append_holdout_decision(
            record,
            decision=HoldoutDecision("inconclusive", ("incomplete_data",)),
            authorization=authorization,
            holdout_guard=guard,
            shortlist=shortlist,
        )
    with ExperimentRegistry(database) as registry, HoldoutEvaluator(database) as guard:
        with pytest.raises(duckdb.ConstraintException):
            registry.append_holdout_decision(
                record.model_copy(update={"experiment_id": "second-attempt"}),
                decision=HoldoutDecision("rejected", ("incomplete_data",)),
                authorization=authorization,
                holdout_guard=guard,
                shortlist=shortlist,
            )


def test_holdout_authorization_cannot_be_self_minted_from_public_plan_fields(
    tmp_path: Path,
) -> None:
    """Regression for the forgeable one-shot guard: every field on `ConsumedHoldout`
    other than `authorization_token` is derived from the plan itself (pre-registered,
    not secret) -- a caller who never called `reserve_once` can copy them all. Only
    a token actually minted and stored by `_consume` must unlock holdout rows,
    even once someone else has legitimately consumed the same plan.
    """
    database = tmp_path / "runs.duckdb"
    plan = holdout_plan()
    with ExperimentRegistry(database) as registry, HoldoutEvaluator(database) as guard:
        real_authorization = guard.reserve_once(plan)  # legitimate consumption happens

        self_minted = ConsumedHoldout(
            plan_id=plan.plan_id,
            data_window_id=plan.data_window_id,
            dataset_manifest_hash=plan.dataset_manifest_hash,
            cost_model_hash=plan.cost_model_hash,
            split_plan_hash=plan.split_plan_hash,
            shortlist_hash=plan.shortlist_hash,
            rejection_rule_hash=plan.rejection_rule_hash,
            metrics_hash=plan.metrics_hash,
            family_hash=plan.family_hash,
            authorization_token="attacker-guessed-this",
        )
        assert guard.validate_authorization(self_minted) is False
        with pytest.raises(PermissionError):
            registry.holdout_records(authorization=self_minted, holdout_guard=guard)

        # the real, minted-by-`_consume` token still works.
        assert guard.validate_authorization(real_authorization) is True


def test_holdout_authorization_must_come_from_registry_database(tmp_path: Path) -> None:
    plan = holdout_plan()
    with (
        ExperimentRegistry(tmp_path / "runs.duckdb") as registry,
        HoldoutEvaluator(tmp_path / "runs.duckdb") as authoritative_guard,
        HoldoutEvaluator(tmp_path / "attacker.duckdb") as unrelated_guard,
    ):
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
