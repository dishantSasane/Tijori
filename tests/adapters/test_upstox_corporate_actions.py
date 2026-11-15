import json

from trading.adapters.upstox_corporate_actions import UpstoxCorporateActionsClient


def test_fetches_upstox_corporate_actions_and_preserves_uninterpreted_ratio() -> None:
    calls: list[tuple[str, dict[str, str]]] = []
    response = {
        "status": "success",
        "data": [
            {
                "name": "Split",
                "expiry_date": "05 Jan 2024",
                "amount": None,
                "ratio": "10:1",
                "event_details": [
                    {"name": "Ex date", "value": "05 Jan 2024"},
                    {"name": "Details", "value": "Face value subdivision"},
                ],
            }
        ],
    }

    def fake_request(url: str, headers: dict[str, str]) -> bytes:
        calls.append((url, headers))
        return json.dumps(response).encode()

    events = UpstoxCorporateActionsClient(requester=fake_request).fetch(
        "INE239A01016", access_token="test-token"
    )

    assert calls == [
        (
            "https://api.upstox.com/v2/fundamentals/INE239A01016/corporate-actions",
            {"Accept": "application/json", "Authorization": "Bearer test-token"},
        )
    ]
    assert len(events) == 1
    assert events[0].name == "Split"
    assert events[0].effective_date.isoformat() == "2024-01-05"
    assert events[0].ratio_text == "10:1"
    assert events[0].details["Details"] == "Face value subdivision"


def test_demerger_and_rights_are_preserved_for_downstream_review_screen() -> None:
    response = {
        "status": "success",
        "data": [
            {"name": "Demerger", "expiry_date": "2025-02-03", "ratio": None},
            {"name": "Rights", "expiry_date": "2025-03-04", "ratio": "1:5"},
        ],
    }

    events = UpstoxCorporateActionsClient(
        requester=lambda _url, _headers: json.dumps(response).encode()
    ).fetch("INE000A01001", access_token="test-token")

    assert [event.name for event in events] == ["Demerger", "Rights"]
