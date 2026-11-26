"""Green peach aphid: winged green peach aphids' flight through the season, read off curves fitted to Wisconsin's
suction trap catches (Bradford and Groves, unpublished; D36's fitted stages), by calendar date or degree days (D101).

The fit (`tmp/R/cpb/cv/20_aphids.R`, 2026-11-19; findings in `tmp/R/cpb/report-cv-aphids.md`): *Myzus persicae* in
the suction traps' EDDMapS records (Doris Lagos-Kutz), a sampled trap-week without the species counted as 0, each
catch at the midpoint of its week; a Tweedie GAM (`bam`, fREML) of the count on the day of year, and another on degree
days 39.2/86 °F (single sine, from January 1), with year, trap and trap-season effects, on 1,345 trap-weeks at 9
Wisconsin traps in 2010 and 2014–2023 (2011–2013 have no usable weather). The typical year's curves (random effects at
zero) on the log scale are `green_peach_aphid_fit_calendar.csv` (days 123–312, May 3 to November 8) and
`green_peach_aphid_fit.csv` (280–5,680 degree days, every 10), exported by `tmp/R/cpb/cv/31_aphid_models.py`. The
calendar is the default: with each year or trap left out, it described the catches better than degree days at every
base tried, as the late-summer flight follows the season (host plants maturing, shorter days, migrants from the south)
more than local warmth.
"""

import csv
from pathlib import Path

from agmodels.phenology import FittedStage, Insect
from agmodels.spec import Change, Check, Citation, TrainingArea

FIT = Path(__file__).with_name("green_peach_aphid_fit.csv")
FIT_CALENDAR = Path(__file__).with_name("green_peach_aphid_fit_calendar.csv")


def _read(path: Path, x: str) -> tuple[tuple[float, ...], tuple[float, ...]]:
    with path.open() as f:
        rows = [(float(r[x]), float(r["log_mean"])) for r in csv.DictReader(f)]
    xs, values = zip(*rows, strict=True)
    return xs, values


_dd, _log_dd = _read(FIT, "gdd")
_days, _log_days = _read(FIT_CALENDAR, "day_of_year")

INSECT = Insect(
    id="green-peach-aphid",
    name="Green peach aphid",
    season=("07-15", "10-31"),
    crops=("potato",),
    topic="aphids-on-potato",
    base_f=39.2,
    upper_f=86,
    biofix="01-01",
    biofix_label="January 1",
    life_stages=(
        FittedStage(
            label="Winged adults",
            count_label="Green peach aphids per suction trap per week (typical catch)",
            dd=_dd,
            log_count=_log_dd,
            days=_days,
            log_count_by_day=_log_days,
            transform="log",
            weight=1,
        ),
    ),
    clock="calendar",
    source="UW–Madison Vegetable Entomology",
    version="0.2",
    trained=TrainingArea(description="catches in Wisconsin's suction traps", years=(2010, 2023), states=("WI",)),
    changelog=(
        Change(
            version="0.1",
            date="2026-11-21",
            note="New: the typical season's flight of winged green peach aphids, from Wisconsin's suction trap catches, by calendar date or degree days.",
        ),
        Change(
            version="0.2",
            date="2026-11-26",
            note="In season from July 15 to October 31: from a week before its earliest activity on 2016–2025's weather at six Wisconsin places to October 31, the end of Wisconsin's growing season. Activity ends after October 31 whatever the weather, as fall freezes end it, so a mild fall no longer holds a stalled curve's activity into winter.",
        ),
    ),
    checks=(
        Check(
            kind="published",
            against="The suction trap analysis behind the model (Bradford and Groves, unpublished)",
            result="The model's curves keep the fit's peak on September 1 (day 244) and at 3,410 degree days, and its rise to half the peak on August 21 and at 2,900 degree days. The curves are fitted to the same trap data, so this shows the model carries the analysis over faithfully.",
            report="docs/validation/models/green-peach-aphid.md#against-the-fit",
        ),
        Check(
            kind="observations",
            against="Wisconsin suction trap catches, 2010 and 2014–2023, with each year or each trap left out of the fit",
            result="Fitted without the year or the trap it was tested on, the calendar curve described the held-out catches better than the degree-day curve at every base temperature tried, from 32 to 52 °F. Neither clock could time a single trap's season: their errors were about 30 to 35 days either way.",
            report="docs/validation/models/green-peach-aphid.md#leaving-years-and-traps-out",
        ),
    ),
    citations=(
        Citation(
            text="Bradford, B. Z. and Groves, R. L. Green peach aphid and potato aphid seasonal curves from Wisconsin suction traps and field scouting, 2010–2025. Vegetable Entomology Lab, UW–Madison, unpublished analysis (2026)."
        ),
        Citation(
            text="Suction trap aphid records, 2010–2023, submitted to EDDMapS by Doris Lagos-Kutz, University of Illinois Urbana-Champaign.",
            url="https://www.eddmaps.org/",
        ),
    ),
)
