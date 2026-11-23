"""Codling moth's estimated first catch against DATCP's apple pest trap network, 2020–2025 (models plan B4, step 4).

DATCP (Wisconsin's Department of Agriculture, Trade and Consumer Protection) publishes each cooperating orchard's
weekly codling moth trap count; docs/validation/data/datcp-apple-traps/codling-moth-site-years.csv has, per site and
year, the first week with a catch and the first week with 5 or more moths (DATCP's biofix threshold), each dated by
the week's last day. Here the model's first catch (estimated from latitude, Jones et al. 2013) on the archive at the
site's cell is compared with that week: 0 if inside it (the 7 days ending on the date), else days early (−) or late
(+) of it. NEWA's default (404 DD50 without an upper from January 1, on the archive's days) is shown beside it.
Mating-disruption orchards are left out (catches suppressed), as are site-years whose first reported week already
had a catch (first catch may have come before traps were read).

    uv run python scripts/check_codling_moth_traps.py [--out docs/validation/models/codling-moth/traps.md]

Its summary is the "First catch against Wisconsin's traps" section of docs/validation/models/codling-moth.md.
"""

import argparse
import csv
import re
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from check_codling_moth import daily_at, ours

from agdata.catalog import DAILY_VARIABLES
from agdata.grid import NDFD
from agdata.store import DAILY, GridStore
from agmodels.degree_days import degree_days_sine

SITE_YEARS = Path("docs/validation/data/datcp-apple-traps/codling-moth-site-years.csv")
MONTHS = {m: k for k, m in enumerate(("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct"), start=1)}


def read_site_years() -> list[tuple[int, str, bool, str, str, str, tuple[float, float] | None]]:
    """(year, site, mating disruption, weeks read, first week with a catch, first week with 5 or more, location)."""
    rows = []
    with SITE_YEARS.open() as f:
        for r in csv.DictReader(f):
            loc = (float(r["lat"]), float(r["lon"])) if r["lat"] else None
            rows.append(
                (
                    int(r["year"]),
                    r["site"],
                    r["mating_disruption"] == "1",
                    r["weeks_read"],
                    r["first_week_with_catch"],
                    r["first_week_5_or_more"],
                    loc,
                )
            )
    return rows


def when(year: int, text: str) -> date | None:
    m = re.match(r"(\w{3}) (\d+)", text)
    return date(year, MONTHS[m.group(1)], int(m.group(2))) if m and m.group(1) in MONTHS else None


