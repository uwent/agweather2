# AgWeather v2 — Build Plan

One Django app that replaces the AgWeather API, the AgWeather website, VDIFN and three Shiny apps (Crop Risk Tool, alfalfa, potato volunteer). Target: live before **April 1, 2027**, with the old stack running in parallel until v2 matches it.

This file is where things stand and what's next: the one handoff, Ben's open choices, what waits on other people, and the order of the work. Rewrite the handoff at the end of each session (with an entry in `tmp/session-log.md`), and keep the lists current.

## Where the docs are

<!-- prettier-ignore -->
| Doc | Holds |
| --- | --- |
| [docs/decisions.md](docs/decisions.md) | Why: the recorded decisions (D1–D105) and the questions put to Ben (Q1–Q40). A new decision takes the next D number |
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

## Handoff (2026-11-23)

**Phase 6** (branch `phase-6`), its remaining backend work: [docs/plans/phase-6-frontend-plan-and-data.md](docs/plans/phase-6-frontend-plan-and-data.md), steps 4–7, then the end-of-phase review and Phase 7 (the web app).

**This session (2026-11-23):**

- **Plans reorganized** (after WISP 3's): this file is the handoff; decisions and questions in `docs/decisions.md`; architecture in `docs/architecture.md`; each phase and side plan in `docs/plans/`, which carry status, not handoffs.
- **Part H round 2 (D103):** Ben's ten answers built by agents in worktrees: a normal of each place read by models (`PlaceNormal`, `PlaceForm`; corn borer's one flight where the normal by August 1 is below 1,500), weights per generation, a "present" window (black cutworm), a fixed biofix (western bean cutworm), `tarnished-plant-bug` retired.
- **The papers read in full (D104):** Ben fetched 40 papers and UW's XHT1087 handout; agents read each against its models (reports in `tmp/papers/`), then built Ben's approved changes: cabbage maggot 0.5 (a generation of 1,275 DD40 instead of NEWA's 850; a partial fourth flight ended by fall freezes), seedcorn maggot 0.4 and onion maggot 0.4 (weights), corn rootworm 0.3 (larvae 550, pupa 200), black cutworm 0.4 (Kaster and Showers' outdoor times). XHT1087 gives base temperatures only (the modified average is our reading).
- **Review of the day's work** (reports in `tmp/review/`): cold checks of all 20 changed insects' pages, reports and topic pages (about 60 corrections, no output changes: stale wording from earlier versions, overclaimed sources such as XHT1086 and A3646, dates out of step with the code); a code review of the engine changes, all eight findings fixed (`/risk` now warns when the normal is missing; the one-flight form evaluated only where it applies, halving corn borer's map cost; the fixed biofix enforced in the runner; a run must be given its normal; normals read once per point). The whole suite passes (4,200), pyright clean, `rebuild --check` clean.

**Next, in order** (Ben, 2026-11-23: step 7's profile next, in a fresh session; the rest of the order proposed, see Ben's open choices):

1. **Step 7's launch-box profile**, planned 2026-11-23 (the phase plan's step 7, items E, A–D, F, G; the coverage settled as D105, a mask of the 12 Midwest states and Kentucky with a 50 km buffer; item E done the same day (place normals read over land within 10 km, corn borer 0.4); next A, the mask), first of the engineering, since it can change how maps are stored: a synthetic `upper_midwest` archive, then `manage.py latency` and the jobs. Apple scab's map takes 8 s and fire blight's 19 s over Wisconsin today; the box has 11.7× the cells. Corn borer's map needs the normals over the launch box (Wisconsin only now: elsewhere two flights with a warning). **When the normals are built for the launch box, build them with the terrain store's water mask** (Ben, 2026-11-23): inland lakes carry a lake-cooled normal today (URMA's years have values over them; gridMET's coast rule covers only the Great Lakes), so corn borer's map shows a one-flight patch over Lake Winnebago; fill water cells from land neighbours by the coast rule (`agdata.coast`), bump `normals.VERSION`, and rebuild `last5`, `last10` and `last30`.
2. **Step 5**, site services: changelog and announcements, the API use form, the verification archive, Open-Meteo when NBM is stale, Open-Meteo usage.
3. **Step 6**, new sources: soil moisture (send the ERA5-Land requests early: the CDS queue takes hours) and cropland fractions.
4. **Step 7's rest** and the **end-of-phase review** (code, docs, tests), then Phase 7.
5. Alongside, as answers arrive: models parts C–G and J ([docs/plans/models.md](docs/plans/models.md), each planned first), D100's humidity correction ([docs/plans/humidity.md](docs/plans/humidity.md), step 1: is URMA the right target in Oklahoma).
6. Small: a top-level `"biofix"` in a JSON POST body is ignored without a word (only `options.biofix` is read; pre-existing): refuse or read it. `scripts/maggot_normals.py` could carry the fourth flight's freeze table (now from a scratch script; the report gives the recipe).

**Where things stand:**

- Phases 1–5 have no open boxes. Phase 6: steps 1–3 done (the API contract, discovery data, events on model layers); step 4's parts A, B (apple), H (all 19 legacy insects on their sources, D102), I1 and I2 (a report and page for every model) done; steps 5–7 open.
- Every model is `beta` and every topic page `status: draft` until launch (D46).
- A test reaches for the network: `app/api/tests/test_takes.py::test_a_models_options_and_its_crop_models_are_listed` (frogeye leaf spot) tries an outside address, which pytest-socket blocks, so it passes with a warning; it predates round 2. Find what it calls and give it a fixture.
- The API's public docs at `/api/v2/docs` come from `app/api/docs/` (`test_docs` checks completeness and style); public text follows CLAUDE.md's "Writing for the public".
- Jobs: ingest :40, forecast :15/:45, IFS :50, crop tiers :55, ERA5-Land 6-hourly, past years and downloads Mondays, `housekeeping` daily.
- Dev environment: `bin/dev` may or may not be running (Ben runs other projects' servers too); a task that needs it asks Ben to start it. The dev archive is full from 2016. gridMET 1996–2025 over Wisconsin in `data/gridmet/`, derived on the archive's basis in `data/climate/gridmet/` (D84); the normals in `data/climate/normals/` (D85); the terrain store built (D6). `rebuild --check` was clean on 2026-11-18, before part H's rebuild.

**Read first in a new session:** this handoff and the newest entries of `tmp/session-log.md`; the current phase's plan; for model work, [docs/plans/models.md](docs/plans/models.md)'s rules, learnings and the part at hand, `tmp/briefs/` and `docs/validation/README.md`; CLAUDE.md's model rules and "Writing for the public"; memory: at most 4 agents at once.

## Ben's open choices

- **The order after step 7** (proposed 2026-11-23): steps 5–7 as the gate to the frontend, with models parts C–G and J alongside Phase 7 rather than before it (Ben, 2026-11-17, had put all of step 4 before the frontend).
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
