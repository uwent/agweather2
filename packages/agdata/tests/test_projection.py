"""Scenarios for the projection past the forecast (D63, PLAN.md Phase 5 D P1)."""

from datetime import date, timedelta

import numpy as np
import pytest

from agdata import projection


def reader(have: dict[int, tuple[date, date]] | None = None, holes: set[date] | None = None):
    """Days whose value is the date as YYYYMMDD (so a test sees which source day landed where), NaN outside the
    years' covered spans and on `holes`."""
    calls = []

    def read(first: date, last: date, names: list[str]) -> dict[str, np.ndarray]:
        calls.append((first, last))
        n = (last - first).days + 1
        days = [first + timedelta(days=k) for k in range(n)]
        out = np.array([float(d.strftime("%Y%m%d")) for d in days])
        for k, d in enumerate(days):
            span = (have or {}).get(d.year)
            if (have is not None and (span is None or not span[0] <= d <= span[1])) or d in (holes or set()):
                out[k] = np.nan
        return {name: out.copy() for name in names}

    read.calls = calls  # type: ignore[attr-defined]
    return read


def test_each_year_by_calendar_date():
    s = projection.build(date(2026, 8, 1), date(2026, 8, 3), [2024, 2025], ["t"], reader())
    assert s.years == [2024, 2025] and s.dates[0] == date(2026, 8, 1)
    assert s.values["t"][:, 0].tolist() == [20240801, 20240802, 20240803]
    assert s.values["t"][:, 1].tolist() == [20250801, 20250802, 20250803]
    assert s.coverage.tolist() == [2, 2, 2]


def test_leap_days():
    # Into a leap year: its Feb 29 takes a common year's Feb 28
    s = projection.build(date(2028, 2, 27), date(2028, 3, 1), [2027], ["t"], reader())
    assert s.values["t"][:, 0].tolist() == [20270227, 20270228, 20270228, 20270301]
    # From a leap year into a common one: the source's Feb 29 is skipped
    s = projection.build(date(2029, 2, 27), date(2029, 3, 1), [2028], ["t"], reader())
    assert s.values["t"][:, 0].tolist() == [20280227, 20280228, 20280301]


def test_a_season_crossing_new_year_keeps_its_shift():
    s = projection.build(date(2026, 12, 30), date(2027, 1, 2), [2025], ["t"], reader())
    assert s.values["t"][:, 0].tolist() == [20251230, 20251231, 20260101, 20260102]


def test_a_year_counts_only_on_its_days_and_an_empty_one_drops():
    have = {2024: (date(2024, 8, 1), date(2024, 8, 2)), 2025: (date(2025, 8, 1), date(2025, 8, 3))}
    s = projection.build(
        date(2026, 8, 1), date(2026, 8, 3), [2023, 2024, 2025], ["t", "rain"], reader(have, holes={date(2025, 8, 2)})
    )
    assert s.years == [2024, 2025]  # 2023 has nothing over the span
    assert np.isnan(s.values["t"][2, 0]) and np.isnan(s.values["t"][1, 1])
    assert s.coverage.tolist() == [2, 1, 1]  # Aug 2: 2025 has its hole; Aug 3: 2024 has ended


def test_years_that_would_overlap_the_season_are_skipped():
    s = projection.build(date(2026, 8, 1), date(2026, 8, 3), [2026, 2027], ["t"], reader())
    assert s.years == []
    with pytest.raises(ValueError, match="up to 366"):
        projection.build(date(2026, 1, 1), date(2027, 6, 1), [2024], ["t"], reader())


def test_the_projection_starts_after_the_last_day_with_data_and_stacks_on_the_season():
    dates = [date(2026, 7, 30), date(2026, 7, 31), date(2026, 8, 1)]
    assert projection.projection_start(dates, ["observed", "forecast", None]) == date(2026, 8, 1)
    assert projection.projection_start(dates, [None, None, None]) is None
    s = projection.build(date(2026, 8, 1), date(2026, 8, 2), [2024, 2025], ["t"], reader())
    values, kinds = projection.stacked({"t": np.array([1.0, 2.0])}, ["observed", "forecast"], s)
    assert values["t"].shape == (4, 2) and values["t"][:2].tolist() == [[1.0, 1.0], [2.0, 2.0]]
    assert values["t"][2].tolist() == [20240801, 20250801]
    assert kinds == ["observed", "forecast", "projection", "projection"]
