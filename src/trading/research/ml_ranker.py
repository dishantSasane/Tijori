"""EXPERIMENTAL -- walk-forward champion/challenger ranker (P8).

What this is NOT: a new way to search for strategies. P1 exists specifically
because "pick whichever backtest has the best number" is the overfitting
failure mode (docs/BUILD_ORDER.md's P1 intro paragraph) -- P1b pre-registers
a fixed candidate library *before* any evaluation, and P1c/P1d run a one-shot
holdout so a candidate cannot be re-tested until it looks good. This module
must not reopen that door. It never touches raw price data, never invents a
new signal, and never gets to evaluate a candidate that P1 hasn't already
pre-registered and scored.

What this IS: given scorecards that *already exist* for a fixed, pre-
registered set of candidate strategy instances (``trading.backtest.scorecard
.Scorecard``, one per walk-forward fold), rank which already-approved
candidate should be the *active* ("champion") instance for a sleeve, versus
sitting as a "challenger" on the bench. The only decision this module makes
is activation ordering among candidates that already cleared P1's gates --
never which candidates exist, never their parameters.

Champion/challenger rule (deliberately simple, no tuning knobs):
a challenger only replaces the champion if it beats it on ``expectancy`` in
every one of the last ``min_consecutive_folds`` walk-forward folds. One good
fold is not enough -- that is exactly the single-lucky-window overfit this
whole structure exists to avoid.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from trading.backtest.scorecard import Scorecard

#: Folds a challenger must win consecutively before it can dethrone the
#: champion. 3 is a judgment call, not derived -- ponytail: raise this if the
#: owner sees champion thrashing on noise; no evidence yet either way.
DEFAULT_MIN_CONSECUTIVE_FOLDS = 3


@dataclass(frozen=True)
class CandidateFoldHistory:
    """Pre-registered candidate id + its walk-forward scorecards, oldest
    fold first. The caller (not this module) is responsible for ensuring
    these scorecards came from P1's pre-registered library and one-shot
    holdout discipline -- this module trusts its input and only ranks it.
    """

    candidate_id: str
    folds: tuple[Scorecard, ...]


@dataclass(frozen=True)
class RankerVerdict:
    champion_id: str
    challenger_ids: tuple[str, ...]
    reason: str


def rank(
    champion_id: str,
    candidates: tuple[CandidateFoldHistory, ...],
    *,
    min_consecutive_folds: int = DEFAULT_MIN_CONSECUTIVE_FOLDS,
) -> RankerVerdict:
    """Decide whether any challenger should replace ``champion_id``.

    This is advisory output for a human/ops process to act on -- same as the
    Brain's advisory role (AGENTS.md §4.6), this ranker does not place
    orders, change strategy versions, or write to the live activation table
    itself. It only answers "who should be champion."
    """
    by_id = {c.candidate_id: c for c in candidates}
    if champion_id not in by_id:
        raise ValueError(f"champion_id {champion_id!r} not among pre-registered candidates")
    champion = by_id[champion_id]

    winners: list[str] = []
    for candidate in candidates:
        if candidate.candidate_id == champion_id:
            continue
        if _beats_every_fold(candidate, champion, min_consecutive_folds):
            winners.append(candidate.candidate_id)

    if not winners:
        return RankerVerdict(
            champion_id=champion_id,
            challenger_ids=tuple(
                c.candidate_id for c in candidates if c.candidate_id != champion_id
            ),
            reason=f"no challenger beat expectancy in all last {min_consecutive_folds} folds",
        )

    # Deterministic tie-break: among winners, the one with the higher
    # expectancy in the most recent fold. Still never "best historical P&L
    # overall" -- only the already-pre-registered, already-walk-forward-
    # validated winners reach this line.
    new_champion = max(winners, key=lambda cid: by_id[cid].folds[-1].expectancy)
    return RankerVerdict(
        champion_id=new_champion,
        challenger_ids=tuple(c.candidate_id for c in candidates if c.candidate_id != new_champion),
        reason=f"beat champion {champion_id!r} on expectancy in last {min_consecutive_folds} folds",
    )


def _beats_every_fold(
    candidate: CandidateFoldHistory, champion: CandidateFoldHistory, n: int
) -> bool:
    if len(candidate.folds) < n or len(champion.folds) < n:
        return False
    for c_fold, champ_fold in zip(candidate.folds[-n:], champion.folds[-n:], strict=True):
        if not c_fold.expectancy > champ_fold.expectancy:
            return False
    return True


def _demo() -> None:
    """Self-check (ponytail: smallest thing that fails if the logic breaks)."""
    zero = Decimal("0")

    def sc(expectancy: str) -> Scorecard:
        return Scorecard(0, 0, 0, zero, zero, zero, zero, zero, zero, Decimal(expectancy))

    champ = CandidateFoldHistory("t1_donchian", (sc("1.0"), sc("1.0"), sc("1.0")))
    weak_challenger = CandidateFoldHistory("t4_rsi_pullback", (sc("0.5"), sc("1.5"), sc("0.9")))
    strong_challenger = CandidateFoldHistory("t2_momentum", (sc("1.2"), sc("1.3"), sc("1.4")))

    verdict = rank("t1_donchian", (champ, weak_challenger, strong_challenger))
    assert verdict.champion_id == "t2_momentum", verdict
    assert "t1_donchian" in verdict.challenger_ids

    # Missing champion id must fail closed, not silently pick something.
    try:
        rank("does_not_exist", (champ,))
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for unknown champion_id")

    print("ml_ranker self-check OK")


if __name__ == "__main__":
    _demo()
