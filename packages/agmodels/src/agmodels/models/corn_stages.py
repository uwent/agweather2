"""Corn growth stages from planting, for any hybrid maturity, by growing degree days (modified 50/86 °F).

Each day's GDD (min raised to 50 °F, both capped at 86 °F) add up from planting, and each stage starts at a GDD
total set by the hybrid's rating, its GDD from planting to black layer (R6) on the seed bag:

- VE at 110 GDD (Nielsen: emergence takes 100–120 GDD from planting);
- a leaf collar every 82 GDD from VE to V10, then every 50 (Nielsen, from Wuethrich's 14 hybrids);
- R1 (silking) from Hybrid-Maize's fit over 107 hybrids (Yang et al. 2004, eq. 12, base 10 °C, from emergence):
  GDD_silking = 100 + 0.445 GDD_total, here 180 + 0.445 GDD_total in °F·d. Yang et al. take 50 °C·d off the
  intercept for irrigated fields at yield potential; fields in general are the fit's own population, so it's left
  as fitted. For a 2700 GDD hybrid R1 falls at 1443 GDD, against NCH-40's 1400;
- VT one leaf interval (50 GDD) before R1, so the last V-stage is the last collar before it. An assumption to check
  against Abendroth et al. (2011); it gives 17, 19 and 21 leaves for 2500, 2700 and 2900 GDD hybrids, where Iowa
  State says most hybrids have 18–21;
- R2–R6 at NCH-40's fractions of the time from R1 to R6 (Neild and Newman, Table 3, 2700 GDD hybrid: blister
  1660, dough 1925, kernels denting 2190, dented 2450, black layer 2700 from silking at 1400), R3 from Nielsen's
  milk stage 900 GDD before black layer. R5 is the start of denting (2190); R5.5, half milk line, is NCH-40's
  "kernels dented" (Nielsen 1996 labels these R4.5 and R5; his later grain-fill article puts R5 at 31–33 days after
  silking and R6 at 55–65, which matches the start of denting).

The old AgWeather site's corn table (V8 600 … R6 2400–2600 from May 15) predates current staffing and isn't vetted,
so it isn't a parity reference; the tests check the published benchmarks instead. NCH-40's leaf counts (6 leaves
at 475 GDD) run ahead of the leaf-collar method used here (V6 at 602), as leaf-tip counts do.
"""

from collections.abc import Mapping

import numpy as np

from agmodels.accumulate import running_total
from agmodels.crops import CropStage, number_option, stage_reached
from agmodels.degree_days import degree_days_modified
from agmodels.spec import Biofix, Change, Citation, ExplorerInput, ModelSpec, Option, Quantity

EMERGENCE_GDD = 110.0
LEAF_GDD_TO_V10 = 82.0
LEAF_GDD_AFTER_V10 = 50.0
SILKING_INTERCEPT_F = 180.0  # Yang et al.'s 100 °C·d
SILKING_SLOPE = 0.445
VT_BEFORE_R1 = LEAF_GDD_AFTER_V10
MAX_LEAVES = 25
# Fraction of the GDD from R1 to R6 at which each grain-fill stage starts (NCH-40 Table 3; R3 from Nielsen 1996)
GRAIN_FILL = (
    ("R2", 260 / 1300),
    ("R3", 400 / 1300),
    ("R4", 525 / 1300),
    ("R5", 790 / 1300),
    ("R5.5", 1050 / 1300),
    ("R6", 1.0),
)

MATURITY = Option(
    name="black_layer_gdd",
    label="Hybrid maturity: GDD from planting to black layer",
    choices=(
        ("2100", "2100 GDD (early season)"),
        ("2300", "2300 GDD (early season)"),
        ("2500", "2500 GDD (mid-season)"),
        ("2700", "2700 GDD (mid-season)"),
        ("2900", "2900 GDD (full season)"),
        ("3100", "3100 GDD (full season)"),
    ),
    default="2500",
)  # NCH-40's classes: early season 2100–2400, mid-season 2400–2800, full season 2900–3200

MARGIN_DAYS = 3  # VE, R1 and R6 came within 3 days of observed on Yang et al.'s seasons

STAGES = (
    CropStage(code="VE", name="Emergence", description="The coleoptile breaks the soil surface."),
    *(
        CropStage(code=f"V{n}", name=f"{n} leaf collars", description="Leaf collars visible on the main stem.")
        for n in range(1, MAX_LEAVES)
    ),
    CropStage(
        code="VT", name="Tasseling", description="The last branch of the tassel is fully visible.", estimated=True
    ),
    CropStage(code="R1", name="Silking", description="Silks visible outside the husks; pollination."),
    CropStage(code="R2", name="Blister", description="Kernels white and blister-like, filled with clear fluid."),
    CropStage(code="R3", name="Milk", description="Kernels yellow outside with milky white fluid inside."),
    CropStage(code="R4", name="Dough", description="Kernel contents thicken to a pasty consistency."),
    CropStage(code="R5", name="Dent", description="Kernels at the top of the ear begin to dent; the milk line forms."),
    CropStage(code="R5.5", name="Half milk line", description="The milk line is halfway down the kernel."),
    CropStage(
        code="R6",
        name="Black layer",
        description="Physiological maturity: kernels have reached their maximum dry weight.",
    ),
)

