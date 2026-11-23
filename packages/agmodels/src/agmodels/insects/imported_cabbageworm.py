"""Imported cabbageworm, rebuilt on UW–Madison's degree-day table (Delahaut's XHT1087, 2005) for the spring flight,
with later generations from development times (Tatchell 1981's larvae, Nealis et al. 1984's pupae; part H, D36, D37),
checked against iNaturalist."""

from agmodels.phenology import ActionWindow, DerivedStage, Insect, LifeStage
from agmodels.spec import Change, Check, Citation, TrainingArea

# Development in degree days (°F, base 50). The egg from UW–Madison's days at about 21 DD50 a day, the normal daily
# total in July at Arlington (modified 50/86): about 5 days (UW Veg Ento; "about a week", UW Hort), and egg laying
# centered about 5 days after a butterfly emerges (a judgment: females lay over their 2–3 weeks). The larva is Tatchell
# 1981's 349 °F·d above 48.9 °F (193.9 °C·d above 9.4 °C, his p. 293 and Table 2), taken as DD50 (the 1 °F difference
# is about 15 °F·d over the larval period). The pupa is Nealis, Jones and Wellington 1984's 107.0 °C·d above 10.4 °C
# (Table 1, p. 225; Vancouver, from N. Gilbert's unpublished data): 193 °F·d above 50.7 °F, taken as DD50 (Ben,
# 2026-11-23; it replaces 180, 8.5 days from UW's 6–11). Nealis et al. also give the egg and larva together, 216.8 °C·d
# above 10.0 °C (390 DD50), shorter than UW's egg and Tatchell's larva (454): not used, since they don't split the egg
# from the larva. The pupa enters only the generation time's check (the flights are 840 apart, set from Wisconsin's
# records), so the model's output doesn't change with it
EGG_LAYING_LAG = 105
EGG = 105
LARVA = 349
PUPA = 193

