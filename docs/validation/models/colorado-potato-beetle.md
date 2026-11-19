# Colorado potato beetle (`colorado-potato-beetle`): validation

Model version 0.2, written 2026-11-18 (D98). The model: `packages/agmodels/src/agmodels/insects/colorado_potato_beetle.py`, four fitted stages (D36) run by the insect engine (`agmodels.phenology.FittedStage`), reading `colorado_potato_beetle_fit.csv` beside it; its page: `colorado_potato_beetle.md`. Version 0.1 (2026-10-28 to 2026-11-18) was the Crop Risk Tool's step table; its report is in git history. The separate `colorado-potato-beetle-adults` and `-larvae` models (VDIFN's) are retired in favor of this one's outputs.

**In short:** the model reads adults, egg masses and larvae, and adults and larvae together, off GAM curves fitted to a decade of Wisconsin field scouting counts (Bradford and Groves, unpublished). It reproduces the fits' own critical points to within the 10 degree days the predictions are tabulated at. The fit is the model, so these checks show it was carried over faithfully, not that it predicts fields it wasn't fitted on; no held-out years or fields have been compared. Checking the predicted values for slips found that the first adults and larvae curve had been fitted to the two stages' rows stacked rather than to their sum; Ben refitted it the same day, and it now tracks the sum (below).

## Sources and what we took from each

<!-- prettier-ignore -->
| Source | What it gives | What we took |
| --- | --- | --- |
| Bradford and Groves, unpublished analysis (Vegetable Entomology Lab, UW–Madison): figure `tmp/cpb/CPB GAM fit - all.png`, predictions `tmp/cpb/cpb_gam_predictions.csv` (2026-11-18) | GAMs (`y ~ s(x, bs = "cs")`, k = 13; egg masses k = 11) of log(count + 1) on degree days 52/86 °F, single sine from January 1, on Pest Pros' field scouting data, 2014–2025; degree days from gridMET's daily minimum and maximum, uncorrected (Ben, 2026-11-18: the published fit stays on gridMET until AgWeather's corrections are published). Adults and larvae per 25 sweeps of a standard net in the canopy; egg masses per 10 plants (per plant in the figure); each a field's mean of several sites on a date. Critical points by local maxima, minima and axis crossings. Predicted values every 10 degree days, 0–2,400; the adults and larvae curve refitted to each date's sum (2026-11-18). Fits by year (`tmp/cpb/CPB GAM fit by year - all.png`): the same pattern each year, with magnitudes that vary | The four curves, to 2,310 (the data end at 2,311) |
| The Crop Risk Tool (`tmp/R/crop-risk-tool/src/models.R`, `cpb`) | A step table of the same analysis, rounded (colonization 200, egg hatch 350, first-generation adult peak 600, larval peak 800, pupation 935, second-generation emergence 1,100 and peak 1,470, …), with severities 1–4, on 50/86 °F | Compared only (below); it was version 0.1 |
| VDIFN's `cpb`, `cpbad` and `cpbl` (`../ag-vdifn/db/seeds.rb`) | Sine-ramped generations on 50/86 °F: total (265, 895, 1115) and (1115, 1375, 2500), adults, larvae | Nothing now; the old page's numbers were these |

## Choices and differences

- **Degree days:** single sine, 52 °F, cutoff 86 °F, from January 1, the analysis's own (the tool and VDIFN ran the same thresholds' events on 50/86, so their events came early).
- **Reading the fits:** linear between the predictions every 10 degree days; a fitted log(count + 1) below 0 (before colonization) is 0; past 2,310, the end of the data, each curve holds its last value until fall freezes end the season (the shared D36 freeze factor, which scales every count).
- **Counts:** each curve back-transformed, exp(fit) − 1, a typical count in the data's units. A mean of log(count + 1) back-transformed is a geometric-type mean, below the arithmetic mean of the counts, so it reads low against a field's average.
- **Risk:** adults and larvae together, as the tool's score was: its count over its curve's peak (6.88 per 25 sweeps at 1,350), Low from 0.05, Moderate from 0.25, High from 0.5, Very high from 0.75 (the D36 defaults). The other three curves are outputs with weight 0.
- **One model, not three:** VDIFN and the Crop Risk Tool split adults and larvae into separate models because of how their engines worked (Ben, 2026-11-18); `colorado-potato-beetle-adults` and `-larvae` are retired.

## Checks

### Against the analysis's own critical points

`packages/agmodels/tests/test_colorado_potato_beetle.py`, run in CI: the critical points found on the predictions the model reads (upward axis crossings, local maxima and minima), against the labels on the analysis's figure, within 10 degree days:

