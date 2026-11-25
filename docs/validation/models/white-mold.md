# White mold (`white-mold`): validation

Model version 0.2, written 2026-11-18 (D98), updated 2026-11-19 for 0.2. The model: `packages/agmodels/src/agmodels/models/white_mold.py`, with its risk levels from `agmodels.probability`; gated by `soybean-stages` (R1 to R3, D33); its page: `white_mold.md` beside it (a two-sentence stub, rewritten in part I2). Ported from the Crop Risk Tool (`tmp/R/crop-risk-tool/src/models.R`, `predict_white_mold_dry`, `predict_white_mold_irrig`, `build_white_mold`) in Phase 3 (Phase 3 D step 2).

**In short:** the equations of the 2025 Soybean White Mold Model Algorithm (Smith, Willbur and Webster; Willbur et al. 2018's models), with two corrections to the Crop Risk Tool it was ported from (0.2, from the audit in `tmp/crt-model-audit.md`): the third non-irrigated logit's temperature coefficient is −0.56, not the tool's −0.86, and the algorithm's gate (inactive unless the 30-day mean maximum is above 10 °C) replaces the tool's scaling by the 21-day mean minimum. Given the tool's daily weather for 2025 at Eau Claire, the irrigated probability matches the tool's on every day the model is active; the non-irrigated one runs about 1.5 times the tool's in summer. The model hasn't been compared with apothecia counts or white mold in fields.

## Sources and what we took from each

<!-- prettier-ignore -->
| Source | What it gives | What we took |
| --- | --- | --- |
| Willbur et al. 2018, Plant Disease 102:73–84 (doi:10.1094/PDIS-04-17-0504-RE) | Logistic models of *Sclerotinia sclerotiorum* apothecia in soybean fields from 30-day moving averages of weather, for non-irrigated and irrigated fields (cited by the tool; no copy in `tmp/references/`) | The models, through the tool |
| The 2025 Soybean White Mold Model Algorithm (Smith, Willbur and Webster; `tmp/R/crop-risk-tool-models/`) | The same models as the tool but the third non-irrigated logit's temperature coefficient (−0.56), and a gate: the models run only while the 30-day mean maximum is above 10 °C | The −0.56 and the gate (0.2) |
| The Crop Risk Tool (`src/models.R`; `docs/white-mold.md`) | Non-irrigated: three logits, −0.47·T − 1.01·W + 16.65, −0.68·T + 17.19 and −0.86·T + 0.1·RH − 0.75·W + 8.2 (T the 30-day mean daily maximum temperature, °C; W the 30-day mean daily maximum wind, m/s; RH the 30-day mean daily maximum RH), each through the logistic, averaged, then scaled down as the 21-day mean minimum falls below 10 °C; risk Low from 1 %, Moderate from 20 %, High from 35 %. Irrigated: one logit, −52.65 − 2.38·(30-inch rows) + 0.65·T + 0.38·RH, not scaled; risk Low from 1 %, Moderate from 5 %, High from 10 %. Susceptible R1–R3; credit Damon Smith (UW–Madison) and Wade Webster (NDSU) | Everything but the −0.86 (a transcription error: with it the third logit stays under 0.2 % all summer) and the cold scaling |
| Crop Protection Network, white mold of soybean | Background on the disease | Cited only |

## Choices and differences

- **Wind:** stored and passed in m/s. The tool receives Open-Meteo's km/h and converts it before the non-irrigated model (`kmh_to_mps`), so the two agree.
- **Options:** irrigation (non-irrigated by default) and row spacing (30-inch by default, used only when irrigated) are the grower's choices, as in the tool.
- **Weather:** the tool runs on Open-Meteo (about 9 km); v2 on the 2.5 km archive. Not compared on the same place and days.
- **Season and gate:** the spec's season is June 15 to August 7 (the tool's), and the risk is shown as susceptible from R1 to R3 of `soybean-stages` with its 5-day margin (D33). Canopy closure, which the tool's page names as a factor, isn't modelled.
- **Gate:** "inactive" (30-day mean maximum at or below 10 °C) is shown as 0 % (Very low) until the authors say whether they mean 0 % or no value; with partial windows at the start of a series, as the tool's moving means.
- **Not modelled:** the tool's comment lists "No risk: Fungicide app in last 14 days, min temp <32F"; neither it nor v2 applies them.

