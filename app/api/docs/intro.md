The AgWeather API gives hourly and daily weather, growing degree days, and crop disease, insect and crop development models for the Upper Midwest. It is free to use and needs no account. AgWeather is a service of the University of Wisconsin–Madison.

The weather comes from the National Weather Service's analyses and forecasts on a 2.5 km (1.6 mi) grid, with a forecast up to 16 days ahead. Our records keep the most recent 11 years, from 2016 to the present at first; each January the oldest year is removed. Maps cover only those years. For a location, earlier dates and places outside the area we cover come from Open-Meteo. Every request is computed from the same data and code that the AgWeather website uses.

## Making a request

Every request is a simple web address (a GET request), so you can open it in a browser, bookmark it, or read it into R, Python or a spreadsheet. For example, this request returns this season's growing degree days at Madison, Wisconsin:

```
/api/v2/degree-days?lat=43.07&lng=-89.40&dd=modified_50_86
```

- **Locations** are latitude and longitude in decimal degrees (`lat`, `lng`), with west longitudes negative. The weather and degree-day endpoints also take up to 50 locations at once (`points`).
- **Dates** are written as YYYY-MM-DD. Inside the area we cover, each day runs from midnight to midnight Central Standard Time all year (06:00 to 06:00 UTC), the same days our maps use; outside it, a day follows the location's own clock. Add `day_basis=local` for a location's own days anywhere. Hours are given in UTC, and each hour is labeled by its end.
- **Units** are US customary (°F, inches, mph) unless you add `units=metric`. You can also set the unit of a single variable by its name, for example `precipitation=mm`.
- **Formats:** JSON by default, or CSV with `format=csv`. Maps are also available as NetCDF and GeoTIFF files, map tiles and finished images. For the whole archive, `/downloads` lists a NetCDF file for each daily variable and year.

## What a response contains

A JSON response has two parts. `meta` describes the request as it was computed, including any defaults that were filled in, the grid cell that was read, the units of every column, a summary, the data sources and any warnings. `data` holds the values as named columns of equal length, or as a list of rows with `orient=records`.

Each day or hour says where its values came from in a `kind` column: `observed`, `partial` (today: the hours observed so far, then the forecast), `forecast`, or `projection` (past the forecast, from earlier years' weather, where you ask for it). **Missing data is always `null` (an empty cell in CSV), never zero.** A running total such as degree days bridges a short gap with an estimate and marks those days in a column of its own, so you can see how much of a total was estimated. Precipitation is never estimated: a total counts only the days that have data and reports how many were missing.

If a request can't be answered, the response has a status code of 400 or higher and an `errors` list in place of `data`. Each error names the parameter at fault and says how to correct the request. A parameter the endpoint doesn't take is an error too (`unknown_parameter`), rather than being ignored, so a misspelled name can't change your results without your knowing.

## Models

Each model's description, citations, inputs, options and version history are available from `/models/{model_id}`. A model's output is guidance based on weather data, not a guarantee of what will happen in a field. Check the model's region and season, and combine its output with scouting and local knowledge.

## Limits and good use

- A request can cover up to ten years of daily data or two years of hourly data at a location.
- Requests are limited per IP address, by how much work they take: a quick request counts as 1 unit, and one that takes longer to compute counts for more. Each response's `RateLimit-Limit` and `RateLimit-Remaining` headers give your allowance per minute and how much of it is left. If you exceed the limit, the API returns status 429, and the `Retry-After` header says how many seconds to wait.
- Responses carry an ETag. If you send it back in an `If-None-Match` header, the API answers with a short "not modified" response until the data changes.
- Weather you send to the model endpoints is used to compute your answer and is not stored.
- The API changes only by addition: new endpoints, parameters and columns may appear, but existing ones keep their meaning. Your code should ignore fields it doesn't recognize. Changes are listed on the [API changes page](/api/changes).

We would like to hear how you use the API and what you would like it to do. Please tell us through the [feedback form](/api/feedback).

## Data sources and credit

When you publish results from this API, please credit "AgWeather, University of Wisconsin–Madison". The weather data come from NOAA's National Weather Service (URMA, RTMA, HRRR and the National Blend of Models), Open-Meteo (CC BY 4.0) and the European Centre for Medium-Range Weather Forecasts. Soil temperature and snow depth contain modified Copernicus Climate Change Service information (ERA5-Land). Normals before 2016 come from gridMET (Abatzoglou, 2013, University of California, Merced), adjusted to our records. The software is open source under the GNU Affero General Public License.
