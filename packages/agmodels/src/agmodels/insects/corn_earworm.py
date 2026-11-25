"""Corn earworm, rebuilt on Hartstack et al. 1976 as USPest.org runs it (part H, D36, D37), its default biofix set from
DATCP's corn earworm pheromone traps."""

from agmodels.phenology import DerivedStage, Insect, LifeStage
from agmodels.spec import Change, Check, Citation, TrainingArea

INSECT = Insect(
    id="corn-earworm",
    name="Corn earworm",
    season=("08-01", "10-31"),
    crops=("beans", "corn", "sweet-corn"),
    # USPest.org's model (Hartstack et al. 1976; read 2026-11-21): single sine, 55 and 92 °F, from egg laying near
    # first silk (its default date August 1, its validation "partly validated" in the Pacific Northwest). UC IPM's
    # first model has the same rates in °C (12.6/33.3 °C, intermediate cutoff). NEWA runs no corn earworm model
    base_f=55,
    upper_f=92,
    biofix="08-15",
    biofix_label="Eggs first found on silks, or the first week of a significant moth flight in your area; without a date, August 15",
    source="Hartstack et al. 1976, as USPest.org runs it",
    ported_from="VDIFN",
    life_stages=(
        # Eggs laid by the flight that starts at the biofix, taken to follow the moths caught. DATCP's pheromone catches
        # after the main flight's first week of 35 or more moths (5 a night, from July 25), 2021–2026, 63 site-years:
        # 25, 50, 75 and 90 % at 81, 141, 266 and 505 degree days from that week's first day
        # (scripts/check_corn_earworm.py; weekly counts, and traps come down in September). This curve, fitted to the
        # quartiles, gives 73, 152, 263 and 383. Moths and eggs carry no risk of their own
        LifeStage(label="Egg laying", start=0, peak=45, end=920, weight=0),
        # Hartstack et al. 1976 (USPest's events): egg hatch begins 73 degree days after laying, larvae leave the ears
        # to pupate at 437 (UC IPM's model 1, the same in °F·d: egg 72.9, small and large larva 147.1 + 217.1). Larvae in the ears are the crop's damage
        DerivedStage(label="Larvae in ears", follows="Egg laying", lag=73, duration=364),
    ),
    # Hartstack: adults emerge 760 and lay eggs 873 after the eggs they came from (UC IPM: 872.8). From August 15
    # DATCP's trap sites reached a median 652 degree days (484–776) by October 15 (the report), so the eggs' own moths rarely
    # emerge, and none overwinter here: one generation
    max_generations=1,
    version="0.3",
    status="beta",
    # Hartstack's rates came from Texas (USDA, College Station); the egg-laying spread and default date from DATCP's
    # pheromone traps in Wisconsin, 2021–2026. Hartstack's data years aren't in hand: the span runs from his report
    trained=TrainingArea(
        description="development rates from Texas, with the moth flight's timing from Wisconsin's pheromone traps",
        years=(1976, 2026),
        states=("TX", "WI"),
    ),
    changelog=(
        Change(
            version="0.2",
            date="2026-11-21",
            note="Rebuilt on Hartstack et al. 1976 as USPest.org runs it: single sine 55/92 °F from egg laying; larvae in the ears from 73 to 437 degree days after each egg is laid, the eggs spread as DATCP's pheromone traps show the main flight; the default biofix moved from August 1 to August 15, where DATCP's traps put the main flight's first week of 35 or more moths. Replaces VDIFN's ramp (70, 275, 440) from August 1.",
        ),
        Change(
            version="0.3",
            date="2026-11-26",
            note="In season from August 1 to October 31: from a week before its earliest activity on 2016–2025's weather at six Wisconsin places to October 31, the end of Wisconsin's growing season. Activity ends after October 31 whatever the weather, as fall freezes end it, so a mild fall no longer holds a stalled curve's activity into winter.",
        ),
    ),
    checks=(
        Check(
            kind="published",
            against="Hartstack et al. 1976's development times, as USPest.org and UC IPM give them",
            result="Larvae enter the ears 73 degree days after each egg is laid and leave them 437 degree days after, as in the source.",
            report="docs/validation/models/corn-earworm.md#against-its-sources-numbers",
        ),
        Check(
            kind="observations",
            against="Corn earworm pheromone trap catches in Wisconsin (DATCP), 2021–2026",
            result="The main flight's first week of 35 or more moths came a median 1 day after August 15 (63 site-years; 42 within a week of it), and 15 days after August 1, the old default. The default was set from these same traps, so this shows the fit, not a test.",
            report="docs/validation/models/corn-earworm.md#against-wisconsins-pheromone-traps",
        ),
    ),
    citations=(
        Citation(
            text="Hartstack, A. W., et al. (1976). MOTHZV-2: a computer simulation of Heliothis zea and Heliothis virescens population dynamics. USDA Agricultural Research Service, ARS-S-127.",
        ),
        Citation(
            text="USPest.org, Oregon State University: corn earworm degree-day model (Hartstack et al. 1976).",
            url="https://uspest.org/cgi-bin/ddmodel2.pl?spp=cew",
        ),
        Citation(
            text="Coop, L. B., Croft, B. A. and Drapek, R. J. (1993). Model of corn earworm (Lepidoptera: Noctuidae) development, damage, and crop loss in sweet corn. Journal of Economic Entomology 86, 906–916.",
            doi="10.1093/jee/86.3.906",
        ),
        Citation(
            text="Wisconsin Department of Agriculture, Trade and Consumer Protection: corn earworm pheromone trap counts, 2021–2026.",
            url="https://datcp.wi.gov/Pages/Programs_Services/CornEarwormTraps.aspx",
        ),
        Citation(
            text="UW–Madison Vegetable Entomology. Corn Earworm.",
            url="https://vegento.russell.wisc.edu/pests/corn-earworm/",
        ),
    ),
)
