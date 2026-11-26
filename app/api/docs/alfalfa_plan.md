# An alfalfa cutting plan

A season of alfalfa cuttings at one location, timed by growing degree days (GDD, single sine, base 41 °F with an upper threshold of 86 °F): the degree days since spring regrowth or the last cut. Alfalfa is generally ready to cut once 900 to 1,100 GDD have accumulated.

The season's degree days are this year's own through the forecast, then the normal: for each later day, the average of that day's degree days over the past 30 years (or the period you choose). The season starts after the last spring killing freeze, a day at or below 24 °F. While spring is still ahead of the typical (median) date of that freeze, the season starts at the typical date; after it, at this year's last one.

Without `cuts`, we schedule the season. Any cuts you hold with `held` stay where they are. The rest of the season, between held cuts and from the last of them to the season's end, is divided into equal parts: as near as possible to `interval` degree days each (1,000 unless you choose another from 800 to 1,200), or to give `count` cuts in all. The season's end, where the last cut falls, is the date by which one year in ten has had its first fall killing freeze, or this year's own freeze if it comes first. If less than 360 GDD would remain after the last held cut, no cut is added after it. With `cuts`, we check the dates you give as they are.

Before winter, alfalfa needs either too little regrowth to draw down the reserves in its roots, under 360 GDD after the last cut, or enough to rebuild them, over 900 GDD, before the killing freeze. To check a plan against this rule, we count the regrowth from its last cut to each year's own first fall killing freeze in the period, along this season's degree days.

Each row is a day of the year:

- `kind` is `observed` or `forecast` for this year's weather, and `normal` where the plan uses the normal, after the forecast or for days missing in gaps too long to estimate.
- `gdd` is the day's degree days.
- `gdd_since_cut` is the running total since the season started or the last cut, which starts again the day after each cut. It is empty before the season starts and after this year's fall killing freeze.
- `kill_chance` is the chance, in percent, of a killing freeze: from January through June, the share of the period's years with one still to come after the date; from July through December, the share that had had one by the date.
- `cut` is true on the plan's cutting days.

A plan is guidance based on weather data and the normal, not a guarantee for any one field or year. Growth also depends on the variety, the soil and its moisture, and the stand's health. Plans are available only inside the area we cover, since the normal comes from our own gridded records.

## In meta.summary

- `period`, `first_year`, `last_year`, `years` and `missing_years`: The period the normal comes from, as for `/climate/normals`.
- `plan`: The plan, with these parts:
  - `spring_freeze`: The last spring killing freeze the season counts from (`date`, null when there was none and the season counts from January 1) and its `basis`: `observed` for this year's, `typical` for the typical date, or `none`.
  - `season_end`: Where the season ends for scheduling (`date`) and its `basis`: `observed` for this year's fall killing freeze, `typical` for the date by which one year in ten has had one, or `none` (December 31).
  - `interval` and `count`: What the plan was scheduled by. Both are null when you gave `cuts`.
  - `cuts`: Each cut's `date`, whether it was `held`, the `gdd` and `days` since the season started or the previous cut, its `status` against the cutting window (`early` under 900 GDD, `window` from 900 to 1,100, `late` over 1,100), and whether it is `projected`, resting partly on the normal.
  - `fall`: The fall check: the `last_cut`, the number of `years` counted, and how many had regrowth `under` 360 GDD, `over` 900 GDD or `between` them before their first fall killing freeze, or a freeze on or `before_cut`. `typical_freeze` and `typical_regrowth` give the typical (median) first fall killing freeze and the regrowth before it, and `observed_freeze` and `observed_regrowth` this year's own, once it has come.
  - `thresholds`: The cutting window (`cut_from`, `cut_until`), the fall rule's limits (`fall_under`, `fall_over`) and the `killing_freeze` temperature, in the request's units.
- `days_observed`, `days_forecast` and `days_normal`: How many days of the year come from each.
- `days_estimated`: Days of this year's weather estimated from the days on either side, in gaps of up to seven days.
- `corrections`: The corrections we applied to the weather we read.
