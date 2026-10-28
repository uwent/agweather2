"""Spring wheat growth stages (Haun scale) from planting, by growing degree days (Bauer et al. 1984, as NDAWN runs it).

Daily GDD (°F) are the mean of the maximum and minimum less 32 °F, with both raised to 32 °F; the maximum is capped at
70 °F until Haun stage 2.0 (395 GDD from planting) and at 95 °F after. Stages follow NDAWN's table: emergence (Haun
0.5) at 180 GDD, a leaf every 143 GDD from leaf 2, the flag leaf, boot, heading from 1567, flowering from 1739 to
1768, and watery-ripe kernels at 1825. The table gives no GDD past watery ripe, so grain fill and maturity aren't
modelled (a source for them is the next step), nor is winter wheat (D7, next session).

No published error for the dates, so the gating margin is corn's 3 days until one is found.
"""

from collections.abc import Mapping

import numpy as np

from agmodels.crops import CropStage, stage_reached
from agmodels.spec import Biofix, Change, Citation, ExplorerInput, ModelSpec, Quantity

BASE_F = 32.0
EARLY_CAP_F, LATE_CAP_F = 70.0, 95.0
EARLY_UNTIL_GDD = 395.0  # Haun 2.0
MARGIN_DAYS = 3

STAGES_GDD = (  # (Haun stage, accumulated GDD from planting, description), NDAWN's table
    ("0.5", 180, "Emergence: the first leaf is half its full length."),
    ("1.0", 252, "First leaf fully developed."),
    ("2.0", 395, "Second leaf fully developed."),
    ("3.0", 538, "Third leaf; tillers begin to emerge."),
    ("4.0", 681, "Fourth leaf fully extended."),
    ("5.0", 824, "Fifth leaf."),
    ("6.0", 967, "Sixth leaf; tillering ends."),
    ("7.0", 1110, "Seventh leaf fully extended."),
    ("7.5", 1181, "Flag leaf visible."),
    ("8.0", 1255, "Flag leaf fully emerged."),
    ("9.0", 1396, "Boot swelling begins as the flag leaf's stem elongates."),
    ("10.0", 1539, "Boot complete; awns visible at the flag leaf collar."),
    ("10.2", 1567, "Heading begins: the head starts through the flag leaf collar."),
    ("11.0", 1682, "Headed: the head clears the collar."),
    ("11.4", 1739, "Flowering begins, mid-head first."),
    ("11.6", 1768, "Flowering complete on the main stem and early tillers."),
    ("12.0", 1825, "Kernels watery ripe: kernel size set, little dry matter yet."),
)
STAGES = tuple(CropStage(f"H{code}", f"Haun {code}", text) for code, _, text in STAGES_GDD)
THRESHOLDS = np.array([gdd for _, gdd, _ in STAGES_GDD], dtype=float)

SPEC = ModelSpec(
    id="spring-wheat-stages",
    name="Spring wheat growth stages",
    group="crop",
    version="1.0",
    status="beta",
    summary="Spring wheat's Haun stages from planting through flowering and watery-ripe kernels, by growing degree "
    "days (base 32 °F).",
    topics=("spring-wheat",),
    crops=("Wheat",),
    citations=(
        Citation(
            "Bauer, A., Fanning, C., Enz, J. W. and Eberlein, C. V. (1984). Use of growing-degree days to determine "
            "spring wheat growth stages. North Dakota Cooperative Extension Service EB-37.",
        ),
        Citation(
            "NDAWN (North Dakota Agricultural Weather Network): Wheat growing degree days.",
            "https://ndawn.ndsu.nodak.edu/help-wheat-growing-degree-days.html",
        ),
    ),
    inputs=(
        Quantity("air_temperature_min", "Minimum temperature", "degC"),
        Quantity("air_temperature_max", "Maximum temperature", "degC"),
    ),
    outputs=(
        Quantity("stage", "Growth stage", "index", "Index in the crop's stage list"),
        Quantity("gdd_total", "GDD (base 32 °F) since planting", "degF_day"),
        Quantity("gdd", "GDD (base 32 °F)", "degF_day"),
    ),
    risk=None,
    explorer=(ExplorerInput("gdd_total", "GDD since planting", "degF_day", 0, 2000, 10, 800),),
    sweep={"gdd_total": tuple(float(g) for g in range(0, 2001, 10))},
    season=("03-15", "09-15"),
    biofix=Biofix("04-25", "Planting date"),
    changelog=(Change("1.0", "2026-10-28", "First version."),),
)


def stages(**options: str) -> tuple[CropStage, ...]:
    return STAGES


def outputs(inputs: Mapping[str, np.ndarray], biofix_index: int = 0, **options: str) -> dict[str, np.ndarray]:
    lo, hi = (np.asarray(inputs[k], dtype=float) * 1.8 + 32 for k in ("air_temperature_min", "air_temperature_max"))
    gdd = np.full(lo.shape, np.nan)
    total = np.full(lo.shape, np.nan)
    running = np.zeros(lo.shape[1:])
    for d in range(biofix_index, lo.shape[0]):
        cap = np.where(running < EARLY_UNTIL_GDD, EARLY_CAP_F, LATE_CAP_F)  # the cap changes once Haun 2.0 is reached
        day = (np.clip(hi[d], BASE_F, cap) + np.clip(lo[d], BASE_F, cap)) / 2 - BASE_F
        gdd[d] = day
        running = running + np.nan_to_num(day)  # a missing day adds nothing
        total[d] = running
    return {"stage": stage_reached(total, THRESHOLDS), "gdd_total": total, "gdd": gdd}


def explore(gdd_total: float) -> dict[str, float]:
    return {"stage": float(stage_reached(gdd_total, THRESHOLDS))}
