"""Winter (cereal) rye cover crop biomass in spring, from growing degree days since fall planting.

A logistic in degree days with a fixed ceiling (version 0.3, Ben 2026-11-19; `tmp/rye-study/report.md`):
G = GDD since planting, with the fall's part (planting through December 31) counted up to 800 °C-days (Crespo et al.
2024's plateau), and biomass (lb/ac) = 12000 / (1 + exp(−0.00327 (G − 1127)))². GDD single sine above 0 °C with no
upper threshold, from planting. Fitted on √biomass over 138 site-year means of Colet et al.'s Wisconsin data
(2015–2024 falls) with AgWeather's archive weather at each site (`tmp/rye-study/fit03.py`), the ceiling fixed: the
data can't tell 10,000 from 14,000 apart. Modified from the authors' models (their published logistic adds fall
rain, planting date and latitude; their draft algorithm is linear in two 60-day windows): this form stays between 0
and the ceiling and rises every day on real weather, and fall rain and planting date added nothing out of sample.

Levels by cover crop goals (UW–Madison Extension): Low below 2000 lb/ac (some nitrate leaching reduction), Moderate
from 2000 (erosion, runoff P and nitrate), High from 4500 (weed suppression too). Biomass is shown from March 1 (the
data's terminations run April 10 to June 17); the season ends June 15, so later days are flagged out of season, and
`planting_outside_data` flags plantings outside the data's August 25 to November 10. Beta; fitted in southern and
central Wisconsin, shown in Wisconsin and its neighbours.
"""

from collections.abc import Mapping

import numpy as np

from agmodels.degree_days import degree_days_sine
from agmodels.ingredients import Accumulation, DegreeDays, Ingredient, finished
from agmodels.lookup import level_reached
from agmodels.spec import Biofix, Change, Check, Citation, ExplorerInput, Input, ModelSpec, Quantity, Risk

BASE_C = 0.0
CEILING_LB_AC = 12000.0  # fixed, not fitted (the study's profile: 10,000–14,000 fit equally)
K, X0 = 0.00327, 1127.0  # per °C-day and °C-days, on AgWeather's archive (tmp/rye-study/fit03.py)
FALL_CAP_C_DAYS = 800.0  # fall degree days beyond this don't add biomass (Crespo et al. 2024)
LEVELS_LB_AC = (2000, 4500)
# The study's plantings ran August 27 to November 10; the first and last day of year (non-leap) of the planting
# window not flagged, and the first day shown (March 1)
PLANTING_FIRST_DOY, PLANTING_LAST_DOY, SHOWN_FROM_DOY = 237, 314, 60  # August 25, November 10, March 1

