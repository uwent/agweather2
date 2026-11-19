# Soybean growth stages (`soybean-stages`): validation

Model version 0.1, written 2026-11-18 (D98). The model: `packages/agmodels/src/agmodels/models/soybean_stages.py`, run through `agmodels.crops` (D32–D34); its page: `soybean_stages.md` beside it. Built in Phase 3 (PLAN.md, Phase 3's crop growth stages, step 4).

**In short:** a port of SOYDEV (Setiyono et al. 2007) in its mode that sets every parameter from the maturity group. On the paper's six Lincoln, Nebraska seasons of a maturity group 3.0 variety, run on reanalysis weather, beginning bloom (R1) came within 6 days of the observed date and beginning maturity (R7) within 3, close to the paper's own error for this mode (3.6 days). There is no check against Wisconsin fields, and no legacy tool to compare with.

## Sources and what we took from each

| Source | What it gives | What we took |
| --- | --- | --- |
| Setiyono et al. 2007 (SOYDEV) | Daily development rates Rmax·f(T)·f(P) per phase, with beta functions of mean temperature (Wang and Engel 1998) and day length (after Yin et al. 1995); relations from maturity group to the photoperiod and rate parameters (Figs. 4 and 11, option c: RMSE 3.6 days over V1, R1, R3.5, R5 and R7 for 21 cultivars of maturity group 0.8–4.2); node appearance (Fig. 13); emergence from planting by the hypocotyl's growth (after STICS); Table 3's Lincoln seasons of NE3001 | The model as published in that mode, with Fig. 13's indeterminate node parameters read from its points; the seasons as a check |
| Fehr and Caviness 1977 | The V and R stage definitions | Stage names and descriptions |

## Choices and differences

- **Day-length pairs:** Table 2 prints each phase's day lengths as critical then optimum (11 and 25 h; 12 and 18 h); the function needs the optimum below the critical, and Figs. 4 and 12 show optima of about 11–12 h, so the pairs are read as optimum, critical. At maturity group 3 this gives an optimum of 11.07 h and a critical 25.20 h for floral induction.
- **Stages predicted and placed:** the model predicts VE, VC, V1 and later V-stages, R1, R3.5, R5 and R7. R2, R3 and R4 are spaced evenly on the R1–R5 progress either side of R3.5, and R6 halfway from R5 to R7; these four are flagged as estimated. R8 isn't modelled.
- **Nodes:** indeterminate varieties only; semi-determinate parameters aren't offered.
- **Emergence:** from planting by the hypocotyl model at 1, 1¼ or 1½ in, or the biofix set to emergence.
- **Maturity groups below 0.8** extrapolate the paper's fits (the options run from 0.0).
- **Gating margin:** 5 days either side of a disease's stage window (white mold, frogeye leaf spot, soybean Cercospora; red crown rot is anchored to R1), from the paper's RMSE of 3.6 days and the 6 days R1 missed by on its seasons (below).

## Checks

### Against Setiyono et al.'s seasons

`packages/agmodels/tests/test_crops.py::test_soybean_seasons_from_setiyono_et_al`, run in CI: the six seasons of NE3001 (maturity group 3.0) at Lincoln in the paper's Table 3 (1999, 2000, 2001, 2002, 2004, 2005), started from the observed emergence. The weather is ERA5 reanalysis from Open-Meteo at the site (`packages/agmodels/tests/fixtures/phenology_weather.csv`), not the site's station. The test allows 6 days at R1 and 4 at R7 and checks the final node count is 15–25; the differences it found (ours − observed, days):

| Season | R1 | R7 | Nodes at the end |
| --- | --- | --- | --- |
| 1999 | +3 | +1 | 20.7 |
| 2000 | +2 | +2 | 20.8 |
| 2001 | +6 | −3 | 21.4 |
| 2002 | −1 | +2 | 23.5 |
| 2004 | +1 | −1 | 18.7 |
| 2005 | +1 | +2 | 23.3 |

R1 came within 6 days in all 6 seasons (RMSE 2.9 days, a mean of 2.0 days late) and R7 within 3 (RMSE 2.0), against the RMSE of 3.6 days Setiyono et al. (2007) report for this mode over their 21 cultivars. These are seasons the paper itself reported, likely among those its relations were built from, so they show the port reproduces SOYDEV rather than test it on new fields.

### Behavior

Also in `test_crops.py`: the temperature and day-length functions are 1 at their optima and 0 at and beyond their limits; Fig. 4's parameters at maturity group 3 (`test_response_functions`); stages come in order from planting and later maturity groups mature later (`test_soybean_from_planting_and_by_maturity_group`); on the same weather, a site farther north flowers later (`test_soybean_on_the_grid`).

## Limits and open questions

- No Wisconsin comparison, and none from planting: the seasons above start at observed emergence, so the hypocotyl model's emergence dates aren't checked against anything.
- Fig. 13's node parameters were read from plotted points, not a published fit.
- Maps use maturity group 2.0 everywhere until location-adjusted maturity (D66, parked; Mourtzinis and Conley 2017's map is the lead).
- **Cheapest independent comparison:** USDA NASS's weekly Crop Progress for Wisconsin (percent emerged, blooming, setting pods, dropping leaves), run from typical planting dates by region, 2016–2025; better, if UW–Madison's soybean program has recorded planting, R1 and R7 dates by maturity group in its trials, those.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_crops.py
uv run python packages/agmodels/tests/fixtures/make_phenology_weather.py   # the ERA5 seasons (needs the network)
```
