import pytest

from trading.backtest.holdout_seals import shortlist_sha256


def test_shortlist_hash_is_order_independent_and_binds_exact_candidate_definitions() -> None:
    first = [
        {"candidate_id": "t1-a-v1", "parameters": {"lookback": 20}},
        {"candidate_id": "t4-b-v1", "parameters": {"threshold": 10}},
    ]
    reordered = list(reversed(first))
    common = {
        "catalog_hash": "a" * 64,
        "rejection_rule_hash": "b" * 64,
        "metrics_hash": "c" * 64,
        "family_hash": "d" * 64,
        "dataset_manifest_hash": "e" * 64,
    }

    original_hash = shortlist_sha256(first, **common)

    assert original_hash == shortlist_sha256(reordered, **common)
    changed = [first[0], {**first[1], "parameters": {"threshold": 12}}]
    assert original_hash != shortlist_sha256(changed, **common)


def test_shortlist_seal_rejects_duplicate_ids_and_malformed_identity_hashes() -> None:
    common = {
        "catalog_hash": "a" * 64,
        "rejection_rule_hash": "b" * 64,
        "metrics_hash": "c" * 64,
        "family_hash": "d" * 64,
        "dataset_manifest_hash": "e" * 64,
    }
    duplicate = [
        {"candidate_id": "same", "parameters": {}},
        {"candidate_id": "same", "parameters": {}},
    ]
    with pytest.raises(ValueError, match="unique"):
        shortlist_sha256(duplicate, **common)

    with pytest.raises(ValueError, match="SHA-256"):
        shortlist_sha256(
            [{"candidate_id": "t1-a-v1", "parameters": {}}],
            **{**common, "catalog_hash": "not-a-hash"},
        )
