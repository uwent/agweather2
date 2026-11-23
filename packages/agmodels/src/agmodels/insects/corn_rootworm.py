"""Corn rootworm, rebuilt on Apple, Walgenbach and Knee 1971's egg hatch of the northern corn rootworm in Wisconsin,
with larvae timed from hatch and beetles from UW–Madison's degree-day table (part H, D36, D37)."""

from agmodels.phenology import ActionWindow, DerivedStage, Insect, LifeStage
from agmodels.spec import Change, Check, Citation, TrainingArea

# Larvae feed for about three weeks (UW Vegetable Entomology; A3646): about 350 degree days above 52 °F at the normal
# rate from mid-June to mid-July (15 to 19 a day at Arlington, 12 to 16 at Rhinelander; the report). A judgment, and
# short of Jackson and Elliott 1988's western corn rootworm larvae on fresh corn seedlings at constant temperatures:
# their three instars (Table 1) come to 371–478 degree days above 52 °F at 18–27 °C (the report)
LARVAE = 350
# Hatch to beetle: UW–Madison's table (Delahaut, XHT1087) has adult beetles at 1,300 DD50 (modified average, 50/86 °F,
# from January 1), which the 1996–2025 normals reach on the days they reach 1,054 to 1,094 here (Arlington, Hancock,
# Rhinelander; the report). Taken as half the beetles out at about 1,075: 542 after half the eggs have hatched (533).
# What's left after the larvae, about 190 (11 days in July), is the pupa in its soil cell (Jackson and Elliott 1988:
# 167–195 at 18–27 °C). Davis, Brenes and Allee 1996's New York cages had half the beetles out at about 1,330–1,380
# air degree days above 11 °C (52 °F) from January 1, later than this (the report)
HATCH_TO_BEETLE = 542
# Beetles live and feed for weeks; 700 (about six weeks in July and August) is a judgment
BEETLES = 700

