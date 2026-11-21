"""Imported cabbageworm's flights against Wisconsin's iNaturalist records of cabbage white butterflies (part H, H3).

The records (research grade, Wisconsin, 2016–2026; `tmp/inat-check/obs_pieris_rapae_wi.csv`, from the iNaturalist
check of 2026-11-19, `tmp/inat-check/report.md`) are placed at their own cell's running degree days on the model's
setting (the modified average, 50/86 °F, from January 1; the archive's `dd_modified_50_86`), as
`tmp/inat-check/analyze.py` does for the old setting. Kept: records with a date, coordinates not obscured, located
within 5 km, inside the archive's box. Observers' effort: each day's research-grade records of all Lepidoptera in
Wisconsin (iNaturalist's histogram, cached in `tmp/inat-check/cache`), placed at the degree days of the records'
median cell that day. The index is cabbage whites per 1,000 Lepidoptera records in 50-degree-day bins (bins with
fewer than 300 Lepidoptera records left out), smoothed over three bins; its local peaks are the flights.

    uv run python scripts/check_imported_cabbageworm.py
"""

import csv
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
INAT = ROOT / "tmp" / "inat-check"
sys.path.insert(0, str(INAT))

from inat import get  # noqa: E402  # pyright: ignore[reportMissingImports]  (tmp/inat-check, on the path above; iNaturalist client; reads the cache, fetching only what's missing)

from agdata.catalog import CUMULATIVE_VARIABLES  # noqa: E402
from agdata.grid import NDFD  # noqa: E402
from agdata.store import CUMULATIVE, GridStore  # noqa: E402
from agmodels.insects.imported_cabbageworm import INSECT  # noqa: E402
from agmodels.phenology import curves, dd_grid  # noqa: E402

DATA = ROOT / "data"
TOTAL = "dd_modified_50_86"
LEPIDOPTERA = 47157
YEARS = range(2016, 2027)
BIN = 50


def running(year: int, cells: list[tuple[int, int]]) -> np.ndarray:
    store = GridStore.open(DATA, CUMULATIVE, year, [CUMULATIVE_VARIABLES[TOTAL]])
    return store.read_cells(TOTAL, cells)


def records() -> list[dict]:
    kept = []
    with (INAT / "obs_pieris_rapae_wi.csv").open() as f:
        for o in csv.DictReader(f):
            if not o["observed_on"] or o["obscured"] == "True":
                continue
            d = date.fromisoformat(o["observed_on"])
            if d.year not in YEARS or (o["accuracy_m"] and float(o["accuracy_m"]) > 5000):
                continue
            cell = NDFD.cell_of(float(o["lat"]), float(o["lon"]))
            if cell is not None:
                kept.append({**o, "date": d, "cell": cell})
    return kept


def main() -> None:
    obs = records()
    by_year = defaultdict(list)
    for o in obs:
        by_year[o["date"].year].append(o)
    used = []
    for year, os_ in sorted(by_year.items()):
        store = GridStore.open(DATA, CUMULATIVE, year, [CUMULATIVE_VARIABLES[TOTAL]])
        cells = sorted({o["cell"] for o in os_ if store.window.contains(*o["cell"])})
        if not cells:
            continue
        dd = running(year, cells)
        col = {c: k for k, c in enumerate(cells)}
        for o in os_:
            doy = o["date"].timetuple().tm_yday - 1
            if o["cell"] in col and doy < dd.shape[0] and np.isfinite(dd[doy, col[o["cell"]]]):
                used.append({**o, "dd": float(dd[doy, col[o["cell"]]])})
    lat = float(np.median([float(o["lat"]) for o in used]))
    lon = float(np.median([float(o["lon"]) for o in used]))
    ref = NDFD.cell_of(lat, lon)
    assert ref is not None
    focal = defaultdict(int)
    for o in used:
        focal[o["date"]] += 1
    ref_dd, effort, count = [], [], []
    for year in sorted(by_year):
        series = running(year, [ref])[:, 0]
        days = get("observations/histogram", taxon_id=LEPIDOPTERA, place_id=32, quality_grade="research", interval="day", date_field="observed", d1=f"{year}-01-01", d2=f"{year}-12-31")["results"]["day"]  # fmt: skip
        for k, v in days.items():
            d = date.fromisoformat(k[:10])
            doy = d.timetuple().tm_yday - 1
            if doy < len(series) and np.isfinite(series[doy]) and series[doy] > 0:
                ref_dd.append(series[doy])
                effort.append(v)
                count.append(focal.get(d, 0))
    ref_dd, effort, count = map(np.asarray, (ref_dd, effort, count))
    edges = np.arange(0, 3600 + BIN, BIN)
    k = np.digitize(ref_dd, edges) - 1
    index = np.full(len(edges) - 1, np.nan)
    for b in range(len(edges) - 1):
        e = effort[k == b].sum()
        if e >= 300:
            index[b] = count[k == b].sum() / e * 1000
    centers = edges[:-1] + BIN / 2
    smooth = np.convolve(np.nan_to_num(index), np.ones(3) / 3, mode="same")
    peaks = [
        float(centers[b])
        for b in range(1, len(smooth) - 1)
        if smooth[b] > smooth[b - 1] and smooth[b] >= smooth[b + 1] and centers[b] < 2600
    ]
    print(f"{len(used)} records ({len({o['user'] for o in used})} observers), effort cell {lat:.2f}, {lon:.2f}")
    print("Index by bin (records per 1,000 Lepidoptera; smoothed):")
    for c, v, s in zip(centers, index, smooth, strict=True):
        if c < 3300:
            print(f"  {c:6.0f}  {v:6.1f}  {s:6.1f}")
    print("Local peaks of the smoothed index below 2,600:", peaks)
    spring = (centers < 700) & np.isfinite(index)
    w = np.where(spring, np.nan_to_num(index), 0)
    cum = np.cumsum(w) / w.sum()
    print("Spring (below 700) 10, 50, 90 %:", [round(float(np.interp(q, cum, centers))) for q in (0.1, 0.5, 0.9)])
    # Flights between the index's troughs (lowest smoothed bins near 625 and 1,525): each one's median
    for lo, hi in ((0, 650), (650, 1550), (1550, 2300)):
        inside = (centers > lo) & (centers < hi) & np.isfinite(index)
        w = np.where(inside, np.nan_to_num(index), 0)
        print(f"Records between {lo} and {hi}: median at {float(np.interp(0.5, np.cumsum(w) / w.sum(), centers)):.0f}")
    x = dd_grid()
    a = curves(INSECT)["activity_adult_flight"]
    model_peaks = [float(x[i]) for i in np.flatnonzero((a[1:-1] > a[:-2]) & (a[1:-1] >= a[2:]) & (a[1:-1] > 0.05)) + 1]
    print("Model's flight peaks:", model_peaks[:4])
    done = curves(INSECT)["generations_adult_flight"]
    print("Model's flights' 50 %:", [round(float(np.interp(g + 0.5, done, x))) for g in range(4)])


if __name__ == "__main__":
    main()
