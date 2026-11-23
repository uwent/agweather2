# Potato emergence (`potato-stages`): validation

Model version 0.1, written 2026-11-18 (D98). The model: `packages/agmodels/src/agmodels/models/potato_stages.py`, run through `agmodels.crops`; its page: `potato_stages.md` beside it. Built 2026-11-03 (Phase 5, "Potato emergence", `docs/plans/phase-5-api.md`); its predicted emergence starts the early and late blight models when a planting date is given (`biofix_stage`).

**In short:** 50 % emergence at 208 °C·d of air degree days above 4 °C from planting, a threshold fitted to the planting and emergence dates UW Vegetable Pathology's newsletters gave for Wisconsin's potato areas, 2020–2026. Held out by year, it predicts those dates with a mean error of 3.3 days, against 7.5 for a fixed 24 days after planting. The dates it was fitted to are the newsletters' estimates, not field records, and no other data set has tested it.

## Sources and what we took from each

| Source | What it gives | What we took |
| --- | --- | --- |
| UW Vegetable Pathology, Vegetable Crop Updates, 2020–2026 | Each season's early, mid and late planting dates and 50 % emergence dates at Wisconsin's potato areas, in the early and late blight tables | 120 planting and emergence pairs at 7 places (Antigo, Arlington, Grand Marsh, Hancock, Plover, Rhinelander, Spring Green), compiled by Ben Bradford (`tmp/potato/dates.csv`), to fit the threshold |
| Holden et al. 2011, Potato Progress XI(6) (Washington State Potato Commission) | 200–300 heat units above 45 °F in air from planting to emergence for potatoes planted 8 in deep in the Columbia Basin, with 250 as their base value | A check on the fitted threshold's size |

## Choices and differences

- **Degree days:** the daily mean of the maximum and minimum less 4 °C, none below it, in air. Bases from 2 to 7 °C fit about as well, and soil temperature fit no better than air (the plans, `docs/plans/`).
- **Stages:** planting and 50 % emergence only. Tuber initiation and later stages need another source.
- **Gating margin:** 4 days, the fit's held-out RMSE rounded up.
- **Weather for the fit:** Open-Meteo's daily temperatures at each place (`tmp/potato/weather.json`), not the archive.

## Checks

### Against Wisconsin's newsletter dates

`tmp/potato/fit_threshold.py` (working material, not in CI; rerun for this report with the same result): the threshold that minimizes the mean absolute error over the 120 dates (7 places, 2020–2026) is 208 °C·d. Fitted with each year left out in turn and tested on that year:

| | Mean absolute error, days | RMSE, days | Bias, days |
| --- | --- | --- | --- |
| 208 °C·d above 4 °C, held out by year | 3.3 | 4.0 | +0.1 |
| The same, in sample | 3.1 | | |
| A fixed 24 days after planting (the plans, `docs/plans/`) | 7.5 | | |

The newsletters' planting dates come from growers' reports and their emergence dates are estimates, so this measures agreement with Wisconsin's extension estimates, not with counted emergence.

### Against Holden et al.

At a 45 °F base the same dates take about 250 °F·d (the plans, `docs/plans/`), Holden et al.'s (2011) base value within their range of 200–300 for the Columbia Basin.

## Limits and open questions

- The fit's dates are estimates; the plans (`docs/plans/`) note that the newsletters' numbers come from the old AgWeather and VDIFN, and whether that includes their emergence dates isn't recorded. If it does, the fit partly reproduces an older model.
- Planting depth, seed size, sprouting before planting and soil moisture all change emergence, and none is an input.
- Only one threshold for all varieties.
- **Cheapest independent comparison:** emergence counted in Wisconsin fields with known planting dates, from potato trials at UW–Madison's Hancock Agricultural Research Station, or from growers' and consultants' records, on the archive at each field's cell.

## Reproducing

```bash
uv run python tmp/potato/fit_threshold.py   # needs tmp/potato/dates.csv and weather.json (working material, not committed)
```
