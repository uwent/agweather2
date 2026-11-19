---
id: degree-days
title: Degree days
kind: weather
crops: []
scientific_name: ''
summary: A measure of the heat a crop or insect has received, used to predict growth stages and insect activity more reliably than the calendar; this page explains how degree days are counted and how to use them.
image: null
image_credit: null
status: draft
updated: 2026-11-19
sources:
  - key: uw-vegento-predictive
    text: 'Predictive Modeling. UW–Madison Vegetable Entomology, 2026.'
    url: https://vegento.russell.wisc.edu/ipm/predictive-modeling/
  - key: delahaut
    text: 'Delahaut, K. Calculating Degree Days (XHT1086). UW–Madison Division of Extension, Wisconsin Horticulture.'
    url: https://hort.extension.wisc.edu/articles/degree-day-calculation
  - key: ucipm-concepts
    text: 'Degree-Days: About Degree-Days. UC Statewide IPM Program, University of California, revised 2016.'
    url: https://ipm.ucanr.edu/WEATHER/ddconcepts.html
  - key: osu-methods
    text: 'Degree-Day Calculation Methods. Oregon IPM Center, Oregon State University.'
    url: https://hopper.science.oregonstate.edu/CalcMethods.html
  - key: nielsen-heat
    text: 'Nielsen, R. L. Heat Unit Concepts Related to Corn Development. Purdue University, updated 2020.'
    url: https://www.agry.purdue.edu/ext/corn/news/timeless/heatunits.html
  - key: newa-dd
    text: 'About Degree Days. NEWA, Cornell University, 2020.'
    url: https://newa.cornell.edu/about-degree-days
  - key: dean-hodgson
    text: 'Dean, A. and E. Hodgson. Growing Degree Days for Insect Pests. Iowa State University Extension and Outreach, reviewed 2026.'
    url: https://crops.extension.iastate.edu/encyclopedia/growing-degree-days-insect-pests
  - key: becker-2024
    text: 'Becker, F. Use Tools To Help Prepare For Pest Damage To Fields, Crops. Ohio State University Extension, Wayne County, 2024.'
    url: https://wayne.osu.edu/news/use-tools-help-prepare-pest-damage-fields-crops
  - key: baskerville-1969
    text: 'Baskerville, G. L. and P. Emin. Rapid estimation of heat accumulation from maximum and minimum temperatures. Ecology 50:514–517, 1969.'
    url: https://doi.org/10.2307/1933912
  - key: agweather-custom-dd
    text: 'AgWeather. Custom degree days model: validation report. UW–Madison, 2026.'
    url: https://github.com/uwent/agweather2/blob/main/docs/validation/models/custom-degree-days.md
---

Insects and crops can't control their own temperature, so they grow faster in warm weather and slower in cool weather, and below a certain temperature they hardly develop at all. Degree days measure the heat they receive. Because they follow the weather of each year, they predict an insect's emergence or a crop's growth stage more reliably than the calendar, and with a forecast they can look ahead.[^uw-vegento-predictive] Growing degree days (GDD) are the same idea, usually for crops; the term most often means degree days above 50 °F.[^newa-dd] This page explains how degree days are counted, why totals from different sources can differ, and how to use them.

## What a degree day is

One degree day is one day with the temperature one degree above the base temperature. A day averaging 60 °F, with a base of 50 °F, adds 10 degree days.[^ucipm-concepts][^delahaut] Days are added into a running total, and each stage of an insect or crop is reached at a known total.[^uw-vegento-predictive]

- **Base (lower threshold):** the temperature below which the organism stops developing. It differs by species: 50 °F for corn and many insects, 48 °F for alfalfa weevil, and as low as 39 °F for seedcorn maggot.[^ucipm-concepts][^newa-dd]
- **Upper threshold:** the temperature above which development no longer speeds up. Many insects use about 90 °F; corn uses 86 °F.[^dean-hodgson][^nielsen-heat]
- **Cutoff:** what happens above the upper threshold. A **horizontal cutoff** assumes development goes on at its top rate, so the hottest part of the day counts as if it were at the threshold. A **vertical cutoff** assumes development stops entirely while the temperature is above it. An intermediate cutoff assumes it slows.[^ucipm-concepts][^osu-methods]

