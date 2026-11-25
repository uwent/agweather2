# AgWeather v2 — Build Plan

One Django app that replaces the AgWeather API, the AgWeather website, VDIFN and three Shiny apps (Crop Risk Tool, alfalfa, potato volunteer). Target: live before **April 1, 2027**, with the old stack running in parallel until v2 matches it.

This file is where things stand and what's next: the one handoff, Ben's open choices, what waits on other people, and the order of the work. Rewrite the handoff at the end of each session (with an entry in `tmp/session-log.md`), and keep the lists current.

## Where the docs are

<!-- prettier-ignore -->
| Doc | Holds |
| --- | --- |
| [docs/decisions.md](docs/decisions.md) | Why: the recorded decisions (D1–D123) and the questions put to Ben (Q1–Q41). A new decision takes the next D number |
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

**Next, in order:**

1. **Wave 4** (named in the plan): the backend fixes wave 3 found (probability models return fractions but declare '%': tar spot's 0.61 shown as '%', so each needs a version bump; insects have no season, so `/risk` lists 27 models "in season" in November while home shows 3; `/risk` lists retired models; names such as "Colorado Potato Beetle (Adults)"); the map explorer's phone sheet, county table and links; a model at a site with risk sparklines; the model catalog and pages.
2. **Ben, small:** today's precipitation shows "—" (the day isn't over; or "not counted yet"); 2- and 3-level risk scales borrow the probability colours (or add the API's BuYlRd_2/3 as tokens).
3. **Restart `bin/dev`** after pulling: dependencies changed in wave 1 (a stale Vite serves blank pages).
4. Then the rest of tracks 2 and 3, and tracks 4–8 as the plan orders them; Phase 6's carried items (models C–G and J, humidity, cropland's follow-ons) alongside.

**2026-11-26: the review's open items** (Ben approved the recommendations; three built by agents in worktrees, reviewed and merged; suite 4,435 passed, 90 skipped, 3 min 41 s; pyright clean). Record: the phase plan's "Code review", last item.

- **IFS reads concurrently** (omfiles' async reader, 64 ranges in flight, each pinned to its file's ETag, per-request timeouts and retries, a 20-minute deadline on the whole read): the launch box's read **80 s, from ~3–4 h**, values equal to the old reader's. It mattered beyond the backfill: the worker runs one job at a time, and every 6-hourly run was a full read.
- **Heavy computations wait for a slot** (`api.heavy`, one per process; else 503 `busy`); requests past the time limit are charged as the limit passes and in the minute they finish (they were charged to their arrival minute); a client with 2 requests running past the limit gets 429. New settings `API_HEAVY_SLOTS`, `API_HEAVY_WAIT`, `API_OVERRUN_LIMIT` (compose and `.env.example`). The heavy threshold (50 million cell-steps) is an estimate: retune from the server's logs.
- **Requests open stores read-only**; a variable a store lacks reads as missing. Five other readers that added arrays outside the lock fixed with it.
- **Moved to Phase 7:** the flag for days missing past the gap fill (every model, not just apple scab and fire blight) and the projection's speed measured mid-season.

**Overnight 2026-11-25/26: the end-of-phase review** (four agents in worktrees: agdata/agmodels code, app code, documentation, tests; then live measurements). ~30 fixes, each checked against the code and tested; ~70 stale doc facts corrected; the suite 4,411 passed in 3 min 46 s at `-n 4`. The dev archive was rebuilt (`rebuild --stale`: soil moisture's daily variables and apple scab's ingredients, 11 min), its past-years copies built again (24 min, 10 years), and gridMET's years re-derived under the coverage mask (2.2 h). Highlights: `AlreadyEnqueued` failing the ingest and forecast jobs (seen in `bin/dev`); `manage.py verify` failed from the command line in every mode; `forecast.publish` could delete the run readers were on; coverage-mask leaks in three direct writers; a block-pool race adding arrays; `test_takes`'s network leak hid a wrong assertion (leaks now fail). Measured: the verification copy 3.75 s over the launch box; a forecast run 14 min; a day's update 173 s warm; `latency` 12 of 12; IFS's read over the launch box ~4 h (now 80 s, above); the projection 1.4 s.

