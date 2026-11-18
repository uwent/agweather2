"""Fire blight (Erwinia amylovora) of apple: blossom blight risk from first bloom to petal fall, by Cougarblight 2010 and
MaryBlyt's epiphytic infection potential (EIP), as NEWA runs them (D95), with the published models where they differ.

- **Bloom:** from first blossom open to petal fall. NEWA's defaults: first blossom at 230 degree days (base 43 °F,
  single sine, from January 1) and petal fall at 578 or June 15, whichever comes first. Given a grower's first
  blossom date (the biofix), petal fall is 348 degree days later (578 − 230) or June 15.
- **Cougarblight 2010** (Smith and Pusey 2011): each hour scores a value by its temperature (Smith's table in °F as
  NEWA and WSU's 2019 sheet hold it, from 0.05 at 51 °F to 52 at 88–89 °F, 0 from 96 °F; the paper's values have no
  negatives above 100 °F), the day's values are summed (`fire_blight_features`), and the risk is the last four days'
  total (today and the three before) against thresholds set by the orchard's blight history: NEWA's three (Low, High
  from 300, 150 or 80, Extreme from 800, 350 or 200). NEWA counts no hour below 60 °F, as the model did before 2010;
  the 2010 paper counts from 50 °F. Smith and Pusey give 500, 200 and 100 for High (WSU's Decision Aid System 400,
  150 and 80).
- **Wetting:** rain of 0.01 in or more in the day, or 2 or more hours estimated wet (RH ≥ 90 % or rain; dew), Smith and
  Pusey's two hours. Infection is possible when the blossoms are wet while Cougarblight's risk is High or above.
- **MaryBlyt EIP** (version 7.1; Turechek and Biggs 2015, Biggs and Turechek 2018): degree hours above 65 °F, summed
  hour by hour (the program estimates them from the day's high and low; NEWA sums hours, as here), over the blossoms'
  life: a day's degree hours stay while the degree days above 40 °F (single sine, 90 °F cutoff) from that day through
  yesterday are under 80. While the total is under 400 °F·h, a day with a high under 65 °F cuts the total by a third,
  a second in a row by half of what's left, a third to nothing, and a low at or below 32 °F clears it (the day's own
  hours too); a low at or below 24 °F restarts the blossoms' clock whatever the total. EIP = 100 × total / 198 (110
  degree hours above 18.3 °C).
- **MaryBlyt's risk:** of its four conditions (blossoms open; EIP ≥ 100; wetting: rain of 0.01 in that day or 0.10 in
  the day before, or a dew; a mean temperature above 60 °F), Low with the blossoms alone, Moderate with one more, High
  with two, Infection with all four. Blossom blight symptoms are expected 103 degree days above 55 °F (single sine,
  90 °F cutoff) after an infection day.
- **Risk** (the map's colors): Cougarblight's level during bloom; none outside it.

Differences from NEWA kept: Cougarblight counts hours from 50 °F (the 2010 paper; NEWA from 60) and has a wetting
output (NEWA has none); MaryBlyt's degree days are the sine with a 90 °F cutoff (NEWA: the simple average), its cool
day is a high under 65 °F (NEWA: at or under), freezes at or below 32 and 24 °F (NEWA: under 33 and under 24), EIP ≥ 100
(NEWA: over 100), the day before's rain from 0.10 in (NEWA: over 0.1), and symptoms after 103 degree days (NEWA: 90
with the sine, which mixes the 1990 interval with the later method). Trauma blight (hail, a storm) and canker and
shoot blight aren't modelled.
"""

from collections.abc import Mapping

import numpy as np

from agmodels.degree_days import degree_days_sine
from agmodels.spec import Biofix, Change, Citation, ExplorerInput, Input, ModelSpec, Option, Quantity, Risk

# Cougarblight's hourly value by the hour's temperature, rounded to a whole °F (Smith's table, 2019 sheet and NEWA)
COUGARBLIGHT_F: dict[int, float] = {
    51: 0.05, 52: 0.1, 53: 0.16, 54: 0.21, 55: 0.23, 56: 0.29, 57: 0.33, 58: 0.38, 59: 0.44, 60: 0.52, 61: 0.62,
    62: 0.72, 63: 0.95, 64: 1.06, 65: 1.16, 66: 1.41, 67: 2, 68: 2.7, 69: 3.3, 70: 4, 71: 4.9, 72: 6.3, 73: 7.95,
    74: 11, 75: 14.1, 76: 17, 77: 20.3, 78: 23.5, 79: 27, 80: 30, 81: 33.2, 82: 36, 83: 38.9, 84: 42.2, 85: 46,
    86: 48.2, 87: 50.2, 88: 52, 89: 52, 90: 51.5, 91: 50.5, 92: 47.5, 93: 40, 94: 28, 95: 10,
}  # fmt: skip
_VALUES = np.array([COUGARBLIGHT_F.get(t, 0.0) for t in range(0, 130)])
DAYS = 4

