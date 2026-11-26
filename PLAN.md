# AgWeather v2 — Build Plan

One Django app that replaces the AgWeather API, the AgWeather website, VDIFN and three Shiny apps (Crop Risk Tool, alfalfa, potato volunteer). Target: live before **April 1, 2027**, with the old stack running in parallel until v2 matches it.

This file is where things stand and what's next: the one handoff, Ben's open choices, what waits on other people, and the order of the work. Rewrite the handoff at the end of each session (with an entry in `tmp/session-log.md`), and keep the lists current.

## Where the docs are

<!-- prettier-ignore -->
| Doc | Holds |
| --- | --- |
| [docs/decisions.md](docs/decisions.md) | Why: the recorded decisions (D1–D126) and the questions put to Ben (Q1–Q41). A new decision takes the next D number |
| [docs/architecture.md](docs/architecture.md) | How the system is laid out (§3–13: data, ingest, forecast, models, API, web app, jobs, testing, deployment) |
| [docs/plans/](docs/plans/) | The work, by phase in build order (Phases 1–5 done, 6 current, 7–9 sketches), and the plans that run beside a phase (models, humidity). Its README says what each holds and its status |
| [docs/api.md](docs/api.md) | The API v2 contract |
| [docs/frontend.md](docs/frontend.md) | The frontend spec (pages, features, conventions, open questions F#), built in Phase 7 |
| [docs/validation/](docs/validation/) | Technical reports: weather, legacy, and one per model (D98) |
| [docs/project-plan.md](docs/project-plan.md) | The original inventory and proposal (background; the docs above win where they differ) |
| [TODO.md](TODO.md) | What only Ben can do |
| [DEVELOPMENT.md](DEVELOPMENT.md) | Setting up a machine and the commands |

## Goals

- **Hourly-native weather archive** on the native 2.5 km NDFD grid, 11-year rolling window (2016 onward), so hourly models run on stored data.
- **One model library** (`agmodels`) used by ingest, maps, point series, the forecast and alerts, so a model gives the same answer everywhere.
- **Forecast as a first-class layer**: NBM in the box, Open-Meteo elsewhere, stitched to observations with a source flag, and run through the models.
- **Fast maps**: value-encoded data tiles colored on the GPU; cumulative cubes make any date-range sum one subtraction.
- **Open, cited, versioned models** with generated about pages and a validation report each.
- **A public v2 API** with OpenAPI docs, ready for Veg Path and DATCP before the 2027 season.
- **Sites, feeds and email**: multi-site dashboard, one-model and one-site feeds, a richer daily digest and event alerts.

Not for the 2027 launch: a v1 API shim (v1 URLs redirect to the old server, which runs through 2027); CONUS coverage (the box is configuration); AWON, HYD scraping, gnuplot maps, the three point-forecast vendors, Diak ET; personal API keys.

## Handoff (2026-11-26, evening)

**Phase 7, the web app** (branch `phase-6`, not yet renamed): [docs/plans/phase-7-web-app.md](docs/plans/phase-7-web-app.md). Phase 6 closed this morning (below). Ben settled Phase 7's architecture (D117–D123) and the detailed plans of tracks 2 (map explorer) and 3 (sites, home), all as recommended, with the map explorer split 50:50 (map left, controls right, detail below the fold). Claude orchestrates; agents build in worktrees, at most four at once.

**2026-11-26: Phase 7 waves 1–3** (11 build agents, 3 planning agents; each merged and checked; suite and Playwright 36/36 pass after the last merge):

- **Base (wave 1):** WISP 3's frontend ported in place (D121): dependencies to its versions, tokens, `AppLayout` (six sections; phones scroll them sideways, Ben), the settings dialog with the units switch, primitives, storage, the unsaved-changes guard, test helpers and Playwright's `scan()`; the chart and map cores, overlays, place search; `lib/api.ts`, `lib/viewState.ts` with Share (D118), `lib/routes.ts` from `bin/types`; the missing-days flags for every model (`<input>_missing`, warnings on runs, `/risk` and maps; the dev archive's ingredients rebuilt for it, 1.8 h).
- **Data tiles (wave 2):** `DataMap` colors the API's tiles with MapLibre's color-relief (D119 proved; values within the step at 25 cells). The TileJSON's `baseShift` had the wrong sign for MapLibre (it subtracts): fixed, worth a changelog line once live.
- **Pages (wave 3):** `/map` (picker, time and stepper, options, title chip, cell panel, Share), `/sites` (cards loading as they scroll in), the site page (header, Overview, Weather), the home page, the shared `status` prop with a stale banner; the TileJSON's `subtitle`, `caption`, `warnings`, `categories`; `/risk` over several days.

**Wave 4 (2026-11-26, later):** D124 (probability outputs in percent, eight models), D125 (one in-season rule; every insect a season, derived from our runs: provisional, for Ben), names; `/map` on phones, its county table and links; `/models` and the model pages; a model at a site with its chart and table; risk sparklines on cards and the site page. Suite 4,680 and Playwright 54 pass. The dev archive's ingredients were being rebuilt for the version bumps (`manage.py ingredients`, ~2 h, started 16:50).

**Wave 5 (2026-11-26, night; done):** the map's date control (the data's range moved from the title chip into a timeline slider after Ben's alfalfa tool: observed solid, forecast hatched, "Recent weeks" or a year, the stepper, a sentence on what can be mapped); the site page's Degree days and Data tabs and the one-model feed `/sites/models/{id}`; groups and preferences at three levels with where each value comes from, a group's map view, saving from the map into a group; topic pages `/topics`, `/topics/{id}` and the generated methods page `/methods`; potato planting per cell (D126, replacing D64's 40 km circles; maps show no data where a cell has no typical date). Suite 4,807 passed; pyright clean; vitest 504; Playwright 78. **Data:** `manage.py ingredients` restarted on the merged code at ~19:40 (the version bumps of D124–D126 make every year stale; ~15–18 min a year, ~3 h, ~3 GB; log `tmp/ingredients-w5.log`); blight and potato maps answer 503 "updating" until it's done. Check `ingredients --check` next session.

**Branches (Ben, 2026-11-26):** once wave 6 is merged and the suite is green, a PR `phase-6` → `main` (167 commits behind; Phase 6 is closed), merged after CI, then a `phase-7` branch from the new `main`; wave 7's briefs then start from `phase-7` (and worktrees from `main` need no reset).

**Next, in order:**

1. **Check the ingredients rebuild** (`uv run app/manage.py ingredients --check`; rerun if it stopped).
2. **Ben's reviews** (Ben's open choices, below): D125's insect seasons, D126's planting rule, the content list from the topic and methods pages (the plan's wave 5 notes), the two small choices (today's precipitation "—"; 2- and 3-level risk colours).
3. **Wave 6** (plan first, as each track starts): the climate pages (track 6), the tools (track 5: degree-day calculator, oak wilt, freeze dates, calendar; the alfalfa planner and crop GDD outlook), downloads, status and the reference pages (track 7), legacy redirects; the `_estimated`-on-null fix (`<input>_estimated` true where the value is null); the county table's speed (~4.5 s a state); the map's increments (Save image first). Accounts and email (track 8) when SES is set up.
4. **Restart `bin/dev`** after pulling (dependencies changed in wave 1).

