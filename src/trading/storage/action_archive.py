"""Persist exact Upstox action evidence and map events to review notices."""

from __future__ import annotations

import os
import tempfile
from hashlib import sha256
from pathlib import Path

from trading.adapters.upstox_corporate_actions import UpstoxCorporateActionsSnapshot
from trading.storage.corporate_actions import CorporateActionNotice, classify_corporate_action


def save_action_snapshot(snapshot: UpstoxCorporateActionsSnapshot, directory: Path) -> Path:
    """Atomically save one response envelope; never infer coverage from its events."""
    if sha256(snapshot.raw_response).hexdigest() != snapshot.response_sha256:
        raise ValueError("corporate-action response checksum mismatch")
    directory.mkdir(parents=True, exist_ok=True)
    payload = snapshot.model_dump_json(indent=2).encode()
    identity = sha256(payload).hexdigest()
    destination = directory / f"{snapshot.isin}-{identity}.json"
    if destination.exists():
        if destination.read_bytes() != payload:
            raise ValueError("existing corporate-action archive is corrupt")
        return destination
    descriptor, temporary = tempfile.mkstemp(dir=directory, prefix=".action-")
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return destination


def action_notices(
    snapshot: UpstoxCorporateActionsSnapshot, *, symbols_by_isin: dict[str, str]
) -> list[CorporateActionNotice]:
    """Require an explicit ISIN mapping; retain unsupported actions for screening."""
    symbol = symbols_by_isin.get(snapshot.isin, "").strip().upper()
    if not symbol:
        raise ValueError("corporate-action ISIN has no verified symbol mapping")
    notices = []
    for index, event in enumerate(snapshot.events):
        if event.isin != snapshot.isin:
            raise ValueError("corporate-action event ISIN differs from response ISIN")
        purpose = " | ".join([event.name, *(value for _, value in event.details)])
        notices.append(
            CorporateActionNotice(
                symbol=symbol,
                # Provider event name is the type field. Detail text may mention
                # a different action and must never upgrade an unknown type.
                kind=classify_corporate_action(event.name),
                purpose=purpose,
                effective_date=event.effective_date,
                source_ref=f"{snapshot.source_ref}#sha256={snapshot.response_sha256}",
                event_id=sha256(
                    (
                        f"{snapshot.response_sha256}|{index}|{event.name}|"
                        f"{event.effective_date.isoformat()}"
                    ).encode()
                ).hexdigest(),
            )
        )
    return notices
