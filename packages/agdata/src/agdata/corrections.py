"""Every correction v2 applies to a source's weather, in one place: what it corrects, how, against what, where its
table lives and where the raw value is kept. `docs/corrections.md` is generated from it
(`uv run python -m agdata.corrections > docs/corrections.md`; a test checks it's current), and the methods pages
and the API will read it too (PLAN.md Phase 6), so the record follows the code.

A correction's version and fitted date come from its table, so refitting one updates the record.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from agdata import calibration, shortwave, soil_seam

DOCS = "docs"


@dataclass(kw_only=True, frozen=True)
class Correction:
    id: str
    source: str  # whose data, and where v2 uses it
    variable: str  # the catalog variable it changes
    method: str
    fitted_against: str
    applies_to: str
    raw_kept: str  # where the uncorrected value stays
    decision: str  # PLAN.md
    evidence: str  # the validation write-up
    table: Path | None = None
    version: str | None = None  # when there's no table
    fitted: str | None = None

    def _table(self) -> dict:
        return json.loads(self.table.read_text()) if self.table is not None and self.table.exists() else {}

    @property
    def current_version(self) -> str:
        return str(self._table().get("version", self.version or ""))

    @property
    def fitted_on(self) -> str:
        return str(self._table().get("fitted", self.fitted or ""))

    @property
    def label(self) -> str:
        """`id v<version>`, as a corrected series lists it."""
        return f"{self.id} v{self.current_version}"


HRRR_SHORTWAVE = Correction(
    id="hrrr-shortwave",
    source="HRRR (the archive)",
    variable="shortwave_radiation",
    method="Factor by the hour's clearness (HRRR over FAO-56 clear-sky Rso), linear between bins",
    fitted_against="80 Wisconet pyranometers, hourly (2025; tested on 2026)",
    applies_to="Every archive hour; ET0 and daily sums derive from the corrected value",
    raw_kept="`shortwave_radiation_hrrr` in the hourly store",
    decision="D48",
    evidence="docs/validation-shortwave-correction.md",
    table=shortwave.TABLE_PATH,
)
NBM_SHORTWAVE = Correction(
    id="nbm-shortwave",
    source="NBM (the forecast, in the box)",
    variable="shortwave_radiation",
    method="Factor by lead group and the forecast day's clearness",
    fitted_against="The archive, 2025 backtest (73 13z runs, 2695 cells)",
    applies_to="Every forecast hour (`forecast.adjust_hours`)",
    raw_kept="Not stored (the backtest keeps its raw hours)",
    decision="D48",
    evidence="docs/validation-forecast-shortwave.md",
    table=shortwave.NBM_TABLE_PATH,
)
NBM_MAX = Correction(
    id="nbm-max",
    source="NBM (the forecast, in the box)",
    variable="air_temperature",
    method="Each day's warm hours reshaped to NBM's 12-hour TMAX less a seasonal offset",
    fitted_against="The archive's daily max, 2025 backtest, lead days 1–3",
    applies_to="Every forecast day (`forecast.adjust_hours`)",
    raw_kept="Not stored",
    decision="D39, D49",
    evidence="docs/validation-forecast-calibration.md",
    table=calibration.MAX_OFFSET_PATH,
)
NBM_NIGHT_MIN = Correction(
    id="nbm-night-min",
    source="NBM (the forecast, in the box)",
    variable="air_temperature",
    method="Each night's coldest hours (00–12Z) lowered by the warm bias for its lead",
    fitted_against="The archive's daily min, 2025 backtest",
    applies_to="Every forecast night (`forecast.adjust_hours`)",
    raw_kept="Not stored",
    decision="D39, D49",
    evidence="docs/validation-forecast-calibration.md",
    table=calibration.NIGHT_MIN_PATH,
)
NBM_RH = Correction(
    id="nbm-rh",
    source="NBM (the forecast, in the box)",
    variable="dew_point",
    method="Hourly RH quantile-mapped by season, lead and solar hour; dew point recomputed, temperature kept",
    fitted_against="The archive's hourly RH, 2025 backtest",
    applies_to="Every forecast hour (`forecast.adjust_hours`)",
    raw_kept="Not stored",
    decision="D49",
    evidence="docs/validation-forecast-calibration.md",
    table=calibration.RH_MAP_PATH,
)
OPENMETEO_SHORTWAVE = Correction(
    id="openmeteo-shortwave",
    source="Open-Meteo `ncep_nbm_conus` then `best_match` (points outside the box, before the archive)",
    variable="shortwave_radiation",
    method="Factor by the hour's clearness, as for HRRR",
    fitted_against="80 Wisconet pyranometers, hourly (2025–2026; each year tested on the other)",
    applies_to="The historical-forecast and forecast endpoints, as hours are read from the cache; not ERA5 "
    "(the archive endpoint, unchecked). Fitted in Wisconsin, applied everywhere until other mesonets are compared "
    "(Phase 9)",
    raw_kept="`Hours.raw` (the cache keeps Open-Meteo's values)",
    decision="D51",
    evidence="docs/validation-openmeteo.md",
    table=shortwave.OPENMETEO_TABLE_PATH,
)
OPENMETEO_RH = Correction(
    id="openmeteo-rh",
    source="Open-Meteo `ncep_nbm_conus` then `best_match` (points outside the box, before the archive)",
    variable="dew_point",
    method="Hourly RH quantile-mapped by season and solar hour; dew point recomputed, temperature kept",
    fitted_against="The archive's hourly RH at 80 Wisconet stations' cells (2025–2026)",
    applies_to="As for Open-Meteo's shortwave",
    raw_kept="`Hours.raw` (the cache keeps Open-Meteo's values)",
    decision="D51",
    evidence="docs/validation-openmeteo.md",
    table=calibration.OPENMETEO_RH_MAP_PATH,
)
GRIDDED_RH_90 = Correction(
    id="gridded-rh-90",
    source="Any hourly RH (the archive, the forecast, Open-Meteo)",
    variable="hours_rh_over_90 and the other RH ≥ 90% features",
    method="Counted at RH ≥ 88% (`agmodels.features.STATION_RH_90_AS_GRIDDED`); not pecan scab's",
    fitted_against="80 Wisconet stations' RH ≥ 90% hours and leaf-wet hours, May–September 2025–2026",
    applies_to="The six disease models whose 90% comes from field stations",
    raw_kept="The hourly RH itself is unchanged",
    decision="D50",
    evidence="docs/validation-humidity.md",
    version="2",
    fitted="2026-10-31",
)
IFS_SOIL_SEAM = Correction(
    id="ifs-soil-seam",
    source="ECMWF IFS (the archive's provisional hours and the forecast, in the box)",
    variable="soil_temperature_4cm, soil_temperature_10cm, soil_temperature_30cm",
    method="Each cell shifted by ERA5-Land − IFS in ERA5-Land's last hour, times a weight by lead (1 at the seam, "
    "fading to a lasting share)",
    fitted_against="The archive (ERA5-Land) minus Open-Meteo's IFS at 80 Wisconet stations' cells (2025; tested on "
    "2026)",
    applies_to="IFS's hours after ERA5-Land's last (`ops.ifs`); replaced by ERA5-Land's as it arrives. Not points "
    "outside the box, whose recent days and forecast are all IFS",
    raw_kept="Each cell's offset in `ifs/latest.zarr` (raw = value − offset × weight)",
    decision="Q23",
    evidence="docs/validation-soil.md",
    table=soil_seam.TABLE_PATH,
)
CORRECTIONS: tuple[Correction, ...] = (
    HRRR_SHORTWAVE,
    NBM_SHORTWAVE,
    NBM_MAX,
    NBM_NIGHT_MIN,
    NBM_RH,
    IFS_SOIL_SEAM,
    OPENMETEO_SHORTWAVE,
    OPENMETEO_RH,
    GRIDDED_RH_90,
)


def markdown() -> str:
    rows = [
        "# Corrections to source data",
        "",
        "Generated from `agdata.corrections` (`uv run python -m agdata.corrections > docs/corrections.md`); a test "
        "checks it's current. Each table's version and fitted date come from its file.",
        "",
        "| Correction | Source | Variable | Method | Fitted against | Applies to | Raw kept | Version | Fitted "
        "| Decision | Evidence |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for c in CORRECTIONS:
        table = f" (`{c.table.relative_to(c.table.parents[2])}`)" if c.table is not None else ""
        rows.append(
            f"| `{c.id}`{table} | {c.source} | `{c.variable}` | {c.method} | {c.fitted_against} | {c.applies_to} "
            f"| {c.raw_kept} | {c.current_version} | {c.fitted_on} | {c.decision} | [{Path(c.evidence).name}]"
            f"({Path(c.evidence).name}) |"
        )
    return "\n".join(rows) + "\n"


if __name__ == "__main__":
    print(markdown(), end="")
