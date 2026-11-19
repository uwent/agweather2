---
id: cabbage-looper
status: draft
updated: 2026-11-19
summary: Rates the risk of cabbage looper caterpillar feeding in two windows of degree days counted from May 15, a fixed date that stands in for the moths' arrival from the south; in an average year its first window comes about a month before UW–Madison says the moths arrive.
sources:
  - VDIFN's cabbage looper model (the thresholds, the May 15 start and the two windows, unchanged)
  - Toba, Kishaba, Pangaldan and Vail 1973 (laboratory development of the cabbage looper; its times from egg to adult average the windows' spacing in degree days)
  - USPest.org's cabbage looper model, as summarized in VDIFN's notes (counts from the first trap catch)
  - Delahaut, Cabbage Looper, UW–Madison Division of Extension (moths arrive from mid-July; the second generation does the most damage)
  - Commercial Vegetable Production in Wisconsin (A3422), 2026 (scouting and thresholds)
---

## What it predicts

Cabbage loopers can't survive Wisconsin winters. Each year's moths migrate in from the south, and their caterpillars feed on cabbage, broccoli and the other cole crops, and on lettuce, celery, peas, potatoes, tomatoes and other crops. The model rates the risk of caterpillar feeding from 0 (Very low) to 4 (Very high) in two windows, one for each generation of caterpillars. The rating says where the season is in the model's timing, not how many caterpillars there are.

## How it works

Degree days are counted by the single-sine method, base 50 °F with a cutoff at 90 °F, from May 15.

- **First window:** caterpillars from 325 degree days after May 15, peaking at 520 and ending at 750.
- **Second window:** from 1,115, peaking at 1,310 and ending at 1,540. The model has no third window.
- **The rating** rises a level at a time from Low at a window's start through Moderate and High to Very high, and falls the same way to its end. It's Very high from about 455 to 595 degree days in the first window and from about 1,245 to 1,385 in the second, and Very low outside the windows.
- **The end of the season.** After early September, the rating drops by one level for each day in the last two weeks at or below about 28 °F (−2 °C).

When you look up a single location, you can change the start date (the biofix) to the day you first catch moths in a pheromone trap. Maps count from May 15.

The model comes from VDIFN, the vegetable forecasting tool AgWeather replaces. Its two windows are 790 degree days apart, about one generation. In Toba and colleagues' laboratory study (1973, in California), loopers held at three constant temperatures took 21.5 to 73.5 days to develop from egg to adult, which comes to 666 to 873 degree days above 50 °F, 791.5 on average. Models of the looper developed elsewhere, such as USPest.org's, count from the first moth caught in a trap rather than from a fixed date, because the moths arrive at a different time each year. The May 15 start has no published source.

## How to read it

- **Use the windows as a reminder to scout, not as spray dates.** Scout cole crops weekly through the season whatever the model shows. Walk a W-shaped path, examine 25 to 50 plants, and count a plant as infested if it has eggs or caterpillars of the looper, the imported cabbageworm or the diamondback moth.
- **Treat by the share of infested plants.** For cabbage, Commercial Vegetable Production in Wisconsin gives 10 % in the seedbed, 30 % from transplanting to cupping, 20 % from cupping to early head and 10 % at mature head; for broccoli and cauliflower, 10 % in the seedbed, 50 % from transplanting to the first flower bud or curd, and 10 % after.
- **Pheromone traps** show when moths reach your area. A trap date entered as the biofix moves the windows to follow your own season, though the windows haven't been tested that way in Wisconsin.

The [cabbage looper topic page](/topics/cabbage-looper) explains the insect, its scouting and its management in more detail.

## Validation and caveats

- Draft (model version 0.1, beta).
- Given the same degree days, the model's rating matches VDIFN's at all 701 totals tested from 0 to 3,500, with VDIFN's own code run on this model's windows, and its degree days match those of the calculator VDIFN used. This shows that AgWeather reproduces VDIFN, not that VDIFN's timing is right for Wisconsin. The model hasn't been compared with trap catches or field counts.
- **The first window comes early.** On AgWeather's long-term averages (degree days for 1996 to 2025) at Arlington and Lancaster, the first window opens in early to mid-June, about a month before the moths that UW–Madison says arrive from mid-July. The second window, from mid-July to early August, falls closer to when the first caterpillars of those moths would appear.
- **Late summer isn't covered.** UW–Madison says the second generation in Wisconsin, the caterpillars of moths that grew up here from the migrants' eggs, does the most damage to cole crops. By UW–Madison's account (moths arriving from mid-July, caterpillars feeding four to five weeks, new moths 10 to 14 days later), that generation feeds from late summer into fall. In an average year the model's last window ends in early August in southern Wisconsin, weeks before then.
- **May 15 is a stand-in.** Arrival varies from year to year; your own trap date at a location follows it, but the maps can't.
- The model's timing is to be reviewed against its sources, and it is likelier to change than UW–Madison's account of the insect.
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your field.
