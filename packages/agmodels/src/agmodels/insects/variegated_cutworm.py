"""Variegated cutworm, rebuilt on Simonet, Clement, Rubink and Rings 1981 (part H, D36, D37)."""

from agmodels.phenology import ActionWindow, DerivedStage, Insect, LifeStage
from agmodels.spec import Change, Check, Citation, TrainingArea

INSECT = Insect(
    id="variegated-cutworm",
    name="Variegated cutworm",
    crops=(
        "asparagus",
        "beans",
        "beet",
        "carrot",
        "celery",
        "corn",
        "sweet-corn",
        "cucumber",
        "hops",
        "leafy-greens",
        "melon",
        "mint",
        "potato",
        "tomato",
    ),
    # Simonet et al. 1981's method (D37): 7.2 °C (45 °F), their threshold for total development, with no upper
    # threshold, from January 1, as they summed degree days for 15 years of light-trap catches at Wooster, Ohio. They
    # don't say how daily degree days were computed; single sine is assumed. VDIFN's 80.1 °F cap (26.7 °C) is only
    # one of their rearing temperatures, and its May 1 start isn't theirs
    base_f=45,
    upper_f=None,
    biofix="01-01",
    source="Simonet et al. 1981",
    life_stages=(
        # The overwintering generation's flight peaks at about 500 °C·d (900 °F·d) from January 1 in the 15-year mean
        # of Wooster's black light catches (Simonet et al. 1981, p. 897 and Fig. 3 on p. 896); its spread isn't given, so start and
        # end are set from DATCP's black light catches in Wisconsin, 2020–2026 (scripts/check_cutworms.py)
        LifeStage(label="Adult flight", start=200, peak=900, end=1500, weight=0),
        # Pre-oviposition 127.5 °C·d above 3.5 °C and egg 89.2 °C·d above 5.6 °C, then the larva's 386.6 °C·d above
        # 6.2 °C (Simonet et al. 1981, p. 895), each carried to the 7.2 °C base at a 20 °C day (99, 79 and 359 °C·d):
        # 320 °F·d from emergence to hatch, 645 °F·d of feeding. Enviroweather's events put hatch 302 after first flight
        DerivedStage(label="Larvae", follows="Adult flight", lag=320, duration=645),
    ),
    # Peak to peak, 500 to 1,200 °C·d (900 to 2,160 °F·d); 15 years of Wooster's catches gave 733 ± 67 °C·d (mean
    # ± SD) between peaks, and the laboratory 775 °C·d from egg to egg laying (p. 897). The SD (121 °F·d) is theirs
    generation_dd=1260,
    generation_sd=120,
    # Two flights a season in Ohio (the overwintering generation and the first); a third would peak near 3,400, past
    # the end of most Wisconsin seasons, and isn't reported
    max_generations=2,
    action_windows=(
        # Simonet et al. 1981: scouting for eggs and young caterpillars should begin at the peak capture of moths
        ActionWindow(label="Scout for eggs and young caterpillars", stage="Adult flight", between=(0.5, 0.95)),
    ),
    version="0.2",
    status="beta",
    trained=TrainingArea(
        description="black light trap catches at Wooster, Ohio, from 1965 to 1979 (the flights' peaks and the time between them) and in Wisconsin's trap network from 2020 to 2026 (the first flight's spread)",
        years=(1965, 2026),
        states=("OH", "WI"),
    ),
    changelog=(
        Change(version="0.1", date="2026-10-28", note="Ported from VDIFN."),
        Change(
            version="0.2",
            date="2026-11-21",
            note="Rebuilt on Simonet et al. 1981: single-sine degree days above 45 °F with no upper threshold from January 1; two moth flights peaking at 900 and 2,160 degree days, with caterpillars timed from each. Replaces VDIFN's one window (900, 1,450, 2,100 degree days, 45/80.1 °F from May 1), whose cap and start date had no source.",
        ),
    ),
    checks=(
        Check(
            kind="published",
            against="Simonet et al. 1981's light-trap catches at Wooster, Ohio, and development times in the laboratory",
            result="The two moth flights peak at 900 and 2,156 degree days, against 900 and 2,160 in 15 years of catches at Wooster. Caterpillars hatch 320 degree days after a moth emerges, against 302 after first flight in Michigan State's Enviroweather model.",
            report="docs/validation/models/variegated-cutworm.md#against-its-sources-numbers",
        ),
        Check(
            kind="observations",
            against="Wisconsin's black light trap network (DATCP), 2020–2026",
            result="Half the moths of the first flight were caught by 1,072 degree days and of the second by 2,064, against the model's 887 and 2,146. Only 273 moths were caught in seven years, so these are rough, and the first flight's spread was set from these same traps.",
            report="docs/validation/models/variegated-cutworm.md#flights-against-wisconsins-black-light-traps",
        ),
    ),
    citations=(
        Citation(
            text="Simonet, D. E., Clement, S. L., Rubink, W. L. and Rings, R. W. (1981). Temperature requirements for development and oviposition of Peridroma saucia (Lepidoptera: Noctuidae). The Canadian Entomologist 113, 891–897.",
            doi="10.4039/Ent113891-10",
        ),
        Citation(
            text="Enviroweather, Michigan State University: variegated cutworm model.",
            url="https://enviroweather.msu.edu/",
        ),
    ),
)
