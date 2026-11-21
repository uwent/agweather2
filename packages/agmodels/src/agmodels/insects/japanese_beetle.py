"""Japanese beetle, rebuilt on Oregon State's USPest model (`jpb`, version 2, June 2024) as a D36 curve (part H)."""

from agmodels.phenology import ActionWindow, Insect, LifeStage
from agmodels.spec import Change, Check, Citation, TrainingArea

INSECT = Insect(
    id="japanese-beetle",
    name="Japanese beetle",
    crops=(
        "asparagus",
        "beans",
        "beet",
        "blackberry",
        "cole-crops",
        "eggplant",
        "hops",
        "horseradish",
        "leafy-greens",
        "melon",
        "mint",
        "pea",
        "pepper",
        "potato",
        "pumpkin-squash",
        "raspberry",
        "tomato",
    ),
    # USPest's method (Coop and Barker 2024, p. 1): single sine, 50 °F with an upper threshold of 92 °F (33.3 °C, near
    # the optimum in Ludwig 1928's development rates), from January 1. On Wisconsin's weather the cap takes at most
    # 2.7 degree days off a season (2016–2025 at Arlington, Hancock and Rhinelander), a day at most; a stored total
    base_f=50,
    upper_f=92,
    biofix="01-01",
    source="Oregon State University's Japanese beetle model (USPest.org)",
    ported_from="VDIFN",
    life_stages=(
        # Adults caught in traps (Coop and Barker 2024, p. 1 and p. 15): 10 % at 1,100, 50 % at 1,540, 90 % at 1,985
        # and 94 % at 2,110, the rounded means of 13 site-years of trap catches in Minnesota, 1994–1997 and 2019–2021
        # (1,128, 1,540, 1,985, 2,108); "2 %" at 1,000 is set below their mean (1,027) to warn early, and the last
        # adults at 2,700 above theirs (2,534). Least squares through the four shares (fitted 2026-11-21): 9.9, 50.2, 89.1 and 95.0 % there; 2 % at
        # 921 and 5 % at 1,007; 99 % at 2,275. A trap catch is beetles active that day, so the curve is read as
        # feeding activity, not emergence: the adults are the damage
        LifeStage(label="Adult beetles", start=722, peak=1513, end=2503),
    ),
    # Scout from the first beetles (2 %, about 920; USPest's "place traps" at 920) to the end of main activity (94 %,
    # USPest's 2,110), and treat when feeding threatens the crop (UW–Madison, University of Minnesota)
    action_windows=(ActionWindow(label="Scout for beetles feeding", stage="Adult beetles", between=(0.02, 0.94)),),
    version="0.2",
    status="beta",
    trained=TrainingArea(
        description="adult trap catches in Minnesota",
        years=(1994, 2021),
        states=("MN",),
    ),
    changelog=(
        Change(
            version="0.2",
            date="2026-11-21",
            note="Rebuilt on Oregon State's Japanese beetle model (USPest.org, version 2, 2024): single-sine degree days above 50 °F with an upper threshold of 92 °F from January 1, and adult activity as a curve through its 10, 50, 90 and 94 % of beetles trapped (1,100, 1,540, 1,985 and 2,110 degree days), with a scouting window from the first beetles to the end of main activity. Replaces VDIFN's window (970, 1,600, 2,150 degree days, no upper threshold), which was USPest's first version.",
        ),
    ),
    checks=(
        Check(
            kind="published",
            against="Oregon State's Japanese beetle model (USPest.org, 2024), from adult trap catches in Minnesota",
            result="Our curve passes 10, 50, 90 and 94 % of the beetles at 1,102, 1,538, 2,001 and 2,085 degree days, against the model's 1,100, 1,540, 1,985 and 2,110. Its first beetles (2 %) come at 921 degree days, earlier than the model's 1,000, and its last (99 %) at 2,275, before the model's last adults at 2,700.",
            report="docs/validation/models/japanese-beetle.md#against-its-sources-numbers",
        ),
        Check(
            kind="observations",
            against="2,818 research-grade iNaturalist records of Japanese beetle adults in Wisconsin, 2016–2026",
            result="Half the records fell by 1,487 degree days and 10 % by 1,048, within about 50 degree days (2 days) of our 50 % and 10 %; the last tenth of the records ran later than our curve (90 % at 2,255 against 2,001), as records of beetles still feeding would. The model wasn't fitted to these records.",
            report="docs/validation/models/japanese-beetle.md#against-inaturalist-records-in-wisconsin",
        ),
    ),
    citations=(
        Citation(
            text="Coop, L. and Barker, B. (2024). Japanese beetle phenology/degree-day and climate suitability model, version 2. Oregon IPM Center, Oregon State University.",
            url="https://uspest.org/wea/japanese_beetle_model.pdf",
        ),
        Citation(
            text="Ebbenga, D. N., Hanson, A. A., Burkness, E. C. and Hutchison, W. D. (2022). A degree-day model for forecasting adult phenology of Popillia japonica (Coleoptera: Scarabaeidae) in a temperate climate. Frontiers in Insect Science 2, 1075807.",
            doi="10.3389/finsc.2022.1075807",
        ),
        Citation(
            text="Vittum, P. J. (1986). Biology of the Japanese beetle (Coleoptera: Scarabaeidae) in eastern Massachusetts. Journal of Economic Entomology 79, 387–391.",
            doi="10.1093/jee/79.2.387",
        ),
    ),
)
