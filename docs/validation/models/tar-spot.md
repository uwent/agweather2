# Tar spot (`tar-spot`): validation

Model version 0.3, written 2026-11-18 (D98). The model: `packages/agmodels/src/agmodels/models/tar_spot.py`, with its humid night hours from `agmodels.features` (`hours_rh_over_90_7pm_to_6am`) and its cold scaling and risk levels from `agmodels.probability`; gated by `corn-stages` (V10 to R3, D33); its page: `tar_spot.md` beside it (a two-sentence stub, rewritten in part I2). Ported from the Crop Risk Tool (`tmp/shiny/crop-risk-tool/src/models.R`, `predict_tarspot`, `build_tar_spot`) in Phase 3 (PLAN.md Phase 3 D step 2).

**In short:** the port reproduces the Crop Risk Tool exactly: given the tool's daily weather for 2025 at Eau Claire, the probability matches on all 365 days. That shows a faithful port, not a right model: the model hasn't been compared with tar spot observations. Read against the paper (2026-11-18), the two equations and their coefficients are its LR4 and LR6, and more humid weather lowering the probability is what the paper found; but the paper's response is an increase in tar spot severity between two ratings, not spore presence, so version 0.3 renamed the model and its output (below).

## Sources and what we took from each

<!-- prettier-ignore -->
| Source | What it gives | What we took |
| --- | --- | --- |
| Webster et al. 2023, Scientific Reports 13:17064 (doi:10.1038/s41598-023-44338-6) | Eight logistic models of an increase in *Phyllachora maydis* severity between two sequential ratings (response 1 for any increase, 0 for none; 96 and 310 observations) from moving averages of weather; a 35 % threshold for classifying (open access, PMC10564858) | The two models, through the tool: LR4 (30-day mean temperature, 30-day mean daily maximum RH) and LR6 (30-day mean temperature, 14-day mean nighttime hours with RH > 90 %), coefficients identical |
| The Crop Risk Tool (`src/models.R`, `predict_tarspot`, `build_tar_spot`; `docs/tar-spot.md`) | Two logits: 32.06987 − 0.89471·T30 − 0.14373·RHmax30 and 20.35950 − 0.91093·T30 − 0.29240·N14 (T30 the 30-day mean temperature, °C; RHmax30 the 30-day mean daily maximum RH; N14 the 14-day mean night hours with RH ≥ 90 %), each through the logistic, averaged; scaled down as the 21-day mean minimum falls below 10 °C ("this model overwinters at 100% risk"); risk Low from 1 %, Moderate from 20 %, High from 35 %; susceptible V10–R3; credit Damon Smith (UW–Madison) and Wade Webster (NDSU) | Everything, unchanged |
| Crop Protection Network, tar spot of corn | Background on the disease | Cited only |

## Choices and differences

- **Night hours:** the readings stamped 20:00 to 06:00 (11 hours, 7 p.m. to 6 a.m. under D74's window rule), the night the tool counts and the coefficients were fitted on. Since version 0.2 they're on CST all year, so in summer v2's night is an hour later by the clock than the tool's (PLAN.md D74).
- **Gridded humidity:** on the archive an hour counts as RH ≥ 90 % at 88 % (D50, `features.STATION_RH_90_AS_GRIDDED`), because the archive's RH ≥ 88 % counts as many hours as 80 Wisconet stations' RH ≥ 90 %; a station's own hours (a POSTed run) count at 90 %. The weather the fit used is unknown (Ben, 2026-10-31: perhaps IBM's EIS), so the correction applies anyway. Its effect on this model hasn't been measured.
- **Weather:** the tool runs on Open-Meteo (about 9 km, its README); v2 on the 2.5 km archive. Not compared on the same place and days.
- **Season and gate:** the spec's season is July 1 to August 15 (the tool's), and the risk is shown as susceptible from V10 to R3 of `corn-stages` with its 3-day margin (D33).
- **Not modelled:** the tool's comment lists "No risk: Fungicide in last 14 days, temperature <32F"; neither it nor v2 applies them beyond the cold scaling.

## Checks

### Against the Crop Risk Tool on the same weather