A degree-day total only means something with the base, upper threshold and method the model was built with. Use the same ones as the research behind the model you follow.[^ucipm-concepts]

## How degree days are calculated

Most weather records give only each day's minimum and maximum temperature, so every method estimates how the temperature moved between them. They differ in that estimate.[^osu-methods]

- **Simple average:** the average of the minimum and maximum, minus the base, with a negative result counted as zero. It is easy to work out by hand.[^delahaut][^newa-dd]
- **Modified average:** the corn method. Before averaging, a minimum below the base is raised to the base, and a maximum above the upper threshold is lowered to it. For corn the thresholds are 50 and 86 °F.[^nielsen-heat]
- **Single sine:** the day's temperature is drawn as a smooth curve through the minimum and maximum, and the degree days are the area of the curve above the base (and below the upper threshold). This is Baskerville and Emin's method.[^baskerville-1969][^osu-methods]
- **Double sine, and single and double triangle:** variations that also use the previous day's maximum, or straight lines in place of the curve. They tend to give values close to the single sine.[^osu-methods]

Totals differ most on cool days, when the temperature crosses the base for only part of the day. Take a day of 45 and 65 °F with a base of 50 °F: the simple average gives 5 degree days, the single sine about 6.1, and the modified average 7.5, because it raises the minimum to 50.[^agweather-custom-dd] The sine method follows these days better, which matters most in spring, when temperatures hover near the base.[^uw-vegento-predictive] Over a season these daily differences add up, so totals from two calculators can disagree even on the same weather.

## Fahrenheit and Celsius

A Celsius degree is larger than a Fahrenheit degree, so a Celsius degree day is too: 9 Fahrenheit degree days make 5 Celsius degree days.[^ucipm-concepts] A total of 900 °F degree days is 500 °C degree days. Thresholds convert as temperatures do (50 °F is 10 °C). Many models in the United States use Fahrenheit degree days; some, such as NEWA's cabbage maggot model, use Celsius.[^newa-dd]

## Biofix and start dates

The biofix is the date the count starts. Some models start on January 1, since little heat builds up in winter; others start at a biological event, such as planting or the first moth caught in a trap.[^ucipm-concepts][^dean-hodgson] In Wisconsin, few degree days usually build up before April 1.[^delahaut] A model's totals assume its own start date: counting from January 1 when the model counts from first catch puts every event too early.

## Using degree days well

- **Match the model.** Use the base, upper threshold, method and start date the model was developed with.[^ucipm-concepts]
- **Check the field.** Degree days tell you when to look, not what you'll find. Use them with traps and scouting to time your visits and controls.[^dean-hodgson][^newa-dd]
- **Expect local differences.** Totals come from weather stations or a weather grid, and a field's microclimate can run warmer or cooler, though the order in which events happen stays the same.[^becker-2024] A missing or misread daily maximum or minimum also changes a total.[^newa-dd]
- **Treat forecasts as estimates.** A forecast of degree days a week or two ahead helps you plan, but it is a prediction: it shifts as the weather comes in, and it doesn't replace what you see in the field.[^dean-hodgson][^newa-dd]

## AgWeather's models

AgWeather counts degree days from the daily minimum and maximum temperature on its weather grid.

- The [custom degree days model](/models/custom-degree-days) counts degree days from any start date with the single sine (horizontal cutoff), simple average or modified average method, any base and upper threshold, in °F or °C. In this model the simple average takes no upper threshold; use the modified average for one. It doesn't offer double sine, triangle methods or a vertical cutoff. Our methods match the old AgWeather calculator to within a millionth of a degree day, and at Waunakee, Wisconsin, a season's total on our weather came within 0.6 % of the old service's on its own.[^agweather-custom-dd]
- The [degree-day calculator](/tools/degree-days) totals one or several settings at a location through the forecast, with presets for common crops and for each insect we model. A gap of up to seven days is bridged with estimated temperatures and flagged; a longer gap adds nothing to the total and is counted as missing.
- Each insect and crop stage model keeps its own setting and start date, so the stages it shows agree with a calculator total that uses its preset.

A total comes from the weather of a grid cell about 1½ miles (2.5 km) across, not from a sensor in your field. For checking a model against your own traps or crop, your own observations are the best test.
