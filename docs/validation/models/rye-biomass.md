# Winter rye cover crop biomass (`rye-biomass`): validation

Model version 0.3, written 2026-11-18 (D98), rewritten 2026-11-19 for 0.3 (Ben's go-ahead, from the study in `tmp/rye-study/report.md` and audit round 2, `tmp/crt-model-audit-2-cotton-pecan-rye.md` section 3). The model: `packages/agmodels/src/agmodels/models/rye_biomass.py`; its page: `rye_biomass.md` beside it. Versions 0.1–0.2 were the Crop Risk Tool's logistic (`predict_rye_biomass`), ported in Phase 3; 0.3 is a new model fitted on the authors' data.

**In short:** biomass rises with growing degree days since planting (base 0 °C, single sine, no upper threshold), the fall's counted up to 800 °C-days, on a logistic whose square levels off at a fixed 12,000 lb/ac. Its two coefficients were fitted on 138 Wisconsin site-years (Colet et al.'s data) with AgWeather's archive weather. Leaving out one location at a time it misses by about 1,180 lb/ac on average (MAE; RMSE 1,887) and puts 68 % of site-years in the right level; it underpredicts heavy stands. The data are nearly all from southern and central Wisconsin.

## Sources and what we took from each

| Source | What it gives | What we took |
| --- | --- | --- |
| Colet, Bradford, Mourtzinis et al. (2026), Crop, Forage & Turfgrass Management 12:e70157, doi:10.1002/cft2.70157 | Rye biomass from 135 site-years in Wisconsin (2015/16–2024/25) against weather and management; their best model a logistic in season GDD, fall rain, planting date and latitude (RMSE 1,870 lb/ac). The draft in `tmp/R/crop-risk-tool-models/Rye biomass/` ("Weather-Based Prediction of Cereal Rye Biomass Accumulation in Wisconsin") and the authors' 2026 algorithm document give a linear model in two 60-day windows instead | Their plot data (`CR_data_forR v2.xlsx`, 791 plots → 144 site-years), refitted to our own form; not their equation |
| Crespo, O'Brien, Ruis, Kovar and Kaspar (2024), Field Crops Research 315:109473, doi:10.1016/j.fcr.2024.109473 | A 13-year Iowa study: above 800 GDD (base 0 °C) in the fall, final rye biomass wasn't limited by fall thermal time | The 800 °C-day cap on the fall's degree days |
| UW–Madison Extension, "Biomass thresholds for cereal rye cover crop goals" | Biomass needed for each goal: nitrate leaching, erosion and runoff phosphorus, weed suppression | The levels: Low below 2,000 lb/ac, Moderate from 2,000, High from 4,500 |
| Badger Crop Network, "How much cereal rye cover crop biomass is needed to suppress troublesome weeds in Wisconsin?" | Weed suppression by biomass | Background for the High level |

The published paper (Crossref, online September 11, 2026) has a different title and author list (Ben added) from the draft in the folder, and its abstract's best model is a logistic with latitude, not the draft's linear model. We haven't read the published text; its model wasn't compared here.

## The model

```
G       = gdd_total − gdd_fall + min(gdd_fall, 800)    # °C-days; gdd_fall = planting through December 31
biomass = 12000 / (1 + exp(−0.00327 × (G − 1127)))²     # lb/ac
```

2,000 lb/ac at G ≈ 1,010 °C-days (1,820 °F-days); 4,500 at G ≈ 1,270 °C-days (2,280 °F-days); a quarter of the ceiling, 3,000 lb/ac, at G = 1,127 °C-days (2,029 °F-days).

## Choices and differences

