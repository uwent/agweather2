# Wheat scab (`wheat-scab`): validation

Model version 0.1, written 2026-11-18 (D98). The model: `packages/agmodels/src/agmodels/models/wheat_scab.py`, with its risk levels from `agmodels.probability`; not gated by crop stage yet (wheat's stages wait for papers, PLAN.md Phase 3 D step 7); its page: `wheat_scab.md` beside it (a stub, "To write", rewritten in part I2). Ported from the Crop Risk Tool (`tmp/shiny/crop-risk-tool/src/models.R`, `predict_wheat_scab`, `build_wheat_scab`) in Phase 3 (PLAN.md Phase 3 D step 2).

**In short:** the port reproduces the Crop Risk Tool exactly: given the tool's daily weather for 2025 at Eau Claire, the probability of a Fusarium head blight epidemic matches on all 365 days for each of the four resistance classes. The model is meant to be read at flowering, but neither the tool nor v2 knows when wheat flowers, so it shows a value every day of the year, High on many winter days for susceptible cultivars. Its source paper isn't cited (the tool's page names Shah, Paul, De Wolf and Madden), and it hasn't been compared with scab in fields.

## Sources and what we took from each

<!-- prettier-ignore -->
| Source | What it gives | What we took |
| --- | --- | --- |
| The Crop Risk Tool (`src/models.R`, `predict_wheat_scab`, `build_wheat_scab`; `docs/wheat-scab.md`) | One logit, −3.6432643 + shift + 0.051459669·RH14 (RH14 the 14-day mean daily mean RH), through the logistic; the shift by cultivar resistance: very susceptible 0, susceptible −0.82795556, moderately susceptible −1.4812696, moderately resistant −1.8484537; risk Low from 1 %, Moderate from 24 %, High from 32 %; "relevant during wheat flowering"; the code credits "Erick DeWolf, U. Kentucky", the page "logistic equations developed by Shah, Paul, DeWolf, and Madden" using "relative humidity readings for 14 days prior to flowering (anthesis)" | Everything, unchanged; susceptible as the default class |
| Crop Protection Network, an overview of Fusarium head blight | Background on the disease | Cited only |

## Choices and differences

- **Resistance:** an option, susceptible by default; the model also gives all four classes' probabilities as outputs.
- **Weather:** the tool runs on Open-Meteo (about 9 km); v2 on the 2.5 km archive. Not compared on the same place and days.
- **No season, no gate:** the tool has no risk period for it, and v2's spec has none (PLAN.md Phase 4's review: "30 models have no season"). Gating at flowering (Feekes 10.5.1 for winter wheat; Haun 11.4–11.6 for spring wheat) waits for wheat's stage models (PLAN.md's model review, "Wheat").
- **No cold scaling:** neither the tool nor v2 scales it for cold.

## Checks

### Against the Crop Risk Tool on the same weather

The Crop Risk Tool is the program this model replaces: a reference, not the truth (D54). Run in CI, on the tool's own recorded weather for one Open-Meteo cell at Eau Claire, Wisconsin (44.815, −91.530), through 2025, with fixtures written by the tool's R code (`packages/agmodels/tests/fixtures/make_crt_fixtures.R`):

- `test_field_crops.py::test_wheat_scab_resistance_classes_match`: given the tool's daily inputs, v2's probability equals the tool's (`crt_wheat_scab_eau_claire_2025.csv`) on all 365 days of 2025, within 1e-9, for each of the four resistance classes.
- The risk levels use the same function as the tool's `risk_from_prob`, which `test_field_crops.py::test_probability_levels_match` checks at two other sets of thresholds; this model's (1, 24, 32 %) aren't tested against the tool directly.

### The 2025 season at Eau Claire

From the tool's fixture (computed for this report; no test holds it), for the default class (susceptible): from June 1 to July 15, 2025 (45 days, chosen for this report), 10 days Low, 5 Moderate and 30 High; in January and February (59 days), 15 Low, 27 Moderate and 17 High. Very susceptible cultivars were Moderate or High on every one of those days, moderately resistant ones Low on every one.

## Limits and open questions

- **Read only at flowering:** the probability is for a field flowering on the day shown. Shown every day without a gate, it reports Moderate and High in winter, when there's no crop to infect. Until wheat's stages exist, a season or a note on the map should say so.
- **High in ordinary weather:** by the coefficients, a 14-day mean RH of 70 % gives a susceptible cultivar 29.5 % (Moderate) and 80 % gives 41.2 % (High) (`wheat_scab.probabilities`).
- **Citation (a slip to fix):** the spec cites "Erick De Wolf, as implemented in the Crop Risk Tool", while the tool's page names Shah, Paul, De Wolf and Madden, which points to a published paper by those authors; find it and cite it with its DOI (PLAN.md Phase 4's review, "Citations"). The tool's code comment gives De Wolf's affiliation as the University of Kentucky; check it.
- **No observations:** not compared with Fusarium head blight in Wisconsin wheat.
- **Cheapest independent comparison:** the U.S. Wheat and Barley Scab Initiative's Fusarium head blight risk tool, whose models come from the same group of authors, on the same days and places (a system comparison, not observations); then UW's wheat disease survey records, once flowering dates come from wheat's stage models.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_field_crops.py
Rscript --no-init-file packages/agmodels/tests/fixtures/make_crt_fixtures.R   # the tool's fixtures (needs tmp/shiny/crop-risk-tool, PLAN.md Phase 3 F)
```
