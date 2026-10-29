"""Colorado potato beetle, from the Crop Risk Tool."""

from agmodels.insects import CRT
from agmodels.phenology import Insect, Stage

INSECT = Insect(
    "colorado-potato-beetle",
    "Colorado potato beetle",
    ("Potato", "Tomato", "Eggplant"),
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
        Stage(200, 1, "1st gen adult colonization"),
        Stage(350, 2, "1st gen egg hatch"),
        Stage(600, 3, "1st gen peak adults"),
        Stage(800, 4, "1st gen peak larvae"),
        Stage(935, 2, "1st gen pupation"),
        Stage(1100, 3, "2nd gen adult emergence"),
        Stage(1470, 4, "2nd gen peak adults"),
        Stage(1800, 3, "2nd gen adult feeding continues"),
        Stage(1970, 2, "2nd gen adults begin dispersing"),
        Stage(2265, 1, "2nd gen adults mostly dispersed"),
    ),
    source=CRT,
)