SPEC = ModelSpec(
    id="rye-biomass",
    name="Winter rye cover crop biomass",
    group="agronomic",
    version="0.3",
    checks=(
        Check(
            kind="observations",
            against="Rye biomass clipped at 138 Wisconsin site-years in fields and research plots, falls 2015 to 2024, compiled by Colet et al. (2026)",
            result="Refitted with one location left out at a time, the model missed the measured biomass by about 1,180 lb/acre on average and put 68 % of site-years in the right level. Misses were about 630 lb/acre where rye made under 2,000 lb/acre and about 2,270 lb/acre where it made 4,500 or more, which the model tends to underpredict.",
            report="docs/validation/models/rye-biomass.md#against-measured-biomass",
        ),
    ),
    status="beta",
    summary="Spring biomass of a fall-planted cereal rye cover crop, from growing degree days (base 32 °F) since planting, against the biomass cover crop goals need. Fitted on Wisconsin data, mostly from southern and central Wisconsin.",
    topics=("cereal-rye-cover-crop",),
    crops=("rye",),
    citations=(
        Citation(
            text="Colet, F., Bradford, B., Mourtzinis, S., Severo Silva, T., Smith, D. L., Chudzik, G., Kendall, M. A., Ruark, M. D., Kurth, A., Nunes, J. J., Smith, D. H., Werle, R. and Conley, S. P. (2026). Prediction of cereal rye biomass accumulation in Wisconsin based on weather and agronomic management. Crop, Forage & Turfgrass Management 12, e70157. AgWeather's model is modified from the authors' and refitted on their data.",
            doi="10.1002/cft2.70157",
        ),
        Citation(
            text="Crespo, C., O'Brien, P. L., Ruis, S. J., Kovar, J. L. and Kaspar, T. C. (2024). Thermal time and precipitation dictate cereal rye shoot biomass production. Field Crops Research 315, 109473.",
            doi="10.1016/j.fcr.2024.109473",
        ),
        Citation(
            text="UW–Madison Extension: Biomass thresholds for cereal rye cover crop goals.",
            url="https://cropsandsoils.extension.wisc.edu/articles/biomass-thresholds-for-cereal-rye-cover-crop-goals/",
        ),
        Citation(
            text="Badger Crop Network: How much cereal rye cover crop biomass is needed to suppress troublesome weeds in Wisconsin?",
            url="https://badgercropnetwork.com/how-much-cereal-rye-cover-crop-biomass-is-needed-to-suppress-troublesome-weeds-in-wisconsin/",
        ),
    ),
    inputs=(
        Input(name="air_temperature_min", label="Minimum temperature", unit="degC"),
        Input(name="air_temperature_max", label="Maximum temperature", unit="degC"),
    ),
    outputs=(
        Quantity(
            name="biomass",
            label="Predicted biomass",
            unit="lb_ac",
            description="From March 1 after planting; none in the fall and winter",
        ),
        Quantity(name="gdd_total", label="GDD (base 32 °F) since planting", unit="degC_day"),
        Quantity(name="gdd_fall", label="GDD (base 32 °F) from planting through December 31", unit="degC_day"),
        Quantity(
            name="gdd_counted",
            label="GDD counted toward biomass",
            unit="degC_day",
            description="GDD since planting, with the fall's counted up to 800 °C-days (1,440 °F-days)",
        ),
        Quantity(
            name="planting_outside_data",
            label="Planting date outside the model's data",
            unit="index",
            description="1 when the planting date is before August 25 or after November 10",
        ),
    ),
    risk=Risk(
        levels=("Low", "Moderate", "High"),
        criteria="Biomass: Low below 2,000 lb/ac (modest nitrate leaching reduction), Moderate from 2,000 (erosion, runoff phosphorus and nitrate), High from 4,500 (weed suppression as well).",
    ),
    explorer=(
        ExplorerInput(
            name="gdd_total",
            label="GDD (base 32 °F) since planting",
            unit="degC_day",
            minimum=0,
            maximum=3000,
            step=10,
            default=1200,
        ),
        ExplorerInput(
            name="gdd_fall",
            label="GDD (base 32 °F) from planting through December 31",
            unit="degC_day",
            minimum=0,
            maximum=1500,
            step=10,
            default=500,
        ),
    ),
    explorer_outputs=(
        Quantity(name="level", label="Biomass level", unit="index", description="Index into the risk levels"),
    ),
    sweep={
        "gdd_total": tuple(float(g) for g in range(0, 3001, 100)),
        "gdd_fall": (0.0, 400.0, 800.0, 1200.0),
    },
    context=("day_of_year", "year"),
    region=("WI", "MN", "IA", "IL", "MI"),
    season=("08-25", "06-15"),
    biofix=Biofix(default="10-01", label="Fall planting date"),
    ingredients=(Ingredient(name="gdd", unit="degC_day", degree_days=DegreeDays(method="sine", base_f=32)),),
    accumulations=(
        Accumulation(name="gdd_total", of="gdd"),
        Accumulation(name="gdd_fall", of="gdd", until="12-31"),
    ),
    changelog=(
        Change(version="0.1", date="2026-10-28", note="Ported from the Crop Risk Tool."),
        Change(
            version="0.2",
            date="2026-11-01",
            note="Biomass is 0 where the fit's linear term goes negative (a late planting after a very wet fall); squaring it had made biomass rise again with more rain.",
        ),
        Change(
            version="0.3",
            date="2026-11-19",
            note="A new model, refitted on Colet et al.'s Wisconsin data with AgWeather's weather: biomass rises with degree days since planting (no upper threshold) to a ceiling of 12,000 lb/ac, the fall's degree days counting up to 800 °C-days (Crespo et al. 2024). Planting date and fall rain are no longer inputs. The Crop Risk Tool's logistic (height 423.1 − 1.031 × planting day − 0.2878 × fall rain, k 0.003663, midpoint 1,049 GDD at 0/35 °C) was fed all fall precipitation where it had been fitted on rain above freezing, and fitted no better out of sample. Shown from March 1; out of season after June 15; plantings outside August 25 to November 10 flagged.",
        ),
    ),
)


