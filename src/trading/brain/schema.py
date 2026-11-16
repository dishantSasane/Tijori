"""Strict parsing of the Brain's raw provider output into a `BrainVerdict`.

Anything that doesn't match exactly is a parse failure -> `None` (treated as
absent/neutral by the risk engine, AGENTS.md §4.6, I8). This is the second
line of defense named in docs/specs/RED_TEAM.md §1: no text the Brain saw,
including an injected instruction in a headline, can produce anything other
than a validated `support|neutral|veto` + a size multiplier in [0, 1] --
there is no code path from "the model said something unexpected" to an
order, a price, or a limit change.
"""

from __future__ import annotations

import json
from datetime import datetime

from pydantic import ValidationError

from trading.core.models import BrainVerdict

MAX_REASONS = 3
MAX_REASON_LEN = 120


def parse_verdict(raw_text: str, *, expected_signal_id: str, now: datetime) -> BrainVerdict | None:
    """`raw_text` is the provider's full response text. Returns `None` (never
    raises) on malformed JSON, a schema mismatch, a `signal_id` that doesn't
    match the request, or reasons that violate the count/length caps in
    docs/BRAIN_AND_COSTS.md §3.
    """
    try:
        data = json.loads(raw_text)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    # `BrainVerdict` (trading.core.models, P0) doesn't model `news_refs` --
    # it's audit-only context per docs/BRAIN_AND_COSTS.md §3, not consumed by
    # risk/sizing. `Contract` is `extra="forbid"`, so pop it here rather than
    # widen a P0 core contract for a field nothing reads yet (see
    # docs/decisions.md ADR for this phase).
    data.pop("news_refs", None)
    data.setdefault("created_ts", now)
    try:
        verdict = BrainVerdict.model_validate(data)
    except ValidationError:
        return None
    if verdict.signal_id != expected_signal_id:
        return None
    if len(verdict.reasons) > MAX_REASONS:
        return None
    if any(len(r) > MAX_REASON_LEN for r in verdict.reasons):
        return None
    return verdict
