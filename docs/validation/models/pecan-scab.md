# Pecan scab hours (`pecan-scab`): validation

Model version 0.3 (beta), written 2026-11-18 (D98), updated 2026-11-19 for 0.2 and 0.3 (D100) (audit round 2, `tmp/crt-model-audit-2-cotton-pecan-rye.md` section 2). The model: `packages/agmodels/src/agmodels/models/pecan_scab.py`, reading the daily feature `hours_rh_over_90_temperature_over_70f` (`agmodels.features`, counted from the hours over the calendar day); its page: `pecan_scab.md` beside it. The notes this condenses are Phase 3 (step 6, "Southern models prototyped") and D50.

**In short:** the Oklahoma Mesonet's Pecan Scab Advisor: hours with RH at or above 90 % and temperature at or above 70 °F, summed from March 1 or the last spray, against the Mesonet's spray threshold for the variety (10, 20 or 30 hours for highly, moderately and low susceptible varieties) and its waiting period (30 days after March 1, or the chosen 5 to 14 days after a spray), since 0.2. At the tool's own thresholds v2 reproduces its daily and running scab hours exactly; v2 counts at the Mesonet's thresholds instead, where the tool's code differs from its own docs. The model is beta: pecans grow outside the data's box, so it runs only at points through Open-Meteo, and nothing compares it with the Mesonet's own advisor or with scab in orchards.

## Sources and what we took from each

| Source | What it gives | What we took |
| --- | --- | --- |
| Oklahoma Mesonet's Pecan Scab Advisor (mesonet.org) | Scab hours (RH ≥ 90 % and ≥ 70 °F) from March 1 to August 31; spray once 10, 20 or 30 have accrued, by variety susceptibility, and 30 days after March 1 or 5 to 14 days after the last spray | The definition, the season and the thresholds (as quoted in the tool's docs; checked on 2026-11-19 against the Mesonet's "How to use" document of June 12, 2023, https://content.prod.mesonet.org/learn/ag/tools_documentation/pecan-scab-advisor-202306-tagged.pdf: every number matches) |
| University of Arkansas, pecan scab (pecanscab.uada.edu) | Background on the disease; the same scab hours counted since the last spray, with a fungicide assumed to protect 10–14 days | Background; the 14-day default protection |
| Payne and Smith 2012, Plant Disease 96:1358–1364, doi:10.1094/PDIS-03-11-0202-RE (Crossref checked 2026-11-19; the corrected republication of 96:117–123) | Logistic models (GEE) of scab severity ≥ 25 % on fruit at five Oklahoma locations, 1994–96 and 2009–10 (eight site-years); the scab hour as average temperature ≥ 21.1 °C and RH ≥ 90 %; field studies found the thresholds "viable, but a modification of the relative humidity component should be considered" (abstract; full text not read) | Cited as the only published evaluation of the scab hour; nothing taken into the code |
| LSU AgCenter (2025) | The same rule; two or more 14-day windows reaching 50–90 % of the threshold signal rising risk | Moderate from half the threshold |
| The Crop Risk Tool (`build_pecan_scab`, `tmp/R/crop-risk-tool/docs/pecan-scab.md`) | Its docs give the Mesonet's 90 % and 70 °F and the variety lists; its code counts RH ≥ 92 % and temperature above 21.1 °C | The risk levels and variety examples; parity at its thresholds below |

## Choices and differences

