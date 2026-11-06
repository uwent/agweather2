"""Models' ingredients on the grid (`agdata.modelmaps`): built, updated from a changed day, and continued by a run."""

from datetime import date, timedelta

import numpy as np
import pytest

from agdata import modelmaps
from agdata.catalog import DAILY_VARIABLES
from agdata.store import DAILY, GridStore
from agdata.testing import WINDOW
from agmodels.registry import all_models
from agmodels.testing import DATES, WEATHER

# Five months across a New Year (each day of each variable is a chunk, so a long archive makes slow tests)
FIRST, LAST = date(2025, 9, 1), date(2026, 1, 31)
K0 = DATES.index(FIRST)
SPAN = DATES[K0 : DATES.index(LAST) + 1]
HOLE = (date(2025, 10, 20), date(2025, 10, 22))  # a short gap the runner's estimate bridges
# One of each kind, for the update tests: a total and count (P-days' 7-day mean), a total (late blight), the
# held minimum (freeze factor), days ahead (cotton), and a shared moving mean
KEYS = (
    "early-blight-pdays.pdays",
    "late-blight-dsv.dsv",
    "insect_freeze_factor",
    "cotton-planting.air_temperature_min_9_day_ahead",
    "air_temperature_min_21_day",
)


def _weather(shift: float = 0.0) -> dict[str, np.ndarray]:
    """WEATHER on every cell of the window, each cell warmer or cooler and noisier (seeded), missing in HOLE."""
    rng = np.random.default_rng(11)
    cells = np.linspace(-3, 3, int(np.prod(WINDOW.shape))).reshape(WINDOW.shape)
    out = {}
    gone = [k for k, d in enumerate(SPAN) if HOLE[0] <= d <= HOLE[1]]
    for name, series in WEATHER.items():
        v = np.broadcast_to(series[K0 : K0 + len(SPAN), None, None], (len(SPAN), *WINDOW.shape)).astype(float)
        if DAILY_VARIABLES[name].unit == "degC":
            v = v + cells + shift + rng.normal(0, 1.0, v.shape)
        variable = DAILY_VARIABLES[name]
        v = np.clip(v, variable.valid_min, variable.valid_max)
        v[gone] = np.nan
        out[name] = variable.decode(variable.encode(v))  # as the daily store holds it

    return out


def _archive(root, weather, last: date = LAST) -> None:
    n = (last - FIRST).days + 1
    for year in range(FIRST.year, last.year + 1):
        try:
            store = GridStore.create(root, DAILY, year, WINDOW, DAILY_VARIABLES.values())
        except FileExistsError:
            store = GridStore.open(root, DAILY, year, DAILY_VARIABLES.values())
        ks = [k for k in range(n) if SPAN[k].year == year]
        store.write(SPAN[ks[0]], {name: v[ks[0] : ks[-1] + 1] for name, v in weather.items()}, source="test")


def _variables():
    return [v for k in KEYS for v in modelmaps.stored()[k].variables()]


def _inputs(weather) -> dict[str, np.ndarray]:
    """The days of weather KEYS' models read (6 of WEATHER's 24 variables): each is a chunk a day to write."""
    models = all_models()
    names = {q.name for k in KEYS for q in models[modelmaps.stored()[k].model_id].SPEC.inputs}
    return {name: v for name, v in weather.items() if name in names}


def _series(root, name: str, first: date, last: date) -> np.ndarray:
    """Days first..last of a stored variable, one read per year."""
    parts = []
    for year in range(first.year, last.year + 1):
        store = GridStore.open(root, modelmaps.INGREDIENTS, year, modelmaps.variables())
        a, b = max(first, date(year, 1, 1)), min(last, date(year, 12, 31))
        parts.append(store.read_steps(name, store.index_of(a), store.index_of(b) + 1))
    return np.concatenate(parts)


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    root = tmp_path_factory.mktemp("full")
    weather = _weather()
    _archive(root, weather)
    written = modelmaps.update(root, WINDOW, date(2025, 10, 1), LAST)
    assert written[0] == FIRST  # nothing stored before: resumed from the year's first day of weather
    return root, weather


