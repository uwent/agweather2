"""Common asparagus beetle, rebuilt on UW–Madison's degree-day table (Delahaut's XHT1087) for the overwintered beetles'
egg laying on spears, with larvae and later generations from Taylor and Harcourt 1978's development times (part H,
D36, D37)."""

from agmodels.phenology import ActionWindow, DerivedStage, Insect, LifeStage
from agmodels.spec import Change, Check, Citation, TrainingArea

# Taylor and Harcourt 1978 (Ottawa, laboratory, base 10 °C; p. 62): egg 58 °C·d (104 °F·d above 50 °F), larval
# instars 21 + 26 + 32 + 88 = 167 (301; the fourth includes the prepupa in the soil), pupa 92 (166). VDIFN's window
# (105, 250, 405) and its new adults at about 570 are these sums from egg laying. The model's egg and larvae round them
# (UW–Madison's week for the egg, about 14 degree days a day in late May at Arlington, gives the same 100). The pupa,
# 166 (their 92 °C·d), and the days from new adults to their first eggs make up the rest of a generation (below)
EGG = 100
LARVAE = 300

INSECT = Insect(
    id="common-asparagus-beetle",
    name="Common asparagus beetle",
    season=("03-15", "10-31"),
    opens="degree_days",
    crops=("asparagus",),
    # UW–Madison's method (XHT1086; XHT1087 gives only the 50 °F base): the modified average, the minimum raised to 50 °F
    # and the maximum capped at 86 °F, from January 1 (the stored `dd_modified_50_86`). NEWA runs no asparagus beetle
    # model
    base_f=50,
    upper_f=86,
    dd_method="modified",
    biofix="01-01",
    ported_from="VDIFN",
    source="UW–Madison's degree-day table for asparagus beetle",
    life_stages=(
        # Overwintered beetles on the spears, feeding and laying eggs: XHT1087's "egg laying 150–240 DD50" are this
        # curve's 10 and 50 % (149 and 239), as the same table's numbers for imported cabbageworm. The beetles scar
        # spears and their eggs make spears unmarketable during harvest, so adults count in the risk alongside
        # larvae (weight 1 each). Later generations' adults feed on the ferns
        LifeStage(label="Adults feeding and laying eggs", start=100, peak=210, end=550),
        # Larvae feed on spears and ferns from hatch until they drop to the soil to pupate
        DerivedStage(label="Larvae", follows="Adults feeding and laying eggs", lag=EGG, duration=LARVAE),
    ),
    # Adult to adult, from Taylor and Harcourt 1978: the egg (100), the larvae (300), the pupa (166, their 92 °C·d;
    # egg to adult 317 °C·d, 571 °F·d) and the days from new adults to the next eggs, about 30: in their field counts
    # near Ottawa in 1976 each generation's adults peaked 1 to 2 days before the next generation's eggs (July 2 and 4,
    # August 6 and 7; Table III), 20 to 40 degree days at July's normal 20 a day at Arlington. 596, kept at 600. (Until 2026-11-23 version 0.2
    # split the same 600 as a pupa of 120 and 80 before laying, from UW's days)
    generation_dd=600,
    # Three generations at most: Taylor 1979 found three in eastern Ontario; UW–Madison gives two to three. At 600 a
    # generation, southern Wisconsin's normal season (about 2,500 degree days by September 15 at Arlington) would
    # otherwise start a fourth in late August
    max_generations=3,
    action_windows=(
        # UW–Madison: scout spears from emergence and ferns all summer; thresholds for adults, eggs and larvae. This
        # marks each generation's main egg laying, from 10 to 90 % of its beetles active
        ActionWindow(label="Scout for beetles and eggs", stage="Adults feeding and laying eggs", between=(0.1, 0.9)),
    ),
    version="0.4",
    status="beta",
    # XHT1087 gives no years for its numbers; the span runs from Taylor and Harcourt's rearing (1975) to XHT1137's
    # revision (2026). Ontario has no code here, so only Wisconsin is named
    trained=TrainingArea(
        description="egg laying in Wisconsin, as UW–Madison's degree-day table gives it, and development measured in the laboratory and field near Ottawa, Ontario",
        years=(1975, 2026),
        states=("WI",),
    ),
    changelog=(
        Change(
            version="0.2",
            date="2026-11-21",
            note="Rebuilt on UW–Madison's degree-day table (Delahaut's XHT1087; the modified average, 50/86 °F, from January 1): the overwintered beetles feeding and laying eggs on spears as a curve whose 10 and 50 % are the table's 150 and 240 degree days, larvae timed from them, and up to three generations 600 degree days apart (from UW–Madison's development times; Taylor 1979 found three in Ontario). Adults and larvae both count in the risk. Replaces VDIFN's one larval window (105, 250, 405 degree days, single sine 50/86 °F), whose source isn't known and which left out the beetles on spears and the summer generations.",
        ),
        Change(
            version="0.3",
            date="2026-11-26",
            note="In season from March 15 to October 31: from a week before its earliest activity on 2016–2025's weather at six Wisconsin places to October 31, the end of Wisconsin's growing season. Activity ends after October 31 whatever the weather, as fall freezes end it, so a mild fall no longer holds a stalled curve's activity into winter.",
        ),
        Change(
            version="0.4",
            date="2026-11-26",
            note="The season opens at each place about a week before the first adults feeding and laying eggs in a typical year (the day the 30-year normal degree days, averaged over about 50 km, reach it), rather than on March 15 everywhere; where we don't have the normals, it still opens on March 15.",
        ),
    ),
    checks=(
        Check(
            kind="published",
            against="UW–Madison's degree-day table for asparagus beetle (Delahaut, XHT1087)",
            result="The table's egg laying at 150 to 240 degree days is the overwintered beetles' 10 and 50 %, at 149 and 239. The egg (100) and larvae (300) round Taylor and Harcourt 1978's 104 and 301 degree days. The time between generations (600) is their egg to adult (571, with a pupa of 166) plus about 30 for the day or two from each generation's adults to the next one's eggs in their field counts near Ottawa.",
            report="docs/validation/models/common-asparagus-beetle.md#against-its-sources-numbers",
        ),
        Check(
            kind="published",
            against="UW–Madison's and Commercial Vegetable Production in Wisconsin's descriptions of the season, on AgWeather's 1996–2025 normals",
            result="The beetles become active in late April in southern Wisconsin and early May in the north, and half are out by May 10 at Arlington and May 20 at Rhinelander, as UW–Madison and A3422 describe (adults in April to early May). The second generation's beetles peak in late June (early July at Rhinelander) and the third in late July (early August at Rhinelander).",
            report="docs/validation/models/common-asparagus-beetle.md#on-the-normals",
        ),
    ),
    citations=(
        Citation(
            text="Delahaut, K. (2005). Degree Days for Common Fruit and Vegetable Insect Pests (University of Wisconsin Garden Facts XHT1087, revised April 20, 2005). University of Wisconsin–Extension, Cooperative Extension; revised 2012, UW–Madison Division of Extension, Wisconsin Horticulture.",
            url="https://hort.extension.wisc.edu/articles/degree-days-common-fruit-vegetable-insect-pests/",
        ),
        Citation(
            text="Lowenstein, D., Groves, R. and Liesch, P. J. Asparagus Beetle (XHT1137). UW–Madison Division of Extension, Wisconsin Horticulture, revised 2026.",
            url="https://hort.extension.wisc.edu/articles/asparagus-beetle/",
        ),
        Citation(
            text="Taylor, R. G. (1979). Population dynamics of the asparagus beetle, Crioceris asparagi (L.) (Coleoptera: Chrysomelidae). PhD thesis, Carleton University.",
            doi="10.22215/etd/1979-00406",
        ),
        Citation(
            text="Taylor, R. G. and Harcourt, D. G. (1978). Effects of temperature on developmental rate of the immature stages of Crioceris asparagi (Coleoptera: Chrysomelidae). The Canadian Entomologist 110, 57–62.",
            doi="10.4039/Ent11057-1",
        ),
    ),
)
