# Wheat scab (`wheat-scab`): validation

Model version 0.4, written 2026-11-18 (D98), updated 2026-11-19 for 0.2, 0.3 and 0.4. The model: `packages/agmodels/src/agmodels/models/wheat_scab.py`, with its risk levels from `agmodels.probability`; shown May 1 to July 31, gated by flowering at a point (below); its page: `wheat_scab.md` beside it. Ported from the Crop Risk Tool (`tmp/R/crop-risk-tool/src/models.R`, `predict_wheat_scab`, `build_wheat_scab`) in Phase 3 (Phase 3 D step 2); audited against the model team's documents on 2026-11-19 (`tmp/crt-model-audit-2-wheat-rcr.md`).

**In short:** model M6 of the U.S. Fusarium head blight prediction models (Shah et al. 2013's model 3; M6 in Shah et al. 2021), with the coefficients the model team refit for 2026 ("Wheat Scab Models Deployment 2026", unpublished): the probability of severe head blight (field severity of 10 % or more) for wheat flowering on the day, from the mean RH of the 14 days before, by resistance class. The port matches the deployment document term for term and the Crop Risk Tool on every day once the window is full (shifted a day: v2's window ends the day before, as the deployment says). It's shown May 1 to July 31, with the national FHB Risk Tool's three levels. Since 0.3 a point is gated by flowering (D33's `susceptibility`) from a spring wheat planting date the user gives (`spring-wheat-stages`, Haun 10.2 through 7 days after 11.4, since 0.4) or a flowering date the user gives for any wheat (that day through 7 days after); the map stays ungated, the risk for wheat flowering on each day. It hasn't been compared with scab in fields.

## Sources and what we took from each

<!-- prettier-ignore -->
| Source | What it gives | What we took |
| --- | --- | --- |
| Shah, Molineros, Paul, Willyerd, Madden and De Wolf 2013, Phytopathology 103:906–919 (doi:10.1094/PHYTO-11-12-0304-R) | Pre-anthesis logistic models of FHB epidemics (severity ≥ 10 %); model 3: resistance (three dummy variables) plus the 14-day mean RH before anthesis | The model's form and its meaning |
| Shah, De Wolf, Paul and Madden 2021, PLOS Computational Biology 17:e1008831 (doi:10.1371/journal.pcbi.1008831) | The model set the national tool ensembles; this one is M6 (Table S2) | Cited |
| "Wheat Scab Models Deployment 2026" and "Fusarium Head Blight of Wheat v20260216" (`tmp/R/crop-risk-tool-models/Wheat scab/`) | M6's coefficients refit for 2026 (linear in RH; no spring/winter term; resistance odds ratios 0.44, 0.23, 0.16 against 2013's 0.53, 0.27, 0.22); the window is the 14 days before flowering; levels Low below 24 %, Moderate from 24 %, High from 32 % | The coefficients (as the tool has them), the window's end, the levels |
| The Crop Risk Tool (`src/models.R`, `predict_wheat_scab`, `build_wheat_scab`; `docs/wheat-scab.md`) | The same logit, −3.6432643 + shift + 0.051459669·RH14; shifts: very susceptible 0, susceptible −0.82795556, moderately susceptible −1.4812696, moderately resistant −1.8484537; risk Low from 1 %, Moderate from 24 %, High from 32 %; every day of the year; its code credits De Wolf at "U. Kentucky" (he is at Kansas State) | The coefficients; susceptible as the default class |
| The national Fusarium Head Blight Risk Tool (wheatscab.psu.edu) | A map of the risk for wheat flowering on the date shown, susceptible by default, April to August, no stage gate: the grower reads it at their own flowering | The framing and the season's span |
| Crop Protection Network, an overview of Fusarium head blight (Friskop et al. 2021); Smith 2022, Wisconsin Crop Manager | Spray the heads from the start of flowering (Feekes 10.5.1) to about 7 days after; in Wisconsin research about 5 days after flowering began cut DON the most | The flowering date's window (0.3): that day through 7 days after |
| `spring-wheat-stages` (Bauer et al. 1984, as NDAWN runs it) | Haun stages by GDD from planting: heading begins 10.2 at 1567, flowering 11.4–11.6 at 1739–1768, watery ripe 12.0 at 1825 | Spring wheat's window (0.3): Haun 10.2 through 11.6 (until 12.0) |

## Choices and differences