INSECT = Insect(
    id="imported-cabbageworm",
    name="Imported cabbageworm",
    crops=("cole-crops",),
    # UW–Madison's method (XHT1086; XHT1087 gives only the base, 50 °F): the modified average, the minimum raised to
    # 50 °F and the maximum capped at 86 °F, from January 1 (the stored `dd_modified_50_86`). NEWA runs no cabbageworm
    # model
    base_f=50,
    upper_f=86,
    dd_method="modified",
    biofix="01-01",
    ported_from="VDIFN",
    source="UW–Madison's degree-day table for imported cabbageworm",
    life_stages=(
        # Butterflies from overwintering chrysalises: XHT1087's "adult butterflies at 150–240 DD50" are this curve's 10
        # and 50 % (149 and 239); its peak is 210 and 95 % have emerged by 394. Wisconsin's iNaturalist records peak
        # at 150–300 on the same degree days (the report). No crop feeding by butterflies
        LifeStage(label="Adult flight", start=100, peak=210, end=550, weight=0),
        # Eggs, from about 5 days after each butterfly emerges, for about 5 days; the scouting window follows them
        DerivedStage(label="Eggs", follows="Adult flight", lag=EGG_LAYING_LAG, duration=EGG, weight=0),
        # Caterpillars feed from hatch to pupation (Tatchell 1981's 349): the crop's risk
        DerivedStage(label="Larval feeding", follows="Adult flight", lag=EGG_LAYING_LAG + EGG, duration=LARVA),
    ),
    # Flight to flight: egg laying, egg, larva and pupa, 105 + 105 + 349 + 193 = 752 with the shorter readings of
    # UW's days, or about 835 with UW Hort's week-long egg and egg laying centered a week after emergence (a
    # judgment). Wisconsin's iNaturalist records of butterflies have their flights' medians 832 and 861 apart
    # (scripts/check_imported_cabbageworm.py), so 840, at the top of the development times' range
    generation_dd=840,
    # No cap: UW–Madison gives usually three generations, UW Veg Ento three to six; the season's degree days limit
    # them (three flights in the normal season everywhere, a fourth begun at Arlington by October), and fall freezes
    # end it
    # UW–Madison: the second generation does the most damage. It weighs 1 and the others 0.5: the sources say which
    # generation matters, not by how much, so 0.5 is a judgment (Ben, 2026-11-23)
    generation_weights=(0.5, 1.0, 0.5),
    action_windows=(
        # Scout weekly all season (A3422); this marks when each generation's young caterpillars are hatching, from 10
        # to 90 % of its eggs hatched, when sprays work best (UW Hort: target small caterpillars)
        ActionWindow(label="Scout for eggs and young caterpillars", stage="Eggs", between=(0.1, 0.9)),
    ),
    version="0.3",
    status="beta",
    # XHT1087 gives no years for its numbers; the span runs from Tatchell's study (1981) to the last iNaturalist
    # records the generation time was set from (2026)
    trained=TrainingArea(
        description="the spring butterfly flight in Wisconsin, as UW–Madison's degree-day table gives it, the spacing of later flights in iNaturalist records in Wisconsin, and caterpillar development measured in the laboratory in England",
        years=(1981, 2026),
        states=("WI",),
    ),
    changelog=(
        Change(
            version="0.2",
            date="2026-11-21",
            note="Rebuilt on UW–Madison's degree-day table (Delahaut's XHT1087; the modified average, 50/86 °F, from January 1): the spring butterfly flight as a curve whose 10 and 50 % are the table's 150 and 240 degree days, eggs and caterpillar feeding timed from it (Tatchell 1981's 349 degree days for the caterpillars), later generations every 840 degree days to the season's end (within the range development times give, and the spacing of Wisconsin's iNaturalist records), and a window to scout for eggs and young caterpillars. Risk follows the caterpillars, not the butterflies. Replaces VDIFN's two windows on single sine 50 °F, whose summer window stood in for every later generation.",
        ),
        Change(
            version="0.3",
            date="2026-11-23",
            note="The second generation's caterpillars weigh twice as much as the others' in the risk, since UW–Madison says the second generation does the most damage.",
        ),
    ),
    checks=(
        Check(
            kind="published",
            against="UW–Madison's degree-day table for imported cabbageworm (Delahaut, XHT1087)",
            result="The table's butterflies at 150 to 240 degree days are the spring flight's 10 and 50 %, at 149 and 239.",
            report="docs/validation/models/imported-cabbageworm.md#against-its-sources-numbers",
        ),
        Check(
            kind="observations",
            against="iNaturalist research-grade records of cabbage white butterflies in Wisconsin, 2016–2026",
            result="Records, corrected for observers' effort, put the middle of the spring flight at 234 degree days, against the model's 239 from UW–Madison's table. The middles of the next two flights, at 1,066 and 1,927, set the model's generation time, so the model's 1,083 and 1,924 there show the fit, not a test.",
            report="docs/validation/models/imported-cabbageworm.md#against-inaturalist-records",
        ),
    ),
    citations=(
        Citation(
            text="Delahaut, K. (2005). Degree Days for Common Fruit and Vegetable Insect Pests (University of Wisconsin Garden Facts XHT1087, revised April 20, 2005). University of Wisconsin–Extension, Cooperative Extension; revised 2012, UW–Madison Division of Extension, Wisconsin Horticulture.",
            url="https://hort.extension.wisc.edu/articles/degree-days-common-fruit-vegetable-insect-pests/",
        ),
        Citation(
            text="Tatchell, G. M. (1981). The effects of a granulosis virus infection and temperature on the food consumption of Pieris rapae (Lep.: Pieridae). Entomophaga 26, 291–299.",
            doi="10.1007/BF02371879",
        ),
        Citation(
            text="Nealis, V. G., Jones, R. E. and Wellington, W. G. (1984). Temperature and development in host-parasite relationships. Oecologia 61, 224–229.",
            doi="10.1007/BF00396765",
        ),
        Citation(
            text="UC IPM, University of California: imported cabbageworm degree-day model (Tatchell 1981).",
            url="https://ipm.ucanr.edu/weather/phenology-models-description/imported-cabbageworm/",
        ),
        Citation(
            text="Liesch, P. J. and Groves, R. Imported Cabbageworm. UW–Madison Division of Extension, Wisconsin Horticulture, revised 2026.",
            url="https://hort.extension.wisc.edu/articles/imported-cabbageworm",
        ),
        Citation(
            text="iNaturalist research-grade observations of Pieris rapae in Wisconsin, 2016–2026.",
            url="https://www.inaturalist.org/observations?taxon_id=55626&place_id=32&quality_grade=research",
        ),
    ),
)
