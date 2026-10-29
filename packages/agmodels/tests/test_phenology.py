"""Insect phenology as curves (D36): PERT life stages, generations spreading as a distributed delay, summed risk,
action windows and the freeze factor that ends the season."""

from dataclasses import replace

import numpy as np
import pytest

from agmodels.degree_days import degree_days_average
from agmodels.phenology import (
    ActionWindow,
    DerivedStage,
    Insect,
    LifeStage,
    PhenologyModel,
    curves,
    dd_grid,
    evaluate,
    freeze_factor,
    generation_densities,
    pert_pdf,
    pert_sd,
    window_periods,
)

FLIGHT = LifeStage(label="Adult flight", start=250, peak=360, end=540)
FEEDING = LifeStage(label="Larval feeding", start=400, peak=600, end=810, weight=0.5)
AVOID = ActionWindow(label="Avoid planting during adult flight", stage="Adult flight")
INSECT = Insect(
    id="test-maggot",
    name="Test maggot",
    crops=("Corn",),
    base_f=39.2,
    upper_f=86,
    biofix="01-01",
    life_stages=(FLIGHT, FEEDING),
    generation_dd=720,
    action_windows=(AVOID,),
)
X = dd_grid()


def moments(density):
    mass = np.sum(density)
    mean = np.sum(X * density) / mass
    return mass, mean, np.sum((X - mean) ** 2 * density) / mass


def test_pert_is_a_density_peaking_at_its_peak():
    pdf = pert_pdf(X, start=250, peak=360, end=540)
    mass, mean, var = moments(pdf)
    assert mass == pytest.approx(1, abs=1e-6)
    assert X[np.argmax(pdf)] == 360
    assert mean == pytest.approx((250 + 4 * 360 + 540) / 6, abs=1e-3)
    assert np.sqrt(var) == pytest.approx(pert_sd(start=250, peak=360, end=540), rel=1e-3)
    assert pdf[X <= 250].max() == 0 and pdf[X >= 540].max() == 0


def test_generations_add_the_generation_time_and_its_variance():
    """Generation n's mean is the first's plus n − 1 intervals, its variance the first's plus n − 1 generation-time
    variances (the first stage's first-generation SD by default)."""
    densities = generation_densities(insect=INSECT, stage=FLIGHT)
    _, mean_1, var_1 = moments(densities[0])
    sd = pert_sd(start=250, peak=360, end=540)
    for n, density in enumerate(densities[:8], start=1):
        mass, mean, var = moments(density)
        assert mass == pytest.approx(1, abs=1e-6), n
        assert mean == pytest.approx(mean_1 + (n - 1) * 720, abs=0.01), n
        assert var == pytest.approx(var_1 + (n - 1) * sd**2, rel=1e-3), n
    peaks = [d.max() for d in densities[:8]]
    assert peaks == sorted(peaks, reverse=True), "equal area: wider generations have lower peaks"


def test_overlapping_generations_level_off_at_one_per_interval():
    """Once generations overlap fully, their sum tends to 1 / the interval (the renewal theorem)."""
    insect = Insect(
        id="x",
        name="x",
        crops=(),
        base_f=50,
        upper_f=None,
        biofix="01-01",
        life_stages=(FLIGHT,),
        generation_dd=720,
        generation_sd=400,
    )
    total = np.sum(generation_densities(insect=insect, stage=FLIGHT), axis=0)
    late = total[(X >= 7000) & (X <= 8000)]
    assert late.min() == pytest.approx(1 / 720, rel=0.02) and late.max() == pytest.approx(1 / 720, rel=0.02)


def test_activity_risk_and_generations_complete():
    out = PhenologyModel(insect=INSECT, summary="").explore(dd_total=360)
    assert out["activity_adult_flight"] == pytest.approx(1)
    assert out["activity_larval_feeding"] == 0 and out["risk"] == pytest.approx(1)
    at_feeding_peak = PhenologyModel(insect=INSECT, summary="").explore(dd_total=600)
    assert at_feeding_peak["risk"] == pytest.approx(
        at_feeding_peak["activity_adult_flight"] + 0.5 * at_feeding_peak["activity_larval_feeding"]
    )
    complete = evaluate(insect=INSECT, dd_total=np.array([0.0, 900, 1475]))["generations_adult_flight"]
    np.testing.assert_allclose(complete, [0, 1, 2], atol=0.01)


def test_the_action_window_is_open_from_10_to_90_percent_of_each_generation():
    fraction = np.cumsum(generation_densities(insect=INSECT, stage=FLIGHT)[1])  # the second generation
    first_open, last_open = X[np.argmax(fraction >= 0.1)], X[np.flatnonzero(fraction <= 0.9)[-1]]
    window = evaluate(insect=INSECT, dd_total=np.array([first_open - 1, first_open, last_open, last_open + 1]))
    np.testing.assert_array_equal(window["window_avoid_planting_during_adult_flight"], [0, 1, 1, 0])
    opened = window_periods(curves(INSECT)["window_avoid_planting_during_adult_flight"])
    assert len(opened) >= 10 and X[opened[0][0]] > 250 and X[opened[0][1]] < 540


def test_window_periods():
    assert window_periods(np.array([0, 1, 1, 0, np.nan, 1, 0, 1])) == [(1, 2), (5, 5), (7, 7)]
    assert window_periods(np.zeros(3)) == []


