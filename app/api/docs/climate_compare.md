# This year against normal

This year's running totals at one or more locations, beside last year's and the normal, from January 1 unless you choose another start. It covers precipitation, reference evapotranspiration (ET0), sunlight and growing degree days. The normal comes from the past 30 years unless you choose a shorter period.

Each row is one location and day, with its `kind` (`observed`, `partial` or `forecast`; empty after the forecast ends). For each variable or degree-day setting, such as `dd_modified_50_86`:

- `dd_modified_50_86_cum` is this year's running total from `start`, through the forecast.
- `dd_modified_50_86_cum_last_year` is last year's total from the same date to the same date.
- `dd_modified_50_86_cum_normal` is the normal total: each year's own total to that date, averaged across the period's years. `dd_modified_50_86_cum_normal_p10` and `_p90` give the range that most years fell within.
- `dd_modified_50_86_departure` is this year's total less the normal, and `dd_modified_50_86_percent_of_normal` is this year's total as a percentage of it.
- `dd_modified_50_86_percentile` ranks this year's total among the period's years: 50 is a typical year, and 90 means this year is ahead of nine years in ten.

`meta.summary.compare` gives each location's last observed day (`as_of`), each total's percentile on that day and, for degree days, `days_ahead`: how many days ahead of normal the season is. It is negative when the season is behind. It is the number of days between today and the day the normal total reaches this year's total, so 5 means this year reached today's total 5 days sooner than a normal year would. It is empty when this year's total is beyond the highest normal total for the year.

This year's totals are computed as on `/degree-days` and `/weather/totals`: short gaps in temperature and ET0 are filled with an estimate, and missing precipitation counts as no rain. Totals are available only inside the area we cover.
