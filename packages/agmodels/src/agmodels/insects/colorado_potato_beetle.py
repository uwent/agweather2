"""Colorado potato beetle: adults, egg masses and larvae read off curves fitted to a decade of Wisconsin scouting
counts (Bradford and Groves, unpublished; D36's fitted stages), by degree days or by the calendar (D101).

The fits are GAMs (`y ~ s(x, bs = "cs")`, k = 13; egg masses k = 11) of log(count + 1) on Pest Pros' field scouting
data, 2014–2025: adults and larvae per 25 sweeps of a standard net in the canopy, egg masses per 10 plants. Since 0.3
(`tmp/R/cpb/cv/10_cpb_cv.R` with `COUNT_RULE=mean`, exported by `cv/30_export.py`): each visit's count is the mean of
the scout's main count and the edge and patch counts recorded with it, a blank main count taken as 0 (Ben, 2026-11-21;
0.2's fit used the main count alone and dropped 1,681 rows with only edge or patch counts), and the degree days are
the archive's, 52/86 °F single sine from January 1, where 0.2's were gridMET's (31 above the archive at the fields).
`colorado_potato_beetle_fit.csv` holds the curves every 10 degree days and `colorado_potato_beetle_fit_calendar.csv`
the same fits on the day of year, each over its rows' 0.1–99.9 % range: 0 before, held after until fall freezes end
the season, or its season does (September 30). The adults and larvae curve is its own fit to each field date's adults plus larvae.
"""

import csv
from pathlib import Path

from agmodels.phenology import FittedStage, Insect
from agmodels.spec import Change, Check, Citation, OpensOnCropStage, TrainingArea

FIT = Path(__file__).with_name("colorado_potato_beetle_fit.csv")
FIT_CALENDAR = Path(__file__).with_name("colorado_potato_beetle_fit_calendar.csv")


def _read(path: Path, x: str, column: str) -> tuple[tuple[float, ...], tuple[float, ...]]:
    """A curve's (x, log(count + 1)) where it has values (each stage over its own data's range)."""
    with path.open() as f:
        rows = [(float(r[x]), float(r[column])) for r in csv.DictReader(f) if r[column]]
    xs, values = zip(*rows, strict=True)
    return xs, values


def _stage(*, label: str, count_label: str, column: str, weight: float) -> FittedStage:
    dd, log_count = _read(FIT, "gdd", column)
    days, by_day = _read(FIT_CALENDAR, "day_of_year", column)
    return FittedStage(
        label=label,
        count_label=count_label,
        dd=dd,
        log_count=log_count,
        days=days,
        log_count_by_day=by_day,
        weight=weight,
    )


# The scouted fields' counties with at least 10 fields (1,924 of 1,937 fields; Adams, Waushara and Portage hold 85 %)
CENTRAL_WISCONSIN = (
    "55001",  # Adams
    "55137",  # Waushara
    "55097",  # Portage
    "55077",  # Marquette
    "55135",  # Waupaca
    "55111",  # Sauk
    "55049",  # Iowa
    "55057",  # Juneau
    "55141",  # Wood
    "55021",  # Columbia
    "55073",  # Marathon
    "55103",  # Richland
)

INSECT = Insect(
    id="colorado-potato-beetle",
    name="Colorado potato beetle",
    season=("05-01", "09-30"),
    opens=OpensOnCropStage(crop="potato-stages", stage="EM", event="early-planted potatoes emerge", planting="early"),
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
    version="0.5",
    trained=TrainingArea(
        description="scouting counts in commercial potato fields in central Wisconsin, mostly the Central Sands",
        years=(2014, 2025),
        counties=CENTRAL_WISCONSIN,
    ),
    changelog=(
        Change(
            version="0.2",
            date="2026-11-18",
            note="Rebuilt on the scouting fits themselves (adults, egg masses, larvae, and adults and larvae together) on degree days 52/86 °F, where the Crop Risk Tool used a rounded step table of them on 50/86 °F. Replaces the separate adults and larvae models.",
        ),
        Change(
            version="0.3",
            date="2026-11-21",
            note="Refitted on AgWeather's own degree days (the fit had used another weather source's, which ran about 30 degree days higher) and on every scouting record, each visit's count the mean of the field, edge and patch counts the scout recorded. Events come 5 to 80 degree days earlier: colonization at about 205, the larval peak at 735, and counts run higher with the edge counts in. Adds the same curves by calendar date, as an option.",
        ),
        Change(
            version="0.4",
            date="2026-11-26",
            note="In season from May 1 to September 30: from a week before its earliest activity on 2016–2025's weather at six Wisconsin places to the end of September, when the scouting data end and potato vines are killed. Activity ends after September 30 whatever the weather, as fall freezes end it, so a mild fall no longer holds a stalled curve's activity into winter.",
        ),
        Change(
            version="0.5",
            date="2026-11-26",
            note="The season opens at each place on the day early-planted potatoes emerge in a typical year (from the 30-year normal temperatures, averaged over about 50 km), rather than on May 1 everywhere; where we don't have the normals, it still opens on May 1.",
        ),
    ),
    checks=(
        Check(
            kind="published",
            against="The events of the scouting analysis's refit behind the model (Bradford and Groves, unpublished)",
            result="Every event of the four degree-day curves falls within 10 degree days of the refit's own, and every calendar event within a day: colonization at 203 degree days (May 22 on the calendar) and the larval peak at 734 (July 2), for example. The curves are fitted to the same scouting data, so this shows the model carries the analysis over faithfully.",
            report="docs/validation/models/colorado-potato-beetle.md#against-the-refits-own-events",
        ),
        Check(
            kind="observations",
            against="Central Wisconsin scouting counts, 2014–2025, refitted with each year left out",
            result="Fitted without the year it was tested on, the degree-day curves timed that year's events within 3.6 to 10.2 days (root mean square error) and the calendar curves within 3.2 to 8.0 days, so in these fields the calendar did as well. The fields lie close together, so these data can't test how the timing shifts north or south, which is where degree days should do better.",
            report="docs/validation/models/colorado-potato-beetle.md#leaving-each-year-out",
        ),
        Check(
            kind="system",
            against="The Crop Risk Tool, which this model replaces, on the weather of Eau Claire, Wisconsin, 2025",
            result="Each event comes 3 to 9 days later than in the Crop Risk Tool, which used rounded values from the first analysis on degree days from a base of 50 °F rather than 52 °F.",
            report="docs/validation/models/colorado-potato-beetle.md#against-the-crop-risk-tool-on-the-same-weather",
        ),
    ),
    citations=(
        Citation(
            text="Bradford, B. Z. and Groves, R. L. Colorado potato beetle phenology from Wisconsin field scouting counts, 2014–2025 (Pest Pros data). Vegetable Entomology Lab, UW–Madison, unpublished analysis."
        ),
    ),
)