HISTORY = Option(
    name="blight_history",
    label="Fire blight near the orchard",
    choices=(
        ("none", "None in the neighborhood last year"),
        ("last_year", "In the neighborhood last year"),
        ("active", "Active in the neighborhood now"),
    ),
    default="last_year",
)  # NEWA's three, with its default
THRESHOLDS = {"none": (300.0, 800.0), "last_year": (150.0, 350.0), "active": (80.0, 200.0)}  # High, Extreme

FIRST_BLOSSOM_DD = 230.0  # DD43 from January 1 (NEWA)
PETAL_FALL_DD = 578.0
JUNE_15 = 166  # day of year in a common year
WET_RAIN_MM = 0.254  # 0.01 in
DEW_HOURS = 2
YESTERDAY_RAIN_MM = 2.54  # 0.10 in
DH_BASE_F = 65.0
EIP_FULL_F_HOURS = 198.0
WINDOW_DD40 = 80.0
CUT_STOPS_F_HOURS = 400.0
FREEZE_F = 32.0
HARD_FREEZE_F = 24.0
MEAN_F = 60.0
SYMPTOMS_DD55 = 103.0
F_HOURS_PER_C_HOUR = 1.8

SPEC = ModelSpec(
    id="fire-blight",
    name="Fire blight (blossom blight)",
    group="disease",
    version="0.1",
    status="beta",
    summary="Fire blight blossom infection risk during bloom, by Cougarblight 2010's four-day temperature risk and MaryBlyt's infection potential, with wetting and expected symptoms.",
    topics=("fire-blight",),
    crops=("apple",),
    citations=(
        Citation(
            text="Smith, T. J. and Pusey, P. L. (2011). CougarBlight 2010, a significant update of the CougarBlight fire blight infection risk model. Acta Horticulturae 896, 331–336.",
            doi="10.17660/ActaHortic.2011.896.45",
        ),
        Citation(
            text="Steiner, P. W. (1990). Predicting apple blossom infections by Erwinia amylovora using the MARYBLYT model. Acta Horticulturae 273, 139–148.",
            doi="10.17660/ActaHortic.1990.273.18",
        ),
        Citation(
            text="Turechek, W. W. and Biggs, A. R. (2015). Maryblyt v. 7.1 for Windows: an improved fire blight forecasting program for apples and pears. Plant Health Progress 16, 16–22.",
            doi="10.1094/PHP-RS-14-0046",
        ),
        Citation(
            text="Biggs, A. R. and Turechek, W. W. (2018). Maryblyt 7.1.1 for Windows: a predictive program for forecasting fire blight disease in apples and pears. User manual, West Virginia University and USDA-ARS.",
            url="https://grapepathology.org/wp-content/uploads/2018/12/Maryblyt-7.1.1-Manual-12142018.pdf",
        ),
        Citation(
            text="NEWA, Network for Environment and Weather Applications, Cornell University: fire blight model (Cougarblight and MaryBlyt EIP).",
            url="https://newa.cornell.edu/fire-blight",
        ),
        Citation(
            text="Enviroweather, Michigan State University: fire blight model.",
            url="https://enviroweather.msu.edu/crops/apple/fireblight",
        ),
    ),
    inputs=(
        Input(name="air_temperature_min", label="Minimum temperature", unit="degC"),
        Input(name="air_temperature_max", label="Maximum temperature", unit="degC"),
        Input(name="precipitation_sum", label="Precipitation", unit="mm"),
        Input(name="cougarblight_risk_values", label="Cougarblight's hourly risk values, summed", unit="index"),
        Input(name="degree_hours_over_65f", label="Degree hours above 65 °F", unit="degC_hour"),
        Input(name="hours_wet", label="Hours estimated wet (RH at or above 90% or rain)", unit="hour"),
    ),
    outputs=(
        Quantity(name="cougarblight", label="Cougarblight four-day risk value", unit="index"),
        Quantity(
            name="eip",
            label="Epiphytic infection potential (EIP)",
            unit="index",
            description="100 when the blossoms' degree hours above 65 °F reach 198",
        ),
        Quantity(
            name="maryblyt", label="MaryBlyt risk", unit="index", description="0 Low, 1 Moderate, 2 High, 3 Infection"
        ),
        Quantity(
            name="wetting",
            label="Blossoms wet",
            unit="index",
            description="1 with rain of 0.01 in or two hours estimated wet",
        ),
        Quantity(
            name="infection_possible",
            label="Infection possible",
            unit="index",
            description="1 when the blossoms are wet while Cougarblight's risk is High or Extreme",
        ),
        Quantity(name="degree_hours", label="Degree hours above 65 °F, blossoms' life", unit="degC_hour"),
        Quantity(
            name="symptoms_dd",
            label="Degree days since the latest MaryBlyt infection (base 55 °F)",
            unit="degF_day",
            description="Symptoms are expected from 103",
        ),
        Quantity(
            name="bloom",
            label="Bloom",
            unit="index",
            description="0 before first blossom, 1 in bloom, 2 after petal fall",
        ),
    ),
    risk=Risk(
        levels=("Low", "High", "Extreme"),
        criteria="During bloom, Cougarblight's four-day total by the orchard's history: with blight in the neighborhood last year (the default), High from 150 and Extreme from 350; with none, 300 and 800; with blight active now, 80 and 200.",
    ),
    explorer=(
        ExplorerInput(
            name="cougarblight",
            label="Cougarblight four-day total",
            unit="index",
            minimum=0,
            maximum=1000,
            step=10,
            default=200,
        ),
    ),
    explorer_outputs=(
        Quantity(name="risk", label="Risk level", unit="index", description="Index into the risk levels"),
    ),
    sweep={"cougarblight": tuple(float(v) for v in range(0, 1001, 25))},
    options=(HISTORY,),
    context=("day_of_year", "year"),
    season=("03-01", "07-15"),
    biofix=Biofix(default="01-01", label="January 1, or the day the orchard's first blossoms opened"),
    changelog=(Change(version="0.1", date="2026-11-18", note="First version."),),
)


