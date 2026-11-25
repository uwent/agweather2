"""Mint flea beetle, rebuilt on Oregon State's USPest model (`mfb`, Berry et al.) as D36 curves (part H)."""

from agmodels.phenology import ActionWindow, DerivedStage, Insect, LifeStage
from agmodels.spec import Change, Check, Citation, TrainingArea

INSECT = Insect(
    id="mint-flea-beetle",
    name="Mint flea beetle",
    season=("04-15", "08-31"),
    crops=("mint",),
    # USPest's method: single sine 41/103 °F from January 1. 103 °F isn't a stored total, and on Wisconsin's weather
    # it never binds: a 103 °F cap changed no season's total at Arlington, Hancock or Rhinelander in 2016–2025, so
    # the stored 41 °F without an upper threshold is the same model here
    base_f=41,
    upper_f=None,
    biofix="01-01",
    source="Oregon State University's mint flea beetle model (USPest.org)",
    ported_from="VDIFN",
    life_stages=(
        # Overwintered eggs hatch from 405 (USPest's first instars begin). USPest gives only the start; the Pacific
        # Northwest handbook has hatch from early April through May, about 550 degree days there. This PERT has 2 % at
        # 416, half at 590 and 99 % at 863 (a judgment, no source gives the spread). Eggs aren't the damage
        LifeStage(label="Egg hatch", start=380, peak=560, end=980, weight=0),
        # Larvae feed on roots and in rhizomes until they leave the rhizomes to pupate: USPest's first larvae leave at
        # 900, 495 after the first hatch (prepupae from 1,205, pupae from 1,395)
        DerivedStage(label="Larval feeding", follows="Egg hatch", lag=0, duration=495),
        # Adults emerge from 1,475 (USPest's "begin adult emergence"; its last event). The spread is a judgment: the
        # handbook's late June and July, about 900 degree days in the Pacific Northwest. 2 % at 1,479, half at 1,706,
        # 95 % at 2,001. Emergence itself isn't the damage
        LifeStage(label="Adult emergence", start=1440, peak=1650, end=2300, weight=0),
        # Adults feed (shot holes in leaves) for two to three weeks before laying eggs, and on while they lay (the
        # handbook; A3422): 600 degree days, about three to four weeks in July (a judgment)
        DerivedStage(label="Adult feeding", follows="Adult emergence", lag=0, duration=600),
    ),
    # Sweep for adults from the first to emerge (2 %) until nearly all are out (95 %): A3422's thresholds are in adults
    # per 100 sweeps, and sprays go on after most adults are out and before egg laying
    action_windows=(ActionWindow(label="Sweep mint for adults", stage="Adult emergence", between=(0.02, 0.95)),),
    version="0.3",
    status="beta",
    # Berry et al.'s fields were Pacific Northwest mint; the years aren't in hand: 1990–1997 is an estimate (the
    # mint root borer model from the same group is dated 1997)
    trained=TrainingArea(
        description="observations in Pacific Northwest mint",
        years=(1990, 1997),
        states=("OR", "WA", "ID"),
    ),
    changelog=(
        Change(
            version="0.2",
            date="2026-11-21",
            note="Rebuilt on Oregon State's mint flea beetle model (USPest.org, Berry et al.): single-sine degree days above 41 °F from January 1 (its 103 °F upper threshold never binds in Wisconsin), egg hatch from 405 and larval feeding until the larvae leave the rhizomes, and adult emergence from 1,475 with the adults' feeding after it, as curves; a window to sweep for adults through emergence. Replaces VDIFN's window (1,475, 1,675, 1,880), whose peak and end weren't USPest's.",
        ),
        Change(
            version="0.3",
            date="2026-11-26",
            note="In season from April 15 to August 31: from a week before its earliest activity on 2016–2025's weather at six Wisconsin places to the end of the month its latest activity ended in (August 28). Activity ends after August 31 whatever the weather, as fall freezes end it, so a mild fall no longer holds a stalled curve's activity into winter.",
        ),
    ),
    checks=(
        Check(
            kind="published",
            against="Oregon State's mint flea beetle model (USPest.org; Berry et al.), from Pacific Northwest mint",
            result="Egg hatch begins (2 %) at 416 degree days and the first larvae leave the rhizomes at 911, against the model's 405 and 900; adult emergence begins (2 %) at 1,479, against its 1,475. The model gives only when each stage begins, so the spread of each is our judgment.",
            report="docs/validation/models/mint-flea-beetle.md#against-its-sources-numbers",
        ),
        Check(
            kind="published",
            against="Commercial Vegetable Production in Wisconsin (A3422): adults emerge in late July, at about 1,100 degree days above 40 °F in soil 6 inches deep",
            result="On AgWeather's soil temperatures, 1,100 soil degree days came 2 to 14 days before the model's first adults (1,475 in air) at Arlington, Hancock and Rhinelander in 2016–2025, from early June to early July, not late July. The model's first adults come in late June in southern Wisconsin and early July in the north, weeks before the guide's late July.",
            report="docs/validation/models/mint-flea-beetle.md#against-wisconsins-guide",
        ),
    ),
    citations=(
        Citation(
            text="Berry, R. E. and others. Mint flea beetle degree-day model. Oregon State University, on USPest.org.",
            url="https://uspest.org/cgi-bin/ddmodel2.pl?spp=mfb",
        ),
        Citation(
            text="Mint-Mint flea beetle. In Pacific Northwest Pest Management Handbooks: Insect Management Handbook. Oregon State University, Washington State University and University of Idaho, 2026.",
            url="https://pnwhandbooks.org/insect/agronomic/mint/mint-mint-flea-beetle",
        ),
        Citation(
            text="Bradford, B. Z., Colquhoun, J. B., Chapman, S. A., Gevens, A. J., Groves, R. L., Heider, D. J., Nice, G. R. W., Ruark, M. D., Wang, Y. and Dewerff, R. (2026). Commercial Vegetable Production in Wisconsin (A3422). UW–Madison Division of Extension.",
            url="https://vegpath.plantpath.wisc.edu/resources/a3422/",
        ),
    ),
)
