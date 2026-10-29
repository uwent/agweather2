"""Seedcorn maggot, from the Crop Risk Tool."""

from agmodels.insects import CRT
from agmodels.phenology import Insect, Stage

INSECT = Insect(
    id="seedcorn-maggot",
    name="Seedcorn maggot",
    crops=("Corn (Field and Sweet)", "Bean", "Cucumber", "Melon", "Pumpkin and Squash"),
    base_f=39.2,
    upper_f=86,
    biofix="01-01",
    stages=(
        Stage(start=295, severity=1, label="1st gen: Low abundance and risk of damage"),
        Stage(start=315, severity=2, label="1st gen: Medium abundance and risk of damage"),
        Stage(start=330, severity=3, label="1st gen: High abundance and risk of damage"),
        Stage(start=340, severity=4, label="1st gen: Peak adult flight and risk of damage"),
        Stage(start=510, severity=3, label="1st gen: High abundance and risk of damage"),
        Stage(start=585, severity=2, label="1st gen: Medium abundance and risk of damage"),
        Stage(start=660, severity=1, label="1st gen: Low abundance and risk of damage"),
        Stage(start=810, severity=0, label="1st gen: Absent or very low abundance"),
        Stage(start=990, severity=1, label="2nd gen: Low abundance and risk of damage"),
        Stage(start=1020, severity=2, label="2nd gen: Medium abundance and risk of damage"),
        Stage(start=1035, severity=3, label="2nd gen: High abundance and risk of damage"),
        Stage(start=1050, severity=4, label="2nd gen: Peak adult flight and risk of damage"),
        Stage(start=1245, severity=3, label="2nd gen: High abundance and risk of damage"),
        Stage(start=1325, severity=2, label="2nd gen: Medium abundance and risk of damage"),
        Stage(start=1405, severity=1, label="2nd gen: Low abundance and risk of damage"),
        Stage(start=1570, severity=0, label="2nd gen: Absent or very low abundance"),
        Stage(start=1650, severity=1, label="3rd gen: Low abundance and risk of damage"),
        Stage(start=1700, severity=2, label="3rd gen: Medium abundance and risk of damage"),
        Stage(start=1725, severity=3, label="3rd gen: High abundance and risk of damage"),
        Stage(start=1750, severity=4, label="3rd gen: Peak adult flight and risk of damage"),
        Stage(start=1985, severity=3, label="3rd gen: High abundance and risk of damage"),
        Stage(start=2080, severity=2, label="3rd gen: Medium abundance and risk of damage"),
        Stage(start=2175, severity=1, label="3rd gen: Low abundance and risk of damage"),
        Stage(start=2360, severity=0, label="3rd gen: Absent or very low abundance"),
    ),
    source=CRT,
)
