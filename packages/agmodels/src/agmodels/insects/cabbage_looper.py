"""Cabbage looper, rebuilt on USPest.org's model (Toba et al. 1973's development times) from the first moth catch, with
a default catch date from UW–Madison's account of the moths' arrival (part H, D36, D37)."""

from agmodels.phenology import ActionWindow, DerivedStage, Insect, LifeStage
from agmodels.spec import Change, Check, Citation, TrainingArea

# USPest.org's cabbage looper events (degree days, °F, single sine 50/90, from the first catch): 120 first egg laying,
# 218 first hatch, 325 small larvae, 428 first fourth instar, 520 large larvae, 638 first pupae, 750 last large larvae,
# 912 first adults. So the egg takes 98, the larva 420 (hatch to pupation), and a generation 912 from egg laying to the
# next egg laying: Toba et al. 1973's 791.5 from egg to adult plus the 120 before laying
FIRST_EGGS = 120
EGG = 218 - FIRST_EGGS
LARVA = 638 - 218
GENERATION = 912

INSECT = Insect(
    id="cabbage-looper",
    name="Cabbage looper",
    crops=("celery", "cole-crops", "hops", "leafy-greens", "melon", "mint", "pea", "potato", "tomato"),
    # USPest.org's method: single sine, 50/90 °F (Toba et al. 1973: no development at 7.2 °C, 45 °F; few normal adults
    # below 12.7 °C, 55 °F). Both thresholds are stored. NEWA runs no looper model
    base_f=50,
    upper_f=90,
    # The moths migrate from the south each year, so the biofix is the first moth caught in a pheromone trap
    # (USPest.org). Without a grower's date, July 15: UW–Madison has the moths arriving from mid-July through September
    # (UW Hort, UW Veg Ento); the University of Minnesota gives early July to late August. No Wisconsin or Minnesota trap
    # records were found (DATCP's black light traps count other loopers), so this is a typical arrival, not a forecast
    biofix="07-15",
    biofix_label="First moth caught in a pheromone trap; without a date, July 15",
    ported_from="VDIFN",
    source="USPest.org's cabbage looper model",
    life_stages=(
        # Egg laying from the first catch: USPest's first eggs at 120. Its single cohort lays for about 110 degree days
        # (its last large larvae at 750), but migrants keep arriving for weeks, so the spread here is wider (a
        # judgment): peak 200, end 450, half the first generation's eggs laid by 221. Moths don't feed on the crop
        LifeStage(label="Egg laying", start=FIRST_EGGS, peak=200, end=450, weight=0),
        # Eggs hatch in 98 (USPest's 120 to 218); the scouting window follows them
        DerivedStage(label="Eggs", follows="Egg laying", lag=0, duration=EGG, weight=0),
        # Caterpillars from hatch to pupation (USPest's 218 to 638), large ones from 428 (its fourth instar): the risk
        DerivedStage(label="Larval feeding", follows="Egg laying", lag=EGG, duration=LARVA),
    ),
    # Every 912 to the season's end: the second generation, which UW–Madison says does the most damage, lays its eggs
    # in late August and September in southern Wisconsin on the normals; fall freezes end the season
    generation_dd=GENERATION,
    # UW–Madison: the second generation does the most damage. It weighs 1 and the others 0.5: the sources say which
    # generation matters, not by how much, so 0.5 is a judgment (Ben, 2026-11-23)
    generation_weights=(0.5, 1.0, 0.5),
    action_windows=(
        # From 10 to 90 % of each generation's eggs hatched: small caterpillars, the target for sprays (A3422; UW)
        ActionWindow(label="Scout for small caterpillars", stage="Eggs", between=(0.1, 0.9)),
    ),
    version="0.3",
    status="beta",
    trained=TrainingArea(
        description="development times measured in the laboratory in Riverside, California, as USPest.org's model uses them",
        years=(1973, 1973),
        states=("CA",),
    ),
    changelog=(
        Change(
            version="0.2",
            date="2026-11-21",
            note="Rebuilt on USPest.org's cabbage looper model (Toba et al. 1973; single sine 50/90 °F): counted from the first moth caught in a pheromone trap, or July 15 without one (UW–Madison: moths arrive from mid-July); egg laying, eggs and caterpillar feeding as curves (hatch 98 and pupation 518 degree days after an egg is laid), generations every 912 degree days to the season's end, and a window to scout for small caterpillars. Risk follows the caterpillars. Replaces VDIFN's two windows from May 15, whose first came about a month before the moths arrive and which missed the damaging late-summer generation.",
        ),
        Change(
            version="0.3",
            date="2026-11-23",
            note="The second generation's caterpillars weigh twice as much as the others' in the risk, since UW–Madison says the second generation does the most damage.",
        ),
    ),
    checks=(
        Check(
            kind="published",
            against="USPest.org's cabbage looper model and Toba et al. 1973's laboratory development times",
            result="Eggs hatch 98 degree days after laying and caterpillars pupate 420 later, as USPest's events from 120 to 638; the next generation's egg laying follows 912 after this one's, Toba et al.'s 791.5 from egg to adult plus USPest's 120 before laying.",
            report="docs/validation/models/cabbage-looper.md#against-its-sources-numbers",
        ),
        Check(
            kind="published",
            against="UW–Madison's account of the moths' arrival and the damaging second generation",
            result="From the July 15 default, on the 1996–2025 normals the first generation's caterpillars peak in early to mid-August and the second generation's eggs are laid in early to mid-September at Arlington and Hancock, so the generation UW–Madison calls the most damaging is covered; at Rhinelander the season ends during the second generation's egg laying.",
            report="docs/validation/models/cabbage-looper.md#on-the-normals",
        ),
    ),
    citations=(
        Citation(
            text="Toba, H. H., Kishaba, A. N., Pangaldan, R. and Vail, P. V. (1973). Temperature and the development of the cabbage looper. Annals of the Entomological Society of America 66, 965–974.",
            doi="10.1093/aesa/66.5.965",
        ),
        Citation(
            text="USPest.org (Oregon State University's degree-day site): cabbage looper degree-day model, credited there to the University of Minnesota (Toba et al. 1973).",
            url="https://uspest.org/cgi-bin/ddmodel2.pl?spp=cbl",
        ),
        Citation(
            text="Delahaut, K. Cabbage Looper. UW–Madison Division of Extension, Wisconsin Horticulture.",
            url="https://hort.extension.wisc.edu/articles/cabbage-looper/",
        ),
        Citation(
            text="Schuh, M., Hahn, J. and Wold-Burkness, S. Caterpillars on Cole Crops. University of Minnesota Extension.",
            url="https://extension.umn.edu/yard-and-garden-insects/caterpillars-cole-crops",
        ),
    ),
)
