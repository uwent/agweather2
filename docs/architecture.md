# Architecture

How the system is laid out: the architecture, the data, ingest, the forecast, the models, the API, the web app, jobs, testing and deployment. Formerly PLAN.md §3–13 (moved 2026-11-23, section numbers kept, since code and reports cite them as §5.4 and so on). Written as the design and kept current as decisions change it; the end-of-phase documentation check holds it to the code. Decisions are in [decisions.md](decisions.md); the work, by phase, in [plans/](plans/).

## 3. Architecture

```
Sources (AWS NOAA buckets, Open-Meteo, nClimGrid, gridMET)
   │  ingest jobs: hourly pulls, QC, rollups, cumulative + climatology cubes
   ▼
Zarr stores (data volume)                     Postgres (RDS)
  hourly/{year}.zarr   time × y × x            users, sites, alert rules,
  daily/{year}.zarr    day × y × x             job queue, ingest status,
  cumulative/{year}    day × y × x             Open-Meteo cache index,
  climatology/         doy × y × x             API feedback, changelog
   │                                              │
   └──────────── agdata (read/write) ─────────────┤
                 agmodels (pure functions) ───────┤
                                                  ▼
Django (ASGI, uvicorn)
   ├── Inertia pages (accounts, sites, catalog, map shell, DOY calendar)
   ├── Django Ninja /api/v2 (points, grids, tiles, models, downloads; OpenAPI)
   ├── Django admin (users, sites, model metadata, ingest status, API feedback)
   └── Job worker (same codebase): ingest, rollups, alerts, digests, health
   ▼
Caddy (TLS, static files, v1 redirects; the app caches maps and sets Cache-Control, G4)
   ▼
Browser: Svelte 5 + Tailwind v4, MapLibre with a WebGL data-tile layer, ECharts
```

**Request paths that must be fast** (targets from project-plan.md): risk map for any range < 300 ms (cumulative subtraction → cached tile), custom DD map season-to-date < 2 s (Numba sine DD), point season hourly < 300 ms (time-chunked read), point with forecast and all models < 1 s, palette change instant (browser).

---

## 4. Repository layout

<!-- prettier-ignore -->
| Path | Holds |
| --- | --- |
| `packages/agmodels/` | Model library: hourly → daily → windows → DD → disease/insect models. Pure functions on xarray/pandas, NumPy and Numba. Each model: one file, metadata (citations, version, status, region, season, sweep). No I/O |
| `packages/agdata/` | Grid definition and service box, variable catalog, Zarr store layout and read/write, source adapters (URMA, RTMA, HRRR, NBM, Open-Meteo, nClimGrid, gridMET), QC, rollups, tile encoding |
| `app/` | Django project: `config/` (settings, urls, asgi), apps `accounts`, `sites`, `alerts`, `catalog`, `api`, `ops`; jobs; management commands (backfill CLI) |
| `frontend/` | Svelte pages and components, `lib/` (ported from WISP 3: units, dates, charts, map, glossary, tables, csv), `types/` (generated) |
| `infra/` | Dockerfile, `compose.yaml`, Caddyfile, backup scripts |
| `bin/` | `dev`, `ci`, `e2e` |
| `docs/` | project-plan.md, pilot results, accessibility, deployment, model notes |

Package boundaries: `agmodels` imports nothing from the others. `agdata` may import `agmodels` (rollups and cumulative cubes run models). `app` imports both. No Django in the packages.

---

## 5. Data

### 5.1 Grid and service box