The Crop Risk Tool is the program this model replaces: a reference, not the truth (D54). Run in CI, on the tool's own recorded weather for one Open-Meteo cell at Eau Claire, Wisconsin (44.815, −91.530), through 2025, with fixtures written by the tool's R code (`packages/agmodels/tests/fixtures/make_crt_fixtures.R`):

- `test_field_crops.py::test_probability_matches`: given the tool's daily inputs (`crt_daily_eau_claire_2025.csv`, `crt_daily_more_eau_claire_2025.csv`), v2's probability equals the tool's (`crt_tar_spot_eau_claire_2025.csv`) on all 365 days of 2025, within 1e-9, cold scaling included.
- `test_features.py::test_tar_spots_night_matches_the_crop_risk_tool`: from the tool's hourly weather, v2's night count (at the tool's 90 %, on the tool's local clock) equals the tool's on every day of 2025.
- `test_field_crops.py::test_probability_levels_match`: v2's risk levels equal the tool's `risk_from_prob` at this model's thresholds (1, 20, 35 %) at 201 probabilities from 0 to 1.

These show the port reproduces the tool. They don't test D50's 88 % or the CST night, which the tool doesn't use.

### By hand

`test_logistic_by_hand.py::test_tar_spot_averages_two_logistic_models`: at a 30-day mean of 20 °C, maximum RH 95 % and 8 night hours, the two logits worked out with `math` average to 53.9 %, and the model gives the same. This checks the arithmetic against the coefficients in the module, not against the paper.

### Crop stage window

`test_crops.py::test_tar_spot_and_don_windows_over_a_season`: corn planted April 22 in the recorded 2000 season at Lincoln (`fixtures/phenology_weather.csv`) is susceptible to tar spot for between 26 and 59 days (V10 to the end of milk, about six weeks), with silking inside it.

### The 2025 season at Eau Claire

From the tool's fixture (computed for this report; no test holds it): over the spec's season, July 1 to August 15, 2025 (46 days), the probability ran 11.9 % to 64.7 % (median 24.8 %): 14 days Low, 25 Moderate and 7 High. Its highest of the year, 99.7 %, came on June 14, before the season.

## Limits and open questions

- **What the probability is, and the direction of humidity (read against the paper, 2026-11-18):** the coefficients in `tar_spot.probability` are Webster et al. 2023's LR4 and LR6 exactly (Results, "Development of predictive models", equations 4 and 6). Both logits fall as temperature and humidity rise: at a 30-day mean of 22 °C, a maximum RH of 100 % and 10 night hours give 9.5 %, while 80 % and 2 hours give 57 %; 18 °C gives 87 % and 26 °C 0.6 % at 95 % and 8 hours (`tar_spot.probability`). That direction is the paper's own finding (Discussion: "tar spot is discouraged by extended periods of high relative humidity (> 90%)"), so it isn't a sign slip, though it runs against the Crop Risk Tool's page ("high relative humidity and prolonged leaf wetness favor disease development"). The paper doesn't write out the link function; the standard inverse logit (the tool's and ours) is assumed. **Until version 0.3 the model's name, output label, summary and page called the result the probability of spores being present; the paper's response is an increase in tar spot severity between two sequential ratings** (Methods, "Data collection"). Version 0.3 renamed the model and its output for what it predicts (2026-11-18); and the night-hour count is the paper's RH > 90 % where ours counts ≥ 90 % (88 % on the grid, D50).
- **No observations:** the model hasn't been compared with tar spot's appearance in Wisconsin fields.
- **D50 on this model:** counting gridded hours at 88 % adds night hours, which (as coded) lowers the probability; how much hasn't been measured.
- **Cheapest independent comparison:** UW Field Crops Pathology's tar spot survey records (fields and dates of first detection in Wisconsin) against the model's July risk on the archive at those fields.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_field_crops.py packages/agmodels/tests/test_features.py packages/agmodels/tests/test_logistic_by_hand.py packages/agmodels/tests/test_crops.py
Rscript --no-init-file packages/agmodels/tests/fixtures/make_crt_fixtures.R   # the tool's fixtures (needs tmp/shiny/crop-risk-tool, PLAN.md Phase 3 F)
```
