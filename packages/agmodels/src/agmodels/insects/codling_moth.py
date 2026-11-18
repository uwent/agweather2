"""Codling moth, from WSU's model (PETE) with first catch by latitude (docs/models-plan.md B4; D36, D37)."""

import numpy as np

from agmodels.phenology import ActionWindow, EstimatedBiofix, GenerationSize, Insect, LifeStage
from agmodels.spec import Check, Citation

# Jones et al. 2013: mean first catch (DD°C from January 1, 10/31 °C single sine with a horizontal cutoff) at sites
# below 400 m = 1923.387 − 73.806·lat + 0.745·lat². The quadratic's minimum (≈ 95.5 DD°C at 49.5 °N) is the plateau
# the paper describes near Washington's 96, so latitudes north of it are held there.
FIRST_CATCH_C = (1923.387, -73.806, 0.745)
PLATEAU_LAT = -FIRST_CATCH_C[1] / (2 * FIRST_CATCH_C[2])
# Wisconsin's commercial orchards catch their first moth later than Jones's research orchards (checked every day or
# two): in DATCP's trap network, 2020–2025, 71 site-years without mating disruption, first catch came at a mean
# 337 DD50/86 from January 1 (median 326, SD 129), 121 after Jones's equation at the same sites, with no trend by
# latitude inside the state (scripts/check_codling_moth_traps.py). So the default is Jones's curve shifted later by
# 120 DD°F, keeping its latitude trend (Ben, 2026-11-18); a grower's trap date replaces it.
WISCONSIN_SHIFT_F = 120.0


def jones_first_catch_dd_f(latitude: np.ndarray) -> np.ndarray:
    """Degree days (°F, base 50 °F) from January 1 to the mean first catch at a latitude (Jones et al. 2013)."""
    lat = np.minimum(np.asarray(latitude, dtype=float), PLATEAU_LAT)
    a, b, c = FIRST_CATCH_C
    return 1.8 * (a + b * lat + c * lat**2)


def first_catch_dd_f(latitude: np.ndarray) -> np.ndarray:
    """The model's default first catch: Jones et al. 2013's, shifted by Wisconsin's trap catches."""
    return jones_first_catch_dd_f(latitude) + WISCONSIN_SHIFT_F


