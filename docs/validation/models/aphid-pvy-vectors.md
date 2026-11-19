# Aphid PVY vectors (`aphid-pvy-vectors`): validation

Model version 0.2, written 2026-11-18 (D98). The model: `packages/agmodels/src/agmodels/insects/aphid_pvy_vectors.py`, a fitted stage (D36, `agmodels.phenology.FittedStage`) reading `aphid_pvy_vectors_fit.csv` beside it; its page: `aphid_pvy_vectors.md`. Version 0.1 (2026-10-28 to 2026-11-18) was VDIFN's sine-ramped window (1,838, 2,515, 3,228); its report is in git history.

**In short:** the model reads the risk of PVY spread by winged aphids off a curve refitted on 2026-11-18 to Wisconsin's suction trap catches, 2016–2023 (Bradford and Groves, unpublished). Risk rises through midsummer to a broad peak near 3,580 degree days (39.2/86 °F from January 1), above 90 % of the peak from about 2,980 to 3,990. The model reproduces the fit's points; the fit describes the trap data it came from and hasn't been tested on other years. The refit replaced a 2019/2024 method whose first stage never converged and whose "peak at 2,515" was only the curve's crossing of its sample mean.

## Sources and what we took from each

<!-- prettier-ignore -->
| Source | What it gives | What we took |
| --- | --- | --- |
| Bradford and Groves, unpublished analysis (Vegetable Entomology Lab, UW–Madison), refitted 2026-11-18: `tmp/R/pvy_model/pvy-model-v2.R`, figure `pvy-model-v2.png`, predictions `pvy_predictions_v2.csv` | Each trap-week's risk index, the sum over PVY vector species of log(1 + count) × asin(√efficiency) (transmission efficiencies from the literature, `data/pvy-vectors.csv`); a Tweedie GAM (log link, REML) on degree days 39.2/86 °F at the midpoint of each collection week, with each year's own curve, trap and trap-season effects; 955 trap-dates at 8 Wisconsin traps, 2016–2023, on AgWeather v2's weather. Deviance explained 47 % | The typical year's curve (random effects at zero), every 10 degree days from 290 to 5,490 |
| Suction trap records, 2016–2023 (EDDMapS, submitted by Doris Lagos-Kutz, University of Illinois Urbana-Champaign) | Weekly catches by species at Wisconsin's traps | Through the fit |
| VDIFN's `pvy-vectors` (`../ag-vdifn/db/seeds.rb`) and UW Vegetable Entomology's Potato Virus Y Management page | A window from 1,838 to 3,228 peaking at 2,515 (base 39.2 °F); the page's figure, from the 2024 fit, labels 1,452, 1,838, 2,515 (its zero line) and 3,266 | Compared only (below) |

## Choices and differences

- **The refit (Ben, 2026-11-18):** the 2019/2024 method fitted a Poisson mixed model to the risk index, which isn't a count, so it never converged (its random-effect SDs stayed at 1), then smoothed its per-sample intercepts; the zero of that curve is the samples' average, not an event. Its weather (the old AgWeather API) had gaps counted as zero degree days, and trap-dates with aphids but no vector species were left out. The refit is one model; keeps those dates as zero risk; places each catch at the degree-day midpoint of its collection week; gives each trap location its own weather (the Antigo trap moved in 2019); and runs on v2's weather for every year. The response (the index) is unchanged; `pvy-model-v2.R`'s header lists each change and its reason.
- **Reading the curve:** linear between the predictions; 0 before 290 degree days (no trap data; the curve is 13 % of its peak there, so risk steps up when the data begin); held at its last value (28 % of the peak) after 5,490 until fall freezes end the season.
- **Risk:** the index over its peak (1.48), Low from 0.05, Moderate from 0.25, High from 0.5, Very high from 0.75 (the D36 defaults).
- **Degree days:** single sine, 39.2 °F (4 °C), cutoff 86 °F, from January 1; the 2024 fit used 39 °F.

## Checks

### Against the fit

`packages/agmodels/tests/test_aphid_pvy_vectors.py`, run in CI, against `pvy_critical_points_v2.csv`, within 10 degree days (the model's points read on its 1-degree-day table):

| Point | The fit | The model |
| --- | --- | --- |
| Peak | 3,582 | 3,580 |
| 50 % of peak, rising | 2,236 | 2,236 |
| 90 % of peak, rising | 2,980 | 2,980 |
| 90 % of peak, falling | 3,994 | 3,993 |
| 50 % of peak, falling | 4,985 | 4,984 |

The fit's own checks (`tmp/R/pvy_model/out/v2/`): converged (gradient 1e-4, Hessian positive definite); the degree-day smooth uses 6.5 of 19 degrees of freedom (k-index 0.95, p = 0.48); observed over fitted 0.92–1.19 in 500-degree-day bins. Refitting with each year left out moved the peak between 3,370 and 3,788, 50 % rising between 1,887 and 2,385, and 90 % rising between 2,870 and 3,241. The years differ a great deal: each year's own curve peaks anywhere from 1,720 (2023) to 4,757 degree days (2021).

Sensitivity of the peak to the analysis's choices: the catch at its collection date's total rather than the week's midpoint, 3,711; gap weeks as zero, 3,612; efficiency itself as the weight rather than asin(√efficiency), 3,488; year intercepts only rather than each year's curve, 3,177.

### Against VDIFN

VDIFN, the system this model replaces (a reference, not the truth, D54), rated risk from 1,838 to 3,228 degree days, peaking at 2,515. The 2024 fit's figure shows 2,515 is where the curve crossed its sample mean on the way up and its own peak was 3,266, so VDIFN's risk fell while the fitted risk was still rising and ended before it peaked. On the refitted curve, risk at 2,515 is 63 % of the peak (0.633 in the test) and still rising.

## Limits and open questions

- **In sample, and years vary:** the curve is the typical year's; single years peak from about 1,720 to 4,760 degree days. Trap catches in the current season are a better guide than the curve.
- **The trap data hold presence records only:** weeks with no aphids at all aren't in the EDDMapS export, so the season's edges carry no zeros, and the curve's low end may be too high.
- **Thin ends:** 18 catches below 500 degree days and 16 above 5,000.
- **The index's weighting** (log counts times asin(√efficiency)) is a choice: weighting by efficiency itself, or a vector pressure index of counts times efficiency, moves the peak to 3,488 or 3,226 and changes the shape. A question for the analysis, not settled here.
- **Transmission efficiencies** are single values from wide literature ranges (green peach aphid 0.08–0.83).
- **Cheapest independent comparison:** the suction traps' 2024–2026 seasons (the network's later catches), against the curve.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_aphid_pvy_vectors.py
cd tmp/R/pvy_model && Rscript pvy-model-v2.R   # the fit (about 2.5 minutes); needs data/weather-v2.csv
```
