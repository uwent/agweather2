# API v2 design

Agreed 2026-11-02 (D57, D58). The contract for `/api/v2`: what each endpoint takes and returns, in which formats, and why. PLAN.md Phase 5 holds the work list and the decisions (D57 the contract, D58 models on your own weather); this file is the spec they refer to, and the source for the public API docs page in Phase 6. Details below are refined as the endpoints are built, and recorded here.

## Who it serves

1. **The app's own frontend.** Pages get their first render from Inertia props, but everything interactive (click the map → a chart, change a model option, scrub the slider) fetches from `/api/v2`. The frontend is the API's first client, so the public API is never a second-class copy of what the site can do.
2. **Researchers and scripts** (R, Python, Excel): a URL that reads straight into a data frame, with the query and units stated in the response.
3. **Agencies** (DATCP, DNR): stable URLs, CSV, and GIS formats (GeoTIFF, rendered XYZ tiles) that drop into ArcGIS and QGIS.
4. **Farmers' and vendors' software:** simple GET requests and predictable JSON. Missing data is `null`, never 0, and nothing depends on undocumented defaults.

## Principles

- **GET with query parameters** for every read, so a URL can be shared, bookmarked, cached and read with `read.csv(url)`. POST only where the input won't fit in a URL (model evaluation, very many points).
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
      "start": "2026-05-01",
      "end": "2026-05-07",
      "vars": ["air_temperature_min", "air_temperature_max", "precipitation"],
      "units": "us",
      "forecast": true
    },
    "location": {
      "lat": 43.073,
      "lng": -89.401,
      "cell": { "j": 112, "i": 140, "lat": 43.071, "lng": -89.398 },
      "in_box": true,
      "timezone": "America/Chicago",
      "county": "Dane",
      "state": "WI"
    },
    "units": { "air_temperature_min": "°F", "air_temperature_max": "°F", "precipitation": "in" },
    "summary": {
      "days_requested": 7,
      "days_returned": 7,
      "days_forecast": 2,
      "missing": { "precipitation": 0 },
      "estimated": {},
      "stats": { "air_temperature_max": { "min": 61.2, "max": 78.4, "mean": 70.1 }, "precipitation": { "total": 0.42 } }
    },
    "sources": ["urma", "nbm"],
    "warnings": [],
    "attribution": "…",
    "api_version": "2.0",
    "generated_at": "2026-05-06T14:02:11Z",
    "compute_ms": 38
  },
  "data": {
    "date": ["2026-05-01", "2026-05-02", "…"],
    "kind": ["observed", "observed", "…", "forecast"],
    "air_temperature_min": [44.1, 47.9, "…"],
    "air_temperature_max": [61.2, 70.4, "…"],
    "precipitation": [0.0, 0.31, "…"]
  }
}
```

(Values are illustrative.)

- `meta.request` is the request **after** defaults and normalization: what was actually computed, not just what was sent.
- `meta.location` reports the cell actually read. A point snaps to the cell center, which can differ from the point asked for, so a user can see the snap.
- `meta.summary` holds what v1's `info` had (days requested and returned, min, max, total) per variable, plus the D45/D56 counts.
- `meta.warnings` is for non-fatal notes in plain language ("2 days of precipitation missing and counted as no rain", "forecast past day 7 is NBM's", "model status beta").
- Errors return 4xx with the same envelope and `errors` in place of `data`: `{"meta": {…}, "errors": [{"code": "out_of_range", "param": "start", "message": "…"}]}`. This replaces Ninja's default `{"detail": …}`.
- Timing also goes in a `Server-Timing` header, so latency checks against §3 don't need to parse the body.
- **Rounding:** each value to its stored precision (the catalog's scale) in the unit shown, rounded up to a whole decimal: 0.1 °C is 0.18 °F, so 1 decimal; 0.02 mm is 0.0008 in, so 4. The summary's statistics use the same digits (a mean one more).
- **Error codes** (`errors[].code`): `missing`, `conflict`, `invalid`, `out_of_range`, `out_of_order`, `too_many`, `unknown_variable`, `bad_unit`, `format_unavailable`, `not_found`, `internal_error`, and Pydantic's own type names for a value of the wrong type (`float_parsing`, `date_from_datetime_parsing`, `literal_error`). `param` names the query parameter at fault, or is `null`.
- **Caching:** every answer carries an ETag and `Cache-Control: public, no-cache`: clients and caches keep it but check before reusing it, and a request with `If-None-Match` gets a bodiless 304 while the answer stands. The ETag changes when the data the answer reads is rewritten (an ingest, a rebuild), when the service is updated, or when the request does (including a default such as today's date). API responses set no cookies.

**Name:** `meta`, not v1's `info`. `meta` is the common convention (JSON:API and most data APIs), and `info` would collide with discovery endpoints. v1's URLs keep working by redirecting to the old server until it's retired (Phase 8), so v2 doesn't need v1's names.

## Data layout

**Columnar by default** (`data` is an object of equal-length arrays, as above), with `orient=records` for an array of row objects:

|                             | columnar (default)                  | records                                       |
| --------------------------- | ----------------------------------- | --------------------------------------------- |
| size, 1 year daily × 5 vars | ~1×                                 | ~2.5× before gzip, ~1.3× after                |
| R                           | `as.data.frame(fromJSON(url)$data)` | `fromJSON(url)$data` (jsonlite simplifies it) |
| pandas                      | `pd.DataFrame(r["data"])`           | `pd.DataFrame(r["data"])`                     |
| JS / ECharts                | arrays go straight into series      | `.map()` per field                            |
| simple scripts              | index by position                   | `row.date`, `row.value`                       |

Both read into a data frame in one line in R and pandas. Table tools that want rows under a root key (wpDataTables in WordPress, Power Query) take `orient=records` with root `data`, or CSV. Columnar is smaller, and it is what charts want.

**Several points** come back long (tidy): one `point` column indexing `meta.locations[]`. One table holds any number of points, and CSV is the same shape.

**Flags are columns**, not nested objects: `kind` per row, and `<var>_estimated` (boolean) beside each cumulative variable that bridges gaps. They survive the conversion to CSV and data frames unchanged.

## Formats

`format=` (or the `Accept` header; the parameter wins):

| format           | for                                       | where                                    |
| ---------------- | ----------------------------------------- | ---------------------------------------- |
| `json` (default) | apps, scripts                             | everything                               |
| `csv`            | spreadsheets, R, agencies                 | points, tables, grids (one row per cell) |
| `netcdf`         | xarray, R (`terra`, `ncdf4`), researchers | grids, and point series on request       |
| `geotiff`        | ArcGIS, QGIS                              | grids (one band per day)                 |
| `png` / `webp`   | maps                                      | tiles                                    |
| `xml`            | not offered (below)                       | —                                        |

- **CSV** puts `meta` as `# key: value` comment lines above the header (as v1 did; `headers=false` drops them), one per top-level key, its value as compact JSON (`# units: {"air_temperature_max":"°F"}`). `read.csv(url, comment.char = "#")` and `pd.read_csv(url, comment="#")` skip them. A `Content-Disposition` filename describes the query.
- **NetCDF** keeps the native grid with its CRS (CF `grid_mapping`, Lambert conformal) and 2-D `lat`/`lon`, so `xr.open_dataset` puts it on a map correctly. Attributes carry `meta`. This is what "xarray format" means over HTTP. Zarr stays internal; a remote Zarr endpoint isn't worth exposing.
- **XML:** not offered unless a named consumer needs it. Nobody in the v1 logs is known to, it doubles the serializer and test surface, and every agency tool that reads XML also reads CSV or JSON. If one turns up, it's a serializer over the same envelope.
- Parquet is a cheap later addition for bulk downloads if anyone asks.

