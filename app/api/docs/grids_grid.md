# Map data

A layer's values over an area, for one day or hour, each step of a range, or a range combined into one map (`stat`). The area is everything the service covers unless you choose a box (`bbox`), a state or a county (`region`).

Maps cover the years our records hold, the most recent 11. A date before them is refused, with the first date we have. For an earlier date at a location, use `/weather/daily` or `/degree-days`, which take those days from Open-Meteo.

JSON and CSV give one row per grid cell (and step), with the cell's center as `lat` and `lng`, which reads directly into a table. NetCDF and GeoTIFF files keep the native grid and its projection, which GIS software and xarray place correctly. Cells with no data are `null` or empty.

A model layer shows each location's result using that location's typical planting date and the model's default settings. To use your own planting or biofix date, run the model at your location with `/models/{model_id}/run`. Model layers cover land only.

When a range is combined with `stat=sum`, each cell also reports how many of its days were estimated or missing, in JSON, CSV and GeoTIFF (as extra bands). A NetCDF file holds the map's values only, so that GIS software opens it as a single layer. Degree days can be mapped by any method and thresholds with the `degree_days` layer (`/grids/degree_days?dd=sine_50_86&start=2026-03-01&stat=sum`).

You can also map the first or last day in a range when a daily value was within bounds, or the days since the last one: `first=frost` on `air_temperature_min` is each location's first fall frost (32 °F or colder) since July 1, `last=hard_freeze` its last hard freeze (28 °F), and `first=above_50` on `soil_temperature_10cm_mean` the first day the soil reached 50 °F since January 1. Each location also has a `found` column, `false` where no day in the range was within the bounds, and `missing_days`, the days without a value, which a freeze could have happened on. A model's map finds days in its results the same way, through the forecast: `first=high` on `tar-spot` is the first day the risk was High or higher this season, and `first=R1` on `corn-stages` the first day the crop reached R1.

`roll` gives a rolling window of days ending on `date` as one map: `date=2026-06-19&roll=14` is the 14 days from June 6 through June 19, averaged (or added up, for precipitation and other values that add up) unless you choose `stat`. Each cell needs data on at least `roll_coverage` percent of the window's days (75 by default).

`climate` shows the map against the past years' climate: `climate=normal` for its normal, `climate=departure` for the map less its normal, or `climate=percentile` for where it ranks among the years of `period` (the past 30 by default). A normal is kept for one day of a daily variable, a range with `stat=mean` or `stat=sum`, a running total and degree days, but not for a range's lowest or highest value, counts or first and last days. `/layers` lists what each layer takes, and the freeze and elevation layers. A departure of temperature is a difference, so it converts between °F and °C without the 32-degree offset.

## In meta.summary

- `steps`: The number of days or hours the map covers.
- `kinds`: How many of those days or hours are `observed`, `partial`, `forecast` or `missing`.
- `cells`: The number of grid cells in each map.
- `stat`: With a range of days, the statistic that combined them.
- `corrections`: The corrections we applied to the weather we read, each with its version, such as our calibration of the forecast's temperatures.
- `from_running_totals`: For degree days added over a range, the stored running totals the sum was worked out from.
- `model`: For a model's map, the model's `id` and `version` and the `output` shown.
- `planting`: For a model that follows a crop's planting date, the crop, the planting tier (`tier`), the earliest and latest typical planting dates in the area (`dates`), and the number of cells with no typical date (`cells_without`).
- `season`: For a model counted over a season, such as a winter: the season's `name` and `label`, its `first` and `last` days, the day its map is first shown (`appears`), the last day counted so far (`through`), and whether the count is `final`.
- `projection`: For a season's projected map, the earlier seasons it was projected with (`seasons`), and a `note` when the season is over.
