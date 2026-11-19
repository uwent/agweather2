# Red crown rot (`red-crown-rot`): validation

Model version 0.2 (beta), written 2026-11-18 (D98). The model: `packages/agmodels/src/agmodels/models/red_crown_rot.py`, anchored to R1 (beginning flowering) from `soybean-stages` or the grower's date (`biofix_stage`, D33); on the map computed on request from each cell's R1 (`modelgrid.ON_REQUEST`; PLAN.md Phase 5 step 2b); its page: `red_crown_rot.md` beside it (the tool's text, rewritten in part I2). Ported from the Crop Risk Tool (`tmp/R/crop-risk-tool/src/models.R`, `predict_red_crown_rot`, `build_red_crown_rot`, "CPN CRT ver. 1.0, 2026-08-12") in Phase 3 (PLAN.md Phase 3 D step 2).

**In short:** the port reproduces the Crop Risk Tool exactly: given the tool's daily weather for 2025 at Eau Claire and R1 on July 1, incidence, rain before R1 and mean temperature from R1 match on every day of the year. Where rain is missing v2 sums the known days and says how many are missing, where the tool filled them with the mean of the others (tested). The model comes from field surveys in northern Japan (Ochi et al. 2026) and hasn't been tested in the United States; its risk levels are provisional, and the lowest, Very low, can't be reached in any weather.

## Sources and what we took from each

<!-- prettier-ignore -->
| Source | What it gives | What we took |
| --- | --- | --- |
| Ochi, Kishi, Kawaguchi and Akamatsu 2026, Phytopathology 116:1405–1413 (doi:10.1094/PHYTO-06-25-0207-R) | Logistic models of field-level incidence of red crown rot from weather around R1, from surveys of 242 soybean fields in northern Japan (the tool's page; no copy in `tmp/references/`) | The three single-variable models and their weights, through the tool |
| The Crop Risk Tool (`src/models.R`; `docs/red-crown-rot.md`) | Incidence = 1 / (1 + e^logit) for each of: the mean temperature over the 31 days from R1, 15.067 − 0.602·T; rain over the 31 days before R1, 0.184 − 0.004·P (mm); rain over the 31 days from R1, −1.257 + 0.005·P; combined with weights 0.66, 0.16 and 0.18 (each model's R² over their sum: 0.33, 0.08 and 0.09 of 0.50). Until 31 days after R1, the mean temperature so far and rain prorated to 31 days; then the final values hold. Rain before R1 with missing days as the mean of the known days times 31. Risk, provisional: Very low below 5 %, Low from 5 %, Moderate from 30 %, High from 60 %. "Past history of red crown rot in a field was the strongest predictor of disease in the original study, and is not included in this model" | Everything but missing rain (below) |
| Crop Protection Network, red crown rot of soybean | Background on the disease | Cited only |

## Choices and differences

- **Missing rain** (version 0.2, D45): rain is the sum of the known days; missing days count as no rain and are reported in `precipitation_days_missing`, as are days filled by the runner and days of the window before the series starts. The rain from R1 is prorated over the days elapsed, not the days known. The tool took the mean of the known days times 31, which estimates the missing ones. The same without gaps.
- **R1:** `soybean-stages`' R1 from the planting date (typical or the grower's), or the grower's R1; July 1 when neither is given (the spec's default). If the planting hasn't reached R1 in the series, the model hasn't started (PLAN.md Phase 5, "Runner change").
- **Weather:** the tool runs on Open-Meteo (about 9 km); v2 on the 2.5 km archive. Not compared on the same place and days.

## Checks

### Against the Crop Risk Tool on the same weather

The Crop Risk Tool is the program this model replaces: a reference, not the truth (D54). Run in CI, on the tool's own recorded weather for one Open-Meteo cell at Eau Claire, Wisconsin (44.815, −91.530), through 2025, with fixtures written by the tool's R code (`packages/agmodels/tests/fixtures/make_crt_fixtures.R`):

- `test_field_crops.py::test_red_crown_rot_matches_from_r1`: with R1 on July 1, 2025, v2's incidence, rain in the 31 days before R1 and mean temperature from R1 equal the tool's (`crt_red_crown_rot_r1_2025_07_01_eau_claire_2025.csv`) on all 365 days of 2025, within 1e-9, missing on the same days (incidence has values on the 184 days from R1).
- The risk levels use the same function as the tool's `risk_from_prob`, which `test_field_crops.py::test_probability_levels_match` checks at two other sets of thresholds; this model's (5, 30, 60 %) aren't tested against the tool directly.

### Missing rain

- `test_field_crops.py::test_red_crown_rot_counts_missing_rain_as_none`: with three days of rain removed (two before R1, one after), each total is the sum of the remaining days, and the count of missing days is 2 before R1, 2 after it and 3 at the year's end; on the year without gaps it's 0.
- `test_field_crops.py::test_red_crown_rot_counts_the_window_before_the_series_as_missing`: with R1 on the series' 11th day, the 21 days of the window before the series count as missing.

### The 2025 season at Eau Claire

From the tool's fixture (computed for this report; no test holds it), with R1 on July 1, 2025: predicted incidence ran 30.7 % to 45.5 % while the windows filled, and held at 34.2 % from July 31; Moderate on every day from R1.

## Limits and open questions

- **Developed in Japan:** the fit comes from 242 fields in northern Japan. The tool calls it "in the testing phase for application in the US", and its page says the risk thresholds "have not been validated in the United States"; ours are the same, provisional.
- **Very low can't be reached:** each single-variable model is bounded by its weather, so the weighted sum has a floor. By the coefficients, with no rain in the 31 days before R1, a mean of 0 °C from R1 and unlimited rain after it, incidence is still 7.3 %; with 400 mm after R1 it's 13.1 % (`red_crown_rot.incidence`). So the Very low level (below 5 %) never shows, and Low needs a cool month after R1. A design question for the provisional levels, not a bug in the port.
- **A field's history isn't in it**, though it was the strongest predictor in the original study (the tool's page).
- **The docstring's weights:** the module's docstring says the ensemble "weighs each by its R² (0.66, 0.16, 0.18)"; those are each model's share of the summed R² (R² 0.33, 0.08 and 0.09; the tool's comment). The numbers used are right.
- **Map speed:** computed on request from each cell's R1, 2.4 s cold and about 0.7 s warm over the Wisconsin window, over the 300 ms target (PLAN.md Phase 5 step 2b); to cache or vectorize if the map is used much.
- **Cheapest independent comparison:** field incidence surveys with R1 dates from the states where red crown rot has been confirmed (Illinois, Kentucky and others named on the tool's page), run on the archive or Open-Meteo at those fields; Wisconsin isn't among the states the tool's page names.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_field_crops.py
Rscript --no-init-file packages/agmodels/tests/fixtures/make_crt_fixtures.R   # the tool's fixtures (needs tmp/R/crop-risk-tool, PLAN.md Phase 3 F)
```
