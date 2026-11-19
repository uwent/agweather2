---
id: carrot-foliar-dsv
status: draft
updated: 2026-11-19
summary: Scores each day's weather for Alternaria and Cercospora leaf blights of carrot in disease severity values (TOMCAST), from the hours of high humidity and their temperature, and rates risk from the last 7 days' total.
sources:
  - Madden, Pennypacker and MacNab 1978 (FAST's table of disease severity values, Pennsylvania)
  - Pitblado 1992 (TOMCAST, Ontario)
  - UW Vegetable Pathology's carrot Alternaria and Cercospora leaf blight page (what to do when risk is high)
  - Rogers and Stevenson 2006 (spray programs by severity values on carrot, Wisconsin)
  - Bounds, Podolsky and Hausbeck 2007 (a 15-value program on carrot, Michigan)
  - Midwest Vegetable Production Guide 2026 and Cornell's carrot leaf blight fact sheet (15 values between sprays)
  - The Crop Risk Tool's and VDIFN's carrot foliar model (the risk levels; compared)
---

## What it predicts

Alternaria and Cercospora leaf blights kill carrot leaves and weaken their stalks in warm, wet weather, so tops can break off at harvest. Both are favored by the same weather, and one model serves both. It scores each day by the TOMCAST method and shows:

- **Disease severity values (DSVs)**: each day's score, from 0 (unfavorable) to 4 (very favorable).
- **The last 7 days**: the DSVs of the past week, which set the risk.
- **The total since your start date**: DSVs since planting or your last fungicide spray.

## How it works

- **Daily values.** TOMCAST (Pitblado 1992) scores days with the table of FAST, a forecaster Madden, Pennypacker and MacNab built for early blight of tomato (1978). It counts the hours with relative humidity of 90 % or more, and their mean temperature, over the day from 6 p.m. CST the evening before. Below 55 °F (13 °C) a day earns nothing. The warmer the humid hours, up to about 79 °F, the fewer it takes: from 70 to 79 °F (21 to 26 °C), 3 humid hours earn 1 value and 21 or more earn 4. Above 79 °F the hours needed rise again.
- **Humid hours.** We have no leaf wetness sensors, so hours of high humidity stand in for wet leaves. Gridded humidity reads slightly low, so an hour counts as humid at 88 % rather than 90 %.
- **The start.** The total counts from planting or your last fungicide spray, June 1 unless you enter your own date at a location. The model runs from June 1 to September 30.
- **Risk levels** follow the last 7 days' total, as the Crop Risk Tool and VDIFN set them: **Very low** below 5, **Low** from 5, **Moderate** from 10, **High** from 15 and **Very high** from 20.

## How to read it

- UW Vegetable Pathology advises starting a preventive fungicide spray, or watching the crop closely for disease, when risk is high. Scout weekly from emergence, checking leaves and leaf stalks for spots.
- Guides and trials time sprays by the total since the last spray instead. The Midwest Vegetable Production Guide uses a total of 15 DSVs, and Cornell suggests spraying again once more than 15 have built up since the last spray. In Wisconsin trials, spraying after each 15 to 20 DSVs cut fungicide use by 30 to 50 % from weekly sprays without losing control or yield. To follow such a program, enter your last spray date and watch the total, not the risk level.
- See the [Alternaria](/topics/carrot-alternaria-leaf-blight) and [Cercospora](/topics/carrot-cercospora-leaf-blight) leaf blight topic pages for when to start, fungicide choices and resistance management.

## Validation and caveats

- Draft (model version 0.4, beta). Our daily values follow FAST's published table at every whole hour in each of its temperature bands, checked in a test. The Crop Risk Tool's table needed an hour more than FAST's for the first value in its two cooler bands and placed the band edges a degree differently; we follow FAST. On the tool's own inputs for 2025 at a location near Eau Claire, this changed 2 days, from 99 to 101 DSVs between May 15 and September 30. Given the same inputs, our values otherwise match the tool's.
- The risk levels come from the 7-day total, as the tools this model replaces had them. The guides and the Wisconsin and Michigan trials time sprays by 15 to 20 DSVs since the last spray, so the risk level and a spray program can disagree: a High week that began before a recent spray may not call for another, and a total can reach 15 over several weeks while each week stays Low or Moderate. Nothing yet ties the 7-day levels to carrot leaf blight in Wisconsin fields.
- FAST's table stops at 29 °C (84 °F). Above it, we keep scoring as in the warmest band, as the Crop Risk Tool did, while MSU's Enviroweather scores such days 0. Whether TOMCAST itself scores them hasn't been checked in Pitblado's report. Humid periods that warm are rare in Wisconsin's carrot season.
- FAST and TOMCAST were developed for early blight of tomato. Their use for carrot leaf blights rests on extension practice and trials, not on a comparison here.
- Humid hours stand in for leaf wetness, and the model adds up all the humid hours in a day, where FAST scores each wet period separately. Irrigated fields stay wet longer than the weather data show.
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your field.
