# Seedcorn maggot (`seedcorn-maggot`): validation

Model version 0.3, generation weights added 2026-11-23 (part H, round 2); version 0.2 written 2026-11-18 (D98); NEWA's comparison and the units of New York's first-emergence numbers added 2026-11-21 (part H, H1), with no change to the model. The model: `packages/agmodels/src/agmodels/insects/seedcorn_maggot.py`, life-stage curves (D36) run by the insect engine (`agmodels.phenology`, `PhenologyModel`) on degree days by its sources' method (D37); its page: `seedcorn_maggot.md` beside it. Rebuilt on its sources on 2026-10-29, replacing the Crop Risk Tool's step table; the notes this condenses, with the sources' numbers converted to °F·d, are in Phase 3 D8 ("Seedcorn maggot first"). The sources' PDFs are in `tmp/references/insects/`.

**In short:** the first (over-wintered) flight was set from field data, so it matches them by construction: half the flies have emerged at 345 degree days, against 347 in Wisconsin. The later flights, placed by the laboratory's adult-to-adult time rather than fitted, come at 1065 and 1785, against Wisconsin's field peaks at 1051 and 1912, and well before Iowa's second flight (1228). On the same weather our flight peaks come 3 to 6 days after the Crop Risk Tool's, mostly because of the degree-day method. Only the first flight's start is held by a test in CI (`test_maggots.py`). On the same weather at 34 Wisconsin NEWA stations, our flight starts a median 5 days before NEWA's first-emergence window opens and is half over a day before NEWA's window closes: NEWA reads New York's first-emergence numbers as °C·d, where the studies counted °F·d (below). Not compared with Wisconsin trap catches.

## Sources and what we took from each

