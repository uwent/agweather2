# Normals

Normal weather at one or more locations, for each day of a calendar year (this year unless you choose other dates). By default, the normals cover the 30 complete years before this one. Each January the period moves forward a year.

Each row is one location and day, with its `date` and `day_of_year`, and a column for each variable in `vars`. A day's normal is the average of every year's days within a window centered on it: 15 days by default, so 450 days over 30 years. This makes the normals for neighboring days change smoothly, and percentiles steady. Ask for percentiles with `percentiles=10,90` to add the range most years fall within (`air_temperature_max_p10` and `air_temperature_max_p90`).

For precipitation and other values that add up, a column ending `_cum` gives the normal running total from `start`. It comes from each year's own total, then averaged across the years, as do its percentiles. Degree days (`dd=modified_50_86`) work the same way. Each year's degree days come from that year's own daily temperatures, which gives a truer normal than degree days computed from normal temperatures. `dd_modified_50_86` is the normal for each day, and `dd_modified_50_86_cum` is the normal running total from `start`.

Counts of days within bounds (`count=air_temperature_max:days_above_90`) are normals of the same kind. On a given day, the column is the share of the period's years and nearby days within the bounds, so 0.4 means about two days in five. Over any span these add up to the normal count, and `_cum` gives it from `start`. With `interval=month`, it is the average of each year's own count for the month. These are the heat days, freeze days, dry days and heavy-rain days a month or a season usually brings.

With `interval=month`, each row is a month. A month's normal is the average across years of each year's mean (or total) for that month, and its percentiles are taken among those years. With `interval=year`, one row covers the whole period from `start` to `end`.

The 30-year normals combine our own records, which begin in 2016, with gridMET, a gridded record from the University of California, Merced. We adjust gridMET's years, cell by cell and season by season, to match our records where the two overlap, so the normals don't jump where one source ends and the other begins. gridMET has no daily mean temperature, so the 30- and 20-year normals give only the minimum and maximum. It has no values over the Great Lakes, where only our own years count. Its maximum temperature for 2011–2013 runs warm in summer and is left out. The 20-year normals (`period=last20`) also reach into gridMET's years. The 10- and 5-year normals (`period=last10` or `last5`) come from our own records alone. `meta.summary` names the years used.

Normals are available only inside the area we cover.