def counted_gdd(gdd_total, gdd_fall) -> np.ndarray:
    """GDD since planting with the fall's part (planting through December 31) counted up to 800 °C-days."""
    total, fall = (np.asarray(x, dtype=float) for x in (gdd_total, gdd_fall))
    return total - fall + np.minimum(fall, FALL_CAP_C_DAYS)


def biomass(gdd_counted) -> np.ndarray:
    """Biomass (lb/ac) from the counted GDD (°C-days): the square of a logistic, rising to the ceiling."""
    g = np.asarray(gdd_counted, dtype=float)
    return CEILING_LB_AC / (1 + np.exp(-K * (g - X0))) ** 2


def _is_leap(year: np.ndarray) -> np.ndarray:
    y = year.astype(int)
    return ((y % 4 == 0) & ((y % 100 != 0) | (y % 400 == 0))).astype(float)


def ingredients(inputs: Mapping[str, np.ndarray]) -> dict[str, np.ndarray]:
    lo, hi = (np.asarray(inputs[k], dtype=float) for k in ("air_temperature_min", "air_temperature_max"))
    return {"gdd": degree_days_sine(lo, hi, BASE_C)}


def finish(values: Mapping[str, np.ndarray], **options: str) -> dict[str, np.ndarray]:
    """Biomass from the GDD since planting and its fall part, from March 1 after planting; the planting flag."""
    gdd_total, gdd_fall = values["gdd_total"], values["gdd_fall"]
    counted = counted_gdd(gdd_total, gdd_fall)
    along_time = (-1, *([1] * (counted.ndim - 1))) if counted.ndim else ()  # a day's context, on every cell
    doy, year = (np.asarray(values[k], dtype=float).reshape(along_time) for k in ("day_of_year", "year"))
    planted = np.asarray(values["biofix_day_of_year"], dtype=float)
    with np.errstate(invalid="ignore"):
        spring = (doy < planted) & (doy >= SHOWN_FROM_DOY + _is_leap(year))  # the year after planting, from March 1
        planting_year = np.where(doy >= planted, year, year - 1)
        leap = _is_leap(planting_year)
        outside = (planted < PLANTING_FIRST_DOY + leap) | (planted > PLANTING_LAST_DOY + leap)
    known = np.isfinite(counted)
    return {
        "biomass": np.where(spring & known, biomass(counted), np.nan),
        "gdd_total": gdd_total,
        "gdd_fall": gdd_fall,
        "gdd_counted": counted,
        "planting_outside_data": np.where(known, outside.astype(float), np.nan),
    }


def outputs(inputs: Mapping[str, np.ndarray], biofix_index: int = 0, **options: str) -> dict[str, np.ndarray]:
    return finished(
        accumulations=SPEC.accumulations,
        values=ingredients(inputs),
        inputs=inputs,
        biofix_index=biofix_index,
        finish=finish,
        options=options,
    )


def risk(outputs: Mapping[str, np.ndarray], biofix_index: int = 0, **options: str) -> np.ndarray:
    return level_reached(outputs["biomass"], *LEVELS_LB_AC)


def explore(gdd_total: float, gdd_fall: float) -> dict[str, float]:
    value = biomass(counted_gdd(gdd_total, gdd_fall))
    return {"biomass": float(value), "level": float(level_reached(value, *LEVELS_LB_AC))}
