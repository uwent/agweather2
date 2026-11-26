---
id: potato-stages
status: draft
updated: 2026-11-25
summary: Estimates the date half of a potato planting has emerged, from degree days in air above 39 °F (4 °C) since planting; that date starts AgWeather's early and late blight models.
sources:
  - UW Vegetable Pathology's Vegetable Crop Updates, 2020–2026 (planting and emergence dates the model was fitted to)
  - Holden, Pavek, Knowles and Knowles 2011, Washington State Potato Commission (heat units from planting to emergence)
---

## What it predicts

Much of a potato grower's season is timed from emergence, including the first fungicide sprays for early and late blight. The model estimates the date half the plants in a planting have emerged, from its planting date and the weather since. It shows two stages, planted and emerged, and the degree days since planting.

Its main use is to start the [early blight](/models/early-blight-pdays) and [late blight](/models/late-blight-dsv) models: when you give those models a planting date, they count from this model's emergence date.

## How it works

- **Degree days.** Each day adds the amount its average temperature, the mean of the high and low, is above 39.2 °F (4 °C), counted from planting.
- **Emergence** comes at 374 degree days in °F (208 in °C) after planting. We fitted that number to the planting and 50 % emergence dates in UW Vegetable Pathology's Vegetable Crop Updates: 120 early, mid and late plantings at seven Wisconsin potato areas, from Spring Green and Arlington to Antigo and Rhinelander, from 2020 to 2026.
- Without a planting date, the model assumes May 1. It runs from March 15 to July 31.
- **Typical planting dates.** When you choose an early, mid or late planting instead of your own date, and on the maps, each location's dates are an estimate for its grid cell. They are set from the normal date of the last spring freeze at 28 °F, over the 30 years to 2025, averaged over the area within about 30 miles of the location (nearer places count more), so a frost pocket in low ground doesn't move a location's dates: early planting 6 days before that date, mid planting a week after it and late planting four weeks after it. We fitted those numbers to the planting dates in the same newsletters, at the same seven places. Where we have no 30-year normal, as outside the area AgWeather covers, there is no typical date, and the map shows no data there.
- Only planting and emergence are modelled. Tuber initiation and later stages need another source.

## How to read it

- Use the emergence date as the start for early and late blight. If you know when your field reached 50 % emergence, enter that date instead: your own date is better than any estimate.
- Record each field's planting and emergence dates. They let you check the estimate, and they set the start of the disease counts.

## Validation and caveats

- The typical planting dates came within about a week (6.7 days on average) of the newsletters' dates at the seven places, tested with each place left out in turn. Growers on the central sands plant about 5 days earlier than the estimate, and growers around Antigo and Rhinelander about 9 days later. Outside Wisconsin they haven't been checked against planting records, and in the southern part of the area we cover they are the least certain. Your own planting date is always better than the estimate.
- Draft (model version 0.2, beta). Fitted with each year left out in turn and tested on that year, the model's emergence dates were off from the newsletters' by 3.3 days on average. A fixed 24 days after planting missed them by 7.5 days on average.
- The dates it was fitted to are the newsletters' estimates, with planting dates from growers' reports, not emergence counted in fields. Some may themselves have come from older forecasting tools, in which case the fit partly repeats an older estimate. The model hasn't been tested against emergence counted in Wisconsin fields.
- As a check on its size: at a 45 °F base, the same dates take about 250 degree days, the value Holden and colleagues use, within their range of 200 to 300, for potatoes planted 8 inches deep in Washington's Columbia Basin.
- The fit used daily temperatures from Open-Meteo, a public weather service, at each location, not AgWeather's own weather data; how much that shifts the estimated dates hasn't been measured.
- Degree days in air are a stand-in for the soil around the seed piece. Bases from 36 to 45 °F (2 to 7 °C) fit about as well, and soil temperature fit no better than air.
- Planting depth, seed size, sprouting before planting and soil moisture all change emergence, and none is an input. One threshold serves every variety.
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your field.