- **Thresholds:** RH at or above 90 % and temperature at or above 70 °F (21.11 °C), the Mesonet's and the tool's docs', not the tool's code (92 % and above 21.1 °C). An hour at 21.1 °C doesn't count in v2 and does in the tool; the RH difference matters more (more hours count from 90 %). The tool's 92 % was Ben's trial-and-error adjustment to bring its Open-Meteo scab hours toward the Mesonet's (2026-11-19); v2 handles its weather's humidity bias in its own corrections (Ben), so it keeps the Mesonet's 90 %. The research behind the Mesonet's advisor (its thresholds' origin) is still to be read.
- **Counted at 88 % (0.3, D100):** as the other humid-hour models are (D50), the Mesonet's 90 % is counted at 88 % on our weather, and outside the Upper Midwest Open-Meteo's RH isn't mapped by D51. Below, "On real weather".
- **Risk (0.2), the Mesonet's spray decision:** options `susceptibility` (`high` 10 hours, the default, since Desirable, Pawnee and Wichita are the most planted susceptible cultivars; `moderate` 20; `low` 30) and `protection_days` (5, 7, 10 or 14; default 14, as Arkansas and LSU assume). The wait is 30 days when the count starts on March 1 (the biofix's default; the 30 days stand for the start of susceptible growth, budbreak in Oklahoma being early April), `protection_days` when it starts on a spray. Three levels: Low below half the threshold; Moderate from half (LSU's 50–90 % caution), or at the threshold within the wait; High, spray advised, at the threshold once the wait has passed. A spray entered on March 1 itself counts as the season's start (30 days). New outputs: `days_since_start` and `wait_days_left` (0 once the wait has passed); the count runs within one calendar year, as the season does.
- **Why (audit round 2):** without the wait, a count since March 1 says "spray" in late March in a warm wet spring, before shoots and nuts are susceptible, and a count since a spray two days ago says "spray" again; and without a reset the season's total passes 30 by early June and 0.1's top level lasted to August 31. On the Mesonet's 2025 station data at Okmulgee (OKMU), the rule (threshold since the last spray, a 10-day protection) calls for 10 sprays at 10 hours from May 19 and 9 at 30 hours from June 6; in a wet June and July the waiting period, not the hours, sets the interval.
- **0.1's risk:** Low below 10 scab hours, Moderate from 10, High from 20, Very high from 30, the tool's; the timing conditions were stated but not modelled.
- **The day:** the calendar day; a day with a missing hour has no count.
- **Region:** 16 pecan states; runs at points through Open-Meteo until the gridded data reach the South.

## Checks

### Against the Crop Risk Tool

`packages/agmodels/tests/test_southern_and_cover.py`, run in CI, on the tool's fixture (written by `make_crt_fixtures.R` from its R code and its recorded 2025 hourly weather at one grid cell near Eau Claire, Wisconsin, not a pecan area, used only to test the arithmetic):

- **At the tool's thresholds** (RH ≥ 92 % and above 21.1 °C, over each calendar day), the daily scab hours and their running total match the tool's on all 365 days of 2025.
- **At the Mesonet's** (RH ≥ 90 % and ≥ 70 °F; since 0.3 v2 counts the 90 % at 88 % on its weather, D100), the season counts more hours than the tool's, and of hours at 21.1 °C and 95 %, 21.2 °C and 95 %, and 25 °C and 89.9 %, only the second counts.
- 0.1's risk levels stepped at 10, 20 and 30 scab hours, as the tool's do; 0.2 replaces them with the spray decision below.

The tool is the model v2 replaces: this shows the arithmetic is the tool's, not that the advisor is right (D54).

### The spray decision

`test_southern_and_cover.py`, run in CI, on constructed series from March 1, 2025 (the audit's cases):

- From March 1, with highly susceptible varieties: a series that reaches 5 hours on day 15 and 10 on day 20 is Low before day 15, Moderate from day 15 through day 29 (half the threshold, then the threshold within the 30-day wait), and High from day 30.
- From a spray: with 2 scab hours a day, the threshold is reached on the spray's fifth day, and High (spray advised) starts exactly `protection_days` after the spray for each of 5, 7, 10 and 14.
- The susceptibility option moves the threshold to 10, 20 or 30 hours and Moderate to half of it.

These test the rule as the Mesonet states it, not that the rule predicts scab.

### On real weather

From the audit (scratch scripts on the Mesonet's 5-minute observations at Okmulgee, OKMU, March 1 to August 31, 2025, against Open-Meteo at the same point; not run in CI): the station counts 516 scab hours at 90 % and 70 °F, Open-Meteo's historical forecast 347 (254 at the tool's 92 % and above 21.1 °C) and ERA5 374. In warm hours Open-Meteo's RH runs 3.0 points below the station's (ERA5 1.6), with temperature within 0.4 °C, so 92 % moves the wrong way there; matching the station would take about 86–88 %, close to D50's 88 % for gridded RH in Wisconsin. One station and one season, so the check below followed.

### Against five Mesonet stations (0.3)

`tmp/pecan-check/report.md` (scripts and tables beside it; the Mesonet's files are copyrighted and stay out of the repository): Okmulgee, Burneyville, Durant, Eufaula and Shawnee, March 1 to August 31, 2023–2025 (15 station-seasons, 2,760 daily files of 5-minute observations, top-of-hour readings), against Open-Meteo at each station.

- Raw Open-Meteo at 90 % counts 0.68 of the stations' scab hours pooled (0.40–0.90); the historical forecast matches at 87.6 % pooled (88.2 against hourly means), station-seasons 85.0–89.4 (IQR 86.5–88.7); v2's own fetch (NBM, then best_match) at 87.5. Okmulgee needs the lowest (85.0–86.5).
- The gap grows through the season: matching thresholds April 90.3, May 89.8, June 88.2, July 86.9, August 86.0 (historical forecast).
- The advisor's spray rule simulated (10 hours; 30 days from March 1, 10 after a spray): stations 9.7 sprays a season; Open-Meteo at 90 % 8.7, at 88 % 10.0 (first spray a median 2 days early, −27 to +5); v2's fetch at 88 % 9.9.
- D51's RH map (fitted in Wisconsin) made April 3.7 and May 2.2 times too humid: with it, 0.2 at 90 % counted 1.12 times the stations' hours and reached 10/20/30 hours a median 15 days early. So 0.3 counts at 88 % on unmapped RH (D100).
- Reanalyses follow the stations' days poorly (daily r 0.58–0.66, against 0.84 for the historical forecast).

## Limits and open questions

- **No comparison with the Mesonet's advisor or with orchards:** nothing checks our scab hours against the Mesonet's at its stations, or the thresholds against scab outbreaks.
- **Open-Meteo's humidity beyond Oklahoma:** 88 % rests on five Oklahoma stations over three seasons; the Southeast is more humid and unchecked. A single station-season matched at 84–89 %, and a seasonal threshold (about 90/90/88/87/86 % April to August) would fit better, on more stations.
- **The thresholds' evidence:** the scab hour's only published evaluation is Payne and Smith's eight site-years in Oklahoma; the 10, 20 and 30 hour thresholds themselves have no published validation we found. The research behind them (Driever 1996; von Broembsen et al. 1998) wasn't retrieved.
- **The waiting periods** are the Mesonet's rule, not a fitted quantity: 30 days from March 1 everywhere in the region, though budbreak comes earlier in the Gulf states than in Oklahoma.
- **Cheapest independent comparison:** the Oklahoma Mesonet's Pecan Scab Advisor at a few Oklahoma pecan-area stations for one season, against our scab hours at the same points through Open-Meteo.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_southern_and_cover.py -k "scab or pecan"
Rscript --no-init-file packages/agmodels/tests/fixtures/make_crt_fixtures.R   # the tool's fixtures; needs tmp/R/crop-risk-tool
```
