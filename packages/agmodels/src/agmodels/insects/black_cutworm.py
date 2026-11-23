"""Black cutworm, rebuilt on Kaster and Showers 1984's outdoor development times (with Luckmann et al. 1976's egg)
from a significant moth capture, with a default capture date from Wisconsin's pheromone trap network (part H, D36,
D37, D97)."""

from agmodels.phenology import ActionWindow, DerivedStage, Insect, LifeStage
from agmodels.spec import Change, Check, Citation, TrainingArea

# Kaster and Showers 1984, Table 1: median °C·d above 10.4 °C from hatch, larvae reared on diet outdoors in weather
# shelters at Ankeny, Iowa, in spring (April 30 to June 30, 1981–1982): the fourth instar (when caterpillars can cut)
# 105.7, pupation 288.3. Spring, because spring larvae are the ones that cut corn; their summer times (105.9, 331.9) did
# not differ significantly. They reared from hatch, so the egg is Luckmann et al. 1976's (Table 2, median 52 °C·d from
# oviposition, constant temperatures in the laboratory). After the egg is laid: hatch 52 × 1.8 = 94, fourth instar
# (52 + 105.7) × 1.8 = 284, pupation (52 + 288.3) × 1.8 = 613 °F·d. Luckmann's own times (fourth instar 170, pupation
# 405 °C·d from oviposition: 306 and 729 °F·d), from constant temperatures, ran behind larvae under outdoor ones
HATCH_F = 94
FOURTH_INSTAR_F = 284
PUPATION_F = 613

