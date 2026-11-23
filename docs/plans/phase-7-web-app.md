# Phase 7: Web app, accounts and email — sketch (XL; WISP 3's frontend is the source to port)

The pages in `docs/frontend.md`, on Phase 6's data and API, with sign-in and email (a separate phase until Ben merged them, 2026-11-06: accounts are pages too, and WISP 3 has both to port).

From Phase 3 and docs/landscape.md: a model view with weather inputs, output and risk on one time axis (the Crop Risk Tool's view) through observed, forecast and projection; insect views with degree days, life stage and crop risk to the end of the year (U2U-style projection from the climatology built here); topic pages and model pages with the interactive explorer; custom DD maps with any thresholds and biofix.

Insects (D36; Ben, 2026-10-29: show as much as is useful without hiding how it's derived): the map colors by risk, by any life stage's phenology (activity or fraction complete), or by days to the next action window or risk threshold (which needs the forecast and projection). The chart switches between phenology and risk, with risk drawn as each stage's weighted share stacked to the total so the step from one to the other shows, and action windows as bands.

Map explorer with the WebGL data-tile layer and an elevation hillshade beneath it (D6's leftover: drawn as images from NHDPlus's `shdrelief` or the terrain store's 30 m DEM, never served as data), sites dashboard and both feeds, charts and downloads, model catalog and about pages (text and citations; sweeps in P1), climate endpoints (`docs/api.md`, Climate: normals, compare, frost, history, and normal and departure layers; Q34–Q35), climatology cubes and current-vs-normal comparisons (D22: nClimGrid-daily 1991–2020 and gridMET reduced to day-of-year statistics on the grid, plus 5- and 10-year normals from the archive), DOY calendar, changelog, glossary and notes from WISP 3; accessibility and keyboard tests on every page.

The methods page and model pages render Phase 6's methods data (above).

**Accounts and email:** allauth sign-in by link or code, synced sites, settings (units, beta models, alerts, service updates), daily digest and event alerts, email layout ported from WISP 3, BCC announcement to current subscribers. Site groups and preferences (Phase 6 A) sync to the account.

**Moved from Phase 6 (2026-11-12).** First, the frontend's design:

- [ ] **Site groups and inherited preferences** (Ben, 2026-11-06; F3, F11, F12): preferences at three levels, all sites > group > site, the group level optional. What they hold is still open; likely which crops and models to show or hide, plus map view and chart defaults. A site in several groups gets the union of its groups' choices (a site in "corn" and "soybean" groups shows both crops' models) unless the site sets its own; "Reset to my defaults" at each level. A group's map view frames its sites and labels them. Design the data model (browser storage first, the same shape as Phase 7's Django models) before Phase 7's sites pages.
- [ ] Architecture decisions, recorded as D#: Inertia props against API fetches per page; URL state for the map and charts; the map component (data tiles, overlays, the saved-image export from late-blight-db); browser storage and its sync; how WISP 3's base (layout, tokens, charts, units, glossary, accessibility tests) is ported.

Then the tools that compose Phase 6's data, each with its page (specialized endpoints are added as the page needs them):

- [ ] **Alfalfa season planner** (F5): from a location, a weather year and cut dates (some locked) or a target interval or count, the schedule with each cut's days and GDD, the fall rule (< 360 or > 900 GDD before the killing freeze) and the killing-freeze odds by date; a pure function in `agmodels` beside `alfalfa-growth`, on the projection (D63) and `/climate/frost`, served by a small endpoint. S–M.
- [ ] **Crop GDD outlook** (U2U Corn GDD, CliGrow): `/degree-days` with projection plus `/climate/normals?dd=` with its spread, `corn-stages`' silking and black layer by maturity, first fall freeze odds, comparison years (before the archive from Open-Meteo, its source named, D87). Mostly composition of the above; S once they exist.
- [ ] **Insect layers by time to act** (Insects, above, D36): days to the next action window or risk threshold, through the forecast and projection. M. Its backend is Phase 6's events on model layers.
- Moved 2026-11-17 to Phase 6's remaining backend work, step 4 (the write-ups, before the frontend). **Model page content in structured form:** what to do at each risk level (NEWA's management guidance), the susceptible stages and the valid-use warning (the Crop Risk Tool's), each model's acknowledgments; in its Markdown front matter or spec, served by `/models/{id}`. M (content for ~50 models; the model review's content step, started here). Starts here and continues alongside the later tracks; it's writing, not code.

- **Exit:** beta users on the new site; digests and alerts verified on staging for test sites.
