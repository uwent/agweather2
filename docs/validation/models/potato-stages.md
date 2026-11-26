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

## Typical planting dates

Written 2026-11-26 with model version 0.2. When a request asks for a typical planting (`planting_date=early|mid|late` at a location, `planting=` on a map), the dates are each grid cell's estimate (`agdata.potatoplanting`): its median last spring freeze at 28 °F over the 30-year normal (`last30`, `freeze_28/spring_p50`, D85), less 7 days for early planting, plus 7 for mid and plus 29 for late. The numbers are the medians, over Veg Path's 120 plantings (`docs/validation/data/vegpath-potato-planting/`), of each planting date less the freeze date at its place's cell. They replace D64's interim rule, the mean dates of the nearest of Veg Path's seven places within 40 km and none beyond, which drew circles on the early and late blight maps (Ben, 2026-11-26).

The dates are climatological: one set per cell for every year. A rule on each year's own soil or air degree days missed Veg Path's dates by 10–12 days (2026-11-03 fit, `tmp/potato/planting.py`), a rule on each place's normal by about 6: a year's planting follows the place's usual spring more than that spring's weather.

### Rules compared at Veg Path's places

`scripts/fit_potato_planting.py` on the development archive (Wisconsin), each place's dates predicted from the other six places' (held out by place); error is the estimate less Veg Path's date:

