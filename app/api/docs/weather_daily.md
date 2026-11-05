# Daily weather

Daily weather at one or more locations, from January 1 through the forecast unless you choose other dates. Days follow each location's own calendar and time zone.

Each row is one location and day: `date`, `kind` (`observed`, `partial` or `forecast`), and a column for each variable in `vars`. A day without data has a `kind` of `null`, and its values are missing. `meta.summary` gives each variable's minimum, maximum, mean or total over the period, and how many days were missing.

Locations outside the area the service covers, or dates before its archive begins, are filled from Open-Meteo, and `meta.sources` says so. A request can cover up to ten years.
