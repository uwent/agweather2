"""Codling moth (`docs/plans/models.md` B4): WSU's curves, first catch by latitude (Jones et al. 2013), a grower's
trap date, two generations, and the second generation's size (Riedl and Croft 1978)."""

import csv
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pytest

from agmodels import runner
from agmodels.insects.codling_moth import INSECT, WISCONSIN_SHIFT_F, first_catch_dd_f, jones_first_catch_dd_f
from agmodels.phenology import DD_STEP, PhenologyModel, dd_grid, generation_densities

TABLE = Path(__file__).parent / "fixtures" / "codling_moth_wsu_table.tsv"
MODEL = PhenologyModel(insect=INSECT, summary="")
HATCH = "window_protect_fruit_during_egg_hatch"


def _wsu_table() -> dict[str, list[tuple[np.ndarray, np.ndarray]]]:
    """WSU's cumulative % flight and hatch by DD°F after first catch, split into generations where it restarts."""
    rows = list(csv.DictReader(TABLE.open(), delimiter="\t"))
    dd = np.array([float(r["dd_biofix"]) for r in rows])
    out = {}
    for column, stage in (("pct_flight", 0), ("pct_hatch", 1)):
        pct = np.array([float(r[column]) for r in rows])
        generation = np.cumsum(np.r_[0, np.diff(pct) < -50])
        out[INSECT.life_stages[stage].label] = [(dd[generation == g], pct[generation == g]) for g in (0, 1)]
    return out


@pytest.mark.parametrize("stage", [0, 1])
def test_flight_and_hatch_follow_wsus_table_in_both_generations(stage):
    life_stage = INSECT.life_stages[stage]
    cumulative = [np.cumsum(d) * DD_STEP * 100 for d in generation_densities(insect=INSECT, stage=life_stage)]  # type: ignore[arg-type]
    for g, (dd, pct) in enumerate(_wsu_table()[life_stage.label]):
        ours = np.interp(dd, dd_grid(), cumulative[g])
        assert np.abs(ours - pct).max() <= 3.5, (life_stage.label, g)
        assert np.sqrt(np.mean((ours - pct) ** 2)) <= 1.2, (life_stage.label, g)


def test_two_generations_and_no_third():
    for stage in INSECT.life_stages:
        assert len(generation_densities(insect=INSECT, stage=stage)) == 2  # type: ignore[arg-type]
    out = MODEL.explore(dd_total=3000)
    assert out["generations_egg_hatch"] == pytest.approx(2, abs=1e-3)
    assert out["risk"] < 1e-3 and out[HATCH] == 0


# Jones et al. 2013, Table 1: mean first catch (DD°C from January 1) at the sites nearest Wisconsin
SITES = {"Allegan MI": (42.59, 129), "Geneva NY": (42.86, 139), "Highland NY": (41.69, 139), "Burlington VT": (44.43, 121), "Hood River OR": (45.69, 111), "Biglerville PA": (39.93, 151)}  # fmt: skip


def test_first_catch_by_latitude_is_jones_2013s_quadratic_shifted_for_wisconsin():
    np.testing.assert_allclose(
        first_catch_dd_f(np.array([43.0, 46.0])), jones_first_catch_dd_f(np.array([43.0, 46.0])) + WISCONSIN_SHIFT_F
    )
    assert jones_first_catch_dd_f(np.array(43.0)) / 1.8 == pytest.approx(127.2, abs=0.1)
    assert jones_first_catch_dd_f(np.array(46.0)) / 1.8 == pytest.approx(104.7, abs=0.1)
    for site, (lat, observed) in SITES.items():
        assert abs(jones_first_catch_dd_f(np.array(lat)) / 1.8 - observed) < 15, site
    # held at the curve's minimum, about Washington's 96, north of 49.5 °N
    assert jones_first_catch_dd_f(np.array(55.0)) == pytest.approx(jones_first_catch_dd_f(np.array(49.6)), abs=0.1)
    assert jones_first_catch_dd_f(np.array(49.6)) / 1.8 == pytest.approx(95.5, abs=0.5)


def test_the_hatch_window_opens_at_riedls_first_hatch():
    """Riedl et al. 1976, Table II: first egg hatch 253 ± 5 DD°F after first catch (8 orchard-years); WSU's first
    cover spray at 250 (3 % hatch). The window opens at 1 % of the curve and closes at 95 % (WSU's table: 800)."""
    totals = np.arange(0, 1100, 1.0)  # the first generation's (the second's opens about 1,200)
    open_ = np.array([MODEL.explore(dd_total=float(t))[HATCH] for t in totals])
    first, last = totals[open_ > 0][[0, -1]]
    assert abs(first - 253) <= 15
    assert abs(last - 800) <= 20