<!-- prettier-ignore -->
| Rule (each place's cell) | Mean absolute error, days | RMSE, days | Bias, days |
| --- | --- | --- | --- |
| (a) Soil degree days above 0 °C from January 1, 4 cm, the archive's 2016–2025 mean (thresholds 119, 226, 468 °C·d) | 6.2 | 7.7 | −0.5 |
| (b) Air degree days above 32 °F from January 1 (single sine), 30-year normal | 7.4 | 9.2 | −1.2 |
| (b) Air degree days above 39.2 °F from January 1 (average), 30-year normal | 7.5 | 9.5 | −1.4 |
| **Last 28 °F spring freeze, 30-year median, −7, +7, +29 days (chosen)** | **6.7** | **8.3** | **−0.5** |
| Last 32 °F spring freeze, 30-year median | 8.6 | 10.0 | −0.7 |
| Last 28 °F spring freeze, 10-year median | 10.3 | 12.7 | −2.3 |
| Last 32 °F spring freeze, 10-year median | 10.0 | 11.8 | −1.4 |

Soil degree days, the rule the plan named (Phase 6, "Cropland and planting estimates"), fit Wisconsin best, and the 28 °F freeze date is 0.5 days behind. Every rule has the same regional pattern. With the chosen rule, the central sands plant earlier than estimated (Grand Marsh +4.8 days, Hancock +7.0, Plover +1.4) and the north later (Antigo −8.4, Rhinelander −9.2); Spring Green −0.7 and Arlington −3.4. The soil rule's are Grand Marsh +3.4, Hancock +4.7, Plover +4.4, Antigo −8.4 and Rhinelander −7.3. Sandy, irrigated fields that warm and drain early, and the north's later-maturing seed and processing crops, are likely reasons; no rule here knows soil or market.

Ten years' freeze dates are too few for a median (10.0–10.3 days); the 30-year normal's are steadier.

### Outside Wisconsin

The degree-day rules were fitted where the ground freezes all winter. Where it doesn't, winter's warm days add up, and the thresholds come early. `scripts/check_potato_planting_states.py` fits each rule at Veg Path's places and applies it to potato areas in the states NASS's Usual Planting and Harvesting Dates (2010, crop progress 1990–2009) lists in the launch area, on Open-Meteo's ERA5-Land soil and ERA5 air temperatures, 2016–2025 (the development archive covers Wisconsin only). Mid planting against the middle of NASS's "most active" period (15–85 % planted):

<!-- prettier-ignore -->
| Place | NASS most active | Soil degree days | Air degree days | Last 28 °F freeze | Last 32 °F freeze |
| --- | --- | --- | --- | --- | --- |
| Montcalm Co., MI | Apr 24 – May 31 | Apr 21 | Apr 21 | Apr 18 | Apr 23 |
| Sherburne Co., MN (sands) | Apr 25 – May 30 | May 3 | May 1 | Apr 18 | Apr 23 |
| Clay Co., MN (Red River Valley) | Apr 25 – May 30 | May 6 | May 7 | Apr 26 | Apr 30 |
| Walsh Co., ND | May 5 – May 30 | May 9 | May 10 | Apr 29 | Apr 25 |
| Wayne Co., OH | Apr 20 – May 28 | Mar 30 | Mar 29 | Apr 4 | Apr 21 |
| Fayette Co., KY | (none) | Mar 2 (early Feb 9) | Mar 2 (early Feb 14) | Mar 24 (early Mar 10) | Apr 6 (early Mar 24) |
| Jackson Co., IL | (none) | Feb 28 (early Feb 7) | Mar 5 (early Feb 19) | Mar 18 (early Mar 4) | Mar 28 (early Mar 15) |
| Mid less NASS's middle: mean, spread across the 5 places (SD) | | −17, 12.6 | −17, 13.0 | −24, 6.3 | −18, 3.4 |

Veg Path's tiers come earlier than NASS's percentages (in Wisconsin too), so the level of these differences says little; their spread across the states says whether a rule keeps NASS's geography. The degree-day rules put Ohio's mid planting at the end of March, 40 days before NASS's middle where Minnesota's and North Dakota's come 6–12 days before theirs, and plant Kentucky and southern Illinois in February. The freeze dates keep the states in NASS's order and put early planting in Kentucky and southern Illinois in March, as gardeners there plant. That is why the freeze date was chosen over the soil rule, at half a day's cost in Wisconsin. The 32 °F freeze kept NASS's geography best but missed Wisconsin's places by 8.6 days; the 28 °F one still puts Ohio about two weeks early relative to the others. These are point checks on Open-Meteo's weather, not on the 30-year normal the grid reads, and NASS's dates are state-wide and 20 years old.

### Places with dates of their own

Veg Path's published dates aren't used at their places: the estimate is the same rule everywhere, so the map has no seams, and the places are its checks. Blending the places' residuals into the field (a correction fading with distance) was rejected: neighbouring places' residuals differ in sign (Spring Green −0.7 and Arlington −3.4 days, 50–80 km from Grand Marsh's +4.8), so the correction would be local and draw the circles again.

### Map

Early blight's P-days on July 1, 2026 at the mid tier, before (D64's circles) and after: `tmp/w5-potato/` in the main checkout (working material, not committed).

## Limits and open questions

- The fit's dates are estimates; the plans (`docs/plans/`) note that the newsletters' numbers come from the old AgWeather and VDIFN, and whether that includes their emergence dates isn't recorded. If it does, the fit partly reproduces an older model.
- Planting depth, seed size, sprouting before planting and soil moisture all change emergence, and none is an input.
- Only one threshold for all varieties.
- **Cheapest independent comparison:** emergence counted in Wisconsin fields with known planting dates, from potato trials at UW–Madison's Hancock Agricultural Research Station, or from growers' and consultants' records, on the archive at each field's cell.
- **Typical planting dates:** fitted at seven places in one state, to the newsletter's tiers rather than to a share of the area planted. Outside Wisconsin only state-wide NASS dates check them, at points on Open-Meteo's weather. The 28 °F freeze date follows frost pockets, where cold air settles on clear nights (the central sands have many), which may be one reason the sands plant earlier than estimated. The estimate moves by a day or so when the 30-year normal is rebuilt each January; the crop stages stored per tier follow at their next rebuild. The cheapest independent check: NASS's weekly crop progress for potatoes planted in Wisconsin, Minnesota, Michigan and North Dakota (state-wide percentages, 2016–2025), against the estimate averaged over each state's potato cells (the Cropland Data Layer's any-year potato share, D116).

## Reproducing

```bash
uv run python tmp/potato/fit_threshold.py   # needs tmp/potato/dates.csv and weather.json (working material, not committed)
uv run python scripts/fit_potato_planting.py --data-dir data   # typical planting: the rules at Veg Path's places, and the offsets
uv run python scripts/check_potato_planting_states.py           # typical planting outside Wisconsin (Open-Meteo, cached in tmp/potato-states)
```
