"""Apple bud and bloom stages by degree days (base 43 °F, single sine, from January 1), for McIntosh-type timing.

The stage thresholds are NEWA's (Cornell's Network for Environment and Weather Applications), which Wisconsin's
apple growers and UW Extension's fruit updates use: silver tip 75, green tip 101, half-inch green 165, tight cluster
199, pink 290, bloom 346, petal fall 454 and post petal fall 580 degree days from January 1 (NEWA 3.0's stage
table, read from its site, 2026-11-17; D95). They sit inside the ranges Cornell's Scaffolds Fruit Journal gives
for McIntosh at Geneva, New York, over about 26 years (normal ± one standard deviation, base 43 °F single sine from
January 1; 2015 issues): silver tip 61–109, green tip 97–145, half-inch green 136–221, tight cluster 176–282, pink
271–317, bloom 345–417, petal fall 448–524, fruit set 510–598. NEWA's "post petal fall" falls in Scaffolds' fruit
set, the name used here.

NEWA's own single sine has `sin` where Baskerville and Emin's method has `asin` (and π as 3.14); this model uses the
method as published, which puts a stage on NEWA's day in 95–102 of 103 Wisconsin station-seasons and at most two days
off (docs/validation/models/apple-stages.md). Early cultivars (Zestar, Paula Red) run a few days ahead of McIntosh and late ones behind
(Wisconsin observations: early cultivars a mean 2.8 days ahead); a grower's own stage observations are the better guide in the orchard.

Not modelled: harvest maturity (MSU's McIntosh, Jonathan and Red Delicious formulas; out of scope), MSU's base
42 °F stage table (Enviroweather's code counts it from January 1; NEWA's wins, D95), and the cover-spray intervals
after fruit set.
"""

from collections.abc import Mapping

import numpy as np

from agmodels.crops import CropStage, stage_reached
from agmodels.degree_days import degree_days_sine
from agmodels.ingredients import Accumulation, DegreeDays, Ingredient, finished
from agmodels.spec import Biofix, Change, Check, Citation, ExplorerInput, Input, ModelSpec, Quantity

BASE_F = 43.0
# Degree days (base 43 °F, from January 1) at which each stage begins: NEWA's stage table
THRESHOLDS = (75.0, 101.0, 165.0, 199.0, 290.0, 346.0, 454.0, 580.0)

# Scaffolds' standard deviations (24–38 DD) are 2–3 days of April and May warmth in Wisconsin
MARGIN_DAYS = 3

STAGES = (
    CropStage(
        code="ST", name="Silver tip", description="Bud scales separate and the silvery leaf tissue shows at the tip."
    ),
    CropStage(code="GT", name="Green tip", description="Green leaf tissue shows at the bud tip."),
    CropStage(code="HIG", name="Half-inch green", description="Leaves stand out about half an inch from the bud."),
    CropStage(code="TC", name="Tight cluster", description="The flower buds are visible, still tightly grouped."),
    CropStage(code="P", name="Pink", description="The flower buds have separated and show pink before opening."),
    CropStage(code="B", name="Bloom", description="Flowers open, from the first king blossoms to full bloom."),
    CropStage(code="PF", name="Petal fall", description="Most petals have fallen."),
    CropStage(code="FS", name="Fruit set", description="Fruitlets are set and growing (NEWA's post petal fall)."),
)

