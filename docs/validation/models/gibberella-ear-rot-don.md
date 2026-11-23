# Gibberella ear rot and DON (`gibberella-ear-rot-don`): validation

Model version 0.2, written 2026-11-18 (D98), updated 2026-11-19 for 0.2. The model: `packages/agmodels/src/agmodels/models/don.py`, with its risk levels from `agmodels.probability`; gated by `corn-stages` (R1, silking, D33); its page: `don.md` beside it (a two-sentence stub, rewritten in part I2). Ported from the Crop Risk Tool (`tmp/R/crop-risk-tool/src/models.R`, `predict_don`, `build_don`) in Phase 3 (Phase 3 D step 2).

**In short:** the port reproduces the Crop Risk Tool but for one correction from the authors' algorithm (0.2: humid days at mean RH ≥ 80 %, where the tool counts > 80 %): given the tool's daily weather for 2025 at Eau Claire, the probability of deoxynivalenol (DON) above 1 ppm matches on the 344 days whose 14-day window holds no day at exactly 80 %, and differs by at most 4e-8 on the rest (the first 7 days of the year have no value in either). The fit is credited to Pierce Paul and Cristiano Nesi (Ohio State) with no published paper, so there is no source to check its numbers against, and it hasn't been compared with DON in harvested grain.

## Sources and what we took from each

<!-- prettier-ignore -->
| Source | What it gives | What we took |
| --- | --- | --- |
| The Crop Risk Tool (`src/models.R`, `predict_don`, `build_don`; `docs/don.md`) | One logit, −59.6309 + 1.3057·Tmax + 0.9090·Tmin − 1.6158·D25 − 0.9350·Dr + 0.2255·RH − 0.9249·D80, through the logistic. Tmax, Tmin, D25 and Dr come from the 14 days ending 7 days before the day (the mean daily maximum and minimum temperature, °C; days with a mean of 25 °C or more; days with rain); RH and D80 from the last 14 days (the mean daily mean RH; days with a mean RH above 80 %). The probability of DON above 1 ppm at harvest; risk Low from 1 %, Moderate from 20 %, High from 40 %; susceptible during silking; credit Pierce Paul and Cristiano Nesi, Ohio State; no paper cited | Everything, but missing rain (below) |
| Crop Protection Network, Gibberella ear rot of corn | Background on the disease | Cited only |

## Choices and differences

- **Missing rain:** a day with missing precipitation counts as a day without rain, in v2 as in the tool (`replace_na(precipitation_daily = 0)`; D45: rain is never estimated). 0.1's docstring, changelog and this report said v2 didn't count it either way; the audit (`tmp/crt-model-audit.md`) found the code counted it as dry, and 0.2 says so and adds `precipitation_days_missing`, the days without data in the rain window (21 to 7 days back), so the interface can say how many there were. The runner bridges gaps of up to 7 days in the other inputs first (D45).
- **Humid days:** mean RH ≥ 80 % (the authors' algorithm, W0); the tool counts > 80 %. It matters only on days at exactly 80 %.
- **The first week:** the window 21 to 7 days back doesn't exist for the first 7 days of a series; v2 gives no value there, where the tool drops the rows.
- **Weather:** the tool runs on Open-Meteo (about 9 km); v2 on the 2.5 km archive. Not compared on the same place and days.
- **Season and gate:** the spec's season is July 1 to August 7 (the tool's `risk_period`), and the risk is shown as susceptible only at R1 (silking) of `corn-stages`, with its 3-day margin (D33; Ben: silking only, since the model's windows end on silking day). Read on any other day, the value is what it would be if silking were that day.

## Checks

### Against the Crop Risk Tool on the same weather

The Crop Risk Tool is the program this model replaces: a reference, not the truth (D54). Run in CI, on the tool's own recorded weather for one Open-Meteo cell at Eau Claire, Wisconsin (44.815, −91.530), through 2025, with fixtures written by the tool's R code (`packages/agmodels/tests/fixtures/make_crt_fixtures.R`):

- `test_field_crops.py::test_don_matches_after_its_lag`: given the tool's daily inputs, v2's probability equals the tool's (`crt_don_eau_claire_2025.csv`) within 1e-9 on the 344 days from January 8 to December 31, 2025 whose 14-day window holds no day at exactly 80 % mean RH (on the other 14 it differs by at most 4e-8), is missing on the first 7, where the tool has no rows, and the count of days without rain data is 0 throughout (the tool's year has every day). Until 0.2 all 358 days matched.
- The risk levels use the same function as the tool's `risk_from_prob`, which `test_field_crops.py::test_probability_levels_match` checks at two other sets of thresholds; this model's (1, 20, 40 %) aren't tested against the tool directly.

### Crop stage window

`test_crops.py::test_tar_spot_and_don_windows_over_a_season`: corn planted April 22 in the recorded 2000 season at Lincoln (`fixtures/phenology_weather.csv`) is susceptible to this model on between 3 and 10 days (silking), inside tar spot's window.

### The 2025 season at Eau Claire

From the tool's fixture (computed for this report; no test holds it): over the spec's season, July 1 to August 7, 2025 (38 days), the probability stayed at or below 2.3 %: 35 days Very low and 3 Low. Its highest of the year, 16.8 %, came on October 12, long after silking.

## Limits and open questions

- **No published source:** the fit is unpublished as far as the tool's documents show; its region, years, hybrids and weather are unknown. Some of its signs run against the tool's own page ("DON accumulation is favored when conditions after silking remain moderately warm and wet"): more days with rain and more days with a mean RH of 80 % or more each lower the probability, though the mean RH raises it. In a model with several related terms that can be right, but ask the authors for the fit (Phase 4's review, "Citations").
- **No observations:** not compared with DON in Wisconsin corn.
- **Silking is estimated:** the gate uses `corn-stages`' silking date, from a planting date (typical or the grower's); a day or two off moves the windows.
- **Cheapest independent comparison:** DON test results from Wisconsin corn with planting or silking dates (UW Field Crops Pathology's ear rot surveys, or grain buyers' records if they can be had), against the model's probability at silking on the archive.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_field_crops.py packages/agmodels/tests/test_crops.py
Rscript --no-init-file packages/agmodels/tests/fixtures/make_crt_fixtures.R   # the tool's fixtures (needs tmp/R/crop-risk-tool, Phase 3 F)
```
