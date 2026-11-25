"""Corn rootworm, rebuilt on Apple, Walgenbach and Knee 1971's egg hatch of the northern corn rootworm in Wisconsin,
with larvae and pupae timed from hatch by Davis, Brenes and Allee 1996's New York fields and Jackson and Elliott 1988's
laboratory (part H, D36, D37)."""

from agmodels.phenology import ActionWindow, DerivedStage, Insect, LifeStage
from agmodels.spec import Change, Check, Citation, TrainingArea

# Larvae: about 550 degree days above 52 °F from hatch to pupation. Davis, Brenes and Allee 1996's New York fields took
# 532 from half the first instars (616) to half the pupae (1,148; Tables 3 and 4, air, sine above 11 °C from January
# 1), above Jackson and Elliott 1988's 371–478 for western corn rootworm larvae on fresh corn seedlings at 18–27 °C
# (Table 1), as field larvae should be. At the normal rate from mid-June to mid-July (18 a day at Arlington, 15 at
# Rhinelander) it's about a month, longer than the three weeks UW Vegetable Entomology gives each larva
LARVAE = 550
# Hatch to beetle: the larvae (550) and the pupa in its soil cell, about 200 (Jackson and Elliott 1988: 167–195 at
# 18–27 °C; Davis et al.'s fields: 180–233 from half the pupae to half the beetles). Half the beetles are then out at
# about 1,283 (533 + 750), near Davis et al.'s 1,328 (northern) and 1,381 (western), and 10 % at about 1,140, which
# the 1996–2025 normals reach at Arlington within the old three-year Arlington study's first beetles (July 16–24, UW
# Vegetable Entomology). UW–Madison's table (Delahaut 2005, XHT1087: "adult beetles present at 1300 DD50", by
# the modified of XHT1086's two methods, 50/86 °F, from January 1) then reads as the first beetles: the normals reach it on the
# days they reach 1,054 to 1,094 above 52 °F, when 0 to 3 % of the model's beetles are out
HATCH_TO_BEETLE = 750
# Beetles live and feed for weeks; 700 (about six weeks in July and August) is a judgment
BEETLES = 700