def test_freezes_end_the_season_and_a_warm_spell_cant_undo_it():
    doy = np.r_[np.arange(240, 366), np.arange(1, 11)]
    tmin = np.full(doy.shape, 5.0)
    tmin[(doy >= 280) & (doy < 282)] = -3  # two freezes: half left
    tmin[(doy >= 300) & (doy < 304)] = -3  # four more within 14 days: the season ends
    factor = freeze_factor(tmin_c=tmin, day_of_year=doy)
    assert factor[doy == 250].item() == 1 and factor[doy == 285].item() == 0.5
    assert factor[doy == 296].item() == 0.5, "a warm spell after two freezes doesn't lift the factor"
    assert (factor[(doy >= 303) & (doy > 250)] == 0).all(), "after the season ends it stays ended"
    assert (factor[doy <= 10] == 1).all(), "a new year starts afresh"
    assert (np.diff(factor[doy > 250]) <= 0).all()


def test_outputs_stop_after_the_season_ends():
    m = PhenologyModel(insect=INSECT, summary="")
    days = 365
    doy = np.arange(1, days + 1)
    tmin = np.where(doy > 300, -5.0, 10.0)
    out = m.outputs({"air_temperature_min": tmin, "air_temperature_max": tmin + 15, "day_of_year": doy})
    done = out["season_complete"] == 1
    assert done.any() and not done[:300].any()
    assert (out["activity_adult_flight"][done] == 0).all() and (m.risk(out)[done] == 0).all()
    assert (out["window_avoid_planting_during_adult_flight"][done] == 0).all()


def test_missing_stays_missing_and_a_grid_runs():
    m = PhenologyModel(insect=INSECT, summary="")
    shape = (200, 2, 3)
    out = m.outputs({"air_temperature_min": np.full(shape, 10.0), "air_temperature_max": np.full(shape, 25.0)})
    assert out["activity_adult_flight"].shape == shape and m.risk(out).shape == shape
    out = m.outputs({"air_temperature_min": np.full(5, 10.0), "air_temperature_max": np.full(5, 25.0)}, biofix_index=2)
    assert np.isnan(out["activity_adult_flight"][:2]).all() and np.isnan(m.risk(out)[:2]).all()
    assert not np.isnan(m.risk(out)[2:]).any()


def test_definitions_are_checked():
    with pytest.raises(ValueError, match="increase"):
        LifeStage(label="x", start=300, peak=200, end=400)
    with pytest.raises(ValueError, match="unknown stage"):
        Insect(
            id="x",
            name="x",
            crops=(),
            base_f=50,
            upper_f=None,
            biofix="01-01",
            life_stages=(FLIGHT,),
            action_windows=(ActionWindow(label="Spray", stage="Larvae"),),
        )


def test_spec_declares_every_output():
    m = PhenologyModel(insect=INSECT, summary="")
    out = m.outputs({"air_temperature_min": np.full(5, 10.0), "air_temperature_max": np.full(5, 25.0)})
    assert [q.name for q in m.SPEC.outputs] == list(out)
    assert m.SPEC.risk is not None and len(m.SPEC.risk.thresholds) == len(m.SPEC.risk.levels) - 1


LARVAE = DerivedStage(label="Larvae", follows="Adult flight", lag=80, duration=370)
DERIVED = Insect(
    id="derived", name="x", crops=(), base_f=39, upper_f=84.2, biofix="01-01", dd_method="average",
    life_stages=(FLIGHT, LARVAE), generation_dd=720,
)  # fmt: skip


def test_a_derived_stage_is_present_from_its_lag_for_its_duration():
    """Larvae enter `lag` after each fly's flight and leave `duration` later, so the share present is the flight's
    fraction complete shifted by the lag, less the same shifted by lag + duration."""
    single = replace(DERIVED, generation_dd=None)
    flight = np.cumsum(generation_densities(insect=single, stage=FLIGHT)[0])
    tables = curves(single)
    peak_present = (np.interp(X - 80, X, flight) - np.interp(X - 450, X, flight)).max()
    at = np.array([250 + 80, 540 + 80, 250 + 450, 540 + 450, 2000.0])
    activity = np.interp(at, X, tables["activity_larvae"]) * peak_present
    np.testing.assert_allclose(activity[:4], [0, 1, 1, 0], atol=1e-3)  # none, all, all (370 > flight's width), none
    assert np.interp(700, X, tables["generations_larvae"]) == pytest.approx(0)
    assert np.interp(990, X, tables["generations_larvae"]) == pytest.approx(1, abs=1e-3)


def test_derived_stages_are_checked():
    with pytest.raises(ValueError, match="isn't a timed life stage"):
        Insect(
            id="x", name="x", crops=(), base_f=50, upper_f=None, biofix="01-01",
            life_stages=(FLIGHT, DerivedStage(label="Larvae", follows="Eggs", lag=10, duration=100)),
        )  # fmt: skip
    with pytest.raises(ValueError, match="first life stage"):
        Insect(id="x", name="x", crops=(), base_f=50, upper_f=None, biofix="01-01", life_stages=(LARVAE, FLIGHT))


def test_the_average_method_caps_both_temperatures():
    assert degree_days_average(60, 100, base=39, upper=84.2) == pytest.approx((60 + 84.2) / 2 - 39)
    assert degree_days_average(60, 100, base=39) == pytest.approx(41)
    m = PhenologyModel(insect=DERIVED, summary="")
    out = m.outputs({"air_temperature_min": np.array([0.0, 20]), "air_temperature_max": np.array([10.0, 40])})
    np.testing.assert_allclose(out["dd"], [max((32 + 50) / 2 - 39, 0), (68 + 84.2) / 2 - 39])
