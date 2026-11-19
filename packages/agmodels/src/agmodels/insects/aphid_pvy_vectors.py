"""Aphid vectors of potato virus Y: the risk of PVY spread by winged aphids, read off a curve fitted to Wisconsin's
suction trap catches (Bradford and Groves, unpublished; D36's fitted stages).

The fit (`tmp/R/pvy_model/pvy-model-v2.R`, refitted 2026-11-18 at Ben's request, replacing the 2019/2024 two-stage
method): each trap-week's risk index is the sum over PVY vector species of log(1 + count) × asin(√efficiency), the
species' transmission efficiency from the literature; a Tweedie GAM of that index on degree days 39.2/86 °F (single
sine, from January 1) at the midpoint of each collection week, with each year's own curve, trap and trap-season
effects (REML), on 955 trap-dates at 8 Wisconsin traps, 2016–2023 (EDDMapS, the suction trap network), on AgWeather
v2's weather. `aphid_pvy_vectors_fit.csv` is the typical year's curve (random effects at zero) on the log scale,
every 10 degree days over the data's range, 290 to 5,490; before it the risk is 0, after it held until fall freezes.
"""

import csv
from pathlib import Path

from agmodels.phenology import FittedStage, Insect
from agmodels.spec import Change, Check, Citation

FIT = Path(__file__).with_name("aphid_pvy_vectors_fit.csv")


def _fit() -> tuple[tuple[float, ...], tuple[float, ...]]:
    with FIT.open() as f:
        rows = [(float(r["gdd"]), float(r["log_risk"])) for r in csv.DictReader(f)]
    dd, values = zip(*rows, strict=True)
    return dd, values


_dd, _log_risk = _fit()

INSECT = Insect(
    id="aphid-pvy-vectors",
    name="Aphid PVY vectors",
    crops=("potato",),
    base_f=39.2,
    upper_f=86,
    biofix="01-01",
    biofix_label="January 1",
    life_stages=(
        FittedStage(
            label="PVY vector pressure",
            count_label="PVY risk index (typical year)",
            dd=_dd,
            log_count=_log_risk,
            transform="log",
            weight=1,
        ),
    ),
    source="VDIFN",
    version="0.2",
    changelog=(
        Change(
            version="0.2",
            date="2026-11-18",
            note="Rebuilt on a refit of the suction trap analysis (one Tweedie GAM with year, trap and trap-season effects, on AgWeather v2's weather at 39.2/86 °F): risk rises through midsummer to a peak near 3,580 degree days. VDIFN's window (1,838 to 3,228, peaking at 2,515) had read the old fit's crossing of its sample mean as the peak and ended before the old fit's own peak at 3,266.",
        ),
    ),
    checks=(
        Check(
            kind="published",
            against="The refitted suction trap analysis behind the model (Bradford and Groves, unpublished), and its year-by-year stability",
            result="The model's curve keeps the fit's peak at 3,582 degree days and its 50 and 90 percent points within 10 degree days. Refitting with each year left out moved the peak between 3,370 and 3,788. The curve is fitted to the same trap data, so this shows the model carries the analysis over faithfully and how much it depends on single years, not how well it predicts new years.",
            report="docs/validation/models/aphid-pvy-vectors.md#against-the-fit",
        ),
        Check(
            kind="system",
            against="VDIFN's PVY vector model, which this model replaces",
            result="VDIFN's risk window ran from 1,838 to 3,228 degree days and peaked at 2,515, which was where the old fit crossed its average, not its peak. On the refitted curve, risk at 2,515 is about 63 percent of the peak and still rising, and VDIFN's window closed before the peak.",
            report="docs/validation/models/aphid-pvy-vectors.md#against-vdifn",
        ),
    ),
    citations=(
        Citation(
            text="Bradford, B. Z. and Groves, R. L. Aphid-vectored PVY risk by degree days from Wisconsin suction trap catches, 2016–2023. Vegetable Entomology Lab, UW–Madison, unpublished analysis (refitted 2026)."
        ),
        Citation(
            text="Suction trap aphid records, 2016–2023, submitted to EDDMapS by Doris Lagos-Kutz, University of Illinois Urbana-Champaign.",
            url="https://www.eddmaps.org/",
        ),
    ),
)