- The NDFD CONUS 2.5 km Lambert conformal grid (2,345 × 1,597), defined once in `agdata.grid` with pyproj, checked against the lat/lon arrays in a real URMA file.
- **Launch coverage is a mask** (D105, `agdata.coverage`, `SERVICE_BOX=upper_midwest`): the 12 Midwest states and Kentucky with a 50 km buffer, Lakes Superior, Michigan, Huron and Erie, and the cells they enclose (447,313 cells), on a fixed window: the mask's bounding rectangle (its extent, 658 × 877) rounded out to the grid-wide lattice of 256-cell blocks (D107; 768 × 1280 at (512, 768)), so a store's daily chunks and the jobs' blocks are the same squares of the grid in every window, and a wider coverage later adds whole blocks without rewriting the stores. Jobs trim each block to its covered cells (`coverage.parts`), and the yearly downloads cover the extent (`coverage.extent`). `GridStore.write` keeps a store over that window missing outside the mask, so zarr writes no chunk wholly outside it; points outside it go to Open-Meteo (`ops.points.in_box`), areas take only covered cells, and summaries and model maps count only them (`regions.use_coverage`). Built by `scripts/make_coverage_mask.py`. The box presets below remain for development and experiments.
- The **service box** is a named preset (D20) chosen by `SERVICE_BOX` (`wisconsin` for development, `conus` later; launch's `upper_midwest` is the mask above), or explicit `south,west,north,east` degrees for experiments. It is converted to a `(y, x)` index window on the full grid. Stores hold only the window, plus its offsets, so widening the box later is a new window and a backfill, not a new grid.
- Cell lookup: lat/lon → (y, x) nearest cell, and back; out-of-box points go to Open-Meteo (§7).

### 5.2 Variable catalog

One table in `agdata.catalog`: name, long name, stored unit, dtype and scale/offset (scaled int16 where precision allows), valid range for QC, sources by period, and daily aggregations (min, max, mean, sum, hours above/below). Hourly variables: 2 m temperature, dew point, RH, wind speed, gust, direction, surface pressure, sky cover, precip, shortwave radiation, soil temperature at 4, 10 and 30 cm, soil moisture in the 0–7, 7–28 and 28–100 cm layers, snow depth (and ET0 derived). Stored in SI (D18); `agdata.units` converts between SI and display units (°F, in, mph, ly/day, …) and is the only place conversion factors live in Python.

### 5.3 Stores

<!-- prettier-ignore -->
| Store | Shape | Chunks | Notes |
| --- | --- | --- | --- |
| `hourly/{year}.zarr` | time × y × x per variable | ~30 days × 32 × 32 | Point reads; one store per year so the window rolls by deleting a directory |
| `daily/{year}.zarr` | day × y × x per variable/statistic | 1 × 256 × 256 | Map reads; local-calendar day per cell |
| `cumulative/{year}.zarr` | day × y × x per fixed DD model and additive index | 1 × 256 × 256 | Running total from Jan 1; range sum = `cum[end] − cum[start−1]` |
| `climatology/` | doy × y × x per statistic | 1 × 256 × 256 | 30-year external and 5/10-year internal |
| `daily-by-time/{year}.zarr` | day × y × x, daily min and max only | 32 × 256 × 256 | A season over the map (custom DD maps); a cache of the daily store's values, kept by `update_days` (`agdata.timecopy`) |
| `daily-by-point/{year}.zarr` | variable × day × y × x, settled years | all × year × 16 × 16 | A point's past years (projection, climatology; `agdata.pastyears`) |
| `forecast/verify/{cycle}/daily/{year}.zarr` | day × y × x, 11 daily variables and 5 disease values | 16 × 256 × 256 | Each published run's lead days 1–10 as published, kept 45 days for scoring (`agdata.verification`, D113; ~5 GB over the launch box) |

Zarr v3, int16 with pcodec (docs/pilot.md); a sharding codec if file counts get large.

Jobs that compute over the grid (the rollup, running totals, chill portions, the models' ingredients and crop tiers, the past-years copies) work in **square blocks of 256 cells** from the store window's corner (`agdata.blocks`): the daily chunk, so a block's write fills whole chunks, and eight hourly chunks a side. Over the coverage mask only blocks with a covered cell are kept, so a job's memory follows a block (~3.8 GB at peak for a 31-day rollup pass), not the window's width, and its work follows the coverage. Every daily statistic, feature and model works on each cell's own series, so blocks are independent: `BLOCK_WORKERS` (or a command's `--block-workers`) runs them in that many worker processes. A worker writes its block's values (`GridStore.write(record=False)`) and the calling process records the writes, creates stores and arrays and holds the write lock, so no chunk and no `_meta` array has two writers. Every hour carries a source flag (urma, rtma, nbm, openmeteo) and an ingest timestamp, so the archive can be revised (RTMA → URMA) idempotently.

### 5.4 Time and days

UTC everywhere in storage. Grid days are Central Standard Time all year, midnight to midnight CST (06:00–06:00 UTC), the same for every cell (D74). Points default to the grid's days inside the box and local days outside it, and take `day_basis=central|local`. Hourly displays show the local clock with UTC. Solar days wait for a national grid (D74). Models that need day/night windows use civil sunrise/sunset or solar noon/midnight, computed per cell (`agmodels.sun`).

---

## 6. Ingest

- **Hourly:** latest URMA (≈6 h lag) and RTMA for the hours since, via Herbie with byte-range reads; HRRR analysis shortwave and soil temperature, regridded to the NDFD window; QC against catalog ranges; write hourly. The days behind their hours (by write time) are rolled up with their running totals, chill and ingredients, and the forecast restitched, only when due: a day just over (after midnight CST), an hour waiting six hours, or before a forecast run is built (D108, `ops.ingest.update_if_due`). Points read the hours, so only maps wait.
- **Forecast:** NBM's long runs (every 6 hours) into a separate forecast store (not the archive), replaced on each run; its hours derived in parts over the coverage in the block pool (`forecast.parts`, D108). Its soil and snow are IFS's (D52): the stitch copies the archive's only through their last archived hour and the run's own carry on from there, so a new IFS read needs no restitch; its hours reach the run at the next update or run.
- **Backfill CLI** (`manage.py backfill --start --end --box`): idempotent, resumable, parallel by day; the same code path as hourly ingest.
- **Yearly roll:** in January, drop the oldest year and rebuild internal climatology.
- **Climatology build:** nClimGrid-daily and gridMET reduced once to doy cubes on the grid.
- Ingest status per source and hour in Postgres (`ops`), feeding the health check and admin page.

---

## 7. Forecast and Open-Meteo blending

- A point or grid request returns one continuous hourly frame: archive through the last observed hour, then NBM, each value with its `source`.
- Outside the box, before the window, or when NBM is missing, the frame comes from Open-Meteo, snapped to its O1280 cell and cached per cell for a few hours (Postgres index + files or cache table).
- Models receive the standard frame and do not know its source; responses carry `source` and the producing model's name and version.
- Each model's region mask is rasterized on the grid at startup; outside it the model returns no value and the map greys it out.
- Verification (D113): when a run is published, its lead days 1–10 that start after its last observed hour are copied as published into `forecast/verify/{cycle}/` (11 daily weather variables and 5 disease severity values, packed as stored), before any restitch overwrites them with observations, and kept 45 days; a failure to keep logs a warning and never stops the publish. The daily `score_forecasts` job (and `manage.py verify`) scores each kept day once the archive has closed it, against the archive's day over the covered cells, and again whenever the archive rewrites it (RTMA → URMA, a rebuild): `ops.models.ForecastScore` holds n, bias, MAE and RMSE per run, lead and variable (degree days 50/86 °F computed from each side's min and max; precipitation also wet-day hits, misses and false alarms at 0.01 in), kept indefinitely and pooled weighted by n. A disease value's error reflects the run's stitch and gap-fill as well as NBM.

---

## 8. Models (`agmodels`)

- A model module exposes a spec (id, name, version, status, citations, region, season, inputs, outputs, risk thresholds, sweep) and a function from a standard hourly or daily frame to its outputs.
- Pipeline stages, each separately testable: hourly → daily (local day) → windows (night, moving averages) → indices (DD, DSV, P-days) → risk.
- DD: sine/average/modified methods; fixed base/upper pairs get cumulative cubes, arbitrary ones run on the fly with Numba.
- Insects: declarative specs (DD base/upper, biofix, stage thresholds, freeze adjustment), like CPN's `Insect()`.
- Tests: parity against old API outputs and R `.rds` fixtures; sweep snapshots that also render the about pages.
- **Maps of models:** most are finished from a few days of stored ingredients (`agdata.modelmaps`). Models that carry a state day to day keep their whole season instead: crop stages per planting tier (`agdata.croptiers`) and apple scab and fire blight (`agdata.seasonmaps`), kept by the job after each update and forecast run. A map is offered only within a budget of storage and compute (D109): no request holds the whole window over a season, and a model that can't be stored reasonably is offered at points only.

---

## 9. API v2 (Django Ninja)

`/api/v2`: points (hourly or daily, variable list, multiple points), grids (date or range with stat, binary or GeoJSON/CSV), data tiles (`/tiles/{layer}/{date}/{z}/{x}/{y}.png`), models (catalog, run at points, grid risk), DD table, freeze counts, downloads, dataset status. Units selectable, source and model version on every response. OpenAPI at `/api/v2/docs`, linked to the changelog page and the "how do you use the API" form. Rate limits at Caddy. If Django overhead shows in tile timings, mount a small Starlette app under `/tiles` sharing `agdata`. The contract (envelope, formats, every endpoint) is designed in `docs/api.md` (agreed 2026-11-02, D57–D58).

---

## 10. Web app

Inertia + Svelte 5, ported from WISP 3 where it overlaps (layout, tokens, light/dark, fonts, units, charts, map helpers, glossary, CSV frontmatter, accessibility tests). Pages: map explorer (weather, DD and risk layers; date range, stat, palette, biofix; point popup), sites dashboard (sites in local storage, synced when signed in), feeds (one model × sites, one site × models), charts and downloads, model catalog and about pages, DOY calendar (keeps its URL or redirects), changelog, alfalfa and potato volunteer modules (P1), account and alert settings, admin (Django admin).

Page prop types: Pydantic schemas → JSON Schema → TypeScript, checked for freshness in CI (as Typelizer is in WISP 3). Public API types from OpenAPI.

---

## 11. Accounts, alerts and jobs

- django-allauth with login by email link or code; no passwords. Sites, alert choices, beta-models opt-in and service-update opt-in per user.
- Daily digest (past week, extended forecast, season vs normal, in-season models per site, upcoming thresholds) and event alerts (threshold crossed or forecast to cross). Users pick digest, alerts, or both.
- One Postgres-backed job queue (Procrastinate, D17) for ingest and app jobs, with periodic tasks.
- Health check: ingest lag, failed jobs, missing hours, the forecast's age and verification (`forecast.verification`: the last 7 scored days' MAE and bias at leads 1, 3 and 7; a problem when lead-1 MAE of the daily max or min passes 3 °C, or a kept day due 3 days ago isn't scored, D113); emails admins; public `/up` JSON for an uptime monitor.

---

## 12. Testing and CI

- Python: pytest per package and for the app; fixtures are small cropped GRIB/NetCDF slices and recorded HTTP responses; no network (pytest-socket).
- Models: parity tests (old API, R fixtures) and sweep snapshot tests.
- Frontend: vitest for logic and components; Playwright smoke, axe accessibility (light and dark), keyboard and reflow tests, as in WISP 3.
- `bin/ci` runs everything locally; GitHub Actions runs the same script on pushes to `main` and on PRs.

---

## 13. Deployment and operations

Docker Compose on the dedicated server: `web` (uvicorn), `worker`, `caddy`; Postgres on RDS; Zarr on an EBS gp3 data volume; a scratch volume for GRIB downloads. Backups: RDS point-in-time, weekly EBS snapshots. Monitoring: external uptime check on `/up`, ingest-lag alert emails. Sizing and the IT request are in project-plan.md, Server requirements. Deploy details are written in Phase 8 (`docs/deployment.md`).