def _direct(weather) -> dict[str, np.ndarray]:
    """Each stored ingredient straight from its model over the whole series, gaps filled as the runner does."""
    from agdata.catalog import GAP_FILL
    from agmodels.gaps import fill_inputs

    filled, _ = fill_inputs(weather, {n: GAP_FILL[n] for n in weather if n in GAP_FILL})
    context = {
        "day_of_year": np.array([d.timetuple().tm_yday for d in SPAN], dtype=float),
        "year": np.array([d.year for d in SPAN], dtype=float),
    }
    out = {}
    models = all_models()
    for s in modelmaps.stored().values():
        m = models[s.model_id]
        values = m.ingredients({q.name: filled[q.name] for q in m.SPEC.inputs} | context)  # type: ignore[attr-defined]
        out[s.key] = values[s.ingredient.name]
    return out


def test_every_stored_ingredient_is_its_models_own(built):
    root, weather = built
    direct = _direct(weather)
    first, last = date(2025, 10, 2), date(2026, 1, 20)  # a full window behind, cotton's days ahead in front
    k0, k1 = SPAN.index(first), SPAN.index(last) + 1
    for s in modelmaps.stored().values():
        stored = _series(root, s.key, first, last)
        scale = s.variables()[0].scale
        np.testing.assert_allclose(stored, direct[s.key][k0:k1], atol=scale / 2 + 1e-9, equal_nan=True, err_msg=s.key)


def test_running_totals_and_counts_restart_on_january_1(built):
    root, weather = built
    direct = _direct(weather)
    for s in modelmaps.stored().values():
        if not s.total:
            continue
        for begin, last in ((FIRST, date(2025, 12, 31)), (date(2026, 1, 1), date(2026, 1, 20))):
            k0, k1 = SPAN.index(begin), SPAN.index(last) + 1
            v = direct[s.key][k0:k1]
            total = _series(root, f"{s.key}.total", begin, last)
            # rounded once, from daily values each rounded to their own step
            atol = s.variables()[1].scale / 2 + len(v) * s.variables()[0].scale / 2 + 1e-6
            np.testing.assert_allclose(total, np.cumsum(np.nan_to_num(v), axis=0), atol=atol, err_msg=s.key)
            if s.known:
                known = _series(root, f"{s.key}.known", begin, last)
                np.testing.assert_array_equal(known, np.cumsum(np.isfinite(v), axis=0), err_msg=s.key)


def test_an_update_from_a_day_gives_what_building_from_january_gives(tmp_path, built):
    """Totals and the freeze factor's running minimum continue from the stored day before; cotton's days ahead are
    rewritten. Built to mid-November, then updated through the end: the same as building it all at once."""
    full, weather = built
    weather = _inputs(weather)
    root = tmp_path / "incremental"
    _archive(root, weather, last=date(2025, 11, 15))
    modelmaps.update(root, WINDOW, FIRST, date(2025, 11, 15), keys=KEYS)
    _archive(root, weather)
    written = modelmaps.update(root, WINDOW, date(2025, 11, 16), LAST, keys=KEYS)
    assert written[0] == date(2025, 11, 16) - timedelta(days=8)  # cotton reads 8 days ahead
    for v in _variables():
        a = _series(root, v.name, date(2025, 10, 1), LAST)
        b = _series(full, v.name, date(2025, 10, 1), LAST)
        np.testing.assert_allclose(
            a, b, atol=v.scale + 1e-9, equal_nan=True, err_msg=v.name
        )  # a step either way: float order