<!-- prettier-ignore -->
| Source | What it gives | What we took |
| --- | --- | --- |
| Sanborn, Wyman and Chapman 1982 (laboratory, Wisconsin) | Base 3.9 °C; egg 30, larva 204, pupa 142, egg to adult 376 °C·d (54, 367, 256 and 677 °F·d); individual development rates within about ±20 % of the mean | The larva's 367 °F·d and the egg's 54; the generations' spread (SD 60 °F·d, about 8 % of a generation) |
| Funderburk, Higley and Pedigo 1984 (cone traps near Ames, Iowa, 1980–1981) | The average method above 3.9 °C with temperatures over 29 °C set to 29, counted from when 5.7 cm soil reached 3.9 °C; adult to adult 392 °C·d (Sanborn's 376 plus 15.7 before egg laying); 50 % capture of each flight in Iowa at 190, 682 and 1181 °C·d, and Sanborn 1981's Wisconsin field data at 193, 584 and 1062 (Table 1); air temperatures overestimate field development (Iowa's flights 492 and 499 °C·d apart against the laboratory's 392); few flies in summer, suggesting the second generation aestivates | The method and its 29 °C cap (39 °F, 84.2 °F); the generation interval (706 °F·d, rounded to 720); 28 °F·d before egg laying; the field peaks as checks |
| Throne and Eckenrode 1985 (emergence traps, New York) | Emergence of over-wintered flies drawn out over the season; more of each generation entering diapause from June on; damage in the week or two during and after flight peaks | The first flight's wide spread; the caveat that later generations are smaller |
| Olaya-Arenas et al. 2024 ([doi:10.1093/jee/toae148](https://doi.org/10.1093/jee/toae148); New York; average method above 39 °F from January 1) | First emergence at 54–94 °F·d (2023; the abstract: a mean of 68 DD at base 39 °F); adults active at 214–417 (2022, abstract: a mean of 282); NEWA's 2022 model had predicted first emergence at 471 | The flight's start at 70 |
| Cho, Crowther, Stratton, Olmstead and Poveda 2025 ([doi:10.1016/j.cropro.2024.107011](https://doi.org/10.1016/j.cropro.2024.107011); abstract as indexed, paper not in hand) | First emergence at 52–197 degree days from January 1 (mean 98 ± 7 SE), 4 sites in 2023 and 25 in 2024; units not stated in the abstract; a press summary dates it March 8–April 2, 2024 (mean March 16) | A check on the start (below); NEWA's current table |
| NEWA's seedcorn maggot model (newa.cornell.edu, read 2026-11-21) | Air temperature, simple average above 3.9 °C, no upper, °C·d from January 1, to July 31: 0–52 overwintering pupae, 53–197 first adult emergence, 198+ complete (Cho et al. 2025; Broatch et al. 2006) | Compared (below) |
| The Crop Risk Tool (`src/models.R`, `scm`) | Single sine 4/30 °C from January 1; a step table peaking at 340, 1050 and 1750 (three generations); its text gives 360, 1080 and 1800 | Replaced (changelog 0.2); its 340 and 1050 are Sanborn 1981's Wisconsin peaks |
| VDIFN (`db/seeds.rb`) | Sine-ramped generations (peak − 65, peak, peak + 450) at 360 + 720*n*, single sine 39.2/86 °F | Replaced; its 720 kept, which the laboratory's 706 supports |
| Enviroweather (MSU), SeedCornMaggot (`docs/enviroweather-models.md`) | Single sine 39 °F, no upper, from March 1: over-wintered flight 200–813, peak 342; generation 1 flight 901–1650, peak 1234; no source cited | Compared only |

## Choices and differences

- **Degree days:** the sources' average method (D37): the day's high and low each capped at 84.2 °F (29 °C), averaged, less 39 °F (3.9 °C), from January 1. At Eau Claire in 2025 single sine (the tool's and VDIFN's method) ran 70–100 degree days ahead of this in spring, which would put each event 5–7 days early in spring and 2–3 days early in summer (Phase 3 D8).
- **Start:** January 1, where Funderburk et al. started when the soil at 5.7 cm reached 3.9 °C (February 16 and March 15 in their two years). At Eau Claire in 2025 the model had 52 degree days by March 15 (computed on `crt_daily_eau_claire_2025.csv`), so a January 1 start can put spring events earlier than the sources' counting would.
- **Adult flight:** a PERT curve from 70 to 650, most likely at 340; its 10, 50 and 90 % points are 201, 345 and 495.
- **Larval feeding:** derived from the flight: from 82 degree days after it (28 before egg laying plus the egg's 54), lasting 367. The first generation's feeding runs from about 150 to 1100 and peaks near 611.
- **Generations:** every 720 degree days, each as large as the first, spreading by an SD of 60 per generation, repeated until fall freezes end the season (D36's engine: after day 250, each day at or below −2 °C in the last 14 reduces activity, and 4 end it).
- **Risk:** flight plus larval feeding, both weighted 1 in each generation (egg laying leads to the feeding; Ben, 2026-10-29), continuous, with 1 meaning the first flight's peak. The action window "Avoid planting during adult flight" is open from 10 % to 90 % of each generation's flight.
- **Generation weights** (version 0.3; Ben, 2026-11-23): the over-wintered flight and the spring generation's larvae weigh 1 and each summer generation 0.25, since Iowa's second generation mostly aestivated and few flies were caught in summer (Funderburk et al. 1984; Throne and Eckenrode 1985), and the damage is to germinating seed of spring plantings. The sources say which generation matters, not by how much, so 0.25 is a judgment. With equal generations (version 0.2) the risk stayed High to Very high all summer (Phase 3 D8); now the summer generations peak at Moderate (below). The model still times every generation as large as the first; the weight is the risk only.
- **Differences from the Crop Risk Tool and VDIFN** (intended, Phase 3 D8): the method; the flight starting at 70 rather than 295; a continuous risk of flight and larvae rather than steps. The tool's parity test was dropped.

## Checks

### Against its sources' numbers

Computed from the model's own curves (`agmodels.phenology.generation_densities` on its 1-degree-day grid); no test in CI holds these numbers. Field peaks converted at × 1.8 from Funderburk et al. 1984, Table 1.

<!-- prettier-ignore -->
| Flight | Ours, 10 % / 50 % / 90 %, °F·d | Wisconsin fields, 50 % (Sanborn 1981) | Iowa, 50 % (Funderburk et al., mean of 1980 and 1981) |
| --- | --- | --- | --- |
| Over-wintered | 201 / 345 / 495 | 347 | 342 |
| First generation | 904 / 1065 / 1232 | 1051 | 1228 |
| Second generation | 1607 / 1785 / 1968 | 1912 | 2126 (a small, early cohort) |

- **The first flight is in sample:** its curve was set so that 50 % falls near Wisconsin's 347 and the start (70) inside New York's first emergence (54–94; Olaya-Arenas et al. 2024). Its agreement shows the fit, not a test.
- **The later flights are out of sample:** they follow from the laboratory's adult-to-adult time (706, rounded to 720), not from the field peaks. Against Wisconsin, the first generation's midpoint is 14 degree days late and the second's 127 early (Wisconsin's flights were 704 and then 860 apart). Against Iowa, the first generation's midpoint is 163 early: Funderburk et al. found field development slower than air temperatures predict in every interval, which they put down to the soil, where the insects develop, being cooler than the air.
- The sources' totals count from when the soil reached 3.9 °C; ours from January 1 (above). With the 52 degree days Eau Claire had by March 15, 2025, all our dates would come earlier than these thresholds suggest.

The engine's mechanics are tested on a made-up insect (`test_phenology.py`: each generation's mean and variance add as they should, windows open at 10 % and close at 90 %, the freeze factor ends the season), and the model's own windows and levels in `test_runner.py` and `test_scenarios.py` (the first window falls between April 1 and July 1 on the test weather). Those check the machinery, not the biology.

### Against the Crop Risk Tool on the same weather

Computed from the tool's fixtures for one cell at Eau Claire, Wisconsin, through 2025 (`crt_daily_eau_claire_2025.csv`, `crt_insect_scm_eau_claire_2025.csv`, made by the tool's own R code); no test asserts it. The tool's flight peaks (the start of severity 4 at 340, 1050 and 1750 on its sine total) against the day half of each of our flights has emerged (345, 1065 and 1785 on ours):

<!-- prettier-ignore -->
| Flight | The tool's peak | Ours, 50 % | Days later |
| --- | --- | --- | --- |
| Over-wintered | April 29 | May 5 | 6 |
| First generation | June 5 | June 8 | 3 |
| Second generation | June 29 | July 2 | 3 |

At the end of April the tool's total was 361 against our 294, and at the end of June 1802 against 1731: the method, not the thresholds, makes most of the difference. The tool is the system v2 replaces, a reference rather than the truth (D54).

### Units of New York's first-emergence numbers

Our flight's start (70 °F·d) came from Olaya-Arenas et al. 2024's first emergence, "54–94 FDD". The paper's abstract (Crossref) gives its method as the average above 39 °F from January 1 and its 2023 mean as 68 DD: degree-Fahrenheit days, so the start stands. Cho et al. 2025's 52–197 (mean 98) are the same group's, same method; their abstract gives no unit, but the mean date of first emergence in 2024, March 16, settles it: at Geneva, New York, the average above 39 °F from January 1, 2024 reached 94 °F·d (52 °C·d) on March 8, 142 °F·d (79 °C·d) on March 16 and 177 °F·d (98 °C·d) on April 2 (Open-Meteo's archive at 42.88 °N, 77.03 °W, fetched 2026-11-21). A mean of 98 °C·d would fall in early April, at the end of their range of dates; 98 °F·d falls in early to mid-March, inside it. NEWA's table (53–197 °C·d, 95–355 °F·d) reads the numbers as Celsius, which asks 1.8 times the degree days the studies found before the window opens. The start stays at 70 °F·d, inside both papers' ranges (`test_maggots.py::test_seedcorn_maggots_first_flight_starts_within_new_yorks_first_emergence`).

### Against NEWA on the same weather

`scripts/check_maggots.py`; full table in [seedcorn-maggot/newa.md](seedcorn-maggot/newa.md). NEWA's model as deployed, recomputed from its rules (`scripts/newa_reference.py`: the simple average above 3.9 °C in °C·d from January 1; its first-emergence window opens at 53 and closes at 198) on the hours of 34 Wisconsin NEWA stations, 2024 and 2025 (67 station-seasons); ours (average 39/84.2 °F) on the same daily max and min, and on the archive at each station's cell.

<!-- prettier-ignore -->
| Ours − NEWA's, days | Station days: median (10th–90th percentile; range) | Archive: median (10th–90th percentile) |
| --- | --- | --- |
| Our flight's first day (70 °F·d) against NEWA's window opening (53 °C·d, 95 °F·d) | −5 (−13 to −2; −16 to −1) | −7 (−13 to −2) |
| Our flight's 50 % (345 °F·d) against NEWA's window closing (198 °C·d, 356 °F·d) | −1 (−2 to 0; −4 to 0) | 0 (−4 to +1) |

Our flight starts a median 5 days before NEWA's first-emergence window opens and is half over a median 1 day before the window closes. The two differ by design, not by method (both are the simple average above 39 °F, ours capping each temperature at 84.2 °F, which spring days don't reach): NEWA's window is the studies' first-emergence range read as °C·d (above), so it covers most of our spring flight rather than its first flies. NEWA has no later generations (its season ends July 31). D95 changes nothing here: the method is the same family, and NEWA's thresholds rest on the unit reading above.

### What the weights change

`uv run app/manage.py shell < scripts/generation_weights_normals.py`: the risk on the same normal totals with every generation alike (version 0.2) and with version 0.3's generation weights, at each peak of the risk through October 15, without fall freezes.

<!-- prettier-ignore -->
| Place | Peak | Equal generations | Weighted |
| --- | --- | --- | --- |
| Arlington | May 7 | 1.38 (Very high) | 1.38 (Very high) |
| Arlington | June 10 | 1.33 (Very high) | 0.33 (Moderate) |
| Arlington | July 4 | 1.28 (Very high) | 0.32 (Moderate) |
| Arlington | July 27 | 1.24 (Very high) | 0.31 (Moderate) |
| Arlington | August 19 | 1.21 (Very high) | 0.30 (Moderate) |
| Arlington | September 15 | 1.18 (Very high) | 0.30 (Moderate) |
| Arlington | Days at High or above | 181 | 40 |
| Hancock | May 12 | 1.38 (Very high) | 1.38 (Very high) |
| Hancock | June 14 | 1.33 (Very high) | 0.33 (Moderate) |
| Hancock | July 9 | 1.28 (Very high) | 0.32 (Moderate) |
| Hancock | August 2 | 1.24 (Very high) | 0.31 (Moderate) |
| Hancock | August 27 | 1.21 (Very high) | 0.30 (Moderate) |
| Hancock | September 27 | 1.18 (Very high) | 0.30 (Moderate) |
| Hancock | Days at High or above | 176 | 39 |
| Rhinelander | May 20 | 1.38 (Very high) | 1.38 (Very high) |
| Rhinelander | June 22 | 1.33 (Very high) | 0.33 (Moderate) |
| Rhinelander | July 18 | 1.28 (Very high) | 0.32 (Moderate) |
| Rhinelander | August 13 | 1.24 (Very high) | 0.31 (Moderate) |
| Rhinelander | September 13 | 1.21 (Very high) | 0.30 (Moderate) |
| Rhinelander | Days at High or above | 167 | 38 |

The spring generation stays Very high; each summer generation now peaks at Moderate, and a season has about 40 days at High or above instead of nearly every day from early May to October.

## Limits and open questions

- **No field check in Wisconsin:** the over-wintered flight is fitted to Wisconsin's and New York's numbers, and the later flights are checked only against two published sets of peaks: Sanborn's Wisconsin flights (from his 1981 dissertation, as Funderburk et al. report them) and 2 years of traps in Iowa.
- **Air, not soil:** the insects develop in soil cooler than the air (Funderburk et al. 1984), so later generations may come later than shown, as Iowa's did.
- **The summer generations' weight (0.25)** is a judgment: the sources say the spring generation matters and the summer one mostly aestivated (in Iowa), not by how much.
- **The model page** says larval feeding is heaviest "around 650" (the curve peaks near 611).
- **NEWA's units** (above) are for the courtesy email to NEWA, with its soil-temperature description against its air computation and its table against its hidden per-crop guide (255–434 adults, 461–1030 first generation).
- **Cheapest independent comparison** now: dated flight records, such as Olaya-Arenas et al. 2024's and Cho et al. 2025's New York traps (if the papers give sites and dates) on Open-Meteo's weather, or Wisconsin trap catches if any are kept.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_phenology.py packages/agmodels/tests/test_runner.py packages/agmodels/tests/test_maggots.py
uv run python scripts/check_maggots.py   # NEWA on the same weather; needs the archive in data/ and tmp/newa/hours/
uv run python -c "
import numpy as np
from agmodels.phenology import dd_grid, generation_densities
from agmodels.registry import all_insects
insect = next(i for i in all_insects() if i.id == 'seedcorn-maggot')
x = dd_grid()
for g, d in enumerate(generation_densities(insect=insect, stage=insect.life_stages[0])[:3]):
    c = np.cumsum(d) / d.sum()
    print(g, [float(x[np.argmax(c >= p)]) for p in (0.1, 0.5, 0.9)])
"
uv run app/manage.py shell < scripts/generation_weights_normals.py  # what the generation weights change
```

The comparison with the tool: run `model("seedcorn-maggot").outputs()` on `crt_daily_eau_claire_2025.csv`'s minimum and maximum and find the days `dd_total` reaches 345, 1065 and 1785, against the days `crt_insect_scm_eau_claire_2025.csv`'s `cum_gdd` reaches 340, 1050 and 1750.
