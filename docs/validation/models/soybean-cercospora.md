# Cercospora leaf blight of soybean (`soybean-cercospora`): validation

Model version 0.1 (beta), written 2026-11-18 (D98). The model: `packages/agmodels/src/agmodels/models/soybean_cercospora.py`, with its humid hours from `agmodels.features` and its risk levels from `agmodels.probability`; gated by `soybean-stages` (R3 to R6, provisional, D33); its page: `soybean_cercospora.md` beside it (a one-sentence stub, rewritten in part I2). Ported from the Crop Risk Tool (`tmp/R/crop-risk-tool/src/models.R`, `predict_soybean_cercospora`, `build_soybean_cercospora`) in Phase 3 (Phase 3 D step 2).

**In short:** the port reproduces the Crop Risk Tool exactly: given the tool's daily weather for 2025 at Eau Claire, each of the three species' probabilities matches on all 365 days. The fits are Wade Webster's (NDSU), unpublished; their weather, the unit of wind in one of them and the crop stages they apply to are open questions for him. Nothing beyond the port has been checked.

## Sources and what we took from each

<!-- prettier-ignore -->
| Source | What it gives | What we took |
| --- | --- | --- |
| The Crop Risk Tool (`src/models.R`, `predict_soybean_cercospora`, `build_soybean_cercospora`; `docs/cercospora-soybean.md`) | Three logits, each through the logistic: *C. flagellaris* −6.30565 + 0.19559·Tmin5 + 0.16999·DPD5 (5-day means of the daily minimum temperature and mean dew point depression, °C); *C.* cf. *sigesbeckiae* 3.25803 − 0.35362·W14 + 0.05473·H90₁₀ (the 14-day mean daily maximum wind as the tool passes it, km/h; the 10-day mean hours with RH ≥ 90 %); *C. kikuchii* −7.67159 + 0.34914·H90₁₄ + 0.25508·DPDmax5 (the 14-day mean hours with RH ≥ 90 %; the 5-day mean daily maximum dew point depression). Risk: *C. flagellaris* Low from 1 %, Moderate from 10 %, High from 15 %; the other two from 1, 5 and 10 %. Credit Richard (Wade) Webster, NDSU; no paper cited; marked beta | Everything, unchanged |
| Crop Protection Network, Cercospora leaf blight of soybean, and its overview publication | Background; symptoms usually from the beginning of seed set | The provisional risk period, R3–R6 (Ben, 2026-10-28) |

## Choices and differences

- **Wind:** stored in m/s and multiplied by 3.6 to give the *C.* cf. *sigesbeckiae* model the km/h the tool passes it (Open-Meteo's default), unlike white mold, which the tool gives m/s. Kept until the fit's unit is confirmed (Phase 3 D step 2, open question for Webster).
- **Gridded humidity:** on the archive an hour counts as RH ≥ 90 % at 88 % (D50, `features.STATION_RH_90_AS_GRIDDED`); a station's own hours count at 90 %. The weather the fits used is unknown (perhaps Open-Meteo through the tool; Ben, 2026-10-31), so the correction applies anyway. Its effect on this model hasn't been measured.
- **The model's risk** is the highest of the three species' levels (the tool shows the three apart). A species whose inputs are missing for a whole window is left out (`fmax`), so the level is at least what the others say; it's missing only if all three are (Phase 4's review, "checked and left as they are").
- **Dew point depression** is stored as a temperature difference (`delta_degC`), so a request in °F converts it by 1.8 without adding 32.
- **Weather:** the tool runs on Open-Meteo (about 9 km); v2 on the 2.5 km archive. Not compared on the same place and days.
- **Season and gate:** no calendar season; susceptible from R3 to R6 of `soybean-stages` with its 5-day margin, provisionally: the fit gave no risk period (D33; Phase 3's stage table).

## Checks

### Against the Crop Risk Tool on the same weather

The Crop Risk Tool is the program this model replaces: a reference, not the truth (D54). Run in CI, on the tool's own recorded weather for one Open-Meteo cell at Eau Claire, Wisconsin (44.815, −91.530), through 2025, with fixtures written by the tool's R code (`packages/agmodels/tests/fixtures/make_crt_fixtures.R`):

- `test_field_crops.py::test_soybean_cercospora_species_match`: given the tool's daily inputs (its wind converted from km/h to m/s, which the model converts back), v2's probability for each of the three species equals the tool's (`crt_soybean_cercospora_eau_claire_2025.csv`) on all 365 days of 2025, within 1e-9.
- `test_field_crops.py::test_probability_levels_match`: v2's risk levels equal the tool's `risk_from_prob` at 1, 5 and 10 % (the thresholds of two of the species) at 201 probabilities from 0 to 1; *C. flagellaris*'s (1, 10, 15 %) use the same function but aren't tested against the tool directly.

### The 2025 season at Eau Claire

From the tool's fixture (computed for this report; no test holds it), the year's highest probabilities: *C. flagellaris* 29.0 % (June 24), *C.* cf. *sigesbeckiae* 26.0 % (September 29), *C. kikuchii* 16.5 % (September 30).

## Limits and open questions

- **Wind's unit (km/h, by the fit's arithmetic):** the authors' 2026 algorithm labels the wind m/s, but read as m/s *C.* cf. *sigesbeckiae* would be 63–89 % on every realistic day (43 % even at 10 m/s with no humid hours), above its 10 % High on all of them, while the algorithm's own appendix reports 78.8 % accuracy at that threshold; read as km/h (at 6 humid hours, 5 m/s is 18 km/h: 5.9 % against 86 %) the predictions straddle the bands as a fitted model's should. The m/s label is inconsistent with the fit unless its data were unusual (`tmp/crt-model-audit.md`); km/h is kept until Webster confirms.
- **No published source, no risk period:** the fits are unpublished; their region, years, weather and response (spores trapped, or disease) are unknown, and so is the stage window (R3–R6 is our provisional choice). Ask Webster (the models plan's record, "Open questions for Ben or collaborators").
- **No observations:** not compared with Cercospora leaf blight in fields.
- **Cheapest independent comparison:** the data behind Webster's fits, if he can share them, run on Open-Meteo's weather at their sites; asking would also settle the wind unit and the risk period.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_field_crops.py
Rscript --no-init-file packages/agmodels/tests/fixtures/make_crt_fixtures.R   # the tool's fixtures (needs tmp/R/crop-risk-tool, Phase 3 F)
```
