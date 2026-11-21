"""Western bean cutworm, on Hanson et al. 2015's flight model, which NEWA runs (D95; D36, D37)."""

from agmodels.phenology import ActionWindow, DerivedStage, Insect, LifeStage
from agmodels.spec import Change, Check, Citation, TrainingArea

INSECT = Insect(
    id="western-bean-cutworm",
    name="Western bean cutworm",
    crops=("corn", "sweet-corn", "dry-bean"),
    # Hanson et al. 2015's best model: the simple average with the daily mean (not each temperature) capped at the
    # upper threshold, 3.3 and 23.9 °C (38 and 75 °F), from March 1. NEWA uses the same numbers; its deployed code
    # rounds each day's max and min to whole °C and swaps them, which we don't reproduce (the report measures it)
    base_f=38,
    upper_f=75,
    dd_method="average_capped_mean",
    biofix="03-01",
    life_stages=(
        # Black light catches in Nebraska, 1981–2009: a log-logistic in °C·d (μ 7.315, s 0.044; Table 4: 5, 25, 50,
        # 75 and 95 % at 2,377, 2,577, 2,704, 2,838 and 3,077 °F·d; NEWA adds 10 % 2,455 and 90 % 2,977). This PERT
        # follows it within 2.3 percentage points from 1,800 to 3,800 (fitted 2026-11-21); moths fly, but don't feed
        LifeStage(label="Adult flight", start=2247, peak=2685, end=3285, weight=0),
        # Females lay on corn near tasseling and the eggs hatch 5 to 7 days later (UW–Madison, A3646): six days at
        # about 33 degree days a day, Arlington's July 15–August 1 rate on the normals. No published duration in degree
        # days; egg masses (and the small larvae just out of them) are what scouts count and sprays must catch
        DerivedStage(label="Egg masses", follows="Adult flight", lag=0, duration=200),
    ),
    # Scout for egg masses from the first moths (5 % flight) until about 7–10 days after the peak (90 %): UW–Madison
    # says to start at 25 % flight or the first moths caught nearby and continue 7–10 days past the peak
    action_windows=(ActionWindow(label="Scout corn for egg masses", stage="Adult flight", between=(0.05, 0.9)),),
    status="beta",
    version="0.3",
    changelog=(
        Change(
            version="0.2",
            date="2026-11-18",
            note="Crops corrected to corn, sweet corn and dry beans (the list had been copied from black cutworm's).",
        ),
        Change(
            version="0.3",
            date="2026-11-21",
            note="Rebuilt on Hanson et al. 2015's flight model, which NEWA runs (D95): the simple average with the daily mean capped, 38/75 °F from March 1, the whole moth flight as a curve (half flown at 2,705) with egg masses timed from it, and a window to scout for egg masses from 5 % to 90 % of the flight. Replaces VDIFN's 25–75 % ramp on single sine 50 °F from May 1 (Ahmad 1979).",
        ),
    ),
    trained=TrainingArea(
        description="black light trap catches at four sites in Nebraska",
        years=(1981, 2009),
        states=("NE",),
    ),
    checks=(
        Check(
            kind="published",
            against="Hanson et al. 2015's flight model, fitted to black light catches in Nebraska, 1981–2009",
            result="Our flight curve follows theirs within 2.3 percentage points: 5, 50 and 95 % of the moths have flown at 2,402, 2,705 and 3,043 degree days, against their 2,377, 2,704 and 3,077.",
            report="docs/validation/models/western-bean-cutworm.md#against-its-sources-numbers",
        ),
        Check(
            kind="system",
            against="NEWA's western bean cutworm model on the weather of Wisconsin's NEWA stations, 2024 and 2025",
            result="Half the flight comes a median 3 days before NEWA's date (2 to 7 days before in most station-years), because NEWA's code caps each day's high temperature at 75 °F before averaging, where Hanson et al. cap the day's average.",
            report="docs/validation/models/western-bean-cutworm.md#against-newa-on-the-same-weather",
        ),
        Check(
            kind="observations",
            against="Wisconsin's western bean cutworm pheromone trap network (DATCP), 2021–2026",
            result="In 286 trap-years with at least 25 moths, our date for half the flight fell a median 3 days before the end of the week in which half the season's moths were caught: inside that week in 135 and within a week of it in 273. The model wasn't fitted to these traps.",
            report="docs/validation/models/western-bean-cutworm.md#against-wisconsins-traps",
        ),
    ),
    citations=(
        Citation(
            text="Hanson, A. A., Moon, R. D., Wright, R. J., Hunt, T. E. and Hutchison, W. D. (2015). Degree-day prediction models for the flight phenology of western bean cutworm (Lepidoptera: Noctuidae) assessed with the concordance correlation coefficient. Journal of Economic Entomology 108, 1728–1738.",
            doi="10.1093/jee/tov110",
        ),
        Citation(
            text="NEWA, Network for Environment and Weather Applications, Cornell University: western bean cutworm model.",
            url="https://newa.cornell.edu/western-bean-cutworm",
        ),
        Citation(
            text="Dewerff, R., Bick, E., Liesch, P. J., et al. (2025). Pest Management in Wisconsin Field Crops (A3646). UW–Madison Division of Extension.",
            url="https://cropsandsoils.extension.wisc.edu/files/2025/01/A3646_2025_web.pdf",
        ),
    ),
)