INSECT = Insect(
    id="corn-rootworm",
    name="Corn rootworm",
    crops=("corn", "sweet-corn"),
    # Apple, Walgenbach and Knee 1971's threshold: 52 °F (11.1 °C), from egg hatch's development rates (51.2 °F for
    # first hatch, 52.6 for median, averaging 51.9: "essentially" Chiang and Sisson 1968's 52; p. 855). Their field
    # totals came from official air temperatures a mile from the plot, by a method they don't state, and Table 3 seems
    # to count from the eggs' burial on April 15; single sine from January 1, with no upper threshold, is our choice
    # (UC IPM's recommendation for the model). Little accumulates above 52 °F before mid-April (47 on Arlington's normal
    # by April 15), so the start date matters little
    base_f=52,
    upper_f=None,
    biofix="01-01",
    ported_from="VDIFN",
    source="Apple, Walgenbach and Knee 1971",
    life_stages=(
        # Northern corn rootworm eggs from south-central Wisconsin soil (Apple et al. 1971, Table 2): first hatch at 304
        # and median at 530 degree days above 52 °F at constant temperatures in the laboratory. Eggs buried 2 inches
        # deep in a bare field plot in 1970 (Table 3) had 37 % hatched at 483 air degree days, half on June 13 (533),
        # 81 % at 651, 95 % at 832 and all at 998, with first hatch in late May at about 300. This curve starts at 300,
        # is half hatched at 533 and ends at 1,000 (35, 79, 98 and 100 % at 483, 651, 832 and 998)
        LifeStage(label="Egg hatch", start=300, peak=495, end=1000, weight=0),
        # The larvae feed on roots from hatch to pupation: the crop's risk
        DerivedStage(label="Larvae feeding on roots", follows="Egg hatch", lag=0, duration=LARVAE),
        # Beetles feed on silks and pollen and lay next year's eggs; not part of the root-feeding risk
        DerivedStage(label="Beetles", follows="Egg hatch", lag=HATCH_TO_BEETLE, duration=BEETLES, weight=0),
    ),
    # One generation a year: the eggs laid in August hatch the next spring
    action_windows=(
        # UW Vegetable Entomology and A3646: dig roots in July or August to rate the larvae's injury, before root
        # decay hides it. From half the larvae done feeding to 95 % done
        ActionWindow(
            label="Dig and rate roots for larval injury", stage="Larvae feeding on roots", between=(0.5, 0.95)
        ),
    ),
    version="0.2",
    status="beta",
    trained=TrainingArea(
        description="northern corn rootworm eggs hatched in the laboratory and in the field at Madison, Wisconsin, and UW–Madison's degree-day table for the beetles",
        years=(1967, 2012),
        states=("WI",),
    ),
    changelog=(
        Change(
            version="0.2",
            date="2026-11-21",
            note="Rebuilt on Apple, Walgenbach and Knee 1971 (northern corn rootworm in Wisconsin): single-sine degree days above 52 °F from January 1 with no upper threshold; egg hatch as a curve from 300 degree days, half hatched at 533; larvae feeding on roots for about 350 degree days after hatch (the risk); beetles half out at about 1,075, from UW–Madison's degree-day table (1,300 by the modified average above 50 °F); and a window to dig and rate roots. Replaces VDIFN's window (329, 472, 636 degree days), whose source isn't known and which closed before the larvae peak.",
        ),
    ),
    checks=(
        Check(
            kind="published",
            against="Northern corn rootworm egg hatch in Wisconsin (Apple, Walgenbach and Knee 1971)",
            result="Half the eggs have hatched at 533 degree days above 52 °F, the air temperature total on the day buried eggs reached median hatch in 1970, and hatch begins at 300, against the 304 measured in the laboratory. Those buried eggs had 37 % hatched at 483 degree days, 81 % at 651 and 95 % at 832; the model has 35, 79 and 98 %.",
            report="docs/validation/models/corn-rootworm.md#against-its-sources-numbers",
        ),
        Check(
            kind="observations",
            against="Corn rootworm larvae and beetles in 11 New York cornfields, 1991–1993 (Davis, Brenes and Allee 1996)",
            result="Half the northern corn rootworm beetles had emerged at about 1,328 degree days above 52 °F and half the western at 1,381, against the model's 1,075, and half the pupae were found at 1,148, when the model has half the larvae done feeding at 885. On Arlington's normals the model's beetles come about 13 days before those fields' totals; the model wasn't changed to match them.",
            report="docs/validation/models/corn-rootworm.md#against-larvae-and-beetles-in-new-york-fields",
        ),
        Check(
            kind="published",
            against="UW–Madison's and Iowa State's descriptions of the season on AgWeather's 1996–2025 normals",
            result="Half the eggs hatch around June 14 at Arlington and June 26 at Rhinelander, one to three weeks after central Iowa's average peak hatch (June 6, Iowa State). Larvae peak in late June in the south and early July in the north, a week or two before UW–Madison's early to mid-July, and half the beetles are out around mid-July at Arlington.",
            report="docs/validation/models/corn-rootworm.md#on-the-normals",
        ),
    ),
    citations=(
        Citation(
            text="Apple, J. W., Walgenbach, E. T. and Knee, W. J. (1971). Thermal requirements for northern corn rootworm egg hatch. Journal of Economic Entomology 64, 853–856.",
            doi="10.1093/jee/64.4.853",
        ),
        Citation(
            text="Chiang, H. C. and Sisson, V. (1968). Temperature relationships of the development of northern corn rootworm eggs. Journal of Economic Entomology 61, 1406–1410.",
            doi="10.1093/jee/61.5.1406",
        ),
        Citation(
            text="UC IPM, University of California: northern corn rootworm degree-day models (Apple, Walgenbach and Knee 1971 and others).",
            url="https://ipm.ucanr.edu/PHENOLOGY/ma-n_corn_rootworm.html",
        ),
        Citation(
            text="Delahaut, K. Degree Days for Common Fruit & Vegetable Insect Pests (XHT1087). UW–Madison Division of Extension, Wisconsin Horticulture, revised 2012.",
            url="https://hort.extension.wisc.edu/articles/degree-days-common-fruit-vegetable-insect-pests/",
        ),
        Citation(
            text="Dean, A. and Hodgson, E. Corn Rootworm Peak Egg Hatch Is Occurring. Integrated Crop Management News, Iowa State University Extension and Outreach, 2024.",
            url="https://crops.extension.iastate.edu/cropnews/2024/06/corn-rootworm-peak-egg-hatch-occurring",
        ),
        Citation(
            text="Iowa State University Extension and Outreach. Biology and Ecology of Corn Rootworm.",
            url="https://cornrootworm.extension.iastate.edu/basics/biology-and-ecology",
        ),
        Citation(
            text="Dewerff, R., Bick, E., Liesch, P. J., et al. (2025). Pest Management in Wisconsin Field Crops (A3646). UW–Madison Division of Extension.",
            url="https://cropsandsoils.extension.wisc.edu/files/2025/01/A3646_2025_web.pdf",
        ),
    ),
)
