"""The 30-year climatology's gridMET years (D82, D84; PLAN.md Phase 6 D3): what `manage.py climatology` and the
January job do.

`plan` says what the trailing 30 complete years need: gridMET's files for the years the archive lacks (the normal's
own) and for the years both have (the fit's overlap); a fit when there's none, it's from other years, or it's asked
for; the normal's gridMET years derived where they're missing or out of date; each period's normal maps
(`agdata.normals`, D85) where its years or their data changed; and kept files and derived years no longer needed,
dropped. `run` downloads outside the write lock, then takes it (politely) to fit and to write each year. The normal
maps read only the years' copies and swap their own store into place, as the past-years copies do, so they build
without the lock.
"""

from collections.abc import Callable, Iterable
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from agdata import climatestore, normals
from agdata.climatology import PERIODS
from agdata.grid import Window
from agdata.progress import Reporter
from agdata.series import archive_years
from agdata.sources import gridmet

Lock = Callable[[], AbstractContextManager[None]]


@dataclass(kw_only=True)
class Plan:
    period: tuple[int, ...]  # the trailing 30 complete years
    normal: list[int]  # those the archive lacks, from gridMET
    overlap: list[int]  # those both have, for the fit
    fetch: list[tuple[str, int]] = field(default_factory=list)  # (gridMET variable, year)
    refit: str | None = None  # why, or None
    derive: dict[int, str] = field(default_factory=dict)  # year → why
    drop_files: list[Path] = field(default_factory=list)
    drop_years: list[int] = field(default_factory=list)
    normals: dict[str, str] = field(default_factory=dict)  # period → why its normal maps need building
    archive: set[int] = field(default_factory=set)  # the archive's complete years

    @property
    def nothing(self) -> bool:
        return not (self.fetch or self.refit or self.derive or self.drop_files or self.drop_years or self.normals)


def plan(data_dir: Path, today: date, window: Window, refit: bool = False, rederive: bool = False) -> Plan:
    period = tuple(range(today.year - PERIODS["last30"], today.year))
    archive = {y for y in archive_years(data_dir) if y < today.year}
    normal = [y for y in period if y not in archive and y >= gridmet.FIRST_YEAR]
    overlap = [y for y in period if y in archive]
    wanted = set(normal) | set(overlap)
    kept = climatestore.kept_years(data_dir)
    fetch = [(s.name, y) for y in sorted(wanted) for s in gridmet.SOURCES if s.name not in kept.get(y, [])]
    found = Plan(period=period, normal=normal, overlap=overlap, fetch=fetch)
    fitted = climatestore.fit_attrs(data_dir)
    if refit:
        found.refit = "asked for"
    elif overlap and fitted is None:
        found.refit = "none yet"
    elif fitted is not None and (fitted.get("years") != overlap or fitted.get("version") != climatestore.FIT_VERSION):
        found.refit = "the overlap's years changed" if fitted.get("years") != overlap else "the fit's code changed"
    elif fitted is not None and fitted.get("names") != sorted(climatestore.ADJUST):
        found.refit = "the variables adjusted changed"
    elif fitted is not None and fitted.get("window") != climatestore._window_attrs(window):
        found.refit = "the service box changed"
    elif any(y in overlap for _, y in fetch):
        found.refit = "new gridMET files for the overlap"
    for year in normal:
        reason = "asked for" if rederive else climatestore.status(data_dir, year)
        if found.refit or any(y == year for _, y in fetch):
            reason = reason or "its inputs change in this run"
        if reason is not None:
            found.derive[year] = reason
    for source in gridmet.SOURCES:
        folder = Path(data_dir) / gridmet.KIND / source.name
        for file in sorted(folder.glob("*.nc")) if folder.exists() else ():
            if file.stem.isdigit() and int(file.stem) not in wanted:
                found.drop_files.append(file)
    found.drop_years = [y for y in climatestore.years(data_dir) if y not in normal]
    found.archive = archive
    for name in PERIODS:
        years = period_years(found, name)
        if not years:
            continue
        reason = normals.status(data_dir, name, years, archive)
        if name == "last30" and (found.derive or found.fetch) and reason is None:
            reason = "its gridMET years change in this run"
        if reason is not None:
            found.normals[name] = reason
    return found


