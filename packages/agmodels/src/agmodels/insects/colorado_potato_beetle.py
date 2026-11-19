"""Colorado potato beetle: adults, egg masses and larvae read off curves fitted to a decade of Wisconsin scouting
counts (Bradford and Groves, unpublished; D36's fitted stages).

The fits are GAMs (`y ~ s(x, bs = "cs")`, k = 13; egg masses k = 11) of log(count + 1) on degree days 52/86 °F
(single sine) from January 1, on Pest Pros' field scouting data, 2014–2025: adults and larvae per 25 sweeps of a
standard net in the canopy, egg masses per 10 plants, each a field's mean over several sites on a date. Their
predicted values every 10 degree days are `colorado_potato_beetle_fit.csv` (Ben, 2026-11-18); the data end at
2,311 degree days, so the curves are read to 2,310 and held there until fall freezes end the season. The adults and
larvae curve is its own fit to each field date's adults plus larvae (refitted 2026-11-18: the first stacked the two
stages' rows), so it tracks the log of the other two curves' counts summed.
"""

import csv
from pathlib import Path

from agmodels.phenology import FittedStage, Insect
from agmodels.spec import Change, Check, Citation

FIT = Path(__file__).with_name("colorado_potato_beetle_fit.csv")
END_OF_DATA_DD = 2311  # the largest total in the scouting data (the fits' "end of season")


def _fit(column: str) -> tuple[tuple[float, ...], tuple[float, ...]]:
    """The fit's (degree days, log(count + 1)) to the end of the data."""
    with FIT.open() as f:
        rows = [(float(r["gdd"]), float(r[column])) for r in csv.DictReader(f) if float(r["gdd"]) <= END_OF_DATA_DD]
    dd, values = zip(*rows, strict=True)
    return dd, values


def _stage(*, label: str, count_label: str, column: str, weight: float) -> FittedStage:
    dd, log_count = _fit(column)
    return FittedStage(label=label, count_label=count_label, dd=dd, log_count=log_count, weight=weight)


INSECT = Insect(
    id="colorado-potato-beetle",
    name="Colorado potato beetle",
    crops=("potato", "tomato", "eggplant"),
    base_f=52,
    upper_f=86,
    biofix="01-01",
    biofix_label="January 1",
    life_stages=(
        _stage(
            label="Adults and larvae",
            count_label="Adults and larvae per 25 sweeps (typical count)",
            column="adults_larvae",
            weight=1,
        ),
        _stage(label="Adults", count_label="Adults per 25 sweeps (typical count)", column="adults", weight=0),
        _stage(label="Egg masses", count_label="Egg masses per 10 plants (typical count)", column="eggs", weight=0),
        _stage(label="Larvae", count_label="Larvae per 25 sweeps (typical count)", column="larvae", weight=0),
    ),
    source="the Crop Risk Tool",
    version="0.2",
    changelog=(
        Change(
            version="0.2",
            date="2026-11-18",
            note="Rebuilt on the scouting fits themselves (adults, egg masses, larvae, and adults and larvae together) on degree days 52/86 °F, where the Crop Risk Tool used a rounded step table of them on 50/86 °F. Replaces the separate adults and larvae models.",
        ),
    ),
    checks=(
        Check(
            kind="published",
            against="The critical points of the scouting analysis behind the model (Bradford and Groves, unpublished)",
            result="Every critical point of the four curves the model reads (first appearance, peaks and lows) falls within 10 degree days of the analysis's own: colonization at 210 and the second-generation adult peak at 1,480 against 1,477, for example. The curves are fitted to the same scouting data, so this shows the model carries the analysis over faithfully, not how well it predicts other years.",
            report="docs/validation/models/colorado-potato-beetle.md#against-the-analysiss-own-critical-points",
        ),
        Check(
            kind="system",
            against="The Crop Risk Tool, which this model replaces, on the weather of Eau Claire, Wisconsin, 2025",
            result="Each event comes 3 to 9 days later than in the Crop Risk Tool, which used rounded values from the same analysis on degree days from a base of 50 °F rather than the analysis's 52 °F.",
            report="docs/validation/models/colorado-potato-beetle.md#against-the-crop-risk-tool-on-the-same-weather",
        ),
    ),
    citations=(
        Citation(
            text="Bradford, B. Z. and Groves, R. L. Colorado potato beetle phenology from Wisconsin field scouting counts, 2014–2025 (Pest Pros data). Vegetable Entomology Lab, UW–Madison, unpublished analysis."
        ),
    ),
)
