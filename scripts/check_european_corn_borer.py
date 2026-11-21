"""European corn borer's flights against DATCP's black light traps, 2020–2026, and its dates on the 1996–2025 normals (models-plan part H, batch H2).

For each black light site-year with a location (docs/validation/data/datcp-blacklight-traps/), the model runs on the
archive's daily min and max at the site's cell from January 1. The site-year's weekly catches are split into a spring
and a summer flight at the model's own trough between its two flight peaks there (not check_insect_traps.py's fixed
July 7), and each flight's first catch, the week its cumulative catch reaches 50 % and its peak week (percentiles and
peak only for flights of 5 or more moths) are compared with the model's dates: its first moths (1 % of the flight), 50
% and peak. Days off: 0 inside the observed week (the 7 days ending on its date), else days before (−) or after (+)
it. Also: the degree days (modified 50/86 °F from January 1) at the middle of each observed week, and by August 1,
north (Wausau, Marshfield, Antigo, at 44.6 °N and above) against the rest, for the second-generation question.

    uv run python scripts/check_european_corn_borer.py [--out docs/validation/models/european-corn-borer/traps.md]

Its summary is the "Against Wisconsin's black light traps" section of docs/validation/models/european-corn-borer.md.
The normals table is printed by `uv run app/manage.py shell < scripts/corn_moth_normals.py`.
"""

import argparse
import csv
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from check_insect_traps import DATA, MIN_FLIGHT, SiteYear, flight_of, read_blacklight

from agdata.catalog import DAILY_VARIABLES
from agdata.grid import NDFD
from agdata.store import DAILY, GridStore
from agmodels.degree_days import degree_days_modified, degree_days_sine
from agmodels.insects.european_corn_borer import INSECT
from agmodels.phenology import curves, dd_grid
from agmodels.registry import model

NORTH_LAT = 44.6
SUSPECT = {("Arlington", 2021), ("Arlington", 2022), ("Arlington", 2023)}  # mid-May "corn borers" (README, Caveats)


def locations() -> dict[str, tuple[float, float]]:
    with (DATA / "sites.csv").open() as f:
        return {
            r["site"]: (float(r["lat"]), float(r["lon"])) for r in csv.DictReader(f) if r["network"] == "black light"
        }


def offset(day: date | None, week_end: date | None) -> int | None:
    if day is None or week_end is None:
        return None
    if week_end - timedelta(days=6) <= day <= week_end:
        return 0
    return (day - week_end).days if day > week_end else (day - (week_end - timedelta(days=6))).days


def model_events() -> dict[str, float]:
    """The model's flight events in degree days from January 1: 1 %, 50 % and the peak of each flight, and the trough."""
    x = dd_grid()
    t = curves(INSECT)
    done = t["generations_adult_flight"]
    act = t["activity_adult_flight"]
    p1, p2 = int(np.argmax(np.where(x < 1200, act, 0))), int(np.argmax(np.where(x > 1200, act, 0)))
    return {
        "first 1": float(np.interp(0.01, done, x)),
        "first 50": float(np.interp(0.5, done, x)),
        "first peak": float(x[p1]),
        "trough": float(x[p1 + int(np.argmin(act[p1:p2]))]),
        "second 1": float(np.interp(1.01, done, x)),
        "second 50": float(np.interp(1.5, done, x)),
        "second peak": float(x[p2]),
    }


def day_reaching(total: np.ndarray, dd: float, year: int) -> date | None:
    k = np.flatnonzero(np.nan_to_num(total) >= dd)
    return date(year, 1, 1) + timedelta(days=int(k[0])) if len(k) else None


def show(v: int | None) -> str:
    return "–" if v is None else f"{v:+d}" if v else "0"


