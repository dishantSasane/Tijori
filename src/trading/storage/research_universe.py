"""Deterministic point-in-time turnover universe selection.

This module consumes normalized, provenance-bearing records. It deliberately
does not fetch or parse provider files; source authorization and completeness
must be established before real observations are supplied.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal, localcontext

from pydantic import Field, field_validator, model_validator

from trading.core.models import Contract
from trading.storage.membership import _isin_checksum_is_valid


class ResearchInstrument(Contract):
    """Eligibility and verified history for one Indian equity identity."""

    isin: str = Field(min_length=12, max_length=12, pattern=r"^IN[A-Z0-9]{9}[0-9]$")
    active_as_of: bool
    eligible: bool | None
    verified_history_start: date

    @field_validator("isin")
    @classmethod
    def _check_isin(cls, value: str) -> str:
        if not _isin_checksum_is_valid(value):
            raise ValueError("ISIN check digit is invalid")
        return value

    @field_validator("eligible")
    @classmethod
    def _require_known_eligibility(cls, value: bool | None) -> bool:
        if value is None:
            raise ValueError("unknown instrument eligibility fails closed")
        return value


class TurnoverObservation(Contract):
    """One normalized turnover fact for a session and ISIN."""

    session_date: date
    isin: str = Field(min_length=12, max_length=12, pattern=r"^IN[A-Z0-9]{9}[0-9]$")
    turnover_inr: Decimal = Field(ge=0)
    explicit_zero: bool

    @field_validator("isin")
    @classmethod
    def _check_isin(cls, value: str) -> str:
        if not _isin_checksum_is_valid(value):
            raise ValueError("ISIN check digit is invalid")
        return value

    @model_validator(mode="after")
    def _check_zero_evidence(self) -> TurnoverObservation:
        if self.turnover_inr == 0 and not self.explicit_zero:
            raise ValueError("zero turnover requires explicit source confirmation")
        return self


class RawFileProvenance(Contract):
    identifier: str = Field(min_length=1)
    checksum: str = Field(min_length=1)


class UniverseProvenance(Contract):
    universe_version: str = Field(min_length=1)
    eligible_set_rule_version: str = Field(min_length=1)
    source_reference: str = Field(min_length=1)
    licence_reference: str = Field(min_length=1)
    raw_files: tuple[RawFileProvenance, ...] = Field(min_length=1)
    parser_version: str = Field(min_length=1)


class RankedCandidate(Contract):
    isin: str
    median_turnover_inr: Decimal = Field(ge=0)


class ExcludedInstrument(Contract):
    isin: str
    reason: str = Field(min_length=1)


class MonthlyUniverseSnapshot(Contract):
    universe_version: str
    eligible_set_rule_version: str
    source_reference: str
    licence_reference: str
    raw_files: tuple[RawFileProvenance, ...]
    parser_version: str
    k: int = Field(gt=0)
    lookback_length: int = Field(gt=0)
    lookback_sessions: tuple[date, ...] = Field(min_length=1)
    as_of_date: date
    effective_date: date
    ranked_candidates: tuple[RankedCandidate, ...]
    exclusions: tuple[ExcludedInstrument, ...]
    selected_isins: tuple[str, ...]


def _median(values: list[Decimal]) -> Decimal:
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    left, right = ordered[middle - 1], ordered[middle]
    exponents = (left.as_tuple().exponent, right.as_tuple().exponent)
    if not all(isinstance(exponent, int) for exponent in exponents):
        raise ValueError("turnover values must be finite decimals")
    precision = (
        max(len(left.as_tuple().digits), len(right.as_tuple().digits))
        + max(abs(exponent) for exponent in exponents if isinstance(exponent, int))
        + 4
    )
    with localcontext() as context:
        context.prec = max(context.prec, precision)
        return (left + right) / Decimal(2)


def build_snapshot(
    sessions: list[date] | tuple[date, ...],
    effective_date: date,
    instruments: list[ResearchInstrument] | tuple[ResearchInstrument, ...],
    observations: list[TurnoverObservation] | tuple[TurnoverObservation, ...],
    provenance: UniverseProvenance,
    k: int,
) -> MonthlyUniverseSnapshot:
    """Build one monthly snapshot from normalized inputs, failing closed."""
    if isinstance(k, bool) or not isinstance(k, int) or k <= 0:
        raise ValueError("k must be positive")
    if len(sessions) < 61:
        raise ValueError("calendar must include 60 lookback sessions and the prior session")
    if any(
        current >= following for current, following in zip(sessions, sessions[1:], strict=False)
    ):
        raise ValueError("sessions must be unique and strictly increasing")
    month_start = date(effective_date.year, effective_date.month, 1)
    first_month_session = next((day for day in sessions if day >= month_start), None)
    if effective_date != first_month_session:
        raise ValueError("effective_date must be the first supplied session of its month")
    effective_index = sessions.index(effective_date)
    if effective_index < 60:
        raise ValueError("calendar lacks 60 sessions preceding effective_date")
    lookback = tuple(sessions[effective_index - 60 : effective_index])
    as_of_date = lookback[-1]

    instruments_by_isin: dict[str, ResearchInstrument] = {}
    for instrument in instruments:
        if instrument.isin in instruments_by_isin:
            raise ValueError(f"duplicate instrument identity: {instrument.isin}")
        instruments_by_isin[instrument.isin] = instrument

    observations_by_identity: dict[tuple[date, str], Decimal] = {}
    for observation in observations:
        if observation.isin not in instruments_by_isin:
            raise ValueError(f"observation references unknown ISIN: {observation.isin}")
        key = (observation.session_date, observation.isin)
        if key in observations_by_identity:
            raise ValueError(f"duplicate turnover observation: {key}")
        observations_by_identity[key] = observation.turnover_inr

    values_by_isin: dict[str, list[Decimal]] = defaultdict(list)
    for instrument in instruments:
        if instrument.eligible is None:
            raise ValueError(f"unknown eligibility: {instrument.isin}")
        if not instrument.active_as_of:
            continue
        if not instrument.eligible:
            continue
        if instrument.verified_history_start > lookback[0]:
            continue
        for session in lookback:
            key = (session, instrument.isin)
            if key not in observations_by_identity:
                raise ValueError(f"missing turnover observation: {key}")
            values_by_isin[instrument.isin].append(observations_by_identity[key])

    exclusions: list[ExcludedInstrument] = []
    for instrument in instruments:
        if not instrument.active_as_of:
            reason = "inactive_as_of"
        elif not instrument.eligible:
            reason = "ineligible_instrument_class"
        elif instrument.verified_history_start > lookback[0]:
            reason = "less_than_60_sessions_verified_history"
        else:
            continue
        exclusions.append(ExcludedInstrument(isin=instrument.isin, reason=reason))

    ranked = sorted(
        (
            RankedCandidate(isin=isin, median_turnover_inr=_median(values))
            for isin, values in values_by_isin.items()
        ),
        key=lambda candidate: (-candidate.median_turnover_inr, candidate.isin),
    )
    if len(ranked) < k:
        raise ValueError(f"fewer than k eligible candidates: found {len(ranked)}, need {k}")

    return MonthlyUniverseSnapshot(
        universe_version=provenance.universe_version,
        eligible_set_rule_version=provenance.eligible_set_rule_version,
        source_reference=provenance.source_reference,
        licence_reference=provenance.licence_reference,
        raw_files=provenance.raw_files,
        parser_version=provenance.parser_version,
        k=k,
        lookback_length=60,
        lookback_sessions=lookback,
        as_of_date=as_of_date,
        effective_date=effective_date,
        ranked_candidates=tuple(ranked),
        exclusions=tuple(sorted(exclusions, key=lambda exclusion: exclusion.isin)),
        selected_isins=tuple(candidate.isin for candidate in ranked[:k]),
    )
