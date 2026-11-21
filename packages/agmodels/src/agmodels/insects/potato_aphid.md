---
id: potato-aphid
status: draft
updated: 2026-11-21
summary: Shows the typical season's potato aphid counts in central Wisconsin potato fields, by degree days or calendar date, from curves fitted to a decade of scouting counts.
sources:
  - Bradford and Groves, unpublished analysis of Pest Pros' scouting counts, 2014–2025 (UW–Madison Vegetable Entomology)
---

## What it predicts

The potato aphid is a large green or pink aphid that colonizes potato and can spread potato viruses. The model shows how many potato aphids a typical field in central Wisconsin has per 25 sweeps of a standard sweep net at each point in the season, as a typical count and as a share of the season's highest count.

It shows typical pressure for the time of year, not a count for your field.

## How it works

The curves come from scouting counts in commercial potato fields in central Wisconsin, mostly the Central Sands, from 2014 to 2025. Only visits where the scout recorded a potato aphid count were used, since a blank could mean either none seen or not checked. A smooth curve was fitted to the counts by degree days, counted from January 1 by the single-sine method, base 39.2 °F (4 °C) with a cutoff at 86 °F, allowing for differences between years and farms; another was fitted by calendar date.

The model reads degree days unless you choose the calendar. Degree days described each year's numbers better: in a warm year, aphids build up earlier by date. The calendar timed the season's rise as well or better.

In a typical season:

- Potato aphids are rare in sweep counts until late July.
- Counts reach 10 % of their highest at about 2,520 degree days (about August 1) and half at about 3,360 (about August 30).
- They are still near their highest when scouting ends in mid-September. Counts after that weren't observed, so the model holds them until fall freezes end the season.

## How to read it

- Include potato aphids in sweep counts from mid-July, and expect counts to build through August.
- Risk levels compare the day's typical count with the season's highest: Very high means counts are usually near their highest at this time of year.
- The counts are from fields that were treated at planting, and sprayed for aphids when counts reached a threshold, so they show typical pressure in managed fields.

## Validation and caveats

- Draft (model version 0.1, beta). Fitted with each year left out, degree days described the held-out year's counts better than the calendar in 10 of 12 years. Leaving groups of farms out, the two did about equally well.
- The counts are from central Wisconsin. Elsewhere the model runs with a warning: the timing may carry by degree days, but northern seed potato fields, which are sprayed for aphids more consistently, aren't in the data.
- Suction trap catches of potato aphids were too sparse to check the field curve against.
