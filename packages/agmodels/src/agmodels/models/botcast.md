---
id: botrytis-onion-botcast
status: draft
updated: 2026-11-19
summary: Runs BOTCAST for Botrytis leaf blight of onion, scoring each day for whether spores are likely present and whether its wet period favored infection, and adds the scores up from crop emergence to time the first fungicide spray.
sources:
  - Sutton, James and Rowell 1986 (BOTCAST, Ontario)
  - UW Vegetable Pathology's onion Botrytis leaf blight page (what to do at each season total)
  - The Crop Risk Tool's Botrytis leaf blight model (the tables in code and the risk levels; compared)
  - VDIFN's and the old AgWeather service's Botrytis leaf blight models (compared)
---

## What it predicts

Botrytis leaf blight spots and kills onion leaves after long periods of leaf wetness in mild weather. BOTCAST, developed by Sutton, James and Rowell in Ontario (1986), was built to time the first fungicide spray. The model shows:

- **The disease severity index (DSI)**: each day's score, 0, 1 or 2.
- **The season total**: the sum of the daily scores since crop emergence, which sets the risk.
- **The two parts of each day's score**: whether spores are likely to be present (the inoculum value, 0 or 1) and how favorable the day's wet period was for infection (the infection value, 0 to 2).

## How it works

Each day's score is the inoculum value times the infection value. Hours of relative humidity of 90 % or more stand in for leaf wetness, counted over the day from 6 p.m. CST the evening before. Gridded humidity reads slightly low, so an hour counts as humid at 88 % rather than 90 %.

- **Inoculum (0 or 1).** Spores are taken to be absent (0) after a hot spell, 4 or more hours at 86 °F (30 °C) or above on any of the last 5 days, or on a day with fewer than 5 humid hours. A day with more than 12 humid hours has spores present (1). In between, spores are present unless the day before was dry: 6 or more hours below 70 % humidity with less than 0.04 inch (1 mm) of rain.
- **Infection (0 to 2).** This comes from the number of humid hours and their mean temperature, read from a chart in Sutton and colleagues' paper. A wet period of 6 hours or less, or one below 43 °F (6 °C) or above 82 °F (28 °C), scores 0. Long wet periods in mild weather score 2: for example, 15 hours or more from about 47 to 77 °F (8 to 25 °C), or 11 hours or more from 56 to 62 °F (13.5 to 16.5 °C). Short periods that are cool or warm score 0, and at 46 °F (8 °C) or below it takes 13 hours to score 1 and 23 to score 2. The rest score 1.
- **The start.** The total counts from crop emergence, May 15 unless you enter your own date at a location. The model runs from May 15 to September 15.
- **Risk levels** follow the season total, as the Crop Risk Tool set them: **Very low** up to 10, **Low** from 11, **Moderate** from 21, **High** from 31 and **Very high** above 40.

## How to read it

UW Vegetable Pathology's guidance on the season total:

- **21 to 30 (Moderate):** a warning. No spray is needed unless rain is forecast or you irrigate overhead.
- **31 to 40 (High):** a high risk of rapid disease development. Apply the first spray as soon as possible.
- **Above 40 (Very high):** the risk is extremely high.

BOTCAST times the first spray only. After that, scout for leaf spots and follow the [Botrytis leaf blight topic page](/topics/onion-botrytis-leaf-blight) for spray intervals, fungicide choices and resistance management.

## Validation and caveats

- Draft (model version 0.3, beta). The model reproduces the Crop Risk Tool's inoculum and infection values in every combination tested, and on the tool's own inputs for 2025 at a location near Eau Claire its daily score matches the tool's on every day both score. Where an input that decides a day is missing, we give no score; the tool scored such days.
- The infection chart is a reading of a figure in Sutton and colleagues' paper, and the tools that read it disagree in places. VDIFN, through the old AgWeather service, scored 2 from 10 humid hours at 56 to 62 °F, where we and the Crop Risk Tool need 11, and drew the chart's last boundary slightly differently. Its inoculum value also left out the dry day before and looked for heat only during the day's humid hours, not over the last 5 days. Neither reading of the chart has been checked against the paper yet.
- The risk levels also differ from VDIFN's. VDIFN's Very high began at a total of 40, where ours begins above 40, as UW Vegetable Pathology's guidance has it. VDIFN's Low covered any total from 1 to 20, where ours begins at 11; the line between Very low and Low is the Crop Risk Tool's, not BOTCAST's or UW's.
- The model hasn't been compared with Botrytis leaf blight in Wisconsin onion fields, and Sutton and colleagues' own spray threshold hasn't been checked against these levels.
- Humid hours stand in for leaf wetness. Onion fields on muck soils or under overhead irrigation may stay wet longer than the weather data show. The model also adds up all the humid hours in a day, so two short humid spells count like one long one.
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your field.
