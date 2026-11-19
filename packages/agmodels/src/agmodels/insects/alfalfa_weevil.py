"""Alfalfa weevil, from the Crop Risk Tool."""

from agmodels.insects import CRT
from agmodels.phenology import Insect, Stage
from agmodels.spec import Check

INSECT = Insect(
    id="alfalfa-weevil",
    name="Alfalfa weevil",
    crops=("alfalfa",),
    base_f=48.2,  # 9 °C
    upper_f=86,  # 30 °C
    biofix="01-01",
    stages=(
        Stage(start=300, severity=1, label="Egg hatch, begin scouting"),
        Stage(start=370, severity=2, label="2nd instar larvae"),
        Stage(start=440, severity=3, label="3rd instar larvae"),
        Stage(start=505, severity=4, label="4th instar larvae"),
        Stage(start=595, severity=2, label="Pupal stage, end scouting"),
        Stage(start=815, severity=1, label="Adult emergence"),
        Stage(start=1000, severity=0, label="Adult diapause"),
    ),
    source=CRT,
    checks=(
        Check(
            kind="system",
            against="The Crop Risk Tool, which this model replaces, on the weather of Eau Claire, Wisconsin, 2025",
            result="The risk level matched the Crop Risk Tool's on all 365 days. The tool's degree days ran up to 7.7 higher by late summer, because it skips the upper temperature limit on some hot days, but no stage began on a different day.",
            report="docs/validation/models/alfalfa-weevil.md#against-the-crop-risk-tool-on-the-same-weather",
        ),
        Check(
            kind="published",
            against="Development times of alfalfa weevil larvae in Wisconsin (Litsinger and Apple 1973) and a degree-day model from southern Ontario (Harcourt 1981)",
            result="After egg hatch, each larval stage begins within 3 degree days of the Wisconsin study's development times, and adult emergence at 815 degree days is within 2 of Ontario's 817. We found no published source for egg hatch at 300 degree days from January 1.",
            report="docs/validation/models/alfalfa-weevil.md#against-its-sources-numbers",
        ),
    ),
)
