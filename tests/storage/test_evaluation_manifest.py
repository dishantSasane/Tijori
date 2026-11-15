from datetime import date

import pytest
from pydantic import ValidationError

from trading.storage.evaluation_manifest import (
    P1EvaluationManifest,
    calendar_snapshot_sha256,
    evaluation_manifest_sha256,
)

HASH_A = "a" * 64
HASH_B = "b" * 64


def manifest(**changes: object) -> P1EvaluationManifest:
    return P1EvaluationManifest.model_validate(
        {
            "provider": "upstox",
            "symbols": ["INFY", "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK"],
            "windows": {
                "1d": ["2010-01-01", "2026-11-14"],
                "1m": ["2022-01-01", "2026-11-14"],
                "5m": ["2022-01-01", "2026-11-14"],
            },
            "candle_snapshot_sha256": {"1d": HASH_A, "1m": HASH_B, "5m": HASH_A},
            "action_register_sha256": HASH_B,
            "calendar_snapshot_sha256": {"daily": HASH_A, "intraday": HASH_B},
            "calendar_summary": {"daily_common_sessions": 2},
            "action_coverage_status": "unverified",
            "adjustment_basis": {
                "daily_price": "provider_adjusted_empirically_verified",
                "daily_volume": "unverified",
                "intraday_price_volume": "unverified",
            },
            "transform_version": "upstox-provider-basis-v1",
            "cost_model_version": "backtest-profile-schema-v1",
            **changes,
        }
    )


def test_calendar_hash_is_order_independent_and_preserves_symbol_specific_sessions() -> None:
    left = calendar_snapshot_sha256(
        {
            "INFY": [date(2024, 1, 2), date(2024, 1, 1)],
            "RELIANCE": [date(2024, 1, 1), date(2024, 1, 3)],
        }
    )
    right = calendar_snapshot_sha256(
        {
            "RELIANCE": [date(2024, 1, 3), date(2024, 1, 1)],
            "INFY": [date(2024, 1, 1), date(2024, 1, 2)],
        }
    )
    assert left == right
    assert left != calendar_snapshot_sha256(
        {"INFY": [date(2024, 1, 1)], "RELIANCE": [date(2024, 1, 1)]}
    )


def test_calendar_hash_rejects_empty_or_single_symbol_inputs() -> None:
    with pytest.raises(ValueError, match="at least two"):
        calendar_snapshot_sha256({"INFY": [date(2024, 1, 1)]})
    with pytest.raises(ValueError, match="non-empty"):
        calendar_snapshot_sha256({"INFY": [date(2024, 1, 1)], "TCS": []})


def test_evaluation_manifest_hash_is_stable_and_includes_action_coverage_status() -> None:
    left = manifest()
    right = manifest(symbols=["ICICIBANK", "INFY", "HDFCBANK", "RELIANCE", "TCS"])
    assert evaluation_manifest_sha256(left) == evaluation_manifest_sha256(right)
    assert evaluation_manifest_sha256(left) != evaluation_manifest_sha256(
        manifest(action_coverage_status="partial")
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"action_register_sha256": "missing"},
        {"candle_snapshot_sha256": {"1d": HASH_A}},
        {"calendar_snapshot_sha256": {"daily": HASH_A}},
        {"action_coverage_status": "complete"},
    ],
)
def test_evaluation_manifest_rejects_incomplete_or_malformed_evidence(
    changes: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        manifest(**changes)
