"""Seedcorn maggot, from the Crop Risk Tool, rebuilt on its sources (D36, D37)."""

from agmodels.insects import CRT
from agmodels.phenology import ActionWindow, DerivedStage, Insect, LifeStage
from agmodels.spec import Change, Citation

INSECT = Insect(
    id="seedcorn-maggot",
    name="Seedcorn maggot",
    crops=("Corn (Field and Sweet)", "Bean", "Cucumber", "Melon", "Pumpkin and Squash"),
    # The sources' method (D37): simple average above 3.9 °C (39 °F), temperatures capped at 29 °C (84.2 °F)
    base_f=39,
    upper_f=84.2,
    dd_method="average",
    biofix="01-01",
    life_stages=(
        # Over-wintered flies: first emergence 54–94 FDD in New York (Olaya-Arenas et al. 2024) and 50% at 347 in
        # Wisconsin (Sanborn 1981 in Funderburk et al. 1984); this curve's 10, 50 and 90% are 201, 345 and 495
        LifeStage(label="Adult flight", start=70, peak=340, end=650),
        # Pre-oviposition 15.7 and egg 30 °C·d (28 + 54 FDD), then the larva's 204 °C·d (367 FDD; Sanborn et al.
        # 1982, Funderburk et al. 1984): oviposition leads to the feeding, so both carry the risk (Ben, 2026-10-29)
        DerivedStage(label="Larval feeding", follows="Adult flight", lag=82, duration=367),
    ),
    # Adult to adult 392 °C·d (706 FDD) in the lab (Funderburk et al. 1984); Wisconsin's field peaks 704 then 860 apart
    generation_dd=720,
    # Individuals' development rates ranged about ±20% of the mean in the lab (Sanborn et al. 1982, Table 1, larvae
    # at 14.6 °C), about ±2 SD, so an SD near 8% of a generation; the first flight's own spread (~120) is wider
    # because over-wintered emergence is drawn out (Throne and Eckenrode 1985), not because development varies
    generation_sd=60,
    action_windows=(ActionWindow(label="Avoid planting during adult flight", stage="Adult flight"),),
    version="2.0",
    status="beta",
    changelog=(
        Change(
            version="2.0",
            date="2026-10-29",
            note="Life stages as curves (D36): adult flight from 70 FDD, half done by 345, and larval feeding timed "
            "from it, in every generation 720 FDD apart; degree days by the sources' average method (D37) rather than "
            "single sine, which ran 5–7 days early in spring. Replaces the Crop Risk Tool's step table.",
        ),
    ),
    source=CRT,
    citations=(
        Citation(text="The Crop Risk Tool (UW–Madison Vegetable Entomology)."),
        Citation(
            text="Sanborn, S. M., Wyman, J. A. and Chapman, R. K. (1982). Threshold temperature and heat unit "
            "summations for seedcorn maggot development under controlled conditions. Annals of the Entomological "
            "Society of America 75, 103–106.",
            doi="10.1093/aesa/75.1.103",
        ),
        Citation(
            text="Funderburk, J. E., Higley, L. G. and Pedigo, L. P. (1984). Seedcorn maggot (Diptera: Anthomyiidae) "
            "phenology in central Iowa and examination of a thermal-unit system to predict development under field "
            "conditions. Environmental Entomology 13, 105–109.",
            doi="10.1093/ee/13.1.105",
        ),
        Citation(
            text="Throne, J. E. and Eckenrode, C. J. (1985). Emergence patterns of the seedcorn maggot, Delia platura "
            "(Diptera: Anthomyiidae). Environmental Entomology 14, 182–186.",
            doi="10.1093/ee/14.2.182",
        ),
        Citation(
            text="Olaya-Arenas, P., Cho, C. Y. L., Olmstead, D., et al. (2024). Degree-day models for predicting "
            "adult Delia platura (Diptera: Anthomyiidae) spring flight and first emergence in New York State. "
            "Journal of Economic Entomology 117, 2181–2185.",
            doi="10.1093/jee/toae148",
        ),
    ),
)
