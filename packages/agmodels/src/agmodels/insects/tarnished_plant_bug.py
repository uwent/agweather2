"""Tarnished plant bug (Lygus lineolaris), rebuilt with Ugine 2012's development times for the generations and the
spring nymphs timed by UW–Madison's 275 degree days, a number from a western lygus bug model (part H, D36, D37). The
spring timing has no source for this species. Retired 2026-11-23 (Ben, part H round 2): with no degree-day timing
for L. lineolaris's spring generation, every generation the model shows inherits an unsupported start."""

from agmodels.phenology import DerivedStage, Insect, LifeStage
from agmodels.spec import Change, Check, Citation, TrainingArea

# Ugine 2012 (L. lineolaris on green beans at constant temperatures; Tables 2, 4 and 5) gives development in °C·d
# above each stage's threshold. Counted on Wisconsin's summer weather, degree days above 52 °F (single sine) are
# 0.737 of those above 46.2 °F (7.9 °C) and 0.873 of those above 49.6 °F (9.8 °C): June to August on the 1996–2025
# normals, the mean of Arlington, Hancock and Rhinelander (the report). The sums here are converted by those ratios
RATIO_46 = 0.737
RATIO_49_6 = 0.873
# First and second instars: 62.5 + 50.0 °C·d (thresholds 8.2 and 7.9 °C), 202.5 °F·d, × 0.737
YOUNG_NYMPHS = 150
# All five instars: 250.0 °C·d above 9.8 °C, 450 °F·d, × 0.873
NYMPHS = 393
# Adults: females lived 24.5 to 34.7 days from 18 to 27 °C and 17.6 at 30 °C, a mean of 408 °C·d above 7.9 °C
# (735 °F·d), × 0.737
ADULTS = 540

