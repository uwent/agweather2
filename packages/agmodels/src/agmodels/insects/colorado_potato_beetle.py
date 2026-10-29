"""Colorado potato beetle, from the Crop Risk Tool."""

from agmodels.insects import CRT
from agmodels.phenology import Insect, Stage

INSECT = Insect(
    id="colorado-potato-beetle",
    name="Colorado potato beetle",
    crops=("Potato", "Tomato", "Eggplant"),
    base_f=50,
    upper_f=86,
    biofix="01-01",
    criteria="Our Colorado potato beetle risk model was derived from 10 years of scouting data in the Central "
    "Sands and uses a base 50°F degree day model. The indicated risk score represents the estimated total "
    "abundance of adults and larvae. First adult colonization of crops is typically around 265 FDD with peak "
    "first-generation populations observed around 895 FDD. Total populations decline slightly through 1115 FDD "
    "during the period between generations. Populations peak again around 1375 FDD during second generation "
    "adult emergence and decline through the end of the season.",
    stages=(
        Stage(start=200, severity=1, label="1st gen adult colonization"),
        Stage(start=350, severity=2, label="1st gen egg hatch"),
        Stage(start=600, severity=3, label="1st gen peak adults"),
        Stage(start=800, severity=4, label="1st gen peak larvae"),
        Stage(start=935, severity=2, label="1st gen pupation"),
        Stage(start=1100, severity=3, label="2nd gen adult emergence"),
        Stage(start=1470, severity=4, label="2nd gen peak adults"),
        Stage(start=1800, severity=3, label="2nd gen adult feeding continues"),
        Stage(start=1970, severity=2, label="2nd gen adults begin dispersing"),
        Stage(start=2265, severity=1, label="2nd gen adults mostly dispersed"),
    ),
    source=CRT,
)
