from decimal import Decimal

import pytest

from trading.backtest.scorecard import Scorecard
from trading.research.ml_ranker import CandidateFoldHistory, rank

ZERO = Decimal("0")


def _sc(expectancy: str) -> Scorecard:
    return Scorecard(0, 0, 0, ZERO, ZERO, ZERO, ZERO, ZERO, ZERO, Decimal(expectancy))


def test_champion_keeps_title_if_no_challenger_wins_every_recent_fold() -> None:
    champ = CandidateFoldHistory("A", (_sc("1.0"), _sc("1.0"), _sc("1.0")))
    one_good_fold = CandidateFoldHistory("B", (_sc("0.1"), _sc("0.1"), _sc("5.0")))
    verdict = rank("A", (champ, one_good_fold))
    assert verdict.champion_id == "A"


def test_challenger_takes_over_only_after_beating_every_recent_fold() -> None:
    champ = CandidateFoldHistory("A", (_sc("1.0"), _sc("1.0"), _sc("1.0")))
    consistent_winner = CandidateFoldHistory("B", (_sc("1.1"), _sc("1.2"), _sc("1.3")))
    verdict = rank("A", (champ, consistent_winner))
    assert verdict.champion_id == "B"
    assert verdict.challenger_ids == ("A",)


def test_too_few_folds_cannot_dethrone_champion() -> None:
    champ = CandidateFoldHistory("A", (_sc("1.0"), _sc("1.0"), _sc("1.0")))
    short_history = CandidateFoldHistory("B", (_sc("9.0"), _sc("9.0")))  # only 2 folds
    verdict = rank("A", (champ, short_history), min_consecutive_folds=3)
    assert verdict.champion_id == "A"


def test_unknown_champion_id_fails_closed() -> None:
    champ = CandidateFoldHistory("A", (_sc("1.0"),))
    with pytest.raises(ValueError, match="not among pre-registered"):
        rank("ghost", (champ,))
