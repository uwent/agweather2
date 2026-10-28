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
| D6 | **Hourly precip from 2018**; 2016–2017 keep URMA 6-hour totals | 2026-10-25 |
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

Zarr v3 with a sharding codec if file counts get large; chunk sizes are confirmed by the Phase 1 pilot. Every hour carries a source flag (urma, rtma, nbm, openmeteo) and an ingest timestamp, so the archive can be revised (RTMA → URMA) idempotently.

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

- [ ] `agdata.grid`: NDFD 2.5 km Lambert conformal definition, service-box presets (D20) → index window, lat/lon ↔ (y, x), cell polygons for tiles; tests against lat/lon arrays from a cropped real URMA fixture.
- [ ] `agdata.catalog`: the §5.2 variables with SI units (D18), scale/offset, QC ranges, daily aggregations.
- [ ] `agdata.units`: unit registry and conversions (SI ↔ display), used by the API's `units=` and mirrored by `frontend/lib/units.ts` with a shared test table so the two can't drift.
- [ ] `agdata.store`: create/open a year's hourly and daily stores for the window, write an hour, read a point series and a daily tile window; source flag and ingest time per hour; tests on synthetic data in `tmp_path`.
- [ ] `agdata.sources.urma`: fetch one hour via Herbie (byte range where an index exists, whole file otherwise), crop to the window, map GRIB fields to catalog variables.

**D. One-month pilot**

- [ ] Ingest July 2025 (all hourly variables available) for the `wisconsin` box into `data/` locally, plus a day of 2016 to time the whole-file path.
- [ ] Measure: compressed size per variable per month (compare int16 scaled vs float32, zstd levels, chunk shapes), download and decode time per hour, point-season read time, daily tile read time.
- [ ] Write `docs/pilot.md` with the measurements, chosen chunking and codecs, and the extrapolated 11-year size for each preset (measured on `wisconsin`, scaled by cell count); update §5.3 and the IT sizing in TODO.md.

**E. Containers**

- [ ] `infra/Dockerfile` (multi-stage: Node build of `frontend/`, then Python 3.13 slim with eccodes) and `compose.yaml` (`web`, `worker`, `caddy`, local `postgres` for testing only); `docker compose up` serves the home page.

- **Exit:** `bin/ci` passes locally and on GitHub Actions; the home page renders through Inertia; the pilot report is written; server requirements confirmed with IT.

### Phase 2: Hourly archive (November–December) — sketch

URMA via Herbie (2016 onward), RTMA for the latest hours, HRRR shortwave and soil temperature regridded; QC and gap-fill; derived RH, vapor pressure, hourly FAO-56 ET0; daily rollups by local day; solar day/night windows; cumulative cubes for fixed DD pairs; climatology cubes (nClimGrid-daily, gridMET, internal 5/10-year); backfill CLI and yearly roll; ingest status and health check; backfill run on a temporarily larger instance.

- **Exit:** v2 daily min/max/DD/precip agree with the old API within tolerance, 2016–present; ET0 checked against Open-Meteo and SSEC.

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

Map explorer with the WebGL data-tile layer, sites dashboard and both feeds, charts and downloads, model catalog and about pages (text and citations; sweeps in P1), DOY calendar, changelog, glossary and notes from WISP 3; accessibility and keyboard tests on every page.

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