def _season(year: int, mean_c: float = 18.0, swing_c: float = 12.0):
    """A year of daily min and max (°C): a seasonal cycle peaking in mid-July."""
    days = [date(year, 1, 1) + timedelta(days=k) for k in range((date(year + 1, 1, 1) - date(year, 1, 1)).days)]
    doy = np.array([d.timetuple().tm_yday for d in days], dtype=float)
    mean = mean_c * np.cos(2 * np.pi * (doy - 196) / 365) + 2
    return days, {"air_temperature_min": mean - swing_c / 2, "air_temperature_max": mean + swing_c / 2}


def _run(days, weather, latitude: float, biofix_index: int = 0):
    context = runner._context(days, latitude)
    inputs = {k: np.asarray(v, dtype=float) for k, v in weather.items()} | {k: context[k] for k in MODEL.SPEC.context}
    return MODEL.outputs(inputs, biofix_index=biofix_index)


def test_without_a_date_the_curves_start_at_the_latitudes_first_catch():
    days, weather = _season(2025)
    south, north = _run(days, weather, latitude=43.0), _run(days, weather, latitude=46.0)
    for out, lat in ((south, 43.0), (north, 46.0)):
        expected = float(first_catch_dd_f(np.array(lat)))
        assert np.nanmax(out["first_catch_dd_estimate"]) == pytest.approx(expected)
        assert (out["first_catch_estimated"] == 1).all()
        np.testing.assert_allclose(out["dd_after_first_catch"], np.maximum(out["dd_total"] - expected, 0))
    # the same weather: the north (an earlier first catch on the degree-day scale) hatches first
    first_hatch = [int(np.argmax(o[HATCH] > 0)) for o in (south, north)]
    assert first_hatch[1] < first_hatch[0]


def test_a_trap_date_replaces_the_estimate():
    days, weather = _season(2025)
    estimated = _run(days, weather, latitude=43.0)
    catch = int(np.argmax(estimated["dd_after_first_catch"] > 0)) - 1  # the estimate's first-catch day
    trapped = _run(days, weather, latitude=43.0, biofix_index=catch)
    assert (trapped["first_catch_estimated"][catch:] == 0).all() and np.isnan(trapped["dd_total"][:catch]).all()
    # the same first-catch day gives the same hatch, within the part of a day's degree days the estimate falls in
    later = slice(catch + 1, None)
    day_dd = trapped["dd"][catch : catch + 2].sum()
    assert np.abs(trapped["dd_after_first_catch"][later] - estimated["dd_after_first_catch"][later]).max() <= day_dd
    assert abs(int(np.argmax(trapped[HATCH] > 0)) - int(np.argmax(estimated[HATCH] > 0))) <= 1
    # a trap date a week later moves every event later
    late = _run(days, weather, latitude=43.0, biofix_index=catch + 7)
    assert np.argmax(late[HATCH] > 0) > np.argmax(trapped[HATCH] > 0)


def test_second_generation_size_from_degree_days_on_august_4():
    for year in (2025, 2024):  # August 4 is day 216, or 217 in a leap year
        aug4 = date(year, 8, 4).timetuple().tm_yday - 1
        for mean_c, expected in ((12.0, 1.0), (18.0, 2.0), (21.0, 3.0), (22.0, 4.0), (24.0, 5.0)):
            days, weather = _season(year, mean_c=mean_c)
            out = _run(days, weather, latitude=44.0)
            size = out["second_generation_size"]
            assert np.isnan(size[:aug4]).all() and (size[aug4:] == size[aug4]).all()
            on_aug4 = out["dd_total"][aug4]
            bounds = INSECT.generation_size.bounds  # type: ignore[union-attr]
            assert size[aug4] == 1 + sum(on_aug4 >= b for b in bounds) == expected, (year, mean_c, on_aug4)


def test_second_generation_size_from_a_trap_date_counts_from_january():
    days, weather = _season(2025, mean_c=21.0)
    estimated = _run(days, weather, latitude=44.0)
    catch = int(np.argmax(estimated["dd_after_first_catch"] > 0)) - 1
    trapped = _run(days, weather, latitude=44.0, biofix_index=catch)
    aug4 = date(2025, 8, 4).timetuple().tm_yday - 1
    assert trapped["second_generation_size"][aug4] == estimated["second_generation_size"][aug4]


def test_latitude_is_required():
    days, weather = _season(2025)
    with pytest.raises(KeyError, match="latitude"):
        context = runner._context(days, 44.0)
        MODEL.outputs(weather | {"day_of_year": context["day_of_year"], "year": context["year"]})
