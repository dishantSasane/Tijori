"""Real `LLMProvider` against the Anthropic API (docs/BRAIN_AND_COSTS.md §4
names Anthropic/OpenAI as the two swappable choices; Anthropic is the
default since the owner already has an Anthropic-side agent on this repo).

Wraps every call with the budget guard (checked BEFORE spending a token),
the shared context cache (checked first, so an unchanged signal/context never
pays twice), and strict schema parsing (`brain/schema.py`) so a malformed or
adversarial response can never reach the risk engine as anything but `None`.
Every attempted call is logged via `BudgetGuard.record_call` regardless of
outcome (AGENTS.md §4.8).

The `anthropic` package is only imported when this class is instantiated --
tests and the rest of the system never need it installed; they use
`FakeLLMProvider` (`trading.adapters.llm_provider`).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Protocol

from trading.brain.budget_guard import BudgetGuard
from trading.brain.context_cache import ContextCache
from trading.brain.schema import parse_verdict
from trading.core.models import BrainVerdict, Signal


class Clock(Protocol):
    def now(self) -> datetime: ...


# INR per raw token, configured (not hardcoded) because prices change
# (docs/BRAIN_AND_COSTS.md §5). These are placeholder defaults for the
# cheapest current Anthropic tier the owner should confirm before spending
# real money -- see the needs-human handoff note for this phase.
DEFAULT_PRICE_PER_INPUT_TOKEN_INR = Decimal("0.0025")
DEFAULT_PRICE_PER_OUTPUT_TOKEN_INR = Decimal("0.0125")


class AnthropicBrainProvider:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        budget_guard: BudgetGuard,
        clock: Clock,
        cache: ContextCache | None = None,
        price_per_input_token_inr: Decimal = DEFAULT_PRICE_PER_INPUT_TOKEN_INR,
        price_per_output_token_inr: Decimal = DEFAULT_PRICE_PER_OUTPUT_TOKEN_INR,
        max_tokens: int = 200,
    ) -> None:
        import anthropic  # noqa: PLC0415 - deliberately lazy, see module docstring

        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model
        self._budget = budget_guard
        self._clock = clock
        self._cache = cache or ContextCache(ttl=timedelta(hours=4))
        self._price_in = price_per_input_token_inr
        self._price_out = price_per_output_token_inr
        self._max_tokens = max_tokens

    def get_verdict(self, signal: Signal, context: str) -> BrainVerdict | None:
        now = self._clock.now()

        cached = self._cache.get(signal.id, context, now=now)
        if cached is not None:
            return cached

        if not self._budget.allow(now):
            # Fail closed: refuse the call outright, never make it and
            # discard the result (that would still spend money).
            return None

        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                messages=[{"role": "user", "content": context}],
            )
        except Exception:  # noqa: BLE001 - any provider failure => absent verdict, not a crash
            return None

        raw_text = "".join(
            block.text for block in response.content if getattr(block, "type", None) == "text"
        )
        tokens_in = response.usage.input_tokens
        tokens_out = response.usage.output_tokens
        cost_inr = tokens_in * self._price_in + tokens_out * self._price_out

        verdict = parse_verdict(raw_text, expected_signal_id=signal.id, now=now)

        self._budget.record_call(
            now=now,
            provider="anthropic",
            model=self._model,
            purpose="signal_context_verdict",
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_inr=cost_inr,
            signal_id=signal.id,
            ok=verdict is not None,
        )

        if verdict is not None:
            self._cache.put(signal.id, context, verdict, now=now)
        return verdict