INSECT = Insect(
    id="corn-rootworm",
    name="Corn rootworm",
    season=("05-15", "09-30"),
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
        # is half hatched at 533 and ends at 1,000 (35, 79, 98 and 100 % at 483, 651, 832 and 998). Western corn
        # rootworm eggs aren't timed separately: half hatched at 509 (South Dakota; Fisher 1989 as Levine,
        # Oloumi-Sadeghi and Ellis 1992 give it, p. 2430) to 650 (Illinois eggs under monthly soil temperatures; Levine
        # et al. 1992, p. 2430) degree days above 51.8 °F, which this curve has 43 to 78 % hatched by; their constant-
        # temperature medians (Wilde 1971, Table 1: 656–850 at 20–25 °C; Levine et al.: 767) run about 17 % above
        # hatch under changing temperatures (Levine et al., p. 2429). Levine et al.'s hatch took 8 days from 10 to 50 %
        # and 10 from 50 to 90 %; this curve takes 10 and 11 on Arlington's normal
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
    version="0.4",
    status="beta",
    # Apple et al.'s eggs at Madison (1967–1970) and Davis et al.'s 11 cornfields in Tompkins, Cayuga, Schuyler and
    # Cortland counties, New York (1991–1993)
    trained=TrainingArea(
        description="northern corn rootworm eggs hatched in the laboratory and in the field at Madison, Wisconsin, and larvae, pupae and beetles sampled in cornfields in central New York",
        years=(1967, 1993),
        states=("WI",),
        counties=("36109", "36011", "36097", "36023"),
    ),
    changelog=(
        Change(
            version="0.2",
            date="2026-11-21",
            note="Rebuilt on Apple, Walgenbach and Knee 1971 (northern corn rootworm in Wisconsin): single-sine degree days above 52 °F from January 1 with no upper threshold; egg hatch as a curve from 300 degree days, half hatched at 533; larvae feeding on roots for about 350 degree days after hatch (the risk); beetles half out at about 1,075, from UW–Madison's degree-day table (1,300 by the modified average above 50 °F); and a window to dig and rate roots. Replaces VDIFN's window (329, 472, 636 degree days), whose source isn't known and which closed before the larvae peak.",
        ),
        Change(
            version="0.3",
            date="2026-11-23",
            note="Larvae feed for about 550 degree days after hatch (from 350) and the pupa takes about 200, so half the beetles are out about 750 after half the eggs have hatched (from 542): Davis, Brenes and Allee 1996's New York cornfields took 532 from half the first instars to half the pupae (Tables 3 and 4), and Jackson and Elliott 1988's pupae 167–195 (Table 1). Half the beetles now come at about 1,283 degree days (from 1,075), and UW–Madison's 1,300 DD50 for adult beetles (Delahaut 2005, XHT1087) marks the first beetles. On Arlington's 1996–2025 normals the larvae peak about July 3 (from June 24), the window to dig roots opens about July 15 (from July 4) and half the beetles are out about July 25 (from July 15).",
        ),
        Change(
            version="0.4",
            date="2026-11-26",
            note="In season from May 15 to September 30: from a week before its earliest activity on 2016–2025's weather at six Wisconsin places to the end of the month its latest activity ended in (September 2). Activity ends after September 30 whatever the weather, as fall freezes end it, so a mild fall no longer holds a stalled curve's activity into winter.",
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
            result="Half the pupae were found at 1,148 degree days above 52 °F, and half the northern and western beetles had emerged at 1,328 and 1,381. The model has half the larvae done feeding at 1,083 and half the beetles out at 1,283, 3 days and 2 to 5 days before those totals on Arlington's normals. The larvae's 550 degree days come from these fields (532 from half the first instars to half the pupae), so the check isn't independent.",
            report="docs/validation/models/corn-rootworm.md#against-larvae-and-beetles-in-new-york-fields",
        ),
        Check(
            kind="published",
            against="Western corn rootworm egg hatch in the laboratory (Wilde 1971; Levine, Oloumi-Sadeghi and Ellis 1992)",
            result="Western corn rootworm eggs were half hatched at 509 to 650 degree days above 51.8 °F under changing temperatures (South Dakota and Illinois eggs), when the model has 43 to 78 % hatched. Studies at constant temperatures give more (656 to 850 for Minnesota eggs, 767 for Illinois eggs), as constant temperatures usually do. Western hatch isn't timed separately.",
            report="docs/validation/models/corn-rootworm.md#against-western-corn-rootworm-egg-hatch",
        ),
        Check(
            kind="published",
            against="UW–Madison's and Iowa State's descriptions of the season on AgWeather's 1996–2025 normals",
            result="Half the eggs hatch around June 14 at Arlington and June 26 at Rhinelander, one to three weeks after central Iowa's average peak hatch (June 6, Iowa State). Larvae peak around July 3 at Arlington and July 17 at Rhinelander, in UW–Madison's early to mid-July. The first beetles come around July 15 at Arlington, the day the normals reach UW–Madison's 1,300 degree days above 50 °F for adult beetles, and 10 % are out by July 18, within the July 16 to 24 when an older three-year study at Arlington found the first beetles.",
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
            text="Davis, P. M., Brenes, N. and Allee, L. L. (1996). Temperature dependent models to predict regional differences in corn rootworm (Coleoptera: Chrysomelidae) phenology. Environmental Entomology 25, 767–775.",
            doi="10.1093/ee/25.4.767",
        ),
        Citation(
            text="Jackson, J. J. and Elliott, N. C. (1988). Temperature-dependent development of immature stages of the western corn rootworm, Diabrotica virgifera virgifera (Coleoptera: Chrysomelidae). Environmental Entomology 17, 166–171.",
            doi="10.1093/ee/17.2.166",
        ),
        Citation(
            text="UC IPM, University of California: northern corn rootworm degree-day models (Apple, Walgenbach and Knee 1971 and others).",
            url="https://ipm.ucanr.edu/PHENOLOGY/ma-n_corn_rootworm.html",
        ),
        Citation(
            text="Delahaut, K. (2005). Degree Days for Common Fruit and Vegetable Insect Pests (University of Wisconsin Garden Facts XHT1087, revised April 20, 2005). University of Wisconsin–Extension, Cooperative Extension; revised 2012, UW–Madison Division of Extension, Wisconsin Horticulture.",
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
