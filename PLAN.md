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

## Handoff (2026-11-26, late night)

**Phase 7, the web app** (what's built and on deck: [docs/plans/phase-7-status.md](docs/plans/phase-7-status.md), kept current through the night; branch `phase-7`; `phase-6` merged to `main` as PR #1, CI green): [docs/plans/phase-7-web-app.md](docs/plans/phase-7-web-app.md). Claude orchestrates; agents build in worktrees from `phase-7` (briefs in `tmp/briefs/wave6-common.md`, `wave7.md`, `wave8.md`, `wave8b.md`), at most four at once.

**Done before this session:** waves 1–5 (the base, DataMap, `/map`, `/sites`, the site page and its tabs, groups and preferences, `/models` and model pages, a model at a site, the feed, topics, `/methods`, D124–D126). See the phase plan's Waves.

**This session (2026-11-26, evening–night):** tracks 5, 6 and 7 planned (Ben: all as recommended, with his answers recorded after each plan); wave 6 (backend fixes: null inputs no longer estimated or missing, the county table cut from the tiles' map, unknown POST fields refused, potato volunteer's falling milestones; the map's Save image, opacity 80 %, downloads of the view, training areas; D127 planting from the area's freeze; content fixes, today's rain so far, risk colours); stub routes for every page of tracks 5–7; wave 7 (legacy redirects, `/tools`, the place picker, `/calendar`, `/tools/degree-days`, the climate backend and shared charts, `/tools/oak-wilt` with oak wilt 0.3's `flown`); wave 8 (`/data` and the downloads list, About/Accessibility/Contact drafts and `/glossary`, risk colours by name on every scale, retired models' links to topics, the RTMA precipitation label bug, D128 insect seasons opening on warmth, crop stage or calendar). Suite 5,028 passed; vitest 624; Playwright 104; pyright and svelte-check clean.

**Data tonight:** precipitation refilled for 2021-03-12 and 2022-09-21 (RTMA; 2020-03-21 has no source); downloads rebuilt (674 files, 5.1 GB, FORMAT 4); then `climatology` (the season-opening maps, D128) and `ingredients` (all 11 years, for D127, apple scab 0.2, oak wilt 0.3 and D128; ~3 h) running, log `tmp/w8-ingredients.log`. Blight and potato maps answer 503 "updating" until it's done. **Ben: restart `bin/dev`** to pick up the RTMA precipitation fix (the running worker still lags 7–8 h on precipitation) and the merged code.

**Next, in order:**

1. **Check the rebuild** (`ingredients --check`, `climatology --check`; rerun if stopped).
2. **Ben's reviews:** About's five "For Ben" notes and the credits (`content/pages/about.md`, `status: draft`); oak wilt's wording with DNR forest health staff (DNR's 2026 guidelines don't mention 231 degree days); the legend at full strength while the map is at 80 % (or match it).
3. **Wave 9** (plans approved): the freeze tool (on the shared climate core); the site page's Climate tab (6.2); climate on `/map` (6.3); `/climate` as a climate explorer (map, click a location for the charts; Ben) and `/methods#normals` (6.4–6.5); `/status` and the changelog's announcement banner (7.2–7.3); then the P1 tools (crop GDD outlook, potato volunteer page, the alfalfa planner's backend and page). Small: `/grids?region=` should take only the coverage's states (it answers for 19 more, mostly empty); remeasure the climate endpoints on a quiet server (`manage.py latency`; 1–4 s under load, mostly reading the 30 years, plus 0.7 s for the ETag's stamp).
4. **Interface design (Ben, after this wave settles):** a general-purpose map explorer plus a page per model and topic tailored to its inputs and interpretation, in WISP 3's map-plus-sidebar-feed frame for one or more sites or none (phase plan, "Ben, 2026-11-26 (later)").
5. Accounts and email (track 8) when SES is set up.

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

- **About page** drafts and credits; **oak wilt** wording with DNR (above).
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