def cougarblight_values(temperature_c) -> np.ndarray:
    """Each hour's Cougarblight value from its temperature (°C), at the whole °F rounded half up as NEWA does."""
    t = np.floor(np.asarray(temperature_c, dtype=float) * 1.8 + 32 + 0.5)
    known = np.isfinite(t) & (t >= 0) & (t < len(_VALUES))
    return np.where(np.isfinite(t), np.where(known, _VALUES[np.where(known, t, 0).astype(int)], 0.0), np.nan)


def level(total, history: str = HISTORY.default) -> np.ndarray:
    high, extreme = THRESHOLDS[history]
    total = np.asarray(total, dtype=float)
    return np.where(np.isnan(total), np.nan, (total >= high).astype(float) + (total >= extreme))


def _per_day(values, n: int) -> np.ndarray:
    """A context value per day (a map may pass one for every day, or one alone)."""
    v = (
        np.asarray(values, dtype=float).reshape(-1)
        if np.ndim(values) <= 1
        else np.asarray(values, dtype=float)[:, *([0] * (np.ndim(values) - 1))]
    )
    return np.broadcast_to(v if v.size == n else v[:1], (n,)).astype(float)


def _leap(year) -> np.ndarray:
    y = np.asarray(year, dtype=float)
    return ((y % 4 == 0) & ((y % 100 != 0) | (y % 400 == 0))).astype(float)


