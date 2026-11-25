"""Apple scab (Venturia inaequalis): primary infection periods and ascospore maturity, from green tip until the
season's ascospores are released. NEWA's model (Cornell; D95), with the published curves where NEWA approximates them.

- **Green tip** starts the season: `apple-stages`' green tip (101 degree days base 43 °F from January 1), or the
  grower's date.
- **Ascospore maturity:** Gadoury and MacHardy (1982), probit of the percent mature = 2.51 + 0.01 × degree days
  (base 0 °C, daily mean) from green tip (Stensvand et al. 2005's start; the 1982 paper counted from the first mature
  ascospores). A day's degree days count unless it ends 8 dry days in a row (under 0.2 mm each): accumulation
  stops after 7 days without rain and resumes with the next rain (Stensvand et al. 2005; their dew-or-fog clause is
  left out, as NEWA leaves it out). NEWA uses a logistic stand-in for the probit (within 2.3 points), starts a day
  before green tip, and doesn't count the rain day that ends a dry spell.
- **Ascospores released:** NEWA's daily estimate: rain in the night (8 pm to 6 am) releases 5 % of the mature
  ascospores not yet released, then rain in the day (7 am to 7 pm) 90 % if it's at least 0.1 in and its rainy
  hours average at least 50 °F, 50 % if one holds, 25 % if neither. An hour is rainy at 0.01 in or more (NEWA: any).
- **The primary season ends** the day ascospores are 95 % mature and more than 2.5 mm (0.1 in) of rain falls in the
  day with its rainy hours above 10 °C (50 °F): the rest are released (Stensvand et al. 2005; NEWA's rule). As a
  backstop it ends at 1,300 degree days (base 0 °C, unadjusted) after green tip, the latest 95 % release Stensvand et
  al. trapped in 16 site-years, so a cell with a dry or failed gauge doesn't stay open all summer.
- **Infection periods** by NEWA's rules on hours estimated wet (`infection_periods`): a wet period starts at an hour
  with rain, continues while hours stay wet (RH ≥ 90 % or rain, the estimate that agreed best with Wisconsin's leaf
  wetness sensors, models plan B5) or rainy, and periods less than 24 hours apart join (their wet hours added, the gap
  not counted). An infection occurs when a period's wet hours reach the Revised Mills table at its mean temperature
  (MacHardy and Gadoury 1989, as NEWA tabulates it in °F, 34–79 °F; one level, no light, moderate or heavy). The
  infection is put on the day the hours reach the table, where NEWA marks the day the wet period ends. The daily
  rollup runs the rules over the 120 hours to each day's end (`agmodels.features.scab_features`).
- **Risk:** during the primary season, Infection on a day an infection period's hours reach the table, Low otherwise;
  none before green tip or after the season (secondary infections by conidia aren't modelled).

Not modelled: MacHardy and Gadoury's 7 am rule for rain that starts at night (NEWA doesn't apply it to events),
Stensvand et al. (1997)'s rows below 34 °F, light, moderate and heavy infection, and MSU's seasonal discharge curve
(no source found).
"""

from collections.abc import Mapping

import numpy as np

from agmodels.normal import normal_cdf
from agmodels.spec import Biofix, Change, Check, Citation, ExplorerInput, Input, ModelSpec, Quantity, Risk

# NEWA's Revised Mills table: the period's mean temperature (°F, rounded) → wet hours an infection needs. MacHardy and
# Gadoury (1989)'s Mills/a − 3 curve as NEWA tabulates it (newa.cornell.edu, apple scab, 2026).
MILLS_F: dict[int, int] = (
    {34: 41, 35: 41, 36: 35, 37: 30, 38: 30, 39: 28, 40: 28, 41: 21, 42: 21, 43: 18, 44: 18, 45: 15, 46: 13, 47: 13}
    | {48: 12, 49: 12, 50: 11, 51: 11, 52: 9, 53: 9, 54: 8, 55: 8, 56: 8, 57: 7, 58: 7, 59: 7, 60: 7}
    | dict.fromkeys(range(61, 77), 6)
    | {77: 8, 78: 8, 79: 11}
)
_HOURS_NEEDED = np.array([MILLS_F.get(t, np.inf) for t in range(0, 120)], dtype=float)  # by °F, inf outside 34–79

WET_RH = 90.0  # % (models plan B5: on the archive's RH, with rain, the best match to orchard sensors)
RAIN_MM = 0.254  # 0.01 in: a rainy hour
JOIN_HOURS = 24  # periods closer than this join
WINDOW_HOURS = 120  # the hours each day's periods are found in: the day and the four before it

