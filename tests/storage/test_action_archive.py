import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from trading.adapters.upstox_corporate_actions import UpstoxCorporateActionsClient
from trading.storage.action_archive import action_notices, save_action_snapshot
from trading.storage.corporate_actions import CorporateActionKind


def snapshot():
    raw = json.dumps(
        {
            "status": "success",
            "data": [
                {
                    "name": "Scheme of arrangement",
                    "expiry_date": "2024-01-05",
                    "event_details": [{"name": "Details", "value": "Demerger of undertaking"}],
                },
                {"name": "Rights", "expiry_date": "2024-02-05", "ratio": "1:5"},
            ],
        }
    ).encode()
    return UpstoxCorporateActionsClient(
        requester=lambda _u, _h: raw, clock=lambda: datetime(2026, 11, 15, tzinfo=UTC)
    ).fetch("INE002A01018", access_token="fake")


def test_archive_retains_exact_evidence_and_is_idempotent(tmp_path: Path) -> None:
    item = snapshot()
    path = save_action_snapshot(item, tmp_path)
    restored = type(item).model_validate_json(path.read_bytes())
    assert restored == item
    assert save_action_snapshot(item, tmp_path) == path
    assert len(list(tmp_path.iterdir())) == 1
    path.write_text("corrupted")
    with pytest.raises(ValueError, match="corrupt"):
        save_action_snapshot(item, tmp_path)


def test_bad_checksum_cannot_be_archived(tmp_path: Path) -> None:
    item = snapshot().model_copy(update={"response_sha256": "0" * 64})
    with pytest.raises(ValueError, match="checksum"):
        save_action_snapshot(item, tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_mapping_and_details_keep_complex_events_visible() -> None:
    item = snapshot()
    with pytest.raises(ValueError, match="mapping"):
        action_notices(item, symbols_by_isin={})
    notices = action_notices(item, symbols_by_isin={"INE002A01018": "RELIANCE"})
    assert [n.kind for n in notices] == [CorporateActionKind.OTHER, CorporateActionKind.RIGHTS]
    assert "Demerger of undertaking" in notices[0].purpose
    assert all(item.response_sha256 in n.source_ref for n in notices)
