---
id: late-blight-dsv
status: draft
updated: 2026-11-19
summary: Scores each day's weather for potato and tomato late blight in disease severity values, from the hours of high humidity and their temperature, and adds them up from crop emergence or your last fungicide spray to time protective sprays.
sources:
  - Wallin 1962 (disease severity values from humid hours and their temperature)
  - Krause, Massie and Hyre 1975 (BLITECAST, the season and recent totals)
  - UW Vegetable Pathology's potato and tomato late blight pages (starting from emergence or the last spray)
  - UW Vegetable Pathology's Vegetable Crop Update (18 values as the first-spray threshold)
  - UMass Extension's late blight fact sheet (disease 7 to 10 days after 18 values)
  - The Crop Risk Tool's late blight model (the risk levels; compared)
  - The old AgWeather service at UW Vegetable Pathology's forecast locations (compared)
---

## What it predicts

Late blight spreads fast in cool, humid weather, and fungicides work only if they're on the plant before it arrives. The model scores how favorable each day's weather was for late blight and adds the scores up, so you can time protective sprays:

- **Disease severity values (DSVs)**: each day's score, from 0 (unfavorable) to 4 (very favorable).
- **The season total**: DSVs since crop emergence or your last fungicide spray.
- **The last 14 days**: DSVs over the past two weeks, which show how fast risk is building.

The model doesn't say whether late blight is present. The pathogen has to be in the area, or in your field, for the weather to matter.

## How it works

- **Daily values.** Each day's value follows Wallin's table (1962), the one Krause, Massie and Hyre's BLITECAST (1975) is built on. It counts the hours with relative humidity of 90 % or more, and their mean temperature, over the day from 6 p.m. CST the evening before, so a wet night counts whole. The warmer those hours, the fewer it takes: from 59 to 80 °F (15 to 26.6 °C), 10 humid hours earn 1 value and 19 or more earn 4; from 45 to 59 °F more hours are needed; below 45 °F (7.2 °C) or above 80 °F a day earns nothing.
- **Humid hours.** We have no leaf wetness sensors, so hours of high humidity stand in for wet leaves. Gridded humidity reads slightly low, so an hour counts as humid at 88 % rather than 90 %.
- **The start.** The totals count from the start date you set at a location. UW Vegetable Pathology advises crop emergence or your last fungicide spray, whichever is more recent. If you give a planting date instead, emergence comes from the [potato emergence model](/models/potato-stages). Otherwise the count starts on May 15. The model runs from May 1 to September 30.
- **Risk levels** follow the Crop Risk Tool:
  - **Moderate** once the season total reaches 18, the usual threshold for a first fungicide spray.
  - **High** with 14 or more DSVs in the last 14 days, once the season total has reached 18.
  - **Very high** with 21 or more in the last 14 days, once the season total has reached 30.
  - **Low** with any DSVs in the last 14 days below those levels, and **Very low** with none.

## How to read it

- UW Vegetable Pathology treats a season total of 18 DSVs as the threshold for a first protective fungicide spray. UMass Extension expects disease 7 to 10 days after the total reaches 18 if the pathogen is present.
- After you spray, enter the spray date to restart the count, so the total shows the weather since your crop was last protected.
- High and Very high mean recent weather has strongly favored late blight. Keep protection in place and the spray interval short, and scout often.
- Watch for confirmed late blight reports nearby, in UW Vegetable Pathology's weekly Vegetable Crop Update. A low total doesn't protect a field where late blight is already present. See the [late blight topic page](/topics/late-blight) for management.

## Validation and caveats

- Draft (model version 0.3, beta). From the Crop Risk Tool's own daily inputs for 2025 at a location near Eau Claire, the model's daily values, totals and risk levels match the tool's on every day. Taking the humid hours and their temperature from the same day, as Wallin paired them, changed 31 days of 2025; both versions reached 18 DSVs on July 16.
- Against the old AgWeather service at UW Vegetable Pathology's seven forecast locations in Wisconsin, from May 1 to September 30, 2026, our season totals ran 30 to 45 % higher. About two thirds of that comes from counting humid hours at 88 % humidity. Counted at 90 %, our totals ran 5 to 20 % higher, with the same daily value on 83 % of days. This explains the difference, not which is more accurate.
- The model hasn't been compared with late blight outbreaks or first detections in Wisconsin fields, and the spray threshold and risk levels come from the tool it replaces, not from a test in this state. Our copy of Wallin's table matches the tool's and the old service's but hasn't been checked against the original paper.
- Humid hours stand in for leaf wetness. Irrigated fields stay wet longer than the weather data show, so the model may underrate their risk. The model also adds up all the humid hours in a day, so two short humid spells count like one long one.
- The model lists tomato as well as potato, but its estimated emergence comes from the potato emergence model. For tomato, enter your own start date or your last spray date rather than a planting date.
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your field.
