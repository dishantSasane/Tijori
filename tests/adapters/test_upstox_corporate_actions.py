import json
from datetime import UTC, datetime
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pytest

from trading.adapters.upstox_corporate_actions import (
    UpstoxCorporateActionsClient,
    UpstoxCorporateActionsError,
    UpstoxCorporateActionsSnapshot,
    _request,
)


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
                    {"name": "Details", "value": "Second provider detail"},
                ],
            }
        ],
    }

    def fake_request(url: str, headers: dict[str, str]) -> bytes:
        calls.append((url, headers))
        return json.dumps(response).encode()

    raw_response = json.dumps(response).encode()
    snapshot = UpstoxCorporateActionsClient(
        requester=fake_request,
        clock=lambda: datetime(2026, 11, 15, tzinfo=UTC),
    ).fetch("INE239A01016", access_token="test-token")

    assert isinstance(snapshot, UpstoxCorporateActionsSnapshot)
    assert snapshot.raw_response == raw_response
    assert snapshot.response_sha256 == sha256(raw_response).hexdigest()
    assert snapshot.parser_version == "1"
    assert snapshot.source_ref == calls[0][0]
    assert snapshot.retrieved_at_utc == datetime(2026, 11, 15, tzinfo=UTC)
    assert calls == [
        (
            "https://api.upstox.com/v2/fundamentals/INE239A01016/corporate-actions",
            {"Accept": "application/json", "Authorization": "Bearer test-token"},
        )
    ]
    events = snapshot.events

    assert len(events) == 1
    assert events[0].name == "Split"
    assert events[0].effective_date.isoformat() == "2024-01-05"
    assert events[0].ratio_text == "10:1"
    assert events[0].details == (
        ("Ex date", "05 Jan 2024"),
        ("Details", "Face value subdivision"),
        ("Details", "Second provider detail"),
    )


def test_demerger_and_rights_are_preserved_for_downstream_review_screen() -> None:
    response = {
        "status": "success",
        "data": [
            {"name": "Demerger", "expiry_date": "2025-02-03", "ratio": None},
            {"name": "Rights", "expiry_date": "2025-03-04", "ratio": "1:5"},
        ],
    }

    snapshot = UpstoxCorporateActionsClient(
        requester=lambda _url, _headers: json.dumps(response).encode()
    ).fetch("INE000A01001", access_token="test-token")

    assert [event.name for event in snapshot.events] == ["Demerger", "Rights"]


def test_empty_token_fails_before_making_request() -> None:
    called = False

    def fake_request(_url: str, _headers: dict[str, str]) -> bytes:
        nonlocal called
        called = True
        return b'{"status":"success","data":[]}'

    try:
        UpstoxCorporateActionsClient(requester=fake_request).fetch("INE239A01016", access_token=" ")
    except ValueError as error:
        assert "access token is required" in str(error)
    else:
        raise AssertionError("empty token must be rejected")
    assert not called


def test_empty_response_keeps_endpoint_provenance() -> None:
    snapshot = UpstoxCorporateActionsClient(
        requester=lambda _url, _headers: b'{"status":"success","data":[]}',
        clock=lambda: datetime(2026, 11, 15, tzinfo=UTC),
    ).fetch("INE239A01016", access_token="test-token")

    assert snapshot.events == ()
    assert snapshot.source_ref.endswith("/INE239A01016/corporate-actions")


def test_authenticated_request_never_follows_redirect_to_another_host() -> None:
    target_authorizations: list[str | None] = []

    class TargetHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            target_authorizations.append(self.headers.get("Authorization"))
            self.send_response(200)
            self.end_headers()

        def log_message(self, _format: str, *_args: object) -> None:
            pass

    target = ThreadingHTTPServer(("127.0.0.1", 0), TargetHandler)
    target_thread = Thread(target=target.serve_forever)
    target_thread.start()
    target_url = f"http://127.0.0.1:{target.server_port}/capture"

    class RedirectHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_response(302)
            self.send_header("Location", target_url)
            self.end_headers()

        def log_message(self, _format: str, *_args: object) -> None:
            pass

    redirect = ThreadingHTTPServer(("127.0.0.1", 0), RedirectHandler)
    redirect_thread = Thread(target=redirect.serve_forever)
    redirect_thread.start()
    try:
        with pytest.raises(UpstoxCorporateActionsError, match="HTTP 302"):
            _request(
                f"http://127.0.0.1:{redirect.server_port}/redirect",
                {"Authorization": "Bearer fake-secret"},
            )
        assert target_authorizations == []
    finally:
        redirect.shutdown()
        redirect.server_close()
        redirect_thread.join()
        target.shutdown()
        target.server_close()
        target_thread.join()


def test_explicit_user_agent_keeps_authentication_header() -> None:
    calls = []

    def request(url, headers):
        calls.append(headers)
        return b'{"status":"success","data":[]}'

    UpstoxCorporateActionsClient(requester=request, user_agent="Mozilla/5.0").fetch(
        "INE002A01018", access_token="fake"
    )
    assert calls[0]["User-Agent"] == "Mozilla/5.0"
    assert calls[0]["Authorization"] == "Bearer fake"