## Locations, times, units

- **Points:** `lat`, `lng` (decimal degrees; v1's names). `latitude`, `lon`, `long` and `longitude` are accepted as aliases (v1 took `long` and `longitude`, and DATCP sends `long`), and `meta.request` echoes the canonical name. Several points: `points=43.07,-89.40;44.52,-89.57` (up to 50; more via POST with the same body as JSON). Inside the box they read our grid. Outside it, or before the archive's window, they go through Open-Meteo's per-cell cache, and `meta.sources` says so.
- **Dates:** `date` (one day) or `start`/`end` (inclusive, ISO). Daily dates are the location's local calendar days (PLAN.md §5.4). Defaults: from January 1 to today.
- **Hours:** `start`/`end` as ISO datetimes. Times come back in UTC (`2026-05-01T05:00Z`), and `tz=local` adds a `local_time` column in the location's zone.
- **Forecast:** `forecast=true` (default) runs through the forecast, with `kind` marking it; `false` stops at the last observed day.
- **Units:** `units=us|metric`, plus per-variable overrides (`units=metric&precipitation=in`; the value is a unit symbol, its label, or `us`/`metric`, and a variable's name covers its daily statistics, so `precipitation` sets `precipitation_sum` too), **`us` by default**: that's v1's audience, and Wisconsin growers, DATCP and the site all think in °F and inches. `meta.units` always states the units in force, so nothing is ambiguous. Degree days stay in each model's own unit (D18).
- **Gaps:** `gaps=estimate|missing` on cumulative variables (D25).

## Endpoints

All under `/api/v2`. ✓ marks what exists today.

### Discovery

| endpoint                | returns                                                                                                                                                                                                                                                  |
| ----------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `GET /status` ✓         | service version; the archive's first hour, each source's newest hour, the last day rolled up and stale stores; the forecast run (cycle, last hour, in use or why not); the model count. Data facts only: jobs, the write lock and failures stay on `/up` |
| `GET /variables` ✓      | the catalog: name, long name, kind (hourly, daily, cumulative), unit (stored, and `us`/`metric` labels), precision, valid range; a daily variable's statistic and the hourly variables it comes from. Date ranges are `/status`'s                        |
| `GET /models` ✓         | every model: id, name, group, crops, topics, status, version, summary, region, season, citations (with DOIs)                                                                                                                                             |
| `GET /models/{id}` ✓    | one model's spec: required daily inputs and the hourly variables that derive them, outputs (name, unit), options (biofix, planting, maturity group: type, range, default), risk levels and criteria, changelog (see Models below)                        |
| `GET /layers`           | every mappable layer and its time axis, range, units and palette (PLAN.md Phase 5)                                                                                                                                                                       |
| `GET /locate?lat&lng` ✓ | `meta.location`'s fields (cell, in box, timezone, county, state) plus the cell's corners ([lat, lng], SW, SE, NE, NW, for the map highlight) and typical planting dates per crop (early, typical, late, D34)                                             |

### Weather at points

| endpoint                   | notes                                                                                                                                                                                                                                                                                                                                                                                           |
| -------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `GET /weather/hourly` ✓    | `lat, lng \| points, start, end, vars`                                                                                                                                                                                                                                                                                                                                                          |
| `GET /weather/daily` ✓     | daily variables (min, max, mean, sums, hour counts)                                                                                                                                                                                                                                                                                                                                             |
| `GET /weather/totals` ✓    | sums over a window per variable with missing and estimated days: precip, ET0, shortwave, hour counts. What v1's precip/ET/insolation endpoints mostly served                                                                                                                                                                                                                                    |
| `GET /degree-days` ✓       | one or more settings, `dd=sine_48_86,modified_38_75,average_43` (method, base, optional upper, as the catalog names them; `base, upper, method` for one), at one point or several (`points=`), `biofix`. One row per point and day: min and max temperature once, then each setting's daily value and running total as columns (`dd_sine_48_86`, `dd_sine_48_86_cum`), with estimated-day flags |
| `GET /degree-days/table` ✓ | totals only: one row per point and setting over the window, with estimated and missing days (v1's `dd_table`, generalized). What a report like DATCP's needs                                                                                                                                                                                                                                    |
| `GET /freeze` ✓            | freeze counts and dates (last spring and first fall at thresholds)                                                                                                                                                                                                                                                                                                                              |

Built 2026-11-03. Points inside the box (and the archive's years) read the archive and forecast; others read Open-Meteo through our per-cell cache, up to 10 a request. A default `end` runs through the forecast (16 days ahead, trimmed to the last day with data); `forecast=false` stops at the last observed day. Limits: 10 years of days or 2 years of hours a request, 100,000 rows.

**Thresholds** (degree-day `base` and `upper`, freeze `thresholds`) are in the request's units: °F with `units=us` (the default), °C with `units=metric`, echoed as `meta.request.threshold_units`. A threshold no stored air temperature can reach (outside −76 to 140 °F) is refused with a 422. An unusual one runs, with a warning in `meta.warnings`: a base outside 32–60 °F, an upper outside 70–95 °F, a freeze threshold outside 20–36 °F, and with `units=metric` a value that looks like °F (a base above 30 °C). Degree-day settings are `method_base[_upper]` (`sine`, `average`, `modified`; a decimal as `39.2` or `39p2`), named back as given (`dd_sine_39p2_84`).

**Degree-day gaps:** a day's missing min or max is interpolated across gaps up to 7 days, and the day is flagged `temperature_estimated`; a longer gap adds nothing to a running total and counts as a missing day (`gaps=missing` turns estimates off). Freezes use the measured minimum only.

### Models

| endpoint                                  | notes                                                                                                                                                                                                                                                                                                                                                                             |
| ----------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `GET /models/{id}/run`                    | `lat, lng, start, end`, plus the model's options as plain parameters (`biofix=2026-05-10&maturity_group=2.5`). Returns the three layers (D30) as columns: inputs, outputs, `risk` (0–4) and `risk_label`, with `kind`, susceptibility, and estimated/missing days per input. Options left out take their defaults (crop model biofix, typical planting), echoed in `meta.request` |
| `GET /models/{id}/run?maturity_group=all` | several option sets in one call (every maturity group): long form, with an `option_set` column indexing `meta.option_sets`                                                                                                                                                                                                                                                        |
| `GET /models/run`                         | `models=a,b` or `all`: several models at one point on our weather, long form with a `model` column (Veg Path's DSV and P-days)                                                                                                                                                                                                                                                    |
| `GET /risk`                               | `lat, lng, date, models=` (default: all in season): one row per model with risk level and label. The Crop Risk Tool's dashboard and the alerts' query                                                                                                                                                                                                                             |
| `POST /models/{id}/evaluate`              | the explorer: inputs in, outputs out, same code (PLAN.md Phase 3 A)                                                                                                                                                                                                                                                                                                               |
| `POST /models/{id}/run`                   | the model on **your** weather (below)                                                                                                                                                                                                                                                                                                                                             |
| `POST /models/run`                        | several models (or `"all"`) on your weather in one call: long form with a `model` column                                                                                                                                                                                                                                                                                          |

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
- **Checks:** the same QC ranges as ingest (`agdata.qc`). Out-of-range values become missing, with a warning saying how many and where. A model whose inputs can't be made from what was sent returns 422 naming what's missing, and which hourly variables would supply it.
- **`fill=grid`:** fill the station's gaps from our archive at its cell, with those days' kind `grid`. **`extend=forecast`:** run on past the station's last day with our forecast for the cell, so a station network gets the next week's risk too. The default for both is `none`: by default the answer depends only on what was sent.
- **Response:** the same envelope and columns as `GET /models/{id}/run`, with `kind` = `provided`, `estimated`, `grid` or `forecast` per day, and `meta.summary` counting each kind.
- **Nothing sent is stored.** Requests are computed and forgotten, and the docs say so. Limits: about two years of hourly data per request, and Caddy's rate limits.

**POST only** for running on your own weather. A season of daily min/max would fit in a URL, but hourly data won't, and two ways to send the same thing doubles what has to be documented and tested. The GET form of `run` already covers "our weather at a point".

**A complement, not a substitute:** pulling Wisconet's and other networks' stations onto our map and charts is a later enhancement (PLAN.md, "Enhancement: station networks"). The POST endpoint serves anyone without needing an agreement with us.

### Grids

`GET /grids/{layer}`, with `date`, or `start, end, stat` (sum, mean, min, max), and `bbox=` (lat/lng) or `region=wisconsin`; `format` json, csv, netcdf, geotiff, or `bin` (float32 for our frontend if tiles don't cover a need).

The native grid is Lambert conformal, not a lat/lng raster, so:

- NetCDF and GeoTIFF carry the true projection (exact; GIS reprojects).
- JSON and CSV are long form, one row per cell: `lat, lng, value` (the cell center), `j, i` on request. That's what "keyed by lat/lng" becomes without inventing a regular grid.
- `stride=n` takes every nth cell for coarse overviews.
- **Regular lat/lng grids:** v1's grid was regular 0.1° lat/lng, and some consumers (DATCP?) may depend on that shape. `grid=latlon&res=0.1` (any resolution from 0.025°, finer only repeats cells) with `method=nearest` (the cell under each point) or `mean` (the cells whose centers fall in each lat/lng box; the better choice when coarser than ~0.05°, since a 0.1° box holds ~15 cells). The lat/lng → cell index is cached per box and resolution, so it's cheap: measured over Wisconsin, building it takes ~2 ms at 0.1° (3,024 points) and 82 ms at 0.01° (292,491), and each day's values then take 0.1–1.2 ms.

Size limit: a request over ~2 million values (Wisconsin is 57,820 cells, so about 35 days) is refused with a message pointing to netcdf/geotiff or a smaller window. Netcdf's limit is higher.

### Tiles

- `GET /tiles/{layer}/{time}/{z}/{x}/{y}.png`: data tiles (values encoded in RGB, `agdata` tile encoding) for our MapLibre frontend, which colors them on the GPU with the layer's palette.
- **Rendered, colored tiles** for outside users (`?style=default`, XYZ, plus `/tiles/{layer}.json` TileJSON), so DATCP can add a layer in ArcGIS Online, QGIS or Leaflet with one URL. Rendering is the same palette applied server-side, and it's the easiest way for an agency to use the maps. A legend image goes with it (`/tiles/{layer}/legend.png`).
- Past times are immutable and cached by Caddy; today and the forecast get a short max-age tied to the ingest schedule.

### Climate

Built in Phase 6 with the climatology (D11, D22); the contract is set now so Phase 5's plumbing fits it. Normals are a reference period's typical values, by day of year. "Current against normal" compares this year's observed days, then the forecast, with them.

| endpoint                          | notes                                                                                                                                                                                                                                                                                                                                                                                  |
| --------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `GET /climate/normals`            | at points: daily normals by day of year (min, max, mean temperature, precip, and later gridMET's humidity, wind, solar and ET0), with `interval=day\|month\|year`. `period=1991-2020` (nClimGrid-daily and gridMET, the default) or `last5`, `last10` (our archive). Percentiles (`percentiles=10,50,90`) as columns beside the mean                                                   |
| `GET /climate/normals` with `dd=` | normal degree days for any setting (DATCP's eight included): each day's normal and the normal running total from `start` (default January 1), with the spread across years                                                                                                                                                                                                             |
| `GET /climate/compare`            | this year against last year and normal at points, for weather and degree days (`dd=`): observed and forecast running total, last year's total to the same date, the normal total, the departure, the percentile among the reference years, and for degree days "N days ahead/behind normal" (the date the normal total reached today's). DATCP's table could carry departures directly |
| `GET /climate/frost`              | last spring and first fall freeze at thresholds (32, 28, 24 °F; any via `thresholds=`) at probabilities (10, 50, 90%), and growing-season length; from the reference years                                                                                                                                                                                                             |
| `GET /climate/history`            | daily values at a point before our archive begins (2016): nClimGrid-daily from 1951 (temperature, precip) and gridMET from 1979 (more variables), flagged with their source. Degree days and models can run on them (`/degree-days?start=1985-01-01` reads them where the archive doesn't reach)                                                                                       |
| layers                            | normals, departures and percentiles as `/layers` (time axis day of year), so `/grids`, tiles and `/maps/{layer}.png` work for them: a "GDD departure from normal" map is a layer like any other                                                                                                                                                                                        |

Normals of anything with a threshold (degree days, freeze dates, hours above or below) are each year's value averaged across the years, never the value computed from averaged temperatures. A normal day of 45/65 °F gives different degree days from the average of thirty real days. That's why the climatology keeps the daily data of the reference years on the grid, not only day-of-year statistics, so any setting can be computed on request (Q34).

**Gridded and station normals:** NOAA's official 1991–2020 normals (and the Wisconsin State Climatology Office's tables built from them, which DATCP uses) are per station. Ours are gridded from nClimGrid, the same period and the same parent network, but a cell's value differs a little from a station's. The migration guide for DATCP compares the two at their 23 points. Station normals could be added beside the station layer (D59; Q35).

Projection (Phase 6): after the forecast, a degree-day or model run can continue to the end of the season on the normals (`projection=normal`), with a band from the reference years' spread (U2U's method). Those days come back with kind `projection`.

### Static maps

`GET /maps/{layer}.png?date=&region=&units=` (D60): a finished map image for embedding by URL, with outlines, title, date and legend. Without `date` it shows the latest day, so a link such as "Today's growing degree day map" stays current. Rendered with matplotlib on the native grid, cached for past dates, and pre-rendered for today by a job.

### Downloads

Yearly NetCDF per variable for bulk users, as static files beside the API (Phase 5 or later), listed by `/status`.

## Access, limits, stability

- **Anonymous reads** with Caddy rate limits at launch. Optional free API keys (`X-API-Key`) for higher limits, and so we know who to tell before a change, are added when someone needs more.
- **Stability:** `/api/v2` changes only by addition (new endpoints, parameters, columns, `meta` keys). Anything breaking is announced on the changelog page and in `meta.warnings` well ahead. Clients should ignore keys they don't know.
- **Types:** the frontend's TypeScript types are generated from the OpenAPI schema, as `bin/types` does for props (`@/types/api`), so CI fails when the frontend and API disagree.
- **Docs:** OpenAPI at `/api/v2/docs`, with an R, Python and curl example per endpoint, D53's attribution, and the changelog.

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

**DATCP** (confirmed 2026-11-02): their daily table has ten columns at 23 locations: the eight degree-day settings for this year, last year's modified 50/86, and the 1991–2020 normal modified 50/86 (from a State Climatology Office spreadsheet). v1 needs 184 requests and the spreadsheet; v2 needs one `/degree-days/table` for the eight settings (Phase 5), and once the climatology exists (Phase 6) one `/climate/compare`, which adds last year, the normal, the departure and days ahead or behind for every setting.

v1 took one location and one setting per request. Its biggest outside caller, DATCP's daily degree-day report (8 settings × 23 locations, 184 requests every morning, January 1 to yesterday; old server log, December 2024), becomes one request:

```
/api/v2/degree-days/table?points=43.2,-90.2;…&dd=average_43,average_50,average_52,modified_38_75,modified_40,modified_50_86,sine_39_84,sine_48_86&start=2026-01-01
```

or `/degree-days` with the same parameters for the daily series. `units=us` is the default, as in v1.

## Not decided here

How model maps are precomputed (D47, PLAN.md Phase 5), tile encoding details, and whether tiles move to a Starlette mount (§9) are implementation choices, made as the work lands.
