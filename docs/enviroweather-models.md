# MSU Enviroweather's models: an inventory

MSU Enviroweather gave us permission (Ben, 2026-11-17) to use the source code of their models as a basis for new AgWeather models; every model page that draws on it credits Enviroweather. This is the first part of PLAN.md Phase 6 step 4: what each folder of their code (`tmp/enviroweather_src/enviroweather-rm-api-master/app/ResultModels/`, PHP, 60 folders) does, what it needs, how it compares with ours, and what to port first. It is a working document for us, not public text.

Written 2026-11-17 from a reading of the code (four parallel readers; the entries below are theirs, the summary and priorities ours). Paths are relative to `tmp/enviroweather_src/enviroweather-rm-api-master/app/` unless stated. Numbers are as the code has them; nothing here has yet been checked against a published source.

## What we found

- **Almost nothing is cited.** The code names people (Phil Schwallier, Bill Shane, Larry Gut, "Keith's document on trello", Jeff Andresen) and two URLs for the degree-day method, and no papers. Every port needs its primary source found and checked first, as CLAUDE.md's rules ask; the code gives the numbers to look for, not the authority for them.
- **Three tables are in MSU's database, not the dump:** the apple scab infection table (`hrsforinf_applescab`, Mills or Revised Mills), the cherry leaf spot table (`hrsforinf_cherryleafspot`), the peach (`peach_variety`) and blueberry (`blueberry_variety`) variety tables, and the cranberry fruitworm egg-laying curve (`oviposition_cranberryfruitworm`). The `database/` folder is empty. Ask MSU for them, or rebuild from the published sources.
- **Degree days:** almost every model uses "Baskerville-Emin" (single sine, horizontal cutoff) with an upper of 212 °F, so in effect single sine with no upper: our `degree_days_sine` with `upper=None`. Most start on a hard-coded March 1 (ours mostly January 1). A missing day adds 0 with no flag, against our gap rules (D45).
- **Wetness:** leaf wetness is measured only (wet at ≥ 0.25 of the hour). Several models already have a sensor-free variant (rain ≥ 0.01 in or RH ≥ 90 %), which our data can run: apple scab, cherry leaf spot, cucurbit downy mildew's table. Fire blight's wetness is rain-based (and user-entered dew), and sooty blotch counts rain hours without a sensor. TOMCAST's RH fallback never runs (a bug, below).
- **Overlap with ours** is in the field and vegetable folders (alfalfa cutting and weevil, Colorado potato beetle, European corn borer, seedcorn maggot, squash vine borer, variegated cutworm, cabbage maggot, TOMCAST, spotted wing drosophila); their thresholds differ from ours in several places (base 52 °F for CPB against our 50; ECB's "rough numbers"; squash vine borer's flight to 2000 DD against our 1000; variegated cutworm's start, March 1 against our May 1). Each difference goes to step 4's comparison and the insect review.
- **Nothing for tree fruit, small fruit, grapes, cranberries or Christmas trees exists in v2**, and those are most of the dump. Our crop list has `cherry` but no `apple`, `blueberry`, `cranberry` or `grape` yet (D93: add them with their models).
- **Winter wheat phenology is a stub** with no thresholds: our wheat gap (D7) stays a research item, not a port.
- **Neither ET folder computes ET:** both read MSU's station reference ET. Crop ET is Kc × reference ET with Kc tables for corn and soybean that are also in the database.
- **Likely bugs** (each in its entry): TOMCAST always uses the canopy sensor and scores wet periods of exactly 21 or 23 hours as 0; apple scab and cherry leaf spot skip the rest of a day after a missing hour without ending the wet period; McIntosh harvest's temperature correction has the opposite sign in one of three sub-models; codling moth's second generation ignores the user's biofix; fire blight lists a trauma infection twice; sooty blotch's rain threshold is 0.01 mm, not inches; crop ET rounds each day to a whole millimetre; tussock moth's biofix overwrites its degree-day total; Colorado potato beetle's generation 2 thresholds disagree with MSU's own table.

## Priorities

Ranked by how much the crop matters in Wisconsin and the Upper Midwest, how much of the model the code gives us, and whether our data can run it. "Port" means ported and checked against its published source, as Phase 3's models were.

<!-- prettier-ignore -->
| Priority | Models | Why |
| --- | --- | --- |
| 1 | Apple phenology, apple scab, fire blight, codling moth | Apples are Wisconsin's largest fruit crop after cranberries; scab and fire blight are the diseases growers spray by; apple phenology feeds scab, fire blight and sooty blotch. Scab needs the Mills table (published), fire blight is MaryBlyt-style and runs on rain. |
| 1 | Cranberry fruitworm | Wisconsin grows most of the US crop. The thresholds are Michigan's (possibly from blueberry) and the egg-laying curve is missing: check against Wisconsin cranberry research before porting. |
| 1 | Tart cherry: cherry phenology, cherry leaf spot, plum curculio, cherry fruitworm | Door County's tart cherries; cherry leaf spot's table is missing (published: Eisensmith and Jones, to verify). |
| 2 | Plum curculio in apple, apple maggot, obliquebanded leafroller, oriental fruit moth, sooty blotch | The rest of an apple IPM program; simple degree-day calendars except sooty blotch (wetness hours). |
| 2 | Grape berry moth | Wisconsin's cold-hardy grapes are a small but growing crop; needs day length (we can compute it). |
| 2 | Christmas trees: Fraser fir growth, Cooley and eastern spruce gall adelgids, pine sawfly and pine needle scale | Wisconsin is a large Christmas tree producer; four simple calendars. |
| 2 | Spongy moth egg hatch (from the landscape insects) | Spongy moth is established across eastern Wisconsin. |
| 3 | Blueberry bloom, gall wasp, maggot, mummy berry, tussock moth; SWD fruit susceptibility in cherry | Blueberries are minor in Wisconsin; the bloom table is missing. |
| 3 | Peach harvest, grape and Concord berry weight, landscape scales and black vine weevil, asparagus miner | Little Wisconsin acreage, or the model looks broken (asparagus miner's curve). |
| Compare | Alfalfa cutting and weevil, Colorado potato beetle, European corn borer, seedcorn maggot, squash vine borer, variegated cutworm, cabbage maggot, TOMCAST | Ours exist: record which thresholds we keep and why, in the insect review. |
| Not a port | Winter wheat (a stub), crop ET (tables missing), cucurbit downy mildew (a weather table; risk comes from spore forecasts) | Research or later features. |

Features the displays suggest that v2 lacks: a frost-night view and alert at saved sites (hourly temperature and dew point at or below 32, 30 and 28 °F); heat index and wind chill; spray conditions (an inversion needs two heights, so it would be a proxy for us: clear, calm evenings); totals over the last 7, 14 and 30 days; rain-hour counts; comparing saved sites side by side; a days-ahead-of-normal map (our `/climate/compare` gives it at points only). Potato heat and moisture and potato graph suggest a potato field stress view (hot days at 88 °F, heavy rain, high ET, warm nights) with the soil moisture step 6 adds.

## Shared code

### Degree days: `Util/GDD/GDDSingle.php` (one day) and `Util/GDD/GDDArray.php` (accumulation and lookups)

`GDDArray::gddAccumulate($dailyArray, $hourlyArray, $dateStart, $dateEnd, $method, $lowerLimit, $upperLimit = 212, $sensorCode, $unitsLimits = 'F', $unitsObs = 'F', $unitsHourlyArray = 'F', $startGdd = 0)` normalizes the method name (GDDArray.php ~440–470):

- **'Baskerville-Emin'** (also 'baskerville emin', 'baskervilleemin', 'BE') → `GDDSingle::fnGDD_BaskervilleEmin` (GDDSingle.php ~205–290). Single sine through daily min and max, with a **horizontal** upper cutoff: if tmax ≤ base → 0; if tmin ≥ upper → upper − base; if tmax > upper the area above the upper threshold (same sine formula with the upper as base) is subtracted; if tmin ≥ base → tavg − base; otherwise the standard sine integral `(w·cos(a) − (base − tavg)(π/2 − a))/π`, `a = asin((base − tavg)/w)`, `π = 3.1415927`. Each intermediate area and the result rounded to 0.1. Comment cites `http://agbioresearch.msu.edu/nwmihort/be_method.pdf` (changed 8/27/2012 from an atan form). Swaps min/max if reversed. Same as our `degree_days_sine`.
- **'average'/'avg'** → `fnGDD_Average`: caps **tmax** at the upper threshold before averaging (tmin not raised to base), then `max(tavg, …)`: 0 if tavg < base, else tavg − base, rounded 0.1. Not the textbook simple average (the tmax cap changes the mean).
- **'8650'** → `fnGDD_8650`: tmax capped at 86 °F, tmin raised to 50 °F, then the average method (°F only). Calls `fnGDD_Average($tMin, $tMax, …)` with arguments swapped; `FlipMinMax` rescues it.
- **'NI'** (numerical integration, hourly) → `fnGDD_NumericalIntegration`: mean over the day's hours of `min(T, upper) − base` for T > base (hours 1–24, hour stamp = end of hour). Used only for past days with all 24 hours (23 on the DST start day, `fnEnoughHourlyTempData`); otherwise falls back to Baskerville-Emin from daily min/max. Today: the larger of NI-so-far and BE (with forecast max/min). Future days: BE.
- **'GDH'** (degree hours) → NI × number of hours; without full hours, `fnDH65FromDailyMinMax` (Joe Merillat's code, base 65 °F with a 90 °F cutoff hard-coded, rounding to whole degrees inside, ×24). Today: the larger of the two.
- Units: limits in `$unitsLimits`; observations converted (`fnConvertCtoF`, rounded to 2 decimals) before the method runs. Every model in this batch passes base in °F with daily data in °C (`'F', 'C', 'C'`).
- **Upper threshold**: default 212 °F (100 °C) = none; any upper ≤ base is silently replaced by 212/100. Every model in this batch passes 212 (no upper threshold).
- **Missing days** (daily path): if min or max is null, `single = null`, the date goes into `missingArray`, and `accum` carries the previous day's value forward, i.e. the day counts as **0 DD** with no estimate. A date absent from the daily array gets `single = accum = null` and is skipped (`continue`), which breaks the running sum: the next day's `accum` = null + single = single (PHP null arithmetic), so **a missing row resets the running total** while a row with null temps does not (in practice the cleaned daily array probably lists every date, `Util::ListEveryDate`, so the null-temps path is the usual one). Estimated values are not computed here: station gaps arrive pre-filled from the QC database (`mawndb_qc`, flagged by `*_src`, e.g. 'RTMA'; `Util::fnIsEstimateFlag` treats any source other than mawn/user/empty as an estimate), and the array only records `estimatedArray`/`userDataArray` and `accum_src` ('mawn', 'RTMA' if any earlier day was missing or estimated, 'user').
- Days from Jan 1 to the start date are filled with nulls so the array is indexed from Jan 1. Each day's accum is rounded to 0.1.

Lookups (GDDArray.php 28–200):

- **`gddGetDateMatch($arr, $goal, $start, $end)`**: walks from `$start` (inclusive) to `$end`, summing `single` (missing days add nothing), and returns the **first date on which the running sum ≥ goal**, or null if not reached by `$end`. A goal of 0 returns the start date itself. If start = end, returns the date only if goal === 0. `$end` defaults to Dec 31. In every model `$end` = `dateEndWeather`, which includes the forecast, so a "date" can be a forecast date; null displays as "After m/d/Y" or "Out of forecast".
- **`gddGetDiff($arr, $start, $end)`**: `accum[end] − accum[start − 1]` (0 if the day before has no accum), i.e. **inclusive of the start day**; null if `accum[end]` isn't set. Used for "% complete" status lines.
- `gddGetAverageAcrossGddArrays`: averages several stations' or years' arrays (regional/historical views); not used in this batch.

### DDMark and DD notes: `ResultModelsCore/DDMark/DDMark.php`, `ResultModelsCore/Strategy/StrategyBase.php` 353–410

- `DDMark` is a plain record: `base`, `baseUnits`, `method`, `date`, `dateStart`, `dd_goal`, `display`. For a predicted event `dd_goal` is the threshold and `date` is `gddGetDateMatch`'s answer; for a status mark `dd_goal` holds the DD accumulated to `date`.
- `CalculateDDNotes($arr, $start, …)`: if the weather reaches today or later, **selectDate = yesterday** and **forecastDate = last weather date** (end of forecast); otherwise selectDate = last weather date and no forecast mark. Each mark's DD = `round(gddGetDiff(arr, start, date), 0)`. Most models then use the forecast mark (or the select mark when there is none) as `DDMarkEnd` to phrase each event as past, expected or not yet.
- `models_with_multiple_start_dates.txt` (in `ResultModels/`) lists codling moth, alfalfa weevil (?), oriental fruit moth and tussock moth as the models with several accumulation starts; none in this batch.

### Dates and accumulation starts

- Accumulation starts are fixed strings joined to the year of the **last weather date** (`new Carbon('3/1/'.$this->dateEndWeather->format('Y'))`), so a run always covers one calendar year. `CheckDateStartAccumulation` throws "This model is available after m/d." when the start is after the last weather date.
- Biofix models use a user date if given, else an estimated date from a sub-strategy (`gddGetDateMatch` from a fixed Jan 1/Feb 1/Mar 1 start). If neither exists, `ThrowDetailedBiofixDateException` reports the DD so far.
- `TrimByDateTime` trims the shared input weather in place (`DailyData->TrimByDateTime` "modifies original"); sub-strategies get `clone($this->input)`, a shallow copy, so trims can leak between parent and child.
- Hourly arrays are keyed date → hour 1–24, the hour being the end of the period.

### Forecast and today: `WeatherFormatter/EnviroweatherWeatherFormatter.php`

- Daily forecast: air temperature 7 days (today + 6), precipitation 3 days (`numberOfForecastDaysAvailable_atmp = 7`, `_pcpn = 3`, lines 46–50); a run whose select date is today extends to today + 6.
- Today's min and max (lines ~700–750): start from the forecast; the observed 5-minute min replaces it after 8 a.m. local (`HourToReplaceMinAtmp = 8`) or whenever it is lower; the observed max replaces it after 8 p.m. (`HourToReplaceMaxAtmp = 20`) or whenever it is higher. Today's precipitation = the larger of the observed sum and the forecast. User overrides win.
- `Util/Temperature/Temperature.php` `ChooseTodayMinTemperature`/`ChooseTodayMaxTemperature` are empty stubs restating that rule.

### Leaf wetness: `Util/LeafWetness/LeafWetness.php`, `Util/Validation/Validation.php` 405–445

- **Measured only; nothing is estimated.** Hourly sensor values are fraction of the hour wet (valid 0–1.1); an hour is wet if ≥ 0.25 (`fnLWWetHour`). Five-minute values: resistance-grid sensors `leaf0`/`leaf1` are wet when −100 < value < 5000; Decagon `lws*` sensors are wet when ≥ 280 (valid ≥ 250). `CountHoursOfLeafWetness` returns null if any hour lacks the column or more than half the hours are missing.
- Wet-period models (apple scab, cherry leaf spot) combine this with rain and RH in `ResultModels/AppleScab/AppleScabWetPeriod.php` (see CherryLeafSpot below): an hour is wet if leaf wetness ≥ 0.25 **or** hourly rain ≥ 0.01 in (0.254 mm) **or** RH ≥ 90 %. With no sensor (`sensorName = null`) only rain and RH count, which is the version we can reproduce.

### Day length: `Util/SolarRadiation/SolarRadiation.php`

- `calcDayLength(date, latitude)`: FAO-56 eqs. 24, 25, 34 (astronomical day length, no twilight): δ = 0.409 sin(2π J/365 − 1.39), ωs = acos(−tan φ tan δ), N = 24 ωs/π. Used by grape berry moth.

### From the other readings

- **"Baskerville-Emin" (BE)** is `Util/GDD/GDDSingle.php::fnGDD_BaskervilleEmin` (lines 212–326): single sine from daily min/max with a horizontal cutoff, each day rounded to 0.1. Every call here passes an upper limit of 212 °F, i.e. no upper threshold. Our `degree_days_sine(min, max, base)` is the same method.
- **"Numerical Integration" (NI)** is the hourly method (`GDDSingle::fnGDD_NumericalIntegration`): mean over the day's hours of max(0, T − base), falling back to BE from daily min/max for days without enough hourly data and for future (forecast) days. **"GDH"** is NI × number of hourly records = degree-hours, with `fnDH65FromDailyMinMax` ("from Joe Merillat's code") as the daily fallback; on the current day it takes the larger of the two.
- **Dates from a DD target:** `GDDArray::gddGetDateMatch` (lines 30–86) sums daily values from the start date inclusive and returns the first day the sum is ≥ the goal. Missing days are skipped (counted as 0), so a gap delays an event silently.
- Data are stored metric (°C, mm); the code converts to °F/inches where thresholds are imperial.
- `CalculateDDNotes` (StrategyBase lines 353–410) reports DD accumulated to yesterday and to the end of the forecast; it shapes the display only.
- Wetness sensors: hourly `lws0_pwet` (standard sensor) and `lws1_pwet` (canopy sensor), each the fraction of the hour wet; a sensor hour is "wet" at ≥ 0.25 (`Util/LeafWetness::fnLWWetHour`). We have no measured leaf wetness.
- Several tables live in MSU's Postgres database and are **not in the dump**: `hrsforinf_applescab` (the Mills table), `hrsforinf_cherryleafspot`, `peach_variety`. The `database/` folder is empty. We would need to ask MSU for them.
- **'average'** (`fnGDD_Average`, 326–403): caps Tmax at the upper threshold, then (Tmax + Tmin)/2 − base, floored at 0. Tmin is not raised to the base. With upper 212 this is a plain average.
- **'8650'** (`fnGDD_8650`, 405–435): Tmax capped at 86 °F and Tmin raised to 50 °F, then average − 50 (the standard corn GDD method).

## Tree fruit (apple, tart cherry, peach)

### ApplePhenology: apple bud stages, bloom, petal fall and apple maturity (harvest date)

- **Predicts:** (1) the date of each apple bud stage from dormant through ninth cover spray; (2) McIntosh green tip, bloom start and end, petal fall, and McIntosh / Jonathan / Red Delicious bloom, as defaults ("biofixes") for other models; (3) **Apple Maturity**: the expected peak harvest date of McIntosh, Jonathan and Red Delicious from their bloom date and post-bloom temperatures.
- **Crop and pest:** apple; crop development and harvest timing.
- **Inputs:** daily min/max air temperature from January 1 (**have**). Maturity: user bloom dates for McIntosh, Jonathan and Red Delicious (`macBloom`, `jonBloom`, `redBloom`; **user input at points**), else the DD estimates; at least 30 days of data after McIntosh bloom and 15 after Jonathan/Red Delicious bloom.
- **Method:**
  - Phenology (`ApplePhenologyStrategy.php`): DD base 42 °F, BE, no upper, from the first date of the weather supplied, which the comment says must be January 1 ("required date collection - must contain 1/1"). Stage = first day the sum reaches (DD42 °F from Jan 1): Dormant 90; First green 127; 1/4" green 189; 1/2" green 205; Tight cluster 242; Open cluster 284; Pink 367; King bloom 395; Full bloom 422; Petal fall 511; First cover 749; Second 1061; Third 1405; Fourth 1759; Fifth 2167; Sixth 2552; Seventh 2916; Eighth 3261; Ninth cover 3545. Other marks: McIntosh green tip 110; McIntosh bloom 422; Jonathan bloom 440; Red Delicious bloom 450. Outputs a stage table, the last stage reached and the next one.
  - `McIntoshGreenTipStrategy` returns the 110 DD mark (biofix for AppleScab). `PetalFallStrategy` returns the 511 mark (biofix for SootyBlotchEvents). `AppleBloomStrategy` returns **bloom start = Pink (367)** and **bloom end = First cover (749)** (biofix for FireBlight). `AppleMaturityBloomStrategy` returns the three variety bloom marks.
  - Apple maturity (`AppleMaturityStrategy.php`, lines 294–458 McIntosh, 460–549 Jonathan/Red Delicious): daily mean = (min+max)/2, converted to °F and rounded to 0.1.
    - McIntosh is the mean of three day-of-year estimates, each counted from McIntosh bloom B (loops run B to B+n−1, days with data only):
      - Model 1: x = round(mean of the 15 daily means − 50); harvest = B + 120 **+** x.
      - Model 2: c = round(−0.057 × Σ over 21 days of (mean − 40), 1); harvest = B + 144 + round(c + 0.5) (the code adds 0.5 "because we can't add 144.5").
      - Model 3: harvest = B + 226 + round(−0.057 × Σ of the 30 daily means); with fewer than 30 days of data the missing days are filled with the mean of those present.
      - An estimate that falls in the next year is dropped. The rest are averaged by day of year and rounded.
    - Jonathan: harvest = B_jon + 137 − round(mean of 15 daily **minimums** (°F) − 50). Red Delicious: B_red + 143 − the same with its own bloom date. In the comments: "7/1/2011 - Back to average of mins per Phil Schwallier"; "1 day per F degree difference between the ave MIN Temp of the 15 days following Full Bloom and 50 degrees".
    - Output: a table of variety, bloom date used and estimated harvest date.
- **Source:** None cited for the stage DDs. Maturity: comments name Phil Schwallier (MSU Extension) and give the 2008 and 2011 changes; there's no publication. BE method URL: `http://agbioresearch.msu.edu/nwmihort/be_method.pdf` (GDDSingle.php). Upper-cutoff concept: `http://www.ipm.ucdavis.edu/WEATHER/ddconcepts.html#Cutoff` (GDDArray.php).
- **Overlap with ours:** none (no apple crop in `agmodels.croplist`). `custom-degree-days` can reproduce the DD42 marks. Our `chill` module (Utah, dynamic) covers dormancy, not these stages.
- **Notes:**
  - McIntosh Model 1 **adds** x (warmer after bloom → later harvest). Models 2 and 3 and the Jonathan/Red Delicious formulas all make warmer → earlier. The comment shows the sign was changed on purpose in 2008 ("Add iBloomDay + 120 - x" → "+ x") along with a switch from a 30-day min to a 15-day mean. It's still counterintuitive: check it with MSU before porting. With a 15-day mean of 60 °F the three give about B+130, B+121 and B+123.
  - Model 3's coefficient was changed from −0.058 to −0.057 (2008).
  - "Full bloom" and "McIntosh bloom" are both 422. The dormant mark (90 DD after Jan 1) is odd as a stage.
  - Bloom end for fire blight is First cover (749), not Petal fall (511), so blossom-blight risk runs about 240 DD42 past petal fall. That's conservative, perhaps on purpose for late or rattail bloom, but not stated.
  - The start date is whatever the weather request begins with; the code doesn't force January 1.
  - Missing days count as 0 DD (they delay stages). In maturity, missing days are left out of the means, and Model 3 fills them with the mean.
  - Day-of-year arithmetic uses PHP `format('z')` (0-based) added back to Jan 1, so it's consistent. The `array_filter(…,'strlen')` would drop a 0 DOY, which can't occur.
- **Upper Midwest relevance:** high. Apple is Michigan's largest fruit crop (third US state) and grown commercially in Wisconsin and Minnesota (a few thousand acres each). This model is the base for every apple model below.

### AppleScab: apple scab infection periods (Mills-type), ascospore maturity and discharge, symptom dates

- **Predicts:** each wetting period after McIntosh green tip with its apple scab infection risk (None, Light, Moderate, Heavy), the expected date symptoms appear, and the percent of the season's ascospores matured and discharged. A regional view gives each station's most recent wetting event in the last 14 days.
- **Crop and pest:** apple; apple scab (*Venturia inaequalis*), primary (ascospore) season.
- **Inputs:**
  - Hourly air temperature (**have**), hourly precipitation (**have**) and hourly RH (**have**).
  - Hourly leaf wetness from the standard and canopy sensors (**missing**). The model also runs a "no leaf wetness sensor" version from rain and RH ≥ 90 % alone, which we can run as is. **Proxy:** RH ≥ 90 % hours, the same as MSU's own no-sensor table.
  - Daily min/max for the spore and green tip DD (**have**).
  - User input: McIntosh green tip date (`gtStart`), else 110 DD42 BE from Jan 1.
- **Method:**
  - **Wet hour** (`AppleScabWetPeriod.php` 17–19, 188–212): an hour is wet if the leaf wetness sensor fraction is ≥ 0.25, **or** precipitation is ≥ 0.01 in (0.254 mm), **or** RH is ≥ 90 %. Three versions are run: standard sensor, canopy sensor, and none (`sensorName = null`, so rain or RH only). The table shown first uses the standard sensor (`Table`), then canopy (`Table_2`), then none (`Table_3`). The dashboard shows the no-sensor version only when neither sensor has events.
  - **Wet period** (`AppleScabEventsStrategy.php` 184–275, `AppleScabWetPeriod.php` 83–186, 228–277):
    - A period can start only at a **raining hour** (≥ 0.01 in) after green tip and after the previous period ended.
    - From there, each wet hour adds 1 to `numWetHours`, adds its temperature to the total and adds the hour's Mills increment to an accumulator. Dry hours add nothing.
    - The period ends after **8 consecutive dry hours**. A dry spell under 8 hours is bridged: the wet hours on either side are summed, and the span (`numRecHours`) includes the bridged dry hours but not the final 8.
    - A period still wet at the end of the data is shown as "ongoing".
    - Average temperature is over wet hours only.
  - **Infection table** (DB table `hrsforinf_applescab`, columns `mintempf`, `maxtempf`, `devinc`, `hrslow`, `hrsmod`, `hrshigh`; **not in the dump**). Lookup is `mintempf ≤ T < maxtempf` in °F (`AppleScabWetPeriod.php` 566–579). The per-hour increment `devinc` (presumably 1/hours needed for a light infection at that temperature) accumulates over wet hours.
  - **Risk** (lines 440–485):
    - If the accumulator is < 0.95: None.
    - Otherwise, at the period's average wet-hour temperature: wet hours ≥ `hrshigh` → Heavy, else ≥ `hrsmod` → Moderate, else ≥ `hrslow` → Light, else Light anyway (because the accumulator reached 0.95).
    - If the average temperature isn't in the table: None.
    - Outputs per event: start and end, wet hours, span, average temperature (°F), rain (in), risk, `hrslow` at the average temperature ("wet hours at avg temp needed"), and progress = accumulator as a percent.
  - **Symptom date** (lines 816–898): 330 DD base 32 °F by NI (hourly) from the event's start date. Past the end of data, the date is extrapolated at the mean daily DD of the last 3 days. If that's more than 30 days out, or in the next year, it shows "after <last date>". Only events with risk other than None get one.
  - **Spores** (`AppleScabSporesStrategy.php` 223–283): DD32 °F BE from McIntosh green tip (user or 110 DD42 estimate).
    - Maturity (named "Gadoury" in the code): probit = 2.51 + 0.01 × (DD32F / 1.8), i.e. DD °C base 0. Percent = 100 × Φ(probit − 5), forced to 100 % at ≥ 950 DD32F.
    - Discharge (named "Jones"): logit = −25.33 + 3.934 × ln(DD32F), using **°F** DD, not converted. Percent = 100 × e^logit / (1 + e^logit), forced to 100 % at ≥ 2050 DD32F.
    - Shown as "% spores matured / dispersed" at yesterday and at the forecast end, plus dates for 100 % matured (950) and 100 % dispersed (2050).
- **Source:** None cited in a comment. The function name `AppleScabSpores_GadouryJones` points to Gadoury & MacHardy's ascospore maturity model (the probit 2.51 + 0.01·DD°C matches Gadoury & MacHardy 1982, *Phytopathology* 72) and a Jones et al. discharge curve. The table name `HrsForInf` and the Light/Moderate/Heavy scheme are the Mills (1944) table or MacHardy & Gadoury's (1989) Revised Mills; which one is in the database is unknown. 330 DD32F to symptoms isn't attributed. **Verify each against its source.**
- **Overlap with ours:** none for apple. Closest in structure: `late-blight-dsv` (Wallin) and `carrot-foliar-dsv` (TOMCAST) build wet periods from RH ≥ 90 % hours with temperature during wetness. Our RH ≥ 90 % proxy matches this model's own no-sensor wetness rule.
- **Notes:**
  - **The Mills table itself is missing**, so the infection thresholds can't be ported from the dump. Ask MSU for `hrsforinf_applescab`, or rebuild it from MacHardy & Gadoury (1989) or Stensvand et al. (1997) and record which.
  - A period must start with rain ≥ 0.01 in. A dew- or RH-only wet period never starts an event, but RH ≥ 90 % and dew hours extend one.
  - Bridging dry gaps of up to 7 hours is close to the Revised Mills rule on interrupted wet periods. Check that against the source.
  - **Gap bug:** in the period loop (`AppleScabWetPeriod.php` 125–144), a missing hour `break`s out of the rest of that **day**, so one missing hour skips the remaining hours of the day without ending the period.
  - A wet hour with missing temperature adds 0 °C to the total but still counts in `numWetHours`, which biases the average temperature low (line 240).
  - `FormatEventAsPredictionEvent` tests `if ($i)`, so the 'None' category (index 0) falls through to the raw text. That's cosmetic.
  - The constructor sets the start to `startHour − 1` with the comment "this works when start is hour = 24 but problems otherwise??? check linwood 6/1/2020".
  - The dispersal curve takes ln of **°F** DD while maturity converts to °C. That may be correct (each regression's own units), but confirm it.
  - The forced 100 % at 950 and 2050 DD were "added April 2021 to end calculation".
  - The class carries a cherry leaf spot variant (`hrsforinf_cherryleafspot`, risk Low/Moderate/High) and a stub for black rot. Neither is used here.
- **Upper Midwest relevance:** high. Apple scab is the main fungicide target in every Upper Midwest orchard. It's the top fruit disease model to port, and our RH and rain hours already match its no-sensor rule.

### FireBlight: fire blight blossom and trauma blight risk (MaryBlyt-style BHWT with EIP)

- **Predicts:** for each day from bloom start: the Epiphytic Infection Potential (EIP), the four factors B (blossoms open), H (EIP ≥ 100), W (wetting) and T (mean temperature ≥ 60 °F), a risk level, infection days (blossom or trauma), and the date symptoms are expected (103 DD55 °F after infection) with progress toward it.
- **Crop and pest:** apple (blossom life is set "for apples"); fire blight (*Erwinia amylovora*).
- **Inputs:**
  - Daily min/max (**have**) and hourly temperature (**have**; for DD40, DD55 and degree-hours above 65 °F).
  - Daily precipitation (**have**).
  - Hourly leaf wetness is only **displayed** (hours ≥ 0.25 per day), **not used** in W.
  - User inputs per day (**user input at points**): bloom start and end (else the Pink and First cover estimates); dew/fog/spray (any non-empty value counts as wet); bactericide applied ('Yes' resets EIP accumulation); trauma (hail, wind, pruning; 'Yes').
  - The model needs daily data for the 3 days before bloom start.
- **Method:**
  - Main loop: `FireBlightInteractiveStrategy.php` 279–432. Factors: lines 1181–1318. EIP: `EIPCalculator.php` 19–162.
  - DD arrays from bloom start: DD40 °F NI (hourly), DD55 °F NI, and degree-hours above 65 °F (GDH).
  - **EIP** for day d:
    - The window starts at bloom start, or at the last bactericide day. It's then moved later to the day where DD40, summed backward from d, first reaches **80** (`blossomlife`, "for apples"), so only the last ~80 DD40 of blossoms count.
    - Over the window, `cumeGDH` accumulates daily degree-hours >65 °F (`GDH65`) with carry-over rules applied each day while `cumeGDH < 400`:
      - Today's max < 65 °F and yesterday's ≥ 65: carry 2/3.
      - Today's and yesterday's max < 65, the day before ≥ 65: carry 1/2.
      - Three days with max < 65: carry 0.
      - Otherwise: carry all.
      - Any day with min ≤ 32 °F resets the total to 0.
    - Then cumeGDH = carry + today's DH65, and **EIP = round(cumeGDH / 1.95)**.
  - **Factors** (bloom days only):
    - B is always true.
    - H: EIP ≥ 100.
    - W: today's rain ≥ 0.01 in, or user dew/fog/spray, or yesterday's rain ≥ 0.10 in.
    - T: daily mean ≥ 60 °F. The mean is the hourly mean, falling back to (min+max)/2; if max < 60 it's false.
  - **Risk:**
    - Trauma 'Yes' on a day **and** EIP has reached ≥ 100 at any time so far this season → "Infection (trauma)". This applies after bloom too, where EIP keeps being computed only until it first reaches 100.
    - Otherwise the count of true factors gives the risk: 0 None, 1 Low, 2 Medium, 3 High, 4 "Infection (bloom)". Outside bloom, the risk is None.
  - **Symptoms:** each infection's end = first day DD55 (NI, summed from the infection day inclusive) ≥ **103**. Daily progress is shown as percent "(infected on m/d)".
  - **Outputs:** a daily table (min, max, mean, rain, dew/fog/spray, leaf wetness hours, DD40, DD55, DH65, EIP, bactericide, trauma, B/H/W/T, symptoms, risk). The dashboard shows 4 past and 2 forecast days during bloom, and the list of infections after bloom ends.
- **Source:** None cited. The design is Steiner's MaryBlyt (BHWT factors, EIP, 80 DD40 blossom life, 103 DD55 °F to symptoms), but it isn't named. The comments name Bill Shane (MSU): "Per Bill Shane 4/27/18 - Do not use this option!" (returning null outside the blossom range). Verify EIP's divisor (1.95 for °F degree-hours), the 400 cutoff and the 2/3 and 1/2 cold-day carry-overs against the MaryBlyt manual (Steiner & Lightner).
- **Overlap with ours:** none.
- **Notes:**
  - **W doesn't use RH or leaf wetness.** It's rain, yesterday's ≥ 0.10 in, or the user's dew/fog/spray entry. We can run it as is; an RH or dew proxy would be a deliberate change.
  - B is always true in bloom, so risk is never "None" during bloom (at least Low).
  - Bloom start = Pink (367 DD42), not first or king bloom (395), and end = First cover (749).
  - **Probable bug:** a trauma infection during bloom is added twice to `InfectionArray`, once in the bloom block (lines 385–388) and again in the general block (416–421), which compares the risk to `InfectionCategories[5]['display']`. That string equals the risk value, so the comparison is true.
  - The DH65 column's pop-up says "Degree Hours Base 40F" (line 687), a text slip.
  - EIP's 1.95 divisor: if MaryBlyt's EIP 100 is 198 degree-hours °C above 18.3 °C, the °F divisor would be about 3.56, so check the source's units.
  - `gddGetDateMatch_reverse` returns `false`, not null, when the window is shorter than 80 DD40, which is handled correctly by truthiness.
  - On days where the user changed temperatures, hourly temperature is blanked so DD fall back to daily min/max (lines 281–314).
  - A missing day of daily data inside the EIP window throws an exception ("Missing weather data for m/d").
  - The minimum allowed bloom date is January 4.
- **Upper Midwest relevance:** high for apple (and pear) in Michigan, Wisconsin and Minnesota. Fire blight is the most damaging bacterial disease of apple in the region, and the streptomycin-timing decision depends on it.

### SootyBlotchEvents: sooty blotch and flyspeck wetness-hour accumulation

- **Predicts:** wetting events from 10 days after petal fall and the season's running total of wet hours. Risk is flagged (red) once the total passes **240 wet hours** with no fungicide, or 240 wet hours after the fungicide has been washed off by 2 in of rain.
- **Crop and pest:** apple; sooty blotch and flyspeck (SBFS) fungal complex.
- **Inputs:**
  - Hourly precipitation (**have**).
  - Hourly leaf wetness, standard and canopy (**missing**). The no-sensor version uses rain only. **Proxy:** none in the code. RH ≥ 90 % hours would be our choice, but it isn't what MSU's no-sensor version does.
  - User input: petal fall date (else 511 DD42 from Jan 1) and the date of the last fungicide (must be after petal fall).
- **Method** (`SootyBlotchEventsStrategy.php` 237–446):
  - A wet hour is precipitation **> 0.01 mm** (`PcpnThreshold = 0.01; //already in mm`), or leaf wetness > 0.25.
  - Counting begins on days **after** petal fall + 10 days (`theDate > datePetalFallPlus10`, so from the 11th day).
  - Consecutive wet hours form an event. Events of **4 or more** hours count toward the season total; shorter runs are subtracted back out. A single dry hour ends an event.
  - After the fungicide date, rain is summed from wet hours. Once it exceeds **2 in** (50.8 mm, the washoff threshold), later wet hours count toward "wet hours after washoff".
  - **Flag rule:** season total > 240 and no fungicide; or total > 240 and the event started before the fungicide date; or wet hours after washoff > 240.
  - Outputs per event: start and end, hours, season total since PF+10, rainfall since petal fall, and rainfall and wet hours after fungicide. Three tables (standard, canopy, none).
- **Source:** None cited. The footnote says "Days/spans starting 10 days past petal fall with a minimum of 4 hours continuous wetness are included." It's in the line of Brown & Sutton's SBFS warning system (≥ 4 h leaf wetness periods accumulated from 10 days after petal fall, fungicide washoff by 2 in of rain), but the code names no paper, and the 240-hour threshold differs from the 175–200+ hours usually published. Verify.
- **Overlap with ours:** none.
- **Notes:**
  - **Likely unit slip:** the rain threshold is 0.01 **mm** while the other models in these folders use 0.01 **in** (0.254 mm). With hourly data in mm, any non-zero rain counts. Check the intent.
  - Without a sensor, wetness is rain only. Dew periods, the main driver of SBFS in the published model, are missed, so the no-sensor version undercounts badly. We'd need an RH or dew-point-depression proxy, and the threshold would need recalibrating.
  - Rain between the fungicide and PF+10 isn't counted toward washoff (accumulation happens only inside the wet-hour branch after PF+10).
  - The dashboard picks the last event with `if ($index)`, which skips the case where there's exactly one event (index 0).
  - The header comment says this version finds the washoff **hour**, unlike the old version's day, "slightly lower" wet hours than before.
- **Upper Midwest relevance:** moderate. SBFS is a summer cosmetic disease of apples in humid Midwest orchards (Wisconsin, Michigan, Iowa), important for fresh-market growers and for timing late-season fungicides.

### CodlingMoth: codling moth generation timing

- **Predicts:** dates of the first-generation egg laying, first hatch, 20 % hatch and peak egg laying (from biofix), and the second-generation first adults, egg laying, first hatch, peak adults and peak egg laying (from March 1). Treatment timings are marked with an asterisk. Also an estimated biofix (sustained catch).
- **Crop and pest:** apple (and pear); codling moth (*Cydia pomonella*).
- **Inputs:** daily min/max (**have**). User input: biofix = first sustained trap catch (`biofix`), else the estimate (**missing** trap data; **user input at points**).
- **Method:**
  - DD base **50 °F**, BE, no upper, accumulated from **March 1**.
  - Biofix estimate (`CodlingMothSustainedCatchStrategy.php`): **200 DD50 from March 1**.
  - After biofix (DD50 summed from the biofix day inclusive): Gen 1 egg laying starts 100*; first eggs hatch 250*; 20 % egg hatch 350; peak egg laying 550.
  - **From March 1** (not from biofix): Gen 2 first adults 1060; egg laying starts 1160*; first eggs hatch 1250*; peak adults 1600; peak egg laying 1700.
  - (* = "typical treatment timing".)
  - The table highlights the current row. DD notes show DD since biofix until 550 is passed, then DD since March 1.
- **Source:** None cited. A comment: "DDGoal_EggHatchComplete; about 800 to 1000 - Beth confirming with Larry Gut" (Larry Gut, MSU entomology).
- **Overlap with ours:** none.
- **Notes:**
  - The **mixed reference** (Gen 1 from biofix, Gen 2 from March 1) means a user's biofix moves only the Gen 1 dates, which is odd if biofix is the point of the model. Check whether MSU meant Gen 2 from biofix (1060 from Mar 1 ≈ 860 after a 200-DD biofix).
  - The comment "//550 dd from 3/1" at the check is wrong (it's since biofix).
  - `models_with_multiple_start_dates.txt` lists codling moth as a multiple-start-date model.
  - There's no end-of-hatch mark (commented out).
- **Upper Midwest relevance:** high. Codling moth is the key internal fruit-feeding pest of apple in Michigan, Wisconsin and Minnesota.

### OrientalFruitMoth: oriental fruit moth generation timing

- **Predicts:** estimated biofix 1 and biofix 2 (sustained moth catch of the first and second flights), then generation 1–3 egg laying and peak adult emergence windows with treatment timings.
- **Crop and pest:** peach and apple (also tart cherry); oriental fruit moth (*Grapholita molesta*).
- **Inputs:** daily min/max (**have**). User input: biofix 1 and biofix 2 (sustained catch), else the estimates (**user input at points**). Biofix 2 is optional; without it, the later rows are blank.
- **Method:**
  - DD base **45 °F**, BE, no upper.
  - Biofix estimates from **March 1**: biofix 1 = 175 DD45, biofix 2 = 950 DD45 (`OrientalFruitMothAdultEmergenceStrategy.php`).
  - After biofix 1 (DD45 from biofix 1, inclusive): Gen 1 first eggs laid 75; peak adult emergence 150–250* (shown as a range); peak egg laying 350.
  - After biofix 2 (DD45 from biofix 2): Gen 2 peak adult emergence 150–250*; peak egg laying 350; Gen 3 first adults 950; Gen 3 peak adult emergence 1125–1250*.
  - The marks after biofix 2 were changed "1/7/2020 ... per Keith's document on trello". The old values, commented out, were 475, 550 and 950.
- **Source:** None cited beyond "Keith's document on trello" (presumably an MSU entomologist).
- **Overlap with ours:** none.
- **Notes:**
  - The comment in the biofix file says "this model is odd - uses April 1, not March 1 for start of accumulation", but the code uses **March 1** (`StartAccumulation = '3/1/'`). One of them is wrong: check with MSU.
  - Stage labels say "Generation 1: First eggs laid" for the mark after the first flight, an inconsistent generation numbering (the flight is called biofix 1, its eggs "generation 1", its adults "generation 1 peak").
  - Listed in `models_with_multiple_start_dates.txt`.
- **Upper Midwest relevance:** moderate to low. It's a pest of peach and apple in southwest Michigan; minor in Wisconsin and Minnesota, where peaches are scarce, though it does reach apples.

### PlumCurculio: plum curculio control timing in tart cherry

- **Predicts:** the start of the plum curculio control period in tart cherry, 375 DD50 °F after tart cherry (Montmorency) full bloom.
- **Crop and pest:** tart cherry; plum curculio (*Conotrachelus nenuphar*).
- **Inputs:** daily min/max (**have**). User input: full bloom date (`biofix`), else the Montmorency bloom estimate from `CherryPhenology/MontmorencyBloomStrategy.php`: **320 DD42 °F BE from January 1**.
- **Method:** DD base 50 °F, BE, from the biofix day inclusive. One mark: "Start of control period for tart cherries" at **375 DD50**. The output is the biofix row and that row, with the current one highlighted.
- **Source:** None cited. The comment says "this is for tart cherry plum curculio (PITS strategy)", presumably the "PC in tart cherry" timing from MSU; no reference.
- **Overlap with ours:** none (our `cherry` crop exists in `croplist`, but no cherry models).
- **Notes:** The input file's comment says "require biofix - cannot estimate", but the strategy does estimate it from cherry bloom. It's a one-number model. For apple, extension programs usually time the end of plum curculio protection by DD50 from petal fall (a figure around 308 DD is often quoted; not verified here); no apple version is in this folder.
- **Upper Midwest relevance:** moderate. Tart cherry is concentrated in northwest Michigan (most of US production) and Door County, Wisconsin (small). Plum curculio is also a major apple pest, but this model is for cherry only.

### AppleMaggot: apple maggot first flight

- **Predicts:** when to put out traps (fixed: "Place traps in early to mid-June", "By 6/1") and the beginning of the first apple maggot flight.
- **Crop and pest:** apple; apple maggot (*Rhagoletis pomonella*).
- **Inputs:** daily min/max (**have**).
- **Method:** DD base **50 °F**, BE, no upper, from **March 1**. First flight begins at **955 DD50**. The trap row is a fixed date (June 1). A blueberry maggot mark of 913 DD50 is commented out (it lives in its own model).
- **Source:** None cited.
- **Overlap with ours:** none.
- **Notes:** The header comment says "need 2 DD marks from 3/5" (March 5), but the code starts on **March 1**. The trap row isn't weather-based.
- **Upper Midwest relevance:** high for apple in Wisconsin, Minnesota and Michigan (apple maggot is native here and a key late-season pest). It's a simple model to port.

### ObliquebandedLeafroller: obliquebanded leafroller summer generation timing

- **Predicts:** estimated biofix (first sustained catch of the summer flight), then the first-generation egg hatch start and peak, second-generation first adults, first eggs and peak egg hatch, with treatment timings.
- **Crop and pest:** apple (and tart cherry); obliquebanded leafroller (*Choristoneura rosaceana*).
- **Inputs:** daily min/max (**have**). User input: biofix = sustained trap catch (`biofix`), else the estimate (**user input at points**).
- **Method:**
  - DD base **42 °F**, BE, no upper.
  - Biofix estimate (`ObliquebandedLeafrollerSustainedCatchStrategy.php`): **900 DD42 from March 1**.
  - After biofix (DD42 summed from the biofix day inclusive): egg hatch begins 350*; peak egg hatch 400*; second-generation adults first emerge 1150; first eggs laid by second-generation adults 1400; peak egg hatch, second generation 1550*.
- **Source:** None cited.
- **Overlap with ours:** none.
- **Notes:**
  - The whole model uses **base 42 °F**. Extension sources quote OBLR hatch at about 350–400 DD after biofix with a base of 42–43 °F or 50 °F (sources differ; not verified here). Check the base and the post-biofix numbers against MSU's own fact sheet before porting.
  - The sustained-catch DDMark doesn't set `method` (display only).
  - Its sustained-catch file is a near copy of codling moth's.
- **Upper Midwest relevance:** moderate. It's a leaf- and fruit-feeding pest of apple and cherry in Michigan and Wisconsin, often resistant to some insecticides, so timing matters.

### PeachHarvest: peach harvest dates by variety

- **Predicts:** the expected harvest date of Redhaven peach from spring heat, and of other varieties as Redhaven ± a fixed number of days. The dashboard shows Redhaven, Loring and Garnet Beauty.
- **Crop and pest:** peach; harvest timing.
- **Inputs:** daily min/max from January 1 to June 3 (**have**). The variety offsets come from DB table `peach_variety` (`variety_name`, `days_to_add_to_redhaven`; also `bln_low_acid` and `experience_category`, unused), which is **missing** from the dump.
- **Method** (`PeachHarvestStrategy.php` 80–102): DD base **50 °F**, BE, from **January 1 to June 3**. Redhaven harvest day of year = round(**−0.0386 × DD50(Jan 1–Jun 3) + 234.9**). Date = January 1 + (DOY − 1). Each variety = Redhaven + `days_to_add_to_redhaven`. If the June 3 total isn't > 0, it throws "Not enough temperature data". Example: 500 DD50 → day 216 (early August).
- **Source:** None cited.
- **Overlap with ours:** none (our `chill` module cites Richardson et al. 1974 for Redhaven rest, a different stage).
- **Notes:** The model can't run before June 3, and it's a single regression with no stated calibration region (presumably southwest Michigan). The variety table must come from MSU. The code checks ` > 0`, so a cold spring with very few DD would still run.
- **Upper Midwest relevance:** low. Peaches are a small crop in southwest Michigan and negligible in Wisconsin and Minnesota.

## Small fruit, grapes and cherry

### CherryPhenology: tart cherry bract leaves and Montmorency bloom

- **Predicts:** two date estimates used as biofixes by other models: "Expansion of first bract leaves" (start of the cherry leaf spot risk period) and "Montmorency bloom" (biofix for spotted wing drosophila fruit stages).
- **Crop and pest:** tart cherry (Montmorency); phenology.
- **Inputs:** daily air min and max (**have**).
- **Method:** Baskerville-Emin, base 42 °F, no upper, accumulated from Jan 1 of the year of the last weather date. Bract leaves: first date ≥ 250 DD42 (`CherryBractLeavesStrategy.php` 18–22). Montmorency bloom: first date ≥ 320 DD42 (`MontmorencyBloomStrategy.php` 16–21). Outputs the date (`biofix_estimated`), the DDMark, and the DD-to-date notes.
- **Source:** none cited.
- **Overlap with ours:** none (we have `cherry` in the crop list but no cherry phenology model).
- **Notes:** `CherryBractLeavesStrategy` never sets `DDMark->method` (left null). Jan 1 start with base 42 °F: winter warm spells count. The CherryLeafSpot test fixture (`tests/ResultModelsOnlineStatic/CherryLeafSpotTest.php`) still shows the leaf spot biofix as 320 DD "Montmorency bloom", so cherry leaf spot's biofix was changed from bloom to bract leaves (250) after the test was written.
- **Upper Midwest relevance:** Michigan grows most of the US tart cherry crop; Wisconsin has a smaller tart cherry industry in Door County; Minnesota little.

### CherryLeafSpot: cherry leaf spot infection events

- **Predicts:** for each wetting event since the biofix, its start and end, wet hours, span, mean temperature, rain, and an infection risk (None, Low, Moderate, High) with a "progress" percentage; a dashboard with the latest 3–4 events.
- **Crop and pest:** tart (and sweet) cherry; cherry leaf spot (*Blumeriella jaapii*).
- **Inputs:** hourly air temperature (**have**), hourly precipitation (**have**), hourly RH (**have**), hourly leaf wetness from one or two sensors (**missing**; the model already runs a no-sensor version using rain and RH ≥ 90 %, which is our **proxy**); biofix (user date, else estimated bract-leaf expansion, 250 DD42 from Jan 1: **have**).
- **Method:** (`CherryLeafSpotStrategy.php` 120–215; event logic in `ResultModels/AppleScab/AppleScabWetPeriod.php`)
  - Event starts only on a **raining hour** (hourly pcpn ≥ 0.254 mm) on or after the biofix, and not inside an earlier event (`TestDate`).
  - From there each hour is wet if leaf wetness ≥ 0.25 or pcpn ≥ 0.254 mm or RH ≥ 90 % (`isHourWet`, lines 188–212; constants lines 18–20). Dry hours are tallied; the event ends after **8 consecutive dry hours** (`addDryHour`, 257–277); dry gaps shorter than 8 hours count toward the span but not toward wet hours. The end time = start + span (trailing dry hours excluded). An event still open at the end of data is "ongoing".
  - Mean temperature = mean of the wet hours' temperatures (°C, converted to °F).
  - Accumulator: each wet hour adds `devinc` for that hour's temperature from the database table `hrsforinf_cherryleafspot` (rows `mintempf ≤ T < maxtempf`), lines 487–505, 581–594. "Progress" shown = accumulator × 100 %.
  - Risk (`calcCherryLeafSpotRisk`, 507–559): look up the row for the event's mean temperature, giving `hrshigh`, `hrsmod`, `hrslow`. If accumulator < 0.95 → None. Else wet hours ≥ hrshigh → High, ≥ hrsmod → Moderate, ≥ hrslow → Low, else (if mean 46–120 °F) None, else (accumulator ≥ 0.95) Low. No table row for the mean → None.
  - **The infection table is not in the dump** (a Postgres table). From the test fixture (`CherryLeafSpotTest.php`, station hvl, 2009) the low-risk wet hours by mean temperature are roughly: 52.7 °F 15 h; 53.5 °F 14; 54.2–54.9 °F 12; 55.1–56.0 °F 11; 56.2–56.9 °F 10; 57.0–57.9 °F 9; 58.5–58.8 °F 8; 59.2–60.9 °F 7; 61.3–62.7 °F 6; 63.4–67.9 °F 5; 69.6–70.2 °F 6; 71.9–72.1 °F 7; 74.7 °F 9; 77.1 °F 14; means of 38.5–39 °F have no row. At 52.7 °F, 25 wet hours was Moderate and 39 High.
  - Three tables: standard sensor (`lws0_pwet`), canopy sensor (`lws1_pwet`), and no sensor (rain and RH only, always computed).
- **Source:** none cited. (The table's shape resembles Eisensmith and Jones's cherry leaf spot infection model from Michigan, but the code doesn't say so; check with MSU.)
- **Overlap with ours:** none for cherry. Same event-building pattern as an apple scab Mills-type model, which we don't have.
- **Notes:**
  - We'd need the `hrsforinf_cherryleafspot` table (devinc and the three hour thresholds by temperature) from MSU; the test fixture alone can't rebuild `devinc`.
  - The 46–120 °F branch makes the final "accumulator ≥ 0.95 → Low" branch reachable only for means below 46 °F or above 120 °F; probably unintended.
  - A missing hour `break`s out of that day's hour loop but the outer loop continues with the next day, so an event spans a gap silently (`AppleScabWetPeriod.php` 130–145).
  - `dateStart` is set to hour − 1 with a comment "is this ok?… check linwood 6/1/2020".
  - `GetMostRecentEvents`, no-sensor branch: `$anEvent = new PredictionEvent()` is called a second time after the highlight is set, so the highlight is lost.
  - `SetUsedColumns` uses `+=` on numerically keyed arrays, so 'relh', 'atmp', 'pcpn' aren't added when a sensor column is already at key 0 (metadata only).
  - File header: "includedDates is not working / cherryLeafSpotRisk is not workign".
  - An event can only begin with measurable rain; dew-only wet periods never start an event.
- **Upper Midwest relevance:** the main foliar disease of tart cherry; important in Michigan and Door County, Wisconsin.

### CherryFruitworm: cherry fruitworm adult flight and egg laying

- **Predicts:** biofix (first sustained moth catch), adult flight period, egg-laying period (marked as the typical treatment timing), and % of adult flight and of egg laying complete on the select date and the last forecast date.
- **Crop and pest:** tart cherry; cherry fruitworm (*Grapholita packardi*).
- **Inputs:** daily air min and max (**have**); biofix = first sustained trap catch (user date at points: **have**; trap catches themselves **missing**), else estimated.
- **Method:**
  - Biofix estimate (`CherryFruitwormSustainedCatchStrategy.php` 16–21): Baskerville-Emin base 50 °F, no upper, from Mar 1; first date ≥ **238 DD50**.
  - After the biofix (`CherryFruitwormStrategy.php` 34–43), DD50 from the biofix (inclusive): adult flight 0–625 DD; egg laying 194–884 DD (`690 + 194`; "690 is from when equation for % moths is >= 0.9995").
  - Status (lines 470–505): adult flight % = `1 − exp(−(DD/277.02)^2.504)` with DD from the biofix; egg laying % = `1 − exp(−(DD/277.03)^2.224)` with DD from the date egg laying starts (194 DD, start day included via `gddGetDiff`). Rounded to 0.1 %, shown as whole percent, clamped 0–100. Status rows disappear once the stage's end has passed.
- **Source:** none cited.
- **Overlap with ours:** none.
- **Notes:** two Weibull curves with nearly identical scales (277.02 and 277.03), likely fitted separately; worth checking against the source. The egg-laying status counts the start day's DD, so it runs a day ahead of the 194 DD mark. Asterisk = "Typical treatment timing" on egg laying.
- **Upper Midwest relevance:** tart cherry pest; Michigan mainly, some Door County.

### BlueberryBloom: highbush blueberry bloom by variety

- **Predicts:** for each blueberry variety, the dates of first bloom, 10 % bloom, peak bloom and end of bloom, and % of bloom complete on the select date and the last forecast date.
- **Crop and pest:** highbush blueberry; phenology.
- **Inputs:** daily air min and max (**have**); variety table (**missing**: database table `blueberry_variety` with `variety_name`, `seq`, `dd_first`, `dd_pct10`, `dd_peak`, `dd_end`, `dd_duration`).
- **Method:** Baskerville-Emin base 50 °F, no upper, from Mar 1 (`BlueberryBloomStrategy.php` 19–24). Each stage date = first date ≥ that variety's DD goal (lines 90–106). % complete = DD from the first-bloom date (inclusive) to the date ÷ `dd_duration`, rounded, capped at 100 % (lines 108–150); 0 % before first bloom.
- **Source:** none cited.
- **Overlap with ours:** none (no blueberry in our crop list).
- **Notes:** all the numbers live in the missing table; request it from MSU. `JerseyBloomStrategy` (BlueberryGallWasp) separately puts 'Jersey' bloom at 250 DD50 from Mar 1, which may or may not match the table's Jersey row.
- **Upper Midwest relevance:** Michigan is a leading highbush blueberry state; Wisconsin and Minnesota grow small acreages, mostly direct-market.

### BlueberryGallWasp: blueberry stem gall wasp emergence

- **Predicts:** adult emergence: first, 50 %, and 99.5 %; footnote with the expected Jersey bloom date.
- **Crop and pest:** highbush blueberry; blueberry stem gall wasp (*Hemadas nubilipennis*).
- **Inputs:** daily air min and max (**have**).
- **Method:** Baskerville-Emin, **base 54.55 °F** (12.53 °C), no upper, from Mar 1 (`BlueberryGallWaspStrategy.php` 20–33): first emergence 160 DD, 50 % 340 DD, 99.5 % 553 DD. Jersey bloom (`JerseyBloomStrategy.php` 15–20): 250 DD50 from Mar 1, shown only as a footnote.
- **Source:** none cited.
- **Overlap with ours:** none.
- **Notes:** the odd base (54.55 °F) suggests a converted Celsius threshold (~12.5 °C); check the source. `JerseyBloomStrategy` doesn't set `method` on its mark.
- **Upper Midwest relevance:** a Michigan highbush pest; minor in Wisconsin and Minnesota.

### BlueberryMaggot: blueberry maggot first flight

- **Predicts:** "Place traps in early to mid-June" (fixed: by June 1) and the start of the first flight of blueberry maggot.
- **Crop and pest:** blueberry; blueberry maggot (*Rhagoletis mendax*).
- **Inputs:** daily air min and max (**have**).
- **Method:** Baskerville-Emin base 50 °F, no upper, from Mar 1; first flight at **913 DD50** (`BlueberryMaggotStrategy.php` 20–31). Apple maggot (955 DD50) is commented out.
- **Source:** none cited.
- **Overlap with ours:** none.
- **Notes:** header comment says "need 2 DD marks from 3/5, base 50" but the code starts Mar 1. The trap row's date is hard-coded to June 1.
- **Upper Midwest relevance:** a quarantine pest for Michigan blueberries; small in Wisconsin and Minnesota. The commented-out apple maggot mark (955 DD50 from Mar 1) would matter to Wisconsin apple growers.

### MummyBerry: mummy berry risk periods

- **Predicts:** primary risk period (ascospore infection of shoots) and secondary risk period (conidial infection of flowers), as date ranges; footnote with the expected Jersey bloom.
- **Crop and pest:** highbush blueberry; mummy berry (*Monilinia vaccinii-corymbosi*).
- **Inputs:** daily air min and max (**have**). No wetness or rain.
- **Method:** Baskerville-Emin **base 42 °F**, no upper, from **Feb 1** (`MummyBerryStrategy.php` 21–34): primary 100–800 DD42; secondary 801–1000 DD42. Jersey bloom footnote from `JerseyBloomStrategy` (250 DD50 from Mar 1) only when the last weather date is after Mar 1.
- **Source:** none cited.
- **Overlap with ours:** none.
- **Notes:** purely a calendar of susceptible periods; infection needs wet periods and apothecia, which the model doesn't use. A wetness-based version could use our RH-hour proxies.
- **Upper Midwest relevance:** a major blueberry disease in Michigan; minor elsewhere in the region.

### CranberryFruitworm: cranberry fruitworm egg laying

- **Predicts:** biofix (sustained moth catch), the egg-laying period (typical treatment timing), and % of oviposition complete on the select date and the last forecast date.
- **Crop and pest:** cranberry and blueberry (Michigan's model is for blueberry; the pest attacks both); cranberry fruitworm (*Acrobasis vaccinii*).
- **Inputs:** daily air min and max (**have**); biofix = first sustained trap catch (user date: **have**; trap data **missing**), else estimated; oviposition curve (**missing**: database table `oviposition_cranberryfruitworm`, columns `ddgoal`, `pct_oviposition`).
- **Method:**
  - Biofix estimate (`CranberryFruitwormSustainedCatchStrategy.php` 15–20): Baskerville-Emin base 50 °F, no upper, from Mar 1; first date ≥ **350 DD50**.
  - After the biofix (`CranberryFruitwormStrategy.php` 39–42): DD50 from the biofix, egg laying 85–485 DD.
  - Status: % oviposition = the table's `pct_oviposition` for the largest `ddgoal` ≤ DD since the biofix (lines 250–265); 0 below the first row. Since 1/18/2022 DD count from the biofix, not Mar 1 (Trello link in the header).
- **Source:** none cited; the change note links `https://trello.com/c/RAzGuLwU/327-cranberry-fruitworm-oviposition#comment-61e5ebff62c0ad70fda06837`.
- **Overlap with ours:** none.
- **Notes:** the comment in `GetStatusRow` still says "these use dateStartAccumulation of 3/1 - NOT BIOFIX", contradicting the code. The oviposition table must be obtained from MSU. MSU's thresholds were developed in Michigan blueberry; Wisconsin cranberry marshes (flooded, sanded, frost-protected beds) have their own phenology, and Wisconsin's cranberry IPM uses its own degree-day work, so validate before use.
- **Upper Midwest relevance:** Wisconsin grows most of the US cranberry crop, and cranberry fruitworm is one of its key insect pests: high relevance if the thresholds hold for cranberry.

### GrapeBerryMoth: grape berry moth generations

- **Predicts:** the starts of 2nd, 3rd and 4th generation egg laying and egg hatch, with a note on whether a 4th generation will develop (from day length).
- **Crop and pest:** grape (juice and wine); grape berry moth (*Paralobesia viteana*).
- **Inputs:** daily air min and max (**have**); biofix = wild grape bloom (user date: **have**), else estimated; station latitude (**have**, grid cell).
- **Method:**
  - Biofix estimate (`WildGrapeBloomStrategy.php` 13–18): Baskerville-Emin base 50 °F, no upper, from Mar 1; wild grape bloom at **350 DD50** ("changed from 450 to 350 on 1/30/2020 per Keith's email").
  - After the biofix (`GrapeBerryMothStrategy.php` 36, 60–82): Baskerville-Emin **base 47 °F**, no upper, from the biofix: 2nd gen egg laying 810, egg hatch 910; 3rd gen 1620, 1720; 4th gen 2430, 2530 DD47.
  - 4th generation (lines 46–51, 520–537, and the comment at 606–627): day length (FAO-56 formula) on the date 3rd-generation egg laying starts (1620 DD): ≤ 12.5 h "Fourth generation not expected"; ≤ 13 h "At least some fourth generation is expected"; ≤ 14 h "Significant fourth generation is expected"; > 14 h "Full fourth generation expected".
  - Oviposition % (table `oviposition_grapeberrymoth`) was removed 2/15/2021 (commented out).
- **Source:** none cited in code; the day-length rule is quoted from "Trello - June 24 2021 - from Keith". (From memory, not the code: the 810 DD47 generation interval matches the published Michigan/Pennsylvania GBM degree-day model, Tobin et al. and later Isaacs et al.; verify before citing.)
- **Overlap with ours:** none.
- **Notes:** the header comment "biofix guess = GDD450 Base 50F" is stale (350 now). Keith's narrative says a full 4th generation needs ~15 h days and ~14 h gives ~50 %, but the code calls > 14 h "Full". Day length is astronomical (no civil twilight); diapause photoperiod responses are usually stated with twilight, so check which the thresholds assume. If the day length can't be computed the text says "Problem in calculating day length."
- **Upper Midwest relevance:** the key insect of Michigan's Concord juice grapes; Wisconsin and Minnesota grow cold-hardy wine grapes (Frontenac, Marquette) on small acreages where GBM occurs; at their latitudes a 4th generation is rarely expected.

### GrapeBerryWeight: grape berries at half final weight, by variety

- **Predicts:** for each of 15 varieties, the date berries reach half their final weight (a timing aid for crop estimation).
- **Crop and pest:** wine and juice grapes; berry growth.
- **Inputs:** daily air min and max (**have**).
- **Method:** Baskerville-Emin base 50 °F, no upper, from **Apr 1** ("should be 4/1?"), first date ≥ the variety's goal (`GrapeBerryWeightStrategy.php` 19–68): Chardonnay 1070; Pinot noir 1140; Pinot gris 1150; Cabernet franc 1170; Maréchal Foch 1180; Frontenac 1180; Vignoles 1180; Riesling 1190; Cabernet Sauvignon 1200; Concord 1210; Chardonel 1470; Pinot blanc 1470; Traminette 1470; Seyval 1500; Merlot 1700 DD50.
- **Source:** none cited.
- **Overlap with ours:** none.
- **Notes:** disagrees with ConcordBerryWeight (Concord 1210 DD50 from Apr 1 here, 1200 DD50 from Mar 1 there). The variable for Frontenac is misspelled `Frontnac` (harmless). No Marquette, the most planted cold-hardy red in Wisconsin and Minnesota.
- **Upper Midwest relevance:** useful to Michigan's wine and juice grape growers; small but growing in Wisconsin and Minnesota (Frontenac and Maréchal Foch are grown there).

### ConcordBerryWeight: Concord berries at half final weight

- **Predicts:** the date Concord berries reach half their final weight.
- **Crop and pest:** Concord juice grape; berry growth.
- **Inputs:** daily air min and max (**have**).
- **Method:** Baskerville-Emin base 50 °F, no upper, from **Mar 1** ("should be 4/1?"); midpoint at 1200 DD50 (`ConcordBerryWeightStrategy.php` 18–25).
- **Source:** none cited.
- **Overlap with ours:** none.
- **Notes:** start date and threshold disagree with GrapeBerryWeight's Concord row (Apr 1, 1210). DD50 between Mar 1 and Apr 1 is usually small in Michigan, but not zero; pick one.
- **Upper Midwest relevance:** Concord is a major Michigan crop (southwest Michigan); little Concord in Wisconsin or Minnesota.

### SpottedWingDrosophila: SWD fruit-susceptibility stages and insecticide wash-off

- **Predicts:** the fruit stage of tart cherry since bloom (not ripe, coloring, ripe), each with an SWD risk level that depends on whether flies are present; plus, for a spray date, which insecticides have probably lost efficacy to rain since the spray, and the rain total.
- **Crop and pest:** tart cherry; spotted wing drosophila (*Drosophila suzukii*).
- **Inputs:** daily air min and max (**have**); daily precipitation (**have**); biofix = Montmorency bloom (user date: **have**), else estimated (320 DD42 from Jan 1); "flies present" yes/no (user input, default yes: **have** as a user option; trap catches **missing**); date of last spray (user input, default today when the run reaches today: **have**).
- **Method:**
  - Fruit stages (`SpottedWingDrosophilaStrategy.php` 31–76): Baskerville-Emin **base 39.2 °F** (4 °C), no upper, from the biofix: not ripe 0–954 DD; coloring 954–1170 DD; ripe from 1170 DD.
  - Risk by stage (lines 40–44): with flies: not ripe low, coloring medium, ripe high; without flies: not ripe none, coloring none, ripe low. The risk text is prefixed to each row's prediction, except for stages in the far future.
  - Wash-off (`SWDWashoffStrategy.php` 31–37, 230–265): rain from the spray date (spray day included) to the select date and to the end of the precipitation forecast (3 days), via `RainfallAccumulationStrategy` (missing days add nothing). Thresholds: Assail 0.1 in; Mustang Maxx 0.1 in; Imidan 0.25 in; Delegate 0.5 in; Exirel 0.5 in. Rain ≥ threshold by the select date → red ("has reached threshold"); by the forecast end → yellow. Assail marked "This insecticide had generally low efficacy in our trials."
  - `SWDBiofixAndFliesStrategy.php` only returns the defaults (biofix, flies, spray date) to the front end.
- **Source:** none cited ("in our trials" refers to MSU's own insecticide trials).
- **Overlap with ours:** `spotted-wing-drosophila` (`packages/agmodels/src/agmodels/insects/spotted_wing_drosophila.py`, from VDIFN) is a pest-phenology model: single sine, base 45 °F, upper 86 °F, from Jan 1, egg laying from 1276 DD with a peak near 3100 DD (generation 1276/3180/4000). MSU's model is different in kind: it times **host susceptibility** (cherry ripening, base 39.2 °F from bloom) and pairs it with spray wash-off. They complement each other rather than overlap.
- **Notes:**
  - In `GetRow`, when the risk key isn't found, `$row->Prediction = $predictionDateString;` uses an undefined variable (dead path in practice).
  - Wash-off thresholds are fixed per product and assume a single spray date; no decay with time or sunlight.
  - Stage thresholds are for tart cherry; Wisconsin's main SWD hosts are raspberry, blackberry, strawberry and blueberry, which ripen on different schedules.
  - The highlight timeout for the last row is 60 days (`LastRowHighlightDays`).
- **Upper Midwest relevance:** SWD is a top pest of Wisconsin and Minnesota berries and of Michigan cherries; the wash-off table is useful for any crop, the ripening stages only for tart cherry.

## Field crops, vegetables and evapotranspiration

### AlfalfaCutting: Alfalfa first-cutting timing by GDD

- **Predicts:** the date the crop reaches the GDD totals for best harvest timing for the first cutting: optimal for horizontal silos, optimal for vertical silos, and the point where NDF passes the optimal level.
- **Crop and pest:** alfalfa; forage quality (fiber) at first cut.
- **Inputs:** daily Tmax and Tmin (**have**). No user inputs; the start date is fixed.
- **Method:** `average` method, base **41 °F**, no upper (212), accumulated from **March 1** of the selected year. Events (cumulative from March 1):
  - 680 GDD: "Optimal harvest for horizontal silos (if growth is not limited)"
  - 750 GDD: "Optimal harvest for vertical silos (if growth is not limited)"
  - 970 GDD: "NDF higher than optimal level"
  - Output is a table of the 3 events with their dates (past or projected) and the current GDD total; the current row is highlighted for 7 days.
- **Source:** none cited.
- **Overlap with ours:** `alfalfa-growth` (`packages/agmodels/src/agmodels/models/alfalfa_growth.py`). Differences: ours is **single sine 41/86 °F** from **January 1** or the last cutting, with a cut window of **900–1100 GDD**; MSU is the **simple average, base 41 °F, no upper**, from **March 1**, first cut only, with targets of **680 / 750 / 970**. The averaging method gives fewer GDD than single sine on cool spring days (it scores 0 on days whose mean is below 41 °F), which partly explains the lower targets. MSU's targets are tied to silo type and fiber (NDF), which ours lacks. MSU has no later cuttings and no fall-cutting rule.
- **Notes:** no restart after a cutting (first cut only). Missing days count 0.
- **Upper Midwest relevance:** high: alfalfa is a major forage crop in Wisconsin, Minnesota and Michigan (dairy).

### AlfalfaWeevil: Alfalfa weevil larval feeding

- **Predicts:** the dates of light feeding, major feeding, pupation and the end of pupation and feeding; the user can replace each of the first three with an observed date.
- **Crop and pest:** alfalfa; alfalfa weevil (*Hypera postica*).
- **Inputs:** daily Tmax and Tmin (**have**); optional user dates `biofix1` (light feeding starts), `biofix2` (major feeding starts), `biofix3` (pupation starts) (**have at points**, as user inputs).
- **Method:** BE (single sine, no upper), base **48 °F**, from **January 1**. Chained goals (`AlfalfaWeevilBiofixStrategy.php`, `AlfalfaWeevilStrategy.php`):
  - Biofix 1 "Light feeding starts": **300** DD from January 1.
  - Biofix 2 "Major feeding starts": **139** DD after biofix 1 (cumulative 439 if not overridden).
  - Biofix 3 "Pupation starts; major feeding continues": **157** DD after biofix 2 (cumulative 596).
  - "End of pupation and feeding": **224** DD after biofix 3 (cumulative 820).
  - Each later goal counts from the biofix actually used (observed if given, else estimated), so an observed date shifts every later stage. Biofix 2 is computed only if biofix 1 exists, and 3 only if 2 exists.
  - Input checks (`AlfalfaWeevilBiofixInput.php`): a biofix 3 earlier than 2 or 1 is dropped, a biofix 2 earlier than 1 is dropped; all must be in the same year and after January 1.
- **Source:** none cited.
- **Overlap with ours:** `alfalfa-weevil` (`insects/alfalfa_weevil.py`, from the Crop Risk Tool): base **48.2 °F (9 °C), upper 86 °F**, single sine, from January 1; stages 300 egg hatch, 370 2nd instar, 440 3rd instar, 505 4th instar, 595 pupal, 815 adult emergence, 1000 adult diapause. The numbers agree closely: MSU's cumulative 300 / 439 / 596 / 820 line up with our 300 (hatch) / 440 (3rd instar) / 595 (pupal) / 815 (adult emergence). Differences: MSU uses base 48 with no upper (ours 48.2 with 86 °F upper), and MSU lets observed dates reset the later stages, which our stage model does not.
- **Notes:** `models_with_multiple_start_dates.txt` lists alfalfa weevil with a "(?)" because of the chained biofixes. The input check compares a Carbon date with a possibly null earlier biofix (`$this->biofix3 < $this->biofix2` when biofix2 is null); in PHP that comparison is unreliable, so an out-of-order date may slip through. Missing days count 0.
- **Upper Midwest relevance:** high: alfalfa weevil is the main first-cut insect pest of alfalfa in Wisconsin, Minnesota and Michigan.

### AsparagusMiner: Asparagus miner phenology

- **Predicts:** dates of adult flight (start and peak for generations 1 and 2, end of generation 2), larval and pupal first appearance and peaks; plus a seasonal relative-abundance curve for adults, larvae and pupae with the current and forecast positions.
- **Crop and pest:** asparagus; asparagus miner (*Ophiomyia simplex*), which is linked to Fusarium crown and root rot.
- **Inputs:** daily Tmax and Tmin (**have**). No user inputs.
- **Method:** BE (single sine, no upper), base **53.7 °F**, from **March 1**. Stages (cumulative DD from March 1):
  - Gen 1 adults: beginning of flight **170**, peak flight **530**
  - Gen 1 larvae: first appearance **435**, peak **675**
  - Gen 1 pupae: first appearance **570**, peak **855**
  - Gen 2 adults: beginning **975**, peak **1475**, end of flight **2005**
  - Gen 2 larvae: peak **1555**
  - Gen 2 pupae: peak **1775** (overwintering)
  - Commented-out spray guidance: a 95% confidence interval of ±39 DD around the gen 1 adult peak and ±37 around the gen 2 peak.
  - Abundance curves: lookup tables of relative abundance by DD with linear interpolation (`AsparagusMinerAbundance.php`: adults lines 8–110, 0 to 2200 DD, peak ~0.058 near 545 DD and a second rise past 1000; larvae 112–167; pupae 169–224). Above 2200 DD the value is null.
- **Source:** none cited.
- **Overlap with ours:** none (we have `common-asparagus-beetle` only).
- **Notes:** in `GetAbundanceAtDD`, a DD above the table's last key hits `break`, which exits the loop over stages, so larvae and pupae are not returned once adults run past 2200 (minor). The larvae table's values are nearly all ~0 (e.g. 4.8e-5 at 1939), which looks like a fitting artifact or a scaling mistake: the larval curve would be flat. Pupae jump to a constant 0.0362 from 1886 DD on. Treat the curves as unreliable without the original fit.
- **Upper Midwest relevance:** moderate: Michigan is the leading US asparagus state; Wisconsin and Minnesota have smaller acreage.

### CabbageMaggot: Cabbage maggot flights

- **Predicts:** emergence of the overwintering flies, the spring peak flight (the stage to manage), and the first and second summer peak flights, as date ranges, with progress bars and a status line.
- **Crop and pest:** cole crops (cabbage, broccoli, cauliflower, radish, turnip…); cabbage maggot (*Delia radicum*).
- **Inputs:** daily Tmax and Tmin (**have**). No user inputs.
- **Method:** BE (single sine, no upper), base **43 °F**, from **March 1**. Stages (cumulative DD from March 1):
  - 0–299 "Dormant": overwintering flies have not emerged
  - **300–564** "Emergence from overwintering": little or no risk of damage from this flight
  - **565–716** "Spring peak flight": high risk; "the most important stage to manage"
  - (commented out: 717–1210 between flights; 1211–1475 fly emergence and egg laying start)
  - **1476–1728** "First summer peak flight": low risk; management may not be needed
  - (commented out: 1729–2386 between flights; 2387–2651 emergence)
  - **2652–2887** "Second summer peak flight": low risk
  - Status rows stop updating after **October 1** (`EndStatus = '10/1/'`).
- **Source:** none cited.
- **Overlap with ours:** `cabbage-maggot` (`insects/cabbage_maggot.py`, from VDIFN): base **42.8 °F, upper 86 °F**, single sine, from **January 1**, generations (start, peak, end) **(360, 600, 1521)** and **(1881, 2121, 3042)**. Differences: MSU starts March 1 (vs January 1), has no upper threshold, and puts the spring peak at **565–716** (ours peaks at 600 within a 360–1521 generation); MSU has three distinct flights after the spring one (summer peaks at 1476–1728 and 2652–2887), ours two generations whose second peak (2121) falls between MSU's two summer peaks. MSU's explicit risk labels (spring flight high, summer low) are worth carrying over.
- **Notes:** the progress-bar code is long and cosmetic (lines ~470–820). Missing days count 0.
- **Upper Midwest relevance:** moderate: cole crops and radish in Wisconsin (cabbage for kraut), Michigan and Minnesota.

### ColoradoPotatoBeetle: Colorado potato beetle phenology

- **Predicts:** dates of first and peak adults, eggs and larvae in generation 1, peaks of adults, eggs and larvae in generation 2 and the end of adult flight; plus seasonal abundance curves.
- **Crop and pest:** potato (also tomato, eggplant); Colorado potato beetle (*Leptinotarsa decemlineata*).
- **Inputs:** daily Tmax and Tmin (**have**). No user inputs.
- **Method:** BE (single sine, no upper), base **52 °F**, from **March 1**. Stages (cumulative DD from March 1):
  - Gen 1 adults: start of flight **372**, peak **607**
  - Gen 1 eggs: first **459**, peak **699**
  - Gen 1 larvae: first **699**, peak **930**
  - Gen 2 adults: peak **1376**, end of flight **1780**
  - Gen 2 eggs: peak **1386**
  - Gen 2 larvae: peak **1598**
  - Abundance tables (`ColoradoPotatoBeetleAbundance.php` lines 8–66): percent of season catch for adults, eggs and larvae at 17 DD points from 0 to 1780 (e.g. adults 53.96% at 1386.6; eggs 41.18% at 699.5; larvae 48.81% at 930.7), linearly interpolated. A comment says "use linear DD for % complete per call with Keith 3/27/2023".
- **Source:** none cited (the comment names "Keith", presumably the MSU entomologist).
- **Overlap with ours:** `colorado-potato-beetle` (CRT: base **50 °F, upper 86 °F**, single sine, January 1; 200 colonization, 350 egg hatch, 600 peak adults, 800 peak larvae, 935 pupation, 1100 gen 2 emergence, 1470 gen 2 peak adults, 1800, 1970, 2265); `-adults` (VDIFN: 50/86 from January 1, (275, 690, 1090), (1090, 1690, 2500)); `-larvae` ((485, 905, 2500)). Differences: MSU uses base **52 °F** (not 50) with no upper, from **March 1**; with the higher base MSU's numbers are lower for the same calendar date. MSU's gen 1 larval peak at 930 (base 52) vs our 800 (CRT) and 905 (VDIFN) at base 50; MSU's gen 2 adult peak 1376 vs our 1470 / 1690. MSU adds an egg stage, which ours lacks.
- **Notes:** the stage thresholds come from the abundance table's keys (372.6, 607.5, 699.5, 930.7, 1386.6, 1598.9, 1780), except **gen 2 adult peak 1376**, which does not match the table's peak at 1386.6, and **gen 2 egg peak 1386**, where the table's eggs are only 6.95% (the egg table's second bump is at 1019.3, 12.83%). One of these looks like a transcription slip. PHP truncates float array keys to integers (218.2 becomes 218), so the table's decimal DD keys are silently rounded down. A declared `DDMark_AdultsGen2Beginning` has no goal (dead).
- **Upper Midwest relevance:** high: the key insect of Wisconsin's and Michigan's potato industries.

### CucurbitDownyMildew: Cucurbit downy mildew weather table

- **Predicts:** no risk score. It is a daily weather table to read alongside the national cucurbit downy mildew forecast: Tmin, Tmax, mean, rain, RH min/max/mean, a cloudiness category and the number of wet or humid hours.
- **Crop and pest:** cucumber, melon, squash, pumpkin; cucurbit downy mildew (*Pseudoperonospora cubensis*).
- **Inputs:** daily Tmin, Tmax, precipitation, RH min and max (**have**); daily solar radiation (**have**, shortwave); hourly precipitation and RH (**have**); hourly leaf wetness `lws0_pwet` / `lws1_pwet` (**proxy**: RH only).
- **Method:**
  - Wet hour (`fnWetHourCucurbit`, lines 500–518): an hour is wet if precipitation ≥ 0.001 in (0.0254 mm), or leaf wetness > 0.25 of the hour, or RH ≥ 90%. Counted per calendar day, once without a leaf wetness sensor and once per sensor.
  - Cloudiness (`fnGetCucurbitSolarCategory`, 520–600): the day's solar radiation against monthly 30th and 70th percentiles from 10+ years at 5 Enviroweather stations (Jeff Andresen's email in the code), April–October only. In MJ/m²/day, "Cloudy" ≤ 30th, "Partly cloudy" to the 70th, "Mostly sunny" above: Apr 11.9/22.2, May 14.5/24.4, Jun 17.9/25.9, Jul 19.2/25.8, Aug 16.2/22.6, Sep 11.5/18.3, Oct 5.9/12.2 (Nov–Mar values given in the comment but not used: Jan 3.3/6.3, Feb 5.7/10.8, Mar 9.0/16.6, Nov 2.9/7.1, Dec 2.4/5.1). The code compares kJ/m² (22200 etc.).
- **Source:** the percentile table is from an email by Jeff Andresen (MSU state climatologist) to Tracy; no other citation.
- **Overlap with ours:** none for cucurbit downy mildew. We already have hours of RH ≥ 90% and shortwave, so this table is cheap.
- **Notes:** `if ($atmp_min)` and `if ($relh_min)` treat 0 (0 °F, 0%) as missing. The leaf wetness test `lw > 0.25` assumes a fraction of the hour, while its comment calls it a percent: if the column is in percent this counts any wetness at all. Rain over 0.001 in is a very low bar (any trace). The cloudiness categories are an idea we could reuse on daily pages (a local, month-aware "cloudy / partly cloudy / sunny" from shortwave).
- **Upper Midwest relevance:** moderate: cucumbers for pickling (Michigan leads the US; Wisconsin is significant) and squash and pumpkins; downy mildew arrives most years from the south.
- **Feature idea:** a cucurbit downy mildew page that shows our wet hours and the cloudiness category beside a link to the national forecast (cdm.ipmpipe.org).

### EuropeanCornBorer: European corn borer flights

- **Predicts:** date ranges of the first, second and third moth flights (egg laying; when vulnerable crops need protection).
- **Crop and pest:** field corn, sweet corn, peppers, snap beans, potato; European corn borer (*Ostrinia nubilalis*).
- **Inputs:** daily Tmax and Tmin (**have**). No user inputs.
- **Method:** BE (single sine, no upper), base **50 °F**, from **March 1**. Flights (cumulative): first **450–950**, second **1450–1950**, third **2450–2950** ("In most years there won't be a third flight", comment lines 21–29). After **October 1** an event not yet started is shown as not expected this year.
- **Source:** none cited ("Rough numbers for ECB" in the comment).
- **Overlap with ours:** `european-corn-borer` (VDIFN): base **50 °F, upper 86 °F**, single sine, from **January 1**, generations (start, peak, end) **(550, 740, 900)** and **(1660, 1950, 2190)**. Differences: MSU's first flight starts 100 DD earlier (450 vs 550) and runs later (950 vs 900); its second flight 1450–1950 starts ~200 earlier than ours (1660) and ends ~240 earlier (2190); MSU adds a third flight; MSU has no upper threshold and starts March 1. MSU's own comment calls these "rough numbers", so ours (VDIFN) needs no change on this evidence.
- **Notes:** none beyond the shared ones.
- **Upper Midwest relevance:** moderate: ECB pressure has fallen sharply with Bt corn but still matters for sweet corn, peppers, snap beans and non-Bt corn.

### PotatoHeatAndMoisture: Potato heat and soil moisture table

- **Predicts:** no stages: a daily table from a start date (default March 1, user-settable) of air temperature, air DD, soil temperature and soil DD, rain and its total, and soil moisture.
- **Crop and pest:** potato; planting and early growth conditions.
- **Inputs:** daily air Tmin/Tmax (**have**); daily soil temperature min/max at **5 cm** (`stmp_05cm`, labelled "2 inches") (**have**: our soil temperature at 4 cm is the nearest); daily precipitation (**have**); daily soil moisture min/max (`mstr0`, or `smst_20cm`) (**missing**: planned); user start date (**have at points**).
- **Method:** BE (single sine, no upper), base **40 °F**, on air temperature and separately on 5 cm soil temperature, from the start date (default **March 1**). Precipitation is summed from the start date. Columns: date, air min/max, DD40 air daily and total, soil min/max, DD40 soil daily and total, rain daily and total, soil moisture min/max.
- **Source:** none cited.
- **Overlap with ours:** `potato-stages` (base **4 °C (39.2 °F)**, simple average, from planting, emergence at 208 °C·d) covers emergence; ours has no soil-temperature DD and no soil moisture table.
- **Notes:** precipitation is summed with `if (pcpn >= 0)`, which in PHP is true for null, so a missing day adds 0 and is not reported (our D45 counts and reports missing days). Soil DD with a sine curve on soil min/max is unusual (soil temperature's daily curve is flatter than air's), but harmless.
- **Upper Midwest relevance:** high: Wisconsin and Michigan are top potato states (Wisconsin third in the US); Minnesota also grows them.
- **Feature idea:** a potato field-conditions table (air and 4 cm soil DD since planting, rain since planting, soil moisture once we have it) is easy from our data.

### PotatoGraph: Potato field stress graph (basic and advanced)

- **Predicts:** a season chart and table for a potato field from planting to harvest: DD since planting against the average of the previous 5 years, and flags on days that pass stress thresholds (high DD, hot day, heavy rain, high ET; in the advanced version also warm nights and hours of rain), plus the grower's own logged events.
- **Crop and pest:** potato; heat, moisture and growth stress (tuber quality issues such as heat sprout and hollow heart are the likely motive; the code does not say).
- **Inputs:** daily Tmax and Tmin (**have**); daily precipitation (**have**); daily `rpet` (reference potential ET from the station database) (**have**: our FAO-56 ET0; different method, see PotentialEvapotranspiration); hourly air temperature and precipitation (**have**, advanced); planting and harvest dates (**have at points**); the last 5 years' weather at the same place (**have**: our archive); the grower's logged growth, management and pre-harvest panel events (**missing**: a per-field event log in the advanced version, which needs a login and saved fields).
- **Method:**
  - DD: BE (single sine, no upper), base default **40 °F** (user-settable in advanced), from the season start (planting; default **March 1**, or January 1 if the selected date is before March 1) to the season end (harvest; default **September 30**).
  - Historical DD: the same calculation for each of the 5 previous years over the same dates, averaged per day (`gddGetAverageAcrossGddArrays`); the years with enough data are listed.
  - Daily flags (defaults, user-settable in advanced): daily DD ≥ **40**; Tmax ≥ **88 °F**; rain ≥ **1.5 in**; RPET ≥ **0.25 in**.
  - Advanced only (`PotatoGraphAdvancedStrategy.php`): hours with rain ≥ **0.1 in** counted per day; **night heat stress** when at least **6 consecutive hours** of air temperature ≥ **65 °F** fall between **23:00** and **08:00** the next morning (hour-ending 23, 24, then 1–8). Night start, end, minimum hours and thresholds are user-settable with clamping rules.
- **Source:** none cited.
- **Overlap with ours:** `potato-stages` (emergence only). Nothing of ours flags hot nights, hot days or heavy rain for potatoes, and we have no 5-year comparison per point.
- **Notes:** **bug in the night-stress run length** (lines 364, 396, 438): the code compares `$nightstress_count > $nightstress_count_max` but stores into `$nightstress_max_count`, so `$nightstress_count_max` stays 0 and the "longest run" is really the length of the **last** run of warm hours; a 7-hour run followed by a 2-hour run reports 2 hours and misses the stress. Missing hours reset the run. The 5-year average averages whatever years have data (fewer than 5 without warning beyond the footnote). Day-of-season flags count missing DD days as 0.
- **Upper Midwest relevance:** high: potatoes in Wisconsin, Michigan and Minnesota.
- **Feature idea:** a potato season page at a site: DD since planting against recent years, and flagged hot days, warm nights (hours ≥ 65 °F overnight), heavy rain and high ET days. Uses only data we have.

### SeedCornMaggot: Seedcorn maggot flights

- **Predicts:** date ranges of the overwintering generation's flight and egg laying (with its peak), first-generation adult emergence, and the first generation's flight and peak.
- **Crop and pest:** corn, soybean, beans, cucurbits, onion (seed and seedlings); seedcorn maggot (*Delia platura*).
- **Inputs:** daily Tmax and Tmin (**have**). No user inputs.
- **Method:** BE (single sine, no upper), base **39 °F**, from **March 1**. Stages (cumulative):
  - Overwintering generation: adult flight and egg laying **200–813**; peak flight and egg laying **342**
  - Generation 1: adults start to emerge **842**; flight and egg laying **901–1650**; peak **1234**
  - The old site's status text (comment block at the end of the file) gives the finer bands it used: 200–275 flying, peak not yet; 275–325 peak soon; **325–360 peak**; 360–813 after peak; 813–842 a few overwintering adults, gen 1 soon; 842–901 gen 1 emerging; 901–1150 gen 1 flying; 1150–1225 peak soon; **1225–1250 peak**; 1250–1650 after peak; >1650 gen 1 flight complete.
- **Source:** none cited.
- **Overlap with ours:** `seedcorn-maggot` (`insects/seedcorn_maggot.py`, rebuilt on its sources): base **39 °F, upper 84.2 °F, simple average** (Funderburk et al. 1984's method), from **January 1**; adult flight curve start **70**, peak **340**, end **650** (10/50/90% at 201/345/495); larval feeding 82 DD after oviposition for 367; generations **720** DD apart. Differences: the overwintering peak agrees (342 vs our 340/345) though on a different DD method and start date; MSU's flight starts later (200 vs 70) and ends later (813 vs 650); MSU's generation 1 peak comes **892** DD after the first (1234 − 342) against our **720** (Funderburk's lab adult-to-adult 706). With single sine from March 1, MSU's DD run higher than our averaging method in spring, which makes their larger generation gap more surprising; worth a check against Wisconsin trap data before changing anything.
- **Notes:** none beyond the shared ones.
- **Upper Midwest relevance:** moderate: a planting-time pest of corn, soybean and vegetables in cool, wet springs across the region.

### SquashVineBorer: Squash vine borer flight

- **Predicts:** adult emergence, flight and egg laying, the decline of flight, and the end of flight. The old site's advice text (comment at the end): emergence soon, put pheromone traps out; flying, scout for eggs and damage; flight almost complete; flight complete, no more eggs.
- **Crop and pest:** squash, pumpkin, zucchini; squash vine borer (*Melittia cucurbitae*).
- **Inputs:** daily Tmax and Tmin (**have**). No user inputs.
- **Method:** BE (single sine, no upper), base **50 °F**, from **March 1**. Events (cumulative): adult emergence **800**; adult flight and egg laying **900**; flight and egg laying declines **1800**; flight complete **2000**.
- **Source:** none cited.
- **Overlap with ours:** `squash-vine-borer` (VDIFN): base **50 °F, no upper**, single sine, from **January 1**, one generation (start, peak, end) **(750, 900, 1000)**. Differences: emergence 800 vs 750 and the 900 flight mark agree roughly, but MSU's flight lasts to **2000** DD while ours ends at **1000**. Neither cites a source; worth checking where our 1000 end comes from.
- **Notes:** none beyond the shared ones.
- **Upper Midwest relevance:** moderate: important for home gardens and fresh-market squash and pumpkins; less for processing acreage.

### Tomcast: TOMCAST disease severity values

- **Predicts:** daily disease severity values (DSV) and their running total since the last spray, with caution levels at 15, 18 and 20 to time fungicide sprays. No crop is named in the code; TOMCAST is used for tomato early blight, Septoria and anthracnose and for carrot and asparagus leaf diseases.
- **Crop and pest:** tomato (also carrot, asparagus purple spot); early blight (*Alternaria solani*), Septoria leaf spot, anthracnose.
- **Inputs:** hourly air temperature (**have**); hourly RH (**have**); hourly leaf wetness `lws0_pwet` and `lws1_pwet` (fraction of the hour wet, standard and canopy sensors) (**proxy**: RH ≥ 90% hours); the date of the last spray or of the start of accumulation (**have at points**; default the selected date minus 7 days).
- **Method:**
  - TOMCAST day: **12:00 (hour ending 12) to 11:00 the next day**. If hour 11 is wet, the day extends to hour 14; if hour 14 is also wet, the day goes back to ending at 11 and hours 12–14 go to the next day (`TomcastDay.php`). The next day starts the hour after the previous one ended.
  - Wet hour (`TomcastHour::isWet`): leaf wetness ≥ **0.25** of the hour, or RH ≥ **90%**, depending on flags; the strategy sets: RH off, sensor 0 on, sensor 1 off, RH as fallback where the sensor value is missing (but see the bug below).
  - Wet periods: a period ends after **two consecutive dry hours** (a single dry hour is bridged and not counted). Each period's mean temperature (°C, wet hours only, **rounded to a whole degree**) and wet-hour count give a partial DSV; the day's DSV is the sum over its periods.
  - DSV table (`TomcastWetPeriod::GetDSV`, lines 18–113, and the SQL in the comment at the end of `TomcastDay.php`): below 13 °C: 0. 13–17 °C: 0–6 h 0, 7–15 h 1, 16–20 h 2, 21+ h 3. 18–20 °C: 0–3 h 0, 4–8 h 1, 9–15 h 2, 16–22 h 3, 23+ h 4. 21–25 °C: 0–2 h 0, 3–5 h 1, 6–12 h 2, 13–20 h 3, 21+ h 4. 26–29 °C: 0–3 h 0, 4–8 h 1, 9–15 h 2, 16–22 h 3, 23+ h 4. Above 29 °C: 0.
  - Output: per TOMCAST day the DSV and the cumulative DSV since the start date; highlights: cumulative ≥15 "Caution 1", ≥18 "Caution 2", ≥20 "Caution 3"; a second table lists each hour.
- **Source:** none cited in the code (the method is Pitblado 1992's TOM-CAST, from Madden et al. 1978's FAST).
- **Overlap with ours:** `carrot-foliar-dsv` (TOMCAST, `models/carrot_foliar.py`) and `late-blight-dsv` (Wallin). Differences from `carrot-foliar-dsv`: ours counts **all hours with RH ≥ 90% in a day from 6 pm** and their mean temperature (no wet-period splitting); MSU sums DSV over separate wet periods within a **noon-to-11 am** day with the 11/14 hour split rule. Ours reads the 13–17 band as [13, 18) on unrounded temperature; MSU rounds each period's mean to a whole degree first (same effect). Ours keeps the 26–29 row **above 29 °C**; MSU gives **0 above 29 °C** (Pitblado's table also stops at 29). Ours: risk from the **last 7 days' total** (levels 5/10/15/20); MSU: **cumulative since the last spray** with caution at **15/18/20**, which is the TOMCAST spray-interval rule (spray when the total reaches the chosen threshold, then reset). Our carrot model could offer the since-spray total at points.
- **Notes (likely bugs):**
  - `TomcastDay.php` line 58: `$this->blnUseLW1 = $blnUseRelhIfLWIsNull;` overwrites the canopy-sensor flag and never sets `$this->blnUseRelhIfLWIsNull`, so in practice **the canopy sensor is used (OR'd with the standard one) and the RH fallback never applies**. A station without a leaf wetness sensor earns no DSV at all.
  - DSV table gaps: the code uses `> 21` and `> 23` where the table means `≥ 21` / `≥ 23`, so periods of exactly **21 h at 13–17 °C**, **23 h at 18–20 °C**, **21 h at 21–25 °C** and **23 h at 26–29 °C** fall through and return null (scored 0).
  - Highlights use `SumDSV > 15` (strict) while the legend says ≥ 15 (`TomcastStrategy.php` line 175).
  - When hour 14 is missing, the "hour 14" check uses whatever hour object was created last (comment: "does this work?").
  - Missing hours are skipped, not flagged; a day with missing data scores as if dry.
- **Upper Midwest relevance:** moderate: processing and fresh-market tomatoes are small in Wisconsin and Minnesota but significant in Michigan; the same method serves carrots (Wisconsin and Michigan processing carrots).

### VariegatedCutworm: Variegated cutworm

- **Predicts:** the first flight and start of egg laying of the overwintering generation, larval hatch of generation 1, then generation 1's flight and egg laying, and larval hatch of generation 2.
- **Crop and pest:** many vegetables and field crops (asparagus, tomato, potato, beans, mint, alfalfa…); variegated cutworm (*Peridroma saucia*).
- **Inputs:** daily Tmax and Tmin (**have**). No user inputs.
- **Method:** BE (single sine, no upper), base **45 °F**, from **March 1**. Events (cumulative): overwintering generation first flight **900**; egg laying begins **1070**; generation 1 larvae start to hatch **1202**; generation 1 first flight **2160**; egg laying begins **2330**; generation 2 larvae start to hatch **2500**.
- **Source:** none cited.
- **Overlap with ours:** `variegated-cutworm` (VDIFN): base **45 °F, upper 80.1 °F**, single sine, from **May 1**, one generation (start, peak, end) **(900, 1450, 2100)**. Differences: the same 900 DD first-flight number, but MSU counts it from **March 1** and ours from **May 1**, which puts ours later in the season by whatever March and April contribute (not measured here). One of the two start dates is likely a transcription change of the same source: worth finding the original. MSU adds egg laying, hatch and a second generation.
- **Notes:** none beyond the shared ones.
- **Upper Midwest relevance:** low to moderate: sporadic, but outbreaks damage mint, asparagus and vegetables.

### WinterWheatPhenology: Winter wheat phenology (stub)

- **Predicts:** nothing yet. The folder holds only design notes; there is no working model.
- **Crop and pest:** winter wheat; growth stages.
- **Inputs (as planned):** station, planting date (default September 1 of the previous year), selected date; daily Tmax and Tmin (**have**).
- **Method (as planned, from comments in `WinterWheatPhenologyInput.php` and `WinterWheatPhenologyStrategy.php`):** degree days **base 0 °C**, simple average **(max + min)/2 − 0**, computed in °C, accumulated from planting across the year boundary (planting 9/1/2022 with a selected date in 2023). **Green-up = the first 7 consecutive days with DD > 0.** Upper limits were still an open question ("think about how upper and lower limits work here"). A note suggests adding a rainfall tab.
- **Stage thresholds:** **none in the code.** No stage GDD values exist anywhere in the dump (searched for "wheat" across the whole repository: the only other hit is a TODO in `RainfallAccumulationStrategy.php` line 80 about year-crossing dates for winter wheat).
- **Source:** none cited.
- **Overlap with ours:** our wheat gap. `spring-wheat-stages` uses base 32 °F (0 °C) simple average with Tmax capped at 70 °F to Haun 2.0 and 95 °F after (Bauer et al. 1984, NDAWN). MSU's planned base 0 °C average is the same base. The one usable idea is the **green-up rule (7 consecutive days with DD > 0 °C)** as the spring restart for winter wheat; the stage table must come from elsewhere (e.g. Bauer et al.'s winter wheat work, or the MSU/OSU winter wheat GDD guides).
- **Notes:** dead folder: `WinterWheatPhenologyDefaults.php` is a single comment line.
- **Upper Midwest relevance:** moderate: winter wheat is a significant crop in Michigan (and soft red winter wheat in southern Wisconsin); less in Minnesota, where spring wheat dominates.

### CropEvapotranspiration: Crop water use for corn and soybean

- **Predicts:** daily and cumulative crop evapotranspiration (crop water use) from emergence for corn or soybean, with daily and total rain, percent of total growth and the crop coefficient.
- **Crop and pest:** corn (`Corn36`) and soybean (`Soybeans24`); water use.
- **Inputs:** daily `rpet` (reference ET from the station database) (**have**: our FAO-56 ET0 summed daily; see the method note); daily Tmax and Tmin (**have**); daily precipitation (**have**); emergence date (default **May 1**) (**have at points**); maturity length as days (corn default **110**, soybean default **150** days, allowed 30–200) or, for corn only, as GDD 86/50 (default **2300**, allowed 1000–3500) (**have at points**).
- **Method:**
  - Percent of total growth (PTG): days since emergence ÷ maturity days × 100, or GDD (86/50 method) since emergence ÷ maturity GDD × 100 (`Math::fnGetPTG`).
  - Crop coefficient Kc: looked up by PTG in a database table `kc` (rows per crop name at every **10% PTG**), linearly interpolated between the 10% steps; Kc = 0 outside 0–100%. **The Kc values are not in the dump** (the `kc` table lives in MSU's Postgres; we would need it from MSU).
  - Crop ET = Kc × RPET (mm), converted to inches; accumulated from emergence; rain accumulated from emergence. Calculation stops when PTG reaches 100%.
  - The ET method is not in this code: RPET is read pre-computed from the station database ("RPET" = reference potential evapotranspiration, MAWN). The code only multiplies it by Kc.
- **Source:** none cited.
- **Overlap with ours:** no crop-ET model; we have FAO-56 grass ET0 (hourly Penman-Monteith summed daily) and a water balance (precipitation − ET0). The PTG-based Kc curve is a simpler alternative to FAO-56's four-stage Kc (initial, development, mid, late) with lengths in days; ours would need either FAO-56's Kc table for corn and soybean (with Wisconsin stage lengths) or MSU's `kc` table. Note: if MSU's RPET is an alfalfa or other reference, its Kc values would not transfer to our grass ET0 without conversion.
- **Notes (likely bug):** line 154: `$pet = round($kc * $this->dailyWeather[$dateKey]['rpet']);` rounds the day's crop ET **in mm to a whole number** before converting to inches, so a 3.4 mm day becomes 3 mm and a 0.4 mm day 0. The old site's code (commented at lines 605 and 668) had `$pet = $kc * $rpet;` without rounding: a porting regression. Cumulative water use is distorted by up to ±0.5 mm a day. Also, the soybean input forces maturity in days only. The 86/50 maturity option reports "DD notes" with base 50.
- **Upper Midwest relevance:** high: corn and soybean dominate the region; irrigation scheduling matters on the Central Sands (Wisconsin) and in Michigan and Minnesota.
- **Feature idea:** crop water use (ETc) for corn, soybean and potato at a site from our ET0 with FAO-56 or MSU Kc curves, beside rain since emergence: the core of an irrigation scheduler (Wisconsin's WISP does this already).

### PotentialEvapotranspiration: Reference ET and rain table

- **Predicts:** a daily table of Tmin, Tmax, rain and RPET (reference potential evapotranspiration), each with its total since a start date (default **March 1**, or January 1 before March 1; user-settable).
- **Crop and pest:** none (reference ET).
- **Inputs:** daily Tmin, Tmax, precipitation (**have**); daily `rpet` (**have**, as our ET0; method unknown on MSU's side).
- **Method:** no calculation beyond sums: RPET and rain summed from the start date, converted to inches. **Which ET equation produces RPET is not in this code**: it is read pre-computed from the station database (MAWN), hourly and daily. The only FAO-56 references in the dump are in `Util/SolarRadiation/SolarRadiation.php` and `Util/Math/Math.php` (day length, FAO-56 equations 22, 24, 25, 34), used for day length, not for ET. So Penman-Monteith versus another method, and grass versus alfalfa reference, cannot be told from the dump; it must come from MSU (MAWN documentation).
- **Source:** none cited.
- **Overlap with ours:** our `et0` (FAO-56 grass reference Penman-Monteith, computed each hour and summed daily, with Rs/Rso held to 0.3–1 per ASCE-EWRI). Our ET0 with a precipitation total since a date already covers this page; the water balance (precipitation − ET0) goes further.
- **Notes:** `if ($atmp_min)` treats 0 °F as missing; `if ($rpet)` shows a 0 ET day as blank. Missing rain or RPET days add 0 to the totals with no count of missing days.
- **Upper Midwest relevance:** high, for irrigation and drought watching across the region.
- **Feature idea:** none new; we have it. Ask MSU which RPET equation MAWN uses before comparing numbers.

## Trees and landscape

**Shared mechanics for every tree and landscape model below** (read once, they apply to all seven):

- Degree days come from `GDDArray::gddAccumulate(dailyWeather, null, start, end, 'Baskerville-Emin', base, 212, 'atmp', 'F', 'C', 'C', 0)`: daily max/min air temperature at 1.5 m (stored in °C, converted to °F), single-sine (Baskerville–Emin, comment cites `http://agbioresearch.msu.edu/nwmihort/be_method.pdf`), upper 212 °F (that is, no upper threshold). Our sine method with no upper is the same thing.
- A stage date is `GDDArray::gddGetDateMatch` (`app/Util/GDD/GDDArray.php:30-86`): sums each day's `single` from the start date **inclusive**, and returns the first day the sum is ≥ the goal. A day with no `single` value is skipped (adds 0) rather than stopping the count (lines 66-72); whether a gap was estimated upstream depends on `gddAccumulate`'s estimation, which keeps `estimatedArray`/`missingArray`.
- Start date is March 1 of the selected date's year, hard-coded (`StartAccumulation = '3/1/'`), no user override except Tussock moth's biofix. A date before March 1 is refused ("Choose a date after 3/1 to see model results.").
- Output is a table of stages: a range row reads "Name (A to B DD after 3/1)" with "M/D through M/D" (or expected), a single row "Occurred on"/"Expected on"; the current row is highlighted, with a 7-day timeout on the last row. Forecast days count (the DD shown is through the forecast's last day when there is one). No risk logic; these are calendars.
- All are weather-only (daily max/min air temperature): **have** for every one.

### CooleySpruceGallAdelgid: Cooley spruce gall adelgid

- **Predicts:** three overlapping activity windows for timing sprays against the overwintering generation.
- **Crop and pest:** spruces (Colorado blue, Engelmann; alternate host Douglas-fir), *Adelges cooleyi*.
- **Inputs:** daily max/min air temperature (**have**). No user inputs.
- **Method:** DD50 °F, Baskerville–Emin, no upper, from March 1 (`CooleySpruceGallAdelgidStrategy.php:24-39`).
  - Adult activity and egglaying begins: 25 to 120 DD.
  - Egg hatch and feeding by nymphs: 150 to 310 DD.
  - Gall formation begins: 200 to 310 DD.
  Header comment: the DD marks come from the old QPanel class and the text from the old template; two stages share the 310 end.
- **Source:** none cited in code.
- **Overlap with ours:** none.
- **Notes:** Parity fixture in `tests/ResultModelsOnlineStatic/CooleySpruceTest.php`: Romeo (`rom`), select date 2012-06-03 gives 3/14–3/22, 3/25–5/7, 4/16–5/7 (2012 was a record-warm March). The 25 DD start is tiny: a few warm February-like days in early March reach it, which makes the first window sensitive to the start date and to the sine method.
- **Upper Midwest relevance:** spruce is a major Christmas-tree, nursery and landscape tree in WI/MI/MN; this adelgid is a common but cosmetic pest. Low–moderate.

### EasternSpruceGallAdelgid: Eastern spruce gall adelgid

- **Predicts:** five activity windows, the last open-ended.
- **Crop and pest:** spruces (Norway, white, Colorado blue), *Adelges abietis*.
- **Inputs:** daily max/min air temperature (**have**).
- **Method:** DD50 °F, Baskerville–Emin, no upper, from March 1 (`EasternSpruceGallAdelgidStrategy.php:24-47`).
  - Adult activity and egglaying begins: 25 to 100 DD.
  - Egg laying period: 100 to 250 DD.
  - Egg hatch and feeding by nymphs begins: 150 to 250 DD.
  - Egg hatch and nymph feeding period, gall formation begins: 250 to 310 DD.
  - Galls are visible: from 310 DD (no end; a single-date row worded "Started on").
- **Source:** none cited.
- **Overlap with ours:** none.
- **Notes:** The windows overlap (egg laying 100–250 and egg hatch 150–250). Same 25 DD sensitivity as Cooley. Row type is chosen by `property_exists($this, $markVarEnd)` (line 388), which works only because `DDMark_GallsEnd` is not declared.
- **Upper Midwest relevance:** as Cooley; low–moderate (nursery, Christmas trees, landscape).

### FletcherScale: Fletcher scale and euonymus scale

- **Predicts:** crawler windows (the stage to spray) for two scales.
- **Crop and pest:** Fletcher scale (*Parthenolecanium fletcheri*) on arborvitae and yew; euonymus scale (*Unaspis euonymi*) on euonymus.
- **Inputs:** daily max/min air temperature (**have**).
- **Method:** DD50 °F, Baskerville–Emin, no upper, from March 1 (`FletcherScaleStrategy.php:23-39`).
  - Euonymus scale, first generation egg hatch, crawlers appear: 400 to 575 DD.
  - Euonymus scale, second generation crawlers appear: 1900 to 2050 DD.
  - Fletcher scale, first generation egg hatch, crawlers appear: 730 to 900 DD.
  Rows carry photos (credits Diane Brown-Rytlewski and Dave Smitley, MSU).
- **Source:** none cited.
- **Overlap with ours:** none.
- **Notes:** The folder is named for Fletcher scale but two of its three rows are euonymus scale. Empty spacer rows (`varName => null`) only lay out the table.
- **Upper Midwest relevance:** landscape and nursery (arborvitae, yew, euonymus); low.

### FraserFirGrowth: Fraser fir shoot growth

- **Predicts:** percent of the season's shoot elongation reached, and dates of 10, 50, 90 and 100 % growth; useful for timing shearing and for knowing when new growth is frost-sensitive or done.
- **Crop and pest:** Fraser fir (*Abies fraseri*) Christmas trees; a crop-growth model, no pest.
- **Inputs:** daily max/min air temperature (**have**).
- **Method:** DD41 °F, Baskerville–Emin, no upper, from March 1 (`FraserFirGrowthStrategy.php:24-49`). Growth is a logistic in DD (lines 251-256):
  `y = 0.0035 * DD - 5.1939`, `percent = 100 * exp(y) / (1.01 + exp(y))`.
  Stage goals (lines 46-49): 10 % at 859 DD, 50 % at 1487, 90 % at 2115, "100 %" at 3000 (added 8/22/2019). Checked: the logistic gives 10.0, 50.0, 90.0 and 99.50 % at those totals, so the goals are the curve's own points (comment: "these numbers were calculated. 850,1490,2100 close enough?"). Status rows "Shoot growth on M/D: N% growth." for the select date and the forecast's last date; above 99.5 % the text is "All growth is completed for the season." The forecast status row is shown only if the forecast date is on or before October 1 (`EndStatus = '10/1/'`) and the select-date row was not already complete.
- **Source:** none cited in code.
- **Overlap with ours:** none (our phenology models are field crops).
- **Notes:** The `1.01` makes the curve's ceiling 100/1 = 100 % only asymptotically; 100 % is never reached, hence the 3000 DD "100 %" row and the 99.5 % cutoff. `blnAllGrowthCompleted` is set as a side effect of building the select-date row, so the forecast row depends on row order. Parity fixture (`tests/ResultModelsOnlineStatic/FraserFirGrowthTest.php`): Arlene (`arl`) 2018, select 9/30: 10 % 6/8, 50 % 7/1, 90 % 7/22, 100 % 8/20; 3914 DD41 by 9/30 (7 estimated days). That fixture's expected table has no status rows, so it predates them or the test is stale.
- **Upper Midwest relevance:** Fraser fir is a major Christmas tree species in Michigan and Wisconsin, both sizeable Christmas-tree states (from general knowledge, not checked); moderate for that industry.

### MultipleLandscapeInsects: spongy moth, black vine weevil, cottony maple scale, magnolia scale

- **Predicts:** the treatment-timing stage for four landscape pests. Result code is still `gypsymothblackvineweevilcottonymaplescaleandmagnoliascale`; the text was renamed to spongy moth.
- **Crop and pest:** landscape trees and shrubs. The complete list (`MultipleLandscapeInsectsStrategy.php:35-48`), DD50 °F after March 1:

  | Pest | Event | Start DD | End DD |
  | --- | --- | --- | --- |
  | Spongy moth (*Lymantria dispar*) | Eggs hatch | 100 | 201 |
  | Black vine weevil (*Otiorhynchus sulcatus*) | Adults emerge | 560 | (none: a single date, highlighted 7 days) |
  | Cottony maple scale (*Pulvinaria innumerabilis*) | Eggs hatch; crawlers appear | 802 | 1200 |
  | Magnolia scale (*Neolecanium cornuparvum*) | Eggs hatch; crawlers appear | 1925 | 1950 |

  That is every pest in the folder (four, not a long table).
- **Inputs:** daily max/min air temperature (**have**).
- **Method:** DD50 °F, Baskerville–Emin, no upper, from March 1. Table rows with photos (Bugwood/USDA Forest Service, University of Delaware, MSU); the dashboard copy drops the images. Highlighting is `GetBasicHighlightKey`, not the single-current-row highlighting the other models use (comment: "do these need highlighting?? weird one").
- **Source:** none cited. Image links `http://www.ipmimages.org/browse/detail.cfm?imgnum=1929099` and `...imgnum=5429848`.
- **Overlap with ours:** none (our `japanese-beetle` is the only landscape pest we have, and it is not here).
- **Notes:** `strEvent0` ("Eggs have not yet hatched") and the commented-out `GetDashboardString` (a 12-stage loop over `DDMark1..12`) are dead code from an older, longer version of this model. Magnolia scale's window is 25 DD wide (one or two days). Parity fixture (`tests/ResultModelsOnlineStatic/MultipleLandscapeInsectsTest.php`), Albion (`alb`) 2018: spongy moth 5/2–5/10, black vine weevil 6/1, cottony maple scale 6/16–7/3, magnolia scale 8/6–8/7.
- **Upper Midwest relevance:** spongy moth is a significant forest and landscape pest across Wisconsin and Michigan (state suppression programs time sprays to egg hatch and early larvae), so that row matters most; the others are minor landscape pests. Moderate for spongy moth, low for the rest.

### PineSawflyPineNeedleScale: European pine sawfly and pine needle scale

- **Predicts:** sawfly egg hatch and the two pine needle scale crawler generations.
- **Crop and pest:** pines (Scotch, red, mugo; Christmas trees and landscape); European pine sawfly (*Neodiprion sertifer*) and pine needle scale (*Chionaspis pinifoliae*).
- **Inputs:** daily max/min air temperature (**have**).
- **Method:** DD50 °F, Baskerville–Emin, no upper, from March 1 (`PineSawflyPineNeedleScaleStrategy.php:26-60`):
  - European pine sawfly, eggs hatch, first larvae appear: 100 to 195 DD.
  - Pine needle scale generation 1, eggs hatch, crawlers expected soon: 225 to 250 DD.
  - Pine needle scale generation 1, eggs hatch, crawlers appear: 250 to 400 DD.
  - Pine needle scale generation 2, eggs hatch, crawlers expected soon: 1200 to 1250 DD.
  - Pine needle scale generation 2, eggs hatch, crawlers appear: 1250 to 1350 DD.
  Photos credited to Jill O'Donnell and Howard Russell, MSU. A commented block at the end (lines 281-329) keeps the old site's "Current stage" sentences for nine dates.
- **Source:** none cited.
- **Overlap with ours:** none.
- **Notes:** Header comment says "both start and end of periods are NOT ALWAYS defined", but every stage here has an end. The "expected soon" rows are 25 and 50 DD wide.
- **Upper Midwest relevance:** pines for Christmas trees (Michigan, Wisconsin) and landscapes; low–moderate.

### TussockMoth: white-marked tussock moth (in blueberry)

- **Predicts:** a season calendar with two treatment windows: generation 1 control at bloom, and, if the user gives a biofix (first sustained moth catch), generation 2 treatment.
- **Crop and pest:** the text ("bee-safe insecticide at mid-late bloom", "larvae at harvest", "monitoring bushes through harvest") is for highbush blueberry; white-marked tussock moth, *Orgyia leucostigma* (WMTM).
- **Inputs:** daily max/min air temperature (**have**); optional biofix = first sustained trap catch (**missing** as data; possible as a user date at a point). Not estimated if absent.
- **Method:** DD55 °F (base 55, not 50), Baskerville–Emin, no upper (`TussockMothStrategy.php:78-136`).
  From March 1:
  - Generation 1 egg hatch: 100 DD ("If field had WMTM problems last year, remove and destroy egg masses before egg hatch"); shown as "Occurred on".
  - Generation 1 control period: 300 to 500 DD ("Treat with IGR or other bee-safe insecticide at mid-late bloom…"; marked as the typical treatment timing).
  - Generation 2, start monitoring with pheromone traps: 500 DD ("Set traps by").
  - Generation 2, continue monitoring bushes through harvest: 1000 DD.
  From the biofix (only if given; biofix must be on or after March 1, same year):
  - A row showing the biofix date.
  - Generation 2 treatment: 350 to 450 DD55 after the biofix, the biofix day counted ("Treat field, using excellent coverage and an insecticide active on moth larvae"; typical treatment timing).
- **Source:** none cited.
- **Overlap with ours:** none. `models_with_multiple_start_dates.txt` lists it as a model with two DD starts.
- **Notes:** Likely bug: `Calculate()` calls `CalculateDDNotes` twice (lines 316-330); the second call, from the biofix, overwrites `DDMark_selectDate` and `DDMark_forecastDate`, so with a biofix the result's `DD_selectDate` (the "DD to date" figure) is DD since the biofix, not since March 1. Wording oddity: Gen1 egg hatch's past and future texts are both "Occurred on", so a forecast date reads "Occurred on M/D (forecast)" (the code keeps the alternative wording commented out). The "Replace on" string trick (lines 459-483) rewrites the generic prediction text. The asterisk footnote is HTML with a Font Awesome icon in the model.
- **Upper Midwest relevance:** Michigan is a top highbush blueberry state; Wisconsin and Minnesota grow little. Low for Wisconsin, moderate for Michigan.

## Displays

### DegreeDayHistorical: degree days this year against past years at one station

- **Shows:** DD totals from a start date (default January 1) to the select date, in each of the last 5 years (default), 10 years or the station's full record, for bases 32, 40, 42, 45 and 50 °F (fixed list, `DegreeDayHistoricalInput.php:33`), by method `be` (sine), `avg` or `ni` (hourly numerical integration). Each year carries data notes: invalid, estimated and missing days (or hours for `ni`). Reads precomputed daily sums (`gdd_multi` table, `query for historical.txt`).
- **Inputs:** precomputed daily DD per base and method.
- **Calculation worth knowing:** the `ni` method integrates hourly temperatures above the base (`GDDSingle::fnGDD_NumericalIntegration`).
- **Feature idea:** v2's `/climate/compare` and past-years copies cover the comparison. v2 has no **hourly-integrated degree-day method** (ours: sine, average, modified); we have hourly temperatures, so it could be added as a method if a model calls for it. Per-year data notes (missing/estimated day counts beside each year) are worth copying into a year-by-year table.

### DegreeDayMap: base-50 degree-day maps

- **Shows:** four pre-rendered PNG maps for the date: cumulative DD50 (sine) since March 1; the 1981–2010 normal; difference from normal in days; difference from normal in DD. The dashboard shows the "in days" map.
- **Inputs:** daily max/min air temperature; a normal.
- **Calculation worth knowing:** "heat accumulation compared with normal in days" (how many days ahead or behind).
- **Notes:** `CalculateDDNotes` is commented out (`DegreeDayMapStrategy.php`, `Calculate()`), so `DD_selectDate`/`DD_forecastDate` in the result are never set: the dashboard's DD figure is always empty. Normal period is 1981–2010.
- **Feature idea:** none new: v2 has degree-day maps, `departure` climate maps and `days_ahead` in `/climate/compare`. A **days-ahead map** (not only at points) is the one piece to check v2 has.

### DegreeDayRegional: degree days at nearby stations

- **Shows:** DD since a start date (default January 1) at bases 32, 40, 42, 45, 50 °F, method `be`/`avg`/`ni`, for a group of stations (`single`, `closest5`, `closest10`, `closest15`, `watched`, `network`), with a forecast total when the date is today, data notes and links. Also a GeoJSON feature collection for a map.
- **Inputs:** precomputed daily DD.
- **Notes:** `$yesterday = $this->selectDate->addDays(-1)` (`DegreeDayRegionalSingleDatabaseTableStrategy.php:149`) mutates the select date itself (Carbon is mutable), a likely off-by-one in anything that reads it afterwards.
- **Feature idea:** v2's maps cover space. A "my saved sites side by side" table (one row per site, same settings) is the equivalent for growers with several farms.

### DegreeDaySeasonal: degree days over standard windows

- **Shows:** DD at one base (32/40/42/45/50 °F, default 50) and method, for windows ending on the select date: since January 1, since March 1, the last 6 months, 3 months, 1 month, 2 weeks and 1 week (windows starting before January 1 are dropped). Either for nearby stations or for this station's past 5/10/all years.
- **Inputs:** precomputed daily DD.
- **Notes:** March 1 is included if `!$mar1->isFuture()` (line 94), tested against today rather than the select date, so for a past January–February date March 1 (after the select date) is still added. The same select-date mutation as Regional (line 191).
- **Feature idea:** **trailing-window totals** (last 7, 14, 30 days) for DD and rain as a ready-made table; v2's `/weather/totals` can compute any window but has no preset set of them.

### Inversion3m: temperature inversion from a 3 m sensor

- **Shows:** for stations with a 3 m and a 45 cm air temperature sensor, the latest five-minute reading (at most one hour old, else "No data since …"): whether there is an inversion and its strength, on a map and table.
- **Inputs:** 5-minute air temperature at 3 m, 45 cm and 1.5 m (**missing**: we have one level, 2 m).
- **Calculation worth knowing** (`Inversion3mStrategy.php`, `Calculate()`): `diff = T(3 m) − T(45 cm)` in °F (each rounded to 0.1 first). `diff ≤ 0`: "No Inversion"; `0 < diff < 1 °F`: weak inversion; `diff ≥ 1 °F`: strong.
- **Notes:** typo `$dataRow['forecast_link_obj']` and `$dataRow['dod_link_obj']` (should be `$data_row`), so the forecast and Data on Demand links are never added.
- **Feature idea:** v2 has no **spray-drift inversion guidance**. Without a second sensor height it would need a proxy (evening to morning, clear sky, light wind, falling temperature) or a model level (check whether HRRR's files carry a temperature above 2 m that we could read); a spray-conditions summary (wind speed and gusts, temperature, humidity, inversion likelihood, rain-free hours) would be new. Any rule would need a cited source; Enviroweather's rules here are station-based only.

### LatestObsRegional: latest observations at nearby stations

- **Shows:** the latest observation row for a group of stations from a precomputed table (`latestobs2` in `is4db`), with last and next update times, station status messages and links.
- **Inputs:** station observations.
- **Feature idea:** a "current conditions" panel at saved sites from the newest analysis hour; and short **data status notices** per area when a source is late, as Enviroweather's per-station status messages do.

### Meteogram: one station's recent observations (standard and 20 m tower)

- **Shows:** five-minute and hourly table of air temperature, RH, dew point, rain, hourly reference ET (RPET), wind speed and direction, wind chill, heat index, leaf wetness (wet/dry), solar and net radiation, battery voltage; tower stations add air at 10 cm, 10 m, 20 m and soil at 5 and 10 cm.
- **Inputs:** station five-minute data.
- **Calculations worth knowing:**
  - 20 m tower inversion (`Meteogram20mTowerObservation.php:94-105`): `T(20 m) − T(1.5 m) ≥ 2 °F` flags an inversion and shows its strength; below 2 °F nothing is shown (null, displayed "N/A", not "no"). Note the different threshold from Inversion3m (> 0, strong ≥ 1 °F).
  - Dew point (`app/Util/Temperature/Temperature.php:13-29`): saturation vapor pressure `0.61078·exp(17.269·T/(T+237.3))`, actual = RH/100 × that, `Td = (116.9 + 237.3·ln e)/(16.78 − ln e)`.
  - Heat index (lines 31-57): the Rothfusz regression only when T ≥ 80 °F, RH ≥ 40 % and Td ≥ 60 °F; if T ≥ 80 otherwise, the air temperature; else none. No NWS low-RH or high-RH adjustments.
  - Wind chill (lines 59-78): NWS 2001 formula `35.74 + 0.6215T − 35.75V^0.16 + 0.4275TV^0.16`, only below 50 °F and above 3 mph, with the 3 m station wind scaled to 10 m by ×1.365 (`app/Util/Wind/Wind.php`, "email from Jeff Andresen 3/30/2021"; the older log-profile scaling is kept as `fnScaleWindSpeed_oldAsOfApril2021`).
- **Feature idea:** v2 shows hourly weather but no **heat index or wind chill** (useful for livestock and field work; our wind is already 10 m, so no scaling). Hourly ET0 is already ours.

### OvernightTemperatures: frost watch for tonight

- **Shows:** for a station or group, hourly average air temperature from 10–11 p.m. to 9–10 a.m., the lowest five-minute temperature in each hour, hourly dew point from 4–5 p.m. to 9–10 a.m., the night's lowest dew point and its hour, and the NWS forecast minimum. The page switches to the coming night at 5 p.m. (`OvernightTemperatureModel::HourForDateSwitch = 17`).
- **Inputs:** hourly air temperature and dew point (**have**), a forecast minimum (**have**).
- **Calculation worth knowing:** cells are colored at three thresholds (`OvernightTemperaturesSingleDatabaseTableStrategy.php:66-68`): at or below 32 °F yellow, 30 °F orange, 28 °F red; applied to both temperatures and dew points (the legend says "lower than", the code uses `<=`). The evening dew point is shown as a guide to how low the night can fall.
- **Feature idea:** a **frost night view** at saved sites: tonight's hourly forecast temperatures and dew points with 32/30/28 °F marks (v2 has these thresholds as `frost`, `hard_freeze`, and 24 °F `killing_freeze`, and hourly forecasts, but no overnight page or alert built on them). Fits fruit growers, cranberry and vegetable transplants.

### RainfallAccumulation: rain since a date

- **Shows:** daily rain and the running total from a user date (default January 1) through the precipitation forecast's days, forecast days highlighted.
- **Notes:** missing days add 0 to the total with no count of missing days (v2's D45 already reports them).
- **Feature idea:** none (v2 has it).

### RainfallHistorical: rain this year against past years

- **Shows:** rain totals from a start date to the select date in each of the past 5/10/all years, plus **hours with rain** and **leaf-wetness hours** (standard and canopy sensors) over the same window, with data notes.
- **Feature idea:** a "rain hours" count (hours with measurable precipitation) is easy from our hourly precipitation and is a better wetness signal than daily totals; leaf-wetness hours we can only give as RH proxies.

### RainfallRegional: rain at nearby stations

- **Shows:** rain since a date, rain hours and leaf-wetness hours, for a group of stations, with a forecast total when the date is today.
- **Notes:** the same `selectDate->addDays(-1)` mutation (line 114).
- **Feature idea:** as DegreeDayRegional (saved sites side by side).

### RainfallSeasonal: rain over standard windows

- **Shows:** rain since January 1, March 1, the last 6, 3 and 1 months, 2 weeks and 1 week; plus rain hours and leaf-wetness hours; for nearby stations or past years.
- **Notes:** the same March 1 `isFuture()` check against today (line 96) and select-date mutation (line 191) as DegreeDaySeasonal.
- **Feature idea:** trailing-window rain totals beside the DD ones, with departures from normal (v2 has the normals).

### Regional: station picker

- **Shows:** nothing on its own; `GeometryNearDefaults` returns the station list and map features for the selectors `single`, `closest5`, `closest10`, `closest15`, `watched` (the user's stations), `network`.
- **Feature idea:** v2 has no stations, but "compare my sites" (all saved sites in one table) is the analogue; area averaging (`radius`) is the grid's answer to "the stations around me".

### SoilConditions: soil temperature and moisture table

- **Shows:** daily min/max air temperature, daily rain and its running total from a date (default January 1), min/max soil temperature at 2 in (5 cm) and 4 in (10 cm), and min/max soil moisture (0–12 in and 12–24 in from the older `mstr` sensors, or 4, 8 and 20 in from `smst`), choosing between the two sensor families by fewer invalid days (`ChooseBetterSensor`).
- **Inputs:** soil temperature (**have**: 4 cm, 10 cm, 30 cm, 8 in), soil moisture (**missing**, planned).
- **Calculation worth knowing:** none: there is **no workability, planting or frost rule**, only the table.
- **Notes:** `if ($atmp_min)`-style tests treat an exact 0 as missing, so a 0.0 °F reading (and any 0 soil moisture) shows as blank. Missing rain days count as 0 in the total.
- **Feature idea:** v2 could do better than this page: soil temperature thresholds for planting (first day the 4 in soil stays above 50 °F, already possible with `first=` bounds), and soil moisture once it lands.

### WeatherSummary: daily weather and degree-day table

- **Shows:** per day: min, max and average air temperature, average RH, leaf-wetness hours (sensor), daily and cumulative rain from a date, and degree-day columns (daily and since a start). Defaults (`WeatherSummaryMainInput.php`): DD32, 40, 42, 45 and 50 °F, sine, no upper, from January 1; rain from January 1. A logged-in user's saved settings replace them (base, upper, method `be`, `avg`, `ni` or `8650`, start date, per column). The field-crops variant (`WeatherSummaryFieldCropsStrategy.php`) is fixed to DD41 °F simple average from March 1 and modified 86/50 °F from January 1 (or the user's corn date), with rain from January 1 or a user date. A historical variant (`WeatherSummaryHistoricalCollector`, `SingleRowStrategy`) gives the same totals to the same date in each past year and their average across years.
- **Calculations worth knowing:**
  - Average temperature = (min + max)/2; average RH = (RH min + RH max)/2, a crude daily RH.
  - Leaf-wetness hour: an hour whose sensor fraction wet is ≥ 0.25 (`LeafWetness::CountHoursOfLeafWetness`, threshold 0.25).
  - `8650`: max capped at 86, min raised to 50, then the average method base 50 (`GDDSingle::fnGDD_8650`), our "modified" method.
- **Feature idea:** **saved summary settings per user** (several DD columns with their own base, upper, method and start) is the useful part; v2's `/degree-days/table` takes settings per request, so the frontend needs a way to save a set per site. A "DD41 simple average from March 1" column is one we would get from custom degree days already.