def summarize(label: str, values: list[int]) -> str:
    if not values:
        return f"| {label} | 0 | | | | |"
    a = np.array(values)
    return f"| {label} | {len(a)} | {np.sum(a == 0)} | {np.sum(np.abs(a) <= 7)} | {np.median(a):+.0f} | {np.percentile(a, 10):+.0f} to {np.percentile(a, 90):+.0f} |"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="docs/validation/models/european-corn-borer/traps.md")
    parser.add_argument("--data", default="data")
    args = parser.parse_args()
    ev = model_events()
    where = locations()
    temps = [DAILY_VARIABLES["air_temperature_min"], DAILY_VARIABLES["air_temperature_max"]]
    stores: dict[int, GridStore] = {}
    m = model("european-corn-borer")
    site_years: list[SiteYear] = [s for s in read_blacklight() if s.species == "European corn borer"]
    lines = [
        "# European corn borer: flights against DATCP's black light traps, 2020–2026",
        "",
        f"Written by `scripts/check_european_corn_borer.py` from DATCP's black light tables (`docs/validation/data/datcp-blacklight-traps/`) and the archive at each site's cell. The model's events (modified 50/86 °F from January 1): first moths (1 %) {ev['first 1']:.0f}, 50 % {ev['first 50']:.0f}, peak {ev['first peak']:.0f}; trough {ev['trough']:.0f}; summer flight 1 % {ev['second 1']:.0f}, 50 % {ev['second 50']:.0f}, peak {ev['second peak']:.0f}. Each site-year's weeks are split into spring and summer flights at the day the model reaches its trough there. Days off: 0 inside the observed week, else days before (−) or after (+) it. DD: degree days from January 1 at the observed week's middle. Percentiles and peaks only for flights of {MIN_FLIGHT} or more moths; first catch only where the first week read caught none. Arlington 2021–2023 (marked \\*) caught moths in mid-May that may be misidentified.",
        "",
        "| Year | Site | Lat | DD by Aug 1 | Flight | Moths | First catch (off, DD) | 50 % (off, DD) | Peak (off, DD) |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    offs: dict[tuple[str, str, str], list[int]] = {}
    dds: dict[tuple[str, str, str], list[float]] = {}
    by_aug1: dict[str, list[float]] = {"north": [], "south": []}
    spring_share: dict[str, list[tuple[str, int, int, int]]] = {"north": [], "south": []}
    pooled: dict[str, list[tuple[float, int]]] = {"north": [], "south": []}
    for sy in site_years:
        loc = where.get(sy.site)
        if loc is None or not any(w.count is not None for w in sy.weeks):
            continue
        cell = NDFD.cell_of(*loc)
        assert cell is not None
        if sy.year not in stores:
            stores[sy.year] = GridStore.open(Path(args.data), DAILY, sy.year, temps)
        lo, hi = (stores[sy.year].read_point(n, *cell) for n in ("air_temperature_min", "air_temperature_max"))
        good = np.isfinite(lo) & np.isfinite(hi)
        f_lo, f_hi = (np.where(good, v * 1.8 + 32, 0.0) for v in (lo, hi))
        total = np.cumsum(degree_days_modified(f_lo, f_hi, base=50, upper=86))
        sine = np.cumsum(degree_days_sine(f_lo, f_hi, 50) - degree_days_sine(f_lo, f_hi, 86))
        out = m.outputs({"air_temperature_min": lo, "air_temperature_max": hi})
        assert np.allclose(np.nan_to_num(out["dd_total"]), total, atol=0.01) or not good.all()
        region = "north" if loc[0] >= NORTH_LAT else "south"
        aug1 = float(total[(date(sy.year, 8, 1) - date(sy.year, 1, 1)).days])
        by_aug1[region].append(aug1)
        trough = day_reaching(total, ev["trough"], sy.year)
        split = trough or date(sy.year, 12, 31)
        spring = flight_of(weeks=[w for w in sy.weeks if w.end <= split], name="first")
        summer = flight_of(weeks=[w for w in sy.weeks if w.end > split], name="second")
        spring_share[region].append((sy.site, sy.year, spring.total, summer.total))
        for w in sy.weeks:  # every moth at its week's middle, for the season's catch by degree days
            if w.count:
                pooled[region].append((float(total[(w.end - timedelta(days=3) - date(sy.year, 1, 1)).days]), w.count))
        star = "\\*" if (sy.site, sy.year) in SUSPECT else ""
        for name, fl, key in (("spring", spring, "first"), ("summer", summer, "second")):
            cells = []
            for what, observed, dd in (
                ("first", None if fl.caught_in_first_week_read else fl.first_catch, ev[f"{key} 1"]),
                ("50", fl.percent_weeks[50], ev[f"{key} 50"]),
                ("peak", fl.peak, ev[f"{key} peak"]),
            ):
                ours = day_reaching(total, dd, sy.year)
                o = offset(ours, observed)
                obs_dd = None
                if observed is not None:
                    mid = (observed - timedelta(days=3) - date(sy.year, 1, 1)).days
                    obs_dd = float(total[mid])
                    if o is not None:
                        offs.setdefault((region, name, what), []).append(o)
                        if (sy.site, sy.year) not in SUSPECT:
                            offs.setdefault((region, name, what + " (no Arlington 2021–23)"), []).append(o)
                    dds.setdefault((region, name, what), []).append(obs_dd)
                    if what == "50":  # VDIFN's peaks (740 and 1,950, single sine 50/86 °F), the old model's midpoints
                        vdifn = day_reaching(sine, 740 if key == "first" else 1950, sy.year)
                        if (v := offset(vdifn, observed)) is not None:
                            offs.setdefault((region, name, "50, VDIFN's peak"), []).append(v)
                cells.append("–" if observed is None else f"{observed:%b %-d} ({show(o)}, {obs_dd:.0f})")
            lines.append(
                f"| {sy.year} | {sy.site}{star} | {loc[0]:.2f} | {aug1:.0f} | {name} | {fl.total} | {' | '.join(cells)} |"
            )
    lines += [
        "",
        "## Summary: the model's dates against the observed weeks",
        "",
        "| Region, flight, event | n | Inside the week | Within a week | Median, days | 10th–90th percentile |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for key in sorted(offs):
        lines.append(summarize(", ".join(key), offs[key]))
    lines += [
        "",
        "## Degree days (modified 50/86 °F from January 1) at the observed weeks",
        "",
        "| Region, flight, event | n | Median | 25th–75th percentile |",
        "| --- | --- | --- | --- |",
    ]
    for key in sorted(dds):
        a = np.array(dds[key])
        lines.append(
            f"| {', '.join(key)} | {len(a)} | {np.median(a):.0f} | {np.percentile(a, 25):.0f} to {np.percentile(a, 75):.0f} |"
        )
    lines += ["", "## One flight or two", ""]
    for region in ("south", "north"):
        a = np.array(by_aug1[region])
        rows = spring_share[region]
        caught = [r for r in rows if r[2] + r[3] > 0]
        with_spring = [r for r in caught if r[2] > 0]
        lines.append(
            f"- {region.capitalize()}: {len(rows)} site-years; degree days by August 1 median {np.median(a):.0f} (range {a.min():.0f}–{a.max():.0f}); {len(caught)} caught corn borers, {len(with_spring)} of them before the model's trough; moths before the trough {sum(r[2] for r in caught)}, after {sum(r[3] for r in caught)}."
        )
        d = np.array([v for v, _ in pooled[region]])
        c = np.array([n for _, n in pooled[region]], dtype=float)
        o = np.argsort(d)
        cum = np.cumsum(c[o]) / c.sum()
        pct = ", ".join(f"{p} % at {np.interp(p / 100, cum, d[o]):.0f}" for p in (10, 25, 50, 75, 90))
        lines.append(
            f"  - The season's {c.sum():.0f} moths by degree days at their week's middle (every moth alike): {pct}."
        )
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text("\n".join(lines) + "\n")
    print("\n".join(lines[-40:]))


if __name__ == "__main__":
    main()