INSECT = Insect(
    id="black-cutworm",
    name="Black cutworm",
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
        "melon",
        "mint",
        "pea",
        "potato",
        "tomato",
    ),
    # Single sine 50/86 °F: the extension tables' base (Purdue, Iowa State) and USPest's thresholds. Luckmann et al.
    # 1976's threshold, which Kaster and Showers 1984 counted on too, is 10.44 °C (50.8 °F): counting from 50 °F instead adds about 40 °F·d over May and June and
    # puts cutting's start 1–2 days earlier and its end 2–3 days earlier on the archive (Arlington and Rhinelander,
    # 2016–2025), less than the weekly trap dates resolve, and 50.8 would need a running total of its own. Their
    # rates are linear from 18 to 30 °C, so the 86 °F cutoff is kept. Air temperature, not soil: Kaster and Showers 1984
    # found the two gave much the same predictions
    base_f=50,
    upper_f=86,
    # The biofix is a significant moth capture (Iowa State, Minnesota: 8 or more moths in a pheromone trap over two
    # nights; DATCP: 9). Without a grower's date, May 1: the median first week with 9 or more moths in DATCP's black
    # cutworm pheromone network, 2021–2023 and 2026 (129 site-years; scripts/check_cutworms.py). The moths are
    # migrants, so their arrival follows storms rather than local degree days: a fixed date fitted those weeks better
    # than a fixed degree-day total (mean error 10.3 against 11.3 days)
    biofix="05-01",
    biofix_label="A significant moth capture in a pheromone trap; without a date, May 1",
    source="Kaster and Showers 1984, Luckmann et al. 1976",
    life_stages=(
        # Females lay over the weeks after a capture, as moths keep arriving: DATCP's traps catch half their moths
        # after the significant week within about 60 degree days and 90 % within about 240, while traps are still
        # read (scripts/check_cutworms.py). Egg laying is spread the same way, peaking soon after the capture (its 10,
        # 50 and 90 % at 23, 82 and 174); the tables in Purdue's and Iowa State's guides count every egg from the
        # capture itself
        LifeStage(label="Egg laying", start=0, peak=50, end=350, weight=0),
        # First to third instars feed on leaves (Purdue, Iowa State): from hatch to the third molt
        DerivedStage(
            label="Leaf-feeding caterpillars",
            follows="Egg laying",
            lag=HATCH_F,
            duration=FOURTH_INSTAR_F - HATCH_F,
            weight=0,
        ),
        # Fourth to sixth instars cut plants, until they pupate in the soil (Kaster and Showers 1984); the risk
        DerivedStage(
            label="Cutting caterpillars",
            follows="Egg laying",
            lag=FOURTH_INSTAR_F,
            duration=PUPATION_F - FOURTH_INSTAR_F,
        ),
    ),
    # One generation: the moths arriving in spring give the caterpillars that cut seedlings; later generations feed on
    # larger plants and weeds and rarely damage corn (Minnesota)
    action_windows=(
        # From the first caterpillars big enough to cut (1 % of the generation in the cutting stages, 289 after the
        # capture; Purdue's and Iowa State's table has 312) until 90 % have pupated (787): scouting and any treatment belong
        # while cutting caterpillars are present, not after a share has passed through (part H, round 2)
        ActionWindow(
            label="Scout and treat while caterpillars can cut plants",
            stage="Cutting caterpillars",
            between=(0.01, 0.9),
            when="present",
        ),
    ),
    version="0.4",
    status="beta",
    trained=TrainingArea(
        description="caterpillar development measured outdoors in weather shelters in Iowa, the egg's in the laboratory in Illinois, and the default capture date from the first weeks with 9 or more moths in Wisconsin's black cutworm pheromone traps",
        years=(1975, 2026),
        states=("IA", "IL", "WI"),
    ),
    changelog=(
        Change(version="0.1", date="2026-10-28", note="Ported from VDIFN."),
        Change(
            version="0.2",
            date="2026-11-21",
            note="Rebuilt on Luckmann et al. 1976: from a significant moth capture (May 1 without a date, from DATCP's pheromone traps), egg laying, leaf-feeding caterpillars and cutting caterpillars (fourth instar to pupation, 306 to 729 degree days after an egg is laid), single sine 50/86 °F. Replaces VDIFN's window (300, 700, 1,000 degree days from May 15), which peaked after cutting ends.",
        ),
        Change(
            version="0.4",
            date="2026-11-23",
            note="A window to scout and treat while caterpillars can cut plants: from the first caterpillars big enough to cut (about 310 degree days after the capture) until 90 % have pupated (about 900).",
        ),
        Change(
            version="0.4",
            date="2026-11-23",
            note="Caterpillar development from Kaster and Showers 1984 (Table 1, spring), measured outdoors in weather shelters in Iowa, in place of Luckmann et al. 1976's constant laboratory temperatures, with Luckmann's egg: the fourth instar 284 degree days after an egg is laid (was 306) and pupation 613 (was 729). The window to scout and treat now runs from about 290 to 790 degree days after the capture (was 311 to 903), ending about 6 days sooner in a normal June.",
        ),
    ),
    checks=(
        Check(
            kind="published",
            against="Kaster and Showers 1984's and Luckmann et al. 1976's development times, and Purdue's and Iowa State's stage table for black cutworm",
            result="The first caterpillars hatch 99 degree days after the moth capture, as the table's 90, and the first reach cutting size at 289, a day or so before the table's 312; the window to scout and treat opens then. Each caterpillar pupates 613 degree days after its egg is laid, near the table's pupae from 641; with egg laying spread over the weeks after the capture, half the caterpillars have pupated by 695 degree days and 90 % by 788, inside the table's pupal span to 989.",
            report="docs/validation/models/black-cutworm.md#against-its-sources-numbers",
        ),
        Check(
            kind="observations",
            against="Wisconsin's black cutworm pheromone trap network (DATCP), 2021–2023 and 2026",
            result="The default capture date, May 1, is the median first week with 9 or more moths in 129 trap-years, and fell within 7 days of that week in 60 of them. A fixed degree-day total did worse, within 7 days in 45. The date was set from these same traps, so this shows how well it fits them, not a test on new years.",
            report="docs/validation/models/black-cutworm.md#the-default-capture-date-against-wisconsins-traps",
        ),
    ),
    citations=(
        Citation(
            text="Kaster, L. V. and Showers, W. B. (1984). Modeling black cutworm (Lepidoptera: Noctuidae) field development in Iowa. Environmental Entomology 13, 384–389.",
            doi="10.1093/ee/13.2.384",
        ),
        Citation(
            text="Luckmann, W. H., Shaw, J. T., Sherrod, D. W. and Ruesink, W. G. (1976). Developmental rate of the black cutworm. Journal of Economic Entomology 69, 386–388.",
            doi="10.1093/jee/69.3.386",
        ),
        Citation(
            text="Story, R. N., Keaster, A. J., Showers, W. B. and Shaw, J. T. (1984). Survey and phenology of cutworms (Lepidoptera: Noctuidae) infesting field corn in the Midwest. Journal of Economic Entomology 77, 491–494.",
            doi="10.1093/jee/77.2.491",
        ),
        Citation(
            text="Krupke, C. and Obermeyer, J. (2023). Timing black cutworm scouting. Pest&Crop Newsletter, Purdue University.",
            url="https://extension.entm.purdue.edu/newsletters/pestandcrop/article/timing-black-cutworm-scouting",
        ),
        Citation(
            text="Dean, A. and Hodgson, E. Black cutworm. Iowa State University Extension and Outreach.",
            url="https://crops.extension.iastate.edu/encyclopedia/black-cutworm",
        ),
        Citation(
            text="Wisconsin Department of Agriculture, Trade and Consumer Protection: black cutworm pheromone trap counts, 2021–2023 and 2026.",
            url="https://datcp.wi.gov/Pages/Programs_Services/TrapNetworks.aspx",
        ),
    ),
)
