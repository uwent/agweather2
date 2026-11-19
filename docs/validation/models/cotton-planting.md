# Cotton planting stand risk (`cotton-planting`): validation

Model version 0.1, written 2026-11-18 (D98). The model: `packages/agmodels/src/agmodels/models/cotton_planting.py`; its page: `cotton_planting.md` beside it. Ported in Phase 3 (PLAN.md, Phase 3 step 6) from the Crop Risk Tool (`cotton_planting_model`, `build_cotton_planting`; copy in `tmp/R/crop-risk-tool/`), which it replaces. A southern model: it runs at points through Open-Meteo until the archive's box reaches the cotton states.

**In short:** Zachary Noel's (Auburn University) emergence model and its standard error, reproduced from the Crop Risk Tool to within a relative 1e-9 on a sweep of 2,704 input combinations and over a year of daily weather. We don't have the fit's data or the years it covers, and it hasn't been compared with stands counted in the field.

## Sources and what we took from each

| Source | What it gives | What we took |
| --- | --- | --- |
| Zachary Noel (Auburn University, with funding from Cotton Incorporated), as given to the Crop Risk Tool | Emergence as a logistic of Pythium presence, the year, the rain over the 3 days from planting and the mean minimum temperature over the 9 days from planting (coefficients −22.4611, −0.3359, 0.01118 a year, −0.00750 per mm, 0.03929 per °C), with the fit's variance–covariance matrix | The model, its standard error (the delta method on the response scale) and the probability that the stand falls below a limit |
| Adams, Thapa and Kimura 2019 | A synthesis of plant population thresholds for cotton lint yield | Background for the yield-limiting stands offered (15,000 and 20,000 plants per acre) |
| Rothrock et al. 2012 | Seed treatment and environment in cotton seedling disease | Background for the Pythium option |

## Choices and differences

- **Risk:** the probability that seeding rate × emergence falls below the limiting stand, with emergence taken as normal around the prediction; levels Very low below 1 %, Low from 1 %, Moderate from 20 %, High from 35 %, the tool's.
- **Windows at the end of the data:** the tool shrinks the forward windows at the end of its series; v2 gives no value where a window runs past the data or rain is missing in it (a missing minimum temperature is left out of the mean). With the forecast, the windows reach 9 days ahead.
- **The year term** (0.01118 a year on the logit scale) extrapolates the fit's trend to later years; which years the fit covers isn't recorded (an open question for Noel).
- **Region:** the 17 cotton-growing states.

## Checks

### Against the Crop Risk Tool

The tool is what this model replaces: a reference, not the truth (D54). Its outputs were recorded by `packages/agmodels/tests/fixtures/make_crt_fixtures.R`. Run in CI (`packages/agmodels/tests/test_southern_and_cover.py`):

- `test_cotton_model_matches_the_tool`: the probability over 2,704 combinations (rain 0 to 60 mm by 5, mean minimum 0 to 25 °C by 1, Pythium present and absent, seeding rates of 30,000 and 45,000 seeds per acre, a limit of 15,000, years 2020 and 2025) agrees within a relative 1e-9.
- `test_cotton_season_with_full_forward_windows`: each day of 2025 as a planting date at an Eau Claire, Wisconsin grid cell (the tool's recorded weather; not cotton country, but the arithmetic is the same), Pythium present, 45,000 seeds and a 15,000 limit: the probability agrees within a relative 1e-9 on all 357 days whose windows lie inside the year; on the last 8 the tool shrinks its windows and v2 has no value, as intended.
- `test_cotton_risk_levels`: the level boundaries.

## Limits and open questions

- The fit is unpublished: its data, error and range of years, rain and temperatures aren't known to us.
- The year term raises the predicted emergence a little with every year past the fit, a trend that may not hold.
- Seed quality, seed treatment, soil moisture and crusting aren't inputs beyond Pythium's presence.
- The fit assumed untreated seed: the author's model description (`ModelDescription.docx` in the authors' documents) says it "was built assuming no seed treatments were used". Nearly all commercial seed is treated (in Georgia, all of it, per UGA), so the model may overstate the risk for the seed growers plant.
- The author's documents call the risk levels' boundaries arbitrary for now, to be tied to economics later; their edges (Low above 0 %, under 19, over 20, from 35) leave gaps, and the tool and v2 start Low at 1 %.
- **Cheapest independent comparison:** stand counts from cotton planting-date trials in the Southeast (the trials behind the fit, or later years of the same trials, asked of Noel), against Open-Meteo's weather at each site.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_southern_and_cover.py
Rscript --no-init-file packages/agmodels/tests/fixtures/make_crt_fixtures.R   # the tool's outputs (needs its copy in tmp/R/crop-risk-tool)
```
