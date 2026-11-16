"""Run a P1 candidate against whatever a real `MonthlyUniverseSnapshot`
selected, instead of the original fixed five-symbol pilot list.

The five-symbol pilot (`collect_pilot_daily.PILOT_INSTRUMENTS`) was always
an interim stand-in for this (`docs/BUILD_ORDER.md` P1a) -- this module is
the actual switch: it reads `selected_isins` from a real selector run
(`full_universe_loader.build_full_universe_snapshot`) and replays each one,
rather than iterating a hardcoded symbol list.

This does not change the P1d rejection rule (`backtest/promotion.py`) or
its locked "3 of 5" threshold -- that threshold is the pre-registered,
frozen-before-any-holdout-result P1d decision rule
(`docs/specs/P1_REJECTION_RULE.md`: "Do not change the candidate, costs,
universe, or boundaries after this result"). A broader-universe evaluation
needs its own, separately pre-registered rejection rule with an
owner-chosen majority threshold for the new instrument count -- that is an
explicit methodology decision for the owner, not inferred here by scaling
"3 of 5" arithmetically. This module only answers "which instruments does
this period's candidate replay cover", not "did it pass".
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from trading.backtest.action_preflight import ReviewedActionKey
from trading.backtest.daily_candidates import run_p1_daily_candidate
from trading.backtest.fills import BacktestProfile
from trading.backtest.runner import BacktestResult
from trading.core.models import Candle
from trading.storage.action_register import ActionRegister
from trading.storage.research_universe import MonthlyUniverseSnapshot


@dataclass(frozen=True)
class UniverseReplayResult:
    universe_version: str
    effective_date: date
    results_by_isin: dict[str, BacktestResult]
    missing_isins: tuple[str, ...]


def run_p1_daily_candidate_across_universe(
    candidate_id: str,
    universe_snapshot: MonthlyUniverseSnapshot,
    candles_by_isin: Mapping[str, list[Candle]],
    *,
    created_ts: datetime,
    quantity: Decimal,
    profile: BacktestProfile,
    action_register: ActionRegister | None = None,
    candle_snapshot_sha256_by_isin: Mapping[str, str] | None = None,
    reviewed_action_keys: set[ReviewedActionKey] | frozenset[ReviewedActionKey] = frozenset(),
) -> UniverseReplayResult:
    """Replay one candidate against every ISIN `universe_snapshot` actually
    selected for its `effective_date` -- the real, period-specific universe,
    not a fixed symbol list.

    An ISIN the snapshot selected but for which `candles_by_isin` has no
    entry is reported in `missing_isins`, never silently skipped from the
    result or treated as a zero -- same fail-closed discipline as the
    selector itself (`research_universe.build_snapshot`) and the
    corporate-action preflight it already runs through per instrument.
    """
    if not universe_snapshot.selected_isins:
        raise ValueError("universe snapshot selected no instruments")
    candle_snapshot_sha256_by_isin = candle_snapshot_sha256_by_isin or {}

    results_by_isin: dict[str, BacktestResult] = {}
    missing_isins: list[str] = []
    for isin in universe_snapshot.selected_isins:
        candles = candles_by_isin.get(isin)
        if not candles:
            missing_isins.append(isin)
            continue
        results_by_isin[isin] = run_p1_daily_candidate(
            candidate_id,
            candles,
            created_ts=created_ts,
            quantity=quantity,
            profile=profile,
            action_register=action_register,
            candle_snapshot_sha256=candle_snapshot_sha256_by_isin.get(isin),
            reviewed_action_keys=reviewed_action_keys,
        )

    return UniverseReplayResult(
        universe_version=universe_snapshot.universe_version,
        effective_date=universe_snapshot.effective_date,
        results_by_isin=results_by_isin,
        missing_isins=tuple(missing_isins),
    )
