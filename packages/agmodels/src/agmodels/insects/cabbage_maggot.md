---
id: cabbage-maggot
status: draft
updated: 2026-11-19
summary: Rates the risk from cabbage maggot flies and their egg laying in two windows of degree days from January 1, one for the spring flight and one for a summer generation; the second comes later than the Wisconsin trap study puts it, and the model has no third flight.
sources:
  - VDIFN's cabbage maggot model (the thresholds, the January 1 start and the two windows, unchanged)
  - Eckenrode and Chapman 1972 (fly trap catches at Kenosha and Arlington, Wisconsin, by thermal units; compared)
  - Lowenstein and Groves, Cabbage Maggot, UW–Madison Division of Extension, and UW Vegetable Entomology's cabbage maggot page (flights and degree days in Wisconsin)
  - Commercial Vegetable Production in Wisconsin (A3422), 2026 (three generations; soil treatments)
  - University of Minnesota Extension, VegEdge's Cabbage Maggot and the root maggots page (later generations' injury; row covers)
  - MSU Enviroweather's cabbage maggot model (compared)
---

## What it predicts

Cabbage maggot flies lay eggs in the soil at the base of cabbage, broccoli, radish and other cole crops, and the maggots that hatch feed on the roots. Damage can't be stopped once the maggots are in the roots, so control is preventive and has to be in place while flies are laying eggs. The model rates the risk from 0 (Very low) to 4 (Very high) in two windows, each running from a generation's flight through its egg laying.

## How it works

Degree days are counted by the single-sine method, base 42.8 °F (6 °C) with a cutoff at 86 °F, from January 1.

- **The spring flight:** flies from the overwintering pupae begin emerging at 360 degree days, their flight peaks at 600, and the window ends at 1,521. VDIFN's description put egg laying from about 750 to 1,500, most of it around 1,050.
- **A summer generation:** from 1,881, peaking at 2,121 and ending at 3,042, with egg laying from about 2,270 to 3,040 by VDIFN's description. The model has no third window.
- **The rating** rises a level at a time from Low at a window's start through Moderate and High to Very high, and falls the same way to its end. It's Very high from about 520 to 905 degree days in the first window and from about 2,040 to 2,430 in the second, and Very low between them.
- **The end of the season.** After early September, the rating drops by one level for each day in the last two weeks at or below about 28 °F (−2 °C).

The model comes from VDIFN, the vegetable forecasting tool AgWeather replaces. Its numbers most likely come from Eckenrode and Chapman's trap catches of flies in Wisconsin (1972), which counted thermal units above 43 °F from each day's high and low by a slightly different method.

## How to read it

- **Plan spring plantings around the first window.** Plant after the spring flight's peak where you can; plantings made after mid-June usually suffer less damage than earlier ones.
- **Row covers** keep flies off if they are in place before the flight. Don't use them where brassicas grew last year, since flies emerging from the soil would be trapped underneath.
- **Soil insecticides** work only as prevention, at or just before planting, and last only four to five days, so they must go on while flies are laying eggs.
- **The rating peaks with the flight, not with egg laying.** By VDIFN's description, egg laying peaks a few weeks after the flight, so roots remain at risk after the rating starts to fall.
- **Use traps for later flights.** Yellow bowls of soapy water along field edges, checked every four to six days, show whether flies are active; rely on them rather than the model after the spring flight.

The [cabbage maggot topic page](/topics/cabbage-maggot) explains the insect, its monitoring and its management in more detail.

## Validation and caveats

- Draft (model version 0.1, beta).
- Given the same degree days, the model's rating matches VDIFN's exactly, and its degree days match those of the calculator VDIFN used. This shows that AgWeather reproduces VDIFN, not that VDIFN's timing is right for Wisconsin.
- **The spring flight agrees with the Wisconsin study.** The model's first window opens at 360 degree days; over five years in Eckenrode and Chapman's study, spring flies emerged at 290 to 365.
- **The summer generation comes late.** The model's second window opens 1,521 degree days after the first; the study found a mean of 1,176 between generations in the field (1,058 to 1,261 by site and year), so the model's second flight is about 345 degree days later than the study puts it. On AgWeather's long-term averages (degree days for 1996 to 2025) at Arlington and Lancaster, it opens in mid-July, about two weeks after the late-June flight UW–Madison describes.
- **There's no third flight.** The study trapped flies of three generations in a season, and Commercial Vegetable Production in Wisconsin counts three in the state. UW–Madison's third flight, at about 2,652 degree days, comes in early to mid-August in an average year at Arlington and Lancaster and falls inside the model's second window, without a peak of its own.
- **Every window counts alike.** Commercial Vegetable Production in Wisconsin calls the spring generation the largest and most damaging, and the University of Minnesota finds the second generation's injury usually light; the model rates every generation's peak the same.
- NEWA's cabbage maggot model, which counts degree days at a base of 40 °F, hasn't been compared with this one yet. MSU Enviroweather's counts from March 1 without a cutoff and puts the spring flight's peak at 565 to 716 degree days, near the model's 600.
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your field.