def period_years(p: Plan, name: str) -> list[int]:
    """A period's years: the trailing ones the archive has, and for `last30` gridMET's before them."""
    asked = p.period[-PERIODS[name] :]
    return [y for y in asked if y in p.archive or (name == "last30" and y in p.normal)]


def describe(p: Plan) -> list[str]:
    lines = [
        f"30-year period {p.period[0]}–{p.period[-1]}: {_years(p.normal)} from gridMET, "
        f"{_years(p.overlap)} from the archive (and the fit's overlap)"
    ]
    if p.fetch:
        years = sorted({y for _, y in p.fetch})
        lines.append(f"fetch {len(p.fetch)} gridMET files ({_years(years)})")
    if p.refit:
        lines.append(f"fit again: {p.refit}")
    if p.derive:
        reasons = sorted(set(p.derive.values()))
        lines.append(f"derive {len(p.derive)} years ({_years(list(p.derive))}): {'; '.join(reasons)}")
    for name, reason in p.normals.items():
        lines.append(f"build {name}'s normal maps: {reason}")
    if p.drop_files or p.drop_years:
        lines.append(f"drop {len(p.drop_files)} files and {len(p.drop_years)} derived years no longer in the period")
    if p.nothing:
        lines.append("everything is current")
    return lines


def _years(years: Iterable[int]) -> str:
    years = sorted(years)
    if not years:
        return "none"
    runs, start = [], years[0]
    for a, b in zip(years, [*years[1:], None], strict=True):
        if b != a + 1:
            runs.append(f"{start}–{a}" if a != start else str(a))
            start = b
    return ", ".join(runs)


def run(
    data_dir: Path,
    window: Window,
    p: Plan,
    report: Reporter,
    lock: Lock,
    stopping: Callable[[], bool] = lambda: False,
) -> int:
    """Carries out a plan; returns the years derived. Failures are reported and skipped (a rerun retries them)."""
    extent = gridmet.extent(window)
    for k, (name, year) in enumerate(p.fetch):
        if stopping():
            return 0
        report.progress("gridMET files", k, len(p.fetch))
        report.detail(f"{name} {year} ==> GET {gridmet.url(name, year)} (the box's chunks)")
        try:
            size, seconds = gridmet.fetch_with_retries(name, year, gridmet.path(data_dir, name, year), extent)
        except (OSError, TimeoutError, ValueError) as error:
            report.fail(f"gridMET {name} {year}", error)
            continue
        report.detail(f"{name} {year}: {size / 1e6:.1f} MB in {seconds:.0f} s")
    if p.fetch:
        report.progress("gridMET files", len(p.fetch), len(p.fetch))
    kept = climatestore.kept_years(data_dir)
    if p.refit and not stopping():
        missing = [y for y in p.overlap if len(kept.get(y, [])) < len(gridmet.SOURCES)]
        if missing:
            report.fail("fit", f"gridMET files missing for {_years(missing)}; rerun once they're fetched")
        else:
            with lock():
                climatestore.fit(
                    data_dir, window, p.overlap, report=report.step, progress=lambda n, d, t: report.progress(n, d, t)
                )
            report.step("fit written")
    derived = 0
    for year in p.derive:
        if stopping():
            break
        if len(kept.get(year, [])) < len(gridmet.SOURCES):
            report.fail(f"derive {year}", "some of its gridMET files are missing; rerun once they're fetched")
            continue
        with lock():
            names = climatestore.derive(
                data_dir, year, window, progress=lambda d, t, y=year: report.progress(str(y), d, t)
            )
        derived += 1
        report.detail(f"{year}: {len(names)} variables")
    if not stopping():
        for file in p.drop_files:
            file.unlink(missing_ok=True)
            report.detail(f"dropped {file}")
        for year in p.drop_years:
            with lock():
                climatestore.drop(data_dir, year)
            report.detail(f"dropped the derived {year}")
    for name in p.normals:
        if stopping() or report.failures:
            break  # a failed fetch or derive would leave the maps built on missing years
        years = period_years(p, name)
        try:
            normals.build(
                data_dir, name, years, p.archive, window, progress=lambda d, t, n=name: report.progress(n, d, t)
            )
        except ValueError as error:
            report.fail(f"{name}'s normal maps", error)
            continue
        report.step(f"{name}'s normal maps built ({_years(years)})")
    return derived