## Checks

### Against the Crop Risk Tool on the same weather

The Crop Risk Tool is the program this model replaces: a reference, not the truth (D54). Run in CI, on the tool's own recorded weather for one Open-Meteo cell at Eau Claire, Wisconsin (44.815, −91.530), through 2025, with fixtures written by the tool's R code (`packages/agmodels/tests/fixtures/make_crt_fixtures.R`):

- `test_field_crops.py::test_white_mold_irrigated_matches_while_active`: given the tool's daily inputs, v2's irrigated probability equals the tool's within 1e-9 on the 211 days of 2025 when the model is active (30-day mean maximum above 10 °C), in 30- and 15-inch rows (`crt_white_mold_irrigated_30_…` and `crt_white_mold_irrigated_15_eau_claire_2025.csv`), and is 0 on the other days. Until 0.2 every day matched, non-irrigated too. The non-irrigated model differs from the tool by design (−0.56) and is checked by hand below; in June 15 to August 7, 2025 it runs a median 1.46 times the tool's.
- `test_field_crops.py::test_probability_levels_match`: v2's risk levels equal the tool's `risk_from_prob` at both sets of thresholds (1, 20, 35 % and 1, 5, 10 %) at 201 probabilities from 0 to 100 % (the tool's 0 to 1; since 2026-11-26 v2 gives probabilities in percent, and the parity tests compare 100 times the tool's).

### By hand

`test_logistic_by_hand.py`, computed with `math` from the coefficients in the module (not checked against the paper):

- Non-irrigated, at a 30-day mean maximum of 25 °C, maximum wind 3 m/s and maximum RH 90 %: logits 1.87, 0.19 and 0.95, averaging to 71.2 % (with the tool's −0.86 the third logit was −6.55, and the average 47.17 %).
- Irrigated at 30 °C and 90 %: 20.92 % in 30-inch rows and 74.08 % in 15-inch rows.
- The gate (`test_white_mold_is_inactive_unless_the_30_day_mean_maximum_is_above_10_c`): a 30-day mean maximum of 10 °C gives 0 in both settings, 25 °C the model's value; irrigated and non-irrigated use their own risk thresholds.

### The 2025 season at Eau Claire

On the tool's 2025 weather (computed for this report with 0.2; no test holds it), over the spec's season, June 15 to August 7, 2025 (54 days):

<!-- prettier-ignore -->
| Setting | Probability, range (median) | Days Very low / Low / Moderate / High |
| --- | --- | --- |
| Non-irrigated | 18.6–92.8 % (33.9 %); the tool's −0.86 gave 12.7–63.4 % (22.7 %) | 0 / 1 / 30 / 23 (with −0.86: 0 / 17 / 25 / 12) |
| Irrigated, 30-inch rows | 0.0–25.7 % (8.7 %) | 13 / 7 / 11 / 23 |
| Irrigated, 15-inch rows | 0.3–78.9 % (50.8 %) | 3 / 7 / 3 / 41 |

## Limits and open questions

- **Coefficients and thresholds:** checked against the authors' 2025 algorithm (which gives the same bands, 20 and 35 % non-irrigated, 5 and 10 % irrigated), not against Willbur et al. 2018 itself.
- **No observations:** the model predicts apothecia, not disease; neither has been compared with Wisconsin fields in this project. Willbur et al.'s own validation is the evidence until then.
- **The gate applies to both settings**, as the 2025 algorithm has it; the tool scaled only non-irrigated fields.
- **The authors haven't yet confirmed** −0.56 (the 2025 document is unambiguous) or what "inactive" should show.
- **Cheapest independent comparison:** UW Field Crops Pathology's white mold survey records (or the apothecia counts behind Willbur et al. 2018, if published as a table) against the model's probability during R1–R3 on the archive at those fields; NEWA's white mold model, if it runs one, on the same weather.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_field_crops.py packages/agmodels/tests/test_logistic_by_hand.py
Rscript --no-init-file packages/agmodels/tests/fixtures/make_crt_fixtures.R   # the tool's fixtures (needs tmp/R/crop-risk-tool, Phase 3 F)
```
