"""Crucifer flea beetle, rebuilt with the overwintered adults' spring feeding from UW–Madison's degree-day table
(Delahaut's XHT1087) and the new generation from Kinoshita et al. 1979's development (part H, D36, D37)."""

from agmodels.phenology import ActionWindow, DerivedStage, Insect, LifeStage
from agmodels.spec import Change, Check, Citation, TrainingArea

# Kinoshita et al. 1979 (London, Ontario, p. 1402): from egg to adult 456 °C·d above 11 °C (820.6 °F·d above 51.8 °F;
# UC IPM splits it as eggs 146.2, larvae 378.0, prepupae 82.3, pupae 214.2, where the paper gives each stage on its own
# threshold), tested in the field on soil temperatures at 8 cm by a single sine (Baskerville and Emin; Table IV).
# Counted on air by the modified average 50/86 °F, the same days give 1.10 times as many degree days at Arlington,
# 1.11 at Hancock and 1.14 at Rhinelander (May 15 to August 15, 2016–2025; the report): 820.6 × 1.11 ≈ 911
EGG_TO_ADULT = 911
# Egg laying: Kinoshita et al. found the females need about 61 °C·d above about 17 °C (62.6 °F) before they can lay
# (p. 1402; 64 above 16.7 °C by their regression, p. 1399);
# from the spring peak that takes a median 361 to 372 modified degree days at the three places (the report). Here
# laying starts 300 after each beetle becomes active and lasts 300 (a judgment: UW and UMass have eggs laid in May)
EGG_LAYING_LAG = 300
EGG_LAYING = 300

INSECT = Insect(
    id="crucifer-flea-beetle",
    name="Crucifer flea beetle",
    season=("03-15", "09-30"),
    crops=("cole-crops",),
    # UW–Madison's method (XHT1086; XHT1087 gives only the base, 50 °F): the modified average, 50/86 °F, from
    # January 1 (stored). Kinoshita et al.'s threshold, 51.8 °F on soil temperatures, isn't stored; its sum is converted
    # (above)
    base_f=50,
    upper_f=86,
    dd_method="modified",
    biofix="01-01",
    ported_from="VDIFN",
    source="UW–Madison's degree-day table and Kinoshita et al. 1979",
    life_stages=(
        # First generation: overwintered adults becoming active and feeding on seedlings and transplants. XHT1087's
        # "Fleabeetles … 150-200 DD50" (2005; no species, no event named) are this curve's 10 % (144) and peak (200); the end is a judgment (the old beetles feed into
        # June and die off as they finish laying). The second generation is the new summer adults
        LifeStage(label="Adults feeding", start=100, peak=200, end=600),
        # Egg laying in the soil at the base of host plants; the larvae feed on root hairs and rarely matter
        DerivedStage(label="Egg laying", follows="Adults feeding", lag=EGG_LAYING_LAG, duration=EGG_LAYING, weight=0),
    ),
    # Adult to new adult: to the middle of egg laying (300 + 150) and Kinoshita's 911 from egg to adult, 1,361,
    # rounded to 1,350
    generation_dd=1350,
    # Two "generations" of adults: the overwintered beetles and the new summer adults, which feed and then overwinter.
    # Kinoshita et al. found one generation in 1974 and two in 1975 in Ontario, and UMass a second in late July in
    # Massachusetts; a partial third flight of adults isn't modeled
    max_generations=2,
    action_windows=(
        # UW Veg Ento: scout newly planted fields every one to two days. From 5 to 95 % of each generation's adults
        # active: 129–410 in spring
        ActionWindow(label="Scout new plantings every one to two days", stage="Adults feeding", between=(0.05, 0.95)),
    ),
    version="0.3",
    status="beta",
    # XHT1087 gives no years for its numbers; the span runs from Kinoshita et al.'s field seasons (1974–1975) to the
    # table's last revision (2012; the handout read is the 2005 revision). Ontario has no code here, so only Wisconsin is named
    trained=TrainingArea(
        description="adult activity in Wisconsin, as UW–Madison's degree-day table gives it, and development measured in the laboratory and field in southwestern Ontario",
        years=(1974, 2012),
        states=("WI",),
    ),
    changelog=(
        Change(
            version="0.2",
            date="2026-11-21",
            note="Rebuilt with the overwintered adults' spring feeding on seedlings as the first stage (UW–Madison's degree-day table, Delahaut's XHT1087: 150 to 200 degree days by the modified average, 50/86 °F, from January 1), their egg laying, and the new summer adults 1,350 degree days later, from Kinoshita et al. 1979's development from egg to adult. Replaces VDIFN's two summer windows (single sine 50 °F), which left out the spring beetles that do the most damage.",
        ),
        Change(
            version="0.3",
            date="2026-11-26",
            note="In season from March 15 to September 30: from a week before its earliest activity on 2016–2025's weather at six Wisconsin places to the end of the month its latest activity ended in (September 21). Activity ends after September 30 whatever the weather, as fall freezes end it, so a mild fall no longer holds a stalled curve's activity into winter.",
        ),
    ),
    checks=(
        Check(
            kind="published",
            against="UW–Madison's degree-day table for flea beetles (Delahaut, XHT1087)",
            result="The table's flea beetles at 150 to 200 degree days are the spring adults' 10 % at 144 and peak at 200.",
            report="docs/validation/models/crucifer-flea-beetle.md#against-its-sources-numbers",
        ),
        Check(
            kind="published",
            against="Kinoshita et al. 1979 (southwestern Ontario) and UMass's account of new adults in Massachusetts",
            result="On the 1996–2025 normals the new summer adults peak in late July in southern Wisconsin and early August in the north, after UMass's late June in Massachusetts.",
            report="docs/validation/models/crucifer-flea-beetle.md#on-the-normals",
        ),
    ),
    citations=(
        Citation(
            text="Delahaut, K. (2005). Degree Days for Common Fruit and Vegetable Insect Pests (University of Wisconsin Garden Facts XHT1087, revised April 20, 2005). University of Wisconsin–Extension, Cooperative Extension; revised 2012, UW–Madison Division of Extension, Wisconsin Horticulture.",
            url="https://hort.extension.wisc.edu/articles/degree-days-common-fruit-vegetable-insect-pests/",
        ),
        Citation(
            text="Kinoshita, G. B., Svec, H. J., Harris, C. R. and McEwen, F. L. (1979). Biology of the crucifer flea beetle, Phyllotreta cruciferae (Coleoptera: Chrysomelidae), in southwestern Ontario. The Canadian Entomologist 111, 1395–1407.",
            doi="10.4039/Ent1111395-12",
        ),
        Citation(
            text="UC IPM, University of California: crucifer flea beetle degree-day model (Kinoshita et al. 1979).",
            url="https://ipm.ucanr.edu/weather/phenology-models-description/crucifer-flea-beetle/",
        ),
        Citation(
            text="UMass Extension Vegetable Program. Flea Beetle Biology. University of Massachusetts Amherst.",
            url="https://www.umass.edu/agriculture-food-environment/vegetable/fact-sheets/flea-beetle-biology",
        ),
    ),
)
