"""Tests the budget/cache/schema wiring around the real provider WITHOUT
importing the `anthropic` package or making a network call (AGENTS.md §4.4,
§6 instruction to never call a real paid API in tests). A tiny fake stands
in for the SDK client and is injected via monkeypatching `sys.modules`
before `AnthropicBrainProvider.__init__` does its lazy `import anthropic`.
"""

from __future__ import annotations

import json
import sys
import types
from datetime import UTC, datetime
from decimal import Decimal

from trading.brain.budget_guard import BudgetGuard
from trading.core.enums import MarketId, OrderSide, Timeframe
from trading.core.models import Signal
from trading.storage.state_db import connect

TS = datetime(2026, 1, 1, tzinfo=UTC)


class _FixedClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


def _signal() -> Signal:
    return Signal(
        market=MarketId.IN_EQUITY,
        symbol="RELIANCE",
        timeframe=Timeframe.D1,
        strategy_id="t1",
        strategy_version="v1",
        side=OrderSide.BUY,
        entry_ref=Decimal(100),
        stop=Decimal(95),
        bar_ts_utc=TS,
        created_ts=TS,
    )


class _FakeUsage:
    def __init__(self, tokens_in: int, tokens_out: int) -> None:
        self.input_tokens = tokens_in
        self.output_tokens = tokens_out


class _FakeBlock:
    def __init__(self, text: str) -> None:
        self.type = "text"
        self.text = text


class _FakeMessages:
    def __init__(self, response_text: str) -> None:
        self._response_text = response_text
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        return types.SimpleNamespace(
            content=[_FakeBlock(self._response_text)], usage=_FakeUsage(100, 20)
        )


class _FakeAnthropicClient:
    def __init__(self, response_text: str, api_key: str) -> None:
        self.messages = _FakeMessages(response_text)


def _install_fake_anthropic(monkeypatch, response_text: str) -> _FakeAnthropicClient:
    fake_module = types.ModuleType("anthropic")
    client_holder: dict[str, _FakeAnthropicClient] = {}

    def _anthropic_factory(api_key: str) -> _FakeAnthropicClient:
        client = _FakeAnthropicClient(response_text, api_key)
        client_holder["client"] = client
        return client

    fake_module.Anthropic = _anthropic_factory  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "anthropic", fake_module)
    return client_holder


def _make_provider(monkeypatch, response_text: str, *, daily_cap=Decimal(1000)):
    from trading.brain.anthropic_provider import AnthropicBrainProvider

    client_holder = _install_fake_anthropic(monkeypatch, response_text)
    conn = connect(":memory:")
    guard = BudgetGuard(conn, daily_cap_inr=daily_cap, monthly_cap_inr=Decimal(100000))
    provider = AnthropicBrainProvider(
        api_key="fake",
        model="claude-fake",
        budget_guard=guard,
        clock=_FixedClock(TS),
    )
    return provider, guard, client_holder


def test_valid_response_returns_verdict_and_logs_spend(monkeypatch):
    signal = _signal()
    payload = json.dumps(
        {"signal_id": signal.id, "label": "support", "size_multiplier": 1.0, "reasons": []}
    )
    provider, guard, _ = _make_provider(monkeypatch, payload)
    verdict = provider.get_verdict(signal, context="ctx")
    assert verdict is not None
    assert verdict.label.value == "support"
    assert guard.status(TS).spent_today_inr > Decimal(0)


def test_malformed_response_returns_none_but_still_logs_spend(monkeypatch):
    signal = _signal()
    provider, guard, _ = _make_provider(monkeypatch, "not json")
    verdict = provider.get_verdict(signal, context="ctx")
    assert verdict is None
    assert guard.status(TS).spent_today_inr > Decimal(0)  # tokens were spent either way


def test_budget_exceeded_blocks_the_call_entirely(monkeypatch):
    signal = _signal()
    payload = json.dumps(
        {"signal_id": signal.id, "label": "support", "size_multiplier": 1.0, "reasons": []}
    )
    provider, guard, client_holder = _make_provider(monkeypatch, payload, daily_cap=Decimal(0))
    verdict = provider.get_verdict(signal, context="ctx")
    assert verdict is None
    assert client_holder["client"].messages.calls == 0  # never even called the provider


def test_second_call_with_same_context_is_served_from_cache(monkeypatch):
    signal = _signal()
    payload = json.dumps(
        {"signal_id": signal.id, "label": "support", "size_multiplier": 1.0, "reasons": []}
    )
    provider, guard, client_holder = _make_provider(monkeypatch, payload)
    provider.get_verdict(signal, context="ctx")
    spent_after_first = guard.status(TS).spent_today_inr
    provider.get_verdict(signal, context="ctx")
    assert client_holder["client"].messages.calls == 1
    assert guard.status(TS).spent_today_inr == spent_after_first  # no second spend
