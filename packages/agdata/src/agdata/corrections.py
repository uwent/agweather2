"""Every correction v2 applies to a source's weather, in one place: what it corrects, how, against what, where its
table lives and where the raw value is kept. `docs/corrections.md` is generated from it
(`uv run python -m agdata.corrections > docs/corrections.md`; a test checks it's current), and the methods pages
and the API will read it too (Phase 6), so the record follows the code.

A correction's version and fitted date come from its table, so refitting one updates the record. `title`, `summary`
and `scores` are public text, served by `/methods` (CLAUDE.md's "Writing for the public"); the other text fields are
notes for ourselves. A score is a held-out result copied from the evidence: a test checks its numbers are in that
document and that it was measured on the table's current version, so a refit fails until its scores are updated.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from agdata import calibration, climatestore, shortwave, soil_seam

DOCS = "docs"


@dataclass(kw_only=True, frozen=True)
class Score:
    """One held-out measure of a correction, before and after it (public text)."""

    measure: str
    unit: str  # `agdata.units` symbol; `index` for a ratio
    before: float
    after: float
    tested: str  # what it was tested on


@dataclass(kw_only=True, frozen=True)
class Correction:
    id: str
    title: str  # public
    summary: str  # public: what it corrects, how and why, in a few sentences
    variables: tuple[str, ...]  # the catalog variables whose values it changes
    source: str  # whose data, and where v2 uses it
    variable: str  # the catalog variable it changes
    method: str
    fitted_against: str
    applies_to: str
    raw_kept: str  # where the uncorrected value stays
    decision: str  # a D# in docs/decisions.md
    evidence: str  # the validation write-up
    table: Path | None = None
    version: str | None = None  # when there's no table
    fitted: str | None = None
    scores: tuple[Score, ...] = ()
    scored_version: str | None = None  # the version `scores` were measured on

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
    title="Solar radiation in the archive",
    summary="The HRRR model's solar radiation reads about 18% high against pyranometers on the ground. We correct each hour by a factor that depends on how clear the hour was (HRRR's radiation as a share of the radiation on a clear day), fitted against 80 Wisconet pyranometers in 2025 and tested on 2026. Reference evapotranspiration and daily totals are computed from the corrected values, and we keep HRRR's own values too.",
    variables=("shortwave_radiation",),
    scores=(
        Score(
            measure="Daily total, mean absolute error",
            unit="MJ_m2",
            before=2.80,
            after=1.66,
            tested="2026, at 80 Wisconet stations (fitted on 2025)",
        ),
        Score(
            measure="Daily total, ratio to the stations'",
            unit="index",
            before=1.175,
            after=0.987,
            tested="2026, at 80 Wisconet stations (fitted on 2025)",
        ),
    ),
    scored_version="2",
    source="HRRR (the archive)",
    variable="shortwave_radiation",
    method="Factor by the hour's clearness (HRRR over FAO-56 clear-sky Rso), linear between bins",
    fitted_against="80 Wisconet pyranometers, hourly (2025; tested on 2026)",
    applies_to="Every archive hour; ET0 and daily sums derive from the corrected value",
    raw_kept="`shortwave_radiation_hrrr` in the hourly store",
    decision="D48",
    evidence="docs/validation/weather/shortwave-correction.md",
    table=shortwave.TABLE_PATH,
)
NBM_SHORTWAVE = Correction(
    id="nbm-shortwave",
    title="Solar radiation in the forecast",
    summary="The National Blend of Models (NBM) forecasts too little solar radiation on days it expects to be very cloudy and too much on days it expects to be clear, more so the further ahead the day is, and about 11% too much overall. We correct each forecast hour by a factor that depends on how far ahead the day is and how clear NBM expects it to be, fitted against the archive's corrected radiation for 73 forecasts made in 2025.",
    variables=("shortwave_radiation",),
    scores=(
        Score(
            measure="Daily total, ratio to the archive's, days 1 to 10",
            unit="index",
            before=1.109,
            after=1.007,
            tested="2025, each forecast tested on a fit to the others",
        ),
        Score(
            measure="Daily total on day 1, mean absolute error",
            unit="MJ_m2",
            before=2.17,
            after=1.62,
            tested="2025, each forecast tested on a fit to the others",
        ),
    ),
    scored_version="2",
    source="NBM (the forecast, in the box)",
    variable="shortwave_radiation",
    method="Factor by lead group and the forecast day's clearness",
    fitted_against="The archive, 2025 backtest (73 13z runs, 2695 cells)",
    applies_to="Every forecast hour (`forecast.adjust_hours`)",
    raw_kept="Not stored (the backtest keeps its raw hours)",
    decision="D48",
    evidence="docs/validation/weather/forecast-shortwave.md",
    table=shortwave.NBM_TABLE_PATH,
)
NBM_MAX = Correction(
    id="nbm-max",
    title="Daily highs in the forecast",
    summary="NBM's hourly temperatures and its own forecast of the day's high don't always agree. We reshape each day's warm hours to reach NBM's forecast high, less a small seasonal offset (−0.4 to +0.6 °C) fitted against the archive's daily highs in 2025.",
    variables=("air_temperature",),
    scores=(
        Score(
            measure="Daily high on day 3, mean difference from the archive",
            unit="delta_degC",
            before=0.28,
            after=0.08,
            tested="2025, each forecast tested on a fit to the others",
        ),
    ),
    scored_version="1",
    source="NBM (the forecast, in the box)",
    variable="air_temperature",
    method="Each day's warm hours reshaped to NBM's 12-hour TMAX less a seasonal offset",
    fitted_against="The archive's daily max, 2025 backtest, lead days 1–3",
    applies_to="Every forecast day (`forecast.adjust_hours`)",
    raw_kept="Not stored",
    decision="D39, D49",
    evidence="docs/validation/weather/forecast-calibration.md",
    table=calibration.MAX_OFFSET_PATH,
)
NBM_NIGHT_MIN = Correction(
    id="nbm-night-min",
    title="Overnight lows in the forecast",
    summary="NBM's hourly temperatures run warm at night, by about 0.5 °C on the first night and up to 1.9 °C a week or more ahead. We lower each night's coldest hours (6 p.m. to 6 a.m. CST) by that warm bias for how far ahead the night is, fitted against the archive's daily lows in 2025.",
    variables=("air_temperature",),
    scores=(
        Score(
            measure="Daily low on day 1, mean difference from the archive",
            unit="delta_degC",
            before=0.45,
            after=0.09,
            tested="2025, each forecast tested on a fit to the others",
        ),
        Score(
            measure="Daily low on day 10, mean difference from the archive",
            unit="delta_degC",
            before=1.79,
            after=0.72,
            tested="2025, each forecast tested on a fit to the others",
        ),
    ),
    scored_version="1",
    source="NBM (the forecast, in the box)",
    variable="air_temperature",
    method="Each night's coldest hours (00–12Z) lowered by the warm bias for its lead",
    fitted_against="The archive's daily min, 2025 backtest",
    applies_to="Every forecast night (`forecast.adjust_hours`)",
    raw_kept="Not stored",
    decision="D39, D49",
    evidence="docs/validation/weather/forecast-calibration.md",
    table=calibration.NIGHT_MIN_PATH,
)
NBM_RH = Correction(
    id="nbm-rh",
    title="Humidity in the forecast",
    summary="NBM forecasts fewer humid hours than the archive records. We map each forecast hour's relative humidity onto the archive's, by season, hour of the day and how far ahead it is, and compute the dew point from it, keeping the temperature. Disease models that count humid hours read the result.",
    variables=("dew_point", "relative_humidity"),
    scores=(
        Score(
            measure="Hours a day with humidity at or above 80% on day 1, mean difference from the archive",
            unit="hour",
            before=-0.67,
            after=-0.24,
            tested="2025, each forecast tested on a fit to the others",
        ),
        Score(
            measure="The same on day 8",
            unit="hour",
            before=-1.39,
            after=-0.52,
            tested="2025, each forecast tested on a fit to the others",
        ),
    ),
    scored_version="1",
    source="NBM (the forecast, in the box)",
    variable="dew_point",
    method="Hourly RH quantile-mapped by season, lead and solar hour; dew point recomputed, temperature kept",
    fitted_against="The archive's hourly RH, 2025 backtest",
    applies_to="Every forecast hour (`forecast.adjust_hours`)",
    raw_kept="Not stored",
    decision="D49",
    evidence="docs/validation/weather/forecast-calibration.md",
    table=calibration.RH_MAP_PATH,
)
OPENMETEO_SHORTWAVE = Correction(
    id="openmeteo-shortwave",
    title="Solar radiation outside our area",
    summary="For locations outside the area our maps cover, and for dates before our archive, we read weather from Open-Meteo. Its solar radiation reads high against pyranometers, so we correct it the way we correct the archive's, by how clear each hour was, fitted against 80 Wisconet pyranometers. The fit is from Wisconsin, and we apply it everywhere until we can check it against stations elsewhere.",
    variables=("shortwave_radiation",),
    scores=(
        Score(
            measure="Daily total, ratio to the stations'",
            unit="index",
            before=1.136,
            after=0.987,
            tested="2026, at 80 Wisconet stations (fitted on 2025)",
        ),
        Score(
            measure="Daily total, mean absolute error",
            unit="MJ_m2",
            before=2.33,
            after=1.58,
            tested="2026, at 80 Wisconet stations (fitted on 2025)",
        ),
    ),
    scored_version="1",
    source="Open-Meteo `ncep_nbm_conus` then `best_match` (points outside the box, before the archive)",
    variable="shortwave_radiation",
    method="Factor by the hour's clearness, as for HRRR",
    fitted_against="80 Wisconet pyranometers, hourly (2025–2026; each year tested on the other)",
    applies_to="The historical-forecast and forecast endpoints, as hours are read from the cache; not ERA5 (the archive endpoint, unchecked). Fitted in Wisconsin, applied everywhere until other mesonets are compared (Phase 9)",
    raw_kept="`Hours.raw` (the cache keeps Open-Meteo's values)",
    decision="D51",
    evidence="docs/validation/weather/openmeteo.md",
    table=shortwave.OPENMETEO_TABLE_PATH,
)
OPENMETEO_RH = Correction(
    id="openmeteo-rh",
    title="Humidity outside our area",
    summary="Open-Meteo's humidity gives fewer humid hours than our archive and the stations. We map each hour's relative humidity onto the archive's, by season and hour of the day, and compute the dew point from it, keeping the temperature, so disease models outside our area read humidity like the archive's. It closes about half of the gap; Open-Meteo's humidity also changes from year to year. We apply it only in the Upper Midwest, where it was fitted: at five Oklahoma stations it made spring several times too humid, so farther south we use Open-Meteo's humidity as it comes.",
    variables=("dew_point", "relative_humidity"),
    scores=(
        Score(
            measure="Hours a day with humidity at or above 90%, May to September (stations: 7.54)",
            unit="hour",
            before=4.73,
            after=5.71,
            tested="2026, at 80 Wisconet stations (fitted on 2025)",
        ),
    ),
    scored_version="1",
    source="Open-Meteo `ncep_nbm_conus` then `best_match` (points outside the box, before the archive)",
    variable="dew_point",
    method="Hourly RH quantile-mapped by season and solar hour; dew point recomputed, temperature kept",
    fitted_against="The archive's hourly RH at 80 Wisconet stations' cells (2025–2026)",
    applies_to="The historical-forecast and forecast endpoints, at points in the Upper Midwest only (Wisconsin, Minnesota, Michigan, Iowa and northern Illinois, latitude 40–49.5° N and longitude 97.5–82° W; D100): in Oklahoma the map made spring several times too humid, so elsewhere humidity stays Open-Meteo's",
    raw_kept="`Hours.raw` (the cache keeps Open-Meteo's values)",
    decision="D51",
    evidence="docs/validation/weather/openmeteo.md",
    table=calibration.OPENMETEO_RH_MAP_PATH,
)
GRIDDED_RH_90 = Correction(
    id="gridded-rh-90",
    title="Humid hours for disease models",
    summary="Several disease models count hours with relative humidity at or above 90%, as measured at a field weather station. Gridded humidity is an average over a 2.5 km cell, so it reaches 90% less often than a station does. We count those hours at 88% instead, the threshold at which the archive has as many humid hours as 80 Wisconet stations and as many as their leaf wetness sensors, May to September 2025 and 2026. Open-Meteo's humidity, which we use outside our area, matched five Oklahoma Mesonet stations' hours at 90% at about the same threshold, 88%, from March to August 2023 to 2025, so pecan scab's hours are counted the same way.",
    variables=(
        "hours_rh_over_90",
        "hours_rh_over_90_temperature_over_70f",
        "hours_rh_over_90_from_6pm",
        "hours_rh_over_90_night",
        "hours_rh_over_90_7pm_to_6am",
        "temperature_mean_rh_over_90_from_6pm",
    ),
    source="Any hourly RH (the archive, the forecast, Open-Meteo)",
    variable="hours_rh_over_90 and the other RH ≥ 90% features",
    method="Counted at RH ≥ 88% (`agmodels.features.STATION_RH_90_AS_GRIDDED`); pecan scab's too since D100",
    fitted_against="80 Wisconet stations' RH ≥ 90% hours and leaf-wet hours, May–September 2025–2026; for pecan scab, five Oklahoma Mesonet stations' RH ≥ 90% hours on raw Open-Meteo, March–August 2023–2025 (matched at 87.5–88.2%)",
    applies_to="The seven disease models whose 90% comes from field stations",
    raw_kept="The hourly RH itself is unchanged",
    decision="D50",
    evidence="docs/validation/weather/humidity.md",
    version="3",
    fitted="2026-10-31",
)
IFS_SOIL_SEAM = Correction(
    id="ifs-soil-seam",
    title="Soil temperature on the newest days and in the forecast",
    summary="Our soil temperatures come from ERA5-Land, which arrives about five days late. ECMWF's forecast model (IFS) fills the days since and the forecast. The two differ, so we shift each cell's IFS values by the difference between them at ERA5-Land's last hour, by less and less the further ahead the hour is. ERA5-Land replaces these values when it arrives.",
    variables=("soil_temperature_4cm", "soil_temperature_10cm", "soil_temperature_30cm"),
    scores=(
        Score(
            measure="Soil at 4 cm, 3 days ahead, root mean square difference from ERA5-Land",
            unit="delta_degC",
            before=2.34,
            after=1.69,
            tested="2026 (fitted on 2025), at 80 Wisconet stations' cells",
        ),
        Score(
            measure="Soil at 10 cm, 3 days ahead, root mean square difference from ERA5-Land",
            unit="delta_degC",
            before=2.18,
            after=1.39,
            tested="2026 (fitted on 2025), at 80 Wisconet stations' cells",
        ),
    ),
    scored_version="1",
    source="ECMWF IFS (the archive's provisional hours and the forecast, in the box)",
    variable="soil_temperature_4cm, soil_temperature_10cm, soil_temperature_30cm",
    method="Each cell shifted by ERA5-Land − IFS in ERA5-Land's last hour, times a weight by lead (1 at the seam, fading to a lasting share)",
    fitted_against="The archive (ERA5-Land) minus Open-Meteo's IFS at 80 Wisconet stations' cells (2025; tested on 2026)",
    applies_to="IFS's hours after ERA5-Land's last (`ops.ifs`); replaced by ERA5-Land's as it arrives. Not points outside the box, whose recent days and forecast are all IFS",
    raw_kept="Each cell's offset in `ifs/latest.zarr` (raw = value − offset × weight)",
    decision="Q23",
    evidence="docs/validation/weather/soil.md",
    table=soil_seam.TABLE_PATH,
)
GRIDMET_BASIS = Correction(
    id="gridmet-basis",
    title="The earlier years of the 30-year normal",
    summary="Our archive begins in 2016, so the 30-year normal takes its earlier years from gridMET, a gridded daily weather dataset (Abatzoglou, 2013). The two differ: gridMET's daily highs, for one, run about 0.7 °F warmer than the archive's over the years both cover. We adjust gridMET to the archive cell by cell and day of the year, by the difference (temperature, humidity) or the ratio (precipitation, solar radiation, wind, evapotranspiration) between them, so the normal's years are on one basis. We leave out gridMET's daily highs and evapotranspiration for 2011–2013, which run 3–6 °F warm in summer against every station we checked.",
    variables=tuple(climatestore.ADJUST),
    source="gridMET (the 30-year normal's years before the archive)",
    variable=", ".join(climatestore.ADJUST),
    method=f"By cell and calendar day: the archive − gridMET difference added (temperatures, RH; RH kept to 0–100, the minimum no higher than the maximum) or the ratio of their totals applied (precipitation, shortwave, wind, ET0; 0.5 to 2), each pooled over {climatestore.POOL_DAYS} days and averaged across {climatestore.SMOOTH} × {climatestore.SMOOTH} cells. The maximum and ET0 of 2011–2013 are left out as missing (3–6 °F warm in summer against every station checked)",
    fitted_against="The archive's daily values over the years both have (2016–2025 at first), cell by cell",
    applies_to="gridMET's years in the 30-year normal (`agdata.climatestore`); refitted by `manage.py climatology`",
    raw_kept="gridMET's files as received in `data/gridmet/` (the fit in `data/climate/gridmet-fit.zarr`)",
    decision="D84, Q38",
    evidence="docs/validation/weather/climate.md, docs/validation/weather/wind.md, docs/validation/weather/normals.md",
    version=str(climatestore.FIT_VERSION),
    fitted="each `manage.py climatology` fit (its `fitted` attribute)",
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
    GRIDMET_BASIS,
)


BY_ID: dict[str, Correction] = {c.id: c for c in CORRECTIONS}


def touching(variable: str) -> list[str]:
    """The ids of the corrections that change `variable`'s values."""
    return [c.id for c in CORRECTIONS if variable in c.variables]


def markdown() -> str:
    rows = [
        "# Corrections to source data",
        "",
        "Generated from `agdata.corrections` (`uv run python -m agdata.corrections > docs/corrections.md`); a test checks it's current. Each table's version and fitted date come from its file.",
        "",
        "| Correction | Source | Variable | Method | Fitted against | Applies to | Raw kept | Version | Fitted | Decision | Evidence |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for c in CORRECTIONS:
        table = f" (`{c.table.relative_to(c.table.parents[2])}`)" if c.table is not None else ""
        rows.append(
            f"| `{c.id}`{table} | {c.source} | `{c.variable}` | {c.method} | {c.fitted_against} | {c.applies_to} | {c.raw_kept} | {c.current_version} | {c.fitted_on} | {c.decision} | [{Path(c.evidence).name}]({Path(c.evidence).relative_to('docs')}) |"
        )
    return "\n".join(rows) + "\n"


if __name__ == "__main__":
    print(markdown(), end="")
