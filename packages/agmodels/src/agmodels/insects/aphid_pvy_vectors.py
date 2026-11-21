"""Aphid vectors of potato virus Y: the risk of PVY spread by winged aphids, read off a curve fitted to Wisconsin's
suction trap catches (Bradford and Groves, unpublished; D36's fitted stages), by degree days or by the calendar (D101).

The fit (`tmp/R/pvy-model/pvy-model-v3.R`, 2026-11-21; v2 of 2026-11-18 replaced the 2019/2024 two-stage method):
each trap-week's risk index is the sum over PVY vector species of log(1 + count) × efficiency, the species'
transmission efficiency from the literature (v2 weighted by asin(√efficiency), a transform for analyzing proportions,
not a weight); a Tweedie GAM of that index on degree days 39.2/86 °F (single sine, from January 1) at the midpoint of
each collection week, with each year's own curve, trap and trap-season effects (REML), on 955 trap-dates at 8
Wisconsin traps, 2016–2023 (EDDMapS, the suction trap network), on AgWeather v2's weather; and the same model on the
day of year at each week's midpoint. `aphid_pvy_vectors_fit.csv` is the typical year's curve (random effects at zero)
on the log scale every 10 degree days over the data's range, 290 to 5,490, and `aphid_pvy_vectors_fit_calendar.csv`
every day from 123 to 293 (May 3 to October 20); before them the risk is 0, after them held until fall freezes.
"""

import csv
from pathlib import Path

from agmodels.phenology import FittedStage, Insect
from agmodels.spec import Change, Check, Citation, TrainingArea

FIT = Path(__file__).with_name("aphid_pvy_vectors_fit.csv")
FIT_CALENDAR = Path(__file__).with_name("aphid_pvy_vectors_fit_calendar.csv")


def _read(path: Path, x: str) -> tuple[tuple[float, ...], tuple[float, ...]]:
    with path.open() as f:
        rows = [(float(r[x]), float(r["log_risk"])) for r in csv.DictReader(f)]
    xs, values = zip(*rows, strict=True)
    return xs, values


_dd, _log_risk = _read(FIT, "gdd")
_days, _log_risk_by_day = _read(FIT_CALENDAR, "day_of_year")

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
            days=_days,
            log_count_by_day=_log_risk_by_day,
            transform="log",
            weight=1,
        ),
    ),
    source="VDIFN",
    version="0.3",
    trained=TrainingArea(description="catches in Wisconsin's suction traps", years=(2016, 2023), states=("WI",)),
    changelog=(
        Change(
            version="0.2",
            date="2026-11-18",
            note="Rebuilt on a refit of the suction trap analysis (one Tweedie GAM with year, trap and trap-season effects, on AgWeather v2's weather at 39.2/86 °F): risk rises through midsummer to a peak near 3,580 degree days. VDIFN's window (1,838 to 3,228, peaking at 2,515) had read the old fit's crossing of its sample mean as the peak and ended before the old fit's own peak at 3,266.",
        ),
        Change(
            version="0.3",
            date="2026-11-21",
            note="Each aphid species now counts in proportion to how well it transmits the virus (the curve had used a transformed efficiency, which narrowed the gap between good and poor vectors): the peak moves from about 3,580 to 3,490 degree days. Adds the same curve by calendar date, as an option.",
        ),
    ),
    checks=(
        Check(
            kind="published",
            against="The refitted suction trap analysis behind the model (Bradford and Groves, unpublished), and its year-by-year stability",
            result="The model's curve keeps the fit's peak at 3,488 degree days and its 50 and 90 percent points within 10 degree days, and the calendar curve's peak on August 22. Refitting with each year left out moved the peak between 3,297 and 3,721 degree days, or between days 232 and 237. The curves are fitted to the same trap data, so this shows the model carries the analysis over faithfully and how much it depends on single years.",
            report="docs/validation/models/aphid-pvy-vectors.md#against-the-fit",
        ),
        Check(
            kind="observations",
            against="Wisconsin suction trap seasons, 2016–2023, with each year or trap left out of the fit",
            result="Degree days timed the start of a held-out season's catch (its first 10 percent) about 2 days better than the calendar (17.1 against 18.8 days root mean square error); at 50 and 90 percent of the catch they did no better (16.9 and 10.0 days against 17.0 and 11.5).",
            report="docs/validation/models/aphid-pvy-vectors.md#base-temperature-and-timing-on-years-left-out-2026-11-19",
        ),
        Check(
            kind="system",
            against="VDIFN's PVY vector model, which this model replaces",
            result="VDIFN's risk window ran from 1,838 to 3,228 degree days and peaked at 2,515, which was where the old fit crossed its average, not its peak. On the refitted curve, risk at 2,515 is about 64 percent of the peak and still rising.",
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
