"""Cabbage maggot, rebuilt on NEWA's model (D95) and its source, Jyoti, Shelton and Barnard 2003 (part H, D36, D37),
with the generation time from that paper's trap counts and Eckenrode and Chapman 1972 (part H, round 2)."""

from agmodels.phenology import ActionWindow, DerivedStage, Insect, LifeStage
from agmodels.spec import Change, Check, Citation, TrainingArea

INSECT = Insect(
    id="cabbage-maggot",
    name="Cabbage maggot",
    crops=("cole-crops",),
    # NEWA's method (D95): the day's simple average above 40 °F, no upper threshold, from January 1. Its table is
    # Jyoti, Shelton and Barnard 2003's degree days (the simple average above 4 °C, 39.2 °F, from January 1; upstate New
    # York, 1999–2000) times 1.8, counted from 40 °F (about a day and a half late by the spring peak). Eckenrode and
    # Chapman 1972 counted above 43 °F with Arnold's correction in Wisconsin: their generation converted (below)
    base_f=40,
    upper_f=None,
    dd_method="average",
    biofix="01-01",
    source="NEWA's cabbage maggot model",
    ported_from="VDIFN",
    life_stages=(
        # Spring emergence from overwintering pupae (NEWA's table; Jyoti et al. 2003): 25 % at 366, 50 % at 452, 75 %
        # at 547 and 95 % at 697. This curve is at 25.2, 50.6, 74.6 and 95.4 % there (a fit within a point); its 10,
        # 25, 50, 75 and 95 % come at 308, 365, 450, 549 and 692, against the paper's 318, 368, 452, 536 and 704 (NEWA's
        # 547 for 75 % isn't the paper's 297.6 °C·d × 1.8); NEWA's first emergence (288) at 5.9 %
        LifeStage(label="Adult flight", start=230, peak=405, end=935),
        # Pre-oviposition about 4–6 days at 70 °F (Eckenrode and Chapman 1971; Harris and Svec 1966 as they cite
        # it), about 150 DD40, and the egg 82 DD above 44 °F (Eckenrode and Chapman 1971), about 95 DD40; then 18–22
        # days of larval feeding at 66–72 °F (Harris and Svec 1966), about 580 DD40
        DerivedStage(label="Larval feeding", follows="Adult flight", lag=245, duration=580),
    ),
    # A generation of 1,275 DD40 (version 0.4; Ben, 2026-11-23), where NEWA has 850 (a difference kept, D95: NEWA's own
    # source shows its interval wrong). NEWA's later peaks (1,261, 2,176, 3,014) are its spring 50 % plus Jyoti et al.'s
    # spring, F1 and F2 flights' lengths (449.2, 508.4 and 465.3 °C·d from each flight's first increase to its end, × 1.8),
    # not times between peaks; the paper gives no generation time. Its own Fig. 3 peaks, on Open-Meteo's weather at
    # Geneva counted above 40 °F, are 1,040 and 1,055–1,237 apart from spring to F1 and 1,597 and 974–1,156 from F1 to
    # F2 (a mean of 1,212, the 2000 ranges by their midpoints; that archive ran 4–11 % below the farm's station). Eckenrode
    # and Chapman 1972's Wisconsin generation, 1,176 DD43 (Arnold's correction), is a median 1,349 DD40 from the spring
    # peak to the first summer flight and 1,321 from it to the second on the Wisconsin NEWA stations' days (single sine
    # above 43 °F for theirs). 1,275 is the two studies' mean, each counted once: (1,212 + 1,335) / 2. UW's XHT1087
    # (300, 1,476, 2,652 DD43) is the same Wisconsin 1,176 apart
    generation_dd=1275,
    # Eckenrode and Chapman 1972: the spring emergence pattern repeats in later generations, so they spread little;
    # 10 % of a generation, as version 0.2's 85 was of 850 (about the spring flight's own SD, 125)
    generation_sd=128,
    # Three flights at most (part H, round 2; Ben, 2026-11-23): Eckenrode and Chapman 1972 trapped three in Wisconsin
    # (spring, F1 from early July, F2 from mid-August, small), against New York's four (NEWA; Jyoti et al. 2003). At
    # 1,275 a generation a fourth flight's first flies (5 %) would come at 3,880 DD40: on the normals about September 14
    # at Arlington and September 26 at Hancock, not by October 15 at Rhinelander (scripts/maggot_normals.py), and by
    # October 15 in 60 of 67 Wisconsin NEWA station-seasons, 2024 and 2025 (scripts/check_maggots.py). So the cap binds
    # in most seasons in the south, on a fourth flight that would come in the fall
    max_generations=3,
    generation_weights=(1.0, 0.5),
    action_windows=(
        # NEWA: highest risk around peak flights; protect seedlings, transplants and root crops then. From first
        # emergence (NEWA's 288, 5 %) to 95 % of each flight
        ActionWindow(
            label="Protect seedlings and transplants during fly flight", stage="Adult flight", between=(0.05, 0.95)
        ),
    ),
    version="0.4",
    status="beta",
    trained=TrainingArea(description="water-pan trap catches in upstate New York", years=(1999, 2000), states=("NY",)),
    changelog=(
        Change(
            version="0.2",
            date="2026-11-21",
            note="Rebuilt on NEWA's cabbage maggot model and its source (Jyoti, Shelton and Barnard 2003): degree days by the simple average above 40 °F from January 1 with no upper threshold; the spring flight as a curve through NEWA's 25, 50, 75 and 95 % emergence, larval feeding timed from it, and later flights every 850 degree days, as NEWA's peaks. Replaces VDIFN's two windows (single sine 42.8/86 °F), whose second flight came about 345 degree days late and which had no third.",
        ),
        Change(
            version="0.3",
            date="2026-11-23",
            note="At most three flights, as Eckenrode and Chapman trapped in Wisconsin (NEWA's New York has four), and the summer flights weigh half as much as the spring flight in the risk, since the spring flight does the most damage.",
        ),
        Change(
            version="0.4",
            date="2026-11-23",
            note="A generation of 1,275 degree days (SD 128) instead of NEWA's 850, which adds each flight's length to the spring peak: the mean of the flight peaks in Jyoti, Shelton and Barnard's own trap counts (Fig. 3; 1,212 apart on Open-Meteo's weather at Geneva) and Eckenrode and Chapman's 1972 Wisconsin generation (1,176 above 43 °F, about 1,335 above 40 °F). The second and third flights come about two and four weeks later.",
        ),
    ),
    checks=(
        Check(
            kind="published",
            against="NEWA's cabbage maggot table, whose spring flight comes from trap catches in upstate New York (Jyoti, Shelton and Barnard 2003)",
            result="The spring flight passes 10, 25, 50, 75 and 95 % emergence within 13 degree days of the published points, and NEWA's first emergence at 288 comes at 5.9 % of the flight. The later flights are half emerged at 1,731 and 3,007, a generation of 1,275 apart, where NEWA's table has 1,261 and 2,176 (it adds each flight's length to the spring peak); the model stops at three flights, where NEWA has a fourth (3,014).",
            report="docs/validation/models/cabbage-maggot.md#against-its-sources-numbers",
        ),
        Check(
            kind="published",
            against="Fly trap catches at Kenosha and Arlington, Wisconsin, 1965–1969 (Eckenrode and Chapman 1972)",
            result="Wisconsin's spring flies first emerged at 290 to 365 degree days above 43 °F, about the same days as the model's first flies at 288 above 40 °F, or up to about 9 days later. Wisconsin's generations took 1,176 degree days above 43 °F, a median 1,350 and 1,321 above 40 °F on Wisconsin weather; the model's 1,275 puts the first summer flight a median 2 days before their generation would.",
            report="docs/validation/models/cabbage-maggot.md#against-eckenrode-and-chapman-1972",
        ),
        Check(
            kind="published",
            against="The flight peaks in New York trap catches, 1999 and 2000 (Jyoti, Shelton and Barnard 2003), on Open-Meteo's weather at the farm",
            result="The paper gives degree days only for the spring flight. On its trap counts' peak dates, counted above 40 °F, its flights peaked 974 to 1,597 degree days apart (a mean of 1,212), against NEWA's 809 to 915. The model's summer peaks fall 1 day before to 12 days after the trapped ones; NEWA's fall 7 to 26 days before them.",
            report="docs/validation/models/cabbage-maggot.md#against-jyoti-et-als-trap-counts",
        ),
        Check(
            kind="system",
            against="NEWA's cabbage maggot model on the weather of 34 Wisconsin NEWA stations, 2024 and 2025",
            result="The spring flight reproduces NEWA's: first emergence and its 25 to 95 % points fall on NEWA's day at the median. The summer flights peak a median 15 and 26 days after NEWA's, by design: the model's generation is 1,275 degree days, NEWA's 850.",
            report="docs/validation/models/cabbage-maggot.md#against-newa-on-the-same-weather",
        ),
    ),
    citations=(
        Citation(
            text="Jyoti, J. L., Shelton, A. M. and Barnard, J. (2003). Evaluation of degree-day and Julian-day logistic models in predicting cabbage maggot (Diptera: Anthomyiidae) emergence and flight in upstate New York. Journal of Entomological Science 38, 525–532.",
            doi="10.18474/0749-8004-38.4.525",
        ),
        Citation(
            text="NEWA, Network for Environment and Weather Applications, Cornell University: cabbage maggot model.",
            url="https://newa.cornell.edu/cabbage-maggot",
        ),
        Citation(
            text="Eckenrode, C. J. and Chapman, R. K. (1971). Effect of various temperatures upon rate of development of the cabbage maggot under artificial conditions. Annals of the Entomological Society of America 64, 1079–1083.",
            doi="10.1093/aesa/64.5.1079",
        ),
        Citation(
            text="Eckenrode, C. J. and Chapman, R. K. (1972). Seasonal adult cabbage maggot populations in the field in relation to thermal-unit accumulations. Annals of the Entomological Society of America 65, 151–156.",
            doi="10.1093/aesa/65.1.151",
        ),
    ),
)