DRY_DAY_MM = 0.2  # Stensvand et al. 2005
DRY_DAYS = 7  # accumulation stops after this many dry days in a row
PROBIT_A, PROBIT_B = 2.51, 0.01  # Gadoury and MacHardy 1982
MATURE = 95.0  # % mature before the rest are released by a warm day rain
SEASON_RAIN_MM = 2.5
SEASON_RAIN_C = 10.0
BACKSTOP_DD_C = 1300.0
NIGHT_RELEASE = 0.05
DAY_RAIN_MM = 2.54  # 0.1 in
DAY_RAIN_C = 10.0  # 50 °F

SPEC = ModelSpec(
    id="apple-scab",
    name="Apple scab",
    group="disease",
    version="0.1",
    status="beta",
    summary="Primary apple scab infection periods from wet hours and temperature, with the share of the season's ascospores mature and released, from green tip until they're released.",
    topics=("apple-scab",),
    crops=("apple",),
    checks=(
        Check(
            kind="published",
            against="The ascospore maturity curve (Gadoury and MacHardy 1982; Stensvand et al. 2005) and the Revised Mills table (MacHardy and Gadoury 1989, as NEWA tabulates it)",
            result="Estimated ascospore maturity follows the published curve (Gadoury and MacHardy 1982): half the season's spores are mature by 250 degree days (base 0 °C) and 95 percent by 420. The wet hours needed for infection follow NEWA's Revised Mills table, such as 8 hours at 55 °F.",
            report="docs/validation/models/apple-scab.md#against-its-sources-numbers",
        ),
        Check(
            kind="system",
            against="NEWA's apple scab model on the weather of 63 Wisconsin orchard station-seasons, 2024 and 2025",
            result="On the stations' own weather, our model found 669 of NEWA's 786 infection periods (85 percent), and 648 (82 percent) on our map's weather at the same places. We checked first that we reproduce NEWA's own results exactly from its published rules.",
            report="docs/validation/models/apple-scab.md#against-newa-on-the-same-weather",
        ),
        Check(
            kind="observations",
            against="Leaf wetness sensors at NEWA's Wisconsin orchard stations, 2024–2026",
            result="From April through June, wetness estimated from our map's weather gave 560 of the 750 infection events the sensors gave, and 299 the sensors didn't. So the model tends to show more infection periods than a sensor in the orchard would.",
            report="docs/validation/models/apple-scab.md#the-wetness-estimate-against-orchard-sensors",
        ),
    ),
    citations=(
        Citation(
            text="Gadoury, D. M. and MacHardy, W. E. (1982). A model to estimate the maturity of ascospores of Venturia inaequalis. Phytopathology 72, 901–904.",
            doi="10.1094/Phyto-72-901",
        ),
        Citation(
            text="MacHardy, W. E. and Gadoury, D. M. (1989). A revision of Mills's criteria for predicting apple scab infection periods. Phytopathology 79, 304–310.",
            doi="10.1094/Phyto-79-304",
        ),
        Citation(
            text="Stensvand, A., Eikemo, H., Gadoury, D. M. and Seem, R. C. (2005). Use of a rainfall frequency threshold to adjust a degree-day model of ascospore maturity of Venturia inaequalis. Plant Disease 89, 198–202.",
            doi="10.1094/PD-89-0198",
        ),
        Citation(
            text="Gadoury, D. M., Seem, R. C., MacHardy, W. E., Wilcox, W. F., Rosenberger, D. A. and Stensvand, A. (2004). A comparison of methods used to estimate the maturity and release of ascospores of Venturia inaequalis. Plant Disease 88, 869–874.",
            doi="10.1094/PDIS.2004.88.8.869",
        ),
        Citation(
            text="NEWA, Network for Environment and Weather Applications, Cornell University: apple scab model (infection events, Revised Mills table, ascospore release).",
            url="https://newa.cornell.edu/apple-scab",
        ),
        Citation(
            text="Enviroweather, Michigan State University: apple scab model.",
            url="https://enviroweather.msu.edu/crops/apple/applescab",
        ),
    ),
    inputs=(
        Input(name="air_temperature_min", label="Minimum temperature", unit="degC"),
        Input(name="air_temperature_max", label="Maximum temperature", unit="degC"),
        Input(name="precipitation_sum", label="Precipitation", unit="mm"),
        Input(name="precipitation_7am_to_7pm", label="Precipitation, 7 am to 7 pm", unit="mm"),
        Input(name="precipitation_8pm_to_6am", label="Precipitation, 8 pm to 6 am", unit="mm"),
        Input(
            name="temperature_mean_rain_7am_to_7pm", label="Mean temperature of rainy hours, 7 am to 7 pm", unit="degC"
        ),
        Input(name="scab_infection", label="Apple scab infection period", unit="index"),
        Input(name="scab_wet_hours", label="Wet hours of the period", unit="hour"),
        Input(name="scab_wet_temperature", label="Mean temperature of the period", unit="degC"),
    ),
    outputs=(
        Quantity(
            name="infection",
            label="Infection period",
            unit="index",
            description="1 on a day an infection period's wet hours reach the Revised Mills table",
        ),
        Quantity(name="maturity", label="Ascospores mature", unit="percent"),
        Quantity(
            name="released",
            label="Ascospores released",
            unit="percent",
            description="Share of the season's ascospores, estimated",
        ),
        Quantity(name="released_today", label="Ascospores released today", unit="percent"),
        Quantity(name="wet_hours", label="Wet hours of the period", unit="hour"),
        Quantity(name="wet_temperature", label="Mean temperature of the period", unit="degC"),
        Quantity(name="dd_total", label="Degree days since green tip (base 0 °C, rain-adjusted)", unit="degC_day"),
        Quantity(
            name="season",
            label="Primary season",
            unit="index",
            description="0 during the primary season, 1 once it's over",
        ),
    ),
    risk=Risk(
        levels=("Low", "Infection"),
        criteria="During the primary season (green tip until the ascospores are released), Infection on a day a wet period's hours reach the Revised Mills table at its mean temperature, Low otherwise.",
    ),
    explorer=(
        ExplorerInput(name="wet_hours", label="Wet hours", unit="hour", minimum=0, maximum=48, step=1, default=10),
        ExplorerInput(
            name="temperature",
            label="Mean temperature of the wet period",
            unit="degF",
            minimum=32,
            maximum=82,
            step=1,
            default=55,
        ),
    ),
    explorer_outputs=(
        Quantity(name="risk", label="Risk level", unit="index", description="Index into the risk levels"),
    ),
    sweep={
        "wet_hours": tuple(float(h) for h in range(0, 49, 2)),
        "temperature": tuple(float(t) for t in range(32, 83, 2)),
    },
    lookback_days=DRY_DAYS,
    season=("03-01", "07-31"),
    biofix=Biofix(default="04-15", label="Green tip (50% of McIntosh buds showing green)"),
    biofix_stage=("apple-stages", "GT"),
    changelog=(Change(version="0.1", date="2026-11-18", note="First version."),),
)


