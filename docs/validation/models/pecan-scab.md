# Pecan scab hours (`pecan-scab`): validation

Model version 0.1 (beta), written 2026-11-18 (D98). The model: `packages/agmodels/src/agmodels/models/pecan_scab.py`, reading the daily feature `hours_rh_over_90_temperature_over_70f` (`agmodels.features`, counted from the hours over the calendar day); its page: `pecan_scab.md` beside it. The notes this condenses are PLAN.md Phase 3 (step 6, "Southern models prototyped") and D50.

**In short:** the Oklahoma Mesonet's Pecan Scab Advisor as the Crop Risk Tool carries it: hours with RH at or above 90 % and temperature at or above 70 °F, summed from March 1 or the last spray, against the Mesonet's spray thresholds of 10, 20 and 30 hours for highly, moderately and low susceptible varieties. At the tool's own thresholds v2 reproduces its daily and running scab hours exactly; v2 counts at the Mesonet's thresholds instead, where the tool's code differs from its own docs. The model is beta: pecans grow outside the data's box, so it runs only at points through Open-Meteo, and nothing compares it with the Mesonet's own advisor or with scab in orchards.

## Sources and what we took from each

| Source | What it gives | What we took |
| --- | --- | --- |
| Oklahoma Mesonet's Pecan Scab Advisor (mesonet.org) | Scab hours (RH ≥ 90 % and ≥ 70 °F) from March 1 to August 31; spray once 10, 20 or 30 have accrued, by variety susceptibility, and 30 days after March 1 or 5 to 14 days after the last spray | The definition, the season and the thresholds (as quoted in the tool's docs; the page wasn't reread in this round) |
| University of Arkansas, pecan scab (pecanscab.uada.edu) | Background on the disease | Background |
| The Crop Risk Tool (`build_pecan_scab`, `tmp/shiny/crop-risk-tool/docs/pecan-scab.md`) | Its docs give the Mesonet's 90 % and 70 °F and the variety lists; its code counts RH ≥ 92 % and temperature above 21.1 °C | The risk levels and variety examples; parity at its thresholds below |

## Choices and differences

- **Thresholds:** RH at or above 90 % and temperature at or above 70 °F (21.11 °C), the Mesonet's and the tool's docs', not the tool's code (92 % and above 21.1 °C). An hour at 21.1 °C doesn't count in v2 and does in the tool; the RH difference matters more (more hours count from 90 %).
- **No shift for gridded humidity:** unlike the other humid-hour models, the 90 % isn't counted from 88 % (D50): the Mesonet's threshold hasn't been checked against its stations.
- **Risk:** Low below 10 scab hours since March 1 or the last spray, Moderate from 10, High from 20, Very high from 30. The Mesonet's timing conditions (30 days after March 1, or 5 to 14 days after the last spray) are stated with the levels but not modelled.
- **The day:** the calendar day; a day with a missing hour has no count.
- **Region:** 16 pecan states; runs at points through Open-Meteo until the gridded data reach the South.

## Checks

### Against the Crop Risk Tool

`packages/agmodels/tests/test_southern_and_cover.py`, run in CI, on the tool's fixture (written by `make_crt_fixtures.R` from its R code and its recorded 2025 hourly weather at one grid cell near Eau Claire, Wisconsin, not a pecan area, used only to test the arithmetic):

- **At the tool's thresholds** (RH ≥ 92 % and above 21.1 °C, over each calendar day), the daily scab hours and their running total match the tool's on all 365 days of 2025.
- **At the Mesonet's** (RH ≥ 90 % and ≥ 70 °F, as v2 counts), the season counts more hours than the tool's, and of hours at 21.1 °C and 95 %, 21.2 °C and 95 %, and 25 °C and 89.9 %, only the second counts.
- The risk levels step at 10, 20 and 30 scab hours.

The tool is the model v2 replaces: this shows the arithmetic is the tool's, not that the advisor is right (D54).

## Limits and open questions

- **No comparison with the Mesonet's advisor or with orchards:** nothing checks our scab hours against the Mesonet's at its stations, or the thresholds against scab outbreaks.
- **Open-Meteo's humidity:** the hours at or above 90 % depend on its RH, which hasn't been compared with stations in the South (the D50 study compared the archive, not Open-Meteo, with Wisconsin stations).
- **The Mesonet's timing conditions** (30 days after March 1, 5 to 14 days after a spray) aren't in the risk.
- **Cheapest independent comparison:** the Oklahoma Mesonet's Pecan Scab Advisor at a few Oklahoma pecan-area stations for one season, against our scab hours at the same points through Open-Meteo.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_southern_and_cover.py -k "scab or pecan"
Rscript --no-init-file packages/agmodels/tests/fixtures/make_crt_fixtures.R   # the tool's fixtures; needs tmp/shiny/crop-risk-tool
```
