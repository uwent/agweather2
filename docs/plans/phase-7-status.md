# Phase 7 status: built and on deck

A running summary for Ben, kept current as agents' work merges (newest at the top of each list). The plan and its decisions are in [phase-7-web-app.md](phase-7-web-app.md); the handoff is PLAN.md's. Branch `phase-7` (from `main` after PR #1).

Last updated: 2026-11-27, 03:45 CST.

## Built (merged into `phase-7`)

### Pages

| Page | What it does |
| --- | --- |
| `/` | Place search, three headline maps by month, models in season by crop, saved sites, links by task, data through when |
| `/map` | The map explorer: weather, degree days (presets, biofix, planting), crops and pests; day, range, season, hour; the date slider; map options (smoothing, palette, scale, opacity 80 %); title chip, legend, notes; cell panel with chart and links; county table with CSV; overlays; Share, Save image, GeoTIFF/NetCDF/TileJSON of the view; training areas; climate: compare with normal (normal, departure, percentile; 30/10/5 years), freeze maps (chance by a date, typical dates), counts of days |
| `/climate` | Climate explorer: seven headline climate maps; click or search a location for its climate (the Climate tab's sections) |
| `/sites` | Saved sites (browser storage), cards with weather and top risks, groups, import/export CSV, today's rain so far |
| `/sites/{lat},{lng}` | Overview, Weather, Models, Degree days ("since a date" saved with the site), Climate (this season, temperature against normal, frost and freeze, this month's counts, normals), Data |
| `/sites/{lat},{lng}/models/{id}` | A model at a site: answer, stacked chart, NEWA-style table, settings saved to the site, guidance |
| `/sites/models/{id}` | One model across all saved sites |
| `/models`, `/models/{id}` | Catalog by crop; generated model pages (season opening rule, D128) |
| `/topics`, `/topics/{id}` | Pest and disease pages (sentence-case titles) |
| `/methods` | Generated methods: sources, corrections, variables in plain words; "How normals are made" (`#normals`): periods and their years, gridMET's fit, daily normals, totals and percentiles, the 12 counts, freeze odds, the 50 km area average, and a table of each insect's season-opening rule |
| `/tools` | Index of built tools |
| `/tools/degree-days` | Calculator: place picker, up to 3 settings, through a date or the forecast, projection, map link |
| `/tools/freeze` | Freeze dates and odds: this year against typical, cards per threshold, odds chart, look up a date, crop killing freezes, past years |
| `/tools/oak-wilt` | DNR's restricted period from 231 °F·d through July 15, model level and share of beetle flight (`flown`), map, chart, DNR periods |
| `/tools/crop-gdd` | Crop GDD outlook: the answer in a sentence (reached, forecast, projected with its range and the freeze chance before it); GDD since planting over the normal and comparison years with stage lines, over the fall freeze chance; a stage table. Corn through corn-stages, other crops by preset and a typed maturity |
| `/tools/potato-volunteer` | Potato volunteer survival: a winter's hours of soil below 27 °F at 2, 4 and 8 in and the survival risk at a place, in words and a table of when each depth reached 120 hours; the winter's map (risk or hours); stacked charts of risk, hours and soil and air lows; management advice |
| `/tools/alfalfa` | Alfalfa cutting planner: GDD since the last cut (or green-up) against the 900–1,100 window with dates reached or ahead; the season plan by interval or number of cuts, cut cards you can move, hold and remove, the fall rule against past years' killing freezes, a sawtooth chart over the freeze chance |
| `/calendar` | Day-of-year calendar, 1900–2100, printable |
| `/data` | Weather at up to 50 locations; maps as data files with an exact size estimate; yearly files with R and Python snippets |
| `/status` | Sources on time or late, forecast, gaps in the last 30 days, outages; refreshes every 60 s |
| `/changelog`, `/api-use` | Filter by kind, entry links; announcement banner on every page; the API-use form redesigned |
| `/about`, `/accessibility`, `/contact` | Drafts for Ben (`content/pages/*.md`, `status: draft`; five "For Ben" notes on About) |
| `/glossary` | A–Z with filter; terms link here from their pop-ups |
| Legacy URLs | v1 and VDIFN redirects (302 now; one setting for 301 after four weeks), location and year carried to the tools; retired models to their topics |

### Backend and data (this phase)

- Crop models and `/degree-days` project from a planting or start date past the forecast (a spring reader planning ahead; points into next year read the archive, not Open-Meteo); `biofix=` on the crop-stage models is the planting date (a different `planting_date` beside it is refused); count departures' colours centred on 0.
- The alfalfa planner `GET /api/v2/models/alfalfa-growth/plan` (D129: the Shiny tool's scheduling, 15 parity cases exact; the season from the last spring killing freeze to the 1-in-10 fall one; the fall rule checked against each year's own freeze; ~0.2 s a plan); `meta.summary.stages` on crop-model runs; stored counts listed on `/layers`; routes for the three P1 tools.
- D124 percent outputs; D125→D128 insect seasons opening on the area's normal degree days, the crop's stage or the calendar; D126→D127 potato planting from the area's 28 °F freeze (50 km); apple scab 0.2 (no interpolated wet temperature); oak wilt 0.3 (`flown`).
- Null inputs no longer counted estimated or missing; potato volunteer's falling-risk milestones; unknown POST body fields refused (422).
- County table from the tiles' map (~0.05 s a state); `/grids`/`/maps`/`/summaries` `region=` limited to the coverage's states.
- RTMA precipitation's level label (since 2020-08) read: the newest hours' precipitation no longer lags 7–8 h; 2021-03-12 and 2022-09-21 refilled.
- Downloads: an explicit offered list (soil moisture, wet hours, degree hours, day/night rain, water balance added; orphans pruned); 674 files rebuilt (5.1 GB).
- Climate endpoints: threshold units, empty `vars=`, a day's browser caching; `/status` gains `gaps`.
- Risk colours by level name on every scale.

## On deck (in order)

1. **Running now:** review round 2 (the P1 tools and normals; round 1's refactors); backend fixes (crop runs projecting from a future planting date, corn-stages ignoring `biofix=`, the Madison cell's degree days by year, count departures' colour scale).
2. **Next:** review round 2 over waves 9–10 (the climate pages and the P1 tools); a full Playwright and CI run.
3. **Reviews** (Ben, 2026-11-26): periodic review agents over what's been built (bugs, refactoring, duplication); findings and fixes below.
4. **Done overnight:** the map explorer reads counts from `/layers`; a keyboard spec over every tool (focus outlines fixed on the place search fields; focus kept when a place is found). **Small:** the API serves the current winter's potato volunteer map before January 1 though the model says it appears then (the page waits); count departures' colour scale ([0, 6.25] for days ≥ 90 °F, not centred on 0); climate endpoints' speed on a quiet server (`/climate/compare` 13 s under load); the legend at full strength while the map is at 80 % (Ben's call).
5. **Ben:** **the Madison cell (and the row beside it) is treated as lake water by URMA itself since 2017**, so its degree days ran 300–380 below Madison's airport in 2017–2020 and about even since 2021 (cool maxima, warm minima, changing over the years; the airport's own cell tracks the station within ~2 % every year): leave the data and (b) suggest `radius` or `land_only` on pages when a location's cell is mostly water (Madison 24 %), (c) note that normals and projections at inland-lake cells mix the periods (ties to the Lake Winnebago normals question), (d) record the 2017 and ~2021 changes in a weather validation report — which? The alfalfa planner's season end stays on the typical 1-in-10 date even when this year's own freeze came later (Nov 24 and 26 in 2026 and 2024) — as D129's rule says, but readers may ask; the alfalfa planner's last cut lands on the 1-in-10 24 °F date (Nov 1 at Madison), later than most growers cut: should the season end earlier? About's drafts and credits; oak wilt's wording with DNR (their 2026 guidelines don't mention 231 °F·d); restart `bin/dev` after pulling; the interface design pass (map explorer plus bespoke model and topic pages in WISP 3's map-plus-feed frame).
6. **Later:** accounts and email (track 8, when SES is set up); Phase 9's observed phenologies.

## Data jobs

- Ingredients rebuild for D127, apple scab 0.2, oak wilt 0.3 and D128, all years (`tmp/w8-ingredients2.log`); blight and potato maps answer "updating" until done.

## Reviews

### Round 1, frontend (2026-11-27; merged)

Fixed: **`pnpm test` exited 1 though every test passed** (charts loading ECharts after a component test ended threw in jsdom; would have failed CI; a stand-in chart in tests, and the suite runs in ~30 s instead of 73 s); **oak wilt kept the first place's projection for a second place**; two map explorer races (an older cell read could fill the panel; a superseded series request ended the new one's loading state); rain so far outside our area used the grid's date, not the place's own; glossary links landed above their entry (the flaky smoke test; 16/16 after); the freeze tool's own temperature didn't follow a units switch; "1 days ago"; typed examples in error messages quoted. Refactors: one request queue (`lib/slots.ts`), one `siteModelUrl` and `longDate`, shared `rounded()` and `columnsOf()`, page links from `lib/routes`.

Left, recommended: move `lib/sites/request.svelte.ts` and `Failed.svelte` (used by 20 files) to `lib/` when no pages are being built; radar's own tile decoding (colour management on, no `bitmap.close()`) should share dataTiles'; the freeze tool can briefly show the previous place's coldest low; five `plural()` helpers and five month-name arrays; the map explorer page (870 lines) has no component test; two smoke tests wait 3.5 s each for the form timer (`page.clock`); the axe "public pages" test scans 11 pages and is near its 30 s limit under load.

### Round 1, backend (2026-11-27; merged)

Fixed: **the Open-Meteo fallback stopped reading its cell cache once a request's 10 s budget ran out** (or after one failed fetch), so later points in a multi-point request (the feed, `/data`, projections) lost their forecast fill even for cached cells — cache reads now always happen, with a test; `region=`'s unknown-region error now quotes its examples; one `shown_spec` and one `crops_named` (were copied three times); the home page's state list read from the coverage preset; stale comments.

Left, recommended: `seasonopens` stores a never-reached event as Dec 25, not Dec 31 (cosmetic, every season ends by Oct 31; fix at the next version bump), and smoothing averages "never" with real days near the edge of an event's range (harmless now; a sentence for D128); `/data` lists states with half their cells covered while `region=` takes the preset's states (agree under the launch box; one rule); `_site_models` overlaps `model_entries`; Caddy's `/api` redirect stays 302 when Django's go 301; `NOT_OFFERED`'s reason for `temperature_mean_rain_7am_to_7pm` applies equally to the offered humid-hour temperatures (Ben: offer both or neither?).

Checked without findings: legacy redirects (open-redirect safety, degree-day formats), `/status` gaps, the changelog and API-use form, downloads, climate routes, summaries, heavy slots, `/risk`, the season and planting logic, infra. Pages answer in 40–95 ms warm.
