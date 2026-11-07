# Run a model

A model's daily results at one location, or at several, from its biofix or your planting date (January 1 for a model with neither) through the forecast. Each row is one day: `date`, `kind`, the weather the model uses, its results, and where the model defines them, `risk_level` and `risk_label`.

The model's options, such as a crop's maturity group or an irrigation setting, are added as parameters by name (`/models/{model_id}` lists them, as `maturity_group=2.5`). Giving `all` for one option runs every choice, up to 20 at a time, with an `option_set` column identifying each.

With a `planting_date`, a disease model also runs the crop's growth stages and adds a `susceptibility` column for the period when the crop can be infected. With `projection`, the results continue to the end of the season using the weather of each earlier year in the archive, and `meta.summary.projection` gives the range of dates on which each stage or risk level may arrive.

For several locations, give `points` in place of `lat` and `lng`. The results come back as one table, with a `point` column saying which location each row is for, and the same options apply at every location. A typical planting date (`early`, `mid` or `late`) and a biofix set by the crop's growth can fall on different days at each location; `meta.summary.points` lists them. A request with `projection` can include up to 10 locations; for more, make one request per location.

A model's results are guidance based on weather data, not a prediction of what will happen in a particular field. Check the model's region and season in `/models/{model_id}`.
