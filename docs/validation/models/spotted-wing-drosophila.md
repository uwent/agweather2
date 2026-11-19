# Spotted wing drosophila (`spotted-wing-drosophila`): validation

Model version 0.2, written 2026-11-19 (D98). The model: `packages/agmodels/src/agmodels/insects/spotted_wing_drosophila.py`, a fitted stage (D36, `agmodels.phenology.FittedStage`) reading `spotted_wing_drosophila_fit.csv` beside it; its page: `spotted_wing_drosophila.md`. Version 0.1 (2026-10-28 to 2026-11-19) was VDIFN's sine-ramped window (1,276, 3,180, 4,000) on 45/86 °F; its report is in git history.

**In short:** the model reads adult activity off a curve refitted on 2026-11-19 to the original trap counts of Kamiyama et al. 2020 (13 traps in four Door County tart cherry orchards, 2015–2018; Ben Bradford is a coauthor) on AgWeather's weather at 45/86 °F from January 1. Activity peaks at about 2,330 degree days and is above 90 % of the peak from about 2,250 to 2,420. Version 0.1's numbers came from the paper, whose degree days were computed with base 39 °F by a modified average although its methods state 7.2 °C (45 °F): they run about 1.35–1.55 times AgWeather's, so VDIFN's peak at 3,180 came about a month after the flies' and isn't reached at Sturgeon Bay in most years. On AgWeather's scale the paper's peak is 2,340, where the refit peaks too. The fit describes the trap data it came from and hasn't been tested on other years, crops or regions.

## Sources and what we took from each

<!-- prettier-ignore -->
| Source | What it gives | What we took |
| --- | --- | --- |
| Kamiyama, Bradford, Groves and Guédot 2020, PLOS ONE 15(4): e0227726 (open access) | Weekly catches in Scentry traps, 13 traps in four tart cherry orchards near Maplewood, Sturgeon Bay, Egg Harbor and Sister Bay, 2015–2018; degree days "with a lower threshold of 7.2 °C and upper threshold of 30 °C" from PRISM; a GLMM and a GAMM, with critical points 1,276 (first detection), 1,549, 2,019 (above average), 3,180 (peak) and 4,707 | The trap counts and trap locations (Table 1); compared its points (below) |
| The study's original files (`tmp/R/kamiyama_2020_drosophila/`: `swd-data.csv`, `gdd_script.r`, `swd.r`, `prism/`) | The counts with each trap-week's degree days and humidity; the degree-day script; the critical-point analysis | Counts; the investigation below |
| The refit, `tmp/R/kamiyama_2020_drosophila/swd-refit.R` (2026-11-19), figure `swd-refit.png`, predictions `swd_predictions.csv`; the threshold comparison `swd-thresholds.R` | A negative binomial GAM (log link, REML) of each trap's weekly catch on degree days 45/86 °F at the midpoint of its collection week, with each year's own curve, trap and trap-season effects, zeros kept; 772 trap-weeks on AgWeather v2's weather (`swd_weather.py`: the archive for 2016–2018, gridMET on the archive's basis for 2015). Deviance explained 72 % | The typical year's curve (random effects at zero), every 10 degree days from 180 to 3,050 |
| Tochen et al. 2014, Environmental Entomology 43: 501–510 | The fly's development from 10 to 30 °C on cherry and blueberry: minimum 7.2 °C, optimum 28.1 °C, development slowing at 30 °C, the highest tested | The thresholds, 7.2 and 30 °C (45 and 86 °F), as the paper intended |
| VDIFN's `db/seeds.rb` (`../ag-vdifn`) | Single sine 45/86 °F, January 1; one span (1,276, 3,180, 4,000) | Compared only (below) |

## Investigation

### The paper's degree days

