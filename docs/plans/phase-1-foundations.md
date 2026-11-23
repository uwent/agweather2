# Phase 1: Foundations — done 2026-10-27 (S)

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
- [x] Procrastinate installed (D17) with one periodic heartbeat task, run by `bin/dev` (replaced by the ingest job in Phase 2).
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