- **Why this form (Ben, 2026-11-19):** the study compared the deployed logistic, the authors' linear model and a dozen others under leave-one-location, -year and -source-out cross-validation (`tmp/rye-study/report.md`). The linear model fits a little better by RMSE (1,787 against 1,811 leaving out a location, on the Crop Risk Tool's weather; group-bootstrap 90 % intervals of the difference all include 0), but on real weather at 8 Wisconsin points over 320 springs it went negative in 226, read 0 on May 15 in 91 (wet falls), fell from one day to the next in 204 and exceeded 14,000 lb/ac by June 15 in 10. This form stays between 0 and 12,000 by construction, rises every day, has the lowest MAE of the bounded forms (1,154 against the linear model's 1,224) and the smallest error on small stands (MAE 585 against 674 where it predicts under 2,000).
- **Fall rain and planting date dropped:** the deployed logistic's rain and planting terms added nothing out of sample (the GDD-only fit did as well), and the linear model's −330 to −400 lb/ac per inch of rain didn't survive a bounded form or a change of weather source. The planting date still acts through the degree days since planting.
- **The ceiling, fixed at 12,000 lb/ac:** the data can't place it: leaving out a location, RMSE 1,834 at 10,000, 1,811 at 12,000, 1,808 at 14,000, 1,815 at 16,000 (free fit about 11,700). The data's largest site-year mean is 13,537 lb/ac.
- **The fall cap, 800 °C-days:** only 3 site-years exceed it, but capping at 800 lowered the leave-one-location-out RMSE from 1,889 to 1,811; 600 (1,891) and 1,000 (1,857) did worse (`tmp/rye-study/capfall.py`, Crop Risk Tool weather). Crespo's fall runs to December 1, ours to December 31.
- **Degree days:** single sine, base 0 °C (32 °F), no upper threshold, as the study's features (`assemble.py`); 0.2 had a 35 °C cutoff, which doesn't matter between fall and June in Wisconsin.
- **Coefficients from AgWeather's archive:** fitted on √biomass (nonlinear least squares, the ceiling fixed) over the 138 site-years the archive covers (falls from 2016; the Crop Risk Tool's IBM weather covers all 144). Archive: k = 0.00327 ± 0.00024, x0 = 1,126.9 ± 16.2; the tool's weather: k = 0.00334 ± 0.00024, x0 = 1,122.9 ± 14.7 (`tmp/rye-study/fit03.py`, `fit03.log`). The model takes the archive's, rounded to 0.00327 and 1,127, since it runs on the archive.
- **When it's shown:** biomass from March 1 after planting (the data's terminations run April 10 to June 17, 22 after June 1); none in fall and winter, though the degree days show from planting. The season runs August 25 to June 15, so days after June 15 are out of season (flagged, still computed) and the default biofix (October 1) follows the season across New Year.
- **Plantings outside the data:** the data's plantings ran August 27 to November 10 (median October 11). `planting_outside_data` is 1 for a planting before August 25 or after November 10; the biomass is still given.
- **Region:** shown in Wisconsin and its neighbours (Minnesota, Iowa, Illinois, Michigan), with a caution: the data are from 42.6 to 45.3° N in Wisconsin, only 7 of 144 site-years north of 44° N.
- **Missing days:** a missing day adds nothing to the degree days unless the runner bridges it (D45's named estimate, flagged).
- **Levels unchanged:** 2,000 and 4,500 lb/ac, UW–Madison's goals; the study gave no reason to move them.
- **The Crop Risk Tool's logistic (0.1–0.2), as history:** biomass = ((423.1 − 1.031 × planting day − 0.2878 × fall rain in mm) / (1 + exp(−0.003663 (GDD − 1049))))², GDD 0/35 °C since planting, fall rain planting through December 31; 0.2 floored the height at 0. Audit round 2 found it fed all fall precipitation where it had very likely been fitted on rain above freezing (in-sample bias −1,028 lb/ac against −153). The parity tests against the tool went with 0.3: an intended difference.

## Checks

### Against measured biomass

Colet et al.'s (2026) plot data (`CR_data_forR v2.xlsx`): 791 plots averaged to 144 site-years (one site, planting, termination and nitrogen treatment) at 16 locations (site ids within about 5 km merged), falls 2015 to 2024 (none in 2017), eight data sources; 138 of them inside the archive's years. Biomass 48 to 13,537 lb/ac (median 2,531). Each split refits k and x0 without the held-out group (`tmp/rye-study/fit03.py`).

On AgWeather's archive (138 site-years), the coefficients the model uses:

| Left out | RMSE | MAE | Bias | Right level | MAE by measured biomass: < 2,000 / 2,000–4,500 / ≥ 4,500 | MAE by predicted: < 2,000 / 2,000–4,500 / ≥ 4,500 |
| --- | --- | --- | --- | --- | --- | --- |
| A location (15) | 1,887 | 1,182 | −225 | 68 % | 632 / 924 / 2,266 | 644 / 1,478 / 1,675 |
| A fall (8) | 1,966 | 1,264 | −123 | 67 % | 700 / 1,044 / 2,334 | 688 / 1,595 / 1,653 |
| A data source (8) | 2,014 | 1,303 | −106 | 67 % | 738 / 1,142 / 2,324 | 693 / 1,615 / 1,756 |
| Nothing (in sample) | 1,842 | 1,161 | −208 | 71 % | | |

On the Crop Risk Tool's weather (144 site-years): RMSE 1,811 / 1,891 / 1,934 and MAE 1,154 / 1,230 / 1,274 leaving out a location, fall or source; 65–69 % in the right level; MAE by predicted value 585–669 below 2,000, 1,319–1,632 from 2,000 to 4,500, 1,716–1,911 above.

In short: a typical miss of about 1,180 lb/ac leaving out a location (MAE 1,150–1,300 across splits and weather sources); about 630 where the rye made under 2,000 lb/ac (600–700 where the model predicts under 2,000), 920–1,140 where it made 2,000 to 4,500 (1,300–1,600 where it predicts that), and about 2,270 (2,100–2,300) where it made 4,500 or more, which the model underpredicts (bias about −1,500 to −1,850 there). About 7 site-years in 10 land in the right level.

The page's rounded summary ("about 1,200 lb/acre; about 600 below 2,000, about 1,300 at 2,000 to 4,500, 2,000 or more above 4,500; about 7 in 10") takes the study's figures.

Run in CI (`packages/agmodels/tests/test_rye_biomass.py`): the formula on known values and the levels' degree days, the fall cap, the bound, a synthetic season (blank before March 1, March 1 in a leap year, never falling), fall degree days stopping at New Year, missing data, the planting flag at its edges (leap years too) and the season's end.

## Limits and open questions

- **Jose_WeedWisc's plots** (10 site-years at site_06 and Arlington, 2019–2022): every model underpredicts them by 3,400 to 4,000 lb/ac (this one by 4,015 on average); at site_06 they run about 4,000 above Guilherme's plots at the same site. That points to management (previous crop, manure, nitrogen, plot size), not weather, but we don't know; kept in the fit.
- **Thin northern data:** 7 of 144 site-years north of 44° N, none outside Wisconsin. In the north and in the neighbouring states the model is extrapolating.
- **Heavy stands:** above 4,500 lb/ac the model underpredicts by about 1,500 to 1,850 lb/ac on average; early plantings (August 27 to September 27) by about 1,900.
- **The ceiling and the fall cap** are choices the data can't confirm (above).
- Seeding rate, soil, nitrogen and the previous crop aren't inputs (the data hold nitrogen rate; nearly all seeding was 60 lb/ac).
- **The published paper:** its logistic with latitude hasn't been compared; once read, check its form and error against this one.
- **Cheapest independent comparison:** biomass clipped in later seasons (2025 falls on) or outside the authors' sources, such as northern Wisconsin or Minnesota on-farm trials, on the archive at each field's cell.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_rye_biomass.py
uv run --with openpyxl python tmp/rye-study/assemble.py   # the site-years and their weather features (needs data/)
uv run --with scipy python tmp/rye-study/fit03.py         # 0.3's coefficients and the table above
uv run --with scipy python tmp/rye-study/cv.py agw         # every candidate, on the archive
uv run --with scipy python tmp/rye-study/capfall.py        # the fall cap
```