INSECT = Insect(
    id="codling-moth",
    name="Codling moth",
    crops=("apple",),
    # The sources' method (D37): single sine with a horizontal cutoff, 50 °F and 88 °F (10 and 31.1 °C). 86 °F is
    # used instead (the shared totals' upper): on the archive it removes at most 9 DD by August 4 and 16 by October 31
    # in southwest Wisconsin, less than a summer day's degree days (Ben, 2026-11-18)
    base_f=50,
    upper_f=86,
    biofix="01-01",
    biofix_label="First moth caught in a pheromone trap; without a date, estimated from latitude",
    source="WSU's codling moth model",
    status="beta",
    life_stages=(
        # WSU's table (cumulative % flight and egg hatch every 20 DD°F after first catch, both generations; the
        # PETE model as Jones et al. 2008 run it) fitted by these curves within 3 points in both generations
        # (2026-11-18). Flight only times the eggs; the damage is larvae entering fruit, so hatch alone is risk.
        LifeStage(label="Adult flight", start=0, peak=170, end=964, weight=0),
        LifeStage(label="Egg hatch", start=246, peak=405, end=1189),
    ),
    # The table's second generation, 50 % to 50 %, for flight and hatch alike (Rock et al. 1993: 1030 start to start,
    # 1174 peak to peak); its spread is the first flight's, which the table's 1.4–1.5× wider second generation fits
    generation_dd=1084,
    # Larvae from a third flight rarely mature in the Upper Midwest (Riedl and Croft 1978)
    max_generations=2,
    action_windows=(ActionWindow(label="Protect fruit during egg hatch", stage="Egg hatch", between=(0.01, 0.95)),),
    estimated_biofix=EstimatedBiofix(event="first catch", dd_at=first_catch_dd_f),
    # Riedl and Croft 1978, Table II: the degree days from January 1 when half the larvae enter diapause (about
    # August 4 at 43–46 °N) set how much of the first generation's larvae go on to a second generation that season
    generation_size=GenerationSize(
        name="second_generation_size",
        label="Size of the second generation (1: none, 2: up to a third, 3: a third to two thirds, 4: more than two thirds, 5: a full second and a partial third)",
        on="08-04",
        bounds=(900, 1440, 1640, 1900),
    ),
    version="0.1",
    checks=(
        Check(
            kind="published",
            against="Washington State University's codling moth table, and first egg hatch in Michigan orchards",
            result="Moth flight and egg hatch follow WSU's table within 3.5 percentage points in both generations. Egg hatch begins 262 degree days after first catch, against 253 in Michigan orchards (Riedl et al. 1976).",
            report="docs/validation/models/codling-moth.md#against-its-sources-numbers",
        ),
        Check(
            kind="system",
            against="NEWA's codling moth model on the weather of 67 Wisconsin orchard stations, 2024 and 2025",
            result="Given the same first catch, our egg hatch window opens on NEWA's first spray date or the day after. Without a trap date, our estimated first catch comes a median of 6 days before NEWA's default.",
            report="docs/validation/models/codling-moth.md#against-newa-on-the-same-weather",
        ),
        Check(
            kind="observations",
            against="Wisconsin's apple pest trap network (DATCP), 2020–2025",
            result="The estimated first catch fell within a week of the first week with a catch in 50 of 71 orchard-years. The estimate was set from these same orchards, so this shows how well it fits them, not a test on new years.",
            report="docs/validation/models/codling-moth.md#first-catch-against-wisconsins-traps",
        ),
    ),
    citations=(
        Citation(
            text="Jones, V. P., Doerr, M. and Brunner, J. F. (2008). Is biofix necessary for predicting codling moth (Lepidoptera: Tortricidae) emergence in Washington State apple orchards? Journal of Economic Entomology 101, 1651–1657.",
            doi="10.1603/0022-0493(2008)101[1651:IBNFPC]2.0.CO;2",
        ),
        Citation(
            text="Jones, V. P., Hilton, R., Brunner, J. F., et al. (2013). Predicting the emergence of the codling moth, Cydia pomonella (Lepidoptera: Tortricidae), on a degree-day scale in North America. Pest Management Science 69, 1393–1398.",
            doi="10.1002/ps.3519",
        ),
        Citation(
            text="Jones, V. P. and Wiman, N. G. (2012). Modeling the interaction of physiological time, seasonal weather patterns, and delayed mating on population dynamics of codling moth, Cydia pomonella (L.) (Lepidoptera: Tortricidae). Population Ecology 54, 421–429.",
            doi="10.1007/s10144-012-0315-8",
        ),
        Citation(
            text="Washington State University Apple IPM Transition Project: degree-day development table for codling moth.",
            url="http://web.archive.org/web/20120824104423/http://pmtp.wsu.edu/CM-DD.html",
        ),
        Citation(
            text="Riedl, H., Croft, B. A. and Howitt, A. J. (1976). Forecasting codling moth phenology based on pheromone trap catches and physiological-time models. The Canadian Entomologist 108, 449–460.",
            doi="10.4039/Ent108449-5",
        ),
        Citation(
            text="Riedl, H. and Croft, B. A. (1978). The effects of photoperiod and effective temperatures on the seasonal phenology of the codling moth (Lepidoptera: Tortricidae). The Canadian Entomologist 110, 455–470.",
            doi="10.4039/Ent110455-5",
        ),
        Citation(
            text="Rock, G. C., Stinner, R. E., Bacheler, J. E., Hull, L. A. and Hogmire, H. W. (1993). Predicting geographical and within-season variation in male flights of four fruit pests. Environmental Entomology 22, 716–725.",
            doi="10.1093/ee/22.4.716",
        ),
        Citation(
            text="NEWA, Network for Environment and Weather Applications, Cornell University: codling moth model.",
            url="https://newa.cornell.edu/codling-moth",
        ),
        Citation(
            text="Enviroweather, Michigan State University: codling moth model.",
            url="https://enviroweather.msu.edu/crops/apple/codlingmoth",
        ),
    ),
)