| Curve | Point | Figure | Predictions |
| --- | --- | --- | --- |
| Adults | Colonization | 210 | 210 |
| Adults | First-generation peak | 588 | 590 |
| Adults | Minimum between generations | 957 | 960 |
| Adults | Second-generation peak | 1,477 | 1,480 |
| Adults | Partial third generation | 1,983 | 1,980 |
| Larvae | Egg hatch (the low point before the rise) | 374 | 370 |
| Larvae | Peak | 795 | 790 |
| Adults and larvae | Colonization | 220 | 220 |
| Adults and larvae | First-generation peak | 811 | 810 |
| Adults and larvae | Minimum | 1,038 | 1,040 |
| Adults and larvae | Second-generation peak | 1,354 | 1,350 |
| Egg masses | First eggs | 239 | 240 |
| Egg masses | Peak | 565 (per plant) | 580 (per 10 plants) |

The egg peak moved 15 degree days with the change of count basis, as a refit on a different scale can: log(10x + 1) isn't a fixed multiple of log(x + 1). The adults' curve also has an unlabelled low at 1,880 before the partial third generation.

### Against the Crop Risk Tool on the same weather

The same test, on the tool's 2025 weather for Eau Claire, Wisconsin (`crt_daily_eau_claire_2025.csv`). The tool's step dates (its rounded numbers, on 50/86 °F) against the date our total (52/86 °F) reaches the fit's own value:

| Event | The tool | Ours | Days later |
| --- | --- | --- | --- |
| Colonization | May 12 | May 15 | 3 |
| Egg hatch | May 30 | June 6 | 7 |
| First-generation adult peak | June 17 | June 21 | 4 |
| Larval peak | June 24 | July 1 | 7 |
| Second-generation adult peak | July 25 | August 3 | 9 |

The season's total from January 1 was 2,515 on 52/86 °F against the tool's 2,861 on 50/86 °F. The tool is the system this model replaces, a reference rather than the truth (D54); the differences are the base temperature the tool used.

### Checking the predictions for slips

Ben asked for the predicted values to be checked (2026-11-18). Done on `cpb_gam_predictions.csv`:

- 241 rows, every 10 degree days from 0 to 2,400; no gaps. Every critical point matches the figure (above).
- Values below 0 at both ends (to −0.35 at 0 degree days; egg masses −0.06 at 2,400): a GAM's extrapolation of log(count + 1), which can't be negative. Taken as 0.
- Past 2,311 (the figure's end of season, the data's last total) the predictions are extrapolation; the model stops reading them there.
- **The adults and larvae curve** in the first predictions sat below the adults curve alone and near the average of the two stages' log counts (at 800 degree days 1.35, against 0.89 for adults and 1.80 for larvae, whose counts, 1.4 and 5.0 per 25 sweeps, sum to log(1.4 + 5.0 + 1) = 2.01): the fit of both stages' rows stacked in one column. Ben confirmed it and refitted to each field date's adults plus larvae (2026-11-18). The refitted curve tracks the log of the two curves' counts summed within 0.08 from 220 to 2,310 degree days (810: 2.02 against 2.01; 1,350: 2.06 against 2.00), as a test now holds (within 0.1); it dips up to 0.05 below the adults curve alone between 370 and 470, where larvae are just appearing, which is smoothing. Its peak count is 6.88 per 25 sweeps at 1,350, against 3.19 before.

## Limits and open questions

- **In sample:** the curves are fitted to the data they describe, so these checks show the port, not the prediction. A test needs years or fields the fit didn't use (2026's scouting, or a fit leaving each year out).
- **Years differ in size, not much in timing:** fits by year show the same shape each year, with the earliest years' counts (about 2014–2016) well below later years' at the same degree days. A typical count is a middle value across years, so in a given field and year the counts can run well above or below it; the risk levels, a share of the curve's peak, follow its timing, not a field's numbers.
- **Long Very high spells:** adults and larvae stay near their peak from the first generation through the second (the low between them is 84 % of the peak), so at Eau Claire in 2025 the risk was Very high on 48 days, June 24 to August 10.
- **Typical counts** are geometric-type means and run below fields' average counts; the analysis's scatter shows the spread around them (log counts of 0 to 4 at the same degree days).
- **Fitted on gridMET, run on AgWeather's archive:** the curves' degree days came from gridMET's daily temperatures, the model's from the archive, so a bias between the two moves every event. Not yet measured at the fields' cells; `docs/validation/weather/normals.md` (section 4) shows gridMET's summer maximum within about 1 °F of Wisconsin stations in 2014–2015 at Hancock, and the archive within about 1 °F after (both small against the curves' spread). gridMET's warm 2011–2013 (summer maxima 2–7 °F above stations) fall before the scouting data begin. A refit on the archive's weather is the option once its corrections are published.
- **The fits are for the Central Sands' commercial potato fields** (Pest Pros' clients); other regions and crops (tomato, eggplant) take them on trust.
- Degree days from January 1 for every field, whatever its planting date: colonization depends on when the crop emerges near overwintering sites, which the curves average over.
- **Cheapest independent comparison:** this season's (2026) scouting counts, or a leave-one-year-out refit of the same data, against the curves.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_colorado_potato_beetle.py
```
