"""Model maps finished from the stored ingredients (`agdata.modelgrid`): the same as running each model at a cell."""

from datetime import date, timedelta

import numpy as np
import pytest

from agdata import croptiers, cumulative, modelgrid, modelmaps
from agdata.catalog import DAILY_VARIABLES, GAP_FILL
from agdata.grid import NDFD
from agdata.store import DAILY, INGREDIENTS, GridStore
from agdata.testing import WINDOW
from agmodels import runner
from agmodels.accumulate import rolling_mean, rolling_sum, running_total
from agmodels.testing import DATES, WEATHER

# Late April through July: every map's biofix but the fall ones (rye's New Year is checked on `_spans` below)
FIRST, LAST = date(2025, 4, 25), date(2025, 7, 31)
SPAN = [FIRST + timedelta(days=k) for k in range((LAST - FIRST).days + 1)]
HOLE = (date(2025, 6, 10), date(2025, 6, 12))  # a gap the runner's estimate bridges
DAYS = (date(2025, 5, 20), date(2025, 6, 18), date(2025, 7, 30))
# How far a map may be from the point, by unit: the stores' rounding (degree days to 0.5 °F·d a total, an
# accumulated index to its total's step, RH means to 0.01 %); counts and levels are compared separately
ATOL = {"degF_day": 1.0, "degC_day": 0.6, "index": 0.25, "percent": 0.5, "hour": 0.5, "mm": 0.1, "degC": 0.05}
DISCRETE = ("stage", "risk_level")


def _weather() -> dict[str, np.ndarray]:
    """`agmodels.testing`'s weather on each cell, warmer or cooler by cell and noisier (seeded), missing in HOLE."""
    rng = np.random.default_rng(5)
    k0 = DATES.index(FIRST)
    cells = np.linspace(-2, 2, WINDOW.size).reshape(WINDOW.shape)
    gone = [k for k, d in enumerate(SPAN) if HOLE[0] <= d <= HOLE[1]]
    out = {}
    for name, series in WEATHER.items():
        variable = DAILY_VARIABLES[name]
        v = np.broadcast_to(series[k0 : k0 + len(SPAN), None, None], (len(SPAN), *WINDOW.shape)).astype(float)
        if variable.unit == "degC":
            v = v + cells + rng.normal(0, 1.0, v.shape)
        v = np.clip(v, variable.valid_min, variable.valid_max)
        v[gone] = np.nan
        out[name] = variable.decode(variable.encode(v))
    return out


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    root = tmp_path_factory.mktemp("maps")
    weather = _weather()
    store = GridStore.create(root, DAILY, 2025, WINDOW, DAILY_VARIABLES.values())
    store.write(FIRST, weather, source="test")
    cumulative.rebuild_year(root, WINDOW, 2025)
    modelmaps.update(root, WINDOW, FIRST, LAST)
    with pytest.MonkeyPatch.context() as monkeypatch:
        _potato_place(monkeypatch)
        # soybean's, corn's and potato's tiers (spring wheat has no dates in Fayette County)
        croptiers.update(root, WINDOW, 2025, LAST)
    planting_tiers_cleared()
    return root, weather


def planting_tiers_cleared() -> None:
    from agdata import planting

    planting._tier_days.cache_clear()


def _potato_place(monkeypatch) -> None:
    """A Veg Path potato place at the test window (there's none in Fayette County, Iowa), planted Apr 28 / May 5 /
    May 12."""
    from agdata import planting

    lat, lng = NDFD.latlon(WINDOW.j0, WINDOW.i0)
    row = planting.PlantingDate(
        crop="potato", early="04-28", typical="05-05", late="05-12", level="location", area="Here"
    )
    planting._tier_days.cache_clear()
    monkeypatch.setattr(planting, "_potato_table", lambda: ((float(lat), float(lng), row),))


def _at_point(
    model_id: str,
    weather,
    y: int,
    x: int,
    day: date,
    in_region: bool = True,
    sown: date | None = None,
    own=False,
    start: date | None = None,
) -> runner.ModelRun:
    """The model at one cell through `day`, from January 1 (missing before the archive), as a point runs it;
    `sown` is the planting date (the crop model's own biofix with `own`)."""
    m = runner.find_model(model_id)
    begin = date(day.year, 1, 1)
    dates = [begin + timedelta(days=k) for k in range((day - begin).days + 1)]
    lead = (FIRST - begin).days
    names = runner.required_inputs(m)
    daily = {name: np.concatenate([np.full(lead, np.nan), weather[name][: len(dates) - lead, y, x]]) for name in names}
    lat, _ = NDFD.latlon(WINDOW.j0 + y, WINDOW.i0 + x)
    return runner.run(
        m,
        dates=dates,
        daily=daily,
        latitude=float(lat),
        start=start or day,
        biofix=sown if own else None,
        planting=None if own else sown,
        in_region=in_region,
        gap_fill=GAP_FILL,
    )


