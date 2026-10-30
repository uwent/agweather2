"""Alfalfa growth since spring or the last cutting, by growing degree days (base 41 °F, upper 86 °F, single sine).

Ported from the UW alfalfa tool: GDD accumulate from January 1 in spring, or from the last cutting, and the crop is
ready to cut at 900–1100 GDD. The tool's single-sine GDD subtract the upper threshold's GDD from the base's
(`gdd_sine(41) − gdd_sine(86)`), which is D26's identity, so its values match `degree_days_sine` here; its
`gdd_sine` skips the upper cutoff when the minimum is above the base, but only for its default upper of 150 °F, which
no day reaches.

Fall cutting (the tool's other guidance, and its cut scheduling) depends on the first killing freeze still ahead: a
last cut should leave either under 360 or over 900 GDD (base 41 °F) before it (Newell, from Quebec work reported in
base 5 °C; the older 500 and 200 were a misquote of it; the tool's text says 800). That needs the climatology and the
projection to the end of the year (Phase 3 C, Phase 6), so it waits for them.
"""

from collections.abc import Mapping

import numpy as np

from agmodels.accumulate import running_total
from agmodels.crops import CropStage, stage_reached
from agmodels.degree_days import degree_days_sine
from agmodels.spec import Biofix, Change, Citation, ExplorerInput, ModelSpec, Quantity

BASE_F, UPPER_F = 41.0, 86.0
CUT_FROM, CUT_UNTIL = 900.0, 1100.0
MARGIN_DAYS = 0  # no disease is gated on alfalfa's stages yet

STAGES = (
    CropStage(code="Regrowth", name="Growing", description="Regrowing since spring green-up or the last cutting."),
    CropStage(
        code="Cut",
        name="Ready to cut",
        description="900–1100 GDD since spring or the last cutting: the window for cutting.",
    ),
    CropStage(
        code="Late",
        name="Past the cut window",
        description="Over 1100 GDD: forage quality declines as the crop matures.",
    ),
)
THRESHOLDS = np.array([0.0, CUT_FROM, CUT_UNTIL])

SPEC = ModelSpec(
    id="alfalfa-growth",
    name="Alfalfa growth since cutting",
    group="crop",
    version="0.1",
    status="beta",
    summary="Growing degree days (base 41 °F, upper 86 °F) since spring or the last cutting, and when alfalfa is "
    "ready to cut (900–1100 GDD).",
    topics=("alfalfa",),
    crops=("Alfalfa",),
    citations=(
        Citation(
            text="Newell, S. Managing fall alfalfa cutting for persistence. UW–Madison Extension Crops and Soils "
            "(written with the UW alfalfa cutting tool, whose 900–1100 GDD cutting window this follows).",
            url="https://cropsandsoils.extension.wisc.edu/articles/managing-fall-alfalfa-cutting-for-persistence/",
        ),
        Citation(
            text="Iowa State University Extension: Should I take a late fall alfalfa cutting? (the 900 and 360 GDD "
            "rule).",
            url="https://crops.extension.iastate.edu/post/should-i-take-late-fall-alfalfa-cutting-it-too-late-or-warm",
        ),
        Citation(
            text="UW–Madison Extension: Timing of fall alfalfa harvest can impact long-term viability of the stand.",
            url="https://cropsandsoils.extension.wisc.edu/timing-of-fall-alfalfa-harvest-can-impact-long-term-viability-of-the-stand",
        ),
    ),
    inputs=(
        Quantity(name="air_temperature_min", label="Minimum temperature", unit="degC"),
        Quantity(name="air_temperature_max", label="Maximum temperature", unit="degC"),
    ),
    outputs=(
        Quantity(name="stage", label="Growth stage", unit="index", description="Index in the crop's stage list"),
        Quantity(name="gdd_total", label="GDD (41/86 °F) since spring or the last cutting", unit="degF_day"),
        Quantity(name="gdd", label="GDD (41/86 °F, single sine)", unit="degF_day"),
    ),
    risk=None,
    explorer=(
        ExplorerInput(
            name="gdd_total",
            label="GDD since spring or the last cutting",
            unit="degF_day",
            minimum=0,
            maximum=1500,
            step=10,
            default=500,
        ),
    ),
    sweep={"gdd_total": tuple(float(g) for g in range(0, 1501, 10))},
    season=("03-01", "11-30"),
    biofix=Biofix(default="01-01", label="January 1 in spring, or the date of the last cutting"),
    changelog=(Change(version="0.1", date="2026-10-28", note="Ported from the UW alfalfa tool."),),
)


def stages(**options: str) -> tuple[CropStage, ...]:
    return STAGES


def outputs(inputs: Mapping[str, np.ndarray], biofix_index: int = 0, **options: str) -> dict[str, np.ndarray]:
    lo, hi = (np.asarray(inputs[k], dtype=float) * 1.8 + 32 for k in ("air_temperature_min", "air_temperature_max"))
    gdd = degree_days_sine(lo, hi, BASE_F, UPPER_F)
    total = running_total(gdd, biofix_index)
    return {"stage": stage_reached(total, THRESHOLDS), "gdd_total": total, "gdd": gdd}


def explore(gdd_total: float) -> dict[str, float]:
    return {"stage": float(stage_reached(gdd_total, THRESHOLDS))}