INSECT = Insect(
    id="tarnished-plant-bug",
    name="Tarnished plant bug",
    season=("04-01", "10-31"),
    crops=("beans", "celery", "leafy-greens", "pepper", "potato", "raspberry", "tomato"),
    # Single sine above 52 °F from January 1, no upper threshold: the setting of Simko's lygus bug model for seed
    # alfalfa in Oregon and Idaho (USPest.org); UW–Madison's vegetable newsletter (Groves 2021) gives only "275 DD52",
    # probably from Simko's model (an inference: the newsletter cites nothing). Ugine's threshold for development from egg to adult is 7.9 °C (46.2 °F; 9.8 °C for the
    # nymphs); his sums are converted above rather than adding a running total at 46.2 °F for a model with no
    # supported spring timing
    base_f=52,
    upper_f=None,
    biofix="01-01",
    ported_from="VDIFN",
    source="Ugine 2012, with UW–Madison's spring timing",
    life_stages=(
        # Eggs laid in spring by the overwintered adults hatch over several weeks. The curve is placed so that first-
        # and second-stage nymphs (150 degree days from hatch) peak at 275: Simko's peak of young nymphs for the
        # western lygus bug, which UW–Madison's vegetable newsletter gives as the start of the bugs' summer activity.
        # Its start (50) and end (500) are judgments. No source gives a spring degree-day timing for L. lineolaris
        LifeStage(label="Egg hatch", start=50, peak=193, end=500, weight=0),
        # Nymphs feed on buds, flowers and young fruit, and do more damage than adults in strawberries
        DerivedStage(label="Nymphs", follows="Egg hatch", lag=0, duration=NYMPHS),
        # Adults feed on the same parts and lay the next generation's eggs
        DerivedStage(label="Adults", follows="Egg hatch", lag=NYMPHS, duration=ADULTS),
    ),
    # Generation time: Ugine's Table 5 gives 49.2, 36.2, 28.5, 25.7 and 21.0 days at 18, 21, 25, 27 and 30 °C, a mean
    # of 483 °C·d above 7.9 °C (869 °F·d), × 0.737
    generation_dd=640,
    # No cap: UW–Madison's fruit program counts four to five generations a year in the Midwest; the season's degree
    # days allow about four in southern Wisconsin and three in the north, and fall freezes end it
    version="0.4",
    status="retired",
    trained=TrainingArea(
        description="development of a laboratory colony from Stoneville, Mississippi, reared at constant temperatures, with spring timing from a lygus bug model for alfalfa grown for seed in Oregon and Idaho",
        years=(2000, 2010),
        states=("MS", "OR", "ID"),
    ),
    changelog=(
        Change(
            version="0.2",
            date="2026-11-21",
            note="Rebuilt for Lygus lineolaris on Ugine 2012's development times at constant temperatures: egg hatch, nymphs (393 degree days) and adults (540), with generations every 640 degree days above 52 °F (single sine, from January 1) to the season's end. The spring hatch is placed so that young nymphs peak at 275 degree days, the number UW–Madison's vegetable newsletter uses, which comes from a western lygus bug model; no source gives a spring timing for this species. Replaces VDIFN's one window (275, 1,000, 2,000 degree days), whose 1,000 and 2,000 have no known source.",
        ),
        Change(
            version="0.3",
            date="2026-11-23",
            note="Retired: no study or extension source times the tarnished plant bug's spring generation by degree days. The 275 degree days that placed it most likely comes from a model of a western lygus bug, and every later generation followed from it. Scout from early spring instead.",
        ),
        Change(
            version="0.4",
            date="2026-11-26",
            note="In season from April 1 to October 31: from a week before its earliest activity on 2016–2025's weather at six Wisconsin places to October 31, the end of Wisconsin's growing season. Activity ends after October 31 whatever the weather, as fall freezes end it, so a mild fall no longer holds a stalled curve's activity into winter.",
        ),
    ),
    checks=(
        Check(
            kind="published",
            against="Ugine 2012's development times for Lygus lineolaris at constant temperatures, converted to degree days above 52 °F on Wisconsin's summer weather",
            result="Nymphs last 393 degree days and a generation 640, from Ugine's 250 degree-days Celsius above 9.8 °C for the nymphs and a mean generation time of 483 above 7.9 °C. Young nymphs peak at 275 degree days, the number UW–Madison's newsletter uses. That number comes from a model of the western lygus bug in Oregon and Idaho, so the spring timing is unsupported for this species.",
            report="docs/validation/models/tarnished-plant-bug.md#against-its-sources-numbers",
        ),
        Check(
            kind="published",
            against="UW–Madison's descriptions of the season, on AgWeather's 1996–2025 normals",
            result="The first nymphs appear in early May at Arlington, about a week before the mid-May that UW–Madison's fruit program reports in strawberries, and young nymphs peak in late May in the south and early June in the north. The model has about four generations at Arlington and three at Rhinelander, against the four to five UW–Madison counts in the Midwest.",
            report="docs/validation/models/tarnished-plant-bug.md#on-the-normals",
        ),
    ),
    citations=(
        Citation(
            text="Ugine, T. A. (2012). Developmental times and age-specific life tables for Lygus lineolaris (Heteroptera: Miridae), reared at multiple constant temperatures. Environmental Entomology 41, 1–10.",
            doi="10.1603/EN10210",
        ),
        Citation(
            text="Groves, R. L. Vegetable insect update. In Update 9, June 5, 2021, UW–Madison Vegetable Pathology's vegetable crop updates.",
            url="https://vegpath.plantpath.wisc.edu/2021/06/05/update-9-june-5-2021/",
        ),
        Citation(
            text="Simko, B. (2000). Lygus bug degree-day model for alfalfa grown for seed (eastern Oregon and southwestern Idaho). USPest.org, Oregon State University.",
            url="https://uspest.org/cgi-bin/ddmodel2.pl?spp=lyg",
        ),
        Citation(
            text="van Zoeren, J. and Guédot, C. Tarnished plant bug – a strawberry menace. UW–Madison Fruit Program, 2018, updated 2019.",
            url="https://fruit.wisc.edu/2018/05/18/tarnished-plant-bug-a-strawberry-menace/",
        ),
    ),
)
