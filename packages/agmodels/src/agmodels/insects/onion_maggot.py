"""Onion maggot, rebuilt on NEWA's model (D95), checked against Eckenrode, Vea and Stone 1975 and Liu, McEwen and
Ritcey 1982 (part H, D36, D37)."""

from agmodels.phenology import ActionWindow, DerivedStage, Insect, LifeStage
from agmodels.spec import Change, Check, Citation, TrainingArea

INSECT = Insect(
    id="onion-maggot",
    name="Onion maggot",
    season=("04-01", "10-31"),
    opens="degree_days",
    crops=("onion",),
    # NEWA's method (D95): the day's simple average above 40 °F, no upper threshold, from January 1. Eckenrode et al.
    # 1975 counted above 40 °F with Arnold's correction; Liu et al. 1982 by Allen's sine above 4 °C
    base_f=40,
    upper_f=None,
    dd_method="average",
    biofix="01-01",
    source="NEWA's onion maggot model",
    ported_from="VDIFN",
    life_stages=(
        # NEWA's spring flight: first emergence 390 (taken as 5 %, where NEWA's cabbage maggot table puts its first
        # emergence) and peak (50 %) 735; Eckenrode et al. 1975's averages were 389 (initial increase) and 712 (50 %
        # catch). This curve's 5, 50 and 95 % are 390, 735 and 1,103, before NEWA's first summer flies at 1,218
        LifeStage(label="Adult flight", start=200, peak=721, end=1349),
        # Liu et al. 1982 (Ritcey and McEwen's laboratory times, above their 4.38 °C threshold; Liu et al. ran them
        # above 4 °C): pre-oviposition 103 and egg 50 °C·d (275 °F·d), larva 287 °C·d (517 °F·d)
        DerivedStage(label="Larval feeding", follows="Adult flight", lag=275, duration=517),
    ),
    # NEWA's peaks 735, 1,752 and 2,975 are 1,017 and 1,223 apart: 1,100 is the least-squares generation time over
    # both. Eckenrode et al. 1975 measured 1,187 and 1,257, and Liu et al. 1982's laboratory generation is 1,343 °F·d
    generation_dd=1100,
    # NEWA's later flights start 534 and 560 before their peaks, against 345 in spring: each spreads more. An SD of
    # 200 reproduces that roughly (the second's first flies at 1,366, the third's at 2,367, against NEWA's 1,218 and 2,415)
    generation_sd=200,
    # Three flights in New York (NEWA; Eckenrode et al. 1975) and Ontario (Liu et al. 1982); 27–91 % of the second
    # brood's pupae enter diapause (LaFrance and Perron 1959, in Eckenrode et al. 1975)
    max_generations=3,
    # Each generation by its damage (version 0.4; Ben, 2026-11-23), a judgment the papers bound but don't fix. The spring
    # generation does most of the damage to seedlings (NEWA; Eckenrode et al. 1975: 47 % of 1,127 seedlings lost by July
    # 23 at Elba, 1971), so it weighs 1. The second is the smallest brood in every New York catch (Eckenrode et al., p.
    # 787; Fig. 2's second-brood peaks about 0.03 to 0.4 of spring's), with no midsummer injury at Elba in 1971 and no
    # grower complaints in July and August; in Ontario's untreated bed it invaded 1–2 % of onions against the first's
    # 22–25 % (Liu et al. 1982, Fig. 4), 0.04 to 0.09 of it. So 0.1: the damage ratio's top, the catches' lower half.
    # The third damages bulbs near harvest (up to about 15 of 200 at Elba, Eckenrode et al. Fig. 1) and in storage, "the
    # most destructive economically" in Ontario (Liu et al., p. 754), where it's usually escaped by harvesting first
    # (Liu et al. harvested before its peak): 0.5, kept from version 0.3
    generation_weights=(1.0, 0.1, 0.5),
    action_windows=(
        # NEWA: treated seed or an in-furrow treatment at planting, or row covers before flies emerge, kept three
        # weeks past the spring peak. From first emergence (5 %) to 95 % of each flight
        ActionWindow(label="Protect onion seedlings during fly flight", stage="Adult flight", between=(0.05, 0.95)),
    ),
    version="0.6",
    status="beta",
    # NEWA's table cites Andaloro, Rose and Eckenrode 1984 (Search: Agriculture, Cornell; not in hand, title and years unknown), built on the trapping
    # Eckenrode et al. 1975 began in 1971 in New York's muck onion fields: the last year is an estimate
    trained=TrainingArea(
        description="fly trap catches in onion fields in western and central New York",
        years=(1971, 1983),
        states=("NY",),
    ),
    changelog=(
        Change(
            version="0.2",
            date="2026-11-21",
            note="Rebuilt on NEWA's onion maggot model: degree days by the simple average above 40 °F from January 1 with no upper threshold; the spring flight as a curve from NEWA's first emergence and peak, larval feeding timed from it (Liu, McEwen and Ritcey 1982), and two later flights 1,100 degree days apart, as NEWA's three. Replaces VDIFN's two windows (single sine 39.2/86 °F, source not identified), which had no third flight.",
        ),
        Change(
            version="0.3",
            date="2026-11-23",
            note="The summer flights weigh half as much as the spring flight in the risk, since the spring generation does most of the damage to seedlings.",
        ),
        Change(
            version="0.4",
            date="2026-11-23",
            note="The second flight weighs a tenth of the spring flight in the risk and the third half: the second generation was the smallest in New York's traps and did a tenth or less of the first's damage in Ontario (Eckenrode, Vea and Stone 1975, p. 787; Liu, McEwen and Ritcey 1982, Fig. 4), while the third damages bulbs near harvest and in storage.",
        ),
        Change(
            version="0.5",
            date="2026-11-26",
            note="In season from April 1 to October 31: from a week before its earliest activity on 2016–2025's weather at six Wisconsin places to October 31, the end of Wisconsin's growing season. Activity ends after October 31 whatever the weather, as fall freezes end it, so a mild fall no longer holds a stalled curve's activity into winter.",
        ),
        Change(
            version="0.6",
            date="2026-11-26",
            note="The season opens at each place about a week before the first adult flight in a typical year (the day the 30-year normal degree days, averaged over about 50 km, reach it), rather than on April 1 everywhere; where we don't have the normals, it still opens on April 1.",
        ),
    ),
    checks=(
        Check(
            kind="published",
            against="NEWA's onion maggot table, and fly trap catches in New York onion fields, 1971–1974 (Eckenrode, Vea and Stone 1975)",
            result="The spring flight's first flies (5 %) come at 390 degree days and half at 735, as NEWA's table has them. Later flights' midpoints come 79 degree days after NEWA's 1,752 and 45 before its 2,975. In New York fields the spring flight's midpoint averaged 712 and the next two came 1,187 and 1,257 later, against the model's 1,100.",
            report="docs/validation/models/onion-maggot.md#against-its-sources-numbers",
        ),
        Check(
            kind="system",
            against="NEWA's onion maggot model on the weather of 34 Wisconsin NEWA stations, 2024 and 2025",
            result="The model reproduces NEWA's events: first emergence and the spring peak fall on NEWA's day, and the later flights within 2 to 3 days at the median.",
            report="docs/validation/models/onion-maggot.md#against-newa-on-the-same-weather",
        ),
    ),
    citations=(
        Citation(
            text="NEWA, Network for Environment and Weather Applications, Cornell University: onion maggot model.",
            url="https://newa.cornell.edu/onion-maggot",
        ),
        Citation(
            text="Eckenrode, C. J., Vea, E. V. and Stone, K. W. (1975). Population trends of onion maggots correlated with air thermal unit accumulations. Environmental Entomology 4, 785–789.",
            doi="10.1093/ee/4.5.785",
        ),
        Citation(
            text="Liu, H. J., McEwen, F. L. and Ritcey, G. (1982). Forecasting events in the life cycle of the onion maggot, Hylemya antiqua (Diptera: Anthomyiidae): application to control schemes. Environmental Entomology 11, 751–755.",
            doi="10.1093/ee/11.3.751",
        ),
    ),
)