@pytest.mark.parametrize("model_id", sorted(set(modelgrid.mapped()) - set(modelmaps.TIER_MODELS)))
def test_a_maps_cell_is_the_model_run_at_that_cell(built, model_id):
    root, weather = built
    m = runner.find_model(model_id)
    units = {q.name: q.unit for q in m.SPEC.outputs}
    for day in DAYS:
        found = modelgrid.model_map(root, model_id, day, day, WINDOW, tier=None)
        assert found.reads > 0 and not found.stale
        for y in range(WINDOW.shape[0]):
            for x in range(WINDOW.shape[1]):
                inside = found.in_region is None or bool(found.in_region[y, x])
                point = _at_point(model_id, weather, y, x, day, in_region=inside)
                if point.reason is not None:  # out of its region, or not started: missing on the map too
                    assert all(np.isnan(v[0, y, x]) for v in found.outputs.values()), (model_id, day, point.reason)
                    continue
                pairs = {name: (found.outputs[name][0, y, x], point.outputs[name][-1]) for name in units}
                if found.level is not None and point.level is not None:
                    pairs["risk_level"] = (found.level[0, y, x], point.level[-1])
                for name, (a, b) in pairs.items():
                    where = f"{model_id} {name} {day} cell {y},{x}"
                    if name in DISCRETE or units.get(name) == "day":
                        assert a == b or (np.isnan(a) and np.isnan(b)) or abs(a - b) <= 1, where
                    else:
                        np.testing.assert_allclose(
                            a, b, rtol=0.01, atol=ATOL[units[name]], equal_nan=True, err_msg=where
                        )


def test_days_before_a_models_biofix_are_missing(built):
    root, _ = built
    found = modelgrid.model_days(root, "corn-earworm", date(2025, 7, 30), date(2025, 7, 31), WINDOW)  # biofix 08-01
    assert np.isnan(found.outputs["dd_total"]).all() and np.isnan(found.level).all()  # type: ignore[arg-type]
    assert found.biofix == [date(2025, 8, 1)] * 2


def test_a_range_is_each_day_finished(built):
    root, _ = built
    days = modelgrid.model_days(root, "late-blight-dsv", date(2025, 6, 1), date(2025, 6, 20), WINDOW)
    for k in (0, 9, 19):
        one = modelgrid.model_days(root, "late-blight-dsv", days.dates[k], days.dates[k], WINDOW)
        for name, v in one.outputs.items():
            np.testing.assert_array_equal(v[0], days.outputs[name][k], err_msg=f"{name} {days.dates[k]}")


def test_a_model_outside_its_states_is_missing(built):
    root, _ = built
    found = modelgrid.model_days(root, "pecan-scab", date(2025, 6, 1), date(2025, 6, 1), WINDOW)
    assert found.in_region is not None and not found.in_region.any()
    assert np.isnan(found.level).all()  # type: ignore[arg-type]


# `_spans` and the accumulations, on a running total that crosses New Year (rye, potato volunteer)


def _totals(days: list[date], daily: np.ndarray):
    """A reader of running totals from January 1 of `daily` (NaN adds nothing), as the stores keep them."""
    index = {d: k for k, d in enumerate(days)}
    totals = np.zeros_like(daily)
    for k, d in enumerate(days):
        before = totals[k - 1] if k and (d.month, d.day) != (1, 1) else 0.0
        totals[k] = before + np.nan_to_num(daily[k])

    def read(wanted):
        return {d: np.array([[totals[index[d]]]]) for d in wanted}

    return read


SEASON = [date(2025, 10, 1) + timedelta(days=k) for k in range(150)]  # Oct 1 2025 – Feb 27 2026
RAIN = np.where(np.arange(150) % 9 == 4, np.nan, np.sin(np.arange(150) / 5.0) + 1.5)


def test_a_total_from_the_biofix_crosses_new_year():
    read = _totals(SEASON, RAIN)
    biofix = date(2025, 10, 10)
    pairs = [(biofix if d >= biofix else None, d) for d in SEASON]
    got = modelgrid._spans(read, pairs, WINDOW.__class__(j0=0, j1=1, i0=0, i1=1))[:, 0, 0]
    np.testing.assert_allclose(got, running_total(RAIN, 9), equal_nan=True)


