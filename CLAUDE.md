# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Project

AgWeather v2: one Django app replacing the AgWeather API (`../ag-weather`), the AgWeather website (`../soils-ag-wx`), VDIFN (`../ag-vdifn`) and three R Shiny apps (Crop Risk Tool, alfalfa, potato volunteer; copies with their data in `tmp/shiny/`). It stores hourly weather on the native 2.5 km NDFD grid in Zarr, runs every degree-day, disease and insect model from one Python package, and serves maps, sites, charts, alerts and a public API. Target: live before April 1, 2027.

- `PLAN.md`: architecture, recorded decisions (D#), phases and open questions (Q#). The current phase is detailed; later phases are sketches that get detailed when they start. Check it before starting work, and tick its checklists as work lands.
- `TODO.md`: things only Ben can do (installs, accounts, IT, data copies, exit checks), by phase.
- `docs/project-plan.md`: the original inventory and rebuild proposal, with the option comparisons, storage budget and server sizing behind PLAN.md's decisions. Background only; PLAN.md wins where they differ.
- `tmp/`: gitignored scratch (downloads, pilot output, one-off scripts). `data/` (gitignored) holds the local Zarr archive.
- `../wisp3`: the peer app (Rails + Inertia + Svelte). Its frontend (layout, tokens, charts, maps, units, accessibility tests) is the source to port from; its Ruby services map to Python here.

## Commands

```bash
bin/dev                          # Django (uvicorn :8000) + Vite (:5173) + Procrastinate worker, via honcho
bin/ci                           # full CI: ruff, prettier/eslint, pyright, svelte-check, generated types, migrations, pytest, vitest, Playwright
uv run pytest packages/agmodels  # one package's tests
uv run ruff format . && uv run ruff check --fix .
pnpm typecheck:py                # pyright
pnpm check                       # svelte-check + tsc
pnpm test                        # vitest
bin/e2e                          # Playwright on a production build and its own database (args go to playwright test)
bin/types                        # after changing any props.py; commit frontend/types/generated
uv run app/manage.py migrate     # or any other manage.py command
```

Setup and the rest are in `DEVELOPMENT.md`.

## Architecture

- uv workspace: `packages/agmodels` (pure model functions), `packages/agdata` (grid, variable catalog, Zarr stores, source adapters, tile encoding), `app/` (Django project). pnpm for `frontend/`. Python 3.13, Node 24.
- Django project in `app/`: `config/` (settings from env; `DJANGO_ENV` = development, test (automatic under pytest) or production), and top-level apps `web` (Inertia glue and pages), `ops` (`/up`, jobs), `api` (Ninja). Run commands as `uv run app/manage.py …`.
- Pages: a view returns `web.inertia.render(request, "Folder/Page", SomeProps(...))`, which maps to `frontend/pages/Folder/Page.svelte`. Props are Pydantic models subclassing `web.inertia.Props`, defined in each app's `props.py`; `bin/types` generates their TypeScript types (`@/types`), and CI fails if they're stale. Every page uses `AppLayout`.
- Shared props (`web.middleware.SharedPropsMiddleware`): `app` (`SharedProps`) and `errors`. Flash is Django's messages framework, which inertia-django sends as `page.flash.messages` (`{level, message}`).
- Forms: on a validation failure, `redirect_with_errors(request, path, {"input.name": ["message"]})`; the next page gets them as `errors` once. inertia-django has no errors handling of its own.
- Public API: Django Ninja under `/api/v2` (`api/api.py`), docs at `/api/v2/docs`.
- Jobs: Procrastinate (`procrastinate.contrib.django`); tasks in each app's `tasks.py`, run by `manage.py procrastinate worker` (started by `bin/dev`).
- Vite: root `frontend/`, served under `/static/vite/`. django-vite loads `entrypoints/inertia.ts` from the dev server in development and unit tests (`VITE_DEV_MODE`), and from the build's manifest in `app/static/vite` otherwise.
- Gridded weather lives in Zarr (one store per year), never in Postgres rows. Postgres holds app data: users, sites, alert rules, job queue, ingest status.

## Rules

- **Missing data is NaN/NULL, never 0.** A gap stays a gap through rollups and models; fill only in a named, tested gap-fill step.
- **Time:** store and compute in UTC; convert to local time only for display and for models that define days by local calendar or sun position (PLAN.md §5).
- **Units:** every stored variable has one unit, declared in the variable catalog (`agdata`). Conversion to the user's units happens only at the display edge in the frontend, and through explicit `units=` on API requests.
- **One model, one file.** Each model in `agmodels` is a pure function with units in its names, a docstring saying what it predicts, citations, a version, a status (beta, stable, retired), a valid region and season, and a sweep spec. The same code runs on a point (pandas) and the grid (xarray). A deliberate change to a model's output bumps its version and adds a changelog line; parity and sweep tests must otherwise keep passing.
- **Weather is fetched by jobs, never in a request**, except Open-Meteo for points outside the box or before the window, which goes through the per-cell cache.
- **Tests never use the network.** Record GRIB slices and API responses as fixtures (small, cropped) under each package's `tests/fixtures`.
- **Legacy code:** when porting from `../ag-weather`, `../ag-vdifn`, `../soils-ag-wx` or the R apps, port the behavior with a parity test against its outputs, and record any intended difference in PLAN.md.
- **Python style:** ruff (format and lint, rules in the root `pyproject.toml`), pyright in basic mode, type hints on public functions. pytest runs in importlib mode, so test files may share names across packages. Prefer plain functions and small modules for domain math; no Django signals cascading recalculation.

## Gotchas

Carried over from WISP 3; they apply once the frontend exists.

Frontend:

- **Inertia v3** is newer than most training data: check `node_modules/@inertiajs/svelte/dist/*.d.ts` and `@inertiajs/core/types/types.d.ts` rather than guessing. `<Form>` errors come back keyed exactly as the server sends them; `onBefore` returning false cancels the request. Check what inertia-django implements of the v3 protocol before relying on a feature.
- **Svelte trims whitespace** at the start of `{#if}` blocks and inside elements, so "Site{#if x} · Crop{/if}" renders "Site· Crop": put separators and trailing spaces in expressions (``{` · ${crop}`}``, `{'Within '}`). When part of a button's text is hidden on small screens, give it an `aria-label` so its accessible name stays whole.
- **An `$effect` that calls code writing state it also reads** loops; run that call in `untrack`.
- **Accessibility (WCAG 2.1 AA):** an axe test runs on every page in light and dark, so add new pages to it; findings and fixes go in `docs/accessibility.md`. Links inside sentences are always underlined. An `sr-only` span inside a control needs the control to be `relative`. A grid of editable cells is one tab stop (roving tabindex); a bits-ui menu's items are left out rather than hidden with CSS.
- **Content Security Policy** (`SECURE_CSP` in settings, Django 6's built-in middleware): scripts load only from our origin, so an inline `<script>` needs `nonce="{{ csp_nonce }}"`. Development adds the Vite dev server. A violation shows as a console error, which the smoke tests fail on.
- **Tailwind v4 only emits theme variables some class uses.** Tokens read from JavaScript (chart colors, map palettes) go in an `@theme static` block.
- **ECharts and MapLibre can't parse `oklch()`**: convert tokens to rgb on a canvas (WISP 3's `readPalette()` in `lib/charts/palette.ts`).
- **MapLibre** sets `position: relative` on its container, so size the container (`h-full w-full`) rather than positioning it absolutely. Its worker URL breaks under Vite unless loaded through a `loadMapLibre()` helper with `worker.format: 'es'` in `vite.config.ts` (WISP 3's `lib/map/maplibre.ts`).
- **Charts:** ECharts through one `Chart.svelte` taking a pure, unit-tested `build(palette)` option builder. Colors come from color-blind-validated `--color-chart-*` tokens. No dual-axis charts: stack grids or use small multiples.
- **Chromium fires `blur` on a focused input that's removed**; jsdom doesn't, so component tests of edit/cancel flows fire it themselves.
- **Playwright dismisses dialogs by default**, so a stray `confirm` cancels a navigation in a test; handle it with `page.once('dialog', …)`.
- **Colors:** components use the semantic tokens (`surface`, `surface-raised`, `ink`, `ink-muted`, `line`, `frame`, `brand-*`, `danger`, `success`), never the named palette (`sand-*`, `gold-*`, `bark-*`, the current AgWeather site's colors) or raw hex. The tokens pick from the palette per mode in `application.css`; check a new text pair for 4.5:1 in both modes (axe does, on pages it scans).
- **Prettier's Tailwind plugin reorders class lists** on commit, so match a class string as it's written in the file now, not as you first wrote it.
- **Tailwind scans `app/` for classes in Django templates** (`@source '../../app'` in `application.css`); a glob over the template folders matched nothing. Don't write a glob with `*/` in a CSS comment: it ends the comment.
- **Vite's `server.origin`** must stay set: without it, fonts and images imported by CSS load from Django's port in development and 404.
- **lint-staged runs Prettier on committed JSON.** Large data files go in `.prettierignore`, or they're expanded to thousands of lines.

Django and tests:

- **inertia-django 2.0** implements the Inertia v3 protocol (once, deferred with rescue, scroll and merge props, history encryption, 409 on a stale `INERTIA_VERSION`), but not validation errors (see `web/inertia.py`). Its 303 conversion applies only to PUT/PATCH/DELETE redirects.
- **CSRF:** the Inertia v3 client sends the `XSRF-TOKEN` cookie back as `X-XSRF-TOKEN`; settings rename Django's cookie and header to match.
- **django-types lags Django 6:** symbols new in 6 (`django.utils.csp`, `ASGIStaticFilesHandler`) need a `# pyright: ignore[...]` with the reason.
- **uvicorn doesn't serve static files**: `config/asgi.py` wraps the app in `ASGIStaticFilesHandler` in development and tests; Caddy serves them in production.
- **honcho sets `PORT`** (5000, 5100, …) for every process, so `Procfile.dev` uses `DJANGO_PORT`.
- **pytest-socket** blocks the network; only localhost (Postgres) is allowed. Tests run in importlib mode with `app/` on the path. A test that must read a real service is marked `@pytest.mark.network` and `@pytest.mark.enable_socket`, and runs only with `uv run pytest --network` (not in CI).

Data (`agdata`):

- **Grid indices are (j, i)**: rows south to north, columns west to east, from NDFD's southwest corner. A `Window` is half-open; stores hold one window and take grid indices (`read_point(name, j, i)`), converting to local ones themselves.
- **ecCodes is the system library** (`libeccodes0`), not the `eccodeslib` wheel: that wheel bundles its own PROJ, and a process that loads it before pyproj crashes on exit (double free). Import eccodes through `agdata.sources.grib`, which silences the bindings' "2.42 recommended" warning.
- **Use eccodes' typed getters** (`codes_get_long`, `codes_get_double`, `codes_get_string`); plain `codes_get` returns a union pyright rejects.

Deploy:

- **One image, three containers** (`infra/`): `web` migrates and collects static into the volume Caddy serves before starting uvicorn, `worker` runs Procrastinate, `caddy` terminates TLS. Settings come from the environment (`infra/.env` on a server); `DJANGO_ENV=production` in the image.

Outside services:

- **Open-Meteo:** the forecast API reaches only ~92 days back (older days need the historical-forecast API or the archive). best_match, GFS and NBM have no soil variables over North America; ECMWF IFS does. Multi-model requests suffix each variable with the model name; multi-location requests return a list (one location, an object). Coastal points snap to a land cell, so the API's coordinates can differ from our cell's.
- **Nominatim** (place search) forbids search-as-you-type: search only on Enter or Go. Proxy it or switch providers if use grows.
- **Map overlays:** NOAA's MRMS image service labels its values inches but returns millimeters; NOAA's radar image service stores rendered colors, so radar values come from IEM's tiles (WISP 3's `lib/map/radar.ts`).
- **RTMA on AWS** (`noaa-rtma-pds`): the same names and grids as URMA's analysis; hourly precip `rtma2p5.YYYYMMDDHH.pcp.184.grb2` (2145 × 1377) in every year since 2016, which is what the old API read.
- **HRRR on AWS** (`noaa-hrrr-bdp-pds`): a 3 km grid in a different projection (regrid, don't offset). `wrfsfc` DSWRF is instantaneous; hourly means come from `wrfsubhf01`'s four 15-minute averages. Soil temperature (TSOIL) is in `wrfprs`, not `wrfsfc` or `wrfnat`.
- **URMA on AWS** (`noaa-urma-pds`): file names, grids and precip products change in 2017-05 and 2017-12/2018-11 (table in `agdata/sources/urma.py`). Files before 2017-05 have no `.idx`; `RemoteGrib` scans their GRIB2 section headers instead, so only wanted messages download. Every message is a whole CONUS field (~5 MB) whatever the window. Older grids are aligned sub-windows of NDFD (offset 0, 200).

Working here:

- **Propose a plan before building a new feature** unless it's a simple change: the design, the data model and any choices to make, then wait for Ben's go-ahead before implementing.
- Things only Ben can do go in `TODO.md` under the current phase, with the exact commands.
- `tmp/herbie`, `tmp/urma`: downloaded GRIB for exploring; the fixture makers in `packages/agdata/tests/fixtures/make_*.py` rebuild the committed fixtures.
- **Checking CI on GitHub:** filter by workflow (`gh run list --workflow CI`, `gh run watch <id>`). GitHub's "Dependency Graph" runs on every push too, and the newest run is often that one.
- **GitHub Actions versions:** some actions (setup-uv) publish only exact tags, no floating major; check with `gh api repos/<owner>/<repo>/git/ref/tags/<tag>` before pinning.
- `pkill -f` with a pattern that's also in the command line kills the shell running it; stop dev servers by port or PID.