def hours_needed(temperature_f) -> np.ndarray:
    """The Revised Mills table's wet hours at a mean temperature (°F, rounded half up as NEWA does); inf outside 34–79 °F."""
    t = np.floor(np.asarray(temperature_f, dtype=float) + 0.5)
    known = np.isfinite(t) & (t >= 0) & (t < len(_HOURS_NEEDED))
    return np.where(known, _HOURS_NEEDED[np.where(known, t, 0).astype(int)], np.inf)


def infection_periods(temperature_c, rh_percent, precipitation_mm, day_hours: int = 24) -> dict[str, np.ndarray]:
    """NEWA's infection periods over a run of hours (axis 0; more axes for cells), for its last `day_hours` hours.

    Returns `infection` (1 if a period's wet hours reach the table at an hour of the day, else 0), the wet hours and
    mean temperature (°C) of the latest period with wet hours in the day (0 and NaN without one), and `truncated` (1
    if that period may have begun before the run: within its first 24 hours). Any hour missing makes all missing."""
    t = np.asarray(temperature_c, dtype=float)
    rh = np.asarray(rh_percent, dtype=float)
    rain = np.asarray(precipitation_mm, dtype=float)
    n = t.shape[0]
    shape = t.shape[1:]
    missing = (np.isnan(t) | np.isnan(rh) | np.isnan(rain)).any(axis=0)
    t_f = np.nan_to_num(t) * 1.8 + 32
    raining = np.nan_to_num(rain) >= RAIN_MM
    wet = raining | (np.nan_to_num(rh) >= WET_RH)
    in_period = np.zeros(shape, dtype=bool)
    last_wet = np.full(shape, -10_000)  # the last hour counted in a period
    hours = np.zeros(shape)
    t_sum = np.zeros(shape)
    start = np.zeros(shape, dtype=int)
    reached = np.zeros(shape, dtype=bool)
    infection = np.zeros(shape, dtype=bool)
    day_start = n - day_hours
    for k in range(n):
        begins = ~in_period & raining[k]
        new = begins & (k - last_wet >= JOIN_HOURS)
        hours = np.where(new, 0.0, hours)
        t_sum = np.where(new, 0.0, t_sum)
        start = np.where(new, k, start)
        reached &= ~new
        in_period |= begins
        counted = in_period & wet[k]
        in_period &= wet[k]
        hours = hours + counted
        t_sum = t_sum + np.where(counted, t_f[k], 0.0)
        last_wet = np.where(counted, k, last_wet)
        with np.errstate(invalid="ignore", divide="ignore"):
            enough = counted & (hours >= hours_needed(t_sum / np.where(hours > 0, hours, 1)))
        newly = enough & ~reached
        reached |= enough
        if k >= day_start:
            infection |= newly
    touched = last_wet >= day_start
    with np.errstate(invalid="ignore", divide="ignore"):
        mean_c = (t_sum / np.where(hours > 0, hours, 1) - 32) / 1.8
    return {
        "infection": np.where(missing, np.nan, infection.astype(float)),
        "wet_hours": np.where(missing, np.nan, np.where(touched, hours, 0.0)),
        "wet_temperature": np.where(missing | ~touched, np.nan, mean_c),
        "truncated": np.where(missing, np.nan, (touched & (start < JOIN_HOURS)).astype(float)),
    }