SPEC = ModelSpec(
    id="apple-stages",
    name="Apple bud and bloom stages",
    group="crop",
    version="0.1",
    status="beta",
    summary="Apple's stages from silver tip to fruit set, by degree days (base 43 °F) from January 1, at the thresholds NEWA uses.",
    topics=("apple",),
    crops=("apple",),
    checks=(
        Check(
            kind="published",
            against="McIntosh stages at Geneva, New York, over about 26 years (Cornell's Scaffolds Fruit Journal)",
            result="Each of the eight stages begins at a degree-day total inside the range in which McIntosh reached that stage at Geneva. Bloom, for example, begins at 346 degree days (base 43 °F from January 1), against Geneva's range of 345 to 417.",
            report="docs/validation/models/apple-stages.md#against-its-sources-numbers",
        ),
        Check(
            kind="system",
            against="NEWA's apple stages on the weather of 36 Wisconsin orchard stations, 2024–2026",
            result="On the same weather, each stage begins on the same day as NEWA's in 95 to 102 of 103 station-seasons, and never more than 2 days apart. The small differences come from NEWA's slightly different degree-day formula.",
            report="docs/validation/models/apple-stages.md#against-newa-on-the-same-weather",
        ),
        Check(
            kind="observations",
            against="Apple stages observed at research stations and orchards in Wisconsin, 2023–2026 (UW–Madison's fruit program, growers)",
            result="The model gave the observed stage on 41 of 57 dated observations, and was within 3 days on 46. Early cultivars such as Zestar ran a mean of 2.8 days ahead of the model, which follows McIntosh's timing.",
            report="docs/validation/models/apple-stages.md#against-stages-observed-in-wisconsin",
        ),
    ),
    citations=(
        Citation(
            text="NEWA, Network for Environment and Weather Applications, Cornell University: apple phenological stages (base 43 °F, Baskerville–Emin, from January 1).",
            url="https://newa.cornell.edu/",
        ),
        Citation(
            text="Agnello, A. (ed.) (2015). Scaffolds Fruit Journal 24 (3–8), Upcoming pest events: McIntosh stages at Geneva, New York, degree days base 43 °F from January 1. Cornell University.",
            url="http://web.archive.org/web/2015id_/http://www.scaffolds.entomology.cornell.edu/2015/5-4MD.pdf",
        ),
        Citation(
            text="Baskerville, G. L. and Emin, P. (1969). Rapid estimation of heat accumulation from maximum and minimum temperatures. Ecology 50, 514–517.",
            doi="10.2307/1933912",
        ),
    ),
    inputs=(
        Input(name="air_temperature_min", label="Minimum temperature", unit="degC"),
        Input(name="air_temperature_max", label="Maximum temperature", unit="degC"),
    ),
    outputs=(
        Quantity(name="stage", label="Bud stage", unit="index", description="Index in the crop's stage list"),
        Quantity(name="dd_total", label="Degree days since January 1 (base 43 °F)", unit="degF_day"),
        Quantity(name="dd", label="Degree days (base 43 °F)", unit="degF_day"),
    ),
    risk=None,
    explorer=(
        ExplorerInput(
            name="dd_total",
            label="Degree days since January 1 (base 43 °F)",
            unit="degF_day",
            minimum=0,
            maximum=800,
            step=5,
            default=200,
        ),
    ),
    sweep={"dd_total": tuple(float(d) for d in range(0, 801, 10))},
    season=("03-01", "06-30"),
    biofix=Biofix(default="01-01", label="January 1"),
    ingredients=(Ingredient(name="dd", unit="degF_day", degree_days=DegreeDays(method="sine", base_f=BASE_F)),),
    accumulations=(Accumulation(name="dd_total", of="dd"),),
    changelog=(Change(version="0.1", date="2026-11-18", note="First version."),),
)


def stages(**options: str) -> tuple[CropStage, ...]:
    return STAGES


def stage_thresholds(**options: str) -> np.ndarray:
    """Degree days since January 1 at which each stage starts (`dd_total`)."""
    return np.array(THRESHOLDS)


def ingredients(inputs: Mapping[str, np.ndarray]) -> dict[str, np.ndarray]:
    lo, hi = (np.asarray(inputs[k], dtype=float) * 1.8 + 32 for k in ("air_temperature_min", "air_temperature_max"))
    return {"dd": degree_days_sine(lo, hi, BASE_F)}


def finish(values: Mapping[str, np.ndarray], **options: str) -> dict[str, np.ndarray]:
    total = values["dd_total"]
    return {"stage": stage_reached(total, THRESHOLDS), "dd_total": total, "dd": values["dd"]}


def outputs(inputs: Mapping[str, np.ndarray], biofix_index: int = 0, **options: str) -> dict[str, np.ndarray]:
    return finished(
        accumulations=SPEC.accumulations,
        values=ingredients(inputs),
        inputs=inputs,
        biofix_index=biofix_index,
        finish=finish,
        options=options,
    )


def explore(dd_total: float) -> dict[str, float]:
    return {"stage": float(stage_reached(dd_total, THRESHOLDS))}
