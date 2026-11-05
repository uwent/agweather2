"""Seasons of a once-a-season product (`agmodels.seasons`): potato volunteer's winters."""

from datetime import date

import pytest

from agmodels.registry import model
from agmodels.seasons import current_season, season_named, season_of, season_starting

POTATO = model("potato-volunteer").SPEC


def test_a_winter_is_named_by_both_years():
    winter = season_starting(POTATO, 2025)
    assert (winter.name, winter.label) == ("2025-26", "2025–26")
    assert (winter.first, winter.last, winter.appears) == (date(2025, 11, 1), date(2026, 3, 31), date(2026, 1, 1))
    assert season_named(POTATO, "2025-26") == winter
    for wrong in ("2025", "2025-27", "winter"):
        with pytest.raises(ValueError):
            season_named(POTATO, wrong)


def test_a_season_shows_from_when_it_appears_until_the_next_one_does():
    assert current_season(POTATO, date(2025, 12, 31)).name == "2024-25"  # 2025-26 is open but not shown yet
    assert current_season(POTATO, date(2026, 1, 1)).name == "2025-26"
    assert current_season(POTATO, date(2026, 7, 4)).name == "2025-26"  # settled, carried through the summer
    assert season_of(POTATO, date(2025, 12, 1)).name == "2025-26"  # type: ignore[union-attr]
    assert season_of(POTATO, date(2026, 7, 4)) is None


def test_only_seasonal_products_have_seasons():
    with pytest.raises(ValueError, match="seasonal"):
        season_starting(model("late-blight-dsv").SPEC, 2025)