def maturity_percent(dd_c) -> np.ndarray:
    """Gadoury and MacHardy (1982): the percent of ascospores mature after `dd_c` degree days (base 0 °C)."""
    return 100 * normal_cdf(PROBIT_A + PROBIT_B * np.asarray(dd_c, dtype=float) - 5)


def counted_days(precipitation_mm: np.ndarray) -> np.ndarray:
    """Whether each day's degree days count toward maturity: not when it and the 7 days before it are all dry
    (under 0.2 mm). Days before the series count as wet, so the series' first days always count."""
    rain = np.asarray(precipitation_mm, dtype=float)
    dry = np.nan_to_num(rain, nan=DRY_DAY_MM) < DRY_DAY_MM
    run = np.zeros(dry.shape[1:], dtype=int)
    out = np.empty(dry.shape, dtype=bool)
    for d in range(dry.shape[0]):
        run = np.where(dry[d], run + 1, 0)
        out[d] = run <= DRY_DAYS
    return out


def outputs(inputs: Mapping[str, np.ndarray], biofix_index: int = 0, **options: str) -> dict[str, np.ndarray]:
    lo = np.asarray(inputs["air_temperature_min"], dtype=float)
    hi = np.asarray(inputs["air_temperature_max"], dtype=float)
    n, shape = lo.shape[0], lo.shape[1:]
    dd = np.nan_to_num(np.maximum((lo + hi) / 2, 0))
    counted = counted_days(inputs["precipitation_sum"])
    day_rain = np.asarray(inputs["precipitation_7am_to_7pm"], dtype=float)
    night_rain = np.nan_to_num(np.asarray(inputs["precipitation_8pm_to_6am"], dtype=float))
    rain_t = np.asarray(inputs["temperature_mean_rain_7am_to_7pm"], dtype=float)
    out = {q.name: np.full((n, *shape), np.nan) for q in SPEC.outputs}
    total = np.zeros(shape)
    unadjusted = np.zeros(shape)
    released = np.zeros(shape)
    over = np.zeros(shape, dtype=bool)
    for d in range(biofix_index, n):
        total = total + np.where(counted[d], dd[d], 0.0)
        unadjusted = unadjusted + dd[d]
        mature = maturity_percent(total)
        today = np.zeros(shape)
        night = night_rain >= RAIN_MM
        step = np.where(night[d], (mature - released) * NIGHT_RELEASE, 0.0)
        released = released + step
        today = today + step
        wet_day = np.nan_to_num(day_rain[d]) >= RAIN_MM
        warm = np.nan_to_num(rain_t[d], nan=-99) >= DAY_RAIN_C
        heavy = np.nan_to_num(day_rain[d]) >= DAY_RAIN_MM
        share = np.where(warm & heavy, 0.9, np.where(warm | heavy, 0.5, 0.25))
        step = np.where(wet_day, (mature - released) * share, 0.0)
        released = released + step
        today = today + step
        season = over.astype(float)
        out["maturity"][d] = mature
        out["released"][d] = released
        out["released_today"][d] = today
        out["dd_total"][d] = total
        out["season"][d] = season
        out["infection"][d] = inputs["scab_infection"][d]
        out["wet_hours"][d] = inputs["scab_wet_hours"][d]
        out["wet_temperature"][d] = inputs["scab_wet_temperature"][d]
        all_released = (
            (mature >= MATURE)
            & (np.nan_to_num(day_rain[d]) > SEASON_RAIN_MM)
            & (np.nan_to_num(rain_t[d], nan=-99) > SEASON_RAIN_C)
        )
        over = over | all_released | (unadjusted >= BACKSTOP_DD_C)  # from the next day
    return out


def risk(outputs: Mapping[str, np.ndarray], biofix_index: int = 0, **options: str) -> np.ndarray:
    infection = np.asarray(outputs["infection"], dtype=float)
    season = np.asarray(outputs["season"], dtype=float)
    return np.where(season == 0, infection, np.nan)


def explore(wet_hours: float, temperature: float) -> dict[str, float]:
    return {"risk": float(wet_hours >= hours_needed(temperature))}
