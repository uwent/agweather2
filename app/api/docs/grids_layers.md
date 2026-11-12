# Map layers

Every layer that can be shown as a map: weather variables, running totals, degree days, models, freeze odds and elevation. Each layer lists its name and unit, whether it is daily, hourly, by day of the year or without a date, the dates the archive and forecast hold for it, the ways a range of days can be combined, and its color palette.

A model's layer also lists its results (`output`) and options, and a seasonal layer lists the seasons available.

## Climate

Layers that list values under `climate` can be shown against the climate of the past years. Add `climate=normal` for the normal map of what you asked for, `climate=departure` for your map less its normal, or `climate=percentile` for where it ranks among the past years. `period` chooses the years: `last30` (the default), `last10` or `last5`. For example, `/grids/air_temperature_max?date=2026-07-15&climate=departure` shows how far each location's high temperature that day was above or below normal. `/grids/degree_days?dd=modified_50_86&start=2026-01-01&end=2026-07-15&stat=sum&climate=percentile` ranks this season's growing degree days among the past 30 years'.

Three more layers are made from the climate and the land alone:

- `freeze_chance`: for a date, the share of the past years with a freeze (a minimum at or below `threshold`: 32, 28 or 24 °F) after that date in spring, or on or before it in fall.
- `freeze_dates`: the date of the last spring freeze or the first fall freeze by a share of the years (`output=last_spring_p10`, `last_spring_p50`, `first_fall_p90` and so on), or the frost-free season's median length (`output=season_days_p50`). It has no date.
- `elevation`: each grid cell's mean, lowest or highest elevation, or the spread of elevation within it (`output=mean`, `min`, `max` or `spread`), from the 30-meter National Elevation Dataset. It has no date.
