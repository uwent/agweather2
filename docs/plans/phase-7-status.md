# Phase 7 status: built and on deck

A running summary for Ben, kept current as agents' work merges (newest at the top of each list). The plan and its decisions are in [phase-7-web-app.md](phase-7-web-app.md); the handoff is PLAN.md's. Branch `phase-7` (from `main` after PR #1).

Last updated: 2026-11-27, 02:10 CST.

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
| `/calendar` | Day-of-year calendar, 1900–2100, printable |
| `/data` | Weather at up to 50 locations; maps as data files with an exact size estimate; yearly files with R and Python snippets |
| `/status` | Sources on time or late, forecast, gaps in the last 30 days, outages; refreshes every 60 s |
| `/changelog`, `/api-use` | Filter by kind, entry links; announcement banner on every page; the API-use form redesigned |
| `/about`, `/accessibility`, `/contact` | Drafts for Ben (`content/pages/*.md`, `status: draft`; five "For Ben" notes on About) |
| `/glossary` | A–Z with filter; terms link here from their pop-ups |
| Legacy URLs | v1 and VDIFN redirects (302 now; one setting for 301 after four weeks), location and year carried to the tools; retired models to their topics |

### Backend and data (this phase)

- The alfalfa planner `GET /api/v2/models/alfalfa-growth/plan` (D129: the Shiny tool's scheduling, 15 parity cases exact; the season from the last spring killing freeze to the 1-in-10 fall one; the fall rule checked against each year's own freeze; ~0.2 s a plan); `meta.summary.stages` on crop-model runs; stored counts listed on `/layers`; routes for the three P1 tools.
- D124 percent outputs; D125→D128 insect seasons opening on the area's normal degree days, the crop's stage or the calendar; D126→D127 potato planting from the area's 28 °F freeze (50 km); apple scab 0.2 (no interpolated wet temperature); oak wilt 0.3 (`flown`).
- Null inputs no longer counted estimated or missing; potato volunteer's falling-risk milestones; unknown POST body fields refused (422).
- County table from the tiles' map (~0.05 s a state); `/grids`/`/maps`/`/summaries` `region=` limited to the coverage's states.
- RTMA precipitation's level label (since 2020-08) read: the newest hours' precipitation no longer lags 7–8 h; 2021-03-12 and 2022-09-21 refilled.
- Downloads: an explicit offered list (soil moisture, wet hours, degree hours, day/night rain, water balance added; orphans pruned); 674 files rebuilt (5.1 GB).
- Climate endpoints: threshold units, empty `vars=`, a day's browser caching; `/status` gains `gaps`.
- Risk colours by level name on every scale.

## On deck (in order)

1. **Running now:** review round 1 (frontend); the alfalfa page; backend fixes (crop runs projecting from a future planting date, corn-stages ignoring `biofix=`, the Madison cell's degree days by year, count departures' colour scale).
2. **Next:** a keyboard spec over the tools; the map explorer reading the counts from `/layers` instead of its own copy.
3. **Reviews** (Ben, 2026-11-26): periodic review agents over what's been built (bugs, refactoring, duplication); findings and fixes below.
4. **Small:** the API serves the current winter's potato volunteer map before January 1 though the model says it appears then (the page waits); the map explorer reading counts from `/layers`; a flaky smoke test (the glossary not always scrolled to a linked term); count departures' colour scale ([0, 6.25] for days ≥ 90 °F, not centred on 0); climate endpoints' speed on a quiet server (`/climate/compare` 13 s under load); the legend at full strength while the map is at 80 % (Ben's call).
5. **Ben:** the alfalfa planner's last cut lands on the 1-in-10 24 °F date (Nov 1 at Madison), later than most growers cut: should the season end earlier? About's drafts and credits; oak wilt's wording with DNR (their 2026 guidelines don't mention 231 °F·d); restart `bin/dev` after pulling; the interface design pass (map explorer plus bespoke model and topic pages in WISP 3's map-plus-feed frame).
6. **Later:** accounts and email (track 8, when SES is set up); Phase 9's observed phenologies.

## Data jobs

- Ingredients rebuild for D127, apple scab 0.2, oak wilt 0.3 and D128, all years (`tmp/w8-ingredients2.log`); blight and potato maps answer "updating" until done.

## Reviews

### Round 1, backend (2026-11-27; merged)

Fixed: **the Open-Meteo fallback stopped reading its cell cache once a request's 10 s budget ran out** (or after one failed fetch), so later points in a multi-point request (the feed, `/data`, projections) lost their forecast fill even for cached cells — cache reads now always happen, with a test; `region=`'s unknown-region error now quotes its examples; one `shown_spec` and one `crops_named` (were copied three times); the home page's state list read from the coverage preset; stale comments.

Left, recommended: `seasonopens` stores a never-reached event as Dec 25, not Dec 31 (cosmetic, every season ends by Oct 31; fix at the next version bump), and smoothing averages "never" with real days near the edge of an event's range (harmless now; a sentence for D128); `/data` lists states with half their cells covered while `region=` takes the preset's states (agree under the launch box; one rule); `_site_models` overlaps `model_entries`; Caddy's `/api` redirect stays 302 when Django's go 301; `NOT_OFFERED`'s reason for `temperature_mean_rain_7am_to_7pm` applies equally to the offered humid-hour temperatures (Ben: offer both or neither?).

Checked without findings: legacy redirects (open-redirect safety, degree-day formats), `/status` gaps, the changelog and API-use form, downloads, climate routes, summaries, heavy slots, `/risk`, the season and planting logic, infra. Pages answer in 40–95 ms warm.
