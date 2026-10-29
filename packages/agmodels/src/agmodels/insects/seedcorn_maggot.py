"""Seedcorn maggot, from the Crop Risk Tool."""

from agmodels.insects import CRT
from agmodels.phenology import Insect, Stage

INSECT = Insect(
    "seedcorn-maggot",
    "Seedcorn maggot",
    ("Corn (Field and Sweet)", "Bean", "Cucumber", "Melon", "Pumpkin and Squash"),
    base_f=39.2,
    upper_f=86,
    biofix="01-01",
    criteria="In Wisconsin there are typically 3-5 generations per year, with maximum risk coinciding with peak "
    "adult flight times: First (overwintering) generation flight peaks around 360 FDD, second generation flight "
    "peaks around 1080 FDD, third generation peaks around 1800 FDD. Wait 450 FDD after peak flight for larval "
    "pupation and minimum risk to crops.",
    stages=(
        Stage(295, 1, "1st gen: Low abundance and risk of damage"),
        Stage(315, 2, "1st gen: Medium abundance and risk of damage"),
        Stage(330, 3, "1st gen: High abundance and risk of damage"),
        Stage(340, 4, "1st gen: Peak adult flight and risk of damage"),
        Stage(510, 3, "1st gen: High abundance and risk of damage"),
        Stage(585, 2, "1st gen: Medium abundance and risk of damage"),
        Stage(660, 1, "1st gen: Low abundance and risk of damage"),
        Stage(810, 0, "1st gen: Absent or very low abundance"),
        Stage(990, 1, "2nd gen: Low abundance and risk of damage"),
        Stage(1020, 2, "2nd gen: Medium abundance and risk of damage"),
        Stage(1035, 3, "2nd gen: High abundance and risk of damage"),
        Stage(1050, 4, "2nd gen: Peak adult flight and risk of damage"),
        Stage(1245, 3, "2nd gen: High abundance and risk of damage"),
        Stage(1325, 2, "2nd gen: Medium abundance and risk of damage"),
        Stage(1405, 1, "2nd gen: Low abundance and risk of damage"),
        Stage(1570, 0, "2nd gen: Absent or very low abundance"),
        Stage(1650, 1, "3rd gen: Low abundance and risk of damage"),
        Stage(1700, 2, "3rd gen: Medium abundance and risk of damage"),
        Stage(1725, 3, "3rd gen: High abundance and risk of damage"),
        Stage(1750, 4, "3rd gen: Peak adult flight and risk of damage"),
        Stage(1985, 3, "3rd gen: High abundance and risk of damage"),
        Stage(2080, 2, "3rd gen: Medium abundance and risk of damage"),
        Stage(2175, 1, "3rd gen: Low abundance and risk of damage"),
        Stage(2360, 0, "3rd gen: Absent or very low abundance"),
    ),
    source=CRT,
)