def outputs(inputs: Mapping[str, np.ndarray], biofix_index: int = 0, **options: str) -> dict[str, np.ndarray]:
    history = options.get(HISTORY.name, HISTORY.default)
    lo_f = np.asarray(inputs["air_temperature_min"], dtype=float) * 1.8 + 32
    hi_f = np.asarray(inputs["air_temperature_max"], dtype=float) * 1.8 + 32
    n, shape = lo_f.shape[0], lo_f.shape[1:]
    expand = (-1, *([1] * len(shape)))
    doy = _per_day(inputs["day_of_year"], n).reshape(expand)
    year = _per_day(inputs.get("year", 2025.0), n).reshape(expand)
    june_15 = JUNE_15 + _leap(year)
    rain = np.nan_to_num(np.asarray(inputs["precipitation_sum"], dtype=float))
    wet_hours = np.nan_to_num(np.asarray(inputs["hours_wet"], dtype=float))
    daily_values = np.asarray(inputs["cougarblight_risk_values"], dtype=float)
    dh = np.nan_to_num(np.asarray(inputs["degree_hours_over_65f"], dtype=float)) * F_HOURS_PER_C_HOUR
    dd43 = np.nan_to_num(degree_days_sine(lo_f, hi_f, 43.0))
    dd40 = np.nan_to_num(degree_days_sine(lo_f, hi_f, 40.0, 90.0))
    dd55 = np.nan_to_num(degree_days_sine(lo_f, hi_f, 55.0, 90.0))
    out = {q.name: np.full((n, *shape), np.nan) for q in SPEC.outputs}

    # Bloom: from January 1 by degree days, or from the grower's first blossom
    from_january = float(np.ravel(doy[biofix_index])[0]) == 1 if n > biofix_index else True
    total43 = np.zeros(shape)
    started = np.zeros(shape, dtype=bool)
    ended = np.zeros(shape, dtype=bool)
    bloom = np.full((n, *shape), np.nan)
    for d in range(biofix_index, n):
        total43 = total43 + dd43[d]
        started |= (total43 >= FIRST_BLOSSOM_DD) if from_january else True
        bloom[d] = np.where(ended, 2.0, np.where(started, 1.0, 0.0))  # petal fall's own day is still bloom
        reached = total43 >= (PETAL_FALL_DD if from_january else PETAL_FALL_DD - FIRST_BLOSSOM_DD)
        ended |= started & (reached | (doy[d] >= june_15[d]))
    out["bloom"] = bloom
    in_bloom = bloom == 1

    # Cougarblight: today and the three days before
    four = np.full((n, *shape), np.nan)
    for d in range(n):
        if d >= DAYS - 1:
            four[d] = daily_values[d - DAYS + 1 : d + 1].sum(axis=0)
    wetting = (rain >= WET_RAIN_MM) | (wet_hours >= DEW_HOURS)
    out["cougarblight"] = np.where(in_bloom, four, np.nan)
    out["wetting"] = np.where(bloom >= 0, wetting.astype(float), np.nan)
    out["infection_possible"] = np.where(in_bloom, (wetting & (level(four, history) >= 1)).astype(float), np.nan)

    # MaryBlyt: the blossoms' degree hours, day by day from first blossom
    window = np.zeros((n, *shape))  # each day's degree hours still counted (scaled by cuts)
    age = np.zeros((n, *shape))  # DD40 from each day through yesterday
    cool_run = np.zeros(shape)
    since = np.full(shape, np.nan)  # DD55 since the latest infection
    for d in range(biofix_index, n):
        on = in_bloom[d]
        first_day = on & ~(in_bloom[d - 1] if d > biofix_index else np.zeros(shape, dtype=bool))
        window[: d + 1] = np.where(first_day, 0.0, window[: d + 1])
        age[: d + 1] = np.where(first_day, 0.0, age[: d + 1])
        if d > 0:
            age[:d] = age[:d] + dd40[d - 1]  # yesterday's DD40 ages every earlier day
        window[:d] = np.where(age[:d] >= WINDOW_DD40, 0.0, window[:d])
        window[d] = np.where(on, dh[d], 0.0)
        total = window[: d + 1].sum(axis=0)
        hard_freeze = lo_f[d] <= HARD_FREEZE_F
        window[: d + 1] = np.where(hard_freeze, 0.0, window[: d + 1])
        below_stop = window[: d + 1].sum(axis=0) < CUT_STOPS_F_HOURS
        freeze = (lo_f[d] <= FREEZE_F) & below_stop
        window[: d + 1] = np.where(freeze, 0.0, window[: d + 1])
        cool = hi_f[d] < DH_BASE_F
        cool_run = np.where(cool, cool_run + 1, 0)
        factor = np.where(cool_run == 1, 2 / 3, np.where(cool_run == 2, 0.5, 0.0))
        window[: d + 1] = np.where(cool & below_stop & ~freeze, window[: d + 1] * factor, window[: d + 1])
        total = window[: d + 1].sum(axis=0)
        eip = 100 * total / EIP_FULL_F_HOURS
        yesterday = rain[d - 1] if d > 0 else np.zeros(shape)
        wet = (rain[d] >= WET_RAIN_MM) | (yesterday >= YESTERDAY_RAIN_MM) | (wet_hours[d] >= DEW_HOURS)
        warm = (lo_f[d] + hi_f[d]) / 2 > MEAN_F
        count = (eip >= 100).astype(float) + wet + warm
        out["eip"][d] = np.where(on, eip, np.nan)
        out["degree_hours"][d] = np.where(on, total / F_HOURS_PER_C_HOUR, np.nan)
        out["maryblyt"][d] = np.where(on, count, np.nan)
        since = np.where(np.isfinite(since), since + dd55[d], since)
        since = np.where(on & (count == 3), 0.0, since)
        out["symptoms_dd"][d] = since
    return out


def risk(outputs: Mapping[str, np.ndarray], biofix_index: int = 0, **options: str) -> np.ndarray:
    return level(outputs["cougarblight"], options.get(HISTORY.name, HISTORY.default))


def explore(cougarblight: float) -> dict[str, float]:
    return {"risk": float(level(cougarblight))}
