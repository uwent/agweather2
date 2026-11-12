# API v2 design

Agreed 2026-11-02 (D57, D58). The contract for `/api/v2`: what each endpoint takes and returns, in which formats, and why. PLAN.md Phase 5 holds the work list and the decisions (D57 the contract, D58 models on your own weather); this file is the spec they refer to, and the source for the public API docs page in Phase 7. Details below are refined as the endpoints are built, and recorded here.

## Who it serves

1. **The app's own frontend.** Pages get their first render from Inertia props, but everything interactive (click the map → a chart, change a model option, scrub the slider) fetches from `/api/v2`. The frontend is the API's first client, so the public API is never a second-class copy of what the site can do.
2. **Researchers and scripts** (R, Python, Excel): a URL that reads straight into a data frame, with the query and units stated in the response.
3. **Agencies** (DATCP, DNR): stable URLs, CSV, and GIS formats (GeoTIFF, rendered XYZ tiles) that drop into ArcGIS and QGIS.
4. **Farmers' and vendors' software:** simple GET requests and predictable JSON. Missing data is `null`, never 0, and nothing depends on undocumented defaults.

## Principles

- **GET with query parameters** for every read, so a URL can be shared, bookmarked, cached and read with `read.csv(url)`. POST only where the input won't fit in a URL (model evaluation, a station's weather).
- **The same parameter means the same thing everywhere** (`lat`, `lng`, `start`, `end`, `vars`, `units`, `format`), and every default applied is echoed back in `meta.request`.
- **Explicit units.** Every value's unit is in `meta.units`. Storage is SI (D18); conversion happens here, at the edge.
- **Every value says where it came from.** Each day or hour carries its kind (observed, forecast, estimated). Models carry their version and their estimated and missing days (D45, D56).
- **Missing is `null`** in JSON and an empty cell in CSV. NaN never appears (it isn't valid JSON).
- **Compact by default:** values rounded to the variable's stored precision (no 15-digit floats), columnar JSON, gzip/zstd at Caddy, and an ETag on every answer, so a client that holds it gets a bodiless 304.

## The envelope

Every JSON response except tiles and binary grids:

```json
{
  "meta": {
    "request": {
      "lat": 43.073,
      "lng": -89.401,
      "start": "2026-10-28",
      "end": "2026-11-08",
      "vars": ["air_temperature_min", "air_temperature_max", "precipitation_sum"],
      "forecast": true,
      "units": "us"
    },
    "location": {
      "lat": 43.073,
      "lng": -89.401,
      "cell": { "j": 913, "i": 1477, "lat": 43.0706, "lng": -89.3973 },
      "in_box": true,
      "timezone": "America/Chicago",
      "county": "Dane County",
      "state": "WI"
    },
    "units": { "air_temperature_min": "°F", "air_temperature_max": "°F", "precipitation_sum": "in" },
    "summary": {
      "days_requested": 12,
      "days_returned": 12,
      "days_forecast": 3,
      "days_missing": 0,
      "corrections": ["nbm-max v1", "nbm-night-min v1"],
      "missing": { "air_temperature_min": 0, "air_temperature_max": 0, "precipitation_sum": 1 },
      "stats": {
        "air_temperature_max": { "min": 45.0, "max": 69.4, "mean": 58.4 },
        "precipitation_sum": { "min": 0.0, "max": 0.4898, "mean": 0.09084, "total": 0.9992 }
      }
    },
    "sources": ["urma", "rtma", "nbm"],
    "warnings": [],
    "attribution": "AgWeather, University of Wisconsin–Madison. Weather from NOAA (URMA, RTMA, HRRR, NBM), …",
    "api_version": "2.0",
    "generated_at": "2026-11-06T13:56:08Z",
    "compute_ms": 38
  },
  "data": {
    "date": ["2026-10-28", "2026-10-29", "…", "2026-11-06", "2026-11-07", "2026-11-08"],
    "kind": ["observed", "observed", "…", "partial", "forecast", "forecast"],
    "air_temperature_min": [51.6, 51.3, "…"],
    "air_temperature_max": [61.2, 70.4, "…"],
    "precipitation_sum": [0.0, 0.31, "…"]
  }
}
```

(`/weather/daily` at Madison on 2026-11-06, cut short; `stats` lists every column.)

- `meta.request` is the request **after** defaults and normalization: what was actually computed, not just what was sent.
- `meta.location` reports the cell actually read. A point snaps to the cell center, which can differ from the point asked for, so a user can see the snap. From the terrain store (D6; null where it isn't built): `elevation_m` (the point's own, from NHDPlus V2's 30 m elevation model on a 31.7 m grid), `cell_elevation_m` (the cell's mean) and `water_percent` (the cell's share of open water). Nothing is redirected: a cell mostly water is still the one read.
- `meta.summary` holds what v1's `info` had (days requested and returned, min, max, total) per variable, plus the D45/D56 counts and the corrections applied to what was read (`corrections`: the forecast's calibration, D49, and HRRR's shortwave, D48, each with its version).
- `meta.warnings` is for non-fatal notes, each a sentence in the public style (CLAUDE.md): "Precipitation is missing on 2 days. We never estimate precipitation, so the totals count those days as no rain." or "The forecast is out of date, so the series ends with the last observed day."
- Errors return 4xx or 5xx with the same envelope and `errors` in place of `data`: `{"meta": {…}, "errors": [{"code": "out_of_order", "param": "end", "message": "The end date is before the start date. …"}]}`. Each message says what happened and what to change. This replaces Ninja's default `{"detail": …}`.
- Timing also goes in a `Server-Timing` header, so latency checks against §3 don't need to parse the body.
- **Rounding:** each value to its stored precision (the catalog's scale) in the unit shown, rounded up to a whole decimal: 0.1 °C is 0.18 °F, so 1 decimal; 0.02 mm is 0.0008 in, so 4. The summary's statistics use the same digits (a mean one more).
- **Error codes** (`errors[].code`; `param` names the query parameter at fault, or is `null`):
  - the request (422): `unknown_parameter` (one per name the endpoint doesn't take, suggesting the nearest it does: v1's `start_date` → `start`), `missing`, `invalid`, `conflict` (parameters that can't go together), `out_of_range`, `out_of_order`, `too_many`, `too_large`, `unknown_variable`, `unknown_input`, `unknown_layer`, `unknown_region`, `unknown_palette`, `bad_unit`, `format_unavailable`, `not_applicable` (an option the model or layer doesn't take), `no_estimate` (no typical planting date here), `missing_inputs` (weather sent can't feed the model), `outside_box`, `not_observed` (a season's day not yet observed), `not_yet`, `no_data`; and Pydantic's type names for a value of the wrong type (`float_parsing`, `date_parsing`, `literal_error`, …);
  - `not_found` (404), `rate_limited` (429, with `Retry-After`);
  - the service (5xx): `stale` (503, a variable waiting for its rebuild), `weather_unavailable` (503 with `Retry-After`, Open-Meteo unreachable), `internal_error` (500).
- **Caching:** every answer carries an ETag and `Cache-Control: public, no-cache`: clients and caches keep it but check before reusing it, and a request with `If-None-Match` gets a bodiless 304 while the answer stands. The ETag changes when the data the answer reads is rewritten (an ingest, a rebuild), when the service is updated, or when the request does (including a default such as today's date). API responses set no cookies.

**Name:** `meta`, not v1's `info`. `meta` is the common convention (JSON:API and most data APIs), and `info` would collide with discovery endpoints. v1's URLs keep working by redirecting to the old server until it's retired (Phase 8), so v2 doesn't need v1's names.

## Data layout

**Columnar by default** (`data` is an object of equal-length arrays, as above), with `orient=records` for an array of row objects:

<!-- prettier-ignore -->
|  | columnar (default) | records |
| --- | --- | --- |
| size, 1 year daily × 5 vars | ~1× | ~2.5× before gzip, ~1.3× after |
| R | `as.data.frame(fromJSON(url)$data)` | `fromJSON(url)$data` (jsonlite simplifies it) |
| pandas | `pd.DataFrame(r["data"])` | `pd.DataFrame(r["data"])` |
| JS / ECharts | arrays go straight into series | `.map()` per field |
| simple scripts | index by position | `row.date`, `row.value` |

Both read into a data frame in one line in R and pandas. Table tools that want rows under a root key (wpDataTables in WordPress, Power Query) take `orient=records` with root `data`, or CSV. Columnar is smaller, and it is what charts want.

**Several points** come back long (tidy): one `point` column indexing `meta.locations[]`. One table holds any number of points, and CSV is the same shape.

**Flags are columns**, not nested objects: `kind` per row, and `<var>_estimated` (boolean) beside each cumulative variable that bridges gaps. They survive the conversion to CSV and data frames unchanged.

## Formats

`format=` (or the `Accept` header; the parameter wins):

<!-- prettier-ignore -->
| format | for | where |
| --- | --- | --- |
| `json` (default) | apps, scripts | everything |
| `csv` | spreadsheets, R, agencies | points, tables, grids (one row per cell) |
| `netcdf` | xarray, R (`terra`, `ncdf4`), researchers | grids and the yearly downloads |
| `geotiff` | ArcGIS, QGIS | grids (one band per day) |
| `png` | maps | tiles, legends, static maps |
| `xml` | not offered (below) | — |

An endpoint asked for a format it doesn't offer answers 422 `format_unavailable`, naming the ones it does (`/models/run` is JSON only, holding a table per model).

- **CSV** puts `meta` as `# key: value` comment lines above the header (as v1 did; `headers=false` drops them), one per top-level key, its value as compact JSON (`# units: {"air_temperature_max":"°F"}`). `read.csv(url, comment.char = "#")` and `pd.read_csv(url, comment="#")` skip them. A `Content-Disposition` filename describes the query.
- **NetCDF** keeps the native grid with its CRS (CF `grid_mapping`, Lambert conformal), so xarray (with pyproj or cartopy), terra and GIS software put it on a map correctly; it holds no 2-D `lat`/`lon` (D71). Attributes carry `meta`. This is what "xarray format" means over HTTP. Zarr stays internal; a remote Zarr endpoint isn't worth exposing.
- **XML:** not offered unless a named consumer needs it. Nobody in the v1 logs is known to, it doubles the serializer and test surface, and every agency tool that reads XML also reads CSV or JSON. If one turns up, it's a serializer over the same envelope.
- Parquet is a cheap later addition for bulk downloads if anyone asks.

## Locations, times, units

- **Points:** `lat`, `lng` (decimal degrees; v1's names). `latitude`, `lon`, `long` and `longitude` are accepted as aliases (v1 took `long` and `longitude`, and DATCP sends `long`), and `meta.request` echoes the canonical name. Several points: `points=43.07,-89.40;44.52,-89.57` (up to 50) on the weather and degree-day endpoints and `GET /models/{id}/run` (up to 10 with `projection`); `/models/run`, `/risk` and `/locate` take one. Inside the box they read our grid. Outside it, or before the archive's window, they go through Open-Meteo's per-cell cache, and `meta.sources` says so.
- **Dates:** `date` (one day) or `start`/`end` (inclusive, ISO). Days follow `day_basis` (D74): `central`, midnight to midnight CST all year (06:00–06:00 UTC), the grid's days and the default inside the box; `local`, the point's own zone with daylight saving, the default outside it. `meta.location` gives `day_basis` and `days` ("Midnight to midnight CST all year (06:00 to 06:00 UTC)."); a given `day_basis` joins `meta.request` and the ETag. On the daily point endpoints, model runs (GET and POST, as a body field), `/risk`; `/weather/hourly` refuses it (`not_applicable`), and maps, tiles and grids take only `central`. Windows within a day hold the readings stamped after their start through their end: the day from 6 pm (19:00–18:00), night (6 pm–6 am, 19:00–06:00), tar spot's 7 pm–6 am (20:00–06:00), and noon to noon for `air_temperature_min_overnight`. Defaults: from January 1 of `end`'s year through the forecast (up to 16 days ahead, trimmed to the last day with data), or to today with `forecast=false`.
- **Hours:** `start`/`end` (and a map's `time`) as ISO datetimes, with or without minutes (`2026-05-01T05`), a zone (`Z`, `-05:00`; none means UTC), the `T` or the dashes (`20260501T05`), or a bare date for its midnight; or Unix time (Wisconet's), seconds or milliseconds (12+ digits), as text or a JSON number. One parser for every endpoint and station `time` columns (`api.params.parse_time`); a bare 8-digit number is a compact date, so Unix time needs 9 or more digits (after March 1973). Times come back in UTC (`2026-05-01T05:00Z`), each hour labeled by its end, and `tz=local` adds a `local_time` column in the location's zone. Default: the 7 days before the current hour through the forecast.
- **Years** (D3, D87): the archive keeps the most recent 11 years, dropping the oldest each January (2016 goes on January 1, 2028). Maps (`/grids`, tiles, `/maps`, `/summaries`) refuse a first day before the archive's first year (422 `out_of_range`, naming the parameter and pointing to the points); days after its end show as missing. Points answer any date: before the archive (or outside the box) from Open-Meteo, as `meta.sources` says. gridMET's years build the 30-year normals (D84) and never answer as daily weather.
- **Forecast:** `forecast=true` (default) runs through the forecast, with `kind` marking it; `false` stops at the last observed day.
- **Units:** `units=us|metric`, plus per-variable overrides (`units=metric&precipitation=in`; the value is a unit symbol, its label, or `us`/`metric`, and a variable's name covers its daily statistics, so `precipitation` sets `precipitation_sum` too), **`us` by default**: that's v1's audience, and Wisconsin growers, DATCP and the site all think in °F and inches. `meta.units` always states the units in force, so nothing is ambiguous. Degree days follow the system too (°F·d or °C·d; models compute them in their own unit, D18, and the edge converts), and temperature thresholds are read in the request's units (below).
- **Gaps:** `gaps=estimate|missing` on cumulative variables (D25).
- **Areas** (D83; `agdata.areas`, `ops.points.AreaAsk`): `radius` (miles, or km with `units=metric`; over 0 and up to 10 mi or 16 km) and `weighting=equal|center` (a Gaussian with σ = radius / 2, cut off at the radius) on every point endpoint but `/locate`: the cells whose centers lie within the radius (the point's own always), clipped to the box, are read and averaged hour by hour (missing cells skipped; wind direction as vectors) before days, degree days, freezes and models are computed, so the answer is the area's weather. No mask by hand: air and wind keep lake cells, soil and snow are already missing over the Great Lakes (D79). Refused (422 `not_applicable`) for a point outside the box or before the archive. `land_only=true` (D6) leaves out cells all open water (100% by the terrain store; a cell touching land stays), the point's own included; 422 `not_applicable` without `radius`, `no_data` if the store isn't built or no cell is left. `meta.request` echoes `radius`, `weighting` and `land_only`; `meta.location.area` gives `radius_km`, `weighting`, `land_only` and `cells`. Cells are ~2.37 km across at 43°N (NDFD's 2.54 km is true at 25°N), so 10 miles is ~140–145 cells.
- **Rolling windows** (D81, Phase 6 D0; `agdata.rolling`, `api.rolled`): at points (`/weather/daily`, `/degree-days`' daily degree days), `roll=7,14,28` adds a column per window beside each value (`<column>_<N>d`); `roll_stat=sum|mean|min|max` (default `sum` for values that add up, `computed.adds_up` and degree days, else `mean`; `sum` refused on the rest); `roll_align=trailing|centered` (an even centered window has its extra day before, as pandas' `rolling(center=True)`); `roll_partial=true` clips windows at the series' ends (its first and last days with data) instead of leaving them empty; `roll_coverage` (percent, default 75; 0 is zoo's `na.rm = TRUE`). The lead-in before `start` and lead-out after `end` are read but not returned; the lead-in stops at the archive's first year rather than sending the read to Open-Meteo. `meta.summary.roll`: each rolled column's `of`, `stat` and `days`, and per point and window the `clipped` dates and `forecast_from`, the first date whose window holds forecast days; a warning counts values missing for coverage. Not with `projection`. On maps (`/grids`, tiles, `/maps`, `/summaries`, not with `interval=month`): `date` (a tile's day) with `roll=N` is the range ending on (or centered on) it, reduced by `stat` (same default) or counted by `count`; without `roll_partial`, a window reaching days with no data gives an empty map with a warning; a cell needs `roll_coverage` of the window's days. Titles "Precipitation, 7-day total", subtitles "7 days ending Jul 8, 2025 (Jul 2 – Jul 8, 2025)".
- **Biofix:** a date, or a month and day (`biofix=04-15`) meaning the latest one on or before the request's last day (`11-01` in February is last November's), on `/degree-days`, `/degree-days/table`, the model runs and degree-day maps (`api.params.resolve_biofix`).
- **Unknown parameters are refused** (422 `unknown_parameter`), not dropped: Ninja passes an endpoint only what it declares, so a misspelled or v1-style name silently changed nothing (`api.strict`, which also lets through the point aliases, unit overrides named for a variable, a model's options and `_`, a JavaScript cache-buster).

## Endpoints

All under `/api/v2`. ✓ marks what exists today.

### Discovery

<!-- prettier-ignore -->
| endpoint | returns |
| --- | --- |
| `GET /status` ✓ | service version and box; the archive's first hour, each source's newest hour, the last day rolled up and stale stores; the forecast run (cycle, last hour, in use or why not); the model count; the downloads' file count and newest build. Data facts only: jobs, the write lock and failures stay on `/up` |
| `GET /variables` ✓ | the catalog: name, long name, kind (hourly, daily, cumulative), unit (stored, and `us`/`metric` labels), precision, valid range; a daily variable's statistic and the hourly variables it comes from; a variable computed when read from stored ones (`agdata.computed`: `water_balance`, precipitation minus ET0, Phase 6 C) names them in `computed_from`, and is missing wherever one is. Date ranges are `/status`'s |
| `GET /models` ✓ | every model: id, name, group, crops, topics, status, version, summary, region, season, citations (with DOIs) |
| `GET /models/{id}` ✓ | one model's spec: required daily inputs and the hourly variables that derive them, outputs (name, unit), options (biofix, planting, maturity group: type, range, default), risk levels and criteria, changelog, and `crop`: the crop model a `planting_date` runs, whether typical dates exist, and its options (see Models below) |
| `GET /layers` ✓ | every mappable layer (`/grids/{layer}`): id, name, title (the public name maps use), group (weather, running_total, degree_days, model; a model layer also lists its `outputs` and scenario `options`), time axis (`day`, `hour`; `day_of_year` for normals later), the catalog variable, unit (stored, and `us`/`metric` labels), precision, palette id, the stats a range can be reduced to, required parameters (`dd` for degree days), and the range the archive and forecast hold now. No ETag (it follows the data, like `/status`) |
| `GET /locate?lat&lng` ✓ | `meta.location`'s fields (cell, in box, timezone, county, state) plus the cell's corners ([lat, lng], SW, SE, NE, NW, for the map highlight) and typical planting dates per crop (early, typical, late, D34) |

### Weather at points

<!-- prettier-ignore -->
| endpoint | notes |
| --- | --- |
| `GET /weather/hourly` ✓ | `lat, lng \| points, start, end, vars` |
| `GET /weather/daily` ✓ | daily variables (min, max, mean, sums, hour counts) |
| `GET /weather/totals` ✓ | sums over a window per variable with missing and estimated days: precip, ET0, water balance, shortwave, hour counts; counts within bounds (`count=air_temperature_max:days_above_86`, `air_temperature:hours_between_50_86`, repeatable, D75) with `_missing_days`/`_missing_hours`; `interval=month` for a row per month. What v1's precip/ET/insolation endpoints mostly served |
| `GET /degree-days` ✓ | one or more settings, `dd=sine_48_86,modified_38_75,average_43` (method, base, optional upper, as the catalog names them; `base, upper, method` for one), at one point or several (`points=`), `biofix`. One row per point and day: min and max temperature once, then each setting's daily value and running total as columns (`dd_sine_48_86`, `dd_sine_48_86_cum`), with estimated-day flags |
| `GET /degree-days/table` ✓ | totals only: one row per point and setting over the window, with estimated and missing days (v1's `dd_table`, generalized). What a report like DATCP's needs |
| `GET /freeze` ✓ | freeze counts and dates (last spring and first fall at thresholds) |
| `GET /chill` ✓ | winter chill per point and day from the hours (D76): `method=dynamic` (chill portions, default), `utah` (Utah chill units) or `hours` (`bounds`, default 32–45 °F); `chill`, `chill_total` since `start` (default the October 1 before the end), `missing_hours` |

Built 2026-11-03. Points inside the box (and the archive's years) read the archive and forecast; others read Open-Meteo through our per-cell cache, up to 10 a request. A default `end` runs through the forecast (16 days ahead, trimmed to the last day with data); `forecast=false` stops at the last observed day. Limits: 10 years of days or 2 years of hours a request, 100,000 rows.

**Thresholds** (degree-day `base` and `upper`, freeze `thresholds`) are in the request's units: °F with `units=us` (the default), °C with `units=metric`, echoed as `meta.request.threshold_units`. A threshold no stored air temperature can reach (outside −76 to 140 °F) is refused with a 422. An unusual one runs, with a warning in `meta.warnings`: a base outside 32–60 °F, an upper outside 70–95 °F, a freeze threshold outside 20–36 °F, and with `units=metric` a value that looks like °F (a base above 30 °C). Degree-day settings are `method_base[_upper]` (`sine`, `average`, `modified`; a decimal as `39.2` or `39p2`), named back as given (`dd_sine_39p2_84`).

**Degree-day gaps:** a day's missing min or max is interpolated across gaps up to 7 days, and the day is flagged `temperature_estimated`; a longer gap adds nothing to a running total and counts as a missing day (`gaps=missing` turns estimates off). Freezes use the measured minimum only.

### Models

<!-- prettier-ignore -->
| endpoint | notes |
| --- | --- |
| `GET /models/{id}/run` ✓ | `lat, lng` or `points=` (up to 50, 10 with `projection`: one long table with a `point` column, and what's resolved at each point, its biofix, typical planting dates and projection, in `meta.summary.points`), `start, end` (or `season=2025-26` for a seasonal product, D68), `biofix`, `planting_date` (a date, or `early`, `mid`, `late` for the point's typical dates, or `all`), plus the model's options and its crop model's as plain parameters (`maturity_group=2.5`). Columns: `date`, `kind`, the inputs with `<input>_estimated` where gaps were filled, the outputs (a crop model adds `stage_code`), `risk_level`, `risk_label`, `risk_value` (continuous risk only), `susceptibility` (only with a planting date: D64), `in_season`. Defaults: from the biofix or planting (else the spec's biofix this season, else January 1) through the forecast; no planting date, so no susceptible window; resolved values in `meta.request`, action windows in `meta.summary.windows`. Shapes provisional until the frontend uses them (D64) |
| `GET /models/{id}/run?maturity_group=all` ✓ | several option sets in one call (any choice option, or `planting_date=all`; up to 20 sets): long form, with an `option_set` column indexing `meta.summary.option_sets` |
| `GET /models/run` ✓ | `models=a,b` or `all`: several models at one point on one read of our weather; `data` keyed by model id, each with its own `meta` (`request`, `units`, `summary`, `warnings`) and `data` as `GET /models/{id}/run` gives them (D64; Veg Path's DSV and P-days). Options apply to every model that has them, `planting_date` to every model with a crop (a crop without typical dates here runs without one, warned). Default start January 1. JSON only |
| `GET /risk` ✓ | `lat, lng, date` (default today), `models=` (default: every model with a risk layer in season and in its region; given, every one asked, with `reason` where there's no risk), `planting_date`, options: one row per model with `kind`, `risk_level`, `risk_label`, `risk_value`, `susceptibility`, `in_season`, `reason`. The Crop Risk Tool's dashboard and the alerts' query |
| `POST /models/{id}/evaluate` ✓ | the explorer: `{"inputs": {"tmin": 12, "tmax": [20, 24, 28]}}` in the request's `units=`, a list sweeping (lists multiply into rows, up to 10,000); inputs left out take their defaults; values outside an input's usual range run with a warning. One row per combination: the inputs and what the model's core gives (units from `outputs` and `explorer_outputs` in `GET /models/{id}`); JSON or CSV. Same code as the runs (PLAN.md Phase 3 A) |
| `POST /models/{id}/run` ✓ | the model on **your** weather (below) |
| `POST /models/run` ✓ | several models (or `"all"`) on your weather in one call, shaped as `GET /models/run`; models the weather sent can't feed are listed under `meta.summary.skipped` with what they need |

### Where the model list comes from

VDIFN reads its model list from its database. Here the registry in code (`agmodels.registry`, one module per model with its `ModelSpec`) is the only list, so nothing needs to be kept in sync. A model's id, name, inputs, options, version and changelog live in the same file as its math, and adding a model means adding that file. The frontend doesn't hard-code models. It gets them from `GET /models` (or the same data as Inertia props on first render), so the selector, option forms, legends and model pages all follow the registry. If you ever need to hide a model without a deploy, a small admin setting can filter the list; models don't need a table.

`GET /models/{id}` describes everything needed to run the model on someone else's data:

```json
{
  "meta": {
    "…": "…"
  },
  "data": {
    "id": "tar-spot",
    "name": "Tar spot spore probability",
    "group": "disease",
    "status": "stable",
    "version": "0.1",
    "summary": "The probability of tar spot spores being present, …",
    "crops": ["Corn"],
    "topics": ["tar-spot"],
    "region": [],
    "season": ["07-01", "08-15"],
    "citations": [
      {
        "text": "Webster, R. W., Nicolli, C., Allen, T. W…",
        "doi": "10.1038/s41598-023-44338-6",
        "url": "https://doi.org/10.1038/s41598-023-44338-6"
      }
    ],
    "lookback_days": 30,
    "inputs": [
      {
        "name": "air_temperature_mean",
        "label": "Mean temperature",
        "unit": "degC",
        "units": {
          "us": "°F",
          "metric": "°C"
        },
        "description": "…",
        "model": "tar-spot"
      },
      {
        "name": "relative_humidity_max",
        "label": "Maximum RH",
        "unit": "percent",
        "units": {
          "us": "%",
          "metric": "%"
        },
        "description": "…",
        "model": "tar-spot"
      },
      {
        "name": "hours_rh_over_90_night",
        "label": "Night hours with RH ≥ 90%",
        "unit": "hour",
        "units": {
          "us": "h",
          "metric": "h"
        },
        "description": "…",
        "model": "tar-spot"
      },
      {
        "name": "air_temperature_min",
        "label": "Minimum temperature",
        "unit": "degC",
        "units": {
          "us": "°F",
          "metric": "°C"
        },
        "description": "…",
        "model": "tar-spot"
      },
      {
        "name": "air_temperature_max",
        "label": "Maximum temperature",
        "unit": "degC",
        "units": {
          "us": "°F",
          "metric": "°C"
        },
        "description": "…",
        "model": "corn-stages"
      }
    ],
    "derivable_from_hourly": {
      "air_temperature_mean": ["air_temperature"],
      "relative_humidity_max": ["relative_humidity"],
      "hours_rh_over_90_night": ["air_temperature", "dew_point"],
      "air_temperature_min": ["air_temperature"],
      "air_temperature_max": ["air_temperature"]
    },
    "context": [],
    "crop_models": ["corn-stages"],
    "outputs": [
      {
        "name": "probability",
        "label": "Spore probability",
        "unit": "percent",
        "units": {
          "us": "%",
          "metric": "%"
        },
        "description": "…"
      }
    ],
    "options": [],
    "biofix": null,
    "susceptible": {
      "crop": "corn-stages",
      "first": "V10",
      "last": "R3",
      "source": "…",
      "note": ""
    },
    "risk": {
      "levels": ["Very low", "Low", "Moderate", "High"],
      "criteria": "…",
      "thresholds": []
    },
    "explorer": [
      {
        "name": "temperature_mean_30day",
        "label": "Mean temperature, 30-day average",
        "unit": "degC",
        "units": {
          "us": "°F",
          "metric": "°C"
        },
        "minimum": 10.0,
        "maximum": 35.0,
        "step": 0.5,
        "default": 22.0
      }
    ],
    "changelog": [
      {
        "version": "0.1",
        "date": "2026-10-28",
        "note": "Ported from the Crop Risk Tool."
      }
    ]
  }
}
```

(Tar spot's spec as served on 2026-11-03, with long text and lists cut short.) `inputs` lists the daily variables the runner needs under their catalog names, including those of a crop model it's gated by (`runner.required_inputs`; tar spot's `air_temperature_max` comes from `corn-stages`), each with the `model` that reads it. `derivable_from_hourly` says which hourly variables produce each one, found by probing the rollup itself (`agdata.point.hourly_sources`), so it always matches what `POST /models/{id}/run` will do with a station's hours. Note that humid-hour counts come from the temperature and dew point (RH computed from them), not from hourly RH. A client can tell from this alone whether its station can run the model.

### Running models on your own weather

A weather network (Wisconet, a farm's own station, a vendor's sensors) sends its observations and gets the model's output back. The code is the same as for our own weather, so the two answers are directly comparable.

`POST /models/{id}/run` (and `POST /models/run` with `"models": ["tar-spot", "…"]` or `"all"`):

```json
{
  "location": { "lat": 43.07, "lng": -89.4 },
  "units": "metric",
  "hourly": {
    "time": ["2026-06-01T05:00Z", "2026-06-01T06:00Z", "…"],
    "air_temperature": [18.2, 17.9, "…"],
    "relative_humidity": [88, 91, "…"]
  },
  "start": "2026-07-01",
  "options": { "biofix": "2026-06-15" },
  "fill": "none",
  "extend": "none"
}
```

- **Daily or hourly.** Send `daily` (a `date` column plus daily catalog names: `air_temperature_min`, `hours_rh_over_90`, …) or `hourly` (a `time` column, each value for the hour ending then, plus hourly catalog names), or both. Hourly data goes through the same rollup as our archive (`agdata.point.daily_at_point`): the location's timezone sets the day boundaries, and a day needs 20 hours for a min, mean or max and every hour for a count or sum (D25). Daily values sent directly win over ones derived from hours.
- **Location** is required even though no weather is read from it. It gives the latitude (day length), the timezone, the region check and the default planting date.
- **Units** of the inputs: `units=us|metric`, with a per-variable override (`"input_units": {"precipitation": "in"}`). Output units follow the same choice.
- **The body can be CSV** (`Content-Type: text/csv`, with columns named as above), so an R or Excel user can post a file they already have: `httr2::req_body_file("station.csv")`.
- **Humidity:** RH without dew point gets dew point from RH and temperature (Magnus), and dew point without RH gets RH, each with a warning. A station's "RH ≥ 90%" hours are counted at 90%: the archive's 88% (D50) adjusts gridded RH to what in-field stations measure, and a station is that measurement.
- **Checks:** the same QC as ingest (`agdata.qc`: ranges, spikes, short gaps in the hours filled). Out-of-range values become missing, with a warning saying how many and where. A model whose inputs can't be made from what was sent returns 422 naming what's missing, and which hourly variables would supply it.
- **`fill=grid`:** fill the station's gaps from our archive at its cell, with those days' kind `grid`. **`extend=forecast`:** run on past the station's last day with our forecast for the cell, so a station network gets the next week's risk too. The default for both is `none`: by default the answer depends only on what was sent.
- **Response:** the same envelope and columns as `GET /models/{id}/run`, with `kind` = `provided`, `estimated` (a provided day where the model bridged a gap in an input), `grid` or `forecast` per day, and `meta.summary` counting each kind. A CSV body takes the rest as query parameters (`lat`, `lng`, `units`, `start`, `end`, `fill`, `extend`, `biofix`, `planting_date`, options); `meta.request.sent` says which days and variables arrived.
- **Nothing sent is stored.** Requests are computed and forgotten, and the docs say so. Limits: about two years of hourly data per request, and the rate limits (Phase 5 H, PLAN.md D69).

**POST only** for running on your own weather. A season of daily min/max would fit in a URL, but hourly data won't, and two ways to send the same thing doubles what has to be documented and tested. The GET form of `run` already covers "our weather at a point".

**A complement, not a substitute:** pulling Wisconet's and other networks' stations onto our map and charts is a later enhancement (PLAN.md, "Enhancement: station networks"). The POST endpoint serves anyone without needing an agreement with us.

### Grids

`GET /grids/{layer}` ✓ (D65): a layer from `/layers` on one day (`date`, default the last day observed everywhere in the box) or hour (`time`), each step of `start`..`end` (up to 366 days, or 31 days of hours), or that range reduced to one map by `stat` (sum, mean, min, max; sum only where values add: precipitation, ET0, shortwave, hour counts, degree days). `stat` without `start` runs from January 1 of the end's year (the season to date, as at points); an hourly layer's `stat` needs a `start`. Area: the service box, `bbox=south,west,north,east`, and/or `region=` (a state, `wisconsin` or `WI`, or a county by name and state, `Dane, WI`, or FIPS code, `55025`; cells by the county under their center), served as the smallest rectangle of cells holding it (`clip=false`, the default: a complete grid, as most grid services give it; Ben, 2026-11-11) or only the cells inside it (`clip=true`); `land_only=true` leaves out cells all open water (D6). `format` json, csv, netcdf or geotiff (`bin` waits for a need).

- **Steps have kinds** as at points (observed, partial, forecast; a step with no value anywhere is missing): the range runs from the archive into the forecast.
- **A `stat` follows the points' gap rules** (D45, D56): a sum bridges interior gaps up to 7 days by the variable's method, flagged, except precipitation (known days summed, the rest counted missing); mean, min and max use the known days. Each cell gets `estimated_days` and `missing_days` (hourly layers: `missing_hours`). `gaps=missing` turns the estimate off.
- **Counts** ✓ (D75, Phase 6 C): `count=days_above_86`, `days_below_32` or `days_between_50_86` (`hours_…` on an hourly layer; the wrong axis is a 422 naming the right one) is `stat=count`: each cell's days or hours in the range whose value is within the bounds, both inclusive, in the units the layer is shown in, with `missing_days` (or `missing_hours`) beside it; nothing is estimated (degree days count bridged days, with `estimated_days`). Any layer with a `stat` takes it, and model layers (`/maps/tar-spot.png?count=days_above_2` counts days at high risk or above); running totals don't. The value's unit is `d` or `h`, the title adds what's counted ("Air temperature, daily maximum, days at or above 86 °F"), and the legend runs from 0 to the map's high end. On tiles a range takes `count` as it takes `stat`; on `/maps`, `days=N` with `count`.
- **First and last days** ✓ (D78, Phase 6 C): `first=`, `last=` or `since=` with `api.counts`' bounds (`above_50`, `below_32`, `between_50_86`, inclusive, in the units the layer is shown in) or a named threshold of the daily minimum (`frost` 32 °F, `hard_freeze` 28 °F, `killing_freeze` 24 °F, in °F whatever the units) is `stat=first|last|since` on a daily weather layer (not hourly, running totals, degree days or models): each cell's first or last day in `start`..`end` within the bounds, or the days from the last one to `end`. Without `start`, a `below` event starts on the previous July 1 (a cold season runs July to June: in May, `first=frost` is last fall's first frost) and any other on January 1; `date` is refused (give `end`). Measured days only (D45). Each cell is found, none (`found` false: values but no such day) or no data (`found` null), with `missing_days`. Dates are days since 1970-01-01 (unit `date`): ISO dates in JSON and CSV, CF `days since 1970-01-01` in NetCDF (xarray reads them as dates), numbers in GeoTIFF and data tiles, where none is code 1 (`encoding.none`). Images and colored tiles draw none light gray and no data darker gray, with a swatch for each on the map; a date legend ticks month starts (and the 15ths over a short range), with a scale at least 14 days wide inside the window. Titles add what's found ("Air temperature, daily minimum, first frost (32 °F)", "days since the last hard freeze (28 °F)"). On tiles, `{time}` with an event is the window's end. At points: `/weather/totals` `first=air_temperature_min:frost` (and `last`, `since`; repeatable or comma-separated), columns `<var>_<kind>_<event>` (an ISO date, or days) and `_missing_days`, each with its own default start (`meta.request.event_start`); `since` counts to today when `end` is the forecast's default.
- **Degree days for any setting:** `/grids/degree_days?dd=sine_48_86` (one setting) gives each day's degree days from the day's min and max, as `/degree-days` does at points; `stat=sum` over `start`..`end` is the total from `start`; `biofix` (a date or MM-DD) is the same with the sum implied (`/maps/degree_days.png?dd=sine_50_86&biofix=04-15`). A setting the archive keeps as a running total (single sine at its thresholds, a sine pair of them, modified 50/86) is read from it for a sum within one year, the same to its 0.5 °F·d (`meta.summary.from_running_totals`). The running totals themselves (`dd_modified_50_86`, `precipitation_total`, `et0_total`) are layers whose day is the total since January 1; they take no `stat`.
- **Chill and heat stress** ✓ (Phase 6 C6, D76, D77): daily layers `chill_hours` (0–7.2 °C), `utah_chill_units` (each a season's total with `stat=sum` from `start`), `thi_min`, `thi_mean`, `thi_max`, `hours_thi_over_68`, `hours_thi_over_72`, `cci_max`; hourly `thi_hourly` and `cci_hourly` (computed when read); and `chill_portions`, the Dynamic model since October 1 (a running total kept from the hours, `agdata.chillseason`, continued through the forecast; no `stat`). Chill at points from any start is `GET /chill`.
- **A stale variable** (D29, between a deploy and its rebuild) is computed from the hours for up to 7 days; a longer range is a 503 (`stale`) until the rebuild is done.
- **Model layers** ✓ (Phase 5 F3, D47, D66): each model with a map is a layer under its own id (`/grids/tar-spot`), finished per cell from its stored ingredients. `output=` picks the value (`/layers` lists each model's `outputs`): by default the risk level (an index into the model's levels), `risk_value` where the risk is continuous (the insects' activity), or any of the model's outputs; a crop model's default is its stage. The model's scenario options are parameters as at points (`/grids/white-mold?irrigation=irrigated`), one value each. A map uses each place's own settings, so `biofix`, `planting_date`, `black_layer_gdd` and `maturity_group` are refused (422) pointing to `/models/{id}/run`. A model with a crop takes `planting=early|mid|late` (default mid: each place's typical date, `agdata.planting`) or `none` (the model's default dates, no gating): a crop model starts at each cell's planting, a stage-anchored biofix (the blights' emergence) is each cell's day at that stage, and a stage-gated disease adds a `susceptibility` output (0 not susceptible, 1 near, 2 susceptible; D33). `meta.summary.planting` gives the tier's dates over the cells and how many have none (those take the model's defaults, with a warning). Soybean and spring wheat stages are stored per tier and take one (no `none`); red crown rot is computed from each place's R1. A range takes `stat` mean, min or max. Cells outside a model's states are missing, with a warning; so is a day before the season's biofix. Not a model layer: custom degree days (the `degree_days` layer).
- **Seasonal products** ✓ (Phase 4 H, D68): a model that settles once a season (potato volunteer's winter, November 1 to March 31) is a layer like any model's, with seasons. `season=2025-26` (`/layers` lists the seasons held) is its count through the season's last day, or the last observed day before it; without a date or season, the current season: the newest whose map has appeared (`GET /models/{id}`'s `seasonal_appears`, January 1 for potato volunteer, so in November and December the last winter's settled map). `date=` or a range gives the running count on any days, the open season's with a warning before it appears. Seasons count observed days only: a day after the last observed one is a 422 (`not_observed`). `meta.summary.season` gives `name`, `label` (2025–26), `first`, `last`, `appears`, `through` and `final` (the season's last day is in and none of its hours are provisional: ERA5-Land's soil has replaced IFS's, about five days after). Projected outputs carry one day's season to its end on each earlier season in the archive (D63, D67): `projected_<output>` and `projected_risk_level` are the medians (an even count's level is the higher, riskier, of the middle two), `chance_<level>` the percent of seasons ending at that level (`chance_low`, …, `chance_very_high`), with each cell's `projection_seasons`; `meta.summary.projection.seasons` lists them. One day only (a date or season, no range). `/models/{id}/run` on a seasonal model defaults to the current season too and takes `season=`.

The native grid is Lambert conformal, not a lat/lng raster, so:

- NetCDF and GeoTIFF carry the true projection (exact; GIS reprojects). NetCDF-4: CF `grid_mapping` (`lambert_conformal_conic`, one standard parallel at 25° N, central meridian 95° W, on NDFD's 6,371,200 m sphere, with the same projection as `crs_wkt`), projected `x`/`y` in metres, `time` (none for a stat), `cell_methods` (`time: maximum`, then the stat), `meta` as global attributes. No 2-D `lat`/`lon` (D71): beside the data they made GDAL open the file as subdatasets, and terra on Windows given an absolute path (`D:/…`) fell back to the HDF5 driver, losing the CRS (before that, as CF auxiliary coordinates, GDAL took them as geolocation arrays and terra couldn't reproject). To plot on latitude and longitude without a projection library, take them from the downloads' `daily/grid.nc` (`ds.assign_coords(lat=grid.lat, lon=grid.lon)` for a whole-box file), or use JSON or CSV, which give each cell's. A file holds the one gridded variable asked for: with `stat=sum`, the per-cell counts (`estimated_days`, `missing_days`) come only in JSON, CSV and GeoTIFF, since a second variable makes GDAL see subdatasets again. Data deflated at level 6, a whole map per chunk. GeoTIFF: one band per step (then the counts), north up, Lambert 1SP GeoKeys, NaN as no data, each band's date as its description.
- JSON and CSV are long form, one row per cell and step: `date` (or `time`) and `kind` without a stat, `lat`, `lng` (the cell center), `j`, `i` with `cells=true`, the value under the layer's id (so a unit override such as `precipitation=mm` applies), and with a stat the counts.
- `stride=n` takes every nth cell in each direction for coarse overviews.
- **Regular lat/lng grids:** v1's grid was regular 0.1° lat/lng. `grid=latlon&res=0.1` (any step from 0.025° to 5°; points on multiples of it, 42.4, 42.5, …) with `method=nearest` (the cell under each point) or `mean` (the cells whose centers fall within ±res/2 of the point; the default from 0.05°, since a 0.1° box holds ~15 cells). The lat/lng → cell index is cached per area and step: ~1 ms to build at 0.1° (nearest) over Wisconsin, ~20 ms for mean, ~1 ms a day after. v1's `/api/weather/grid?date=` is one such request per variable (`docs/validation-v1-grid.md`).

Size limit: JSON and CSV take up to 2 million values (Wisconsin is 57,820 cells, so about 34 days; ~70 MB), and a bigger request is refused pointing to netcdf/geotiff, a stat, a smaller area or a stride. Files take up to 22 million (a leap year of days over Wisconsin). Answers revalidate by ETag, stamped by the write times of the stores the map reads.

### Summaries

`GET /summaries/{layer}` ✓ (Phase 6 C5, F7): any `/grids` layer, with its time, `stat`, `count`, `first`/`last` and settings, summarized over each county (`by=county`, the default) or state (`by=state`). `region=` limits the rows (a state gives its counties); without it, every county or state at least partly in the box. `interval=month` gives a row per month of a range (daily layers, with a statistic; not seasons or projections). JSON and CSV, long form: `fips`, `name`, `state` (counties), `date`/`time` and `kind` without a stat or `month`, `area` (the Census Bureau's land area; km², sq mi in US units), `cells` (the region's cells on the whole grid), `cells_with_data`, `cells_none` (first/last days: none found, counted as data), `coverage` (percent), `complete`, then `mean`, `min`, `max` (dates for first/last days), or for a map of levels `pct_<level>` and `highest`.

- **A region's cells** are those the county grid gives it less open water (`regions.summary_counties`: `coast.water`, the Great Lakes and the ocean); counts per county are in `counties.csv` (`scripts/build_counties.py`).
- **Coverage** is cells with data over the region's cells, so it falls both outside the box and where cells have no value (soil along the shore, where ERA5-Land has no land point near enough). Under `min_coverage` (default 50) the statistics are null, the row kept, and a warning counts them.
- **The mean is unweighted** (cell areas differ < 2% across a state). Up to 200,000 rows. ETag as the map's.

### Tiles

Built (Phase 5 G1–G2, ✓):

- `GET /tiles/{layer}/{time}/{z}/{x}/{y}.png`: data tiles, 256-pixel web mercator, zooms 0–8 (TileJSON says 3–8; past 8 a client enlarges zoom 8). `{time}` is one step: a day (`2025-07-08`), an hour (`2025-07-08T15`), a range of days with `stat` (`2025-07-01..2025-07-07`), a seasonal product's season (`2025-26`), or `latest`. The layer's settings are query parameters as on `/grids` (`dd`, `output`, `planting`, a model's options). Each pixel is the grid cell under it, its value packed into the color: `value = (R·65536 + G·256 + B) × step − 8,388,608 × step` in the layer's stored unit, transparent (code 0, alpha 0) where missing. MapLibre reads them as a `raster-dem` source with `encoding: "custom"` and the TileJSON's factors, for a `color-relief` layer to color with the layer's palette; a client reads the value under the pointer from the pixel. Model layers are land only (no Great Lakes).
- `?style=default`: the same tiles colored with the layer's palette (`/palettes`) over its `domain` (`/layers`; a layer without one takes it from the whole map, so every tile agrees), for ArcGIS Online, QGIS or Leaflet with one URL.
- `GET /tiles/{layer}.json?time=&…`: TileJSON 3.0 (the tile URL with the settings, bounds, zooms) with `encoding`: `unit`, `step` and MapLibre's `redFactor`, `greenFactor`, `blueFactor`, `baseShift`.
- `GET /tiles/{layer}/legend.png?time=&units=&…`: the colored tiles' legend: a color bar with ticks in the request's units, or a swatch per level.
- `GET /palettes`: every palette, named by its colors from low to high (`BuYlRd`, `YlGnBu`, `viridis`): `id`, `kind` (sequential, diverging, categorical, cyclic), `colors` low to high, `description`, `source` (ColorBrewer, matplotlib, AgWeather v1, VDIFN; ColorBrewer's RdYlBu reversed is `BuYlRd`), and `colorblind_safe`. A palette id ending `_r` (in `/layers`) is that palette reversed: dew point depression's `BrBG_r`. Palettes are defined apart from their uses (`agdata.palettes.PALETTES` and `USES`, D73), so the frontend can offer a reader another palette: v1's `rainbow` and VDIFN's `GnYlRd` are listed for that and assigned to nothing (`colorblind_safe` false).
- **`scale=`** on `/maps`, colored tiles, legends and the TileJSON: what the colors span. Left out or `auto`: the map's 2nd to 98th percentile, rounded (Ben, 2026-11-10: every map fits its colors to its values); `default`: the use's fixed range where it has one, for comparing days color for color; `low,high` in the request's units (`scale=40,90` with `units=us` is °F), or `low,middle,high` to put the palette's middle color at `middle` (`scale=0,32,100`, `scale=,500,`), each half stretched over its side; an end blank takes it from the map, and one that falls on the wrong side of the middle becomes the middle (the map uses only the half it reaches). Wind direction keeps 0–360 (a cyclic palette is fixed) and counts run from 0 to the data's high end. Categorical maps take none. A TileJSON for `style=default` reports `palette`, `domain`, `domain_unit` and, with a middle, `domain_middle`.
- **`palette=`** on the same endpoints: any `/palettes` id, `_r` reversing it (`palette=viridis`, `palette=BuYlRd_r`); it joins the ETag and `meta.request`. A categorical map takes only a categorical palette with as many levels (`not_applicable` otherwise), and a continuous map no categorical one; an unknown name is `unknown_palette`.
- Tiles, legends and maps revalidate by ETag (the request and its data stamp; a tile's stamp is reused for 15 s, so new data shows within that) and carry `Cache-Control`: `latest` and the last 10 days `max-age=300`, older times a day, with `stale-while-revalidate`.

### Climate

Built in Phase 6 with the climatology (D11, D22); the contract is set now so Phase 5's plumbing fits it. Normals are a reference period's typical values, by day of year. "Current against normal" compares this year's observed days, then the forecast, with them.

Points compute from the period's own years (`api.climate`, D86): the archive's past-years copies and gridMET's derived years, read for the cell or the `radius` area (~0.5 s for 30 years), so any percentile, setting, `window` and area works; the stored normal maps (D85) serve only maps, and a test holds a point to its cell's map. Inside the box only. `/climate/normals` ✓ (2026-11-11): rows per point and date of one calendar year (`start`/`end`/`date`, default this year), with `day_of_year`; `vars` from the normal maps' daily variables (no `air_temperature_mean` with `last30`); `<var>`, `<var>_p<N>`, and for values that add up `<var>_cum` from `start`; `dd=` alone gives only degree days (`dd_<s>`, `dd_<s>_cum`, from each year's days bridged as the cumulative store bridges them); `interval=month` or `year` from each year's own mean or total (a year counts with at most 10% of the span's days missing); `roll=` circular around the year; `meta.summary` names the period's years, the missing ones and each point's years with data. `/climate/frost` ✓ (2026-11-11): a row per point and threshold (`thresholds=`, `/freeze`'s parsing), `last_spring_p<N>`, `first_fall_p<N>` (this year's dates; null where the share reaches years with no freeze) and `season_days_p<N>` (fall date less spring date, a season without a freeze counting as the year's end or start) for `probabilities=` (default 10, 50, 90), with the years counted and without a freeze. `/climate/frost/chances` ✓: a long table, a row per point, threshold and date, with `season` and `chance` (percent: after the date in spring, by it in fall). Both match the stored freeze maps (D85) exactly at the dev archive's farm cell. `/climate/compare` ✓ (2026-11-11): rows per point and day from `start` (one calendar year): `kind`, and for each of `vars` (precipitation, ET0, sunlight) and `dd=`: `<X>_cum` (this year through the forecast, totalled as `/degree-days` and `/weather/totals` total it; null past the forecast, or past the observed days with `forecast=false`), `_cum_last_year` (the period's last year), `_cum_normal` with `percentiles` (default 10, 90), `_departure`, `_percent_of_normal`, `_percentile` (ties count half). `meta.summary.compare`: the last observed day (`as_of`), each total's percentile, and for degree days `days_ahead` (the day the normal total is nearest this year's as it passes it, less `as_of`; null when the normal never reaches it in the year). The summary carries no totals, so it needs no unit conversion: they're in the as-of row. Climate maps ✓ (E4, 2026-11-11; `api.climatemaps`): `climate=normal`, `departure` or `percentile` with `period=` on `/grids`, tiles, `/maps` and `/summaries`, for layers listing it in `/layers`' `climate`. A normal reads only the stored maps (D85), so it takes any date, future ones included; it's refused where the map isn't linear in them (a range's min or max, counts, events, hourly and model layers, settings off the cubes, a custom pooling window, several steps without `stat`). A daily sum of precipitation or ET0 takes its normal from the normal running total (each year's own), sunlight's from its days' pooled means. A departure's temperature unit is `delta_degF`/`delta_degC`. Percentiles come from the stored deciles, interpolated, 5 under the 10th and 95 over the 90th; their colors are fixed at 0–100. New layers: `freeze_chance` (`day_of_year`: `date` in any year, `threshold=32`, `28` or `24` °F), `freeze_dates` (`none`: no time; `output=` the 10/50/90% dates in this year, or `season_days_p50`) and `elevation` (`none`; `output=mean`, `min`, `max`, `spread`; units `m`/`ft`, a new `elevation` dimension); a layer with no time has no `date` column or file time step. `manage.py latency` times a season's degree-day departure (196 ms first tile on the dev archive), a month's normal (229 ms) and a point's 30-year normals (592 ms).

<!-- prettier-ignore -->
| endpoint | notes |
| --- | --- |
| `GET /climate/normals` | at points: daily normals by day of year (min, max, mean temperature, precip, and later gridMET's humidity, wind, solar and ET0), with `interval=day\|month\|year`. `period=last30` (the trailing 30 complete years from an external gridded source, the default; D82) or `last10`, `last5` (our archive), all rolled forward each January. Every day's statistics pool a centered 15-day window across the years (`window=`). Percentiles (`percentiles=10,50,90`) as columns beside the mean; `roll=` as on the weather endpoints (D81) |
| `GET /climate/normals` with `dd=` | normal degree days for any setting (DATCP's eight included): each day's normal and the normal running total from `start` (default January 1), with the spread across years |
| `GET /climate/compare` | this year against last year and normal at points, for weather and degree days (`dd=`): observed and forecast running total, last year's total to the same date, the normal total, the departure, the percentile among the reference years, and for degree days "N days ahead/behind normal" (the date the normal total reached today's). DATCP's table could carry departures directly |
| `GET /climate/frost` | last spring and first fall freeze at thresholds (32, 28, 24 °F; any via `thresholds=`) at probabilities (10, 50, 90%), and growing-season length; from the reference years |
| layers | normals, departures and percentiles as `/layers` (time axis day of year), so `/grids`, tiles and `/maps/{layer}.png` work for them: a "GDD departure from normal" map is a layer like any other |

Normals of anything with a threshold (degree days, freeze dates, hours above or below) are each year's value averaged across the years, never the value computed from averaged temperatures. A normal day of 45/65 °F gives different degree days from the average of thirty real days. That's why the climatology keeps the daily data of the reference years on the grid, not only day-of-year statistics, so any setting can be computed on request (Q34).

**Gridded and station normals:** NOAA's official 1991–2020 normals (and the Wisconsin State Climatology Office's tables built from them, which DATCP uses) are per station. Ours are gridded and cover the trailing 30 years (D82), so they differ from a station's both by place and by period; NOAA's station normals serve as a check. The migration guide for DATCP compares the two at their 23 points. Station normals could be added beside the station layer (D59; Q35).

**Projection past the forecast** ✓ (D63, opt-in): `projection=true` on `/models/{id}/run`, `/models/run`, `/degree-days` and `/risk` carries the series past the forecast to `end` (default: the model's season end; December 31 for several models and degree days) once per earlier year in the archive, each year's days spliced on by calendar date. Projected days come back with kind `projection`; each number column holds the P50 across years, with `<name>_p10` and `<name>_p90` beside it and `projection_years` (how many years have a value that day). `projection=years` returns each year's whole path instead, long form with a `year` column. `meta.summary.projection` lists the years and where the projection starts, and `milestones`: when each crop stage, risk level and action window comes, "in k of n years" with P10/P50/P90 dates. `/degree-days` takes `targets=1400,2000` (in the request's units) for when each running total reaches each, with or without a projection; `/risk` with a `date` past the forecast reports each model's P50 level. One year in the archive gives P50 only, with a warning; none, or a point outside the service box, gives no projection and a warning.

### Static maps

`GET /maps/{layer}.png` ✓ (D60, Phase 5 G3): a finished map image to embed by URL, with county and state outlines (Census 1:5M), the title, the date, a legend and a credit. It takes the layer's time and settings as `/grids` does (`date`, `time`, `season`, `start`/`end` with `stat`, `dd`, `output`, `planting`, options), plus `days=N` (the N days ending on `end` or the latest day, with `stat`: `days=7&stat=sum` is the last week's rain), `region` (a state or county, framed; `clip=true` blanks the frame outside it), `units` and `width` (400–2000 px, default 800). Without a time it's the latest day, so a link such as "Today's growing degree day map" (`/maps/dd_modified_50_86.png`) stays current. **Titles** (`api.maptitles`; Ben, 2026-11-06, after v1's `image_title`) go from broad to specific with commas: the subject, then the statistic (`Air temperature, daily maximum`; over a range `Precipitation, cumulative total`, `Air temperature, cumulative maximum` where the range's statistic is the day's own, else `mean daily maximum`), degree days with method and thresholds in the request's units (`Growing degree days, single sine 50–86 °F, cumulative total`), a model as `[model]: [result]`. The subtitle has the region, the dates with three-letter months and, for a range combined or a running total, the days or hours it combines (`Jan 1 – Nov 5, 2026 (309 days)`; Ben, 2026-11-07), an hour in Central time with UTC (`Nov 6, 2026, 7 a.m. CST (13:00 UTC)`), and a model's planting tier and options. A caption gives the data sources by family (`Air temperature (2 m) from URMA/RTMA hourly grids`, and the forecast where the map includes forecast days) and, for a range with any, the most days or hours estimated or missing at any location that has a value (`At some locations, up to 2 days were missing.`). The same title is the legend's, the TileJSON's `name`, a grid file's `long_name`, and `/layers`' `title` (without dates). Images are kept by ETag, drawn once per change of their data; a job draws the default set after each hourly ingest (modified 50/86 degree days, the day's high and low, the last week's rain and ET0, the day's sunlight, the season's rain and ET0).

Added 2026-11-10 (Phase 6 H): a frame with a latitude-longitude graticule labelled at the left and bottom edges (1° over a state, 0.5° or 0.25° over a county); `isolines=auto|off|N` (lines at the legend's ticks, or every N in the shown unit, days on a date map, with the legend ticked at the same values; drawn on the values smoothed by a Gaussian of 2 cells, missing cells left out; the middle of `scale=` heavier; more than 100 lines is `too_large`; categorical maps refuse it); and `Content-Disposition: inline; filename="…"` built from the resolved request (`soil_temperature_4cm_mean_min_2025-07-01_2026-07-01.png`), which browsers offer when the image is saved.

### Downloads

Yearly NetCDF per daily variable for bulk users ✓ (D69, D71, Phase 5 H2), as static files beside the API: `/downloads/daily/{year}/{variable}_{year}.nc`, one per finished year and one for the current year to date (rebuilt at most weekly). `GET /downloads` lists them (variable, year, URL, bytes, first and last day, `complete`, `built_at`) with `grid`, the URL of `daily/grid.nc`; `/status` gives the count and the newest build.

- **A yearly file** holds one gridded variable: the year's days through the last rolled up, in the **stored (metric) units**, on the native grid (CF `grid_mapping` `lambert_conformal_conic`, projected `x`/`y` in metres, `time` as days since 1970-01-01). Values are the daily store's int16 copied as stored, with `scale_factor` and `add_offset` (float32, so readers unpack to float32) and `_FillValue` −32768: lossless against the archive and 20–35% smaller than float32. Deflate 6 with shuffle, a day per chunk.
- **`daily/grid.nc`** holds what every yearly file shares: each cell's `lat` and `lon` (float32, its center, as plain variables as `/grids` writes them) and `time_zone` (CF flags naming the zones), the cell's local zone for showing its hours on its own clock; every file's days are CST (D74, the files' `days` attribute). They're kept out of the yearly files (D71): with 2-D `lat`/`lon` beside the data, GDAL opens a file as three subdatasets, and terra on Windows given an absolute path (`D:/…`, whose colon breaks the subdataset name) fell back to the HDF5 driver: no CRS and the packed integers unscaled. With one variable GDAL opens the file as one raster of N bands (checked: rasterio, terra by absolute and relative path, Ben's Windows terra 1.9.50).
- **Kept current** by `ops.downloads`: a file is rebuilt when its daily store has been written since it was built (`GridStore.written`), the current year's at most weekly, and any built in an older layout (`downloads.FORMAT`); `manage.py downloads` (`--check`, `--variables`, `--background`) and the Monday `build_downloads` job. Caddy serves `/downloads/*` from the data volume (read-only) with `Cache-Control: public, no-cache` and its own ETag; Django serves them in development.
- **Use:** R `terra::rast(file)` reads the projection and the scale; xarray `open_dataset(file)` unpacks the values, and `assign_coords(lat=grid.lat, lon=grid.lon)` from `grid.nc` plots without pyproj. The public page (`api/docs/discovery_download_list.md`) has both examples.

## Access, limits, stability

- **Anonymous reads** with per-IP rate limits ✓ (PLAN.md D69, `api.ratelimit`): a budget of 200 units a minute per IPv4 address or IPv6 /64 (`API_RATE_LIMIT`), a request costing 1 unit plus 1 per 100 ms of server time, so a kept tile or a 304 costs 1 and a map computed afresh several. Every API response carries `RateLimit-Limit`, `RateLimit-Remaining` and `RateLimit-Reset` (seconds to the minute's end); a client over its budget gets a 429 (`rate_limited`) with `Retry-After`. Optional free API keys (`X-API-Key`) for higher limits, and so we know who to tell before a change, are added when someone needs more.
- **Stability:** `/api/v2` changes only by addition (new endpoints, parameters, columns, `meta` keys). Anything breaking is announced on the changelog page and in `meta.warnings` well ahead. Clients should ignore keys they don't know.
- **Types:** the frontend's TypeScript types are generated from the OpenAPI schema, as `bin/types` does for props (`@/types/api`), so CI fails when the frontend and API disagree.
- **Docs:** OpenAPI at `/api/v2/docs`, its public text kept in `app/api/docs/` (an intro, a page per endpoint, `parameters.toml`; `test_docs` checks each endpoint and parameter has text in the public style), with D53's attribution and links to the changelog and feedback pages (Phase 7). R, Python and curl examples per endpoint come in Phase 8, after the frontend; the downloads page has R and Python examples now.

## Examples (target)

```r
library(jsonlite)
r <- fromJSON("https://agweather.cals.wisc.edu/api/v2/degree-days?lat=43.07&lng=-89.40&base=50&upper=86&start=2026-03-01")
dd <- as.data.frame(r$data)
r$meta$summary

wx <- read.csv("https://agweather.cals.wisc.edu/api/v2/weather/daily?lat=43.07&lng=-89.40&format=csv", comment.char = "#")
```

```python
import io

import pandas as pd
import requests
import xarray as xr

base = "https://agweather.cals.wisc.edu/api/v2"
r = requests.get(f"{base}/models/tar-spot/run", params={"lat": 43.07, "lng": -89.40}).json()
df = pd.DataFrame(r["data"])

grid = requests.get(f"{base}/grids/dd_modified_50_86", params={"date": "2026-07-01", "format": "netcdf"})
ds = xr.open_dataset(io.BytesIO(grid.content))
```

## Migrating from v1

**Where v1 goes (D62):** at launch v2 takes over `agweather.cals.wisc.edu`, and v1 moves to `legacy.agweather.cals.wisc.edu` for a year. Any `/api/…` request outside `/api/v2` is redirected there (308, path and query kept), so a v1 caller that follows redirects keeps working until the legacy host is retired; move to v2 before then.

Each v1 caller in the old server's logs (TODO.md, Phase 5, has the list) is below: its query, the v2 request that replaces it, and what it will see differently. The numbers come from comparisons with the live v1 API (D54: they explain differences, they don't judge accuracy), and the per-caller guides in Phase 8 are written from them. Three causes run through every comparison: v2 reads URMA where v1 read RTMA (URMA's minimums run a little cooler); v1 averages the 2.5 km cells around its 0.1° point while v2 reads the point's own cell; and v1's day is the Central-time hours 00–23 where v2's is the local hours ending 01–24. Two behaviours differ everywhere: v1 counts a day without data as 0 in a running total, silently, where v2 bridges gaps up to 7 days with a flagged estimate and counts longer ones as missing; and v1 ends at its last full day, where v2 runs through the forecast unless asked `forecast=false`.

**DATCP's degree-day report** (confirmed 2026-11-02; `docs/validation-v1.md`): eight settings at 23 locations every morning, January 1 to yesterday: 184 requests to `/api/degree_days`. Their table has ten columns: the eight settings, last year's modified 50/86, and the 1991–2020 normal modified 50/86 (from a State Climatology Office spreadsheet). In v2 the eight are one request:

```
/api/v2/degree-days/table?points=43.2,-90.2;…&dd=average_43,average_50,average_52,modified_38_75,modified_40,modified_50_86,sine_39_84,sine_48_86&start=2026-01-01&forecast=false
```

or `/degree-days` with the same parameters for the daily series; last year's column is a second request with last year's dates, and once the climatology exists (Phase 6) one `/climate/compare` adds last year, the normal, the departure and days ahead or behind for every setting. v2's totals run 1.0–1.5% below v1's for every setting (−32 to −52 °F·d on 2,500–5,200 by October 31; single points from −117 to +65), from a daily minimum 0.41 °F lower on average. More than half of that comes from when the day starts: v1's day is midnight to midnight Central time and follows daylight saving, while v2's is midnight to midnight CST all year, an hour later from March to November. Adding `day_basis=local` gives v1's days, and then the totals run 0.4–0.6% below v1's (−13 to −24 °F·d), with a daily minimum 0.21 °F lower on average.

**The Waunakee lawn notifier** (`docs/validation-v1-dd-table.md`): `/api/degree_days/dd_table?lat=43.18&lng=-89.45&models=dd_50_86,dd_32` and 30 days of `/api/precips`, twice a day. v1's `dd_50_86` is single sine 50/86 °F and `dd_32` single sine from 32 °F with no upper threshold, so in v2:

```
/api/v2/degree-days?lat=43.18&lng=-89.45&dd=sine_50_86,sine_32&forecast=false
/api/v2/weather/totals?lat=43.18&lng=-89.45&start=2026-10-02&end=2026-10-31&vars=precipitation_sum
```

The columns match `dd_table`'s (each day's value and running total per setting, the day's minimum and maximum), as columns rather than an object per date. January 1 to October 31, 2026: sine 50/86 3,184 °F·d against v1's 3,203 (−0.6%), sine 32 7,167 against 7,203 (−0.5%), on v2's CST days (`day_basis=local` gives v1's days, which follow daylight saving); precipitation October 2–31 27.0 mm against 28.9.

**Nortera** (a vegetable processor): sine 50/86 degree days from May 1 and precipitation at 8 points, daily. In v2 one `/degree-days?points=…&dd=sine_50_86&start=2026-05-01` and one `/weather/totals` (or `/weather/daily`) with the same `points`. Expect what the lawn notifier's comparison shows for sine 50/86 (about 0.6% below v1) and DATCP's points show for precipitation (4% below v1 over January to October).

**ET at points** (two .NET clients: one point over the last 30 days, with and without `method=adjusted`; 28 points over the last 10 days; `docs/validation-v1.md`): `/weather/daily?points=…&vars=et0_sum&start=…` for each day, or `/weather/totals` for the sum. v2's ET is FAO-56 grass reference ET0, not v1's own method (Diak et al. 1998), and has no `adjusted` variant. At DATCP's points, January to October: v2 772 mm against v1's 796 (3% below) and 566 for `method=adjusted` (36% above), so the client asking for `adjusted` sees the largest change.

**Veg Path's tables** (`pest_forecasts/vegpath` at 7 points, through wpDataTables; `docs/validation-vegpath.md`): one `/weather/daily?points=…` for the weather, plus `/models/run?models=early-blight-pdays,late-blight-dsv` per point; wpDataTables reads `orient=records` with root `data`, or CSV. May to September 2026: daily maximum temperatures within 0.3 °F on average and minimums within 0.8 °F (v2's day is CST all year, v1's follows daylight saving), RH within 1.3%, P-days within ±4%. Late blight DSVs read higher by design: 27–51% above v1's season totals, mostly because gridded RH ≥ 90% is counted at 88% (D50), the rest from v2's late blight day starting at 6 p.m. CST (7 p.m. CDT) and URMA against RTMA.

**Daily Wisconsin grids** (`/api/weather/grid?date=…`, from R; `docs/validation-v1-grid.md`): one `/grids/{variable}?date=…&grid=latlon&res=0.1&method=mean` per variable, on the same 0.1° points. Minimum −0.45 °F on average (MAE 0.72), maximum +0.00 (0.44), dew point −0.02, RH within 0.6%, hours of RH ≥ 90% +1.48 (D50's 88%). Most of the minimum's difference is the day: v2's grid days are CST all year, and v1's followed daylight saving.

**The UW Insect Diagnostic Lab's map link** ("Today's Growing Degree Day Map", v1's `/api/degree_days/map.png`, which draws v1's default, sine 50/86 since January 1): `/api/v2/maps/degree_days.png?dd=sine_50_86&stat=sum` runs from January 1 to the latest day, so the link stays current. v2's own default map, `/maps/dd_modified_50_86.png`, is modified 50/86 since January 1 (one of v1's default map set, Phase 5 G3; drawn when first requested); which one the lab links to is their call.

## Implementation choices

Made as the work landed, and recorded in PLAN.md Phase 5: model maps are finished on request from stored ingredients (D66, F), with crop stages stored per planting tier (D70); tiles pack values as Terrain-RGB with each layer's step (G1); tiles stay in Django, with no Starlette mount (§9; G4 measured Django's share as small).
