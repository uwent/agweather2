"""Spotted wing drosophila: adult activity through the season, read off a curve fitted to weekly trap catches in Door
County tart cherry orchards (Kamiyama et al. 2020's data; D36's fitted stages).

The fit (`tmp/R/kamiyama_2020_drosophila/swd-refit.R`, 2026-11-19): a negative binomial GAM (log link, REML) of each
trap's weekly catch on degree days 45/86 °F (7.2/30 °C, single sine, from January 1) at the midpoint of its
collection week, with each year's own curve, trap and trap-season effects, zeros kept; 772 trap-weeks at 13 traps in
four orchards, 2015–2018, on AgWeather v2's weather (the archive from 2016; gridMET on the archive's basis for 2015).
`spotted_wing_drosophila_fit.csv` is the typical year's curve (random effects at zero) on the log scale, every 10
degree days over the data's range, 180 to 3,050; before it activity is 0, after it held until fall freezes or the season's end (October 31).

Version 0.1 was VDIFN's ramp (1276, 3180, 4000) on 45/86 °F. Those numbers came from the paper, whose degree days
were computed as a modified average with base 39 °F (gdd_script.r), not the 7.2 °C its methods state, so they ran
about 1.5 times AgWeather's: the paper's peak at 3,180 is about 2,340 at 45/86 °F, where the refit peaks too.
"""

import csv
from pathlib import Path

from agmodels.phenology import FittedStage, Insect
from agmodels.spec import Change, Check, Citation

FIT = Path(__file__).with_name("spotted_wing_drosophila_fit.csv")


def _fit() -> tuple[tuple[float, ...], tuple[float, ...]]:
    with FIT.open() as f:
        rows = [(float(r["gdd"]), float(r["log_count"])) for r in csv.DictReader(f)]
    dd, values = zip(*rows, strict=True)
    return dd, values


_dd, _log_count = _fit()

INSECT = Insect(
    id="spotted-wing-drosophila",
    name="Spotted wing drosophila",
    season=("06-01", "10-31"),
    opens="calendar",
    crops=("blackberry", "cherry", "raspberry"),
    base_f=45,
    upper_f=86,
    biofix="01-01",
    biofix_label="January 1",
    life_stages=(
        FittedStage(
            label="Adult activity",
            count_label="Flies per trap per week (typical year)",
            dd=_dd,
            log_count=_log_count,
            transform="log",
            weight=1,
        ),
    ),
    source="Kamiyama et al. 2020, refitted",
    version="0.3",
    changelog=(
        Change(
            version="0.2",
            date="2026-11-19",
            note="Rebuilt on a refit of Kamiyama et al. 2020's trap counts on AgWeather v2's weather at 45/86 °F (one negative binomial GAM with year, trap and trap-season effects): activity peaks near 2,330 degree days. VDIFN's window (1,276 to 4,000, peaking at 3,180) took the paper's numbers, which were computed at base 39 °F by a modified average and run about 1.5 times AgWeather's 45/86 °F, so its peak came weeks after the flies' and isn't reached in Door County in an average year.",
        ),
        Change(
            version="0.3",
            date="2026-11-26",
            note="In season from June 1 to October 31: from a week before its earliest activity on 2016–2025's weather at six Wisconsin places to October 31, the end of Wisconsin's growing season. Activity ends after October 31 whatever the weather, as fall freezes end it, so a mild fall no longer holds a stalled curve's activity into winter.",
        ),
    ),
    checks=(
        Check(
            kind="published",
            against="The refit of Kamiyama et al. 2020's trap counts behind the model, and its year-by-year stability",
            result="The model's curve keeps the fit's peak at 2,334 degree days and its 50 and 90 percent points within 10 degree days. Refitting with each year left out moved the peak between 2,297 and 2,394. The curve is fitted to the same trap data, so this shows the model carries the analysis over faithfully and how much it depends on single years, not how well it predicts new years or other crops.",
            report="docs/validation/models/spotted-wing-drosophila.md#against-the-fit",
        ),
        Check(
            kind="published",
            against="Kamiyama et al. 2020's published peak, converted to AgWeather's degree days",
            result="The paper put the peak at 3,180 degree days, computed with a base of 39 °F by a modified average rather than at the 45 °F it states. On AgWeather's 45/86 °F at the same traps that's 2,340, within 10 degree days of the refit's peak at 2,334.",
            report="docs/validation/models/spotted-wing-drosophila.md#against-the-paper",
        ),
        Check(
            kind="system",
            against="VDIFN, the vegetable disease and insect forecasting tool this model replaces",
            result="VDIFN's window ran from 1,276 to 4,000 degree days and peaked at 3,180, the paper's numbers read on a scale they weren't computed on. On the refitted curve, activity at VDIFN's start is 13 percent of the peak, and at Sturgeon Bay VDIFN's peak was reached by October 31 in only 9 of 27 years.",
            report="docs/validation/models/spotted-wing-drosophila.md#against-vdifn",
        ),
    ),
    citations=(
        Citation(
            text="Kamiyama, M. T., Bradford, B. Z., Groves, R. L. and Guédot, C. (2020). Degree day models to forecast the seasonal phenology of Drosophila suzukii in tart cherry orchards in the Midwest U.S. PLOS ONE 15(4), e0227726. AgWeather's model is refit from the study's original trap counts on AgWeather's weather.",
            doi="10.1371/journal.pone.0227726",
        ),
        Citation(
            text="Tochen, S., Dalton, D. T., Wiman, N., Hamm, C., Shearer, P. W. and Walton, V. M. (2014). Temperature-related development and population parameters for Drosophila suzukii (Diptera: Drosophilidae) on cherry and blueberry. Environmental Entomology 43(2), 501–510.",
            doi="10.1603/EN13200",
        ),
    ),
)
