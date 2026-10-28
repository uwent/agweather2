# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Project

AgWeather v2: one Django app replacing the AgWeather API (`../ag-weather`), the AgWeather website (`../soils-ag-wx`), VDIFN (`../ag-vdifn`) and three R Shiny apps (Crop Risk Tool, alfalfa, potato volunteer; not on this machine, Ben can copy them in). It stores hourly weather on the native 2.5 km NDFD grid in Zarr, runs every degree-day, disease and insect model from one Python package, and serves maps, sites, charts, alerts and a public API. Target: live before April 1, 2027.

- `PLAN.md`: architecture, recorded decisions (D#), phases and open questions (Q#). The current phase is detailed; later phases are sketches that get detailed when they start. Check it before starting work, and tick its checklists as work lands.
- `TODO.md`: things only Ben can do (installs, accounts, IT, data copies, exit checks), by phase.
- `docs/project-plan.md`: the original inventory and rebuild proposal, with the option comparisons, storage budget and server sizing behind PLAN.md's decisions. Background only; PLAN.md wins where they differ.
- `tmp/`: gitignored scratch (downloads, pilot output, one-off scripts). `data/` (gitignored) holds the local Zarr archive.
- `../wisp3`: the peer app (Rails + Inertia + Svelte). Its frontend (layout, tokens, charts, maps, units, accessibility tests) is the source to port from; its Ruby services map to Python here.

## Commands

```bash
bin/ci                           # full CI: ruff, prettier/eslint, pyright, svelte-check, pytest, vitest
uv run pytest packages/agmodels  # one package's tests
uv run ruff format . && uv run ruff check --fix .
pnpm typecheck:py                # pyright
pnpm check                       # svelte-check + tsc
pnpm test                        # vitest
```

Setup and the rest are in `DEVELOPMENT.md`. `bin/dev` (Django + Vite) arrives with Phase 1 B.

## Architecture

- uv workspace: `packages/agmodels` (pure model functions), `packages/agdata` (grid, variable catalog, Zarr stores, source adapters, tile encoding), `app/` (Django project). pnpm for `frontend/`. Python 3.13, Node 24.
- Django renders Svelte pages through Inertia (inertia-django), as WISP 3 does with Rails. The public API is Django Ninja under `/api/v2` with generated OpenAPI docs.
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
- **Content Security Policy:** scripts load only from our origin, so an inline `<script>` needs the nonce. A violation shows as a console error, which the smoke tests fail on.
- **Tailwind v4 only emits theme variables some class uses.** Tokens read from JavaScript (chart colors, map palettes) go in an `@theme static` block.
- **ECharts and MapLibre can't parse `oklch()`**: convert tokens to rgb on a canvas (WISP 3's `readPalette()` in `lib/charts/palette.ts`).
- **MapLibre** sets `position: relative` on its container, so size the container (`h-full w-full`) rather than positioning it absolutely. Its worker URL breaks under Vite unless loaded through a `loadMapLibre()` helper with `worker.format: 'es'` in `vite.config.ts` (WISP 3's `lib/map/maplibre.ts`).
- **Charts:** ECharts through one `Chart.svelte` taking a pure, unit-tested `build(palette)` option builder. Colors come from color-blind-validated `--color-chart-*` tokens. No dual-axis charts: stack grids or use small multiples.
- **Chromium fires `blur` on a focused input that's removed**; jsdom doesn't, so component tests of edit/cancel flows fire it themselves.
- **Playwright dismisses dialogs by default**, so a stray `confirm` cancels a navigation in a test; handle it with `page.once('dialog', …)`.
- **lint-staged runs Prettier on committed JSON.** Large data files go in `.prettierignore`, or they're expanded to thousands of lines.

Outside services:

- **Open-Meteo:** the forecast API reaches only ~92 days back (older days need the historical-forecast API or the archive). best_match, GFS and NBM have no soil variables over North America; ECMWF IFS does. Multi-model requests suffix each variable with the model name; multi-location requests return a list (one location, an object). Coastal points snap to a land cell, so the API's coordinates can differ from our cell's.
- **Nominatim** (place search) forbids search-as-you-type: search only on Enter or Go. Proxy it or switch providers if use grows.
- **Map overlays:** NOAA's MRMS image service labels its values inches but returns millimeters; NOAA's radar image service stores rendered colors, so radar values come from IEM's tiles (WISP 3's `lib/map/radar.ts`).
- **URMA on AWS** (`noaa-urma-pds`): 2016–2023 files have no `.idx`, so each hour is a whole ~69 MB download; later years allow byte-range reads. Hourly precip (`pcp_01h`) starts around 2018–2019.

Working here:

- **Propose a plan before building a new feature** unless it's a simple change: the design, the data model and any choices to make, then wait for Ben's go-ahead before implementing.
- Things only Ben can do go in `TODO.md` under the current phase, with the exact commands.
- `pkill -f` with a pattern that's also in the command line kills the shell running it; stop dev servers by port or PID.
