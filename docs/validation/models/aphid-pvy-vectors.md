# Aphid PVY vectors (`aphid-pvy-vectors`): validation

Model version 0.3, written 2026-11-21 (D98, D101). The model: `packages/agmodels/src/agmodels/insects/aphid_pvy_vectors.py`, a fitted stage (D36, `agmodels.phenology.FittedStage`) reading `aphid_pvy_vectors_fit.csv` (degree days) and `aphid_pvy_vectors_fit_calendar.csv` (day of year) beside it; its page: `aphid_pvy_vectors.md`. Version 0.1 (2026-10-28 to 2026-11-18) was VDIFN's sine-ramped window (1,838, 2,515, 3,228); 0.2 (2026-11-18 to 2026-11-21) the same refit with each species weighted by asin(√efficiency). Their reports are in git history.

**In short:** the model reads the risk of PVY spread by winged aphids off a curve fitted to Wisconsin's suction trap catches, 2016–2023 (Bradford and Groves, unpublished; refitted 2026-11-18 and, with each species weighted by its transmission efficiency, 2026-11-21). Risk rises through midsummer to a broad peak near 3,490 degree days (39.2/86 °F from January 1), above 90 % of the peak from about 2,950 to 3,930; on the calendar, the same model peaks on August 22, above 90 % from August 16 to 30. The calendar describes the catches better than degree days (deviance explained 54 % against 44 %), and on years left out degree days timed only the start of the season's catch better (by about 2 days). The model reads the curve as typical pressure through the season plus an onset signal, not a forecast of a season's peak. The refits replaced a 2019/2024 method whose first stage never converged and whose "peak at 2,515" was only the curve's crossing of its sample mean.

## Sources and what we took from each