**2026-11-25: step 5, the site services, built by four agents in parallel** (plans in `tmp/step5/`, approved by Ben 2026-11-24; each built in its own worktree and merged into `phase-6`; the whole suite 4,376 passed after the last merge). `main` was fast-forwarded to `phase-6` first (152 commits) and CI fixed there (CCI kernel parity and sweep snapshots compared within a few ulps of CI's math library).

- **Changelog and the API-use form (D112):** a new `updates` app; `/api/v2/changelog`, `/changelog.atom`, stub pages `/changelog` and `/api-use` (Phase 7 designs them, and adds the banner, a nav link and the emails).
- **Verification archive (D113):** every published long run's lead days 1–10 kept 45 days (~5 GB), scored daily into `ForecastScore`, `manage.py verify`, `/up`'s `forecast.verification` with a lead-1 alarm at 3 °C. Not measured yet: the copy's time under the lock at publish over the launch box (estimated tens of seconds). Scoring 01/07/19Z is new (D39/D49 were fitted on 13Z): compare with `verify --report --by-cycle` once a week of scores is in.
- **Open-Meteo when NBM is stale (D114):** points in the box take Open-Meteo's forecast past the observed hours; a failure is a warning, not a 503 (soil too). Fixed with it: `cells_days` took each zone's day kinds from its first cell. CLAUDE.md's rule on fetching in a request updated (Ben). Worth a changelog entry once deployed.
- **Cropland fractions (D116, step 6):** `data/cropland.zarr` built here from the CDL's 2021–2025 (zips kept in `data/cdl/`, 9.7 GB; 8 min with 4 workers); each crop's mean and any-year share and cultivated land per cell. Checked over Wisconsin: cultivated within 0.14 points of NASS's Cultivated Layer; five-year means above NASS's planted acreage (corn +7%, soybean +5%, potato +13%), so `_mean` is a relative share. `--box upper_midwest` is needed here (`SERVICE_BOX` is `wisconsin`). Two real-data bugs found and fixed: 2025's file has a wider extent, and only 2025 classes the Great Lakes as water.
- **Open-Meteo usage (D115):** every attempt counted by day (`fetch_counted`, a guard test holds every caller to it); billing month from the 12th; warnings at 80% or on pace to pass, in admin, `/up`, `jobs`, the dashboard and the log.

**Earlier (2026-11-24 and 25): step 7's launch-box profile, B through D** (numbers in the phase plan's step 7; the story in `tmp/session-log.md`):

- **The grid in blocks (D106) and on a lattice (D107):** every job over the grid works in 256-cell blocks in a pool of worker processes (`BLOCK_WORKERS`); the coverage window is the mask's extent rounded out to a grid-wide 256-cell lattice (768 × 1280), blocks trimmed to their covered cells, downloads cropped to the extent. Four workers did less than two on this 4-core machine; the r7i.2xlarge is 4 cores too, so measure 2–3 there.
- **Jobs (D108):** hours fetched every hour, the maps' updates only when due (a day over, 6 hours, or before a forecast build); the forecast derived in parts over the coverage; running totals and ingredients faster (`cumsum_days`). A day's update 356 → 196 s, a forecast run 21 → ~15 min.
- **The crash and D109:** the request profile crashed WSL (apple scab's and fire blight's maps reached 60 GB). A map is offered only within a budget of storage and compute. Safety nets: on-request maps a block at a time, one computation per map, container memory limits (`WEB_MEMORY`, `WORKER_MEMORY`). Apple scab, fire blight and red crown rot (mid tier) keep their seasons stored (`agdata.seasonmaps`): maps 187 s / 242 s / 7 s → under a second, ~4 min of job time a refresh; each shows nothing out of its season.
- **Requests:** custom degree-day season map 46 s → ~0.5 s and season grids 26 s → 0.5 s (gap fills skipped the cells outside the coverage; a sum in the kernel); stage-anchored accumulations cell by cell (early blight 2.4 s a day). **Every model's and 13 weather layers' latest map is precomputed** after each update into a disk cache shared by the web workers (`ops.precompute`, the one list; 64 maps in 24 s, 10 MB). Phase 7 adds the next 7 forecast days to its `DAYS`.
- **D6 done:** the stitch copies the archive's hours as stored and keeps its running totals to the extent; the rollup's apple scab and Cattle Comfort Index features compiled (`agmodels.features_grid`, bit-identical: a block-month 52.7 → ~30 s on one core); the ingredients' gap fill only where there's an interior gap; IFS put on the window 48 hours at a time (was every hour of a run at once, ~14 GB) and a build's soil a day at a time; the stitch keeps the run's IFS soil after the archive's last hour of it, so an IFS read no longer restitches. The stitch 7.3 → 4.1 min.
- Scratch: `tmp/launchbox` (the profile archive, January–August 1, 2025, a published run) and the database `agweather2_launchbox`; drop the database when step 7 is done.

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
