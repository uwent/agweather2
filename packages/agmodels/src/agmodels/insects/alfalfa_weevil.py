"""Alfalfa weevil, on NEWA's model (D95): Harcourt 1981's stage peaks, simple average degree days from January 1 (D36,
D37)."""

from agmodels.insects import CRT
from agmodels.phenology import ActionWindow, DerivedStage, Insect, LifeStage
from agmodels.spec import Change, Check, Citation, TrainingArea

INSECT = Insect(
    id="alfalfa-weevil",
    name="Alfalfa weevil",
    season=("04-01", "07-31"),
    crops=("alfalfa",),
    # NEWA's method (D95): the simple average above 48 °F, no upper threshold, from January 1. Harcourt 1981, whose
    # numbers NEWA's table carries, counted single sine above 9 °C from April 1; on his own 1977–1980 validation dates
    # (Table II) NEWA's rule runs a day or two later than his (docs/validation/models/alfalfa-weevil.md)
    base_f=48,
    upper_f=None,
    dd_method="average",
    biofix="01-01",
    life_stages=(
        # Half the eggs hatched at 280 (NEWA's table: Harcourt's 155 °C·d × 1.8). The spread is a choice: the widest
        # symmetric curve that begins no earlier than January 1 (10 and 90 % at 138 and 422), half as wide as
        # Harcourt's probit of hatch on heat units (Fig. 1: SD 116 °C·d), whose pooled sites and years put its tails
        # before April 1. Eggs are laid over weeks in spring, so hatch is drawn out; hatch itself isn't the damage
        LifeStage(label="Egg hatch", start=0, peak=280, end=560, weight=0),
        # From hatch to cocooning: NEWA's 280 to 600 (Harcourt's four instars, 42 + 42 + 46 + 58 °C·d = 338 °F·d;
        # Litsinger and Apple 1973's Wisconsin larvae 298 TU above 48 °F). This is the damage growers scout for
        DerivedStage(label="Larval feeding", follows="Egg hatch", lag=0, duration=320),
        # Prepupae and pupae: NEWA's cocooning 600 to adult emergence 815 (Harcourt's 39 + 80 °C·d = 214 °F·d)
        DerivedStage(label="Pupae in cocoons", follows="Egg hatch", lag=320, duration=215, weight=0),
        # Summer adults feed briefly, then leave the field until fall: 815 to 1,000 (the Crop Risk Tool's adult
        # diapause; no published source for when they leave)
        DerivedStage(label="New adults", follows="Egg hatch", lag=535, duration=185, weight=0),
    ),
    # From half the eggs hatched (Harcourt's and NEWA's key event, when tip feeding begins to show) until the last
    # have hatched, about 530; NEWA scouts from 315 to 599
    action_windows=(ActionWindow(label="Scout stem tips for larval feeding", stage="Egg hatch", between=(0.5, 0.999)),),
    source=CRT,  # what 0.1 was ported from (its changelog line)
    status="beta",
    version="0.3",
    changelog=(
        Change(
            version="0.2",
            date="2026-11-21",
            note="Rebuilt on NEWA's alfalfa weevil model (D95): simple average degree days above 48 °F from January 1, half the eggs hatched at 280 and cocooning at 600 (NEWA's table, which matches Harcourt 1981's stage peaks converted), as curves: egg hatch, larval feeding (the risk), pupae and new adults, and a window to scout stem tips. Replaces the Crop Risk Tool's step table on single sine 48.2/86 °F.",
        ),
        Change(
            version="0.3",
            date="2026-11-26",
            note="In season from April 1 to July 31: from a week before its earliest activity on 2016–2025's weather at six Wisconsin places to the end of the month its latest activity ended in (July 9). Activity ends after July 31 whatever the weather, as fall freezes end it, so a mild fall no longer holds a stalled curve's activity into winter.",
        ),
    ),
    trained=TrainingArea(
        description="counts of each life stage in alfalfa fields near the Bay of Quinte in eastern Ontario, across Lake Ontario from New York, where NEWA runs the same numbers",
        years=(1973, 1980),
        states=("NY",),
    ),
    checks=(
        Check(
            kind="published",
            against="Peak dates of eight life stages in eastern Ontario alfalfa fields, 1977–1980 (Harcourt 1981)",
            result="On historical weather for the area, NEWA's rule, which this model follows, reached the 36 observed peaks a median 3 days late (from 2 days early to 8 days late), and Harcourt's own method a median 2 days late.",
            report="docs/validation/models/alfalfa-weevil.md#against-harcourts-dated-peaks-in-ontario",
        ),
        Check(
            kind="system",
            against="NEWA's alfalfa weevil model on the weather of Wisconsin's NEWA stations, 2024 and 2025",
            result="On each station's own weather, half the eggs hatch, half the larvae cocoon and half the adults emerge on NEWA's days for these events in all 67 station-years. On AgWeather's gridded weather at the stations, the same events come a median 0 days from NEWA's, and within 3 days in most station-years.",
            report="docs/validation/models/alfalfa-weevil.md#against-newa-on-the-same-weather",
        ),
    ),
    citations=(
        Citation(
            text="NEWA, Network for Environment and Weather Applications, Cornell University: alfalfa weevil model (degree days for peak occurrence of each stage, from R. I. Carruthers).",
            url="https://newa.cornell.edu/alfalfa-weevil",
        ),
        Citation(
            text="Harcourt, D. G. (1981). A thermal summation model for predicting seasonal occurrence of the alfalfa weevil, Hypera postica (Coleoptera: Curculionidae), in southern Ontario. The Canadian Entomologist 113, 601–605.",
            doi="10.4039/Ent113601-7",
        ),
        Citation(
            text="Litsinger, J. A. and Apple, J. W. (1973). Thermal requirements for embryonic and larval development of the alfalfa weevil in Wisconsin. Journal of Economic Entomology 66, 309–311.",
            doi="10.1093/jee/66.2.309",
        ),
    ),
)
