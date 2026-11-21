"""Cabbage maggot, rebuilt on NEWA's model (D95) and its source, Jyoti, Shelton and Barnard 2003 (part H, D36, D37)."""

from agmodels.phenology import ActionWindow, DerivedStage, Insect, LifeStage
from agmodels.spec import Change, Check, Citation, TrainingArea

INSECT = Insect(
    id="cabbage-maggot",
    name="Cabbage maggot",
    crops=("cole-crops",),
    # NEWA's method (D95): the day's simple average above 40 °F, no upper threshold, from January 1. Its table is
    # Jyoti, Shelton and Barnard 2003's degree days above 4 °C (upstate New York, 1999–2000) times 1.8. Eckenrode and
    # Chapman 1972 counted above 43 °F with Arnold's correction in Wisconsin: compared, not used
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
    # NEWA's later flights peak (50 %) at 1,261, 2,176 and 3,014, 809, 915 and 838 apart: 850 sets every
    # generation's 50 % within 45 of NEWA's (least squares over the three). Eckenrode and Chapman 1972 found 1,176 DD43
    # between Wisconsin flights (about 1,300 DD40 in summer): a third longer, kept as a difference (D95)
    generation_dd=850,
    # Eckenrode and Chapman 1972: the spring emergence pattern repeats in later generations, so they spread little;
    # 10 % of a generation (the default, the spring flight's own SD, 125, would widen them half again as fast)
    generation_sd=85,
    # Four flights at most: New York's four (NEWA; Jyoti et al. 2003). At 850 a generation, southern Wisconsin's
    # normal season (about 4,400 DD40 by October 15 at Arlington) would otherwise start a fifth (50 % at 3,858) in
    # late September, which no source reports; Eckenrode and Chapman 1972 trapped three in Wisconsin
    max_generations=4,
    action_windows=(
        # NEWA: highest risk around peak flights; protect seedlings, transplants and root crops then. From first
        # emergence (NEWA's 288, 5 %) to 95 % of each flight
        ActionWindow(
            label="Protect seedlings and transplants during fly flight", stage="Adult flight", between=(0.05, 0.95)
        ),
    ),
    version="0.2",
    status="beta",
    trained=TrainingArea(description="water-pan trap catches in upstate New York", years=(1999, 2000), states=("NY",)),
    changelog=(
        Change(
            version="0.2",
            date="2026-11-21",
            note="Rebuilt on NEWA's cabbage maggot model and its source (Jyoti, Shelton and Barnard 2003): degree days by the simple average above 40 °F from January 1 with no upper threshold; the spring flight as a curve through NEWA's 25, 50, 75 and 95 % emergence, larval feeding timed from it, and later flights every 850 degree days, as NEWA's peaks. Replaces VDIFN's two windows (single sine 42.8/86 °F), whose second flight came about 345 degree days late and which had no third.",
        ),
    ),
    checks=(
        Check(
            kind="published",
            against="NEWA's cabbage maggot table and its source, trap catches in upstate New York (Jyoti, Shelton and Barnard 2003)",
            result="The spring flight passes 10, 25, 50, 75 and 95 % emergence within 13 degree days of the published points, and NEWA's first emergence at 288 comes at 5.9 % of the flight. Half of each later flight has emerged within 45 degree days of NEWA's 1,261, 2,176 and 3,014.",
            report="docs/validation/models/cabbage-maggot.md#against-its-sources-numbers",
        ),
        Check(
            kind="published",
            against="Fly trap catches at Kenosha and Arlington, Wisconsin, 1965–1969 (Eckenrode and Chapman 1972)",
            result="Wisconsin's spring flies first emerged at 290 to 365 degree days above 43 °F, about the same days as NEWA's 288 above 40 °F, or up to about 9 days later. Wisconsin's generations took 1,176 degree days above 43 °F, about a third longer than NEWA's 850 above 40 °F, which would put the first summer flight a median 16 days later; the model follows NEWA.",
            report="docs/validation/models/cabbage-maggot.md#against-eckenrode-and-chapman-1972",
        ),
        Check(
            kind="system",
            against="NEWA's cabbage maggot model on the weather of 34 Wisconsin NEWA stations, 2024 and 2025",
            result="The model reproduces NEWA's events: first emergence, the spring peak and each later peak fall within a day or two of NEWA's on the same weather.",
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
