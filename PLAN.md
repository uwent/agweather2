# AgWeather v2 — Build Plan

One Django app that replaces the AgWeather API, the AgWeather website, VDIFN and three Shiny apps (Crop Risk Tool, alfalfa, potato volunteer). Target: live before **April 1, 2027**, with the old stack running in parallel until v2 matches it. The inventory, option comparisons, storage budget and server sizing behind this plan are in [docs/project-plan.md](docs/project-plan.md).

---

## 1. Goals

- **Hourly-native weather archive** on the native 2.5 km NDFD grid, 11-year rolling window (2016 onward), so hourly models (tar spot, white mold, night RH hours, moving averages) run on stored data.
- **One model library** (`agmodels`) used by ingest, maps, point series, the forecast and alerts, so a model gives the same answer everywhere.
- **Forecast as a first-class layer**: NBM in the box, Open-Meteo elsewhere, stitched to observations with a source flag, and run through the models.
- **Fast maps**: value-encoded data tiles colored on the GPU; cumulative cubes make any date-range sum one subtraction.
- **Open, cited, versioned models** with generated about pages.
- **A public v2 API** with OpenAPI docs, ready for Veg Path and DATCP before the 2027 season.
- **Sites, feeds and email**: multi-site dashboard, one-model and one-site feeds, a richer daily digest and event alerts.

### Non-goals (for the 2027 launch)

- A v1 API shim (v1 URLs redirect to the old server, which runs through 2027).
- CONUS coverage (the box is configuration; widening it is post-launch).
- AWON, HYD scraping, PNG map rendering, the three point-forecast vendors, Diak ET (see project-plan.md, Drop candidates).
- Personal API keys (only if usage demands it).

---

## 2. Recorded decisions