def offset(day: date | None, week_end: date | None) -> int | None:
    if day is None or week_end is None:
        return None
    if week_end - timedelta(days=6) <= day <= week_end:
        return 0
    return (day - week_end).days if day > week_end else (day - (week_end - timedelta(days=6))).days


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="docs/validation/models/codling-moth/traps.md")
    parser.add_argument("--data", default="data")
    args = parser.parse_args()
    rows = read_site_years()
    temps = [DAILY_VARIABLES["air_temperature_min"], DAILY_VARIABLES["air_temperature_max"]]
    stores: dict[int, GridStore] = {}
    lines = [
        "# Codling moth: estimated first catch against DATCP's trap network, 2020–2025",
        "",
        "Written by `scripts/check_codling_moth_traps.py` from DATCP's trap tables (`docs/validation/data/datcp-apple-traps/`). Days off: 0 inside the observed week (the 7 days ending on its date), else days before (−) or after (+) it. Ours: first catch from latitude on the archive at the site's cell. NEWA: its 404 DD50 default on the same days.",
        "",
        "| Year | Site | First week with a catch | Ours | Days off | NEWA's | Days off | First week ≥ 5 | Ours off | NEWA off |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    offs = {"ours catch": [], "newa catch": [], "ours five": [], "newa five": []}
    skipped = []
    observed_dd: list[tuple[float, float, float]] = []  # (latitude, DD50/86 from January 1 at the week's middle, ours)
    for year, name, md, reported, first, five, loc in rows:
        first_day, five_day = when(year, first), when(year, five)
        start = when(year, reported.split("–")[0])
        if md or loc is None or first_day is None:
            skipped.append(
                f"{year} {name} ({'mating disruption' if md else 'no location' if loc is None else 'no catch'})"
            )
            continue
        if start is not None and first_day <= start:
            skipped.append(f"{year} {name} (caught in the first week read)")
            continue
        cell = NDFD.cell_of(*loc)
        assert cell is not None
        if year not in stores:
            stores[year] = GridStore.open(Path(args.data), DAILY, year, temps)
        lo, hi = daily_at(stores[year], cell)
        out = ours(lo, hi, year, loc[0])
        k = int(np.argmax(np.nan_to_num(out["dd_after_first_catch"]) > 0))
        our_day = date(year, 1, 1) + timedelta(days=k)
        good = np.isfinite(lo) & np.isfinite(hi)
        f_lo, f_hi = (np.where(good, v * 1.8 + 32, 0.0) for v in (lo, hi))
        jan1 = np.round(np.cumsum(degree_days_sine(f_lo, f_hi, 50)))
        jan1_86 = np.cumsum(degree_days_sine(f_lo, f_hi, 50) - degree_days_sine(f_lo, f_hi, 86))
        newa_day = date(year, 1, 1) + timedelta(days=int(np.argmax(jan1 >= 404)))
        mid = (first_day - timedelta(days=3) - date(year, 1, 1)).days  # the observed week's middle day
        observed_dd.append((loc[0], float(jan1_86[mid]), float(np.nanmax(out["first_catch_dd_estimate"]))))
        o = {"ours catch": offset(our_day, first_day), "newa catch": offset(newa_day, first_day)}
        o["ours five"], o["newa five"] = offset(our_day, five_day), offset(newa_day, five_day)
        for key, v in o.items():
            if v is not None:
                offs[key].append(v)

        def show(v):
            return "–" if v is None else f"{v:+d}" if v else "0"

        lines.append(
            f"| {year} | {name} | {first} | {our_day:%b %-d} | {show(o['ours catch'])} | {newa_day:%b %-d} | {show(o['newa catch'])} | {five} | {show(o['ours five'])} | {show(o['newa five'])} |"
        )
        print(lines[-1], flush=True)
    lines += ["", "## Summary", ""]
    labels = {
        "ours catch": "Ours against the first week with a catch",
        "newa catch": "NEWA's against the first week with a catch",
        "ours five": "Ours against the first week with 5 or more moths",
        "newa five": "NEWA's against the first week with 5 or more moths",
    }
    for key, v in offs.items():
        a = np.array(v)
        lines.append(
            f"- {labels[key]}: n = {len(a)}, inside the week {np.sum(a == 0)}, within a week of it {np.sum(np.abs(a) <= 7)}, median {np.median(a):+.0f} days (10th–90th percentile {np.percentile(a, 10):+.0f} to {np.percentile(a, 90):+.0f}), early {np.sum(a < 0)}, late {np.sum(a > 0)}"
        )
    d = np.array(observed_dd)
    fit = np.polyfit(d[:, 0], d[:, 1], 1)
    lines += [
        "",
        f"Degree days (50/86 °F, from January 1) at the middle of the first week with a catch: mean {d[:, 1].mean():.0f}, median {np.median(d[:, 1]):.0f}, SD {d[:, 1].std():.0f} (n = {len(d)}), against ours at the same sites mean {d[:, 2].mean():.0f}. A line by latitude: {fit[1]:.0f} {fit[0]:+.1f} × (lat) (Jones et al.'s slope near 44 °N: {-73.806 * 1.8 + 2 * 0.745 * 1.8 * 44:+.1f} DD°F per degree).",
    ]
    for lo_lat, hi_lat in ((42, 43.5), (43.5, 44.5), (44.5, 47)):
        band = d[(d[:, 0] >= lo_lat) & (d[:, 0] < hi_lat)]
        if len(band):
            lines.append(
                f"- {lo_lat}–{hi_lat} °N: observed mean {band[:, 1].mean():.0f} (n = {len(band)}), ours {band[:, 2].mean():.0f}"
            )
    lines += ["", "Left out: " + "; ".join(skipped) + "."]
    Path(args.out).write_text("\n".join(lines) + "\n")
    print("\n".join(lines[-6:]))


if __name__ == "__main__":
    main()
