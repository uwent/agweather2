"""Common asparagus beetle, rebuilt on UW–Madison's degree-day table (Delahaut's XHT1087) for the overwintered beetles'
egg laying on spears, with larvae and later generations from UW–Madison's development times (part H, D36, D37)."""

from agmodels.phenology import ActionWindow, DerivedStage, Insect, LifeStage
from agmodels.spec import Change, Check, Citation, TrainingArea

# UW–Madison (XHT1137; UW Veg Ento) gives the stages in days: eggs hatch in about a week, larvae feed for about two
# weeks, and new adults emerge about a week after the larvae go to the soil. At the normal rate of late May (about 14
# degree days a day, modified 50/86 °F, at Arlington) a week is about 100
EGG = 100
# The larvae: 300, the span of VDIFN's window from first hatch (105) to the last larvae (405), whose source isn't
# known; UW's two weeks at June's normal 16 to 17 a day would be 230 to 240. A judgment, kept as VDIFN's
LARVAE = 300

INSECT = Insect(
    id="common-asparagus-beetle",
    name="Common asparagus beetle",
    crops=("asparagus",),
    # UW–Madison's method (XHT1086/XHT1087, Delahaut 2012): the modified average, the minimum raised to 50 °F and the
    # maximum capped at 86 °F, from January 1 (the stored `dd_modified_50_86`). NEWA runs no asparagus beetle model
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
    # Adult to adult: the egg (100), the larvae (300), the pupa (about a week, 120 at June's rate) and a few days of
    # feeding before the new beetles lay (about 80), 600. A judgment from UW's days: no source gives the generation in
    # degree days (Taylor and Harcourt 1978's development rates aren't in hand)
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
    version="0.2",
    status="beta",
    # XHT1087 gives no years for its numbers; the span runs from its last revision (2012) to XHT1137's (2026)
    trained=TrainingArea(
        description="egg laying in Wisconsin, as UW–Madison's degree-day table gives it, and UW–Madison's description of the beetle's development",
        years=(2012, 2026),
        states=("WI",),
    ),
    changelog=(
        Change(
            version="0.2",
            date="2026-11-21",
            note="Rebuilt on UW–Madison's degree-day table (Delahaut's XHT1087; the modified average, 50/86 °F, from January 1): the overwintered beetles feeding and laying eggs on spears as a curve whose 10 and 50 % are the table's 150 and 240 degree days, larvae timed from them, and up to three generations 600 degree days apart (from UW–Madison's development times; Taylor 1979 found three in Ontario). Adults and larvae both count in the risk. Replaces VDIFN's one larval window (105, 250, 405 degree days, single sine 50/86 °F), whose source isn't known and which left out the beetles on spears and the summer generations.",
        ),
    ),
    checks=(
        Check(
            kind="published",
            against="UW–Madison's degree-day table for asparagus beetle (Delahaut, XHT1087)",
            result="The table's egg laying at 150 to 240 degree days is the overwintered beetles' 10 and 50 %, at 149 and 239. The larvae and the time between generations are judgments from UW–Madison's development times in days, not from a degree-day study.",
            report="docs/validation/models/common-asparagus-beetle.md#against-its-sources-numbers",
        ),
        Check(
            kind="published",
            against="UW–Madison's and Commercial Vegetable Production in Wisconsin's descriptions of the season, on AgWeather's 1996–2025 normals",
            result="The beetles become active in late April in southern Wisconsin and early May in the north, and half are out by May 10 at Arlington and May 20 at Rhinelander, as UW–Madison and A3422 describe (adults in April to early May). The second generation's beetles peak in mid to late June and the third in mid to late July.",
            report="docs/validation/models/common-asparagus-beetle.md#on-the-normals",
        ),
    ),
    citations=(
        Citation(
            text="Delahaut, K. Degree Days for Common Fruit & Vegetable Insect Pests (XHT1087). UW–Madison Division of Extension, Wisconsin Horticulture, revised 2012.",
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
