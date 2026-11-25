"""Seedcorn maggot, from the Crop Risk Tool, rebuilt on its sources (D36, D37)."""

from agmodels.insects import CRT
from agmodels.phenology import ActionWindow, DerivedStage, Insect, LifeStage
from agmodels.spec import Change, Check, Citation

INSECT = Insect(
    id="seedcorn-maggot",
    name="Seedcorn maggot",
    season=("02-15", "10-31"),
    crops=("corn", "sweet-corn", "beans", "cucumber", "melon", "pumpkin-squash"),
    # The sources' method (D37): simple average above 3.9 °C (39 °F), temperatures capped at 29 °C (84.2 °F)
    base_f=39,
    upper_f=84.2,
    dd_method="average",
    biofix="01-01",
    life_stages=(
        # Over-wintered flies: first emergence 54–94 FDD in New York (Olaya-Arenas et al. 2024; °F·d, average above 39 °F;
        # Cho et al. 2025's 52–197 too, though NEWA reads them as °C·d: docs/validation/models/seedcorn-maggot.md) and 50% at 347 in
        # Wisconsin (Sanborn 1981 in Funderburk et al. 1984); this curve's 10, 50 and 90% are 201, 345 and 495
        LifeStage(label="Adult flight", start=70, peak=340, end=650),
        # Pre-oviposition 15.7 and egg 30 °C·d (28 + 54 FDD), then the larva's 204 °C·d (367 FDD; Sanborn et al.
        # 1982, Funderburk et al. 1984): oviposition leads to the feeding, so both carry the risk (Ben, 2026-10-29)
        DerivedStage(label="Larval feeding", follows="Adult flight", lag=82, duration=367),
    ),
    # Adult to adult 392 °C·d (706 FDD) in the lab (Funderburk et al. 1984); Wisconsin's field peaks 704 then 860 apart
    generation_dd=720,
    # Individuals' development rates ranged about ±20% of the mean in the lab (Sanborn et al. 1982, Table 1, larvae
    # at 14.6 °C), about ±2 SD, so an SD near 8% of a generation; the first flight's own spread (~120) is wider
    # because over-wintered emergence is drawn out (Throne and Eckenrode 1985), not because development varies
    generation_sd=60,
    # The over-wintered flight and the first generation (the engine's second, half emerged at 1,065: early June in
    # southern Wisconsin) weigh 1, later generations 0.25 (version 0.4; Ben, 2026-11-23). Iowa's F1 flight, 30 to 45 days
    # after the over-wintered one, was about as large in 1980 (both over 1,000 flies a trap a day) and far larger in 1981
    # (Funderburk et al. 1984, Fig. 2), and New York's large mid-June peak is over-wintered flies plus the offspring of
    # April and May flies (Throne and Eckenrode 1985, p. 185). After it the F2 mostly aestivated in Iowa, with almost no
    # flies after mid-July (Funderburk et al., p. 107–108), and the damage is to germinating seed of spring plantings.
    # The sources say which generations matter, not by how much: 0.25 is a judgment (Ben, 2026-11-23)
    generation_weights=(1.0, 1.0, 0.25),
    action_windows=(ActionWindow(label="Avoid planting during adult flight", stage="Adult flight"),),
    version="0.5",
    status="beta",
    changelog=(
        Change(
            version="0.2",
            date="2026-10-29",
            note="Life stages as curves (D36): adult flight from 70 FDD, half done by 345, and larval feeding timed from it, in every generation 720 FDD apart; degree days by the sources' average method (D37) rather than single sine, which ran 5–7 days early in spring. Replaces the Crop Risk Tool's step table.",
        ),
        Change(
            version="0.3",
            date="2026-11-23",
            note="The summer generations weigh a quarter as much as the over-wintered flight and the spring generation in the risk, since spring plantings take the damage and the summer generation mostly rests through the heat.",
        ),
        Change(
            version="0.4",
            date="2026-11-23",
            note="The first generation's flight in early June weighs as much as the over-wintered flight in the risk, and only the generations after it a quarter: in Iowa that June flight was as large as the spring flight or larger (Funderburk, Higley and Pedigo 1984, Fig. 2), and New York's mid-June peak is a large one (Throne and Eckenrode 1985).",
        ),
        Change(
            version="0.5",
            date="2026-11-26",
            note="In season from February 15 to October 31: from a week before its earliest activity on 2016–2025's weather at six Wisconsin places to October 31, the end of Wisconsin's growing season. Activity ends after October 31 whatever the weather, as fall freezes end it, so a mild fall no longer holds a stalled curve's activity into winter.",
        ),
    ),
    source=CRT,
    checks=(
        Check(
            kind="published",
            against="Seedcorn maggot flights in Wisconsin fields (Sanborn 1981, as reported by Funderburk et al. 1984)",
            result="Half of each flight has emerged at 345, 1,065 and 1,785 degree days, against 347, 1,051 and 1,912 in Wisconsin fields. The first flight was set from these field data; the later two follow from laboratory development times and were not fitted to them.",
            report="docs/validation/models/seedcorn-maggot.md#against-its-sources-numbers",
        ),
        Check(
            kind="published",
            against="Seedcorn maggot trap catches near Ames, Iowa, 1980 and 1981 (Funderburk et al. 1984)",
            result="Half of the over-wintered flight had emerged at 342 degree days, against our 345. The next flight's midpoint came at 1,228, 163 degree days after ours: the authors found the insects developed more slowly in the field than air temperatures predict.",
            report="docs/validation/models/seedcorn-maggot.md#against-its-sources-numbers",
        ),
        Check(
            kind="system",
            against="The Crop Risk Tool, which this model replaces, on the weather of Eau Claire, Wisconsin, 2025",
            result="Our flight peaks came 6 days after the tool's in spring and 3 days after in summer, mostly because we count degree days by the method our sources used.",
            report="docs/validation/models/seedcorn-maggot.md#against-the-crop-risk-tool-on-the-same-weather",
        ),
        Check(
            kind="system",
            against="NEWA's seedcorn maggot model on the weather of 34 Wisconsin NEWA stations, 2024 and 2025",
            result="Our spring flight starts a median 5 days before NEWA's first-emergence window opens and is half over a median 1 day before the window closes. NEWA reads New York's first-emergence numbers as degree days Celsius where the studies counted in Fahrenheit, so its window covers most of the flight rather than its first flies.",
            report="docs/validation/models/seedcorn-maggot.md#against-newa-on-the-same-weather",
        ),
    ),
    citations=(
        Citation(text="The Crop Risk Tool (UW–Madison Vegetable Entomology)."),
        Citation(
            text="Sanborn, S. M., Wyman, J. A. and Chapman, R. K. (1982). Threshold temperature and heat unit summations for seedcorn maggot development under controlled conditions. Annals of the Entomological Society of America 75, 103–106.",
            doi="10.1093/aesa/75.1.103",
        ),
        Citation(
            text="Funderburk, J. E., Higley, L. G. and Pedigo, L. P. (1984). Seedcorn maggot (Diptera: Anthomyiidae) phenology in central Iowa and examination of a thermal-unit system to predict development under field conditions. Environmental Entomology 13, 105–109.",
            doi="10.1093/ee/13.1.105",
        ),
        Citation(
            text="Throne, J. E. and Eckenrode, C. J. (1985). Emergence patterns of the seedcorn maggot, Delia platura (Diptera: Anthomyiidae). Environmental Entomology 14, 182–186.",
            doi="10.1093/ee/14.2.182",
        ),
        Citation(
            text="Olaya-Arenas, P., Cho, C. Y. L., Olmstead, D., et al. (2024). Degree-day models for predicting adult Delia platura (Diptera: Anthomyiidae) spring flight and first emergence in New York State. Journal of Economic Entomology 117, 2181–2185.",
            doi="10.1093/jee/toae148",
        ),
        Citation(
            text="Cho, C. Y.-L., Crowther, S., Stratton, A., Olmstead, D. and Poveda, K. (2025). Validation of degree day threshold for Delia platura first emergence in New York State. Crop Protection 188, 107011.",
            doi="10.1016/j.cropro.2024.107011",
        ),
        Citation(
            text="NEWA, Network for Environment and Weather Applications, Cornell University: seedcorn maggot model.",
            url="https://newa.cornell.edu/seedcorn-maggot",
        ),
    ),
)
