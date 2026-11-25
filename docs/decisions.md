# Decisions and questions

Why AgWeather v2 is built the way it is: the recorded decisions (D1 onward) and the questions put to Ben (Q1 onward, open and settled), formerly PLAN.md §2 and §15 (moved 2026-11-23). Code, reports and plans cite them by ID (`D45`, `Q39`); keep the IDs stable. A new decision takes the next D number, as a `### D103. Title` heading with its date and text below; a decision that's replaced stays, struck through or marked, with a pointer to the one that replaces it.

## Decisions


### D1. Django + Inertia + Svelte 5

_2026-10-26._ All Python on the server; Node only at build time

### D2. Native 2.5 km NDFD grid

_2026-10-25._ Shared by URMA, RTMA and NBM; no regridding between obs and forecast

### D3. Rolling 11-year window

_2026-10-25._ 2016–2026 to start, dropping the oldest year each January. Open-Meteo covers earlier dates

### D4. Service box is configuration

_2026-10-25._ Upper Midwest (≈35–50° N, 100–75° W) now; CONUS later by backfill

### D5. Zarr for gridded data

_2026-10-26._ (one store per year), Postgres for app data. Postgres on RDS in production

### D6. Hourly precip from 2017-12-05

_2026-10-25._ (when URMA's hourly files begin; first set as 2018, corrected 2026-10-27); earlier dates keep URMA 6-hour totals

### D7. Solar radiation from HRRR

_2026-10-26._ Analysis shortwave, regridded; SSEC is a development check only

### D8. ET0 is hourly FAO-56 grass reference

_2026-10-26._ Summed to daily, matching Open-Meteo's method

### D9. Soil temperature modeled everywhere

_2026-10-26._ (HRRR in the box, Open-Meteo outside); no Wisconet dependency. **Superseded by D52**

### D10. Forecast: NBM in the box, Open-Meteo elsewhere

_2026-10-26._ (Professional plan, 5M calls/month)

### D11. 30-year normals from nClimGrid-daily and gridMET

_2026-10-25._ 5/10-year normals from the internal archive

### D12. No v1 shim

_2026-10-26._ V1 URLs redirect to the old production server through 2027

### D13. Models are open, cited, versioned

_2026-10-26._ (beta/stable/retired), with declared regions and seasons and generated about pages; beta hidden unless a user opts in

### D14. Accounts by magic link or code

_2026-10-26._ Digest, event alerts, or both; announce to current subscribers by BCC

### D15. Dedicated server

_2026-10-26._ (Ubuntu 26.04, x86_64) running Docker Compose; RDS and the EBS data volume in the same AZ

### D16. uv workspace + pnpm monorepo

_2026-10-27._ Python 3.13, Node 24

### D17. Procrastinate

_2026-10-27._ Job queue (Postgres-backed, periodic tasks) for ingest and app jobs (Q1)

### D18. SI units in storage

_2026-10-27._ (°C, mm, m/s, W/m², kPa), converted by one units module (`agdata.units`, with a mirror in `frontend/lib/units.ts`) at the API and display edge; degree days stay in each model's own unit (mostly °F-days), labeled in the catalog (Q2)

### D19. Public GitHub repo `uwent/agweather2`

_2026-10-27._ (Q3)

### D20. Named service-box presets

_2026-10-27._ (`wisconsin`, `upper_midwest`, `conus`) chosen by `SERVICE_BOX`; development starts with `wisconsin` and scales up by switching the preset and backfilling

### D21. Coarse stored precision

_2026-10-27._ 0.1 °C temperature and dew point, 0.1 m/s wind and gust, 1 % cloud and RH, 1° direction, 0.1 mm precip, 0.1 kPa pressure (Q6, docs/pilot.md)

### D22. Climatology moves to Phase 6

_2026-10-27._ With the climate comparisons it feeds (Q7)

### D23. RTMA hourly precip before 2017-12-05

_2026-10-27._ When URMA has only 6-hour totals; supersedes D6's 6-hour plan (Q8)

### D24. Local backfill: Wisconsin 2024–2025

_2026-10-27._ Changed to 2025-01-01 to now for the pilot (2026-10-28); the 11-year backfill runs on the server (Q9)

### D25. Gaps:

_2026-10-28._ Hourly and daily stores hold raw values only (no fill at ingest; days need 20 hours for min/max/mean and every hour for sums). Cumulative totals bridge gaps of up to 7 days: DD from linearly interpolated daily min/max, shortwave and ET0 from clear-sky radiation scaled by neighbouring hours' Rs/Rso. Precip is never estimated. Each cumulative variable keeps a running count of estimated (precip: missing) days, so the API and interface can bridge or blank a range (`gaps=estimate|missing`). Longer gaps leave ranges across them blank until a fallback source fills them

### D26. DD cubes by threshold, not by pair:

_2026-10-28._ Single-sine DD with a horizontal cutoff are linear, so DD(base, upper) = DD(base) − DD(upper), daily and cumulative. Twelve sine cubes (39.2, 41, 42.8, 45, 48.2, 50, 52, 55, 80.1, 86, 90, 92 °F; 48 became 48.2 with the Crop Risk Tool's alfalfa weevil, 2026-10-28) give the planned models' 13 pairs and any pair of those thresholds; corn gets a modified 50/86 cube (not decomposable). The legacy pairs no model uses (32, 38/75, 50/87.8, 52/86) are computed on demand. Daily DD aren't stored (they come from daily min/max)

### D27. Cumulative stores rebuild each year from Jan 1

_2026-10-28._ Whenever a day changes, so rounding never compounds; cumulative DD at 0.5 °F·d (any pair's range within ±1 °F·d)

### D28. Hourly precip at 0.01 mm

_2026-10-28._ (amends D21): at 0.1 mm, hours under 0.05 mm (12% of wet cell-hours in January 2025, mostly light snow) were stored as 0, leaving January 6.6% low over Wisconsin. Rounding up and down doesn't cancel when tiny amounts dominate, and the same happens to daily totals on trace days (stored at 0.1 mm, Madison's January summed to 2.0 mm against 2.14 hourly), so daily precip is 0.02 mm with an offset that spends int16 on 0–1,310 mm (above any US daily record). Running totals round once per value, without that bias, so they keep 0.2 mm. About 2 MB a month more (docs/pilot.md). Stores refuse to open at a scale other than the catalog's

### D29. Derived data is versioned

_2026-10-28._ Each derived catalog variable (features, indices, totals) records the version of the code that wrote it in the store; a changed version marks it stale, `manage.py rebuild --stale` recomputes it (run on deploy), the health check lists stale variables, and reads compute from hours rather than serve stale values. Risk scores are never stored

### D30. Models have three layers

_2026-10-28._ (inputs, outputs, risk 0–4 with words and criteria), all available to the API and charts, the Crop Risk Tool's view being the reference; hourly-native features from a standard hourly frame of any source; models run over a series whose days carry their source (observed, forecast, projection)

### D31. Topic and model documentation is Markdown in the repo

_2026-10-28._ Versioned with the models

### D32. Crop growth stages are models

_2026-10-28._ (`agmodels.crops`, one engine, declarative crops): every stage for a range of maturities, biofix at planting by default (emergence where a crop counts from it); no risk layer, shown on a crop growth page and under each of the crop's disease models. Corn by GDD scaled to the hybrid's rating; soybean photothermal (temperature and day length, from its maturity group); wheat next; no further crops for now

### D33. Disease risk is gated by crop stage:

_2026-10-28._ A disease model declares the stages it affects; outside them its risk shows grey as "not susceptible", and from the stage milestone before the window and up to the milestone after it in a muted color (stage estimates are imperfect). Stored outputs and the risk function don't change; the gating is a separate on-read layer

### D34. Default planting dates come from published typical dates

_2026-10-28._ Committed as static tables (county where published, else state); no live crop-progress or other ongoing sources, to keep external dependencies few. The user can always set their own date

### D35. A model's prose sits beside its code

_2026-10-29._ `agmodels/models/<name>.py` + `<name>.md`, and one file per insect, `agmodels/insects/<name>.py` (a typed `Insect(...)`) + `<name>.md`. Front matter holds only id (checked against the spec), status, sources and, for an insect, its one-line `summary` (the spec's summary; plain text is easier to edit there than in a Python call); everything structured comes from the spec. `content/` keeps topics and images, which several models can share. Supersedes D31's location, not its intent

### D36. Insect phenology as curves

_2026-10-29._ Each life stage of each generation is a PERT density in degree days from (start, peak, end), equal-area, so wider generations have lower peaks. Later generations repeat until the season ends, spreading by distributed-delay convolution: generation _n_ is the first convolved with *n*−1 generation times (variances add, so spread grows with √*n*; Manetsch 1976). Without published data, the generation time's spread is the first generation's. Risk is continuous: the sum over stages and generations of each stage's weight times its density, 1.0 being a weight-1 first-generation peak; words are ranges per insect, no 0–4 bins. **Action windows are periods, not a risk level:** an insect declares windows, each with a rule on its phenology or risk (e.g. a stage's fraction complete between 0.1 and 0.9, or risk above a value) and an intervention label ("Avoid planting during adult flight"), giving one start–end date range per generation. They work like a disease's susceptible period (D33): a separate layer drawn as bands on the chart, and a natural alert trigger. **The season ends once and stays ended:** after day 250 a freeze factor, max(0, 1 − f/4) for _f_ days ≤ −2 °C in the last 14, scales risk, held at its running minimum so a warm spell can't raise it again (freeze mortality doesn't come back); the day it reaches 0 the season is marked complete, and later days show no activity, no risk and no windows

### D37. Each model counts degree days by its source's method

_2026-10-29._ A model's thresholds are only valid with the method (single sine, simple average, modified average), base, cap and biofix they were derived with; AgWeather once switched every model to single sine (better in spring) without adjusting its numbers. `Insect.dd_method` and the degree-day functions carry the choice; a model that moves to another method re-derives its thresholds. Every insect is checked in D8 step 4. Insects every generation equally abundant (Ben: later generations' size depends on weather and the previous generation, beyond this app), and a stage can be timed from another (`DerivedStage`: lag and duration, larvae from flight)

### D38. NBM from the four long runs

_2026-10-29._ (01, 07, 13, 19z): hourly fields to f036–f048, then 3- and 6-hourly to f264, with 1-hour precip every hour; ~7 GB of reads a day (Q10)

### D39. Forecast daily min and max from the hourly values, post-processed

_2026-10-29, 2026-10-31._ (settled by the 2025 backtest, Q11): each day's warm hours reshaped to NBM's TMAX, and each night's (00–12Z) coldest hours lowered by the hours' warm bias at the min by lead (`agdata/data/nbm_night_min.json`); NBM's TMIN isn't used

### D40. Open-Meteo outside the box: `ncep_nbm_conus`, then `best_match`

_2026-10-29._ (shortwave past ~2 days and outside CONUS), soil from `ecmwf_ifs` (Q12)

### D41. No soil temperature forecast past HRRR's 48 hours

_2026-10-29._ It's a gap. Only potato volunteer reads soil. A synthetic soil forecast that scales the air temperature is a possible enhancement (Phase 9) (Q13). **Superseded for points by D44**. **Superseded by D52**

### D42. Open-Meteo responses cached in Postgres

_2026-10-29._ Compressed arrays per O1280 cell (Q14)

### D43. Forecast horizon is NBM's 11 days

_2026-10-29._ In the box and out; the Phase 6 projection takes over after (Q15)

### D44. Soil temperature forecast past HRRR's 48 hours comes from Open-Meteo's ECMWF IFS, for points

_2026-10-30._ (it forecasts soil for 11 days, which D41 assumed nobody did). Inside the box, a point's soil hours past HRRR's come from the cell's IFS series, sourced `openmeteo`; the grid keeps the gap rather than mixing sources. Supersedes D41 for points. **Superseded by D52**

### D45. Gaps in a model's inputs get the variable's named estimate, and the model reports how many

_2026-10-30._ Precipitation over a window sums the known days, counts missing days as no rain, and reports how many were missing (never a mean times the window's length). Temperature-like variables are interpolated over short gaps, as D25 does for running totals. Ported models are expected to carry latent bugs and suboptimal methods: parity tests are evidence about where v2 differs and why, not a rule that v2 must match (Ben)

### D46. Model versions are 0.x until launch

_2026-10-30._ (Ben): nothing is settled until the app launches, so every model starts at 0.1 and counts up by changelog entry; all go to 1.0 at launch. Renumbered 2026-10-30 (1.0 → 0.1; 1.1 and seedcorn maggot's 2.0 → 0.2). Status too (Ben, 2026-11-18): every model is `beta` until it is validated and the app launches; `stable` comes with 1.0 (`test_specs`).

### D47. Model maps are precomputed from ingredients

_2026-10-30._ (Ben): each model's display outputs, plus running totals or other ingredients its logic combines on request for a user's settings (as degree days subtract cumulative cubes, D26); only what can't be combined is computed on request and cached. During development only the last week plus the forecast is kept (`MODEL_MAP_DAYS`), to keep compute light. Seasonal products keep their daily running maps until final and the last season's for a year

### D48. HRRR shortwave is corrected against ground pyranometers

_2026-10-30._ (Ben): it reads 18% high against 80 Wisconet stations, more under cloud; a correction by clearness fitted on Wisconet brings a held-out year to 0.99. Design in Phase 2 H

### D49. The forecast is calibrated to the archive

(Ben, 2026-10-31): forecast and observed days must count humidity and heat the same way, since the disease models' thresholds were tuned to gridded data. RH is quantile-mapped onto the archive's by season, lead and solar hour at every lead (counts matter more than hour-by-hour error to threshold models), the max target lowered by a seasonal offset. Fitted on the Wisconsin 2025 backtest (`agdata.calibration`); refitted against other mesonets when the box grows beyond Wisconsin

### D50. Gridded RH ≥ 90% is counted at 88%

(Ben, 2026-10-31): the disease models' 90% comes from in-field stations, and the archive's RH ≥ 88% counts as many hours as 80 Wisconet stations' RH ≥ 90% and their leaf-wet hours. A shim in `agmodels.features` (`STATION_RH_90_AS_GRIDDED`): the RH ≥ 90 features keep their names and the models their published threshold; the catalog's long names say so (pages will show it from there, Phase 7). Not pecan scab (the Oklahoma Mesonet's threshold, unchecked). Ben had tried other thresholds on v1 and VDIFN and left 90%; in-field sensors may over-count where irrigated, which is real for that field. Soybean Cercospora and tar spot get it too, though the weather their fits used is unknown (Ben, 2026-10-31: perhaps Open-Meteo downloaded through the Crop Risk Tool and IBM's EIS; we can't be sure, so the correction applies to all six)

### D51. Open-Meteo is corrected for points

(Ben, 2026-10-31): shortwave by the hour's clearness against 80 Wisconet pyranometers, and RH quantile-mapped onto the archive's by season and solar hour (so D50's 88% holds for every source), both fitted on 2025–2026 and applied as hours are read from the cache (historical-forecast and forecast endpoints; not ERA5). The cache keeps Open-Meteo's values; corrected hours keep the raw ones and list the corrections applied, and every correction is in `agdata.corrections`, from which `docs/corrections.md` is generated. WISP applies the same tables and computes its own ET0 (`../wisp3/docs/plans/design.md` §8.5, D12)

### D52. Soil temperature and snow depth from ECMWF

(Ben, 2026-10-31): the archive's from ERA5-Land (Copernicus CDS, 0.1°, about 5 days behind), the hours since then bridged by IFS's short leads and marked provisional until ERA5-Land replaces them; the forecast's from IFS HRES (9 km) for its whole length, on the grid and at points. HRRR's soil is retired: under 13–20 cm of its own snow its 4 cm soil swings with the air (docs/validation/weather/soil.md). The steps between sources are left as they are, each hour keeping its source. Snow depth is stored. Supersedes D9's HRRR, D41 and D44

### D53. AGPL-3.0-or-later

(Ben, 2026-10-31), here and in WISP 3: anyone who distributes a modified version, or runs one for others over a network, must offer its source. Copyright the Board of Regents of the University of Wisconsin System (`LICENSE`, README, package metadata). `omfiles` is GPL-2.0-only, which doesn't combine with GPL-3 licences in a distributed work, so it stays an optional extra (`agdata[ifs]`) imported only by the IFS ingest; running it on our server distributes nothing. Data attribution, on the about and API docs pages: Open-Meteo (CC BY 4.0) and "Contains modified Copernicus Climate Change Service information [year]" for ERA5-Land

### D54. The Phase 2 tolerances are agreed, and the old API is a reference, not the truth

(Ben, 2026-10-31): comparing v2 with the old API explains where and why they differ; it never shows v2 is wrong. Accuracy is judged against measurements (Wisconet, ACIS) and the corrections fitted to them. A tolerance against the old API that fails is a difference to explain and record, not a defect by default

### D55. IFS's soil is shifted to meet ERA5-Land's at the seam

(Ben, 2026-10-31, Q23): each cell by ERA5-Land − IFS in ERA5-Land's last hour, times a weight by lead fitted on 80 Wisconet stations' cells (least squares, 2025; held out on 2026 it beats no shift and the whole shift at every lead to 24 days), held at its last value (a lasting share: 0.27 at 4 cm, 0.37 at 10, 0.54 at 30). `agdata.soil_seam`, table `ifs_soil_seam.json`, `ops.ifs` (the same run is read again when ERA5-Land moves the seam); the offsets are kept in `ifs/latest.zarr`; `ifs-soil-seam` in `agdata.corrections`. Not points outside the box (all IFS, no seam). Snow depth isn't shifted

### D56. A model with missing weather reports as it is, and the interface says so

(Ben, 2026-11-01, Q24): running totals add nothing for a missing day, so a run over a gap reads its lowest level rather than no value; the API and charts show `ModelRun.missing` (and `estimated`) beside the output ("includes N missing days"). Gaps should be rare: the archive's sources are complete, and weather is fetched by jobs before a page asks (unlike the Crop Risk Tool, which shows outputs on incomplete weather while fresh weather loads)

### D57. API v2's contract

(`docs/api.md`; Ben, 2026-11-02, Q25–Q31 as recommended): every JSON response is `{meta, data}`. `meta` holds the request as computed (defaults filled), the cell read, units, a summary with D45/D56 counts, sources, warnings and compute time; errors return `{meta, errors}`. `data` is columnar by default (`orient=records` for rows), and several points come back as one long table. CSV puts `meta` in `#` lines; NetCDF and GeoTIFF serve grids on the native projection. No XML unless a consumer asks. `units=us` by default, `metric` on request. Regular lat/lng grids at any resolution from 0.025° (`method=nearest|mean`), for v1's grid consumers. Rendered XYZ tiles with TileJSON and a legend for outside GIS users, beside our data tiles. Anonymous at launch with Caddy rate limits; keys when needed. The model list is the code registry (no table), served by `GET /models` to the frontend and everyone else

### D58. Models run on a client's own weather

(Ben, 2026-11-02, Q32–Q33): `POST /models/{id}/run` and `POST /models/run` (several or all) take daily or hourly observations, as JSON or CSV, with a location. Hourly data goes through the archive's rollup, and the same QC applies. Optional `fill=grid` (gaps from our archive) and `extend=forecast` (our forecast after the last day), off by default, each day flagged. Nothing sent is stored. POST only. `GET /models/{id}` lists each model's required daily inputs and the hourly variables that derive them

### D59. Station networks wait for an enhancement after launch

(Ben, 2026-11-02): Wisconet (once its v2 API settles; it whitelists our production IP rather than issuing keys), other mesonets with public APIs, and airport stations, as a station layer, possibly with a Postgres cache of station hours if demand needs it

### D60. Static map images return, rendered in Python

(Ben, 2026-11-02): v1's gnuplot/ImageMagick PNGs stay dropped, but outside pages embed a map image by URL (the UW Insect Diagnostic Lab links "Today's Growing Degree Day Map" to v1's `/api/degree_days/map.png`). `GET /api/v2/maps/{layer}.png` renders any layer with matplotlib: `imshow` on the native grid's projected extent (it's regular in Lambert x/y, so no regridding), state and county outlines from the Census cartographic boundaries projected with pyproj, the layer catalog's palette, a title, date and legend. No cartopy or GDAL. Today's maps are rendered by a job after the rollup; past dates are cached

### D61. The climatology keeps the reference years' daily data

(Ben, 2026-11-02, Q34): nClimGrid-daily 1991–2020 regridded to the window (and gridMET's variables), so normals of anything with a threshold (degree days, freeze dates, hour counts) are each year's value averaged across years, for any setting, ~~and `/climate/history` serves the years before the archive~~ (superseded by D87); the fixed pairs are precomputed. Station normals (NOAA 1991–2020) wait for the station layer (D59, Q35); DATCP's current normals are the mean cumulative modified 50/86 GDD at their 23 points, which `/climate/normals?dd=modified_50_86` reproduces from the grid

### D62. v2 takes over `agweather.cals.wisc.edu`; v1 moves to `legacy.agweather.cals.wisc.edu` for a year

(Ben, 2026-11-02, Q5; as WISP does). Caddy redirects every `/api/…` path outside `/api/v2` to the legacy host with its path and query (308), so v1 callers that follow redirects (python-requests, httr2, RestSharp, WordPress, browsers) keep working on launch day; bare `/api` goes to v2's docs. Callers are still asked to move to v2 this winter (TODO.md's list, Phase 5's migration guides), since the legacy host goes away after a year

### D63. Projection past the forecast runs each model once per past year of the archive

(Ben, 2026-11-02): after the forecast's last day, each earlier year's days from that date are spliced on, the model runs once per year, and each output shows its median as the line, the P10–P90 range as a band, and "reached by date" counts ("in 7 of 9 years"). The archive's own years, not nClimGrid or a mean day: every input exists (hourly features, soil), it's the observed days' source, and users remember recent years. Mean daily rain is rejected (no year has it; it breaks rain-day and wet-hour counts). Resilient to a short archive (a dev server's 2 years): a year counts only for the days it covers, the count per day is reported, one year gives a line without a band, none gives no projection and a warning. Within the forecast, Open-Meteo's GFS ensemble for points later (as WISP 3). Replaces Phase 3's U2U-style normal accumulation. **Refined 2026-11-03 (Ben):** opt-in (`projection=true`; the interface gets an "extended forecast" toggle), so most requests don't pay for it; points outside the box get none for now (a later option: the previous year alone); besides the P10/P50/P90 summary, `projection=years` returns each past year's path verbatim (about 10 years is few enough to draw each one); weighting years by their similarity to this one was tested and dropped (Q36, D67). Built now, with a store for reading past years at a point (shared with Phase 6's climatology)

### D64. Models at points: one answer per model, planting only when asked

(Ben, 2026-11-03): `GET`/`POST /models/run` return `data` keyed by model id, each with its own `meta` and `data` (the shape of `/models/{id}/run`), since models' columns and units differ too much for one long table; `format=csv` with several models is a 422. Long form with `option_set` only for one model's `=all` (same columns). `planting_date=YYYY-MM-DD|early|mid|late|all`: omitted, no crop stage gating and no susceptibility column (risk is never masked, D33); early/mid/late from `agdata.planting`(mid = its typical),`all`= three option sets; echoed with its source. The crop model's options are optional parameters beside it. Risk columns`risk_level`, `risk_label`, and `risk_value` for continuous risk (insects, D36). POSTed RH without dew point gets dew point by inverting Magnus, with a warning. The model-run shapes stay provisional until Phase 7's frontend uses them (the contract is additive-only from launch)

### D65. Grids: layers from the catalog, the points' rules over every cell, files without GDAL

(Ben, 2026-11-04, Phase 5 E): `/layers` lists every daily and hourly variable, the running totals and `degree_days` (any `dd=` setting) with a time axis (`day`, `hour`; `day_of_year` reserved for normals), range and palette id. `/grids/{layer}` takes `date`/`time` or `start`/`end` (up to 366 days or 31 days of hours), `stat` (sum only where values add), `bbox`, `region` (a state or county FIPS, masks from `agdata.places`' county grid: no shapefiles), `stride`, `grid=latlon&res=&method=` (D57). A stat follows the points' gap rules (sums bridge 7 days except precipitation; levels use known days) and returns each cell's `estimated_days` and `missing_days`. Degree days for any setting come from daily min and max, as at points; a setting kept as a cube is read from it for `stat=sum` (the same to its 0.5 °F·d). JSON/CSV long form with the value under the layer's id (so unit overrides work), up to 2 million values; NetCDF (h5netcdf + h5py, CF Lambert) and GeoTIFF (tifffile with hand-written Lambert GeoKeys, checked against GDAL) up to 22 million. A stale daily variable is computed from the hours for up to 7 days, else 503 until the rebuild. `format=bin` waits for a need. Additive indices' running totals move to F/G: `stat=sum` reads a season in ~0.5 s

### D66. Model maps show each place's own settings; a user's settings apply at points

(Ben, 2026-11-04, Phase 5 F): a planting date or biofix set on a map is only valid where the user is (VDIFN's lesson), so maps use location-adjusted defaults: planting from `agdata.planting`'s county tiers (early/mid/late), soybean maturity group and corn hybrid maturity by location, each model's spec biofix otherwise. A user's own planting date, biofix or maturity group applies to clicked and saved points (`/models/{id}/run`), not maps. Options that describe a scenario rather than a place (irrigation, row spacing, resistance, cotton's Pythium and stand) stay selectable on maps. Every model is split into location-free ingredients (daily terms, running totals, windowed values) stored on the grid and a per-cell finish computed on request, so option sets cost nothing to store; soybean stages (a day-by-day state machine) are stored per planting tier. `MODEL_MAP_DAYS` dropped: ingredients cover whole years. Potato volunteer's map waits for Phase 4 H's seasonal product

### D67. Every projected year counts the same

(Ben, 2026-11-05, Q36): D63's band stays the archive's last ~10 years at equal weight, with no similarity, recency or trend weighting and no longer record. A held-out study on ERA5 (6 Wisconsin points, 1980–2025; seasons 2000–2025 projected from Jun 1, Jul 1 and Aug 1; CRPS and P10–P90 coverage on corn GDD, rain, a 2,500 GDD date, late blight DSV and tar spot risk days) found no clear difference for similarity weighting (season-so-far GDD, rain, last 30 days' temperature), weighting recent years, a warming-trend shift (~0.15 °C/decade) or 30–45 years, in a paired bootstrap over target years; one run on 30-year mean weather (U2U-style) was clearly worse (+39% to +256% CRPS: averaged days never trigger a disease). 10 equal years cover 78–80% (80% is calibrated). Scripts in `tmp/projection-study/`

### D68. Seasonal products are computed on request from the ingredients

(Ben, 2026-11-05, Phase 4 H): a seasonal model (potato volunteer: November 1 to March 31, shown from January 1) declares its window on the spec; its map for a season or any day in it is a difference of the ingredients' running totals (F2), so there's no seasonal store or job and every season the ingredients cover is available. A season is final once the permanent weather data (ERA5-Land's soil for potato volunteer) covers its last day. The partial season is available on request; points and maps project the season's end from the past ~10 winters (D63, D67)

### D69. API rate limits live in the app; downloads include the current year

(Ben, 2026-11-05, Q37 closed). A middleware on `/api/` counts each IP's cost per minute in a Postgres table, where a request's cost reflects its work (a point or cached tile 1, a computed map or grid file more, a projection run more still), with a burst allowance for map clients and room for optional API keys later. Stock Caddy and the image stay as they are. Yearly NetCDF downloads cover finished years and a year-to-date file for the current year, rebuilt weekly.

### D70. Corn and potato stages are stored per planting tier too

(Ben, 2026-11-05, Phase 5 H4: "balance performance against perfection"). Every map of a disease gated by their stages (tar spot, gray leaf spot, the blights' emergence) computed them over every cell, 0.2–0.3 s a map, which put risk maps over §3's 300 ms. `agdata.croptiers` keeps them as it does soybean's and spring wheat's (default options: corn black layer 2500 GDD), and `modelgrid` reads them for the crop's own map, gating and stage-anchored biofixes. Without a tier (`planting=none`) corn and potato are still finished from their ingredients with the spec's dates. On a crop's own tier map, cells without a typical planting date now have no stages (as soybean's), where they took the spec's dates.

### D71. Yearly downloads hold one gridded variable, packed int16; the grid goes in one `daily/grid.nc`

(Ben, 2026-11-05). Ben's terra (Windows, 1.9.50) opened a download by absolute path (`D:/…`) without its CRS or its scale (temperatures ×10), and by relative path correctly: the 2-D `lat`/`lon` beside the data made GDAL open each file as subdatasets, and the drive's colon breaks a subdataset name, so GDAL fell back to the HDF5 driver, which ignores CF attributes. A copy without `lat`/`lon` opened correctly both ways. So each yearly file holds only its variable (with `x`, `y` and the `grid_mapping`), and `grid.nc` holds every cell's latitude, longitude and time zone. Packed int16 with `scale_factor`/`add_offset` stays (unpacking is commonplace; 20–35% smaller than float32). `/grids`' NetCDF dropped them too (Ben, for consistency): one raster in GDAL, except a `stat=sum` file, whose counts beside the total still make subdatasets.

### D72. The API refuses query parameters it doesn't take, and maps say what they show

(Ben, 2026-11-06). Ninja drops undeclared parameters, so `start_date` or a misspelled `biofix` changed nothing and the answer looked right: each is now a 422 `unknown_parameter` suggesting the nearest name (`api.strict`, checked before the endpoint runs; the point aliases, unit overrides, a model's options and `_` pass). `biofix` takes a date or a month and day, the latest on or before the request's last day (`api.params.resolve_biofix`), on points, model runs and degree-day maps, where it implies `stat=sum`; `stat` without `start` runs from January 1. Map titles go broad to specific (`Air temperature, daily maximum`, `Precipitation, cumulative total`, `[model]: [result]`), dates with three-letter months, hours in Central time with UTC, and a caption with the data sources and the days or hours combined (`api.maptitles`, after v1's `image_title`).

### D73. Palettes are defined apart from their uses, named by their colors low to high, and a request can set the colors' range

(Ben, 2026-11-06). `agdata.palettes.PALETTES` (each with its source and whether it's color-blind safe) and `USES` (what each kind of map uses: palette, default domains, bounded or centered), so a palette can be reused, changed, or offered to a reader by the frontend (v1's rainbow and VDIFN's green-to-red are listed, assigned to nothing). Names run low to high (`BuYlRd` is ColorBrewer's RdYlBu reversed). Sequential palettes a use assigns keep neighbouring colors at least 7.5 ΔE (CIEDE2000) apart with the largest step at most 2.5× the smallest, which retired YlOrRd; snow's PuBu and cloud's Greys are named exceptions. Degree days BuYlRd, insect activity viridis, radiation inferno, wind RdPu, hours Greens, crop stage viridis, chance magma. `scale=default|auto|low,high` (request units, an end may be blank) after v1's `scale`. Whether a domain from the data is symmetric around zero is now the use's (`centered`), not the palette's: degree days on a diverging palette start at zero.

### D75. Counts name their time axis and bounds, inclusive; water balance totals fill each input its own way

(Ben, 2026-11-06, Phase 6 C). A count is `days_above_X`, `days_below_X` or `days_between_X_Y` on a daily variable and `hours_…` on an hourly one, in the request's units (a decimal as `93.2` or `93p2`, as degree-day settings), both bounds inclusive (≥, ≤, as `/freeze`): with continuous values the exact threshold almost never matters. The time axis is part of the name so the request reads like its column and a mismatch is caught: `hours_above_86` on a daily layer, or `days_` on an hourly one, is a 422 saying which the layer takes. Maps take `count=days_above_86` (implying `stat=count`); points take `count=air_temperature_max:days_above_86` or `count=air_temperature:hours_above_86`, repeatable, so FACTS's eight counts are one request, each named back as a column (`air_temperature_max_days_above_86`, `air_temperature_hours_above_86`). Missing days or hours are counted per cell or point, never assumed (D45). Water balance (precipitation − ET0) shows as missing on a day missing either input, but its totals and running total fill each input its own way, as models' inputs are (Ben, 2026-11-07): a day without rain data counts as no rain and ET0 is bridged as in its own total, both counted as estimated days; a day whose ET0 can't be bridged adds nothing and is counted missing.

### D76. Chill: the Dynamic model by default, Utah and chill hours on request

(Ben, 2026-11-06: recorded, built later). `method=dynamic` (Fishman, Erez and Couvillon 1987; chill portions), `utah` (Richardson, Seeley and Walker 1974; chill units) or `hours` (0–7.2 °C, 32–45 °F; any bounds at points). Utah units and chill hours are daily features (sums of hours). The Dynamic model carries state from hour to hour across days, so a day's portions depend on the season before it: on the grid it's a season store (portions to date and the end-of-day state, from October 1), rebuilt forward from a changed day as the running totals are; at points it's run on the hours from `start`.

### D77. Livestock heat stress: THI (NRC 1971) by default, the Cattle Comfort Index (Mader et al. 2010) as the second index

(Ben, 2026-11-06: the most widely used formula, with options; recorded, built later). THI from temperature and RH, CCI from temperature, RH, wind and shortwave. Stored daily: THI max, mean and min (night relief), hours with THI ≥ 68 and ≥ 72 (dairy), CCI max; hourly THI and CCI are computed when read, so other thresholds count at points from the hours. Thresholds checked against their papers before the features are stored, since a change means a rebuild.

### D78. First and last days within bounds, a statistic like counts; frost, hard freeze and killing freeze by name

(Ben, 2026-11-07, Phase 6 C step 4). `first=`, `last=` and `since=` take counts' bounds (`above_50`, `below_32`, `between_50_86`) or `frost` (≤ 32 °F), `hard_freeze` (≤ 28 °F) and `killing_freeze` (≤ 24 °F), on any daily weather layer and at points (`/weather/totals?first=air_temperature_min:frost`), so the freeze maps are one case of a general tool (soil's first day above 50 °F is another). The window is `start`..`end`; without `start` a `below` event looks back to the previous July 1 and any other to January 1, so one rule gives this fall's first frost, last fall's in spring, and this spring's last; `start` sets any other. Measured days only. A cell is found, none ("None", not "None yet": a past window is complete) or no data, the two empty states in light and darker gray, judged on rendered maps. Dates travel as days since 1970-01-01 (ISO in JSON and CSV).

### D79. ERA5-Land is kept on its own grid; the 2.5 km soil and snow are derived from it

(Ben, 2026-11-07). The ingest regridded ERA5-Land and dropped every cell under half land, so the coast came out in 0.1° steps, missing values spread inland through the bilinear weights, and Door County's tip, Washington Island and the Apostle Islands had no soil data. A check over Door County (July and January 2025) showed ERA5-Land's soil over open water is the lake's temperature (three layers equal, +2.5 °C in mid-January against −5.6 °C on land) and partly-water cells are a blend by land fraction, so water cells can't be used as soil. Now: every ERA5-Land value is stored as received on its 0.1° grid (water included, with the land fraction), and the hourly store's soil and snow are a derived product, rebuilt from it without a download whenever the method changes (D48's pattern): bilinear over land cells only (fraction ≥ 0.5), weights renormalized as the IFS path does; a land cell of ours with no land neighbour takes the nearest ERA5-Land land cell within 40 km (the coast, islands); water on our grid, from a 2.5 km land mask, is missing. The IFS hours take the same coast. ERA5-Land for 2016–2026 is downloaded again into the new store.

### D80. ERA5-Land and IFS reach the 2.5 km grid by a cubic B-spline, not bilinear

(Ben, 2026-11-09). Soil maps showed the 0.1° grid: bilinear's slope jumps at every source cell line, so a year's lowest daily mean drew axis-aligned creases, plus shapes and squares. Each cell now takes the 4 × 4 source points around it (IFS: four points on each of four rings) weighted by the cubic B-spline (`coast.bspline`), with D79's coast rule unchanged (land points only, renormalized; the nearest land within 40 km; our water missing). Its weights are all positive, so a value stays within its land neighbours' and dropping water ones can't push it past them; Catmull-Rom (interpolating bicubic) masked to land reached −136 °C, and ESMF's patch and second-order conservative methods overshoot as well and need ESMF. The B-spline is an approximation: a lone 0.1° extreme is softened toward its neighbours (a warm patch's 4.1 °C to 3.0 °C, January–February 2026), which suits values that are each an area's mean; a field linear in the source's indices comes through exactly. It removes the grid's lines, not ERA5-Land's own cell-scale differences (snow, land cover, soil): fine detail from covariates (URMA air temperature in the snow-free season, SNODAS snow in winter) would need checking against Wisconet first, and is not planned. Measured on January 2026 over Wisconsin: the lowest hourly 4 cm value changed by 0.05 °C at the median cell, 1.0 °C at the 95th percentile and 6.6 °C at most (the isolated cells); no cell gained or lost a value; the derive takes about 1.5× as long at the same memory.

### D81. Rolling windows on every daily series, at points and on maps

(Ben, 2026-11-10; Phase 6 D0). From the alfalfa tool's 7-, 14- and 28-day smoothing, which shows daily weather against its own recent average and against climate. `roll=N[,N…]` (days, 2–365) adds a column per window beside the raw one (`<column>_<N>d`); `roll_stat` is `sum`, `mean`, `min` or `max`, by default `sum` for values that add up (`computed.adds_up`: precipitation, ET0, water balance, hour counts; and degree days) and `mean` for the rest (`sum` refused on the rest: a sum of temperatures means nothing and converts wrongly); `roll_align` is `trailing` (the default: the only one that reaches today without later days, and that doesn't change as days arrive) or `centered` (an even window has its extra day before, as pandas' `rolling(center=True)`; Ben, 2026-11-10: we follow Python's convention, not zoo's). A request reads the days its windows reach before `start` and after `end`, so its first row has a whole window. A centered window reads the forecast's days where the request includes the forecast, so it reaches today and partly past it; `meta.summary.roll` gives the first date whose window holds forecast days. Two separate rules: `roll_partial` governs the series' ends (days that don't exist: before the first day with data, past the forecast's last), coverage governs gaps inside it (days that exist without data). With `roll_partial=false` (the default) a window past the ends has no value; `roll_partial=true` clips it to the days there are (zoo's `partial = TRUE`), and the clipped dates are listed. A window needs `roll_coverage` percent of its days (default 75; of the clipped window with `roll_partial`), or it has no value; `roll_coverage=0` takes any one value, so `roll_partial=true&roll_coverage=0` is zoo's `rollapply(…, na.rm = TRUE, partial = TRUE)`. Sums follow D45 (missing rain counts as none; ET0's short gaps are bridged and counted as estimated). Maps (`/grids`, tiles, `/maps`, `/summaries`): `date` with `roll` is the range ending on (or centered on) the date, read with `stat` (same default) or `count` as any range is, computed on request (no stored rolled variables unless the launch-box review says so). Normals use the same function centered on each day of year and wrapping from Dec 31 to Jan 1 (D82). Not carried over from the alfalfa tool: partial windows by default (half-width windows at the ends of the data, unmarked), no minimum coverage, the map's `date ± N/2` (N + 1 days), and climate smoothing that doesn't wrap the year

### D82. The climatology is our own analysis of the trailing 30 complete years, with 5 and 10 from the archive

(Ben, 2026-11-10; Phase 6 D). Published normals (NOAA's 1991–2020 station normals, PRISM's gridded daily normals) are fixed to 1991–2020 and are day-of-year averages, which can't give D61's per-year thresholded normals, any percentile or frost odds; they serve only as a check (DATCP's 23 points). Periods `last30` (the default), `last10`, `last5`: complete years before the current one (in 2026: 1996–2025, 2016–2025, 2021–2025), all rolled forward each January. 30 years come from an external gridded source (only the years the period needs: no record back to 1951; ~~so `/climate/history` reaches the period's first year~~, superseded by D87: gridMET's years build normals only); the archive's own years serve 5 and 10, for every archive variable. The source is gridMET (Ben, 2026-11-10: one source for every variable, which he has used), its files kept as received in `data/gridmet/` beside the other sources and the 2.5 km years derived from them; nClimGrid-daily was weighed (station-based, but only temperature and precipitation, and its days end at observers' reading times) and isn't used. Every statistic for a day of year pools each year's days within a 15-day window centered on it (±7 days, wrapping the year): 450 values from 30 years, 75 from 5, so percentiles and frost odds are steady (the ETCCDI percentile thresholds' method), and a mean pooled this way equals the daily means smoothed by D81's window. `window=` changes it. Supersedes D11's 1991–2020 default and D61's 1991–2020 reference years (D61's rule of keeping the reference years' daily data stands)

### D83. A point can be an area: the cells within a radius, averaged before anything is computed

(Ben, 2026-11-10). Madison's isthmus cell had a frost-free season 35 days longer than a farm cell 8 miles northwest (2016–2025), lake and city effects that are real at the shore but not for the farms around. `radius` (up to 10 miles or 16 km, well under a county: Wisconsin's average is ~750 sq mi, ~27 miles across) and `weighting` (`equal`, or `center`: a Gaussian with σ = radius / 2) on every point endpoint; each hour's weather is the weighted mean of the cells with a value, and days, degree days, freezes and models come from it (the area's weather, not a typical spot's: an averaged minimum freezes less often than its coldest cells, which the docs say). No water mask (Ben): air and wind keep lake cells, since a lake's air moves inland (Door County's cherries); soil and snow are already missing over the Great Lakes by D79's coast rule, so their averages are over land. The point's own cell is the default

### D84. gridMET's 30 years are put on the archive's basis, and the archive's own years stand in for gridMET's

(Ben, 2026-11-11; Q37, Phase 6 D3). D2 measured gridMET against the archive over 2016–2025 (`docs/validation/weather/climate.md`). Unadjusted, a departure map would show the two sources' difference as weather. Each gridMET year is adjusted when the store is derived, by cell and day of year, fitted on the overlap over a 31-day pooled window and smoothed across ~5 × 5 cells: an added difference for the maximum and minimum temperature and RH (clamped to 0–100, the minimum no higher than the maximum), a ratio of totals for precipitation, shortwave, wind and ET0 (capped at 0.5–2). Shortwave's adjustment moves gridMET toward measurement: the archive reads 1.00 of 80 Wisconet pyranometers (D48), gridMET ~1.16 by implication. Wind and ET0 were added after checking the archive's wind against anemometers (Ben asked whether our own data had earned the right to set the basis; 2026-11-11, `docs/validation/weather/wind.md`): the archive reads 0.97 of 70 airport stations at 10 m (r 0.92, every month 0.96–0.98), gridMET 1.51; against Wisconet's 3 m masts brought to 10 m, 1.21 and 1.82. ET0 follows from its inputs (gridMET's wind ~1.5× and shortwave ~1.16× the instruments). The fit is stored and versioned beside the store and listed in `agdata.corrections`, so it can be refitted without a download. `last30` takes the archive's own days for the years it has (2016 on) and adjusted gridMET before, so it contains `last10` exactly; the two sources then match in mean, not in day-to-day spread. gridMET's day (12Z–12Z, labelled by its start) isn't shifted.

### D85. Normal maps are stored per period; custom settings' normals are at points only

(Ben, 2026-11-11; Phase 6 D4). Each period (`last30`, `last10`, `last5`) keeps 366 day-of-year maps per statistic, chunked a day per chunk, so a normal or departure map costs one more chunk read: the daily variables' pooled means (and P10/P90 of the maximum and minimum), the mean running total from January 1 of every degree-day cube the archive keeps (any single-sine pair of the 14 thresholds is the difference of two, and any start date a subtraction, since means are linear), precipitation's and ET0's, deciles of the running totals of modified GDD 50/86, sine 41/86 and precipitation (`last30`, `last10`: a percentile map interpolates among them), the freeze chances at 32, 28 and 24 °F, and the freeze-date percentiles. A custom setting off the stored thresholds, or percentiles of another setting, is served at points (D1); over the box from 30 years it would take ~10 s a map (D3's measurement).

### D86. Climate on maps is a parameter of the existing layers; points compute from the period's years

(Ben, 2026-11-11; Phase 6 E). `climate=normal`, `departure` or `percentile` with `period=` on `/grids`, tiles and `/maps`, not a second copy of each layer: a departure is the map as asked less the stored normal (D85). It applies where the normal is linear in the stored statistics: one day, a range with `stat=mean` (or `sum` for values that add up), running totals, degree days whose setting the stored cubes make, and `roll=` with a mean or sum; `stat=min`/`max`, counts, `window=` and settings off the cubes are refused, pointing to the points. Percentile maps only where deciles are stored (modified 50/86, sine 41/86, precipitation; not `last5`). Freeze chances, freeze dates, the season's length and elevation are layers off the calendar (time axis `day_of_year` or `none`). Points (`/climate/*`) read the period's years for the cell or area and compute with `agdata.climatology`, so any percentile, setting, `window=` and `roll=` work there, and match the maps where both apply. ~~Inside the service box, point reads before the archive (1996–2015) take adjusted gridMET (D84), not Open-Meteo, so comparison years match the normals~~ (superseded by D87)

### D87. gridMET builds the normals and nothing else; maps cover the archive's 11 years, points any date

(Ben, 2026-11-11; supersedes D86's last sentence, drops E5 and `/climate/history`). The service is 10 years of real weather (and a year's buffer) backed by a 30-year normal (D3, D82): the archive keeps the most recent 11 years and drops the oldest each January (2016 on January 1, 2028), which keeps its size steady. gridMET's years only build the 30-year normals and their statistics (D84, D85); no endpoint serves a gridMET year as daily weather. Maps (`/grids`, tiles, `/maps`, `/summaries`, downloads) cover only the archive's years: a first asked day before its first year is refused (422 `out_of_range`, pointing to the points), not answered as an empty map; days after its end show as missing. Points, including the frontend's charts and comparison years, answer any date and place: outside the box or before the archive from Open-Meteo, named in `meta.sources`. So Q38's three years (2011–2013) need no correction: they were left out to make the normals more accurate and serve nothing else. When a year leaves the archive, `ops.climatology.plan` already derives gridMET's version of it for `last30` (its files are kept as an overlap year)

### D88. Normals of counts: any bounds at points, a fixed set stored as running counts for maps and counties

(Ben, 2026-11-12; Phase 6 E6, FACTS's benchmark, F7). A count of days within bounds is the total of a series that is 1 on a day within them, 0 on a day outside and missing without a value, so its normal follows D61: each year's own count, then the mean and percentiles across years. At points `count=var:days_above_X` (as `/weather/totals`) on `/climate/normals` (a day's expected count from the pooled window, its running total from `start`, months' and the year's counts) and `/climate/compare` (this year's running count against last year's and the normal), any bounds, daily variables of the normals only (the copies are daily, so no `hours_` counts). For maps and counties a fixed set is stored beside the running totals as each period's mean running count from January 1, which is linear like a running total, so any window's normal count is a subtraction and `count=` takes `climate=normal` and `departure` on `/grids`, tiles, `/maps` and `/summaries` (a county's normal is its cells' normals averaged, as `/summaries` averages every map; averaging a county's weather before counting would lose the extremes). No percentile maps of counts. The set: maximum at or above 86, 90 and 93.2 °F (FACTS's heat days) and at or below 32 °F; minimum at or below 32 and 28 °F and at or above 70 °F (warm nights); precipitation at or below 0.01 in (dry days, FACTS's < 0.25 mm on values stored in 0.1 mm), at or above 0.5 and 1 in; sunlight at or above 20 and at or below 10 MJ/m². Bounds include their value where FACTS's are strict. Cold days (FACTS's mean below 50 °F) aren't stored: gridMET's years have no mean temperature, so only `last10` and `last5` count them, at points. A `last20` period (FACTS offers one) at points only; maps refuse it (its stored maps would add ~1 GB over Wisconsin, ~10 GB over the launch box).

### D89. A time limit on API requests: 30 s in the app, 45 s at Caddy, Open-Meteo's wait shortened in requests

(Ben, 2026-11-16; Phase 6, step 1). Some requests hung without answering (2026-11-07), and nothing bounded one. `api.timelimit.TimeLimitMiddleware`, first in `MIDDLEWARE`, answers an API request still running after `API_TIME_LIMIT` (30 s) with a 503 `timeout` envelope and `Retry-After: 120`, and logs the path and query with the stack of the thread running it (recorded by `TimingMiddleware`, Django's middleware frames left out), then its total time when it finishes. A thread can't be stopped, so the request finishes in the background and its answer is dropped. That's safe: API code never takes the write lock, the map caches' locks are held only around dictionary updates, and the rate limit, inside the chain, still charges the request's whole time. The rest of the chain runs as a task of its own and is waited on with `asyncio.wait`, not `wait_for`: asgiref's `sync_to_async`, when cancelled, waits for its thread to finish, so a cancelled await would answer only when the hang ended. Overruns are logged with how many are running, not refused (each request has its own thread under ASGI, so a hung one doesn't block others; checked on uvicorn: the 503 at the limit, a parallel request in 5 ms, the next on the same keep-alive connection in 12 ms). Caddy's `response_header_timeout` of 45 s is the outer bound, for a process too stuck to answer and for pages, and Caddy's `handle_errors` answers `/api/*` 502 and 504 in the envelope (`unavailable`). Open-Meteo calls made in a request (`ops.openmeteo`'s cache) wait 10 s and try twice (25 s at most with the pause) rather than 60 s and three times, so a slow Open-Meteo answers as `weather_unavailable` within the limit; a cold point a year back still makes ~24 calls, which can pass 30 s when Open-Meteo is slow, and the retry then finds the cache filled.

### D90. Every parameter in `meta.params`; identifiers in messages quoted

(Ben, 2026-11-16; Phase 6, step 1, asked 2026-11-06). Beside `meta.request` (what was computed), `meta.params` (`api.takes`) lists every parameter an endpoint takes, in the docs' order, each with the value used: `meta.request`'s value (a model's options from its `options` and its crop model's), else as given (parsed by the field's type, else as sent), else the schema's default, else null; `format` is the one answered in and `day_basis` `meta.location`'s. Beyond the declared schemas it lists what an endpoint reads itself: the options of the model or models asked for (on `/models/run` and `/risk` only those, not every model's; an option whose default differs between them has none), a model layer's options without those a map refuses (`POINT_ONLY`, `PLACE_OPTIONS`), a POSTed CSV's query fields, and a unit given for one variable. Errors carry it with what could be read, so `unknown_parameter` says "'meta.params' lists the parameters it takes" instead of pointing to the docs. CSV (`# params:`), NetCDF attributes and TileJSON carry it too. `api.strict` sets `request.api_takes` before the endpoint runs. In every message and warning, what a reader could type is in single quotes (`api.errors.quoted`): parameter names, values, `name=value`, variable, column, model and layer ids, typed examples; ordinary words used as words, dates in prose and paths stay bare. Under pytest `api.errors.check_style` flags an unquoted `name=value` or snake_case word in anything the API sends, and `app/conftest.py` fails the test; plain-word names ("start") are left to review. Found on the way: `climate.percents` made a singular by dropping an s ("The probabilitie '0' can't be used").

### D91. Response fields described in `api/docs/fields.toml`; the query groups off the docs page

(Ben, 2026-11-16; Phase 6, step 1, deferred from Phase 5's review). Every field of every response schema has public text, kept in `app/api/docs/fields.toml` (a table per schema, keyed by field) beside `parameters.toml`, not in `Field(description=)`: the public text stays in one place, apart from the code and its developer comments. `docs.apply` sets each property's description; shared types (`Location`, `Cell`, `Meta`, `DisplayUnits`) are written once. Each description is written from the code that fills the field, not its comment. The query groups (`GridQuery` and the rest) are components no operation refers to (Ninja spreads them into parameters, which have their text), so the public schema leaves them out; `export_types` keeps them, and the generated TypeScript types carry the field text as comments. Each endpoint page whose `meta.summary` has keys lists them, and a test compares the list with the keys a response from the fixture archive gives. `test_docs` checks every field has text, every entry names a field that exists, and the text keeps the public style. Data columns stay on the endpoint pages: they vary with the variables and models asked for.

### D92. Methods data from the code: `/methods`, sources by date, public corrections

(Ben, 2026-11-17; Phase 6, step 2.) How the data is made is served from the code that makes it, so the methods page (Phase 7) and model pages can't drift from it. `agdata.provenance` lists each source by use (`archive`, `provisional`, `forecast`, `outside`, `normals`) with its variables and the dates it fills where those are limited, taken from the source modules' constants (URMA's hourly precipitation from December 5, 2017; RTMA's before). Each `agdata.corrections.Correction` carries public text (`title`, `summary`) beside the notes for ourselves that generate `docs/corrections.md`, the catalog variables it changes, and held-out scores copied from its validation report, stamped with the table version they were measured on; a test fails when a refit changes the version until the scores are checked again. `GET /methods` serves both, `GET /methods/corrections/{id}` one correction with its fitted table (the tables are small JSON files in the code, the RH quantile maps ~29,000 numbers, so only there). Evidence links go to the validation reports on GitHub (the repository is public) at the running commit (`APP_VERSION`, `main` in development), labelled as technical reports. `/variables` names each variable's sources, gap fill and corrections, and model inputs their corrections, through the hourly variables a daily one is made from. Scores are copied by hand rather than written by the fit scripts: the scripts' outputs are reports, and a check against the report's text catches a copying slip.

### D93. A crop vocabulary; ids by convention, not prefixes

(Ben, 2026-11-17; Phase 6, step 2.) Crops have one set of ids (`agmodels.croplist`): plain nouns (`soybean`, `sweet-corn`), each with a name and a category (field, forage, vegetable, fruit and nuts, specialty, trees). A group is a crop with members (`cole-crops`, `wheat`, `beans`, `leafy-greens`, `pumpkin-squash`): a model naming a group applies to each member, and asking for a member finds its groups' models (`croplist.applies`). Models, topic pages, degree-day presets and typical planting dates name crops by id; responses give the names beside the ids (`crops`, `crop_ids`). `GET /crops` answers "everything we have for this crop". Ids carry no prefix by kind (`insect-…`, `crop-…`): the path names the kind (`/models/…`, `/crops/…`), a model's group can change and an id shouldn't, and a list mixing kinds carries `group`. The convention instead: weather variables and layers of them are snake_case catalog names; models are kebab-case, naming the pest or disease and the method where two could share it (`late-blight-dsv`); crops are plain nouns; no id repeats across lists that meet (the layers mix weather and models, so the model `degree-days` beside the layer `degree_days` became `custom-degree-days`).

### D94. Events on model results: points first, maps computed on request, no store yet

(Ben, 2026-11-17; Phase 6, step 3.) `first=`, `last=` and `since=` (D78) extend to models. Their main use is looking ahead at points (the frontend and email alerts), so points come first: `/models/{id}/run` (GET and POST) takes `first=high` (a risk level by name: at or above it), `first=R1` (a crop stage by code: at it or later), `first=above_2` on the default output, or `first=dd_total:above_450` on any output, in the units it's shown in; insects' life stages are numbers for now (ids may come with step 4's insect review). Answers go in `meta.summary.events`, through the forecast, with each day's kind and `before_start`; with `projection`, a `first` also gives in how many earlier years it's reached and P10/P50/P90 (`agmodels.scenarios.reached`). `meta.summary.milestones` (each stage, risk level and window's first day) now comes without a projection too. Maps take the same on the output they show (`output=`; no `output:` prefix), from the model's season or default biofix through the forecast's last whole day (`since` to the last observed day), computed on request over the range: no stored event maps or daily-levels copy (measured 1.3–14 s for a Wisconsin season before the ramp fix below; storage weighed against maps being the lesser use, and left to step 7, where a `timecopy`-style copy of the levels of the models people map is the option). Not on seasonal products' maps. VDIFN's sine ramp (24 insects) is now counted from its steps, identical to the sine at every 0.01 °F·d: European corn borer's Wisconsin season map 7.0 → 3.6 s at idle (the rest is `model_days`' reads and copies, for step 7); moving those insects to D36's curves is step 4's review.

### D95. NEWA is the standard where model sources conflict

(Ben, 2026-11-17; Phase 6 step 4.) Where NEWA (Cornell's Network for Environment and Weather Applications) runs a model of the same pest, crop or disease, its method and thresholds are the standard: above MSU Enviroweather's code, VDIFN's and the Crop Risk Tool's (Ben's own), unless a newer published source shows NEWA's wrong, and a difference we keep is recorded with its reason. Wisconsin's apple and grape growers use NEWA through about 30 stations run with the UW Fruit Program, so our results should agree with NEWA's on the same weather; we check that ourselves (`docs/plans/models.md` B5) rather than depend on colleagues' reviews. Where NEWA has no model, the next reference is the best published one for the region (WSU's Decision Aid System for tree fruit pests NEWA lacks, with care: it's fitted in central Washington). Enviroweather is credited by citing its website as a source on each model drawing on its code (no further terms). Applies to step 4's ports and to the 25 insects' review (part H): onion and cabbage maggot, among ours, are NEWA models too.

### D96. A daily feature may read hours before its day: apple scab's 120-hour window

(Ben, 2026-11-18; Phase 6 step 4, `docs/plans/models.md` B2.) Apple scab's infection periods are hourly wet periods that can run for days and join when less than 24 hours apart, and every model reads daily inputs. Rather than give models hourly inputs, the daily rollups (the grid's `agdata.daily` and a point's `agdata.point`, the same function `agmodels.features.scab_features` on both) compute the day's scab features from the 120 hours ending at its last reading (the day and the four before it): whether a period's wet hours reach the Revised Mills table during the day, the hours and mean temperature of the day's latest period, a flag when that period began within the window's first 24 hours (it may be longer), and NEWA's day and night rain for ascospore release. Each day is computed alone, so a day's features don't depend on where a rollup pass starts. Costs: the rollup reads four days of hours before the first day of a pass, and the forecast copies 144 archive hours before its first hour (was 48) so the run's first day has its window. The model itself carries a state day to day (ascospore maturity and release, the season's end), so its map is computed on request from each cell's green tip (`modelgrid.ON_REQUEST`), green tip read from apple stages' map from January 1. Fire blight (B3) follows the same pattern with calendar-day features (Cougarblight's values, degree hours above 65 °F, hours wet) and a map computed on request from January 1.

### D97. An insect's biofix may be estimated by latitude; generations may be capped

(Ben, 2026-11-18; Phase 6 step 4, `docs/plans/models.md` B4.) D36's insects gain three optional declarations in `agmodels.phenology`. `estimated_biofix`: the biofix event's degree days from January 1 as a function of latitude, used where the biofix is left at January 1, so each cell's curves start the day its total reaches the estimate (codling moth's first catch by Jones et al. 2013's quadratic, shifted 120 DD°F later to match Wisconsin's trap network, DATCP 2020–2025); a grower's date replaces it, and outputs say which was used (`dd_after_<event>`, `<event>_dd_estimate`, `<event>_estimated`). `max_generations`: the generations stop there (codling moth 2: third-flight larvae rarely mature in the Upper Midwest). `generation_size`: a class by the degree days from January 1 on a date, an output only, read through an `until` accumulation so `finish` stays day by day and maps need nothing new (codling moth's second generation, Riedl and Croft 1978); D37's equal generations stand. Codling moth uses the shared 86 °F cutoff rather than its sources' 88 °F (at most 9 DD by August 4 in southwest Wisconsin; Ben).

### D98. A validation report for every model, reachable from its page

(Ben, 2026-11-18; Phase 6 step 4, `docs/plans/models.md`.) The checks behind each model are kept in the repository, not in working notes. Each model has a technical report, `docs/validation/models/<id>.md`: its sources and what we took from each, the choices and differences from other systems (NEWA, Enviroweather, the legacy tools), its checks (against its sources' own numbers, other systems run on the same weather, observations in the field) with each one's numbers and the command that reproduces it, and its limits. Tables a script writes in full go in `docs/validation/models/<id>/`; the observations and reference tables they read go in `docs/validation/data/<dataset>/` with a README (source, date, caveats), only when small and public (DATCP's trap counts, stage observations); large downloads (NEWA's station hours, the archive) are fetched by the scripts, so no DVC. The model's spec summarizes each check for the public (`agmodels.spec.Check`: kind, what it was compared with, a plain result, the report section), `/models/{id}` serves them with links to the report on GitHub at the running version (as D92's evidence), and the model page shows them. Numbers are copied by hand, and `test_checks` fails if one isn't in the section it links to, or if a model has no report and checks (the older models were listed until part I1 reached them, 2026-11-18). The weather and legacy reports moved from `docs/validation-*.md` to `docs/validation/weather/` and `docs/validation/legacy/`. Codling moth is the worked example. Comparisons with NEWA are published with credit as factual results on public station data, from NEWA's published rules; NEWA's code and raw station hours stay out of the repository.

### D99. A crop-stage gate may take a date the user gives, apply only to a planting date given, and end days after a stage

(Ben, 2026-11-19; Phase 6 step 4, `docs/plans/models.md` handoff, wheat scab.) D33's `Susceptibility` gains three optional fields (`agmodels.spec`). `stage_date` (a `StageDate`): one of the model's options holds a date the user gives (YYYY-MM-DD, empty for none), the day their crop reached the stage; when given it replaces the crop model's estimate, and the window is `first` through `last` days from it, muted `margin_days` either side (`crops.date_susceptibility`). Maps refuse the option (D66), as they do `planting`. `planting_given_only`: when the crop model covers only some of the model's crops (spring wheat's stages for a model of all wheat), the gate runs only from a planting date the user gives, never a typical one, and maps aren't gated (no tier, no susceptibility output). `extend_days`: the window runs on through that many days after the crop reaches `last`, for a window that ends a set time after a stage begins rather than at the next stage. First use: `wheat-scab` 0.4, from heading (Haun 10.2) through 7 days after flowering begins (11.4) for spring wheat, or a `flowering_date` through 7 days after for any wheat, the fungicide window from early flowering. When sites exist (Phase 6 step 7), a spring wheat site passes its planting date, any wheat site its recorded flowering date, and a winter wheat site never a typical planting date.

### D100. D51's humidity map applies only in the Upper Midwest; pecan scab's 90% is counted at 88%

(Ben, 2026-11-19; Phase 6 step 4, `docs/plans/models.md`, audit round 2's pecan scab.) A check at five Oklahoma Mesonet stations in pecan country (Okmulgee, Burneyville, Durant, Eufaula, Shawnee), March–August 2023–2025 (`tmp/pecan-check/report.md`), found D51's RH quantile map, fitted in Wisconsin, made April 3.7 and May 2.2 times too humid there: on mapped RH, `pecan-scab` at 90% counted 1.12 times the stations' scab hours and reached its thresholds a median 15 days early, and D50's 88% counted 1.45 times their RH ≥ 90% hours. Raw Open-Meteo at 90% counted 0.68 of them and matched at 87.5–88.2% (station-seasons 85–89.4%), close to D50's 88%; at 88% the advisor's spray rule gave 10.0 sprays a season against the stations' 9.7. So: (1) D51's RH map applies only inside `openmeteo.RH_MAP_AREA` (40–49.5° N, 97.5–82° W: Wisconsin, Minnesota, Michigan, Iowa, northern Illinois); elsewhere Open-Meteo's RH is read as it comes (its shortwave correction is unchanged, unchecked there). (2) Pecan scab's feature (`hours_rh_over_90_temperature_over_70f`, version 2) is counted at D50's `STATION_RH_90_AS_GRIDDED` like the other RH ≥ 90% features; `pecan-scab` 0.3. The Southeast is more humid and unchecked: southern humidity models' pages say so until stations there are compared (Phase 9's mesonet comparison). **Follow-up (Ben, 2026-11-19): replace the box** with the map fitted against URMA region by region (URMA is the archive's source and covers the country, so the map means "Open-Meteo made to look like the archive" everywhere and has no edge): `scripts/fetch_urma_sample.py` samples URMA's hourly TMP and DPT at ~9,400 cells (every 20th row and column, ~50 km) and the five Oklahoma stations' cells into `data/urma-sample/` (2025, then 2024: ~1.5–3 hours a year). Ben then chose a statistical correction from the hour's own weather (no lattice or regions at run time), adopted only if it clearly beats raw Open-Meteo at one threshold: **`docs/plans/humidity.md`** (its own handoff), results in `docs/validation/weather/openmeteo-humidity.md`.

### D101. Fitted curves on two clocks, degree days and the calendar; every fitted model names its training area

(Ben, 2026-11-21; Phase 6 step 4, `docs/plans/models.md`, the Colorado potato beetle and aphid refits.) Ben's cross-validation of the beetle's scouting curves (`tmp/R/cpb/report-cv-aphids.md`) found the calendar timed a held-out year's events as well as degree days in central Wisconsin, and the calendar described the green peach aphid's suction trap catches better than degree days at every base. Ben asked for both clocks on every fitted model, the frontend to show either or both, and each model's training area to be shown and warned about outside it. (1) **Two clocks:** a `FittedStage` may carry the same fit on the day of year (`days`, `log_count_by_day`); an insect whose stages all do takes a `clock` option, `degree_days` or `calendar` (`clock=all` returns both, as any option), its default `Insect.clock`: the calendar where it fitted better out of sample (`green-peach-aphid`), degree days elsewhere (`colorado-potato-beetle`, `potato-aphid`, `aphid-pvy-vectors`, whose calendar curve fits the traps better in sample but whose degree days time the season's start better). The calendar curve is a typical season where the data came from; it's blank only where the degree days are. The pair also gives the frontend "running N days ahead of a typical year" (`docs/frontend.md`). (2) **Training areas:** `ModelSpec.trained` (`TrainingArea`: a public description, the years, whole states and five-digit county FIPS codes; kept coarse, never fields or farms) says where a model's data came from, apart from `region` (where it's shown at all). A point outside it runs and gets a `meta.warnings` line (`ModelRun.outside_training_area`, set by `agdata.series`); a map reaching past it gets one too (`modelgrid.training_mask`); `/models` lists it as `trained`. Set on the four fitted models now; part H and later fits set theirs, and published models can (spotted wing drosophila's Oregon data, for example). (3) **The beetle's counts** average each visit's main, edge and patch counts, a blank main count as 0 (Ben: the edge-only rows weren't meant to be dropped); `colorado-potato-beetle` 0.3 is refitted that way on the archive's 52/86 (gridMET's ran 31 above it), events 5–80 degree days earlier, "egg hatch" replaced by the larval rise (402). (4) **PVY's weight** is each species' transmission efficiency (Ben: asin(√efficiency) was a transform for proportions misused as a weight); `aphid-pvy-vectors` 0.3 peaks at 3,488 (was 3,582). (5) Two new models from the same analysis, `green-peach-aphid` (traps, calendar by default) and `potato-aphid` (central Wisconsin sweep counts, degree days by default), under one new topic page, `aphids-on-potato`. Aphid blanks in the scouting data are taken as not checked (Ben: scouts differ in whether they enter a zero), so only recorded counts are fitted; spray records aren't sought (Ben: the industry guards them; central Wisconsin fields get a neonicotinoid at planting, beetle sprays, and aphid sprays only at thresholds).

### D102. Part H: every insect on its source's method and curves; two new degree-day settings

(Ben, 2026-11-19 and 11-21; Phase 6 step 4, `docs/plans/models.md` part H.) Ben's answers to the part H plan (`tmp/part-h-plan.md`): retire western flower thrips; move insects without a known source onto D36 curves anyway; each source's own upper threshold; read NEWA's live pages for methods and constants. Built 2026-11-21 (`docs/insect-models.md` has the table): 19 insects rebuilt (0.2, western bean cutworm 0.3), every one but the retired three now on curves; NEWA's models for cabbage and onion maggot (simple average 40 °F) and alfalfa weevil (48 °F), Hanson et al. 2015 for western bean cutworm (NEWA's thresholds, its own method: D95's "unless a newer source shows it wrong" covers NEWA's deployed code, which caps the maximum and swaps two arguments); UW's own degree-day table (Delahaut's XHT1087; the table states no method, and its companion XHT1086 describes both averages, so the modified 50/86 from January 1 is our reading) for corn borer, cabbageworm, flea beetle and asparagus beetle; defaults for migrants' trap-date biofixes fitted to DATCP's traps (black cutworm May 1, corn earworm August 15; in sample, said so). Engine: `Insect.dd_method` gains `modified` and `average_capped_mean` (the day's mean capped at the upper threshold; no shared running total, so its daily degree days are kept per model in the ingredients store, unit `degF_day`); stored simple averages at 40 and 48 °F (`rebuild --stale` on the dev archive, 2026-11-21); `Insect.ported_from` keeps a rebuilt insect's 0.1 changelog line true. Field checks: DATCP's black light traps (2020–2026) and its western bean cutworm, black cutworm and corn earworm pheromone networks are tabulated in `docs/validation/data/datcp-blacklight-traps/` (`scripts/check_insect_traps.py`). Equal weights across generations (D37) are kept, though sources say one generation does the damage for several (the pages say which). Open for Ben: the models-plan handoff's list.

### D74. Grid days are Central Standard Time (UTC−6) all year; points default to the same and can ask for local days

(Ben, 2026-11-06). Per-cell local days drew the Central–Eastern time zone line onto daily maps: Nov 5, 2026 was a cold-front day whose high came in its first hour, so Eastern-time cells (their day an hour earlier) ran a median 0.5 °F and up to 5 °F warmer, a step down the middle of Lake Michigan and along the Upper Peninsula's county lines, plain on a degree-day map at `scale=auto`. The line is artificial, and the site is about weather. Every grid cell now shares one day, midnight to midnight CST (06:00–06:00 UTC), so no map can show a seam. No daylight saving: every day has 24 hours (no 23- or 25-hour precipitation and ET totals), and CST is within ±13 min of solar time across Wisconsin and ±30 min across the Upper Midwest (the equation of time adds ±16 min), so it is close to the natural day; in summer a day runs 1 a.m. to 1 a.m. CDT. v1 followed daylight saving, more or less, and its insolation import failed on the morning clocks fell back (Nov 1, 2026). Points default to the grid's days inside the box (so a map, its sidebar, downloads and alerts agree) and to local days outside it; `day_basis=central|local`on the daily point endpoints chooses, and every daily response states its window in`meta` ("midnight to midnight CST, 06:00–06:00 UTC"). Grid endpoints serve only the stored basis. Hourly views show the local clock with UTC. **Solar days** (from longitude and day of year) are deferred to a national grid, where one zone can't serve: with hourly data a per-cell solar day must start on a whole hour, which steps at a meridian and draws a north–south line, so it needs interpolated edges and partial hours in every daily statistic. **A night's minimum** (noon CST the day before to noon on the date) joins the daily variables beside the calendar-day minimum; a model switches to it only where its source used morning readings (the model review). **Windows within a day** (Ben, 2026-11-06): one rule, a window from A to B holds the readings stamped after A through B (hour ending, as the calendar day's 01:00–24:00), so precipitation in it is exactly what fell between A and B. **Night is 6 p.m. to 6 a.m. CST** (readings 19:00–06:00, 12 hours) site-wide, and the overnight 24-hour day the disease-severity models read (late blight, carrot foliar, Cercospora on beets, Botcast) starts at 6 p.m. too (readings 19:00 the evening before through 18:00), replacing the Crop Risk Tool's 8 p.m., which Ben chose for it more or less arbitrarily: one seam for both. Tar spot keeps the night its coefficients were fitted on (Webster et al. 2023, as the Crop Risk Tool counts it): its readings stamped 20:00–06:00 are 7 p.m. to 6 a.m. under the rule (11 hours; the old label said 8 p.m. to 7 a.m.), named for that window rather than "night". The night minimum stays noon to noon: winter lows often come after 7 a.m. CST. Work list under Phase 5.

### D103. Part H round 2: a normal of each place, weights per generation, a "present" window, a fixed biofix

_2026-11-23._ (Ben, 2026-11-23; Phase 6 step 4, `docs/plans/models.md` part H.) Ben's answers to part H's questions, all as proposed. **A model may read a fixed value of each place**, a normal from the 30-year maps (`spec.PlaceNormal`, `agdata.normals.place_normal`), at a point's cell and per cell on a map; where it's missing (outside the normals' area, or a point off the grid) the model falls back to its own form with a warning, never another cell's value. `european-corn-borer` 0.3 runs one flight (PERT 900, 1,400, 1,900, modified 50/86 °F) where the `last30` normal from January 1 through August 1 is below 1,500: Antigo, Manitowoc, Wausau and Marshfield's traps go one-flight, and Wausau's flight midpoint is a median 0 days off (two flights' summer flight ran 19 days late); the normal moves each January, so a place near 1,500 can change forms. A form is evaluated only at the cells that take it (a review of 2026-11-23 found it doubled every corn borer map's cost); a run must be given the normal (NaN explicitly for none), and crop tiers refuse a model with one. The 1,500 rests on DATCP's traps alone: Hoard and Weiss 1995 (North Dakota) support a form chosen by place, with a partial second flight in warm years, but give no degree-day bound (read 2026-11-23). **D37's equal generations give way to weights per generation** where the sources name the damaging generation (`Insect.generation_weights`; activity outputs stay unweighted): cabbage and onion maggot 1, 0.5 (the spring flight); seedcorn maggot 1, 0.25 (the spring generation; Iowa's summer one mostly aestivated); imported cabbageworm and cabbage looper 0.5, 1, 0.5 (the second generation). The sources say which generation matters, not by how much, so every weight other than 1 is a judgment, labelled as one. Cabbage maggot stops at three flights (Eckenrode and Chapman's Wisconsin count; NEWA's 850 DD40 generation kept, the page saying Wisconsin's summer flights may come later). **An action window may be "present"** (`ActionWindow.when`): open from the first individuals entering a stage timed from another until most have left (black cutworm 0.3's cutting window, 311–903 °F·d after the capture). **A biofix may be fixed** (`Biofix.fixed`, `Insect.biofix_fixed`): the runner refuses any other date (`runner.check_biofix`, so every path does; the default date itself is accepted), the API maps that to its message, discovery reports `fixed`, and a preset gives `starts="date"`; western bean cutworm's March 1 (Hanson et al.'s thresholds were fitted from it). Also: `tarnished-plant-bug` retired (0.3; no source times *L. lineolaris*'s spring generation); `mint-flea-beetle` kept with its Wisconsin emergence doubt stated; variegated cutworm stays on Simonet et al. 1981; corn rootworm keeps air degree days (a soil degree-day feature is a later step); the trap-fitted defaults (black cutworm May 1, corn earworm August 15) labelled as fitted in sample; cautions on corn rootworm (may run early), squash vine borer (the window may close early) and mint root borer (may run late), with no shift.

### D104. The insect papers read in full: five models changed

_2026-11-23._ (Ben, 2026-11-23; Phase 6 step 4, `docs/plans/models.md` part H.) Ben fetched the papers part H had read only through abstracts or other sources (41 in all, with UW's XHT1087 handout), and approved every change their reading proposed. **Cabbage maggot 0.4 leaves NEWA's generation** (850 → 1,275 DD40, SD 128): NEWA's later peaks are Jyoti et al.'s spring 50 % plus each flight's length, not measured intervals; Jyoti et al.'s own trapped peaks (1,212 DD40 on Open-Meteo at Geneva) and Wisconsin's (Eckenrode and Chapman's 1,176 DD43, about 1,335 DD40) both show 850 too short, an exception D95 allows (NEWA's own source shows it wrong). Its summer peaks now fall 1 day before to 12 days after Jyoti et al.'s trapped peaks (NEWA's 7–26 days before). With the three-flight cap (Wisconsin's count) binding in 60 of 67 station-seasons, **0.5 shows a partial fourth flight** (Ben, 2026-11-23: for fall crucifers), weight 0.5, ended by the season's freeze rule: first flies at 3,880 DD40 (about September 14 at Arlington, September 26 at Hancock on the normals, not at Rhinelander); on 2016–2025's weather a median 93 % of it had emerged when freezes ended the season at Arlington, 56 % at Hancock, 2 % at Rhinelander. **Seedcorn maggot 0.4** weights (1, 1, 0.25): the engine's second generation is the large early-June flight (Funderburk et al. 1984, Fig. 2). **Onion maggot 0.4** weights (1, 0.1, 0.5): the second brood was always the smallest and did little damage (Liu et al. 1982, Fig. 4; Eckenrode et al. 1975), the third damages bulbs into storage; judgments. **Corn rootworm 0.3**: larvae 350 → 550 (Davis, Brenes and Allee 1996) and pupa 200 (Jackson and Elliott 1988), so hatch to beetle 542 → 750; XHT1087's 1,300 DD50 is the first beetles; no separate western corn rootworm hatch (Wilde 1971 and Levine et al. 1992 fall within the model's); the "684–767 soil degree days" extension pages give for western hatch are a unit slip from Wilde 1971. **Black cutworm 0.4**: larvae on Kaster and Showers 1984's outdoor spring times with Luckmann et al. 1976's egg (pupation 729 → 613 °F·d after laying), so the cutting window closes about a week sooner. Imported cabbageworm's pupa (Nealis et al. 1984, 193) and common asparagus beetle's split of its 600 (Taylor and Harcourt 1978's pupa 166 plus about 30) change no output. XHT1087 (Delahaut 2005) gives base temperatures only: its numbers are read on the modified average 50/86 °F from January 1, our reading (its companion XHT1086 describes both averages and recommends neither; UW's corn borer guidance, Flandermeyer and Bick, times sprays in modified base 50 °F degree days), which DATCP's corn borer traps support; corn borer's table is not Apple 1952's numbers. Inland lakes' lake-cooled normals (a one-flight patch over Lake Winnebago) are fixed when the normals are built for the launch box, with the terrain store's water mask and the coast rule (Ben, 2026-11-23). Allen 1976's sine is a double sine; our single sine is within a day of it (stalk borer unchanged).

### D105. The launch coverage: the 12 Midwest states and Kentucky with a 50 km buffer, as a mask on a fixed window

_2026-11-23._ (Ben, 2026-11-23; Phase 6 step 7, replacing D20's `upper_midwest` rectangle.) The old preset, 35–50° N and 100–75° W, didn't match its own description: it cut the Dakotas, Nebraska and Kansas in half, reached Philadelphia, and its window (a rectangle in the grid's projection) took in eastern Montana, much of Ontario and Quebec's south and the Atlantic. Launch coverage is now a **mask**: North Dakota, South Dakota, Nebraska, Kansas, Minnesota, Iowa, Missouri, Wisconsin, Illinois, Indiana, Michigan and Ohio (the Census Bureau's Midwest) and Kentucky, each with a 50 km buffer, plus Lakes Superior, Michigan, Huron and Erie whole (the wave-height mask, `coast.water`), so lake maps aren't cut into bands; Lake Ontario borders none of these states and is left out. Measured on the Census Bureau's 2023 state boundaries: 444,535 cells (7.7× Wisconsin's window) inside a window of 656 × 876 (574,656 cells; j 572–1227, i 957–1832); as built (2026-11-23, the buffer on an equal-area projection rather than the grid's, and the 143 cells the mask encloses filled, gaps in the wave-height water), 447,313 cells in 658 × 877 (j 572–1229, i 956–1832), and Pittsburgh falls inside the buffer, against 675,962 for the old rectangle and 627,648 for the states' lines plus 0.2° extended to 78.5° W (discussed the same day for Toronto and Niagara). The **window** is the mask's bounding rectangle and stays fixed; stores keep it, cells outside the mask are written as missing, and zarr writes no chunk that's wholly missing, so storage follows the 32 × 32 hourly chunks the mask touches (487 of 588). Jobs that work over the window skip blocks wholly outside the mask where the profile shows it matters. **Outside the mask is outside coverage**: points there (Ontario, including Toronto, and every other state) go to Open-Meteo as points outside the box always have, the forecast there is Open-Meteo's, and maps leave it blank. Windsor and Thunder Bay fall inside the buffer. No Canadian or other sources are patched in. "Inside the box" in the code becomes "inside the coverage mask". Adding states later within the window is a backfill of their cells; beyond it, a new window.

### D106. Work over the grid in 256-cell blocks, in a pool of worker processes

_2026-11-23._ (Ben, 2026-11-23; Phase 6 step 7 B.) The launch-box profile's first rollup crashed WSL at 20 GB: the rollup worked in strips of 128 rows across the whole window for a month at a time, so its memory grew with the window's width (16.4 GB for one 877-cell strip, against 1.8 GB over Wisconsin), and half of that was the ET0 estimate computed over every cell outside the coverage mask, whose ET0 is always missing. The strips were a leftover from local days per cell (before D74); every daily statistic, feature and model works on a cell's own series, so any block gives the same answer. Every job that computes over the grid (the rollup, running totals, chill portions, the models' ingredients and crop tiers, the past-years copy in halves) now works in **squares of 256 cells from the store window's corner** (`agdata.blocks`), the daily chunk, so a block's write fills whole chunks; over the mask only blocks with a covered cell are kept. The ET0 estimate is computed only over covered cells missing some ET0. A 31-day rollup pass of one block peaks at 3.8 GB whatever the window. Blocks run in a **pool of spawned worker processes** (`BLOCK_WORKERS`, or a data command's `--block-workers`; 1 by default): a worker writes its block's values without the write record (`GridStore.write(record=False)`) and the calling process records them, creates stores and holds the write lock (waves of blocks under a polite lock), so no chunk or `_meta` array has two writers. Chains keep the ingredients' spans of days in order within a block. Cells added to the coverage later fall in whole blocks to compute; aligning the window itself to a grid-wide block lattice, so blocks are the same everywhere, is put to Ben as Q41.

### D107. The coverage window lies on a grid-wide lattice of 256-cell blocks

_2026-11-24._ (Ben, 2026-11-24, answering Q41; Phase 6 step 7 B.) A coverage preset's window is the mask's bounding rectangle (its **extent**, 658 × 877 at (572, 956) for `upper_midwest`) rounded out to multiples of 256 cells from NDFD's southwest corner (`coverage.on_lattice`; `upper_midwest` j 512–1280, i 768–2048, 768 × 1280). The stores' 256-cell daily chunks and the jobs' blocks (D106) are then the same squares of the grid in every store and in any future window, so a wider coverage later grows the window by whole blocks: the stores keep their chunks (renamed by whole chunk offsets, not rewritten) and the cells added are new blocks to backfill. Storage doesn't grow (zarr writes no chunk wholly outside the mask), and neither does the work: a block over the mask is trimmed to its covered cells' bounding rectangle in 32-cell steps from its corner (`coverage.TRIM`, the hourly chunk and a multiple of every smaller one, so no store's chunk is split between two blocks run in different processes); `upper_midwest`'s 14 blocks hold 565,248 cells against the extent's 577,066. The yearly NetCDF downloads and their `grid.nc` cover the extent, not the window (`coverage.extent`), so they don't carry the margin. Not changed: arrays written whole over a store's window (the crop tiers' first days at each stage) and the source requests over the window (ERA5-Land's and IFS's areas grow with it until step 7 F crops them to the extent). Cost: the profile archive (`tmp/launchbox`) rebuilt on the new window. A new state's hours still come from whole-CONUS files (URMA's messages cover the grid), so its backfill downloads as much as the first one did.

### D108. Hours every hour, the maps' updates every six hours; the forecast built in blocks over the coverage

_2026-11-24._ (Ben, 2026-11-24; Phase 6 step 7 D, from B's timings.) On the launch box an hour of ingest cost ~6 min of updates (the days rolled up again, running totals, ingredients) plus ~9 min restitching the forecast, every hour under the write lock, and a forecast run 21 min; the updates cost about as much for one new hour as for six. **The hourly job still fetches and writes every hour** (cheap: ~5 s of work an hour), **but the days behind their hours are rolled up only when an update is due** (`ops.ingest.behind`, `update_if_due`): a grid day has all its hours but no values yet (the day just over, at the first job after midnight CST), or an hour written has waited `UPDATE_EVERY` (6 hours); and always, before a forecast run is built, so the run stitches to the archive as it stands (NBM's long runs, every 6 hours, ~65 min after their cycle). "Behind" is read from the stores' write times (a day's hours against its daily statistics), so nothing extra is kept and a missed run catches up. The restitch follows an update, not every hour, and the crop stages are queued after an update or a published run instead of at :55 each hour. Locations aren't affected: points read the hours themselves; only the maps lag, by at most six hours (a morning's rain shows on the disease and leaf-wetness maps by early afternoon). A forecast run is derived in **parts over the coverage** (`forecast.parts`: the trimmed blocks in 128-cell squares, ~1.1 GB each, in the block pool) instead of strips across the whole window (1.7× the mask's extent). With it, two costs found in the same profile: a year's running totals write only the changed days but summed the whole year as a running sum along days, and NumPy's running sum along the first axis of a 3-D array is ~15× slower than adding each day's map to the one before (`agmodels.accumulate.cumsum_days`, the same numbers to the bit); the running totals now sum the days before the first written one once and keep a running sum only after it.

### D109. A map is offered only within a budget of storage and compute; otherwise a model is point-only

_2026-11-24._ (Ben, 2026-11-24; Phase 6 step 7 C.) The launch-box profile found apple scab's and fire blight's maps, computed on request over the whole window for a season, reaching 60 GB in one request (it crashed the development machine). Maps are worth offering, but only when they don't take an undue share of storage and compute: a model's map is kept only if it can be served from stored data or a bounded computation. Apple scab and fire blight are first to be stored as crop stages are (step 7 D3); if their storage or the job's time can't be made reasonable, their maps are dropped and they're offered at points only, where they run on one cell's hours. No request may hold the whole window over a season (step 7 D2).

### D110. Soil moisture from ERA5-Land and IFS, by the model's layers

_2026-11-25._ (Ben, 2026-11-25; Phase 6 step 6.) Volumetric soil water (m³/m³) by ERA5-Land's layers 0–7, 7–28 and 28–100 cm (`soil_moisture_0_to_7cm`, `_7_to_28cm`, `_28_to_100cm`, daily mean), from the sources and by the coast rule soil temperature uses (D52, D79), IFS for the provisional and forecast hours. Layers rather than depths: interpolating to depths changed the correlation with the stations by 0.02 at most, and plant-available water will want the layers. HRRR isn't used (drier than the stations, no better correlated). Against 80 Wisconet stations (2025–2026, frozen hours left out) ERA5-Land correlates 0.65–0.73 by day, IFS 0.40–0.65; ERA5-Land reads 0.04–0.09 wetter, mostly a fixed offset per station (0.03–0.05 once each station's own bias is removed), so a value is the model's soil, not a field's, and a percentile against the archive's years is the more trustworthy product (`docs/validation/weather/soil-moisture.md`).

### D111. IFS's soil moisture is shifted at the seam as its temperature is (D55)

_2026-11-25._ (Ben, 2026-11-25; with D110.) IFS reads 0.04–0.07 m³/m³ drier than ERA5-Land for weeks at a time, so its moisture is shifted to meet ERA5-Land's at the seam by D55's method, weights by lead fitted on Open-Meteo's ERA5-Land minus IFS at the stations (fitted on 2025, tested on 2026; 3 days on, the gap 0.079 → 0.043, 0.075 → 0.023 and 0.086 → 0.010 by layer), never below 0. `ifs_soil_seam.json` version 2; temperature's weights unchanged.

### D112. The changelog and the "Tell us how you use the API" form

_2026-11-25._ (Ben, 2026-11-24, approving Phase 6 step 5's plan with its seven recommendations.) A new app, `updates`, holds what we tell the people who use AgWeather and what they tell us. `ChangelogEntry` is written by staff in the admin, in Markdown with raw HTML escaped: a kind (`api`, `model`, `data`, `outage`, `announcement`), a date, a title, a body, `published` (off for drafts), an optional `banner_until` (Phase 7 draws the banner), and an optional model id or endpoint, checked against the registry and the OpenAPI paths rather than stored as choices. Published entries are served on `/changelog`, as an Atom feed at `/changelog.atom` (API users have no accounts, so a feed is how they follow changes) and at `GET /api/v2/changelog`, whose ETag follows the published entries' ids and edits. The "Tell us how you use the API" form at `/api-use` saves an `ApiUseReport` for staff to review in the admin, with a `notify` box ("Email me before changes that affect the API") as the anonymous opt-in. No CAPTCHA: a honeypot field, a signed timestamp (a form sent in under 3 s is dropped quietly; one over a day old asks the reader to reload), limits counted in the database (5 an hour per IPv4 address or IPv6 /64, loopback exempt; 100 a day overall) and length caps. The pages live outside `/api/` (Inertia and CSRF are skipped there, and the API's rate and time limits would apply), so the API docs' links moved from `/api/changes` and `/api/feedback` to `/changelog` and `/api-use`. Both pages are minimal stubs; Phase 7 designs them. Models' version histories stay in their specs (`/models/{id}`) and aren't copied into the changelog before launch; staff write the notable ones. Active API notices in `meta.warnings` wait until a breaking change is scheduled; the site banner as a shared prop, and email to reports that ask for notice, come in Phase 7.

### D113. Verification archive: every published run's lead days kept and scored

_2026-11-25._ (Ben, 2026-11-24, approving Phase 6 step 5's plan.) When a long NBM run is published (all four a day: 01, 07, 13 and 19Z), its lead days 1–10 are copied, as published, into `data/forecast/verify/{cycle}/`. Lead k is the grid day k days after the one the cycle falls in (01Z belongs to the day before); only days starting after the run's last observed hour are copied, and lead 0 is never kept or scored. The copy is taken right after publishing, under the write lock and before any restitch (which overwrites the run's days with observations). It holds 11 daily weather variables (min, max, mean dew point, mean RH, precipitation, ET0, shortwave, mean wind, hours of RH over 90, the same at night, wet hours) and 5 disease models' daily values (late blight, carrot foliar and Cercospora DSVs, early blight P-days, BOTCAST DSI), packed as stored over the whole covered grid, kept 45 days (~5 GB) and pruned at publish. A failure to keep logs a warning and never stops a run from publishing. A daily job (`score_forecasts`, 14:25 UTC) and `manage.py verify` score each kept day once the archive has closed it, and again whenever the archive rewrites it (RTMA replaced by URMA, a rebuild, a backfill): the kept day against the archive's over the covered cells where both are known, into `ForecastScore` (n, bias, MAE and RMSE of forecast − observed in catalog units, per run, lead and variable; degree days 50/86 °F from each side's min and max; precipitation also wet-day hits, misses and false alarms at 0.01 in). A variable kept or archived from older code (D29) is skipped. Scores are kept indefinitely (~250,000 rows a year) and pooled weighted by n. `/up` shows `forecast.verification` (the newest scored day; the last 7 days' MAE and bias at leads 1, 3 and 7 for min, max, precipitation and degree days), with a problem when lead-1 MAE of the max or min passes 3 °C (the backtest's is ~1.2–1.3) or a kept day due 3 days ago hasn't been scored. A disease value's error reflects the run's stitch and gap-filling as well as NBM's. Scores cover the whole coverage; per-state pooling (`regions.mask`) can come later.

### D114. Open-Meteo's forecast for points in the box while ours is stale

_2026-11-25._ (Ben, 2026-11-24, approving Phase 6 step 5's plan.) Our NBM run is used for 12 hours after its cycle (`MAX_RUN_AGE`, unchanged). Past that, or with no run, a point inside the box takes Open-Meteo's forecast after the archive's last observed hour, read as for a point outside the box (`ops.openmeteo.cell_hours` through the per-cell cache: NBM then best_match per hour, IFS soil, D51's corrections with humidity mapped only inside `RH_MAP_AREA`; no D49 calibration and no D55 seam shift). Its hours are kind `forecast` through Open-Meteo's last hour, the ingest lag included, sourced `openmeteo`, and its corrections replace the run's. `Forecast.reason` stays `stale` or `none`; a new `Forecast.fallback` says `openmeteo`, or `unavailable` when it couldn't be had. A request's fetches share about 10 seconds, and the first failure stops them. A failure answers 200 with the observed days and a warning, not a 503, and today's in-box soil fill (D44) does the same; `meta.warnings` says which happened, on the daily, hourly, degree-day, chill and model routes. These answers carry no ETag while the days reach the forecast endpoint's week. Running totals at a point stop after the observed days. Grid maps, tiles and map events show no forecast meanwhile. `/status` gives `forecast.fallback` and `/up` `forecast.points_fallback`; `OPEN_METEO_FALLBACK` turns it off. CLAUDE.md's rule on fetching weather in a request now includes "or inside it while the forecast is stale". Built with it: `cells_days` works out day kinds per cell (it took them from the first cell of each zone), and `ops.openmeteo.spans` no longer fetches the month's history when every day asked for is within the forecast endpoint's reach.

### D115. Open-Meteo usage counted against the plan

_2026-11-25._ (Ben, 2026-11-24, approving Phase 6 step 5's plan.) Every request the app makes to Open-Meteo counts against the plan, failures and retries included (Open-Meteo counts what it receives), weighted as Open-Meteo weighs it (variables / 10 × days / 14, at least 1). `agdata.sources.openmeteo.fetch` reports each HTTP attempt to an `on_call` hook, and `ops.openmeteo_usage.fetch_counted` adds them to `OpenMeteoUsage` (a row per UTC day and endpoint) whether the fetch succeeds or raises; every caller in the app fetches through it, and a test fails on one that doesn't. Rows are kept two years. The plan is 5,000,000 calls a month (`OPEN_METEO_MONTHLY_CALLS`), its billing month renewing on the 12th (subscribed May 12, 2026; `OPEN_METEO_BILLING_DAY`), so the month runs from the 12th to the 11th in UTC days; without a key, the free API's 300,000 a month and 10,000 a day. A warning, never a stop: at 80% of the month (`OPEN_METEO_WARN_SHARE`), when the last week's pace would pass the month's limit by its end, and, without a key, at 80% of the day's cap. Each names the period ("November 12 to December 11") and shows on the admin's Open-Meteo usage page (a summary always), on `/up` (degraded, in an `open_meteo` section), in `manage.py jobs` and the dashboard, and as a daily warning in `housekeeping`'s log; email to admins can follow if no one watches `/up`. Not counted: IFS's open-data reads from S3 (not the API) and the development scripts' `agdata.clients.openmeteo_points`.

## Questions


### Q1–Q3

**Question:** Job queue, stored units, repo

**Recommendation or answer:** **Resolved** → D17, D18, D19 (2026-10-27)

**Needed by:** –

### Q4

**Question:** Server size, region and pricing

**Recommendation or answer:** With IT: `docs/server-sizing.md` (2026-11-02): r7i.2xlarge (8 vCPU, 64 GB), 1.5 TB gp3 data volume, RDS db.t4g.medium; ~820 GB of products for the Upper Midwest's 11 years

**Needed by:** Phase 1 exit

### Q5

**Question:** Production domain

**Recommendation or answer:** **Resolved** → D62

**Needed by:** –

### Q6–Q9

**Question:** Precision, climatology timing, early precip, local backfill

**Recommendation or answer:** **Resolved** → D21–D24 (2026-10-27)

**Needed by:** –

### Q10–Q15

**Question:** NBM runs, forecast min/max, Open-Meteo models, soil past 48 h, Open-Meteo cache, horizon

**Recommendation or answer:** **Resolved** → D38–D43 (Ben, 2026-10-29, as recommended)

**Needed by:** –

### Q16

**Question:** Seasonal products (Phase 4 H): potato volunteer's window and whether seasons count forecast days

**Recommendation or answer:** Window November 1 to March 31, appearing January 1 (Ben, 2026-10-30); observed days only; final once the permanent data covers the window → D68

**Needed by:** Phase 4 exit

### Q17

**Question:** Model output maps for the slider (Phase 5)

**Recommendation or answer:** **Resolved** → D47 (Ben, 2026-10-30): precompute, built from ingredients each model's logic can combine; only the last week plus the forecast during development

**Needed by:** –

### Q18

**Question:** Shortwave: HRRR reads 18% high against 80 Wisconet pyranometers (Phase 2 H)

**Recommendation or answer:** **Resolved** → D48 (Ben, 2026-10-30): correct it

**Needed by:** –

### Q19–Q20

**Question:** Forecast humid hours short; NBM's TMAX warm in summer

**Recommendation or answer:** **Resolved** → D49 (Ben, 2026-10-31): calibrate both to the archive

**Needed by:** –

### Q21

**Question:** Gridded humidity thresholds for the RH ≥ 90 models

**Recommendation or answer:** **Resolved** → D50 (Ben, 2026-10-31): 88% on gridded data, through a shim

**Needed by:** –

### Q22

**Question:** IFS at 9 km for the grid (D52)

**Recommendation or answer:** **Resolved** (Ben, 2026-10-31): Open-Meteo's copy on AWS (native O1280), read with `omfiles` as an optional extra (D53)

**Needed by:** –

### Q23

**Question:** The ERA5-Land → IFS seam in soil temperature (Phase 4 I)

**Recommendation or answer:** **Resolved** → D55 (Ben, 2026-10-31): shift IFS, fading with lead

**Needed by:** –

### Q24

**Question:** Models with no weather read their lowest level

**Recommendation or answer:** **Resolved** → D56 (Ben, 2026-11-01): report as is, flag `ModelRun.missing` in the API and charts

**Needed by:** –

### Q25

**Question:** API envelope's metadata key (`docs/api.md`)

**Recommendation or answer:** **Resolved** → D57

**Needed by:** –

### Q26

**Question:** JSON data layout

**Recommendation or answer:** **Resolved** → D57

**Needed by:** –

### Q27

**Question:** XML responses

**Recommendation or answer:** **Resolved** → D57

**Needed by:** –

### Q28

**Question:** Default units

**Recommendation or answer:** **Resolved** → D57

**Needed by:** –

### Q29

**Question:** Regular lat/lng grids for v1's grid consumers

**Recommendation or answer:** **Resolved** → D57 (any resolution from 0.025°, nearest or mean)

**Needed by:** –

### Q30

**Question:** Rendered (colored) XYZ tiles and TileJSON for outside GIS users

**Recommendation or answer:** **Resolved** → D57

**Needed by:** –

### Q31

**Question:** API keys

**Recommendation or answer:** **Resolved** → D57

**Needed by:** –

### Q32

**Question:** Running models on a client's own weather (`docs/api.md`)

**Recommendation or answer:** **Resolved** → D58

**Needed by:** –

### Q33

**Question:** Filling a client's gaps from our archive, and extending it with our forecast

**Recommendation or answer:** **Resolved** → D58

**Needed by:** –

### Q34

**Question:** Climatology: keep the reference years' daily data on the grid, or only day-of-year statistics (`docs/api.md`, Climate)

**Recommendation or answer:** **Resolved** → D61

**Needed by:** –

### Q35

**Question:** Station normals (NOAA 1991–2020, as the State Climatology Office's spreadsheet uses) beside gridded ones

**Recommendation or answer:** **Resolved** → D61

**Needed by:** –

### Q36

**Question:** Weighting projected years by their similarity to this one

**Recommendation or answer:** **Resolved** → D67 (Ben, 2026-11-05, as recommended after the held-out study)

**Needed by:** –

### Q37

**Question:** Adjust gridMET's 30 years to the archive's basis before they become normals (D2's measurement, `docs/validation/weather/climate.md`)? Recommended: yes, by cell and pooled day of year from the 2016–2025 overlap: an added difference for temperatures and humidity (the archive's minimum runs +1.3 °F warmer a year, +2 °F in winter, 1–3 °F across cells; its maximum −0.7 °F), a ratio for precipitation (0.97), ET0 (0.83), shortwave (0.86) and wind (0.64). Without it, every departure map shows the sources' difference as weather, most at the Great Lakes' and Madison's lake shores (the isthmus' minimum +2.8 °F). The alternative for ET0, shortwave and wind: offer no 30-year normal for them (`last10` only)

**Recommendation or answer:** **Decided 2026-11-11 (D84)**: every variable adjusted, wind and ET0 after the wind check (D3 (a))

**Needed by:** 6 D3

### Q38

**Question:** gridMET's maximum temperature for 2011–2013 runs 3–6 °F above every station checked in summer (median +3.3, +4.2, +2.6 °F for June–August; July 2012 at Madison's airport 97.8 °F against ~91), in its files as served (dated 2019, permanent); every other year is within ~0.5 °F (`docs/validation/weather/normals.md` §4). Options: leave out those years' maximum (and ET0, computed from it), so the maximum, degree days and ET0 come from 27 years; correct them by a per-year offset fitted to stations; or take those years from another source. Recommended: leave them out

**Recommendation or answer:** **Decided 2026-11-11**: left out (`climatestore.LEFT_OUT`)

**Needed by:** 6 D5

### Q39

**Question:** URMA treats inland water cells (the Mississippi's channel at La Crosse, Lake Winnebago, Petenwell and Castle Rock, Lake Pepin, the Chippewa and Turtle–Flambeau Flowages) as water to different degrees by year: cells ≥ 3 °C under their neighbours' summer maximum number 0 in 2016, 189–334 in 2018–2020 and 23–91 since; our water mask has only the Great Lakes. A station or field beside them (La Crosse's airport) reads cool, inconsistently across years. Options: extend the water mask to inland water and answer a point on it from the nearest land cells (as the coast rule does), or leave it and rely on area averages (D83)

**Recommendation or answer:** **Decided 2026-11-11**: plan a fix (D6)

**Needed by:** 6 D6

### Q40

**Question:** The 30-year normal's frost dates run ~3 days milder than `last10`'s against stations (`docs/validation/weather/normals.md` §6): D84 adds the archive − gridMET mean difference to every day's minimum, so cold, calm nights warm as much as cloudy ones. Options: adjust the minimum by quantile (the overlap's distributions matched cell by cell and season, so the coldest nights take the coldest nights' difference), or accept it and say so beside the 30-year frost dates (`last10` for frost). Measure first: the archive − gridMET difference on nights below 32 °F against all nights over 2016–2025

**Recommendation or answer:** **Closed 2026-11-11, no change** (Ben: a grid is an approximation and won't fit every microclimate). Measured: by distribution the archive − gridMET minimum is nearly flat across quantiles (April–May P5–P10 +0.55 °F against ~+0.7 on average; fall +1.2–1.4 against ~+1.5), so a quantile fit gains ~half a day. Year by year at the stations, raw gridMET's freeze dates sit closest (spring −2.8, fall +0.2 days, mean), adjusted gridMET −4.9 and +3.5, the archive −3.6 and +2.2: the archive's frost nights run ~1 °F milder than these stations (many in frost pockets), and D84 carries that over. A 10-year median freeze date moves ±3.7 days by chance at a station, so most of `last30` against `last10`'s 3 days is noise

**Needed by:** 6 D5

### Q41

**Question:** Should the coverage window be aligned to a grid-wide lattice of 256-cell blocks (rows and columns that are multiples of 256 from NDFD's southwest corner), so a block is the same block in every store and every future window? Today blocks start at the window's corner (j 572, i 956), so adding a state inside the window is a backfill of its blocks, but a state beyond it means a new window: every store is rewritten. Aligned (j 512–1280, i 768–2048, 768 × 1280, every store's chunks on the lattice), a wider window later is a rename of chunk files by a whole number of blocks rather than a rewrite, and blocks keep their names across windows. Costs: the window grows from 658 × 877 to 768 × 1280 (no storage, since zarr skips empty chunks, but whole-window arrays and the yearly NetCDF downloads grow ~1.7× unless cropped to the mask's extent); the profile archive's hourly store is rebuilt once. Alternative: stores over the whole NDFD grid with the mask alone deciding what's written (no window ever changes; every whole-window array and download must crop). Note that a new state's hours still come from whole-CONUS files (URMA's messages cover the grid), so its backfill downloads as much as the first one

**Recommendation or answer:** **Resolved** → D107 (Ben, 2026-11-24: aligned now)

**Needed by:** –
