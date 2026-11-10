# Summaries by county or state

A layer's values summarized over each county or state: the mean, lowest and highest value across the county's grid cells, for one day or hour, each step of a range, a range combined with `stat`, or each month of a range (`interval=month`). Any layer that `/grids` serves can be summarized, with the same dates, statistics and settings.

Each row gives the county or state's FIPS code and name, its land area (from the U.S. Census Bureau), how many 2.5 km grid cells it has, and how many of them have data for this request. `coverage` is the percent of its cells with data, and `complete` is `true` when every cell has data. A county can be less than complete because part of it lies outside the area we cover, or because some cells have no value (soil temperature has none along the Great Lakes shore, and models only cover land). Open water in the Great Lakes and the ocean is never part of a county here.

When coverage is below `min_coverage` (50% by default), the row is still returned, with its statistics empty (`null`), so a table of counties is always whole. A summary over part of a county describes only that part, so set `min_coverage=100` if you need statistics for whole counties only.

The mean gives each grid cell equal weight; the cells differ in area by less than 2% across a state. For a model's risk level or a crop stage, each row gives the percent of the county's cells with data at each level (`pct_low`, `pct_high` and so on) and the highest level found (`highest`). For the first or last day within bounds (`first=frost`), the statistics are the earliest, average and latest dates, and `cells_none` counts the cells where no day in the range was within the bounds; those cells count as having data.

Examples: each Wisconsin county's highest temperature on July 15, 2026 (`/summaries/air_temperature_max?date=2026-07-15&region=WI`); each state's summer rainfall (`/summaries/precipitation_sum?start=2026-06-01&end=2026-08-31&stat=sum&by=state`); each county's first fall frost (`/summaries/air_temperature_min?first=frost&region=WI`).