def test_a_sum_and_mean_over_days_start_at_the_biofix():
    window = WINDOW.__class__(j0=0, j1=1, i0=0, i1=1)
    biofix, n = date(2025, 12, 25), 7
    b = SEASON.index(biofix)
    starts = [(max(biofix, d - timedelta(days=n - 1)) if d >= biofix else None, d) for d in SEASON]
    sums = modelgrid._spans(_totals(SEASON, RAIN), starts, window)[:, 0, 0]
    np.testing.assert_allclose(sums, rolling_sum(RAIN, n, b), equal_nan=True)
    known = modelgrid._spans(_totals(SEASON, np.isfinite(RAIN).astype(float)), starts, window)[:, 0, 0]
    with np.errstate(invalid="ignore", divide="ignore"):
        means = np.where(known > 0, sums / known, np.nan)
    np.testing.assert_allclose(means, rolling_mean(RAIN, n, b), equal_nan=True)


# Planting tiers (D66): each place's typical date drives a crop model's start, a stage biofix and the gating


@pytest.fixture
def potato_here(monkeypatch):
    """The potato place `built` stored the tiers with (`_potato_place`)."""
    _potato_place(monkeypatch)
    yield
    planting_tiers_cleared()


def test_a_planting_map_is_each_cells_typical_date():
    from agdata import planting

    found = planting.planting_map("corn", "late", WINDOW, season=2025)
    for y in range(WINDOW.shape[0]):
        for x in range(WINDOW.shape[1]):
            lat, lng = NDFD.latlon(WINDOW.j0 + y, WINDOW.i0 + x)
            typical = planting.typical_planting("corn", float(lat), float(lng))
            assert typical is not None
            month, day = (int(p) for p in typical.late.split("-"))
            assert found[y, x] == date(2025, month, day).toordinal()
    assert np.isnan(planting.planting_map("potato", "mid", WINDOW, season=2025)).all()  # no Veg Path place near


TIERED = ("corn-stages", "tar-spot", "gray-leaf-spot", "gibberella-ear-rot-don", "potato-stages")
TIERED += ("late-blight-dsv", "early-blight-pdays", "soybean-stages", "white-mold", "frogeye-leaf-spot")
TIERED += ("soybean-cercospora", "red-crown-rot")


@pytest.mark.parametrize("model_id", TIERED)
def test_a_tiered_maps_cell_is_the_model_run_with_that_cells_planting(built, potato_here, model_id):
    from agdata import planting

    root, weather = built
    m = runner.find_model(model_id)
    crop_id, crop = planting.planting_crop(m.SPEC)  # type: ignore[misc]
    for day in DAYS:
        found = modelgrid.model_map(root, model_id, day, day, WINDOW, tier="mid")
        planted = planting.planting_map(crop, "mid", WINDOW, season=day.year)
        for y in range(WINDOW.shape[0]):
            for x in range(WINDOW.shape[1]):
                sown = date.fromordinal(int(planted[y, x]))
                point = _at_point(model_id, weather, y, x, day, sown=sown, own=crop_id == model_id)
                where = f"{model_id} {day} cell {y},{x}"
                if point.reason is not None:  # not emerged yet: not started
                    assert all(np.isnan(v[0, y, x]) for v in found.outputs.values()), (where, point.reason)
                    continue
                if point.biofix is not None:  # gated diseases have none
                    assert found.cell_biofix is not None
                    assert date.fromordinal(int(found.cell_biofix[0, y, x])) == point.biofix, where
                for name, v in point.outputs.items():
                    a, b = found.outputs[name][0, y, x], v[-1]
                    unit = next(q.unit for q in m.SPEC.outputs if q.name == name)
                    if name in DISCRETE or unit == "day":
                        assert a == b or abs(a - b) <= 1, (where, name, a, b)
                    else:
                        np.testing.assert_allclose(a, b, rtol=0.01, atol=ATOL[unit], equal_nan=True, err_msg=where)
                if m.SPEC.susceptible is not None:
                    # the gate looks the crop's margin ahead (stage dates are a few days off either way), so the
                    # point runs on past the day, as a request for a season does
                    margin = runner.find_model(m.SPEC.susceptible.crop).MARGIN_DAYS  # type: ignore[attr-defined]
                    ahead = _at_point(model_id, weather, y, x, day + timedelta(days=margin), sown=sown, start=day)
                    gate = ahead.susceptibility
                    assert gate is not None
                    assert found.outputs["susceptibility"][0, y, x] == gate[0], where


def test_without_a_tier_a_map_takes_the_specs_dates(built):
    root, _ = built
    plain = modelgrid.model_map(root, "corn-stages", DAYS[1], DAYS[1], WINDOW, tier=None)
    assert plain.cell_biofix is None and plain.biofix == [date(2025, 5, 10)]
    gated = modelgrid.model_map(root, "tar-spot", DAYS[1], DAYS[1], WINDOW, tier=None)
    assert "susceptibility" not in gated.outputs


