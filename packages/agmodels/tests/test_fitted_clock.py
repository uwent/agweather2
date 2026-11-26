"""Fitted stages read by degree days or by the calendar (D101), and a model's training area."""

import numpy as np
import pytest

from agmodels.phenology import FittedStage, Insect, PhenologyModel, calendar_curves
from agmodels.spec import TrainingArea

AREA = TrainingArea(description="trap counts in Wisconsin", years=(2016, 2023), states=("WI",), counties=("27053",))


def _insect(*, clock: str = "degree_days", days: tuple[float, ...] = (150.0, 200.0, 250.0)) -> Insect:
    return Insect(
        opens="calendar",
        id="test-fitted",
        name="Test insect",
        crops=("potato",),
        base_f=50,
        upper_f=86,
        biofix="01-01",
        life_stages=(
            FittedStage(
                label="Adults",
                count_label="Adults per trap (typical count)",
                dd=(100.0, 500.0, 900.0),
                log_count=(0.0, np.log1p(4.0), 0.0),
                days=days,
                log_count_by_day=(0.0, np.log1p(9.0), np.log1p(1.0)) if days else (),
            ),
        ),
        clock=clock,  # type: ignore[arg-type]
        trained=AREA,
    )


def _inputs(n: int = 366) -> dict[str, np.ndarray]:
    doy = np.arange(1.0, n + 1)
    warm = 15 + 12 * np.sin((doy - 110) / 365 * 2 * np.pi)  # °C, a midwestern year's shape
    return {"air_temperature_min": warm - 6, "air_temperature_max": warm + 6, "day_of_year": doy}


def test_the_calendar_curve_peaks_on_its_own_day_and_holds_after_the_data():
    table = calendar_curves(_insect())
    assert table["count_adults"][199] == pytest.approx(9.0)  # day 200 is index 199
    assert table["activity_adults"][199] == 1
    assert table["count_adults"][148] == 0  # before the data's first day
    assert table["count_adults"][300] == pytest.approx(1.0)  # held past the last


def test_the_clock_option_reads_the_chosen_curve():
    m = PhenologyModel(_insect(), summary="Test.")
    assert [o.name for o in m.SPEC.options] == ["clock"] and m.SPEC.options[0].default == "degree_days"
    inputs = _inputs()
    by_day = m.outputs(inputs, clock="calendar")["count_adults"]
    by_dd = m.outputs(inputs, clock="degree_days")["count_adults"]
    assert np.nanargmax(by_day) == 199 and by_day[199] == pytest.approx(9.0)
    assert np.nanmax(by_dd) == pytest.approx(4.0, abs=0.15)  # the peak total falls between two days
    assert m.outputs(inputs)["count_adults"] == pytest.approx(by_dd, nan_ok=True)  # the default


def test_the_calendar_is_blank_where_the_degree_days_are():
    """Before the biofix both clocks are blank (a missing day adds nothing to the running total, so it isn't)."""
    m = PhenologyModel(_insect(clock="calendar"), summary="Test.")
    got = m.outputs(_inputs(), biofix_index=10)["count_adults"]
    assert np.isnan(got[:10]).all() and not np.isnan(got[10:]).any()


def test_the_calendar_reads_a_grid_s_days_by_cells():
    m = PhenologyModel(_insect(clock="calendar"), summary="Test.")
    inputs = _inputs()
    values = {
        "dd_total": np.ones((366, 2, 3)),
        "dd": np.ones((366, 2, 3)),
        m.FREEZE: np.ones((366, 2, 3)),
        "day_of_year": inputs["day_of_year"].reshape(366, 1, 1),
    }
    got = m.finish(values)["count_adults"]
    assert got.shape == (366, 2, 3) and (got[199] == pytest.approx(9.0))


def test_curves_on_both_clocks_or_neither():
    with pytest.raises(ValueError, match="calendar clock needs calendar curves"):
        _insect(clock="calendar", days=())
    assert PhenologyModel(_insect(days=()), summary="Test.").SPEC.options == ()
    with pytest.raises(ValueError, match="days must increase"):
        FittedStage(
            label="A",
            count_label="A",
            dd=(1.0, 2.0),
            log_count=(0.0, 1.0),
            days=(5.0, 4.0),
            log_count_by_day=(0.0, 1.0),
        )


def test_a_training_area_is_its_states_and_counties():
    assert AREA.contains(state="WI", fips="55001")
    assert AREA.contains(state="MN", fips="27053")  # Hennepin County, listed on its own
    assert not AREA.contains(state="MN", fips="27001")
    assert not AREA.contains(state=None, fips=None)
    with pytest.raises(ValueError, match="five-digit"):
        TrainingArea(description="x", years=(2020, 2021), counties=("5500",))
    with pytest.raises(ValueError, match="states or counties"):
        TrainingArea(description="x", years=(2020, 2021))
    assert PhenologyModel(_insect(), summary="Test.").SPEC.trained == AREA
