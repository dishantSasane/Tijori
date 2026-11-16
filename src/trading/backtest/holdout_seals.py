"""Canonical identities for the frozen P1 shortlist sent to holdout."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from hashlib import sha256

from pydantic import Field, computed_field, model_validator

from trading.core.models import Contract

_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")
_BOUND_HASH_FIELDS = (
    "catalog_hash",
    "rejection_rule_hash",
    "metrics_hash",
    "family_hash",
    "dataset_manifest_hash",
)


def shortlist_sha256(
    candidates: Sequence[Mapping[str, object]],
    *,
    catalog_hash: str,
    rejection_rule_hash: str,
    metrics_hash: str,
    family_hash: str,
    dataset_manifest_hash: str,
) -> str:
    """Hash an order-independent candidate list and every decision contract.

    Candidate definitions must include a unique ``candidate_id`` and all
    frozen parameters. The seal changes if a candidate, parameter, catalog,
    rejection rule, metric definition, trial family, or source manifest changes.
    """
    if not candidates:
        raise ValueError("shortlist must contain at least one candidate")
    hash_values = {
        "catalog_hash": catalog_hash,
        "rejection_rule_hash": rejection_rule_hash,
        "metrics_hash": metrics_hash,
        "family_hash": family_hash,
        "dataset_manifest_hash": dataset_manifest_hash,
    }
    for field in _BOUND_HASH_FIELDS:
        value = hash_values[field]
        if not isinstance(value, str) or not _SHA256_HEX.fullmatch(value):
            raise ValueError(f"{field} must be a lowercase SHA-256 hex digest")

    normalized_candidates = [dict(candidate) for candidate in candidates]
    candidate_ids = [candidate.get("candidate_id") for candidate in normalized_candidates]
    if any(not isinstance(candidate_id, str) or not candidate_id for candidate_id in candidate_ids):
        raise ValueError("every shortlisted candidate requires a non-empty candidate_id")
    if len(candidate_ids) != len(set(candidate_ids)):
        raise ValueError("shortlist candidate IDs must be unique")
    normalized_candidates.sort(key=lambda candidate: str(candidate["candidate_id"]))
    payload = {
        "candidates": normalized_candidates,
        "catalog_hash": catalog_hash,
        "rejection_rule_hash": rejection_rule_hash,
        "metrics_hash": metrics_hash,
        "family_hash": family_hash,
        "dataset_manifest_hash": dataset_manifest_hash,
    }
    try:
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as error:
        raise ValueError("shortlist definition must be finite JSON data") from error
    return sha256(canonical.encode("utf-8")).hexdigest()


class SealedShortlist(Contract):
    """Exact, hash-bound P1d candidate definitions allowed onto holdout."""

    candidates: tuple[dict[str, object], ...] = Field(min_length=1)
    catalog_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    rejection_rule_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    metrics_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    family_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    dataset_manifest_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _validate_candidates(self) -> SealedShortlist:
        for candidate in self.candidates:
            if not isinstance(candidate.get("candidate_id"), str) or not candidate["candidate_id"]:
                raise ValueError("every shortlisted candidate requires a non-empty candidate_id")
            if (
                not isinstance(candidate.get("candidate_version"), str)
                or not candidate["candidate_version"]
            ):
                raise ValueError(
                    "every shortlisted candidate requires a non-empty candidate_version"
                )
            if not isinstance(candidate.get("parameters"), dict):
                raise ValueError("every shortlisted candidate requires object parameters")
            try:
                json.dumps(candidate["parameters"], sort_keys=True, allow_nan=False)
            except (TypeError, ValueError) as error:
                raise ValueError("shortlist parameters must be finite JSON data") from error
        return self

    @computed_field  # type: ignore[prop-decorator]  # Pydantic computed-field pattern
    @property
    def shortlist_hash(self) -> str:
        return shortlist_sha256(
            self.candidates,
            catalog_hash=self.catalog_hash,
            rejection_rule_hash=self.rejection_rule_hash,
            metrics_hash=self.metrics_hash,
            family_hash=self.family_hash,
            dataset_manifest_hash=self.dataset_manifest_hash,
        )

    def contains(
        self,
        *,
        candidate_id: str,
        candidate_version: str,
        parameters_json: str,
        catalog_hash: str,
    ) -> bool:
        """Whether an experiment exactly matches a frozen candidate definition."""
        if catalog_hash != self.catalog_hash:
            return False
        try:
            parameters = json.loads(parameters_json)
        except json.JSONDecodeError:
            return False
        return any(
            candidate["candidate_id"] == candidate_id
            and candidate["candidate_version"] == candidate_version
            and candidate["parameters"] == parameters
            for candidate in self.candidates
        )