def test_stored_tiers_are_the_crop_model_run_from_each_planting(built):
    """`agdata.croptiers` keeps soybean's outputs per tier: each cell's the model run from its planting date."""
    from agdata import planting

    root, weather = built
    sown = planting.planting_map("soybean", "early", WINDOW, season=2025)
    store = GridStore.open(root, modelmaps.INGREDIENTS, 2025, modelmaps.variables())
    t0 = store.index_of(DAYS[2])
    stage = store.read_steps(modelmaps.tier_key("soybean-stages", "stage", "early"), t0, t0 + 1)[0]
    for y, x in ((0, 0), (1, 2)):
        point = _at_point("soybean-stages", weather, y, x, DAYS[2], sown=date.fromordinal(int(sown[y, x])), own=True)
        assert stage[y, x] == point.outputs["stage"][-1]
    assert croptiers.last_stored(root, 2025) == LAST


def test_an_hourly_update_rewrites_only_the_recent_days(built, tmp_path):
    root, _ = built
    calls = []
    real = GridStore.write

    def spy(self, first, values, **kwargs):
        calls.append((first, next(iter(values.values())).shape[0]))
        return real(self, first, values, **kwargs)

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(GridStore, "write", spy)
        croptiers.update(root, WINDOW, 2025, LAST, since=LAST - timedelta(days=croptiers.REWRITE_DAYS))
    assert calls and all(first == LAST - timedelta(days=croptiers.REWRITE_DAYS) for first, _ in calls)
    assert all(n == croptiers.REWRITE_DAYS + 1 for _, n in calls)


def test_a_restitched_run_gets_its_tiers_again(built, tmp_path, monkeypatch):
    """A forecast run's tiers are recomputed when a restitch moves its first day, not every hour otherwise."""
    from types import SimpleNamespace

    from agdata import series

    root, _ = built
    calls = []
    first_day = {"value": "2025-07-25"}
    monkeypatch.setattr(croptiers, "update", lambda *args, **kwargs: calls.append(kwargs.get("run_first")) or [])
    monkeypatch.setattr(series, "current_forecast", lambda _: SimpleNamespace(path=tmp_path, last_hour=None))
    monkeypatch.setattr(croptiers, "forecast_first_day", lambda _: first_day["value"])
    today = date(2025, 7, 25)
    croptiers.refresh(root, WINDOW, today)
    croptiers.refresh(root, WINDOW, today)
    first_day["value"] = "2025-07-26"
    croptiers.refresh(root, WINDOW, today)
    assert [c for c in calls if c is not None] == [date(2025, 7, 25), date(2025, 7, 26)]


def test_a_tier_stored_crop_takes_a_tier(built):
    root, _ = built
    with pytest.raises(ValueError, match="per planting tier"):
        modelgrid.model_map(root, "soybean-stages", DAYS[1], DAYS[1], WINDOW, tier=None)


def test_stored_stage_days_are_the_stages_first_days_and_a_store_without_them_says_so(built, potato_here, monkeypatch):
    """`croptiers` keeps each tier's first day at each stage (D70), the first day the stored stage series reaches
    it; a blight's emergence biofix reads them. A store without them is one to rebuild (`modelmaps.status`), and
    until then the blight's planted cells are missing rather than started on a guess."""
    from agdata import planting
    from agmodels.crops import stage_days

    root, _ = built
    found = croptiers.reached(root, "potato-stages", "mid", 2025, WINDOW)
    assert found is not None and found[1] == LAST
    sown = modelgrid._Planting(crop_id="potato-stages", crop="potato", tier="mid", window=WINDOW)
    p = planting.planting_map("potato", "mid", WINDOW, season=2025)
    k = 1  # emergence
    begin = date.fromordinal(int(np.nanmin(p)))
    index = stage_days(modelgrid._crop_stages(root, sown, begin, LAST, None), k + 1)[k]
    first_days = np.where(np.isnan(p), np.nan, np.where(np.isfinite(index), begin.toordinal() + index, np.inf))
    np.testing.assert_array_equal(found[0][k], first_days)
    assert modelmaps.status(root, 2025) is None

    monkeypatch.setattr(croptiers, "REACHED", "_not_kept")  # as a store built before they were kept
    store = GridStore.open(root, INGREDIENTS, 2025, modelmaps.variables())
    assert "potato-stages.mid" in croptiers.missing_reached(store)
    assert modelmaps.status(root, 2025) == modelmaps.NO_STAGE_DAYS
    monkeypatch.setattr(croptiers, "reached", lambda *args: None)
    without = modelgrid.model_map(root, "early-blight-pdays", DAYS[1], DAYS[1], WINDOW, tier="mid")
    assert without.cell_biofix is not None and without.level is not None
    planted = np.isfinite(p)
    assert np.isinf(without.cell_biofix[0][planted]).all()
    assert np.isnan(without.level[0][planted]).all()