- **Resistance:** an option, susceptible by default; the model also gives all four classes' probabilities as outputs.
- **The window:** the mean RH of the 14 days before the day (ending the day before flowering, as the deployment document has it), given only when 12 or more of them are known; the tool's window includes the day itself and takes any known days. On June to mid-July 2025 the shift changes the 14-day mean by 0.8 points on average (at most 2.9).
- **Season:** May 1 to July 31, covering Wisconsin's winter wheat flowering (late May to mid June) and spring wheat's (late June to mid July). Until 0.2 it was shown every day, High on many winter days for susceptible varieties (17 High and 27 Moderate days in January and February 2025 at Eau Claire).
- **Levels:** Low below 24 %, Moderate from 24 %, High from 32 % (the national tool's); the tool's Very low below 1 % was unreachable in any plausible weather.
- **The flowering gate (0.3):** the model is for wheat flowering on the day shown, so the days that matter for a field are its flowering. The gate is D33's `susceptibility` beside the probability (2 in the window, 1 for 3 days either side, 0 elsewhere), not missing values: missing means no data (CLAUDE.md), and the greyed values still say what the risk would be for a field flowering then. Two ways in, at a point only:
  - **A flowering date the user gives** (`flowering_date`, YYYY-MM-DD; `StageDate`): that day through 7 days after, the fungicide window from Feekes 10.5.1 in the CPN overview and Smith 2022. We chose the spray window over a window centred on the date because Shah et al. 2013 predict for the day of anthesis and the decision it informs runs from early flowering onward; the 3 muted days before cover a date a few days off and the forecast's approach. It's the only gate for winter wheat (no stage model yet, the models plan's part J), and it replaces the estimate for spring wheat.
  - **A spring wheat planting date the user gives:** `spring-wheat-stages` from it, susceptible from heading (Haun 10.2) through 7 days after flowering begins (11.4), as for a flowering date (`Susceptibility.extend_days`), muted the stage model's 3 days either side. Until 0.4 it ended at the end of flowering (11.6, so until watery ripe, 12.0): under NDAWN's table only about 2–3 days after flowering begins (1739 to 1825 GDD), short of the fungicide window (Ben, 2026-11-19).
  - **Never from a typical planting date** (`Susceptibility.planting_given_only`): the model's crop `wheat` covers winter wheat too, so a point without a planting date isn't gated (`series.with_planting` skips it), and **the map isn't gated** (`planting.map_crop` is None: no `planting=` tier, no `susceptibility` output), staying the risk for wheat flowering on each day as on the national tool's map. The map's speed is unchanged (no stage model per cell).
- **Weather:** the tool runs on Open-Meteo (about 9 km); v2 on the 2.5 km archive. Not compared on the same place and days.

## Checks

### Against the Crop Risk Tool on the same weather

The Crop Risk Tool is the program this model replaces: a reference, not the truth (D54). Run in CI, on the tool's own recorded weather for one Open-Meteo cell at Eau Claire, Wisconsin (44.815, −91.530), through 2025, with fixtures written by the tool's R code (`packages/agmodels/tests/fixtures/make_crt_fixtures.R`):

- `test_field_crops.py::test_wheat_scab_resistance_classes_match`: given the tool's daily inputs, v2's probability on each day from January 15, 2025 equals the tool's on the day before (`crt_wheat_scab_eau_claire_2025.csv`), within 1e-9, for each of the four resistance classes: the same model with the window ending a day earlier. The first 12 days have no value (fewer than 12 days before them). Until 0.2 the two matched day for day on all 365 days.
- `test_field_crops.py::test_wheat_scab_levels_are_the_national_tools`: Low below 24 %, Moderate from 24 %, High from 32 %, never Very low.

### The flowering gate

On synthetic weather (CI): `test_runner.py::test_wheat_scab_*`: no gate without a planting or flowering date; with a spring wheat planting date, susceptible exactly from the day `spring-wheat-stages` reaches Haun 10.2 to the day before 12.0, muted 3 days either side, and the probabilities identical to the ungated run's; a flowering date gives that day through 7 days after (muted 3 days either side), with or without a planting date; missing humidity stays missing (no probability, no level) inside the window. `test_models.py::test_wheat_scab_is_gated_by_a_flowering_date_the_user_gives` (the API's `susceptibility` column, a malformed date refused), `test_grids.py::test_wheat_scab_map_is_not_gated_by_spring_wheat` (the map refuses `planting` and `flowering_date`), `test_planting.py::test_a_gate_from_a_given_planting_only_has_no_map_tier_or_typical_date`.

### The 2025 season at Eau Claire

From the audit (`tmp/crt-model-audit-2-wheat-rcr.md`, on the tool's 2025 weather): where each class turns, by the 14-day mean RH, Moderate (24 %) and High (32 %) from 48.4 and 56.2 % (very susceptible), 64.5 and 72.2 % (susceptible), 77.2 and 84.9 % (moderately susceptible), 84.3 and 92.1 % (moderately resistant). Over May 15 to July 31, 2025, Low / Moderate / High days were 0 / 0 / 78 for very susceptible, 19 / 13 / 46 susceptible, 58 / 20 / 0 moderately susceptible and 78 / 0 / 0 moderately resistant: in Wisconsin's humidity the class decides the level more than the weather does. At spring wheat's estimated flowering (Haun 11.4 on June 21–30 for plantings April 15 to May 5) susceptible was 33.6–35.6 % (High); at winter wheat's in early June (June 1–10), 24.1–24.4 % (just Moderate).

## Limits and open questions

- **Read only at flowering:** the probability is for a field flowering on the day shown; inside the season, other days' values describe other flowering dates. The gate (above) marks a field's flowering at a point; the map can't, and a site's crop (winter or spring wheat) isn't known to the runner until sites exist (step 7).
- **Spring wheat's stage dates** haven't been compared with observed ones; its window ends 7 days after the estimated start of flowering (0.4).
- **High in ordinary weather:** a 14-day mean RH of 70 % gives a susceptible variety 29.5 % (Moderate) and 80 % gives 41.2 % (High) (`wheat_scab.probabilities`).
- **Unpublished refit:** the 2026 coefficients aren't published; Shah et al. 2013's own cut-point for this model was 0.31. Questions for the model team (Shah, Paul, De Wolf, Madden): the refit's data and publication, the day's definition (08:00 to 08:00 in 2013, or midnight to midnight), the origin of the 24 and 32 % cut-points, and whether the window is 14 days (the deployment) or 15 (Purdue's 2026 article).
- **No observations:** not compared with Fusarium head blight in Wisconsin wheat.
- **Cheapest independent comparison:** the national FHB Risk Tool on the same days and places (a system comparison from the same authors, not observations); then UW's wheat disease survey records with flowering dates.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_field_crops.py
Rscript --no-init-file packages/agmodels/tests/fixtures/make_crt_fixtures.R   # the tool's fixtures (needs tmp/R/crop-risk-tool, Phase 3 F)
```