| # | Decision | Date |
|---|----------|------|
| D1 | **Django + Inertia + Svelte 5**, all Python on the server; Node only at build time | 2026-10-26 |
| D2 | **Native 2.5 km NDFD grid** shared by URMA, RTMA and NBM; no regridding between obs and forecast | 2026-10-25 |
| D3 | **Rolling 11-year window**, 2016–2026 to start, dropping the oldest year each January. Open-Meteo covers earlier dates | 2026-10-25 |
| D4 | **Service box is configuration**: Upper Midwest (≈35–50° N, 100–75° W) now; CONUS later by backfill | 2026-10-25 |
| D5 | **Zarr for gridded data** (one store per year), Postgres for app data. Postgres on RDS in production | 2026-10-26 |
| D6 | **Hourly precip from 2017-12-05** (when URMA's hourly files begin; first set as 2018, corrected 2026-10-27); earlier dates keep URMA 6-hour totals | 2026-10-25 |
| D7 | **Solar radiation from HRRR** analysis shortwave, regridded; SSEC is a development check only | 2026-10-26 |
| D8 | **ET0 is hourly FAO-56 grass reference**, summed to daily, matching Open-Meteo's method | 2026-10-26 |
| D9 | **Soil temperature modeled everywhere** (HRRR in the box, Open-Meteo outside); no Wisconet dependency | 2026-10-26 |
| D10 | **Forecast: NBM in the box, Open-Meteo elsewhere** (Professional plan, 5M calls/month) | 2026-10-26 |
| D11 | **30-year normals from nClimGrid-daily and gridMET**; 5/10-year normals from the internal archive | 2026-10-25 |
| D12 | **No v1 shim**; v1 URLs redirect to the old production server through 2027 | 2026-10-26 |
| D13 | **Models are open, cited, versioned** (beta/stable/retired), with declared regions and seasons and generated about pages; beta hidden unless a user opts in | 2026-10-26 |
| D14 | **Accounts by magic link or code**; digest, event alerts, or both; announce to current subscribers by BCC | 2026-10-26 |
| D15 | **Dedicated server** (Ubuntu 26.04, x86_64) running Docker Compose; RDS and the EBS data volume in the same AZ | 2026-10-26 |
| D16 | **uv workspace + pnpm monorepo**, Python 3.13, Node 24 | 2026-10-27 |
| D17 | **Procrastinate** job queue (Postgres-backed, periodic tasks) for ingest and app jobs (Q1) | 2026-10-27 |
| D18 | **SI units in storage** (°C, mm, m/s, W/m², kPa), converted by one units module (`agdata.units`, with a mirror in `frontend/lib/units.ts`) at the API and display edge; degree days stay in each model's own unit (mostly °F-days), labeled in the catalog (Q2) | 2026-10-27 |
| D19 | **Public GitHub repo `uwent/agweather2`** (Q3) | 2026-10-27 |
| D20 | **Named service-box presets** (`wisconsin`, `upper_midwest`, `conus`) chosen by `SERVICE_BOX`; development starts with `wisconsin` and scales up by switching the preset and backfilling | 2026-10-27 |
| D21 | **Coarse stored precision**: 0.1 °C temperature and dew point, 0.1 m/s wind and gust, 1 % cloud and RH, 1° direction, 0.1 mm precip, 0.1 kPa pressure (Q6, docs/pilot.md) | 2026-10-27 |
| D22 | **Climatology moves to Phase 6**, with the climate comparisons it feeds (Q7) | 2026-10-27 |
| D23 | **RTMA hourly precip before 2017-12-05**, when URMA has only 6-hour totals; supersedes D6's 6-hour plan (Q8) | 2026-10-27 |
| D24 | **Local backfill: Wisconsin 2024–2025**; the 11-year backfill runs on the server (Q9) | 2026-10-27 |

---

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
Caddy (TLS, cache for past-date tiles and grids)
   ▼
Browser: Svelte 5 + Tailwind v4, MapLibre with a WebGL data-tile layer, ECharts
```

**Request paths that must be fast** (targets from project-plan.md): risk map for any range < 300 ms (cumulative subtraction → cached tile), custom DD map season-to-date < 2 s (Numba sine DD), point season hourly < 300 ms (time-chunked read), point with forecast and all models < 1 s, palette change instant (browser).

---

## 4. Repository layout

| Path | Holds |
|---|---|
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
- The **service box** is a named preset (D20) chosen by `SERVICE_BOX` (`wisconsin` for development, `upper_midwest` for launch, `conus` later), or explicit `south,west,north,east` degrees for experiments. It is converted to a `(y, x)` index window on the full grid. Stores hold only the window, plus its offsets, so widening the box later is a new window and a backfill, not a new grid.
- Cell lookup: lat/lon → (y, x) nearest cell, and back; out-of-box points go to Open-Meteo (§7).

### 5.2 Variable catalog

One table in `agdata.catalog`: name, long name, stored unit, dtype and scale/offset (scaled int16 where precision allows), valid range for QC, sources by period, and daily aggregations (min, max, mean, sum, hours above/below). Hourly variables: 2 m temperature, dew point, RH, wind speed, gust, direction, surface pressure, sky cover, precip, shortwave radiation, soil temperature (and ET0 derived). Stored in SI (D18); `agdata.units` converts between SI and display units (°F, in, mph, ly/day, …) and is the only place conversion factors live in Python.

### 5.3 Stores

| Store | Shape | Chunks | Notes |
|---|---|---|---|
| `hourly/{year}.zarr` | time × y × x per variable | ~30 days × 32 × 32 | Point reads; one store per year so the window rolls by deleting a directory |
| `daily/{year}.zarr` | day × y × x per variable/statistic | 1 × 256 × 256 | Map reads; local-calendar day per cell |
| `cumulative/{year}.zarr` | day × y × x per fixed DD model and additive index | 1 × 256 × 256 | Running total from Jan 1; range sum = `cum[end] − cum[start−1]` |
| `climatology/` | doy × y × x per statistic | 1 × 256 × 256 | 30-year external and 5/10-year internal |

Zarr v3, int16 with pcodec (docs/pilot.md); a sharding codec if file counts get large. Every hour carries a source flag (urma, rtma, nbm, openmeteo) and an ingest timestamp, so the archive can be revised (RTMA → URMA) idempotently.

### 5.4 Time and days

UTC everywhere in storage. Daily rollups use each cell's local calendar day (time zone per cell from a time-zone raster). Models that need day/night windows use civil sunrise/sunset or solar noon/midnight, computed per cell (`agmodels.sun`).

---

## 6. Ingest

- **Hourly:** latest URMA (≈6 h lag) and RTMA for the hours since, via Herbie with byte-range reads; HRRR analysis shortwave and soil temperature, regridded to the NDFD window; QC against catalog ranges; write hourly; update today's and yesterday's daily and cumulative slices; invalidate today's tiles.
- **Forecast:** NBM hourly/3-hourly each cycle into a separate forecast store (not the archive), replaced on each run.
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

---

## 8. Models (`agmodels`)

- A model module exposes a spec (id, name, version, status, citations, region, season, inputs, outputs, risk thresholds, sweep) and a function from a standard hourly or daily frame to its outputs.
- Pipeline stages, each separately testable: hourly → daily (local day) → windows (night, moving averages) → indices (DD, DSV, P-days) → risk.
- DD: sine/average/modified methods; fixed base/upper pairs get cumulative cubes, arbitrary ones run on the fly with Numba.
- Insects: declarative specs (DD base/upper, biofix, stage thresholds, freeze adjustment), like CPN's `Insect()`.
- Tests: parity against old API outputs and R `.rds` fixtures; sweep snapshots that also render the about pages.

---

## 9. API v2 (Django Ninja)

`/api/v2`: points (hourly or daily, variable list, multiple points), grids (date or range with stat, binary or GeoJSON/CSV), data tiles (`/tiles/{layer}/{date}/{z}/{x}/{y}.png`), models (catalog, run at points, grid risk), DD table, freeze counts, downloads, dataset status. Units selectable, source and model version on every response. OpenAPI at `/api/v2/docs`, linked to the changelog page and the "how do you use the API" form. Rate limits at Caddy. If Django overhead shows in tile timings, mount a small Starlette app under `/tiles` sharing `agdata`.

---

## 10. Web app

Inertia + Svelte 5, ported from WISP 3 where it overlaps (layout, tokens, light/dark, fonts, units, charts, map helpers, glossary, CSV frontmatter, accessibility tests). Pages: map explorer (weather, DD and risk layers; date range, stat, palette, biofix; point popup), sites dashboard (sites in local storage, synced when signed in), feeds (one model × sites, one site × models), charts and downloads, model catalog and about pages, DOY calendar (keeps its URL or redirects), changelog, alfalfa and potato volunteer modules (P1), account and alert settings, admin (Django admin).

Page prop types: Pydantic schemas → JSON Schema → TypeScript, checked for freshness in CI (as Typelizer is in WISP 3). Public API types from OpenAPI.

---

## 11. Accounts, alerts and jobs

- django-allauth with login by email link or code; no passwords. Sites, alert choices, beta-models opt-in and service-update opt-in per user.
- Daily digest (past week, extended forecast, season vs normal, in-season models per site, upcoming thresholds) and event alerts (threshold crossed or forecast to cross). Users pick digest, alerts, or both.
- One Postgres-backed job queue (Procrastinate, D17) for ingest and app jobs, with periodic tasks.
- Health check: ingest lag, failed jobs, missing hours; emails admins; public `/up` JSON for an uptime monitor.

---

## 12. Testing and CI

- Python: pytest per package and for the app; fixtures are small cropped GRIB/NetCDF slices and recorded HTTP responses; no network (pytest-socket).
- Models: parity tests (old API, R fixtures) and sweep snapshot tests.
- Frontend: vitest for logic and components; Playwright smoke, axe accessibility (light and dark), keyboard and reflow tests, as in WISP 3.
- `bin/ci` runs everything locally; GitHub Actions runs the same script on pushes to `main` and on PRs.

---

## 13. Deployment and operations

Docker Compose on the dedicated server: `web` (uvicorn), `worker`, `caddy`; Postgres on RDS; Zarr on an EBS gp3 data volume; a scratch volume for GRIB downloads. Backups: RDS point-in-time, weekly EBS snapshots. Monitoring: external uptime check on `/up`, ingest-lag alert emails. Sizing and the IT request are in project-plan.md, Server requirements. Deploy details are written in Phase 8 (`docs/deployment.md`).

---

## 14. Phases

Each phase ends with an exit gate. Dates are estimates for Ben and Claude; the old stack runs in parallel throughout.

### Phase 1: Foundations (November 2026) — current

**A. Repo and tooling**

- [x] Ben: install uv and Docker, create `uwent/agweather2` (2026-10-27). First push 7e7c19d; CI green on GitHub Actions.
- [x] uv workspace: root `pyproject.toml` with members `packages/agmodels`, `packages/agdata`, `app`; Python 3.13 pinned; `uv.lock` committed.
- [x] Python tooling: ruff (format + lint, config in root `pyproject.toml`), pyright (basic mode, run through pnpm; django-types added in 1B), pytest with pytest-socket (importlib mode).
- [x] Frontend tooling copied from WISP 3 with paths changed to `frontend/`: `package.json` (pnpm pinned through `packageManager`), Prettier (with svelte and tailwind plugins), ESLint, `tsconfig.json`, `svelte.config.js`, vitest config, `pnpm-workspace.yaml`. Playwright config and `e2e/` move to 1B, when there is a server to test.
- [x] Husky + lint-staged: ESLint/Prettier on frontend files, `ruff format` + `ruff check --fix` on Python.
- [x] `bin/ci` (shell script, one step per check, stops on first failure, mirroring WISP 3's `config/ci.rb`) and `.github/workflows/ci.yml` (Postgres 18 service, uv, pnpm, Playwright).
- [x] `.env.example` (`DATABASE_URL`, `OPEN_METEO_API_KEY`, `DATA_DIR`, `SERVICE_BOX`), `DEVELOPMENT.md` (setup on WSL, like WISP 3's).

**B. Django skeleton**

- [x] Django 6.1 project in `app/` (`config/settings.py` driven by env, local Postgres `agweather2_development`/`_test`), ASGI under uvicorn; `bin/dev` runs Django, Vite and the worker with honcho.
- [x] Inertia: inertia-django 2.0 + django-vite. It implements the v3 protocol except validation errors, which `web/inertia.py` adds (errors through the session, shared once); CSRF cookie and header renamed for the v3 client. Notes in CLAUDE.md. The home page renders through `AppLayout`.
- [x] Port WISP 3's shell: `application.css` tokens (brand, surfaces, UW colors, light/dark; chart tokens wait for charts), fonts, `AppLayout`, brand bar and theme toggle, flash messages, `lib/dates.ts`; Playwright smoke (no console errors) and axe tests in light and dark, run by `bin/e2e` and `bin/ci`. `lib/units.ts` moved to 1C, built with `agdata.units`.
- [x] Django Ninja at `/api/v2` with a `status` endpoint and OpenAPI docs; `/up` health JSON; Django admin on; Content Security Policy (Django 6's) with the nonce for the theme script.
- [x] Procrastinate installed (D17) with one periodic heartbeat task, run by `bin/dev`.
- [x] Prop types: Pydantic `Props` subclasses → JSON Schema (`manage.py export_types`) → TypeScript (`bin/types`, json-schema-to-typescript), used by the home page and shared props; CI fails when stale.

**C. Grid, catalog and store layout (`agdata`)**

- [x] `agdata.grid`: NDFD 2.5 km Lambert conformal definition (from the GRIB2 grid section), service-box presets (D20) → index window, lat/lon ↔ (j, i), aligned sub-grid offsets; tested against 30 cell centers from a real URMA message. Windows: `wisconsin` 245 × 236 (57,820 cells), `upper_midwest` 742 × 911 (675,962), `conus` 1597 × 2345. Cell polygons for tiles move to Phase 5.
- [x] `agdata.catalog`: the §5.2 variables with SI units (D18), int16 scale/offset packing (checked to hold each QC range), QC ranges, daily statistics, sources. Soil temperature waits for Phase 2 (HRRR levels); daily-store variables (units of daily sums) are defined with the rollups in Phase 2.
- [x] `agdata.units`: unit registry and conversions (SI ↔ display), used by the API's `units=` and mirrored by `frontend/lib/units.ts` with a shared test table (`packages/agdata/tests/fixtures/units_cases.json`) so the two can't drift.
- [x] `agdata.store`: create/open a year's hourly and daily stores for the window, write a block of steps, read a point series and a tile window; source and write time per step per variable; tests on synthetic data in `tmp_path`. Writes touch whole time chunks, so the pilot decides how hourly ingest writes (straight into the archive, or a small recent store compacted later).
- [x] `agdata.sources.urma`: fetch one hour (analysis + hourly precip) for a window in SI, for every era of the bucket (file names, grids and precip changed in 2017 and 2018; see the module docstring). Our own range-request reader (`sources/grib.py`) instead of Herbie, whose URMA template knows only current names: it reads the `.idx`, or scans GRIB2 section headers where there's none (2016–2017), so only wanted messages download either way. Network tests (`--network`) fetch a 2016 and a 2025 hour.

**D. One-month pilot**

- [x] Ingest July 2025 (all hourly variables available) for the `wisconsin` box into `data/` locally (744 hours, no errors); the 2016 header-scan path was timed on single files (about 1.7 s per file to index). Each message is a whole CONUS field (~5 MB) whatever the window, so a month is ~30 GB of downloads: measure the rate first and extrapolate the 11-year backfill.
- [x] Measure: compressed size per variable per month (compare int16 scaled vs float32, zstd levels, chunk shapes), download and decode time per hour, point-season read time, daily tile read time.
- [x] `docs/pilot.md`: int16 + pcodec, 720 × 32 × 32 hourly chunks, D21 precision; the Upper Midwest's 11-year hourly store is about 342 GB (about 510 GB with the daily, cumulative and climatology cubes), so 1 TB covers it; CONUS about 2–3 TB. §5.3 and TODO.md updated.

**E. Containers**

- [x] `infra/Dockerfile` (multi-stage: Node build of `frontend/`, then `python:3.13-slim-trixie` with the system ecCodes 2.41 and uv; 1.2 GB) and `infra/compose.yaml` (`web` runs migrations and collects static into a volume, then uvicorn; `worker`; `caddy` serving static with immutable caching for Vite's hashed files and proxying the rest; `postgres` only with `--profile local`). Checked locally: health, pages with no console or CSP errors, admin static, API, and the worker running periodic and deferred jobs.

- **Exit:** `bin/ci` passes locally and on GitHub Actions; the home page renders through Inertia; the pilot report is written; server requirements confirmed with IT.

### Phase 2: Hourly archive (November–December) — next, approved 2026-10-27

> **Handoff (end of session 2026-10-28).** Done in Phase 2: A (precision, codec), B (URMA, RTMA, HRRR sources), C (RH, ET0, sun), D (QC), and F's backfill command and ingest pipeline. Next, in order:
> 1. **Local backfill: running** (TODO.md has the commands), 2025-01-01 to 2026-10-28 (D24's range changed to this for the pilot), about 27 hours at 6 s per hour of data. The command prints progress every 6 hours of data, holds `data/backfill.lock` so only one runs (several at once with 12 workers each crashed WSL), and defaults to 4 workers and 5-day blocks (about 1.3 GB). It resumes, skipping complete blocks.
> 2. **E: daily rollups and degree days.** Local day per cell (time zone per cell; Wisconsin is all Central), daily store variables in the catalog (sums in their own units: shortwave MJ/m²), the 17 legacy DD pairs ported from `../ag-weather` (`app/models/degree_days_calculator.rb`) with parity tests, and the cumulative store. `tmp/bf-test` holds 10 real days (2025-07-01 to 07-10, Wisconsin) for trying them.
> 3. **F, the rest:** `ops.IngestRecord` in Postgres (per block or hour: sources, failed hours, QC counts) and the admin page; the hourly Procrastinate job (the last 7 days' missing or RTMA-only hours, then their days); the health check with ingest lag.
> 4. **H: validation** against the old API (`/api/weather?lat=&lng=&start_date=&end_date=` and the `grid` endpoints), reducing v2 like the old API does (mean of the 2.5 km cells rounding to each 0.1° point, Central days, RTMA) — needs the backfill.
> Notes: the ingest writes `None` sources for failed hours, and short gaps are filled but not yet flagged as filled in the store. HRRR soil temperature over Lake Superior and Michigan is water temperature (about 2 °C in July); models should mask water cells.

Builds the archive the rest of v2 reads: URMA (and RTMA for the newest hours) plus HRRR radiation and soil temperature, QC'd, with derived humidity and ET0, rolled up to local days and running totals, filled by a backfill CLI and kept current by jobs. The data layout follows docs/pilot.md (int16 + pcodec; hourly chunks 720 × 32 × 32, daily and cumulative 1 × 256 × 256). Development runs on the `wisconsin` box locally; the 11-year backfill runs on the server once IT has it up.

**A. Store settings from the pilot**

- [x] pcodec level 8 and the pilot's chunk shapes as `agdata.store` defaults; catalog scales at D21's precision (shortwave stays 0.1 W/m² and hourly ET0 0.001 mm, which D21 doesn't cover).
- [ ] Add the daily-store variables to the catalog: each hourly variable's daily statistics (`air_temperature_max`, `precipitation_sum`, …) with their own units and scales (shortwave's daily sum is MJ/m², not W/m²), plus the per-day counts models need (hours with data).

**B. Sources**

- [ ] URMA (done in 1C). Before 2017-12-05, when URMA has only 6-hour precip, hourly precip comes from RTMA (D23).
- [x] RTMA (`noaa-rtma-pds`) for the hours URMA hasn't published yet (URMA runs about 6 h behind); the same reader and grid. Its files follow URMA's (`rtma2p5.tHHz.2dvaranl_ndfd.grb2_ext` until 2017-04, `_wexp` after), and its hourly precip `rtma2p5.YYYYMMDDHH.pcp.184.grb2` (the 2145 × 1377 grid) exists for every year since 2016 (checked 2026-10-27). An RTMA hour is replaced when URMA's arrives (the store's per-step source makes that visible). URMA and RTMA share `sources/analysis.py`; near a naming change the other naming is tried too (RTMA switched 2017-05-02, a day after URMA).
- [x] HRRR (`noaa-hrrr-bdp-pds`, 3 km Lambert, a different projection), regridded to NDFD by precomputed bilinear weights. Checked 2026-10-27: `wrfsfc` has only instantaneous DSWRF, so the hourly mean shortwave (D7) comes from the sub-hourly file `wrfsubhf01` (four 15-minute averages: 0-15 … 45-60 min, back to 2016); soil temperature is in `wrfprs` (TSOIL at 0, 1, 4, 10, 30, 60, 100 cm, and 160, 300 cm in 2016), so the potato model's 2 in and 4 in come from the 4 and 10 cm levels. 2016's sub-hourly files carry only instantaneous 15-minute values (no averages); their mean stands in. Done in `sources/hrrr.py` with `agdata.regrid` (bilinear, cached weights); soil temperature is stored at 4 and 10 cm. Still to check: how the HRRR versions (v2 2016, v3 2018, v4 2020) shift shortwave and soil temperature, and HRRR's soil temperature against Wisconet at a few stations (development check only, D9).
- [ ] Each source records what it ingested in Postgres (`ops.IngestRecord`: source, valid hour, variables, status, error, written at), shown in Django admin.

**C. Derived variables (`agmodels.weather`, pure functions with unit tests)**

- [x] Relative humidity and vapor pressure from temperature and dew point (FAO-56 eq. 11/14, the Magnus–Tetens form). Still to check against the CPN tool's R code in Phase 3.
- [x] Hourly FAO-56 Penman-Monteith grass reference ET0 (Allen et al. 1998, eq. 53) from temperature, humidity, 10 m wind (to 2 m, eq. 47), surface pressure, and shortwave radiation, with net longwave from the cloudiness ratio Rs/Rso and G = 0.1 Rn by day, 0.5 Rn at night; tested against FAO-56's hourly worked example (Example 19: Ra, Rso, Rn and ET0 for its day and night hours; note the example's clock is UTC − 1). Night Rs/Rso carries the last value from a sun above 17.2° (ASCE-EWRI), 0.8 before any. Done in `agmodels.weather` (`et0_hourly_series` takes stored variables); the Open-Meteo comparison is in H.
- [x] Sun position per cell and hour (solar elevation, FAO-56's solar time) for ET0's day/night split. Civil sunrise and sunset by local day, for model windows, come with Phase 3.

**D. QC and gaps**

- [x] Range checks from the catalog (values outside become NaN and are counted per hour in the ingest record), and a spike check on temperature and dew point (more than 12 °C from both neighbors in time, the same way): `agdata.qc`.
- [x] Short gaps (up to 3 hours) in continuous variables filled by linear interpolation per cell (`agdata.qc.fill_short_gaps`; the catalog's `fillable` excludes precip, ET0 and wind direction); longer gaps stay NaN (CLAUDE.md: missing is never 0). Recording filled steps in the store comes with the ingest job (F).

**E. Daily rollups and running totals**

- [ ] Each cell's local calendar day (Central or Eastern time, from a time-zone lookup per cell; daylight saving included), so a "day" matches what growers and the old API mean. Days with fewer than 20 of their hours present are NaN for that statistic.
- [ ] Daily store: the catalog's daily statistics, ET0 and precip sums, shortwave in MJ/m².
- [ ] Degree days from daily min/max for the 17 legacy base/upper pairs and methods (sine, average, modified; ported from `../ag-weather` with parity tests) into a cumulative store: running totals from January 1, so any range is `cum[end] − cum[start − 1]`. Precip and ET0 get running totals too. (The full model library is Phase 3; DD are here because the Phase 2 gate and the maps need them.)

**F. Ingest jobs and the backfill CLI**

- [x] `manage.py backfill --start --end [--box] [--workers] [--block-days] [--redo]` (`app/ops`), over `agdata.ingest.ingest_block`: fetches hours in parallel (URMA, else RTMA; RTMA precip before URMA's; HRRR) with 3 retries, range-checks and packs each hour, then spikes, short gaps, RH and ET0 over the block, and records each hour's source per variable. Blocks of at most 10 days by default (a month of Wisconsin in one block needs about 12 GB; 10 days peak at 3.9 GB); about 1,750 hours per hour of wall time here. Resumable: blocks already all-URMA are skipped. Rolling up days comes with E.
- [ ] Hourly Procrastinate job: ingest every missing or RTMA-only hour of the last 7 days, then roll up the touched days; daily rollup job after midnight local time; yearly roll in January (drop the oldest year's directories, rebuild the internal climatology).
- [ ] Health check (Phase 8 style, started now): ingest lag (newest URMA hour; newest any-source hour), failed jobs, missing hours in the last week; `/up` reports it and admins get an email when it's degraded.
- [ ] Run the backfill (D24): Wisconsin for 2024–2025 locally (about 17,500 hours, a day of downloads at home) for the gate checks; the full window on the server for the configured box when it's ready (about 4 TB of downloads, docs/pilot.md).

**G. Climatology: moved to Phase 6 (D22)**

- [ ] nClimGrid-daily (1991–2020) and gridMET reduced to day-of-year statistics on the NDFD window (mean, percentiles, frost and freeze probabilities, cumulative GDD for the fixed pairs), and the same from the internal archive for 5 and 10 years.

**H. Validation (the gate)**

- [ ] `scripts/compare_legacy.py`: v2 daily min/max temperature, precip and DD against the old API (`/api/weather`, `/api/precips`, `/api/degree_days` and their `grid` endpoints) at the old 0.1° points inside the box, 2016–present, written to `docs/validation-archive.md`. The old API (`../ag-weather` `WeatherHour`, `WeatherDay`) reads RTMA, not URMA, averages every 2.5 km cell whose lat/lon rounds to a 0.1° point (about 16 cells), and uses Central-time days everywhere; the script reduces v2 the same way, so what remains is RTMA vs URMA (expected: small biases, larger near lakes and terrain). v2's own days are each cell's local time, which differ from Central only east of the Central zone.
- [ ] ET0 against Open-Meteo's at 12 Wisconsin points (WISP 3's comparison points) and against SSEC insolation for shortwave.

- **Exit:** v2 daily min/max/DD/precip agree with the old API within stated tolerances, 2016–present (Wisconsin first; the full box after the server backfill); ET0 checked against Open-Meteo and SSEC; hourly ingest has run unattended for a week with the health check green.

### Phase 3: Model library (December–January) — sketch

Port the API/VDIFN daily models (DD 17 pairs, DSV, P-days, carrot DSV, Cercospora DIV, Botcast, oak wilt, ~30 insects) and the Crop Risk Tool's R models (tar spot, gray leaf spot, DON, white mold, frogeye, soybean Cercospora, red crown rot, wheat scab, pecan scab, cotton planting, winter rye), hourly-native where they exist; corn stages; specs with citations, versions, regions, seasons, sweeps. The R apps and their data are in `tmp/shiny/` (crop-risk-tool with `tests/testthat`, alfalfa-tool, potato-volunteer-risk).

- **Exit:** parity tests pass against the R fixtures and old API outputs.

### Phase 4: Forecast and blending (January) — sketch

NBM ingest into a forecast store on the same grid; obs + forecast stitching with source flags; models through the forecast window; Open-Meteo per-cell cache for out-of-box and pre-window points; region masks.

- **Exit:** a point inside and outside the box returns a continuous frame with sources, and every model runs over it.

### Phase 5: API v2 (January–February) — sketch

Points, grids, data tiles, models, DD table, freeze counts, downloads, dataset status, OpenAPI docs, changelog page, API feedback form; Caddy cache for past dates; latency checks against §3 targets. Veg Path and DATCP switch.

- **Exit:** v2 GDD matches the old API for DATCP's query; DATCP has the new endpoints.

### Phase 6: Web app (February–March) — sketch

Map explorer with the WebGL data-tile layer, sites dashboard and both feeds, charts and downloads, model catalog and about pages (text and citations; sweeps in P1), climatology cubes and current-vs-normal comparisons (D22: nClimGrid-daily 1991–2020 and gridMET reduced to day-of-year statistics on the grid, plus 5- and 10-year normals from the archive), DOY calendar, changelog, glossary and notes from WISP 3; accessibility and keyboard tests on every page.

- **Exit:** beta users on the new site.

### Phase 7: Accounts and email (March) — sketch

allauth sign-in by link or code, synced sites, settings (units, beta models, alerts, service updates), daily digest and event alerts, email layout ported from WISP 3, BCC announcement to current subscribers.

- **Exit:** digests and alerts verified on staging for test sites.

### Phase 8: Launch (by April 1, 2027) — sketch

Production deploy (`docs/deployment.md`), VDIFN and soils-ag-wx redirect to v2, soils-ag-wx emails stop, v1 API URLs redirect to the old production server.

### Phase 9: Refinement and CONUS (2027 season onward) — sketch

P1 (alfalfa, potato volunteer, climate comparisons, downloads, about-page sweeps) and P2 (frost/freeze probabilities, API keys if needed) features, new models and versions; then widen the box, backfill, resize the server, tighten region masks.

---

## 15. Open questions

| # | Question | Recommendation | Needed by |
|---|---|---|---|
| Q1–Q3 | Job queue, stored units, repo | **Resolved** → D17, D18, D19 (2026-10-27) | – |
| Q4 | Server size, region and pricing | With IT; minimum and CONUS sizes in project-plan.md | Phase 1 exit |
| Q5 | Production domain | Does v2 take over agweather.cals.wisc.edu at launch, or run beside it (e.g. v2.agweather…) during the beta? | Phase 6 |
| Q6–Q9 | Precision, climatology timing, early precip, local backfill | **Resolved** → D21–D24 (2026-10-27) | – |
