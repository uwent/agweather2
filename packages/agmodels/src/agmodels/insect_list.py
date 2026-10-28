"""The insects (PLAN.md Phase 3 D): the Crop Risk Tool's three, with life-stage keys, and VDIFN's others.

Degree days are °F and thresholds as each source set them. Seedcorn maggot, alfalfa weevil and Colorado potato
beetle come from the Crop Risk Tool (newer, with stage labels), replacing VDIFN's versions; VDIFN's adult and
larval CPB abundance models stay; its old CPB model (base 52) is dropped (docs/project-plan.md). VDIFN's entries
and crops are generated from `../ag-vdifn/db/seeds.rb`; their criteria are VDIFN's severity texts.
"""

from agmodels.insects import Insect, Stage

CRT = "the Crop Risk Tool"

INSECTS: tuple[Insect, ...] = (
    Insect(
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
    ),
    Insect(
        "alfalfa-weevil",
        "Alfalfa weevil",
        ("Alfalfa",),
        base_f=48.2,  # 9 °C
        upper_f=86,  # 30 °C
        biofix="01-01",
        criteria="Alfalfa weevil egg hatch begins around 300 FDD. Light feeding damage expected during 1st and 2nd "
        "instar life stages (350-500 FDD). Heavy feeding damage expected during 3rd and 4th instar development, "
        "approx. 400-600 FDD.",
        stages=(
            Stage(300, 1, "Egg hatch, begin scouting"),
            Stage(370, 2, "2nd instar larvae"),
            Stage(440, 3, "3rd instar larvae"),
            Stage(505, 4, "4th instar larvae"),
            Stage(595, 2, "Pupal stage, end scouting"),
            Stage(815, 1, "Adult emergence"),
            Stage(1000, 0, "Adult diapause"),
        ),
        source=CRT,
    ),
    Insect(
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
    ),
    Insect(
        "aphid-pvy-vectors",
        "Aphid PVY Vectors",
        ("Potato",),
        base_f=39.2,
        upper_f=86,
        biofix="01-01",
        criteria=(
            "The risk of PVY transmission by aphid vectors begins around 1838 FDD, peaks around 2515 FDD, and remains"
            " elevated through vine kill. PVY transmission risk is calculated from a combination of several aphid "
            "species, the relative abundance of each species in Wisconsin, and the estimated PVY transmission "
            "efficiency of each species. Aphid vectors include Soybean aphid, Bird cherry-oat aphid, Green peach "
            "aphid, Pea aphid, Corn leaf aphid, and Potato aphid."
        ),
        generations=((1838, 2515, 3228),),
    ),
    Insect(
        "common-asparagus-beetle",
        "Asparagus Beetle (Common)",
        ("Asparagus",),
        base_f=50,
        upper_f=86,
        biofix="01-01",
        criteria=(
            "Egg hatch begins around 105 FDD, with peak larvae around 250 FDD and last larvae around 405 FDD. Peak "
            "adults around 570 FDD."
        ),
        generations=((105, 250, 405),),
    ),
    Insect(
        "black-cutworm",
        "Black Cutworm",
        (
            "Asparagus",
            "Bean",
            "Beet",
            "Carrot",
            "Celery",
            "Corn (Field and Sweet)",
            "Cucumber",
            "Hops",
            "Melon",
            "Mint",
            "Pea",
            "Potato",
            "Tomato",
        ),
        base_f=50,
        upper_f=86,
        biofix="05-15",
        criteria=(
            "Egg hatch begins around 180 FDD, with leaf cutting and larval development starting around 300 FDD and "
            "extending through 1000 FDD."
        ),
        generations=((300, 700, 1000),),
    ),
    Insect(
        "cabbage-looper",
        "Cabbage Looper",
        ("Celery", "Cole Crops", "Hops", "Leafy Greens", "Melon", "Mint", "Pea", "Potato", "Tomato"),
        base_f=50,
        upper_f=90,
        biofix="05-15",
        criteria=(
            "The first small larvae appear around 325 FDD after the May 15 biofix date. Feeding continues and worsens"
            " as larvae grow, peaking around 520 FDD and ending around 750 FDD. Second generation larvae may begin "
            "appearing around 1115 FDD, peak around 1310 FDD, and end around 1540 FDD."
        ),
        generations=(
            (325, 520, 750),
            (1115, 1310, 1540),
        ),
    ),
    Insect(
        "cabbage-maggot",
        "Cabbage Maggot",
        ("Cole Crops",),
        base_f=42.8,
        upper_f=86,
        biofix="01-01",
        criteria=(
            "Adult emergence occurs around 360 FDD, with peak emergence occurring around 600 FDD. Egg laying occurs "
            "from around 750 FDD to 1500 FDD with a peak around 1050 FDD. Second generation adult emergence begins "
            "around 1880 FDD and peaks around 2120 FDD, with egg-laying occurring from 2270 FDD through 3040 FDD."
        ),
        generations=(
            (360, 600, 1521),
            (1881, 2121, 3042),
        ),
    ),
    Insect(
        "colorado-potato-beetle-adults",
        "Colorado Potato Beetle (Adults)",
        ("Eggplant", "Potato", "Tomato"),
        base_f=50,
        upper_f=86,
        biofix="01-01",
        criteria=(
            "Our Colorado potato beetle adult abundance model was derived from 10 years of scouting data in the "
            "Central Sands and uses a base 50°F degree day model. First adult colonization of crops is typically "
            "around 275 FDD with peak first-generation adults observed around 690 FDD. Adult populations decline to a"
            " low at 1090 FDD although larval feeding remains a significant threat if not controlled. Second "
            "generation adult populations peak around 1695 FDD and decline through the end of the season (around 2500"
            " FDD)."
        ),
        generations=(
            (275, 690, 1090),
            (1090, 1690, 2500),
        ),
    ),
    Insect(
        "colorado-potato-beetle-larvae",
        "Colorado Potato Beetle (Larvae)",
        ("Eggplant", "Potato", "Tomato"),
        base_f=50,
        upper_f=86,
        biofix="01-01",
        criteria=(
            "Our Colorado potato beetle larval abundance model was derived from 10 years of scouting data in the "
            "Central Sands and uses a base 50°F degree day model. First egg hatch is typically around 485 FDD with "
            "peak larval populations reached during the first generation at around 905 FDD. Larval populations then "
            "decline steadily through the end of the season (around 2500 FDD)."
        ),
        generations=((485, 905, 2500),),
    ),
    Insect(
        "corn-earworm",
        "Corn Earworm",
        ("Bean", "Corn (Field and Sweet)"),
        base_f=55,
        upper_f=92,
        biofix="08-01",
        criteria=(
            "Adjust biofix to match date when first eggs or adults are observed. Corn earworm eggs typically hatch "
            "around 70 FDD after the biofix date. Peak larval populations and damage occur around 275 FDD, with "
            "larvae leaving corn ears and pupating around 440 FDD."
        ),
        generations=((70, 275, 440),),
    ),
    Insect(
        "corn-rootworm",
        "Corn Rootworm",
        ("Corn (Field and Sweet)",),
        base_f=52,
        upper_f=None,
        biofix="01-01",
        criteria=(
            "First instar larvae appear around 329 FDD with light feeding expected. Larval populations peak around "
            "472 FDD with heavy feeding expected. Larval stage expected to end by 636 FDD."
        ),
        generations=((329, 472, 636),),
    ),
    Insect(
        "european-corn-borer",
        "European Corn Borer",
        ("Bean", "Corn (Field and Sweet)", "Eggplant", "Pepper", "Potato"),
        base_f=50,
        upper_f=86,
        biofix="01-01",
        criteria=(
            "First generation adult flight expected starting 329 FDD, peaking 472 FDD, and ending 636 FDD. Second "
            "generation adult flight expected starting 1660 FDD, peaking 1950 FDD, and ending 2190 FDD."
        ),
        generations=(
            (550, 740, 900),
            (1660, 1950, 2190),
        ),
    ),
    Insect(
        "crucifer-flea-beetle",
        "Flea Beetle (Crucifer)",
        ("Cole Crops",),
        base_f=50,
        upper_f=None,
        biofix="01-01",
        criteria=(
            "Adult flea beetles are most damaging with two generations typical in Wisconsin. First generation adults "
            "develop around 820 FDD and feed through around 1155 FDD. Second generation adults emerge around 1640 FDD"
            " and feed through around 1975 FDD."
        ),
        generations=(
            (820, 965, 1155),
            (1640, 1785, 1975),
        ),
    ),
    Insect(
        "mint-flea-beetle",
        "Flea Beetle (Mint)",
        ("Mint",),
        base_f=41,
        upper_f=None,
        biofix="01-01",
        criteria=(
            "Mint flea beetle adults emerge around 1475 FDD, with activity peaking around 1675 FDD and ending around "
            "1880 FDD."
        ),
        generations=((1475, 1675, 1880),),
    ),
    Insect(
        "imported-cabbageworm",
        "Imported Cabbageworm",
        ("Cole Crops",),
        base_f=50,
        upper_f=None,
        biofix="01-01",
        criteria=(
            "First generation adult flight starts around 150 FDD, peaks around 240 FDD, with larval feeding expected "
            "through 630 FDD. Second generation adult flight starts around 830 FDD, peaks around 1030 FDD, with "
            "larval feeding expected through around 2000 FDD."
        ),
        generations=(
            (150, 240, 630),
            (830, 1030, 2000),
        ),
    ),
    Insect(
        "japanese-beetle",
        "Japanese Beetle",
        (
            "Asparagus",
            "Bean",
            "Beet",
            "Blackberry",
            "Cole Crops",
            "Eggplant",
            "Hops",
            "Horseradish",
            "Leafy Greens",
            "Melon",
            "Mint",
            "Pea",
            "Pepper",
            "Potato",
            "Pumpkin and Squash",
            "Raspberry",
            "Tomato",
        ),
        base_f=50,
        upper_f=None,
        biofix="01-01",
        criteria=(
            "Adults emerge starting around 970 FDD, with peak feeding around 1600 FDD, and end of feeding by around "
            "2150 FDD."
        ),
        generations=((970, 1600, 2150),),
    ),
    Insect(
        "tarnished-plant-bug",
        "Tarnished Plant Bug (Lygus Bug)",
        ("Celery", "Leafy Greens", "Potato", "Raspberry"),
        base_f=52,
        upper_f=None,
        biofix="01-01",
        criteria="Lygus bugs are active most of the summer after early-season nymph development (starting 275 FDD).",
        generations=((275, 1000, 2000),),
    ),
    Insect(
        "mint-root-borer",
        "Mint Root Borer",
        ("Mint",),
        base_f=50,
        upper_f=None,
        biofix="04-01",
        criteria=(
            "First moth catch expected around 430 FDD, with peak egg hatch occurring around 1280 FDD. End of risk is "
            "approximately 2150 FDD when hibernaculum formation completes."
        ),
        generations=((430, 1280, 2150),),
    ),
    Insect(
        "onion-maggot",
        "Onion Maggot",
        ("Onion",),
        base_f=39.2,
        upper_f=86,
        biofix="01-01",
        criteria=(
            "First generation adult flight peaks around 680 FDD and second generation adult flight peaks around 1950."
            " Controlling adults is the best way to protect against damage from this pest."
        ),
        generations=(
            (510, 680, 850),
            (1460, 1950, 2435),
        ),
    ),
    Insect(
        "spotted-wing-drosophila",
        "Spotted Wing Drosophila",
        ("Blackberry", "Cherry", "Raspberry"),
        base_f=45,
        upper_f=86,
        biofix="01-01",
        criteria=(
            "In Wisconsin, overwintering adult Spotted Wing Drosophila begin egg-laying in mid to late June (around "
            "1276 FDD), and will complete a generation every 8-12 days. Populations peak around 3100 FDD, and will "
            "continue to be a threat to soft-skinned fruit through the end of the season."
        ),
        generations=((1276, 3180, 4000),),
    ),
    Insect(
        "squash-vine-borer",
        "Squash Vine Borer",
        ("Cucumber", "Melon", "Pumpkin and Squash"),
        base_f=50,
        upper_f=None,
        biofix="01-01",
        criteria="Adult emergence begins around 750 FDD, peaking around 900 FDD, and ending around 1000 FDD.",
        generations=((750, 900, 1000),),
    ),
    Insect(
        "stalk-borer",
        "Stalk Borer",
        ("Corn (Field and Sweet)",),
        base_f=41,
        upper_f=86,
        biofix="01-01",
        criteria=(
            "Adult flight begins around 1110 FDD and peaks around 1650 FDD. Control is best between 1400 and 1700 FDD."
        ),
        generations=((1110, 1400, 1700),),
    ),
    Insect(
        "variegated-cutworm",
        "Variegated Cutworm",
        (
            "Asparagus",
            "Bean",
            "Beet",
            "Carrot",
            "Celery",
            "Corn (Field and Sweet)",
            "Cucumber",
            "Hops",
            "Leafy Greens",
            "Melon",
            "Mint",
            "Potato",
            "Tomato",
        ),
        base_f=45,
        upper_f=80.1,
        biofix="05-01",
        criteria=(
            "Egg-laying peaks around 900 FDD with larval populations active from around 1150 FDD through 1900 FDD, "
            "with end of larval stage around 2100 FDD."
        ),
        generations=((900, 1450, 2100),),
    ),
    Insect(
        "western-bean-cutworm",
        "Western Bean Cutworm",
        (
            "Asparagus",
            "Bean",
            "Beet",
            "Carrot",
            "Celery",
            "Corn (Field and Sweet)",
            "Cucumber",
            "Hops",
            "Melon",
            "Mint",
            "Potato",
            "Tomato",
        ),
        base_f=50,
        upper_f=None,
        biofix="05-01",
        criteria=(
            "25% adult moth emergence expected around 1320 FDD, peaking around 1420 FDD, and ending around 1535 FDD."
        ),
        generations=((1320, 1420, 1535),),
    ),
    Insect(
        "western-flower-thrips",
        "Western Flower Thrips",
        ("Cucumber", "Eggplant", "Onion", "Pepper", "Tomato"),
        base_f=45,
        upper_f=None,
        biofix="01-01",
        criteria=(
            "Thrips typically have several overlapping generations per year in Wisconsin, with peaks occurring around"
            " 675, 1350, 2025, and 2700 FDD."
        ),
        generations=(
            (340, 675, 1010),
            (1010, 1350, 1685),
            (1685, 2025, 2360),
            (2360, 2700, 3375),
        ),
    ),
)