The paper's degree-day totals run about 1.5 times AgWeather's at the same orchards (1,276 on June 22–26 in the paper; July 6–21 on AgWeather's 45/86 °F in 2016–2018). The cause is the calculation, not the weather:

- **The script used base 39 °F, not 7.2 °C.** `gdd_script.r` computes `fn.gdd(tminF, tmaxF, 39, 86)`: a modified average, the minimum raised to 39 °F and the maximum capped at 86 °F, summed from January 1 on PRISM's daily minimum and maximum. Recomputed from the PRISM files kept with the data, this reproduces the data's degree-day column to under 1 degree day at the matching traps in 2016 and 2017 (within about 3 in 2018, whose July–December file here is PRISM's provisional release). 39 °F is 3.9 °C; the methods' 7.2 °C (45 °F) was never computed. Both of the study's degree-day scripts (Ben's and the first author's) carry the same call.
- **On the same weather, base 39 °F modified average runs 1.47–1.58 times single sine 45/86 °F by June 24 and 1.32–1.39 times by August 31** (PRISM at three of the traps, 2016–2018).
- **The weather agrees.** AgWeather's archive is within about 1 °F of PRISM at these traps (daily minimum 0.5–0.8 °F lower, maximum within 1.1 °F, April–August 2016–2018), and the paper's method run on AgWeather's weather gives totals 0.99–1.01 times the paper's in every year (2015 on gridMET on the archive's basis, 0.997).

On AgWeather's 45/86 °F, by a cubic fit of one scale against the other at the trap-weeks, the paper's points are:

<!-- prettier-ignore -->
| The paper's point | Its degree days (base 39 °F, modified average) | AgWeather's degree days (45/86 °F, single sine) |
| --- | --- | --- |
| First detection (a local maximum) | 1,276 | 811 |
| A local minimum | 1,549 | 1,022 |
| Crosses the average, rising | 2,019 | 1,402 |
| Peak | 3,180 | 2,340 |
| VDIFN's end (not from the paper) | 4,000 | 2,916 |
| Falls below average (past the data) | 4,707 | 3,292 |

### The paper's critical points

`swd.r` (reproduced exactly from the original files by `swd-refit.R`, giving 754, 1,276, 1,549, 2,018, 3,180 and 4,709) fits a Poisson GLMM with a random intercept for each distinct degree-day value (and year, trap and their interaction), then a GAM through those intercepts, and reads the curve's turning points and zero crossings. As with the PVY analysis (`aphid-pvy-vectors`), these aren't all events:

- **1,276 "first detection"** is a small local maximum while the curve is still far below the average (the late-June catches of 2016 and 2017). Single traps first caught flies anywhere from 790 to 2,321 of the paper's degree days (median 1,664).
- **2,019 "above average"** is where the curve crosses the sample's average; the zero line has no biological meaning.
- **3,180 is the curve's maximum**, a real peak.
- **4,707** is where the curve falls below average, extrapolated past the data, whose highest total is 4,206. VDIFN's end at 4,000 isn't in the paper.
- The Poisson model's residual deviance is 4.7 times its degrees of freedom: the counts are far more variable than a Poisson allows.

### The trap data

- 806 trap-weeks: 34 without a count (left out, not counted as zero) and 291 zeros, all kept.
- **Three trap-seasons look copied from another trap.** P Mulch and P Plant Path (Sturgeon Bay) share 4 of 7 nonzero weekly counts in 2016 and 6 of 9 in 2018, and P Fence (Sturgeon Bay) and Seaq Hiland (Sister Bay) 6 of 9 in 2017, mostly in runs of consecutive weeks. Leaving the three out moves the refit's points by 4–51 degree days (sensitivity, below). Worth checking against the field sheets.
- **Seasons differ in length.** 2015's trapping began June 26 and ran to October 23; the other years ran from late May or early June to late August or early September. On AgWeather's scale, 2015 reaches 3,058 degree days and the others 2,174–2,669, so the curve after about 2,600 rests on 2015 alone.

### Which degree-day settings?

`swd-thresholds.R` compares 48 settings (base 39, 41, 43, 45, 48 or 50 °F; upper 86 °F or none; single sine or modified average; from January 1 or March 1), plus the paper's own degree-day column and a calendar baseline, out of sample:

- **Event timing, in calendar days.** For each trap-season, the first catch, the first of two weeks in a row with flies, and the collection dates by which the season's catch to August 25 reached 10 % and 50 % (204 events). Each event's degree days in a held-out year (or town) are predicted as the other years' (towns') mean, and the error is the days between the predicted and observed dates.
- **The curve's fit to the counts.** The refit's model fitted to three years and scored on the fourth by its negative binomial log-likelihood, as predicted and with the held-out year's overall level refitted (which isolates timing and shape from the year's abundance).

<!-- prettier-ignore -->
| Setting | Events, leave one year out (RMSE, days) | Events, leave one town out (days) | Curve, out-of-sample log-likelihood | Curve, with the year's level refitted |
| --- | --- | --- | --- | --- |
| Calendar day of year (no degree days) | 15.5 | 13.6 | | |
| The paper's degree-day column (modified average 39/86 °F on PRISM) | 15.0 | 13.4 | −2,788 | −2,486 |
| Modified average 39/86 °F from January 1 (the paper's method on AgWeather's weather) | 15.6 | 14.0 | −2,788 | −2,475 |
| Single sine 39/86 °F from January 1 | 15.6 | 14.0 | −2,799 | −2,478 |
| Single sine 43/86 °F from January 1 | 16.0 | 14.4 | −2,830 | −2,470 |
| **Single sine 45/86 °F from January 1 (the model)** | 16.3 | 14.6 | −2,840 | −2,465 |
| Single sine 45/86 °F from March 1 | 16.4 | 14.6 | −2,852 | −2,464 |
| Single sine 48/86 °F from January 1 | 16.8 | 15.0 | −2,863 | −2,465 |
| Single sine 50/86 °F from January 1 | 17.1 | 15.3 | −2,877 | −2,467 |
| All 48 settings | 15.6 to 17.2 | 14.0 to 15.3 | −2,884 to −2,788 | −2,486 to −2,462 |

All 50 rows are `tmp/R/kamiyama_2020_drosophila/out/thresholds/summary.csv`; higher log-likelihood is better.

The data can't choose. Every setting's event error is 15.6–17.2 days (leave one year out) and none beats the calendar (15.5 days); only the paper's own column does, by half a day. Traps in the same orchard caught their first flies weeks apart under the same weather, and events are seen only at weekly collections. Lower bases do slightly better on events, as they make degree days closer to calendar days. The curve's likelihood points both ways: as predicted, lower bases score better (base 39 °F by about 50 over base 45 °F), but almost all of that difference is 2017, a year whose catches ran about 12 times what the other three years predict (its refitted level 2.5 log units up), and with each held-out year's level refitted the order reverses and bases of 43–50 °F score about 10 better than 39 °F. Upper 86 °F or none, and January 1 or March 1, change little anywhere. With one region and four years, the sites differ little in climate, so the settings are nearly interchangeable. The model keeps the laboratory threshold, 7.2 °C (45 °F; Tochen et al. 2014), the paper's stated setting, with AgWeather's standard method (single sine, 86 °F cutoff, from January 1). The profile is `tmp/R/kamiyama_2020_drosophila/out/thresholds/profile.png`.

## Choices and differences

- **The refit (2026-11-19):** one model of the counts instead of the paper's two stages; negative binomial (the counts' variance is far above a Poisson's: a Poisson fit's AIC is 16,096 against 4,601, and its curve follows the biggest catches to the end of the data); each year's own deviation curve (`s(x, year, bs = "fs", m = 1)`), trap and trap-season random intercepts, as in the PVY refit; zeros kept; each catch at the degree-day midpoint of its collection week; each trap on its own grid cell's weather; relative humidity left out (AgWeather's model runs on degree days alone; the paper found a weak effect).
- **Degree days:** single sine, 45 °F (7.2 °C), cutoff 86 °F (30 °C), from January 1: the paper's stated thresholds and the old model's, computed as AgWeather computes them.
- **Reading the curve:** linear between the predictions; 0 before 180 degree days (no trap data; the curve is essentially zero there); held at its last value (32 % of the peak) after 3,050 until fall freezes end the season.
- **Risk:** activity over its peak (98.9 flies per trap per week for a typical year and trap), Low from 0.05 (about 1,130 degree days), Moderate from 0.25 (1,790), High from 0.5 (2,094), Very high from 0.75 (2,193 to 2,501), the D36 defaults.
- **The early bump:** the curve has a small local maximum at 1,263 degree days (13 % of the peak) and a dip to 9 % at 1,453, from the first large catches of each July (July 24, 2015; July 15, 2016; July 21, 2017), each followed by lower catches for a week or two. Kept: it's in the data, and it puts activity at Low from about mid-July in Door County.

## Checks

### Against the fit

`packages/agmodels/tests/test_spotted_wing_drosophila.py`, run in CI, against `swd_critical_points.csv`, within 10 degree days:

| Point | The fit | The model |
| --- | --- | --- |
| Peak | 2,334 | 2,330 |
| 50 % of peak, rising | 2,094 | 2,094 |
| 90 % of peak, rising | 2,251 | 2,251 |
| 90 % of peak, falling | 2,423 | 2,422 |
| 50 % of peak, falling | 2,948 | 2,947 |

The fit's own checks (`tmp/R/kamiyama_2020_drosophila/out/refit/`): converged (gradient 1e-5, Hessian positive definite); the degree-day smooth uses 11.8 of 14 degrees of freedom (k-index 0.83, p = 0.1; with k = 25 the peak moves 12 degree days); observed over fitted 0.94–1.37 in 300-degree-day bins from 600 to 3,000 degree days (0.47 at 300–600, where 93 % of catches are zero); residuals' week-to-week correlation within a trap-season, median 0.12. Year curves improve the fit over year intercepts alone (AIC 4,601 against 4,675). Refitting with each year left out moved the peak between 2,297 and 2,394, 50 % rising between 1,989 and 2,153, and 90 % rising between 2,192 and 2,299. Each year's own curve peaks between 2,289 and 2,367 degree days, at 0.54 to 2.64 times the typical year's height.

Sensitivity of the peak: the catch at its collection date's total rather than the week's midpoint, 2,407; without the three suspected copies, 2,340; year intercepts only, 2,379; year and trap intercepts only, 2,367.

### Against the paper

Kamiyama et al. 2020 put the peak at 3,180 degree days, computed at base 39 °F by a modified average. On AgWeather's 45/86 °F at the same traps that's 2,340, within 10 degree days of the refit's peak at 2,334: the refit and the paper agree on the peak once both are on one scale. The paper's other points are features of its curve rather than events (above): its "first detection" at 1,276 is 811 on AgWeather's scale, where the refitted activity is under 1 % of the peak, and the traps' first catches were spread over weeks.

### Against VDIFN

VDIFN, the system this model replaces (a reference, not the truth, D54), rated risk from 1,276 to 4,000 degree days on 45/86 °F, peaking at 3,180: the paper's numbers read on a scale they weren't computed on. On the refitted curve, activity at VDIFN's start (1,276) is 13 % of the peak, and VDIFN's peak (3,180) and end lie past the data, where activity is held at 32 %. In AgWeather's 1996–2025 weather at Sturgeon Bay (the research station), the refit's peak (2,330) comes around August 29 in a median year, while 3,180 is reached by October 31 in only 9 of 27 years; at Madison, the refit's peak comes around August 10 and 3,180 around September 14.

## Limits and open questions

- **In sample, one region, one crop:** four seasons of tart cherry orchards in Door County, sprayed four to five times a season with pyrethroids and organophosphates; catches in sprayed orchards reflect the sprays as well as the population. Untested on other years, on berries (the model's other crops) and in southern Wisconsin, where the season runs on past the data.
- **After the peak:** the decline after about 2,600 degree days rests on 2015 alone. In southern Wisconsin the curve's peak comes around August 10, and the model's decline after it is an extrapolation; Leach et al. 2019's model of seven years of catches in Michigan blueberries puts the peak in late September or early October (as Kamiyama et al. 2020 report it).
- **Timing within the season varies by trap more than by year:** single traps' first catches ranged over weeks in the same year. The model is the typical trap's curve, not a forecast of first catch.
- **Three trap-seasons look copied** (above); the field records would settle it.
- **Cheapest independent comparison:** more recent trap counts from Wisconsin's fruit growers or UW's fruit program (berries as well as cherries, and seasons running into October), scored against the curve.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_spotted_wing_drosophila.py
uv run python tmp/R/kamiyama_2020_drosophila/swd_weather.py   # weather at the traps (needs data/)
cd tmp/R/kamiyama_2020_drosophila && Rscript swd-refit.R      # the reproduction and the fit (about a minute)
cd tmp/R/kamiyama_2020_drosophila && Rscript swd-thresholds.R # the threshold comparison (several minutes on 8 cores)
```