<!-- prettier-ignore -->
| Source | What it gives | What we took |
| --- | --- | --- |
| Bradford and Groves, unpublished analysis (Vegetable Entomology Lab, UW–Madison), refitted 2026-11-21: `tmp/R/pvy-model/pvy-model-v3.R` (v2's changes and reasons in its header), figure `pvy-model-v3.png`, predictions `pvy_predictions_v3.csv` and `pvy_predictions_v3_calendar.csv`, log `out/v3-run.log` | Each trap-week's risk index, the sum over PVY vector species of log(1 + count) × efficiency (transmission efficiencies from the literature, `data/pvy-vectors.csv`); a Tweedie GAM (log link, REML) on degree days 39.2/86 °F at the midpoint of each collection week, with each year's own curve, trap and trap-season effects; 955 trap-dates at 8 Wisconsin traps, 2016–2023, on AgWeather v2's weather. Deviance explained 44 %. The same model on the day of year at each week's midpoint: deviance explained 54 %, AIC 673 against 840 | The typical year's curves (random effects at zero): every 10 degree days from 290 to 5,490, and every day from 123 to 293 (May 3 to October 20) |
| Suction trap records, 2016–2023 (EDDMapS, submitted by Doris Lagos-Kutz, University of Illinois Urbana-Champaign) | Weekly catches by species at Wisconsin's traps | Through the fit |
| VDIFN's `pvy-vectors` (`../ag-vdifn/db/seeds.rb`) and UW Vegetable Entomology's Potato Virus Y Management page | A window from 1,838 to 3,228 peaking at 2,515 (base 39.2 °F); the page's figure, from the 2024 fit, labels 1,452, 1,838, 2,515 (its zero line) and 3,266 | Compared only (below) |

## Choices and differences

- **The refit (Ben, 2026-11-18):** the 2019/2024 method fitted a Poisson mixed model to the risk index, which isn't a count, so it never converged (its random-effect SDs stayed at 1), then smoothed its per-sample intercepts; the zero of that curve is the samples' average, not an event. Its weather (the old AgWeather API) had gaps counted as zero degree days, and trap-dates with aphids but no vector species were left out. The refit is one model; keeps those dates as zero risk; places each catch at the degree-day midpoint of its collection week; gives each trap location its own weather (the Antigo trap moved in 2019); and runs on v2's weather for every year. The response (the index) is unchanged; `pvy-model-v2.R`'s header lists each change and its reason.
- **The weight (Ben, 2026-11-21):** each species' log catch times its transmission efficiency. v2 kept the 2019 analysis's asin(√efficiency), a variance-stabilizing transform for analyzing proportions, which as a weight compresses the species' differences (green peach aphid against corn leaf aphid: 23 times in efficiency, 5.2 times after the transform), so abundant poor vectors counted for more than their transmission warrants. The log of counts stays: it keeps one mass flight of a poor vector (a soybean aphid flight can reach thousands) from outweighing several vector species flying at once. The peak moved from 3,582 to 3,488 degree days; counts times efficiency, without the log, would put it at 3,226.
- **The calendar curve (D101):** the same model on the day of year. It describes the catches better than degree days do: these aphids are mostly migrants and host-alternating species, whose flights follow the season's length and weather far to the south more than local warmth.
- **Reading the curves:** linear between the predictions; 0 before 290 degree days or May 3 (no trap data; the curves are 9 % and 4 % of their peaks there, so risk steps up when the data begin); held at the last value (23 % and 20 % of the peak) after 5,490 or October 20 until fall freezes end the season.
- **Risk:** the index over its peak (0.596 on degree days, 0.714 on the calendar), Low from 0.05, Moderate from 0.25, High from 0.5, Very high from 0.75 (the D36 defaults).
- **Training area (D101):** Wisconsin, where the traps are (from Grant and Walworth counties in the south to Oneida County in the north); elsewhere the model runs with a warning.
- **Degree days:** single sine, 39.2 °F (4 °C), cutoff 86 °F, from January 1; the 2024 fit used 39 °F.

## Checks

### Against the fit

`packages/agmodels/tests/test_aphid_pvy_vectors.py`, run in CI, against `pvy_critical_points_v3.csv` within 10 degree days (the model's points read on its 1-degree-day table) and `pvy_critical_points_v3_calendar.csv` within a day:

| Point | The fit | The model |
| --- | --- | --- |
| Point | The fit (degree days) | The calendar fit |
| --- | --- | --- |
| Peak | 3,488 | Day 234 (August 22) |
| 50 % of peak, rising | 2,232 | Day 215 (August 3) |
| 90 % of peak, rising | 2,947 | Day 228 (August 16) |
| 90 % of peak, falling | 3,933 | Day 242 (August 30) |
| 50 % of peak, falling | 4,823 | Day 276 (October 3) |

The calendar curve also has an early-summer shoulder: small peaks near June 4 and July 3, about 27 % of the August peak, which the degree-day curve smooths into a slow rise (40 % of its peak by 1,810 degree days).

The fit's own checks (`tmp/R/pvy-model/out/v3-run.log`): converged (gradient 4e-8, Hessian positive definite); the degree-day smooth uses 5.5 of 19 degrees of freedom (k-index 0.92, p = 0.45). Refitting with each year left out moved the peak between 3,297 and 3,721 degree days (days 232 to 237 on the calendar), 50 % rising between 2,006 and 2,376, and 90 % rising between 2,862 and 3,095. The years differ a great deal: each year's own curve peaks anywhere from 1,743 (2023) to 4,737 degree days (2021).

Sensitivity of the peak to the analysis's choices: the catch at its collection date's total rather than the week's midpoint, 3,627; gap weeks as zero, 3,531; asin(√efficiency) as the weight (0.2), 3,582; counts times efficiency without the log, 3,226; year intercepts only rather than each year's curve, 3,155.

### Against VDIFN

VDIFN, the system this model replaces (a reference, not the truth, D54), rated risk from 1,838 to 3,228 degree days, peaking at 2,515. The 2024 fit's figure shows 2,515 is where the curve crossed its sample mean on the way up and its own peak was 3,266, so VDIFN's risk fell while the fitted risk was still rising and ended before it peaked. On the refitted curve, risk at 2,515 is about 64 % of the peak (0.64 in the test) and still rising.

### Base temperature and timing on years left out (2026-11-19)

`tmp/R/pvy-model/pvy-base-profile.R` (findings in `base-profile.md` there) refitted the v2 model (weights asin(√efficiency); not rerun for 0.3's weights, which move the curve's points by about 100 degree days) at bases 0–10 °C (upper 30 °C, single sine, from January 1; 198 fits, all converged; at 4 °C it reproduces the v2 fit's critical points) and scored each base on years and traps left out, predicting a held-out season from the shared curve alone:

- **Base:** 0–6 °C can't be told apart. Timing errors stay within 0.5 day of 4 °C's, while a single year's error varies by 6–11 days; held-out likelihood favors 10 °C leaving years out and 0 °C leaving traps out, both weakly. Above about 7 °C the fit and timing get worse. The model keeps 4 °C.
- **Degree days against the calendar:** across 45 trap-seasons (June 4 to September 27), the date the season's catch passed 10 % was predicted about 2 days better by degree days (17.1 days RMSE at 4 °C) than by the calendar date (18.8). At 50 % and 90 % of the catch and at the peak week, degree days did no better than the calendar (curve: 16.9, 10.0 and 35.1 days; calendar 17.0, 11.5 and 33.0). The catch is mostly migrant and host-alternating aphids, whose arrival local warmth doesn't time. The curve is read as typical pressure through the season plus an onset signal, not a forecast of a season's peak date (Ben, 2026-11-19).
- The peak week is a poor event: catches are often bimodal, and the observed peak moves between the two flights (SD about 30 days across seasons). At 4 °C the curve puts the 10 % and 50 % points about 6 and 4 days early on held-out years.

## Limits and open questions

- **In sample, and years vary:** the curve is the typical year's; single years peak from about 1,720 to 4,760 degree days. Trap catches in the current season are a better guide than the curve.
- **The trap data hold presence records only:** weeks with no aphids at all aren't in the EDDMapS export, so the season's edges carry no zeros, and the curve's low end may be too high.
- **Thin ends:** 18 catches below 500 degree days and 16 above 5,000.
- **Which clock by default:** degree days, for the onset signal and because they carry across Wisconsin's latitudes; the calendar curve fits the catches better. A question for Ben (D101).
- **Transmission efficiencies** are single values from wide literature ranges (green peach aphid 0.08–0.83).
- **Cheapest independent comparison:** the suction traps' 2024–2026 seasons (the network's later catches), against the curve.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_aphid_pvy_vectors.py
cd tmp/R/pvy-model && OPENBLAS_NUM_THREADS=1 Rscript pvy-model-v3.R   # the fit (a few minutes); needs data/weather-v2.csv
```