**Carried from Phase 6:**

1. **Cropland's follow-ons**, each planned first: potato planting on the grid (needs a soil-DD normal: `last10` from the archive or the rule refitted on air temperature), cropland-weighted summaries and normals, the overlay (Phase 7; Ben's question of serving the 30 m CDL ourselves vs CropScape's map service, D116), models' service areas.
2. Alongside, as answers arrive: models parts C–G and J ([docs/plans/models.md](docs/plans/models.md), each planned first), D100's humidity correction ([docs/plans/humidity.md](docs/plans/humidity.md), step 1: is URMA the right target in Oklahoma). Soil moisture's archive fills when Ben runs the ERA5-Land backfill (TODO.md); soil is otherwise parked for Ben's revisit with Wisconet's station models (Phase 9).
3. Small: a top-level `"biofix"` in a JSON POST body is ignored without a word (only `options.biofix` is read; pre-existing): refuse or read it. `scripts/maggot_normals.py` could carry the fourth flight's freeze table (now from a scratch script; the report gives the recipe). Later (Phase 9): zarr's ~14 ms per array creation dominates test archives; the stored-seasons refresh peaks at ~12 GB over 2 workers on the launch box (under `WORKER_MEMORY`).

**Where things stand:**

- Phases 1–5 have no open boxes. Phase 6 done: steps 1–3 done (the API contract, discovery data, events on model layers); step 4's parts A, B (apple), H (all 19 legacy insects on their sources, D102), I1 and I2 (a report and page for every model) done; step 5 done (D112–D115); step 6 done (soil moisture D110–D111, cropland D116; the archive's ERA5-Land backfill is Ben's); step 7 closed but for G, the end-of-phase review.
- Every model is `beta` and every topic page `status: draft` until launch (D46).
- The API's public docs at `/api/v2/docs` come from `app/api/docs/` (`test_docs` checks completeness and style); public text follows CLAUDE.md's "Writing for the public".
- Jobs: ingest :40, forecast :15/:45, IFS :50, ERA5-Land 6-hourly; the crop stages and seasons, then the maps' precompute, queued after an update or a published run (D108); forecast scores daily 14:25 UTC (D113); past years and downloads Mondays; climatology monthly; `housekeeping` daily.
- Dev environment: `bin/dev` may or may not be running (Ben runs other projects' servers too); a task that needs it asks Ben to start it. The dev archive is full from 2016. gridMET 1996–2025 over Wisconsin in `data/gridmet/`, derived on the archive's basis in `data/climate/gridmet/` (D84); the normals in `data/climate/normals/` (D85); the terrain store built (D6). `rebuild --check`, `pastyears --check` and `climatology --check` were clean on 2026-11-26 after the overnight rebuild.

**Read first in a new session:** this handoff and the newest entries of `tmp/session-log.md`; the current phase's plan; for model work, [docs/plans/models.md](docs/plans/models.md)'s rules, learnings and the part at hand, `tmp/briefs/` and `docs/validation/README.md`; CLAUDE.md's model rules and "Writing for the public"; memory: at most 4 agents at once.

## Ben's open choices

- **Potato planting (D126), Ben 2026-11-26:** smooth the freeze over ~50 km, center-weighted, against frost pockets (wave 6 agent w6-spring building it; D127 to record).
- **Insect seasons (D125, provisional), Ben 2026-11-26:** start each from the same per-cell last-frost determination; Feb 15 (seedcorn maggot) and Mar 15 (crucifer flea beetle) far too early, asparagus not before May. w6-spring writes the design and per-insect offsets for Ben.
- **Ben, 2026-11-26:** content fixes from the topic and methods pages go ahead; today's rain shows the total so far with its time and a clear "not real time" note; 2- and 3-level risk scales take steps of the 5-level palette; the map's data layer gets transparency (harsh colours). Track 5's plan (phase-7-web-app.md) awaits his go.
- **Generation weights** are judgments (TODO.md): the looper's halve the season's only caterpillar peak north of Arlington.
- **The Crop Risk Tool audit's questions for the authors** (`tmp/crt-model-audit.md`).
- **Cabbage maggot transplant timing:** UW's pages against A3422.
- **Spotted wing drosophila** (its report): three trap-seasons that look copied (P Mulch / P Plant Path 2016 and 2018, P Fence / Seaq Hiland 2017: check the field sheets); hold at the peak after it, rather than the fitted decline resting on 2015 alone; an erratum to the journal; newer counts (berries, into October, outside Door County).
- **Early blight:** Pscheidt and Stevenson 1988 seems to give about 400 P-days, not UW's 300 (read the paper).
- **Late blight's start for tomato** needs the site's crop in the runner (Phase 7).
- TODO.md's Phase 6 items.

## Waiting on other people

- **NEWA**, a courtesy email (TODO.md): comparisons on its public station data are published with credit (D98); part H's notes for it (the maggot pages' "BE" labels, western bean cutworm's deployed code, seedcorn maggot's °F studies read as °C·d, the cabbage maggot table's 75 % and "ends 809", the 404 More Info images; from the papers read 2026-11-23: its later cabbage maggot peaks are Jyoti et al.'s spring 50 % plus each flight's length rather than measured intervals, so on Jyoti et al.'s own trap dates its summer peaks come 7–26 days early; its 40 °F base where the paper used 4 °C).
- **Gray leaf spot** on Smith and Webster; soybean Cercospora's wind unit and tar spot's details on Webster; DON's windows on Paul's group; cotton's φ and seed treatment on Noel.
- **Wisconsin trap data**, if UW has it: codling moth (first catch), cabbage maggot and cabbage looper (pheromone traps), the cutworms.
- **Papers** behind library access (part H's list, with DOIs, in TODO.md).

## Before the topic pages go public

Their links to the validation reports (`github.com/uwent/agweather2/blob/main/docs/validation/models/<id>.md`) 404 until `phase-6` merges to `main` and the repository is public: merge, then check them. Recheck wheatscab.psu.edu (down 2026-11-19) and NC State's tarnished plant bug page.

## Ideas, not scheduled

Diagnostic maps (gradient, hour of the day's max and min; Phase 9's wish list); solar days for a national grid (D74); an area average of each cell's results beside the area's weather (D83), if someone needs it. Phase 9's plan holds the backlogs (validation, station networks, ALIVE, the model review).
