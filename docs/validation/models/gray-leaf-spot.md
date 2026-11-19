# Gray leaf spot (`gray-leaf-spot`): validation

Model version 0.1, written 2026-11-18 (D98). The model: `packages/agmodels/src/agmodels/models/gray_leaf_spot.py`, with its risk levels from `agmodels.probability`; gated by `corn-stages` (V10 to R3, D33); its page: `gray_leaf_spot.md` beside it (a two-sentence stub, rewritten in part I2). Ported from the Crop Risk Tool (`tmp/R/crop-risk-tool/src/models.R`, `predict_gls`, `build_gray_leaf_spot`) in Phase 3 (PLAN.md Phase 3 D step 2).

**In short:** the port reproduces the Crop Risk Tool exactly: given the tool's daily weather for 2025 at Eau Claire, the probability matches on all 365 days. The fit is credited to Damon Smith (UW–Madison) and Wade Webster (NDSU) with no published paper, so there is no source to check its numbers against. In a Wisconsin summer it barely moves: at Eau Claire it was High on every day of the 2025 season, between 99.0 and 99.9 %.

## Sources and what we took from each

<!-- prettier-ignore -->
| Source | What it gives | What we took |
| --- | --- | --- |
| The Crop Risk Tool (`src/models.R`, `predict_gls`, `build_gray_leaf_spot`; `docs/gray-leaf-spot.md`) | One logit, −2.9467 − 0.03729·Tmin21 + 0.6534·Td30 (Tmin21 the 21-day mean daily minimum temperature, °C; Td30 the 30-day mean daily minimum dew point, °C), through the logistic; risk Low from 1 %, Moderate from 40 %, High from 60 %; susceptible V10–R3; credit Damon Smith (UW–Madison) and Wade Webster (NDSU); no paper cited | Everything, unchanged |
| Crop Protection Network, gray leaf spot of corn | Background on the disease | Cited only |

## Choices and differences

- **Weather:** the tool runs on Open-Meteo (about 9 km); v2 on the 2.5 km archive. Not compared on the same place and days.
- **No cold scaling:** neither the tool nor v2 scales this model for cold, unlike tar spot and white mold; the probability falls with the dew point, so it's low in winter anyway.
- **Season and gate:** the spec's season is July 1 to August 15 (the tool's), and the risk is shown as susceptible from V10 to R3 of `corn-stages` with its 3-day margin (D33).
- **Not modelled:** the tool's comment lists "No risk: Fungicide app in last 14 days, min temp <32F"; neither it nor v2 applies them.

## Checks

### Against the Crop Risk Tool on the same weather

The Crop Risk Tool is the program this model replaces: a reference, not the truth (D54). Run in CI, on the tool's own recorded weather for one Open-Meteo cell at Eau Claire, Wisconsin (44.815, −91.530), through 2025, with fixtures written by the tool's R code (`packages/agmodels/tests/fixtures/make_crt_fixtures.R`):

- `test_field_crops.py::test_probability_matches`: given the tool's daily inputs, v2's probability equals the tool's (`crt_gray_leaf_spot_eau_claire_2025.csv`) on all 365 days of 2025, within 1e-9.
- The risk levels use the same function as the tool's `risk_from_prob`, which `test_field_crops.py::test_probability_levels_match` checks at two other sets of thresholds; this model's (1, 40, 60 %) aren't tested against the tool directly.

### By hand

`test_logistic_by_hand.py::test_gray_leaf_spot_and_frogeye_by_hand`: the probability at a 21-day mean minimum of 14 °C and a 30-day mean minimum dew point of 12 °C equals the logit worked out with `math` from the coefficients in the module.

### The 2025 season at Eau Claire

From the tool's fixture (computed for this report; no test holds it): over the spec's season, July 1 to August 15, 2025 (46 days), the probability ran from 99.0 to 99.9 %, High on all 46 days.

## Limits and open questions

- **The model saturates in summer (a doubt to resolve):** by the coefficients, at a 21-day mean minimum of 15 °C the probability passes 60 % (High) once the 30-day mean minimum dew point is above about 6 °C (43 °F), and is 99.3 % at 13 °C (`gray_leaf_spot.probability`); at Eau Claire from July 1 to August 15, 2025, it ran from 12.5 to 16.0 °C (the tool's fixture, computed for this report). A model that shows High every summer day can't tell one season or place from another. Either the fit was made on other conditions or scales, or a coefficient or unit was carried over wrongly: ask its authors for the fit and its data (PLAN.md Phase 4's review, "Citations").
- **The authors' algorithm** ("2024 Corn Gray Leaf Spot Model Algorithm", ver. 1.0, March 10, 2024, in `tmp/R/crop-risk-tool-models/`; audited in `tmp/crt-model-audit.md`) gives this equation (no units), a 60 % action threshold (adjustable 50–70 %), V10–R3, and "two models" to average though it gives only one. As written it saturates: above 99 % on every in-season day (its 50 % point is a 30-day mean minimum dew point of 5.4 °C); the authors have been asked.
- **No published source:** the fit is unpublished; its region, years, weather and response (spores trapped, or disease) are unknown. Its temperature coefficient is negative (warmer nights lower the probability slightly), against the tool's page, which says warm weather favours the disease.
- **No observations:** not compared with gray leaf spot in Wisconsin fields.
- **Cheapest independent comparison:** the arithmetic first: the archive's July–August values over Wisconsin's cells, 2016–2025, to see whether the probability ever leaves High (no observations needed); then UW Field Crops Pathology's survey records of gray leaf spot.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_field_crops.py packages/agmodels/tests/test_logistic_by_hand.py
Rscript --no-init-file packages/agmodels/tests/fixtures/make_crt_fixtures.R   # the tool's fixtures (needs tmp/R/crop-risk-tool, PLAN.md Phase 3 F)
```
