# Frogeye leaf spot (`frogeye-leaf-spot`): validation

Model version 0.1, written 2026-11-18 (D98). The model: `packages/agmodels/src/agmodels/models/frogeye.py`, with its risk levels from `agmodels.probability`; gated by `soybean-stages` (R1 to R5, D33); its page: `frogeye.md` beside it (a two-sentence stub, rewritten in part I2). Ported from the Crop Risk Tool (`tmp/R/crop-risk-tool/src/models.R`, `predict_fls`, `build_frogeye_leaf_spot`) in Phase 3 (Phase 3 D step 2).

**In short:** the port reproduces the Crop Risk Tool exactly: given the tool's daily weather for 2025 at Eau Claire, the probability matches on all 365 days. The fit is credited to Damon Smith (UW–Madison) and Wade Webster (NDSU) with no published paper, so there is no source to check its numbers against, and it hasn't been compared with frogeye leaf spot in fields.

## Sources and what we took from each

<!-- prettier-ignore -->
| Source | What it gives | What we took |
| --- | --- | --- |
| The Crop Risk Tool (`src/models.R`, `predict_fls`, `build_frogeye_leaf_spot`; `docs/frogeye.md`) | One logit, −5.92485 + 0.12208·Tmax30 + 0.17326·H80 (Tmax30 the 30-day mean daily maximum temperature, °C; H80 the 30-day mean daily hours with RH ≥ 80 %), through the logistic; risk Low from 1 %, Moderate from 40 %, High from 50 %; susceptible R1–R5; credit Damon Smith (UW–Madison) and Wade Webster (NDSU); no paper cited | Everything, unchanged |
| Crop Protection Network, frogeye leaf spot of soybean | Background on the disease | Cited only |

## Choices and differences

- **Humid hours:** counted at 80 % on the archive as at a station; D50's correction applies only to the 90 % counts.
- **Weather:** the tool runs on Open-Meteo (about 9 km); v2 on the 2.5 km archive. Not compared on the same place and days.
- **No cold scaling:** neither the tool nor v2 scales this model for cold; the probability rises with warmth and humid hours, so it's low in winter anyway.
- **Season and gate:** the spec's season is June 15 to September 7 (the tool's), and the risk is shown as susceptible from R1 to R5 of `soybean-stages` with its 5-day margin (D33).
- **Not modelled:** the tool's comment lists "No risk: Fungicide in last 14 days, temperature <32F"; neither it nor v2 applies them.

## Checks

### Against the Crop Risk Tool on the same weather

The Crop Risk Tool is the program this model replaces: a reference, not the truth (D54). Run in CI, on the tool's own recorded weather for one Open-Meteo cell at Eau Claire, Wisconsin (44.815, −91.530), through 2025, with fixtures written by the tool's R code (`packages/agmodels/tests/fixtures/make_crt_fixtures.R`):

- `test_field_crops.py::test_probability_matches`: given the tool's daily inputs, v2's probability equals the tool's (`crt_frogeye_eau_claire_2025.csv`) on all 365 days of 2025, within 1e-9.
- The risk levels use the same function as the tool's `risk_from_prob`, which `test_field_crops.py::test_probability_levels_match` checks at two other sets of thresholds; this model's (1, 40, 50 %) aren't tested against the tool directly.

### By hand

`test_logistic_by_hand.py::test_gray_leaf_spot_and_frogeye_by_hand`: at a 30-day mean maximum of 27 °C and 12 humid hours a day, the logit worked out with `math` from the coefficients in the module gives 36.60 %, and the model the same.

### The 2025 season at Eau Claire

From the tool's fixture (computed for this report; no test holds it): over the spec's season, June 15 to September 7, 2025 (85 days), the probability ran 12.2 % to 40.5 % (median 33.8 %): 80 days Low and 5 Moderate, none High. Its highest of the year, 40.5 %, came on July 25.

## Limits and open questions

- **The authors' algorithm** ("2024 Soy Frogeye Leaf Spot Model Algorithm", ver. 1.0, May 29, 2024, in `tmp/R/crop-risk-tool-models/`; audited in `tmp/crt-model-audit.md`: the port matches it) gives this equation, hours at RH 80 % or above, a 50 % action threshold (adjustable 40–60 %) and R1–R5.
- **No published source:** the fit is unpublished; its region, years, weather and response (spores trapped, or disease) are unknown. Ask its authors for the fit and its data (Phase 4's review, "Citations").
- **No observations:** not compared with frogeye leaf spot in Wisconsin fields.
- **Cheapest independent comparison:** UW Field Crops Pathology's survey records of frogeye leaf spot against the model's probability during R1–R5 on the archive at those fields.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_field_crops.py packages/agmodels/tests/test_logistic_by_hand.py
Rscript --no-init-file packages/agmodels/tests/fixtures/make_crt_fixtures.R   # the tool's fixtures (needs tmp/R/crop-risk-tool, Phase 3 F)
```
