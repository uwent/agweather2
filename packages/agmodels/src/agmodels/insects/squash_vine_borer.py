"""Squash vine borer, rebuilt from the extension guides (UW–Madison, South Dakota State, Ohio State, Michigan State)
as D36 curves (part H). No primary research source is known; the flight curve is a judgment across the guides."""

from agmodels.phenology import ActionWindow, DerivedStage, Insect, LifeStage
from agmodels.spec import Change, Check, Citation, TrainingArea

INSECT = Insect(
    id="squash-vine-borer",
    name="Squash vine borer",
    crops=("cucumber", "melon", "pumpkin-squash"),
    # UW–Madison Extension's method (XHT1086): the modified average, 50/86 °F, from January 1, a stored total. Its
    # degree-day table (XHT1087, Delahaut, rev. 2005; read in full 2026-11-23) gives only "base temperature = 50°F" and
    # egg laying at 900–1,000 (chicory full bloom), so its numbers are read on XHT1086's method. UW's are the Wisconsin
    # numbers (moths at 900, XHT1136; egg laying 900–1,000, XHT1087). South Dakota
    # State and Ohio State count the simple average above 50 °F, which reaches 1,000 a median 7 days later at
    # Arlington (10 at Rhinelander) in 2016–2025; single sine without an upper, as MSU and VDIFN, 3 to 5 days later
    base_f=50,
    upper_f=86,
    dd_method="modified",
    biofix="01-01",
    source="UW–Madison's and other extension guides",
    ported_from="VDIFN",
    life_stages=(
        # Moth flight and egg laying, a judgment across the guides: moths first seen at about 900 (UW–Madison XHT1136;
        # XHT1087 has egg laying at 900–1,000, this curve's 16 to 35 %) or emerging at 800 (MSU) to 1,000 (UW Vegetable Entomology, SDSU, Ohio State); egg laying over about
        # three weeks centered on 1,000 (XHT1136), so continuing about a week and a half after it; MSU's flight
        # declining from 1,800 and over by 2,000. This PERT: 5 % at 824, half at 1,083, 75 % at 1,242, 95 % at 1,479,
        # the last moths by 1,900. Females lay as they fly, so the flight stands for egg laying too. Moths don't feed
        LifeStage(label="Moth flight and egg laying", start=750, peak=1000, end=1900, weight=0),
        # Eggs hatch 245–300 after they're laid and the larvae feed inside the vines for 660 (SDSU, simple average 50);
        # UW: hatch in one to two weeks, two to six weeks of feeding. The borers in the vines are the damage
        DerivedStage(label="Larvae in vines", follows="Moth flight and egg laying", lag=270, duration=660),
    ),
    # Protect stems from the first moths (5 %, about 825) until three quarters have flown (about 1,240): UW–Madison's
    # three weeks of egg laying around 1,000, treating when moths are first seen and every 5–7 days after
    action_windows=(
        ActionWindow(label="Protect stems during egg laying", stage="Moth flight and egg laying", between=(0.05, 0.75)),
    ),
    version="0.2",
    status="beta",
    trained=TrainingArea(
        description="extension guides' timing in Wisconsin, South Dakota, Ohio and Michigan",
        years=(2012, 2026),
        states=("WI", "SD", "OH", "MI"),
    ),
    changelog=(
        Change(
            version="0.2",
            date="2026-11-21",
            note="Rebuilt from the extension guides (UW–Madison, South Dakota State, Ohio State, Michigan State): UW–Madison's modified-average degree days, 50/86 °F from January 1; the moth flight and egg laying as a curve from about 825 (5 %) through half at 1,085 to the last moths by 1,900, the larvae in the vines timed from it (hatch 270 degree days after laying, 660 of feeding), and a window to protect stems from the first moths until three quarters have flown (about 1,240). Replaces VDIFN's window (750, 900, 1,000 degree days, single sine 50 °F), which ended in the middle of egg laying.",
        ),
    ),
    checks=(
        Check(
            kind="published",
            against="The extension guides' timing: UW–Madison (moths at 900, three weeks of egg laying around 1,000), South Dakota State and Ohio State (moths emerge at 1,000) and Michigan State (emergence 800, decline from 1,800, complete 2,000)",
            result="Our first moths (5 %) come at 824 degree days and half have flown at 1,083; the protection window runs from 824 to 1,242, three weeks around 1,000 in an average Wisconsin July, and the last moths fly by 1,900. The curve was drawn to these numbers; no field data were used.",
            report="docs/validation/models/squash-vine-borer.md#against-its-sources-numbers",
        ),
        Check(
            kind="observations",
            against="235 research-grade iNaturalist records of squash vine borer moths within AgWeather's map area in the upper Midwest, 2016–2026",
            result="The first 5 and 10 % of the records came at 809 and 887 degree days, close to our 824 and 862, but half came at 1,278, about 195 degree days (8 days) after our half, and 90 % at 1,765 against our 1,392: moths are seen later and longer than the guides' three weeks of egg laying. The model wasn't fitted to these records.",
            report="docs/validation/models/squash-vine-borer.md#against-inaturalist-records",
        ),
    ),
    citations=(
        Citation(
            text="Liesch, P. J. and Groves, R. (2026). Squash Vine Borer (XHT1136). UW–Madison Division of Extension, Wisconsin Horticulture.",
            url="https://hort.extension.wisc.edu/articles/squash-vine-borer/",
        ),
        Citation(
            text="Delahaut, K. (2005). Degree Days for Common Fruit and Vegetable Insect Pests (University of Wisconsin Garden Facts XHT1087, revised April 20, 2005). University of Wisconsin–Extension, Cooperative Extension; revised 2012, UW–Madison Division of Extension, Wisconsin Horticulture.",
            url="https://hort.extension.wisc.edu/articles/degree-days-common-fruit-vegetable-insect-pests/",
        ),
        Citation(
            text="Varenhorst, A. and others (2023). Squash vine borer activity estimate, June 21, 2023. South Dakota State University Extension.",
            url="https://extension.sdstate.edu/squash-vine-borer-activity-estimate-june-21-2023",
        ),
        Citation(
            text="Ruger and Leach (2026). Squash Vine Borer (ENT-0106). Ohio State University Extension, Ohioline.",
            url="https://cfaes.osu.edu/fact-sheet/squash-vine-borer-damage-and-management-what-look-and-when-act",
        ),
        Citation(
            text="Michigan State University Enviroweather: squash vine borer model.",
            url="https://enviroweather.msu.edu/",
        ),
    ),
)
