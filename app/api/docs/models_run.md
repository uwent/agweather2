# Run a model

A model's daily results at one location, or at several, from its biofix or your planting date (January 1 for a model with neither) through the forecast. Each row is one day: `date`, `kind`, the weather the model uses, its results, and where the model defines them, `risk_level` and `risk_label`.

The model's options, such as a crop's maturity group or an irrigation setting, are added as parameters by name (`/models/{model_id}` lists them, as `maturity_group=2.5`). Giving `all` for one option runs every choice, up to 20 at a time, with an `option_set` column identifying each.

With a `planting_date`, a disease model also runs the crop's growth stages and adds a `susceptibility` column for the period when the crop can be infected. With `projection`, the results continue to the end of the season using the weather of each earlier year in the archive, and `meta.summary.projection` gives the range of dates on which each stage or risk level may arrive.

For several locations, give `points` in place of `lat` and `lng`. The results come back as one table, with a `point` column saying which location each row is for, and the same options apply at every location. A typical planting date (`early`, `mid` or `late`) and a biofix set by the crop's growth can fall on different days at each location; `meta.summary.points` lists them. A request with `projection` can include up to 10 locations; for more, make one request per location.

A model's results are guidance based on weather data, not a prediction of what will happen in a particular field. Check the model's region and season in `/models/{model_id}`.

## In meta.summary

- `days_returned`, `days_forecast` and `days_missing`: The number of rows returned, how many are forecast days, and how many have no data.
- `estimated_by_input`: For each input the model needed an estimate for, the number of rows on which it was estimated.
- `days_projected`: With `projection`, the number of rows past the forecast.
- `windows`: For an insect, each action window's periods as pairs of first and last days, by window name. With several locations, option sets or projected years, each entry names its `point`, `option_set` or `year`.
- `option_sets`: When an option is given as `all`, the option values of each `option_set`.
- `projection`: With `projection`, how it was made (`mode`), the first projected day (`start`), the earlier years used (`years`), and `milestones`: for each crop stage, risk level and action window (`what` and `name`), in how many of the years it was reached (`reached` of `of`) and the 10th, 50th and 90th percentile dates (`p10`, `p50`, `p90`). With several locations, this is in `points`.
- `points`: With several locations, what was worked out at each: its `biofix`, its `planting_date`, its `option_sets` where they differ between locations, and its `projection`.
- `corrections`: The corrections we applied to the weather we read, each with its version, such as our calibration of the forecast's temperatures.
- `season`: For a model counted over a season, such as a winter: the season's `name` and `label`, its `first` and `last` days, the day its map is first shown (`appears`), the last day counted so far (`through`), and whether the count is `final`.