SPEC = ModelSpec(
    id="corn-stages",
    name="Corn growth stages",
    group="crop",
    version="1.0",
    status="beta",
    summary="Corn's vegetative and reproductive stages from planting, by growing degree days (modified 50/86 °F), "
    "for any hybrid maturity.",
    topics=("corn",),
    crops=("Corn",),
    citations=(
        Citation(
            text="Neild, R. E. and Newman, J. E. (1987). Growing season characteristics and requirements in the Corn "
            "Belt. National Corn Handbook NCH-40, Purdue University.",
            url="https://www.extension.purdue.edu/extmedia/nch/nch-40.html",
        ),
        Citation(
            text="Yang, H. S., Dobermann, A., Lindquist, J. L., Walters, D. T., Arkebauer, T. J. and Cassman, K. G. "
            "(2004). Hybrid-maize: a maize simulation model that combines two crop modeling approaches. Field Crops "
            "Research 87, 131–154.",
            doi="10.1016/j.fcr.2003.10.003",
        ),
        Citation(
            text="Nielsen, R. L. Use thermal time to predict leaf stage development in corn. Corny News Network, "
            "Purdue University.",
            url="https://www.agry.purdue.edu/ext/corn/news/timeless/VStagePrediction.html",
        ),
        Citation(
            text="Nielsen, R. L. Grain fill stages in corn. Corny News Network, Purdue University.",
            url="https://www.agry.purdue.edu/ext/corn/news/timeless/GrainFill.html",
        ),
        Citation(
            text="Abendroth, L. J., Elmore, R. W., Boyer, M. J. and Marlay, S. K. (2011). Corn growth and development. "
            "PMR 1009, Iowa State University Extension.",
            url="https://shop.iastate.edu/extension/farm-environment/crops-and-soils/agronomic-crops/pmr1009.html",
        ),
    ),
    inputs=(
        Quantity(name="air_temperature_min", label="Minimum temperature", unit="degC"),
        Quantity(name="air_temperature_max", label="Maximum temperature", unit="degC"),
    ),
    outputs=(
        Quantity(name="stage", label="Growth stage", unit="index", description="Index in the crop's stage list"),
        Quantity(name="gdd_total", label="GDD since planting", unit="degF_day"),
        Quantity(name="gdd", label="GDD (modified 50/86 °F)", unit="degF_day"),
    ),
    risk=None,
    explorer=(
        ExplorerInput(
            name="gdd_total",
            label="GDD since planting",
            unit="degF_day",
            minimum=0,
            maximum=3500,
            step=10,
            default=1000,
        ),
        ExplorerInput(
            name="black_layer_gdd",
            label="GDD from planting to black layer",
            unit="degF_day",
            minimum=1800,
            maximum=3400,
            step=50,
            default=2500,
        ),
    ),
    sweep={
        "gdd_total": tuple(float(g) for g in range(0, 3501, 25)),
        "black_layer_gdd": tuple(float(m) for m in range(2100, 3101, 200)),
    },
    options=(MATURITY,),
    season=("04-01", "10-31"),
    biofix=Biofix(default="05-10", label="Planting date"),
    changelog=(Change(version="1.0", date="2026-10-28", note="First version."),),
)


def stages(**options: str) -> tuple[CropStage, ...]:
    return STAGES


def thresholds(black_layer_gdd: float) -> np.ndarray:
    """GDD from planting at which each stage in `STAGES` starts, NaN for leaves the hybrid doesn't reach."""
    r6 = float(black_layer_gdd)
    r1 = EMERGENCE_GDD + SILKING_INTERCEPT_F + SILKING_SLOPE * (r6 - EMERGENCE_GDD)
    vt = r1 - VT_BEFORE_R1
    leaves = np.arange(1, MAX_LEAVES)
    v = EMERGENCE_GDD + np.where(
        leaves <= 10, LEAF_GDD_TO_V10 * leaves, LEAF_GDD_TO_V10 * 10 + LEAF_GDD_AFTER_V10 * (leaves - 10)
    )
    v = np.where(v < vt, v, np.nan)
    fill = [r1 + fraction * (r6 - r1) for _, fraction in GRAIN_FILL]
    return np.array([EMERGENCE_GDD, *v, vt, r1, *fill])


def outputs(inputs: Mapping[str, np.ndarray], biofix_index: int = 0, **options: str) -> dict[str, np.ndarray]:
    lo, hi = (np.asarray(inputs[k], dtype=float) * 1.8 + 32 for k in ("air_temperature_min", "air_temperature_max"))
    gdd = degree_days_modified(lo, hi, 50, 86)
    total = running_total(gdd, biofix_index)
    stage = stage_reached(total, thresholds(number_option(options, MATURITY)))
    return {"stage": stage, "gdd_total": total, "gdd": gdd}


def explore(gdd_total: float, black_layer_gdd: float) -> dict[str, float]:
    return {"stage": float(stage_reached(gdd_total, thresholds(black_layer_gdd)))}
