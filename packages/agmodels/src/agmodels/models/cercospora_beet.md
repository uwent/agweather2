---
id: cercospora-beet-div
status: draft
updated: 2026-11-19
summary: Scores each day's weather for Cercospora leaf spot of beet in daily infection values, from the hours of high humidity and their temperature, and rates risk from the last 2 and 7 days' averages.
sources:
  - Windels, Lamey, Hilde, Widner and Knudsen 1998 (the daily infection value table, sugar beet in Minnesota and North Dakota)
  - Harveson 2013, University of Nebraska–Lincoln Extension (what two-day totals mean; when spots show)
  - NDSU Extension's Cercospora leaf spot of sugar beet page (when to start fungicides)
  - North Dakota Agricultural Weather Network's sugar beet Cercospora pages (how the industry's values are counted)
  - The Crop Risk Tool's and VDIFN's Cercospora leaf spot model (the table in code and the risk levels; compared)
---

## What it predicts

Cercospora leaf spot spots and kills the leaves of sugar beet and table beet in warm, humid weather. Spots you see come from infections 7 to 10 days earlier, so more disease is under way than shows. The model scores each day's weather for infection and shows:

- **Daily infection values (DIVs)**: each day's score, from 0 (unfavorable) to 7 (very favorable).
- **The last 2 days' and last 7 days' averages**: which set the risk.
- **The total since planting**: DIVs since your start date.

## How it works

- **Daily values.** Each day's value comes from the table Windels and colleagues described for the sugar beet industry of Minnesota and North Dakota (1998). It counts the hours with relative humidity of 90 % or more, and their mean temperature, over the day from 6 p.m. CST the evening before. At 60 °F (15.6 °C) or below a day earns nothing. From 61 °F up, the warmer the humid hours, the fewer it takes to earn each value: from 66 to 71 °F, 4 humid hours earn 1 and 22 earn 6, and from about 74 °F every humid day earns at least 1. Above 82 °F, 10 humid hours earn the full 7.
- **Humid hours.** We have no leaf wetness sensors, so hours of high humidity stand in for wet leaves. Gridded humidity reads slightly low, so an hour counts as humid at 88 % rather than 90 %.
- **The start.** The total counts from planting, June 1 unless you enter your own date at a location. The model runs from June 1 to September 30.
- **Risk levels** take the higher of two averages, as the Crop Risk Tool and VDIFN set them:
  - **Very high**: the last 7 days average 5 or more, or the last 2 days 5.5 or more.
  - **High**: 3 or more over 7 days, or 3.5 or more over 2 days.
  - **Moderate**: 1.5 or more over 7 days, or 2 or more over 2 days.
  - **Low**: 0.5 or more over 7 days, or 1 or more over 2 days.
  - **Very low**: below those.

## How to read it

- Sugar beet guides read the values as two-day totals: a total of 7 or more means a strong chance of infection, and below 6, little. A two-day average of 3.5, where the model's High begins, is a two-day total of 7.
- In sugar beet, start fungicides after the rows close, at the first spots in the field or district, and use mixtures and rotate fungicide groups, since the fungus resists many of them. Sugar beet growers should also follow their cooperative's agronomists.
- See the [Cercospora leaf spot topic page](/topics/beet-cercospora-leaf-spot) for management of sugar beet and table beet.

## Validation and caveats

- Draft (model version 0.3, beta). The model reproduces the Crop Risk Tool's daily values in every combination of temperature and humid hours tested, and on the tool's own inputs for 2025 at a location near Eau Claire its daily values, averages and risk levels match the tool's on every day. Our copy of the table and the risk levels haven't been checked against Windels and colleagues' paper.
- The method was developed for sugar beet in the Red River Valley, with weather stations in the fields. Its use for table beet in Wisconsin hasn't been tested, and the model hasn't been compared with Cercospora leaf spot in Wisconsin fields. The model lists sugar beet as its crop, though it is meant for table beet as well.
- The North Dakota Agricultural Weather Network, whose values the sugar beet industry uses, counts the hours at 85 % humidity or more, from noon to noon, adjusted to conditions in the crop canopy. Our values count from 88 % in gridded data, from 6 p.m. to 6 p.m., with no canopy adjustment, so they can differ from NDAWN's at the same place. We haven't compared them.
- Humid hours stand in for leaf wetness, and the model adds up all the humid hours in a day. Irrigated fields and closed canopies stay wet longer than the weather data show.
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your field.