def test_a_changed_day_is_recomputed_as_far_as_it_reaches(tmp_path, built):
    weather = _inputs(built[1])
    root = tmp_path / "changed"
    _archive(root, weather)
    modelmaps.update(root, WINDOW, FIRST, LAST, keys=KEYS)
    changed = {name: v.copy() for name, v in weather.items()}
    k = SPAN.index(date(2025, 11, 1))
    for name, v in changed.items():
        if DAILY_VARIABLES[name].unit == "degC":
            v[k] += 10  # a day ten degrees warmer (whole tenths, as stored)
    _archive(root, changed)
    modelmaps.update(root, WINDOW, SPAN[k], LAST, keys=KEYS)
    redo = tmp_path / "redo"
    _archive(redo, changed)
    modelmaps.update(redo, WINDOW, FIRST, LAST, keys=KEYS)
    for v in _variables():
        a = _series(root, v.name, FIRST, LAST)
        b = _series(redo, v.name, FIRST, LAST)
        np.testing.assert_allclose(
            a, b, atol=v.scale + 1e-9, equal_nan=True, err_msg=v.name
        )  # a step either way: float order


def test_a_run_continues_the_archive(tmp_path, built):
    """A run's ingredients from its first day, with the archive's weather and totals before it: the same as an
    archive holding the run's days."""
    full, weather = built
    weather = _inputs(weather)
    run_first = date(2025, 12, 20)
    archive = tmp_path / "archive"
    _archive(archive, weather, last=run_first - timedelta(days=1))
    modelmaps.update(archive, WINDOW, FIRST, run_first - timedelta(days=1), keys=KEYS)
    run = tmp_path / "run"
    k = SPAN.index(run_first)
    tail = {name: v[k:] for name, v in weather.items()}
    for year in (2025, 2026):
        store = GridStore.create(run, DAILY, year, WINDOW, DAILY_VARIABLES.values())
        ks = [n for n, d in enumerate(SPAN[k:]) if d.year == year]
        store.write(SPAN[k + ks[0]], {name: v[ks[0] : ks[-1] + 1] for name, v in tail.items()}, source="test")
    modelmaps.update(archive, WINDOW, run_first, LAST, run=run, run_first=run_first, keys=KEYS)
    for v in _variables():
        a = _series(run, v.name, run_first, LAST)
        b = _series(full, v.name, run_first, LAST)
        np.testing.assert_allclose(
            a, b, atol=v.scale + 1e-9, equal_nan=True, err_msg=v.name
        )  # a step either way: float order


def test_a_years_build_runs_from_january_and_its_status_says_what_it_needs(tmp_path, monkeypatch):
    """`build` (manage.py ingredients) on five days of January: built and marked current, then a day missing; a year
    whose only stale variables are the crops' tiers rebuilds just the tiers."""
    from agdata import croptiers

    weather = _weather()
    k = SPAN.index(date(2026, 1, 1))
    store = GridStore.create(tmp_path, DAILY, 2026, WINDOW, DAILY_VARIABLES.values())
    store.write(date(2026, 1, 1), {name: v[k : k + 5] for name, v in weather.items()}, source="test")
    assert modelmaps.status(tmp_path, 2025) is None  # no daily store: nothing to build from
    assert modelmaps.status(tmp_path, 2026) == "not built"
    assert modelmaps.build(tmp_path, WINDOW, 2026) == (date(2026, 1, 1), date(2026, 1, 5))
    assert modelmaps.status(tmp_path, 2026) is None
    store.write(date(2026, 1, 6), {name: v[k + 5 : k + 6] for name, v in weather.items()}, source="test")
    assert modelmaps.status(tmp_path, 2026) == "1 days missing (from 2026-01-06)"

    tiers = {v.name for v in modelmaps.tier_variables()}
    monkeypatch.setattr(GridStore, "stale_variables", classmethod(lambda cls, *args: tiers))
    monkeypatch.setattr(modelmaps, "build_year", lambda *args, **kwargs: pytest.fail("rebuilt the whole year"))
    updated = []
    monkeypatch.setattr(croptiers, "update", lambda data_dir, window, year, last, lock: updated.append((year, last)))
    assert modelmaps.status(tmp_path, 2026) == f"{len(tiers)} stale variables"
    assert modelmaps.build(tmp_path, WINDOW, 2026) == (date(2026, 1, 1), date(2026, 1, 6))
    assert updated == [(2026, date(2026, 1, 6))]
