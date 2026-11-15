"""Immutable machine-readable rules for the frozen P1 candidate family."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True)
class P1Candidate:
    candidate_id: str
    family: str
    timeframe: str
    parameters: tuple[tuple[str, int | float], ...]


_CANDIDATES = (
    P1Candidate(
        "t1-donchian-n20-m10-k2-v1",
        "T1",
        "1d",
        (("entry_n", 20), ("exit_m", 10), ("atr_k", 2)),
    ),
    P1Candidate(
        "t1-donchian-n10-m10-k2-v1",
        "T1",
        "1d",
        (("entry_n", 10), ("exit_m", 10), ("atr_k", 2)),
    ),
    P1Candidate(
        "t1-donchian-n40-m10-k2-v1",
        "T1",
        "1d",
        (("entry_n", 40), ("exit_m", 10), ("atr_k", 2)),
    ),
    P1Candidate(
        "t2-ema20-50-adx25-v1",
        "T2",
        "1d",
        (("fast_ema", 20), ("slow_ema", 50), ("adx_threshold", 25), ("atr_k", 2)),
    ),
    P1Candidate(
        "t2-ema10-50-adx25-v1",
        "T2",
        "1d",
        (("fast_ema", 10), ("slow_ema", 50), ("adx_threshold", 25), ("atr_k", 2)),
    ),
    P1Candidate(
        "t2-ema20-100-adx25-v1",
        "T2",
        "1d",
        (("fast_ema", 20), ("slow_ema", 100), ("adx_threshold", 25), ("atr_k", 2)),
    ),
    P1Candidate(
        "t4-rsi2-10-atr25-v1",
        "T4",
        "1d",
        (("rsi_threshold", 10), ("atr_k", 2.5), ("time_stop", 5)),
    ),
    P1Candidate(
        "t4-rsi2-5-atr25-v1",
        "T4",
        "1d",
        (("rsi_threshold", 5), ("atr_k", 2.5), ("time_stop", 5)),
    ),
    P1Candidate(
        "t4-rsi2-15-atr25-v1",
        "T4",
        "1d",
        (("rsi_threshold", 15), ("atr_k", 2.5), ("time_stop", 5)),
    ),
    P1Candidate(
        "t6-bollinger20-2-v1",
        "T6",
        "1d",
        (("period", 20), ("band_width", 2), ("adx_max", 20), ("atr_k", 1.5), ("time_stop", 10)),
    ),
    P1Candidate(
        "t6-bollinger20-15-v1",
        "T6",
        "1d",
        (("period", 20), ("band_width", 1.5), ("adx_max", 20), ("atr_k", 1.5), ("time_stop", 10)),
    ),
    P1Candidate(
        "t6-bollinger20-25-v1",
        "T6",
        "1d",
        (("period", 20), ("band_width", 2.5), ("adx_max", 20), ("atr_k", 1.5), ("time_stop", 10)),
    ),
    P1Candidate(
        "t5-orb-m1-v1",
        "T5",
        "5m",
        (("opening_range_minutes", 15), ("buffer_bps", 5), ("target_multiple", 1.0)),
    ),
    P1Candidate(
        "t5-orb-m15-v1",
        "T5",
        "5m",
        (("opening_range_minutes", 15), ("buffer_bps", 5), ("target_multiple", 1.5)),
    ),
    P1Candidate(
        "t5-orb-m2-v1",
        "T5",
        "5m",
        (("opening_range_minutes", 15), ("buffer_bps", 5), ("target_multiple", 2.0)),
    ),
)

P1_CANDIDATES: Mapping[str, P1Candidate] = MappingProxyType(
    {candidate.candidate_id: candidate for candidate in _CANDIDATES}
)

if len(P1_CANDIDATES) != 15:
    raise RuntimeError("P1 candidate IDs must be unique and total exactly 15")


def get_p1_candidate(candidate_id: str) -> P1Candidate:
    """Look up one frozen P1 hypothesis; unknown IDs fail closed."""
    try:
        return P1_CANDIDATES[candidate_id]
    except KeyError as exc:
        raise ValueError(f"unknown P1 candidate: {candidate_id}") from exc
