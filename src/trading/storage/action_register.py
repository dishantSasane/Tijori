"""Bounded, offline human-curated evidence; never infer factors or completeness."""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import Field, HttpUrl, StringConstraints, model_validator

from trading.core.enums import MarketId, Timeframe
from trading.core.models import Contract
from trading.storage.corporate_actions import (
    CorporateActionKind,
    CorporateActionNotice,
    ShareAdjustment,
)

PilotSymbol = Literal["RELIANCE", "INFY", "TCS", "HDFCBANK", "ICICIBANK"]
Basis = Literal["unknown", "raw", "provider_adjusted"]
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4096)]
ISIN = Annotated[str, StringConstraints(pattern=r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")]
MAX_REGISTER_BYTES = 262_144


class ActionRecord(Contract):
    """One event, with separate price and volume evidence for a specific dataset."""

    event_id: Text
    isin: ISIN
    symbol: PilotSymbol
    ex_date: date
    publication_date: date | None = None
    action_type: CorporateActionKind
    original_ratio: Text | None = None
    verified_factor: Decimal | None = Field(default=None, gt=0, allow_inf_nan=False)
    source_url: HttpUrl
    reviewer: Text | None = None
    review_date: date | None = None
    price_basis: Basis = "unknown"
    volume_basis: Basis = "unknown"

    @model_validator(mode="after")
    def validate_evidence(self) -> ActionRecord:
        if (self.reviewer is None) != (self.review_date is None):
            raise ValueError("reviewer and review_date must be supplied together")
        if self.review_date and self.publication_date and self.review_date < self.publication_date:
            raise ValueError("review cannot precede publication")
        if self.verified_factor is not None:
            if self.action_type not in (CorporateActionKind.SPLIT, CorporateActionKind.BONUS):
                raise ValueError("complex actions cannot carry a share factor")
            if self.verified_factor == 1 or (
                self.action_type == CorporateActionKind.BONUS and self.verified_factor < 1
            ):
                raise ValueError("invalid share factor")
            if self.original_ratio is None:
                raise ValueError("verified factor requires original ratio evidence")
        return self

    def _reviewed(self, as_of: date) -> bool:
        return bool(
            self.publication_date is not None
            and self.publication_date <= as_of
            and self.reviewer is not None
            and self.review_date is not None
            and self.review_date <= as_of
            and self.action_type in (CorporateActionKind.SPLIT, CorporateActionKind.BONUS)
        )

    def _raw(self, as_of: date) -> bool:
        return (
            self._reviewed(as_of)
            and self.price_basis == self.volume_basis == "raw"
            and self.verified_factor is not None
        )

    def _provider_adjusted(self, as_of: date) -> bool:
        return (
            self._reviewed(as_of) and self.price_basis == self.volume_basis == "provider_adjusted"
        )


class CoverageRecord(Contract):
    """Explicit inclusive symbol/window/timeframe attestation, independent of event count."""

    symbol: PilotSymbol
    timeframe: Timeframe
    candle_snapshot_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    isin: ISIN | None = None
    start: date
    end: date
    verified: bool = Field(default=False, strict=True)
    source_url: HttpUrl | None = None
    reviewer: Text | None = None
    review_date: date | None = None

    @model_validator(mode="after")
    def validate_coverage(self) -> CoverageRecord:
        if self.end < self.start:
            raise ValueError("coverage end precedes start")
        if (self.reviewer is None) != (self.review_date is None):
            raise ValueError("reviewer and review_date must be supplied together")
        if self.verified and (
            self.isin is None
            or self.source_url is None
            or self.candle_snapshot_sha256 is None
            or self.reviewer is None
            or self.review_date is None
            or self.review_date < self.end
        ):
            raise ValueError("verified coverage requires identity, source and review after window")
        return self


class ActionRegister(Contract):
    """One immutable register per dataset/basis; not a feed or an approval bypass."""

    schema_version: Literal[2] = 2
    events: tuple[ActionRecord, ...] = Field(default=(), max_length=1000)
    coverage: tuple[CoverageRecord, ...] = Field(default=(), max_length=100)

    @model_validator(mode="after")
    def validate_identity(self) -> ActionRegister:
        if len({event.event_id for event in self.events}) != len(self.events):
            raise ValueError("duplicate event ID; revisions require a new register snapshot")
        identities: dict[str, str] = {}
        symbols: dict[str, str] = {}
        for symbol, isin in (
            *((event.symbol, event.isin) for event in self.events),
            *((row.symbol, row.isin) for row in self.coverage),
        ):
            if isin is None:
                continue
            if identities.setdefault(symbol, isin) != isin:
                raise ValueError("conflicting symbol/ISIN mapping")
            if symbols.setdefault(isin, symbol) != symbol:
                raise ValueError("conflicting ISIN/symbol mapping")
        for index, window in enumerate(self.coverage):
            for previous in self.coverage[:index]:
                if (
                    window.symbol == previous.symbol
                    and window.timeframe == previous.timeframe
                    and window.start <= previous.end
                    and previous.start <= window.end
                ):
                    raise ValueError("overlapping coverage windows are ambiguous")
        return self

    def notices(self) -> tuple[CorporateActionNotice, ...]:
        """Retain ALL events, including complex, unreviewed and unpublished ones."""
        return tuple(
            CorporateActionNotice(
                symbol=event.symbol,
                kind=event.action_type,
                purpose=(
                    f"{event.action_type.value}: {event.original_ratio or 'ratio not supplied'}"
                ),
                effective_date=event.ex_date,
                source_ref=str(event.source_url),
                event_id=event.event_id,
            )
            for event in self.events
        )

    def approved_adjustments(self, *, as_of: date) -> tuple[ShareAdjustment, ...]:
        """Reviewed raw split/bonus factors only; caller still checks coverage."""
        result: list[ShareAdjustment] = []
        for event in self.events:
            if not event._raw(as_of):
                continue
            assert event.publication_date is not None and event.verified_factor is not None
            kind: Literal["split", "bonus"] = (
                "split" if event.action_type == CorporateActionKind.SPLIT else "bonus"
            )
            result.append(
                ShareAdjustment(
                    action_id=event.event_id,
                    event_id=event.event_id,
                    revision=1,
                    market=MarketId.IN_EQUITY,
                    symbol=event.symbol,
                    kind=kind,
                    published_date=event.publication_date,
                    effective_date=event.ex_date,
                    new_shares_per_old_share=event.verified_factor,
                    source_ref=str(event.source_url),
                )
            )
        return tuple(result)

    def provider_adjusted_events(self, *, as_of: date) -> tuple[ActionRecord, ...]:
        """Separate evidence, NEVER a transform ledger."""
        return tuple(event for event in self.events if event._provider_adjusted(as_of))

    def blocked_events(self, *, as_of: date) -> tuple[ActionRecord, ...]:
        """Caller scopes these blockers by symbol and inclusive ex-date window."""
        return tuple(
            event
            for event in self.events
            if not event._raw(as_of) and not event._provider_adjusted(as_of)
        )

    def covers(
        self,
        symbol: str,
        timeframe: Timeframe,
        start: date,
        end: date,
        candle_snapshot_sha256: str,
    ) -> bool:
        """Match a reviewed window to its exact immutable candle dataset."""
        if end < start:
            raise ValueError("requested end precedes start")
        return any(
            row.verified
            and row.symbol == symbol
            and row.timeframe == timeframe
            and row.candle_snapshot_sha256 == candle_snapshot_sha256
            and row.start <= start
            and end <= row.end
            for row in self.coverage
        )


def action_register_sha256(register: ActionRegister) -> str:
    """Hash normalized register content independently of YAML/list ordering."""
    payload = {
        "schema_version": register.schema_version,
        "events": sorted(
            (event.model_dump(mode="json") for event in register.events),
            key=lambda item: item["event_id"],
        ),
        "coverage": sorted(
            (row.model_dump(mode="json") for row in register.coverage),
            key=lambda item: (
                item["symbol"],
                item["timeframe"],
                item["start"],
                item["end"],
            ),
        ),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(canonical).hexdigest()


def load_action_register(path: Path) -> ActionRegister:
    """Read at most 256 KiB; reject aliases and duplicate keys before validation."""
    with path.open("rb") as stream:
        content = stream.read(MAX_REGISTER_BYTES + 1)
    if len(content) > MAX_REGISTER_BYTES:
        raise ValueError("action register exceeds 256 KiB")
    try:
        for token in yaml.scan(content):
            if isinstance(token, (yaml.tokens.AliasToken, yaml.tokens.AnchorToken)):
                raise ValueError("YAML aliases/anchors are not allowed")
        node = yaml.compose(content, Loader=yaml.SafeLoader)
        if not isinstance(node, yaml.MappingNode):
            raise ValueError("action register must be a mapping")

        def check_keys(current: yaml.Node) -> None:
            if isinstance(current, yaml.MappingNode):
                keys: set[str] = set()
                for key, value in current.value:
                    if not isinstance(key, yaml.ScalarNode) or key.value in keys:
                        raise ValueError("duplicate or non-scalar YAML key")
                    keys.add(key.value)
                    check_keys(value)
            elif isinstance(current, yaml.SequenceNode):
                for child in current.value:
                    check_keys(child)

        check_keys(node)
        return ActionRegister.model_validate(yaml.safe_load(content))
    except (yaml.YAMLError, RecursionError) as error:
        raise ValueError("invalid action register YAML") from error
