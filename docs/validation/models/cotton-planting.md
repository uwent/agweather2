# Cotton planting stand risk (`cotton-planting`): validation

Model version 0.2, written 2026-11-18 (D98), updated 2026-11-19 for 0.2 (audit round 2, `tmp/crt-model-audit-2-cotton-pecan-rye.md` section 1). The model: `packages/agmodels/src/agmodels/models/cotton_planting.py`; its page: `cotton_planting.md` beside it. Ported in Phase 3 (Phase 3 step 6) from the Crop Risk Tool (`cotton_planting_model`, `build_cotton_planting`; copy in `tmp/R/crop-risk-tool/`), which it replaces. A southern model: it runs at points through Open-Meteo until the archive's box reaches the cotton states.

**In short:** Zachary Noel's (Auburn University) emergence model and its standard error, reproduced from the Crop Risk Tool to within a relative 1e-9 on a sweep of 2,704 input combinations and over a year of daily weather. Since 0.2 the outputs are the predicted stand and its 95 % confidence interval, rated against the limit, rather than the tool's probability of a stand below the limit (which measured the wrong spread; below). We don't have the fit's data or the years it covers, and it hasn't been compared with stands counted in the field.

## Sources and what we took from each

| Source | What it gives | What we took |
| --- | --- | --- |
| Zachary Noel (Auburn University, with funding from Cotton Incorporated), as given to the Crop Risk Tool | Emergence as a logistic of Pythium presence, the year, the rain over the 3 days from planting and the mean minimum temperature over the 9 days from planting (coefficients −22.4611, −0.3359, 0.01118 a year, −0.00750 per mm, 0.03929 per °C), with the fit's variance–covariance matrix | The model, its standard error (the delta method on the response scale) and the 95 % interval (P ± 1.959964·SE, × the seeding rate); the probability that the stand falls below a limit only for the parity tests (0.1 showed it) |
| Adams, Thapa and Kimura 2019 | A synthesis of plant population thresholds for cotton lint yield | Background for the yield-limiting stands offered (15,000 and 20,000 plants per acre) |
| Rothrock et al. 2012 | Seed treatment and environment in cotton seedling disease | Background for the Pythium option |

## Choices and differences

- **Outputs (0.2):** the predicted stand (emergence × seeding rate, plants per acre), its 95 % confidence interval of the mean emergence (`stand_low`, `stand_high`, P ± 1.959964·SE clipped to 0–100 %, × the seeding rate) and the emergence.
- **Risk (0.2):** the predicted stand against the limiting stand: High below it, Moderate from it to under 25 % above it, Low from 25 % above it. The 25 % margin is ours (the audit's interim proposal), not the authors'.
- **Why not the tool's probability:** 0.1 and the tool gave Φ((limit − P·PP)/(PP·SE)), the probability that the stand falls below the limit with emergence normal around the prediction. SE is the standard error of the *fitted mean* emergence (±2.6 points at Pythium, 2026, 10 mm and 12 °C), not the spread of emergence between fields, which in a beta regression is μ(1−μ)/(1+φ) (about 15 points at φ = 10). So the probability was near 0 or 1 almost everywhere and set by the options, not the weather: on ERA5's 2025 weather at Tifton GA, Stoneville MS and Lubbock TX, plantings March 15 to June 30, the defaults never reached 20 % (maximum 12.8 % at Stoneville), and 30,000 seeds with a 20,000 limit was High on every day at Tifton and Stoneville (audit round 2). The authors' documents don't give the precision φ; once they do, the beta predictive distribution, P(stand < limit) = I_{limit/PP}(μφ, (1−μ)φ), can give a field-level probability. `probability_below` keeps the tool's computation for the parity tests only.
- **The year term** (0.01118 a year on the logit scale) is held at 2025 (`LAST_FIT_YEAR`), provisionally: which years the fit covers isn't recorded (the covariance matrix centres the data near 2006; an open question for Noel), and carrying the trend on adds about 0.011 logit a year.
- **Windows at the end of the data:** the tool shrinks the forward windows at the end of its series; v2 gives no value where a window runs past the data or rain is missing in it. The mean minimum temperature needs at least 7 of its 9 days (0.1 took any one; the gaps rule).
- **Seed treatment:** no option yet. The authors' documents disagree on whether the fit includes seed treatment (`ManualModel.R` says it does, `ModelDescription.docx` says the fit assumed none); waiting on the authors.
- **Region:** the 17 cotton-growing states.

## Checks

### Against the Crop Risk Tool

The tool is what this model replaces: a reference, not the truth (D54). Its outputs were recorded by `packages/agmodels/tests/fixtures/make_crt_fixtures.R`. Run in CI (`packages/agmodels/tests/test_southern_and_cover.py`):

- `test_cotton_model_matches_the_tool`: the probability over 2,704 combinations (rain 0 to 60 mm by 5, mean minimum 0 to 25 °C by 1, Pythium present and absent, seeding rates of 30,000 and 45,000 seeds per acre, a limit of 15,000, years 2020 and 2025) agrees within a relative 1e-9.
- `test_cotton_windows_match_the_tools`: each day of 2025 as a planting date at an Eau Claire, Wisconsin grid cell (the tool's recorded weather; not cotton country, but the arithmetic is the same): v2's 3-day rain and 9-day mean minimum match the tool's, and with Pythium present, 45,000 seeds and a 15,000 limit the probability agrees within a relative 1e-9, on all 357 days whose windows lie inside the year; on the last 8 the tool shrinks its windows and v2 has no value, as intended.

The probability is the tool's output, not v2's since 0.2, but it rests on the same emergence and standard error that v2's stand and interval use, so these tests check v2's arithmetic too. Further tests of 0.2's own behaviour: `test_cotton_stand_and_interval`, `test_cotton_year_is_held_at_the_fits_last_year`, `test_cotton_needs_7_of_9_minimum_temperatures` and `test_cotton_risk_levels` (the level boundaries).

## Limits and open questions

- The fit is unpublished: its data, error and range of years, rain and temperatures aren't known to us.
- The year term is held at 2025 until the authors give the fit's last year; until then 2026 and later run as 2025.
- The 95 % interval is of the mean emergence; stands in single fields vary far more (the beta regression's φ would say how much).
- Seed quality, seed treatment, soil moisture and crusting aren't inputs beyond Pythium's presence.
- The fit assumed untreated seed: the author's model description (`ModelDescription.docx` in the authors' documents) says it "was built assuming no seed treatments were used". Nearly all commercial seed is treated (in Georgia, all of it, per UGA), so the model may underestimate the stand for the seed growers plant.
- The author's documents call the risk levels' boundaries arbitrary for now, to be tied to economics later. Their levels were for the probability (Low above 0 %, under 19, over 20, from 35, with gaps); v2's 0.2 levels on the stand are its own.
- **Cheapest independent comparison:** stand counts from cotton planting-date trials in the Southeast (the trials behind the fit, or later years of the same trials, asked of Noel), against Open-Meteo's weather at each site.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_southern_and_cover.py
Rscript --no-init-file packages/agmodels/tests/fixtures/make_crt_fixtures.R   # the tool's outputs (needs its copy in tmp/R/crop-risk-tool)
```
