"""Potato aphid: potato aphids in potato fields through the season, read off curves fitted to a decade of scouting
counts in central Wisconsin (Bradford and Groves, unpublished; D36's fitted stages), by degree days or calendar date
(D101).

The fit (`tmp/R/cpb/cv/20_aphids.R`, 2026-11-19; findings in `tmp/R/cpb/report-cv-aphids.md`): Pest Pros' potato aphid
counts per 25 sweeps, 2014–2025, where the scout recorded one (a blank is taken as not checked, Ben, 2026-11-21: some
scouts leave a zero blank, so blanks can't be counted as zeros); a Tweedie GAM (`bam`, fREML) of the count on degree
days 39.2/86 °F (single sine, from January 1) at each field's cell, and another on the day of year, with each year's
own curve, farm and farm-year effects. The typical year's curves (random effects at zero) on the log scale are
`potato_aphid_fit.csv` (420–4,060 degree days, every 10) and `potato_aphid_fit_calendar.csv` (days 128–257, May 8 to
September 14), exported by `tmp/R/cpb/cv/31_aphid_models.py`. Scouting ends in mid-September, before the counts
decline, so the curves are held at their last value until fall freezes end the season, or its season does
(September 30).
"""

import csv
from pathlib import Path

from agmodels.insects.colorado_potato_beetle import CENTRAL_WISCONSIN
from agmodels.phenology import FittedStage, Insect
from agmodels.spec import Change, Check, Citation, OpensOnCropStage, TrainingArea

FIT = Path(__file__).with_name("potato_aphid_fit.csv")
FIT_CALENDAR = Path(__file__).with_name("potato_aphid_fit_calendar.csv")


def _read(path: Path, x: str) -> tuple[tuple[float, ...], tuple[float, ...]]:
    with path.open() as f:
        rows = [(float(r[x]), float(r["log_mean"])) for r in csv.DictReader(f)]
    xs, values = zip(*rows, strict=True)
    return xs, values


_dd, _log_dd = _read(FIT, "gdd")
_days, _log_days = _read(FIT_CALENDAR, "day_of_year")

INSECT = Insect(
    id="potato-aphid",
    name="Potato aphid",
    season=("06-15", "09-30"),
    opens=OpensOnCropStage(crop="potato-stages", stage="EM", event="early-planted potatoes emerge", planting="early"),
    crops=("potato",),
    topic="aphids-on-potato",
    base_f=39.2,
    upper_f=86,
    biofix="01-01",
    biofix_label="January 1",
    life_stages=(
        FittedStage(
            label="Potato aphids",
            count_label="Potato aphids per 25 sweeps (typical count)",
            dd=_dd,
            log_count=_log_dd,
            days=_days,
            log_count_by_day=_log_days,
            transform="log",
            weight=1,
        ),
    ),
    source="UW–Madison Vegetable Entomology",
    version="0.3",
    trained=TrainingArea(
        description="scouting counts in commercial potato fields in central Wisconsin, mostly the Central Sands",
        years=(2014, 2025),
        counties=CENTRAL_WISCONSIN,
    ),
    changelog=(
        Change(
            version="0.1",
            date="2026-11-21",
            note="New: the typical season's potato aphid counts in central Wisconsin's potato fields, by degree days or calendar date.",
        ),
        Change(
            version="0.2",
            date="2026-11-26",
            note="In season from June 15 to September 30: from a week before its earliest activity on 2016–2025's weather at six Wisconsin places to the end of September, when the scouting data end and potato vines are killed. Activity ends after September 30 whatever the weather, as fall freezes end it, so a mild fall no longer holds a stalled curve's activity into winter.",
        ),
        Change(
            version="0.3",
            date="2026-11-26",
            note="The season opens at each place on the day early-planted potatoes emerge in a typical year (from the 30-year normal temperatures, averaged over about 50 km), rather than on June 15 everywhere; where we don't have the normals, it still opens on June 15.",
        ),
    ),
    checks=(
        Check(
            kind="published",
            against="The scouting analysis behind the model (Bradford and Groves, unpublished)",
            result="The model's curves keep the fit's first activity (10 percent of the peak) at 2,520 degree days and August 1, and its rise to half the peak at 3,360 degree days and August 30. The curves are fitted to the same scouting data, so this shows the model carries the analysis over faithfully.",
            report="docs/validation/models/potato-aphid.md#against-the-fit",
        ),
        Check(
            kind="observations",
            against="Central Wisconsin scouting counts, 2014–2025, with each year or group of farms left out of the fit",
            result="Fitted without the year it was tested on, degree days described the held-out year's counts better than the calendar in 10 of 12 years: a warm year's aphids build earlier by date. The calendar timed the season's rise as well or better: the date a held-out season reached 90 percent of its counts was 8.5 days off by degree days and 5.4 days by the calendar.",
            report="docs/validation/models/potato-aphid.md#leaving-years-and-farms-out",
        ),
    ),
    citations=(
        Citation(
            text="Bradford, B. Z. and Groves, R. L. Green peach aphid and potato aphid seasonal curves from Wisconsin suction traps and field scouting, 2010–2025. Vegetable Entomology Lab, UW–Madison, unpublished analysis (2026)."
        ),
    ),
)
