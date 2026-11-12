# Frontend spec sheet

Drafted 2026-11-06, before Phase 6's architecture decisions. What the site is for, what it does, how its pages are laid out and how they look and behave, with a review of peer sites and what each feature needs from the API. PLAN.md holds the decisions (D#) and the work list; `docs/api.md` is the API contract the pages read from. Where this file proposes something that needs a decision, it's listed under Open questions (F#) rather than decided here.

Legend for the API column throughout: **✓** served by `/api/v2` today; **◐** served with client-side work or several requests; **○** in the API contract but not built (mostly Climate, Phase 6); **✗** needs new API or data work; **—** frontend only (a third-party service, static content or browser state).

## Objectives

AgWeather v2 replaces six sites with one: the AgWeather website, VDIFN, the Crop Risk Tool, the alfalfa tool and the potato volunteer map (and the v1 API behind them). A reader should be able to answer, for any place in the Upper Midwest (and with Open-Meteo, any US point):

1. **What has the weather been, and what's coming?** Hourly and daily weather, totals and degree days, observed through the 11-day forecast (D43), and past it a projection from earlier years (D63).
2. **What does it mean for my crop?** Disease risk, insect stages and risk, crop stages, each with how it was worked out, its citations and its limits.
3. **Where is it happening?** Every weather variable, degree-day setting and model as a map, for any day or range.
4. **How does this year compare?** Against last year and normal, with frost and freeze odds (Phase 6's climatology).
5. **Can I get the numbers?** A CSV of anything on screen, GIS files of any map, yearly NetCDF downloads and the API.
6. **Can it tell me?** A daily email and alerts when a threshold is crossed or forecast to be (Phase 7).

### Readers and their tasks

<!-- prettier-ignore -->
| Reader | Typical visit | What the site must make easy |
| --- | --- | --- |
| Grower | In season, on a phone, between fields: is it time to spray, scout or cut? | Their saved sites first, today's risk in words and color, the forecast's effect, and the action threshold |
| Crop consultant | Weekly, several clients' fields: which fields need attention? | Many sites at once, one model across them, CSV for reports |
| Extension educator | Writing a newsletter or pest alert: where is a pest's flight now? | A clean map with title, legend and date to paste or link (`/maps/{layer}.png`), and a sentence of interpretation |
| Agency staff (DATCP, DNR) | Daily or weekly reports: degree days at fixed points, maps for the state | Stable URLs, tables of totals, GeoTIFF and tiles for GIS |
| Researcher | Seasonal: download a variable for a region and years | Grid and point downloads, methods, citations, the API |
| Gardener, general public | The day-of-year calendar, the GDD map, "when's the last frost?" | A plain page that answers one question fast |

### Principles

- **Location first, not station first.** Every peer that started from stations (NEWA, Enviroweather, Wisconet, Veg Path's seven places) makes the reader find the nearest one; our data is a 2.5 km grid, so a click, a search or "my location" is the whole step.
- **The map and the point are two views of the same thing.** Any map leads to its value at a point (click), and any point view leads back to its map.
- **One model, one answer.** A model's value is the same on the map, the site page, the email and the API, because they all read `agmodels` through `/api/v2` (D57: the frontend is the API's first client).
- **Show where each number came from.** Observed, forecast, projected, estimated and missing look different everywhere (D45, D56), with a count ("includes 3 estimated days").
- **Guidance, not a guarantee.** Each model's output comes with what it predicts, its valid region and season, and what to do at each risk level, with the research behind it.
- **Shareable state.** The URL holds the view (layer, date, settings, location), so a link reproduces what the sender saw.
- **No account needed** to use anything except email and synced sites (Phase 7). Saved sites live in the browser until the reader signs in.
- **Fast on a phone in a field.** Pages work at 320 px wide and over a slow connection; the map's colors change in the browser without new requests.
- **Accessible (WCAG 2.1 AA)**, light and dark, keyboard throughout, with a table and a text summary for every chart (as WISP 3).

## Feature set

Priorities follow project-plan.md's launch table (P0 for April 1, 2027; P1 during the 2027 season; P2 after). "Replaces" names what retires when the feature ships.

### Map explorer (P0; replaces VDIFN, the v1 site's map pages, the alfalfa tool's map, the potato volunteer map)

<!-- prettier-ignore -->
| Feature | Replaces or from | API |
| --- | --- | --- |
| Layer picker by group: weather (63 layers, daily and hourly), running totals, degree days for any setting, models (49), later climate | v1 Weather and Thermal Models, VDIFN | ✓ `/layers` |
| Model layers filtered by crop, then pest or disease, with each model's outputs (risk level, risk value, a stage, an output) and options (irrigation, planting) | VDIFN's crop → model selects | ✓ `/layers`, `/models` |
| One day or hour; a range reduced by sum, mean, min or max; "season to date"; biofix for degree days | VDIFN date range, v1 maps | ✓ tiles `{time}` and `stat` |
| Date scrubber with −7, −1, +1, +7 and Today, playing as an animation (U2U's Animations tab) | alfalfa tool, U2U | ✓ a tile set per step; ◐ prefetch to animate |
| Smoothing: 7-, 14- or 28-day mean (or sum) ending on or centered on the date (D81) | alfalfa tool | ○ `roll=` on tiles and `/maps` (D0) |
| Palette and scale (default, auto, or low and high) changed in the browser | VDIFN palettes, D73 | ✓ `/palettes`, data tiles |
| Click a cell: its value, the cell's outline, and a panel with the recent days, the forecast and a chart, leading to the site page | VDIFN popup, alfalfa "Selected grid" | ✓ `/locate`, `/weather/daily`, `/models/{id}/run` |
| Map title chip ("Tar spot risk, Nov 6, 2026"), legend with units, data credit, and the data's newest hour | Crop Risk Tool, D60 | ✓ `/layers`, `/status` |
| Share and export: copy link; **Save image** (the map as shown, with its title, date, legend, labels the reader can drag, and the credit band, drawn on a canvas at 2× for newsletters; ported from late-blight-db); GeoTIFF or NetCDF of the view; TileJSON for GIS | late-blight-db, v1 map images | — for the image; ✓ `/grids`, `/tiles/{layer}.json` |
| Overlays: radar, MRMS rain (24, 72 h), WPC forecast rain (1, 3, 7 days), U.S. Drought Monitor (port from WISP 3); counties; cropland (CDL) | WISP 3, Crop Risk Tool | — third-party; cropland ✗ (PLAN.md Phase 6 cropland fractions) |
| Climate layers: normal, departure from normal, percentile (U2U and MRCC departure maps) | alfalfa "Weather vs climate" | ○ climate layers |
| Place search, my location, coordinates | all | — Nominatim (search on Enter) |

### Sites (P0; replaces v1 Sites, the Crop Risk Tool, Veg Path's place charts)

<!-- prettier-ignore -->
| Feature | Replaces or from | API |
| --- | --- | --- |
| Saved sites: add by map click, search or coordinates; name, reorder, delete; CSV import and export; kept in the browser, synced when signed in (Phase 7) | Crop Risk Tool site list | — browser storage |
| Up to 50 saved sites (the limit `points=` takes: one model's feed across sites is one request; a site's risk is one `/risk` per site, lazy-loaded) | Ben, 2026-11-06 (F4) | ✓ weather and `/models/{id}/run`; `/risk` per site |
| Site groups: name a group (a farm, a state, a client), put sites in it, show a group on the map and the dashboard; a site can be in several groups and stays one site | Ben, 2026-11-06 | — browser storage; Phase 7 sync |
| Preferences inherited all sites > group > site: which crops and models to show (and likely map view and chart defaults); a site in several groups gets the union of their choices; a site or group changes only what it overrides, with "Reset to my defaults" | Ben, 2026-11-06 (F3, F11) | — |
| Site page header: name, coordinates, county, cell, time zone, in the box or not, data through when | v1 Sites | ✓ `/locate`, `/status` |
| Today and the forecast: the latest observed hour, the last 7 days, the next 11, rain and ET totals | v1 Sites, Enviroweather and Wisconet station pages | ✓ `/weather/hourly`, `/weather/daily`, `/weather/totals` |
| Risk now: every in-season model for the site, as a word, a color and a sparkline through the forecast | Crop Risk Tool, Wisconet "Pest & Disease Models" | ✓ `/risk` (one site per request) |
| A model at a site: weather inputs, output and risk on one time axis through observed, forecast and projection; stage bands for crops; action windows for insects (D36) | Crop Risk Tool, Veg Path charts | ✓ `/models/{id}/run`, `projection=true` |
| A results table in NEWA's form: recent days, then forecast days, with daily, 2-, 7- or 14-day and season accumulations, a risk key and CSV | NEWA | ✓ data; ◐ windowed sums in the browser |
| "Since a date": reset an accumulation at a spray or emergence date (Veg Path asks readers to subtract by hand) | Veg Path | ✓ `biofix` |
| Charts and data: hourly, daily, moving averages, degree days; pick variables; forecast on or off; download CSV | Crop Risk Tool "Charts and data" | ✓ points endpoints; ○ moving averages by `roll=` (D0) |
| Dashboard of all saved sites: one card each with today's weather, risk and alerts | v1 Sites, NEWA profile dashboard | ◐ one `/risk` per site |
| Feeds: one model across all sites; one site across all models | project-plan "Feeds" | ◐ one `/models/{id}/run` per site; ✓ `/models/run` |

### Models and topics (P0 text, citations and the explorer; P1 generated sweeps)

<!-- prettier-ignore -->
| Feature | Replaces or from | API |
| --- | --- | --- |
| Catalog: by crop, then disease, insect or crop stage; one-line summary each; status badges; beta models shown only when opted in | VDIFN, Enviroweather crop menus, NEWA tool list | ✓ `/models` |
| Model page: what it predicts, how to read it, what to do at each risk level, valid region and season, inputs (their catalog definitions, D48–D50 corrections), version and changelog, citations with DOIs, link to its map and to run it at a location, its source at the running version | NEWA's More Info, Acknowledgments and References tabs | ✓ `/models/{id}`; content in `agmodels/models/*.md` |
| Explorer: sliders over a model's inputs and its response | — | ✓ `POST /models/{id}/evaluate` |
| Topic pages: identification, life cycle, damage, management, photos (49 drafted in `content/topics`) | v1 pest pages, VDIFN pest info | — content |
| Methods page generated from the catalog, the corrections and the sources (PLAN.md Phase 6) | — | ✓ `/variables`; ✗ corrections and sources by date aren't served yet |

### Tools (P0 unless noted)

<!-- prettier-ignore -->
| Tool | Replaces or from | API |
| --- | --- | --- |
| Degree-day calculator: location, dates or biofix, one or several settings (method, base, upper), totals table and chart, link to the map | v1, NEWA, Wisconet GDD calculators | ✓ `/degree-days`, `/degree-days/table` |
| Crop GDD outlook: this year against normal with its spread, projection to the year's end, stages by maturity (silking, black layer), first fall freeze odds, comparison years (P1) | MRCC's U2U Corn GDD, HPRCC CliGrow | ◐ `/degree-days` with projection ✓, `corn-stages` ✓ beta; normals, spread and freeze odds ✓ (`/climate/*`); years before the archive from Open-Meteo (D87) |
| Alfalfa: growth since the last cut, and the season planner (target interval or number of cuts, editable and lockable cut dates, killing freeze odds) (P1) | alfalfa tool's Growth Projection and Season Planning | ◐ `alfalfa-growth` and projection ✓; killing freeze odds ○; the planner's logic ✗ (F5) |
| Potato volunteer: season map, killing hours at 2, 4 and 8 in by location, air and soil charts (P1) | potato volunteer map | ✓ `potato-volunteer` layer and run, D68 seasons |
| Oak wilt: vector flight risk with the pruning guidance | v1 Oak Wilt page, emails | ✓ `oak-wilt-vectors` |
| Freeze dates: last spring and first fall freeze this year at a location, and the odds by date (P2 for the grid maps) | v1 frost maps, MRCC freeze tools | ✓ `/freeze`; ○ `/climate/frost` |
| Day-of-year calendar | v1 `weather/doycal` (top page in Analytics) | — |

### Climate (P1)

<!-- prettier-ignore -->
| Feature | From | API |
| --- | --- | --- |
| Normals at a location: daily mean and percentile bands, by day, month or year; 1991–2020, last 5 or last 10 years | alfalfa "Climate plot", MRCC summaries | ○ `/climate/normals` |
| This year against last year and normal: running totals, departure, percentile, "N days ahead of normal" for degree days | alfalfa "Weather plot", U2U | ○ `/climate/compare` |
| Frost and freeze: probability of a freeze on or before each date at 32, 28 and 24 °F, growing season length | alfalfa, MRCC | ○ `/climate/frost` |
| Long record at a location (from 1951 or 1979) | U2U comparison years from 1981 | ✗ not planned (D87): points before the archive come from Open-Meteo, one request per span |
| Monthly benchmark: counts of heat days, cold days, warm nights, freeze days, dry days, heavy-rain days, sunny and cloudy days, against a 10-, 20- or 30-year average | ISU FACTS Weather Tool | ✗ (count statistics, monthly rollups; F7) |

### Data and reference (P0 unless noted)

<!-- prettier-ignore -->
| Page | API |
| --- | --- |
| Downloads: point CSV builder (variables, dates, hourly or daily, several locations), grid builder (layer, area, dates, format), yearly NetCDF list (P1) | ✓ `/weather/*`, `/grids`, `/downloads` |
| API docs at `/api/v2/docs`, linked from every data page; changelog and announcements; "Tell us how you use the API" form | ✓ docs; ✗ form and changelog models (project-plan P0) |
| Data status: each source's newest hour, the forecast run, gaps (public face of `/status`) | ✓ `/status` |
| About, glossary (from WISP 3), methods, accessibility statement, contact and feedback | — |

### Accounts and email (Phase 7, sketched here for the pages)

Sign-in by link or code; synced sites; settings (units, beta models, service updates); the daily digest and event alerts per site and model; unsubscribe. Pages port from WISP 3's `Auth`, `Settings` and `Alerts`.

## Page structure

### Navigation

Header (every page, `AppLayout`): the UW–Madison brand bar, the AgWeather name, and **Map · Sites · Models · Tools · Climate · Data**, with place search and the theme toggle; Sign in at the right once Phase 7 lands. On phones the sections fold into a menu and place search stays visible. Footer: About, Methods, Changelog, API, Status, Accessibility, Contact, credits (UW–Madison Extension, the departments, NOAA and the other sources).

### Pages and URLs (proposed)

<!-- prettier-ignore -->
| URL | Page | Notes |
| --- | --- | --- |
| `/` | Home | Search a place; what's in season now (a few headline maps: GDD since Jan 1, rain this week, a seasonal risk); your saved sites if any; links by task; data through when |
| `/map` | Map explorer | State in the query (`?layer=late-blight-dsv&time=2026-07-01..2026-07-14&stat=sum&at=44.1,-89.5&z=7`); full-bleed map, control panel, detail drawer |
| `/sites/{lat},{lng}` | Site page | Any point, saved or not. Tabs: Overview (today, forecast, risk now), Weather, Models, Degree days, Climate (P1), Data. A saved site shows its name; an unsaved one offers \"Save this site\" (a button, not a prompt). `?name=` labels a shared link |
| `/sites` | Your sites | Cards for each saved site; import, export; the two feeds below |
| `/sites/models/{id}` | One model across your sites |  |
| `/models` | Model catalog | Filter by crop, group, status |
| `/models/{id}` | Model page | Generated sections plus the model's Markdown; "See the map" and "Open at a site" |
| `/topics/{id}` | Pest or disease topic | Lists its models |
| `/tools/degree-days` | Degree-day calculator |  |
| `/tools/crop-gdd` | Crop GDD outlook (P1) | Corn first; other crops by preset |
| `/tools/alfalfa` | Alfalfa growth and planner (P1) |  |
| `/tools/potato-volunteer` | Potato volunteer (P1) | Also reachable as the map's layer |
| `/tools/oak-wilt` | Oak wilt |  |
| `/tools/freeze` | Freeze dates and odds |  |
| `/climate` | Climate explorer (P1) | Normals, this year against normal, frost odds, maps of departure |
| `/calendar` | Day-of-year calendar |  |
| `/data` | Downloads | Point and grid builders, yearly files, API link |
| `/methods`, `/about`, `/glossary`, `/changelog`, `/status`, `/accessibility` | Reference | `/methods` generated from code and data |
| `/account/…` | Sign-in, settings, alerts (Phase 7) |  |

### Legacy URLs (D62)

v1 site and VDIFN URLs redirect to their v2 page where one exists, so bookmarks and search results land: `/vdifn` → `/map`; `/weather`, `/weather/precip`, `/weather/et`, `/weather/insol` → `/map` with that layer; `/weather/doycal` → `/calendar`; `/sites/{lat},{lng}` and `/sites` keep their URLs; `/thermal-models` → `/models`; `/thermal-models/degree-days` → `/tools/degree-days`; `/thermal-models/oak-wilt` → `/tools/oak-wilt`; `/thermal-models/{pest}` → its topic; `/subscribers` → `/account` (Phase 7). The Shiny apps' URLs are DoIT Connect's; their pages get a notice linking to v2.

## Design conventions

WISP 3's frontend is the source to port (CLAUDE.md, Gotchas). This section says what carries over and what AgWeather adds.

### Look

- **Brand and type:** the UW–Madison brand bar; Red Hat Display for headings, Red Hat Text for body (WISP 3). Semantic color tokens only (`surface`, `ink`, `line`, `brand-*`…), light and dark, every text pair 4.5:1 in both.
- **Layout:** content pages in a centered column (WISP 3's width); map pages full-bleed. On wide screens the map explorer has a control panel left and a detail drawer right; on phones the controls are a sheet and the detail slides up from the bottom. Cards for summaries (location cards, model cards), tables for numbers.
- **Plain, quiet pages.** One primary action per view; options behind a disclosure ("Map options", "Chart options") as the alfalfa tool's "Plot options" did, not a wall of radios.

### Maps

- MapLibre with the data-tile layer colored on the GPU; palettes from `/palettes` (color-blind-safe by default), the scale from the layer's domain; a light basemap with labels above the data.
- Every map shows a title with its date or range, a legend in the reader's units, the credit, and the data's newest hour. Missing cells are transparent with a hatched legend swatch; forecast and projected days say so in the title ("Forecast for Nov 9").
- Categorical risk uses the same colors for the same level everywhere (`agmodels.spec`'s severity levels, Very low to Very high, and the probability levels, Very low to High), with words beside colors so color is never the only cue.
- Clicking selects a cell and outlines it (`/locate`'s corners); the selection and the view are in the URL.
- Overlays (radar, rain, drought, cropland) in one Layers control with their own legends and credits, as in WISP 3.
- **Save image** (late-blight-db's `export-image.ts`): render the map at 2× pixel ratio, capture the WebGL frame in the render callback, and redraw everything else with Canvas 2D from data: a title band (title, date or range, "As of"), the map, labels with leader lines where the reader dragged them, the legend where it sits on screen, and a footer in the brand color with "University of Wisconsin–Madison" left and the sources right. No screenshot library, so the image matches the screen. Labels here are saved sites or chosen counties (late-blight-db caps them at 10: past that they crowd). In dark mode, suggest light for print. Distinct from `/maps/{layer}.png` (D60), which is a fixed, linkable image for embedding by URL.

### Charts

- ECharts through one `Chart.svelte` and pure, tested option builders; colors from `--color-chart-*`.
- **One time axis per page section, no dual axes.** Peers stack two units on one plot (Veg Path, the Crop Risk Tool, the alfalfa planner, U2U); here inputs, output and risk are stacked panels sharing the time axis (small multiples), so each has its own scale.
- **Kinds are visible:** observed solid; forecast on a shaded band with a "Forecast" label; projection as the P50 line with a P10–P90 band; estimated days as hollow points; missing as a gap. A dashed "Today" line.
- Thresholds as labeled reference lines (32 °F frost, 18 DSV, 300 P-days), windows as bands (the alfalfa cut window, an insect's action window, a crop's susceptible stages).
- Each chart has "Summary and data" (WISP 3): a generated text summary and a table of every value, newest first; CSV and PNG download. Legend items toggle series.

### Numbers, units and time

- Units from one US or metric switch (F10), in a settings dialog reachable from the header on every page, so changing them never leaves the page; converted only in the frontend (the `units` module from WISP 3); the API is asked for stored units or `units=`.
- Dates as "Nov 6, 2026" in tables and "November 6, 2026" in text; times with their zone ("2 p.m. CST"). Grid days are CST midnight to midnight (D74); a site's page says when it uses the site's own days (`day_basis`).
- Precision from the catalog; degree days to whole numbers, rain to hundredths of an inch.

### States and feedback

- Loading: skeletons the size of what's coming, never a blank map; the map keeps the previous tiles until the new ones arrive.
- Errors and warnings from the API's `meta.warnings` and `errors` shown in its words (they're written for the public, CLAUDE.md).
- Outside the box or before the archive, say where the data comes from (Open-Meteo) and what differs.
- Stale data: a banner when `/status` shows a source behind.

### Words

- CLAUDE.md's "Writing for the public" rules apply to every page. Define a term (biofix, DSV, P-days, growing degree days) at its first use on a page with the glossary's `Term` (WISP 3).
- Risk in words before numbers: "High risk: 22 DSV since June 30. Treat if you haven't in 7 days."

### Accessibility and testing

As WISP 3: axe on every page in light and dark, keyboard and reflow tests, Playwright smoke tests, findings in `docs/accessibility.md`. The map is supplemented, not replaced: every map view has the same values reachable as a site's table and a download.

## Peer review

Visited 2026-11-06 with a headless browser (Playwright), late-blight-db added the same day with its source read: each site's pages read and screenshotted, and the interactive tools driven (a site added at Hancock, WI, tabs and model groups opened, a station picked, a county clicked). Ben's notes on each site come first; findings follow.

### UW sites v2 replaces

**[UW Vegetable Pathology weather pages](https://vegpath.plantpath.wisc.edu/weather/hancock/)** host interactive charts that draw from the v1 API. Weather data chart: min/max daily temperature, mean RH, precip, solar insolation. Potato disease chart: daily and cumulative late blight DSV and early blight P-days.

- Highcharts, May 1 to today, seven fixed places (Arlington, Hancock, Grand Marsh, Plover, Antigo, Spring Green, Rhinelander). Both charts are dual-axis.
- Take: Highcharts' accessibility module gives each chart a text description and a "View as data table" button; WISP 3's "Summary and data" does the same and should be on every chart. Its interpretation text is the right kind of guidance: what a DSV is, the threshold of 18, the 300 P-days after emergence.
- Improve: readers are told to "note the cumulative DSVs at your last spray and subtract"; v2's "since a date" (biofix) does that for them. The seven places become any location.
- API: ✓ (`/models/run` for DSV and P-days, D64; `/weather/daily`). An embeddable chart for their WordPress site is F6.

**[VDIFN](https://agweather.cals.wisc.edu/vdifn)** is AgWeather v1's interactive mapping interface (repo `../ag-vdifn`). Daily gridded weather feeds disease risk and insect development models, shown as color-coded risk; clicking a cell brings up its daily history.

- Layout: left panel (Disease, Insect, Custom; Wisconsin or Upper Midwest; crop → model; date range with Past week, Past month, This year, Defaults; Tmin/Tmax for custom degree days; °C/°F; Submit), Google Maps right, palette Spectral or Viridis. Nothing shows until Submit.
- Take: the crop-first model picker, quick date ranges, the custom degree-day model, the point popup.
- Improve: no Submit (the map updates as settings change, data tiles make it instant); a default view on load (the most relevant in-season layer); the extent toggle becomes zoom.
- API: ✓ throughout.

**[AgWeather v1 site](https://agweather.cals.wisc.edu/)** (repo `../soils-ag-wx`): weather data maps and tables (temperature, precipitation, dew point, vapor pressure, high-humidity hours, ET), thermal models (degree days, disease risk, oak wilt), email subscriptions for saved sites, the free API.

- Pages are organized by data type (Weather, Thermal Models, Site Data, Emails); each map page is a server-rendered image plus a table. Also: the day-of-year calendar, NWS HYD reports, the corn development and pest pages.
- Take: the plain home page that routes by task; "Sites" bookmarkable by coordinates (`/sites/43.07,-89.4`), kept as v2's site page, with v1's offer to save an unsaved site.
- Drop: HYD (project-plan Drop candidates), image maps.
- API: ✓.

**[WISP](https://dev.wisp.cals.wisc.edu/)** (v3, `../wisp3`): the design and code source. Its home page is the model for ours: a plain statement of what the service does, four numbered steps, one call to action. Its map overlays (IEM radar, MRMS 24 and 72 h rain, WPC 1-, 3- and 7-day forecast rain, the Drought Monitor's ArcGIS feature service) port as they are.

**[Vegetable Disease Detections](https://late-blight-db.vercel.app/)** (`../../projects/late-blight-db`, SvelteKit, MapLibre; in development): a portal for confirmed late blight and cucurbit downy mildew detections, by county, across the US and Canada. Ben built it before WISP 3, which took its layout: the map on one side and a feed on the other.

- Layout: disease toggle and year in the header; Map and Detections (a table) tabs; a "Map tools" bar (Download CSV, Save image, Share); counties colored by time since the latest detection (within 7 days, 8–14, 15–30, over 30, none), with the legend on the map; the feed beside it in sections by the same bands, each entry with county, date and "(1 month ago)", crop, strain and the reporter, opening a detail dialog. Share gives a link to the current view.
- **Save image:** a "Label counties with detections" switch and a "since" slider (default the last 14 days, at most 10 labels, "8 counties labelled · drag to adjust"); labels are placed to avoid each other and the legend, and can be dragged. The saved PNG (checked: 2112 × 1630 from a 1056-wide map) has a title ("Late blight detections · 2026"), a subtitle ("As of Nov 6, 2026 · labelled: detections since Jan 1, 2026"), the map with the labels and their leader lines, the legend, and a red footer band with the university's name and the sources. A note suggests light mode before saving for print.
- Take: Save image for every map, with sites or counties as labels; the feed's sections by recency; Share as an explicit button showing the link; the detail dialog's plain label/value list. Its time-since-detection coloring is a model for any "how recent" layer (the last freeze, the last rain over an inch).
- API: — (all browser-side); maps ✓.

**[Crop Risk Tool](https://connect.doit.wisc.edu/cpn-risk-tool/)** (Shiny, `tmp/shiny/crop-risk-tool`): hourly weather anywhere, crop risk and insect models, several sites, no grids.

- Layout: sites and dates left, map center, results right. Adding a site by coordinates asks for a name in a dialog. Risk tab: model groups (Field crops, Vegetable, Cover, Tree, Insects), a model select with a paragraph on when the crop is susceptible, a warning box ("only valid between V10 and R3"), "All" or "Last 30 days", "Show additional variables", then one card per site with a sentence ("Tar spot for Nov 06, 2026: 66% (High risk)") over a risk-colored area chart with a Today line and the forecast shaded. Charts tab: Hourly, Daily, Moving averages, Growing degree days, All; variables as removable chips; metric and forecast switches; CSV.
- Take: the per-site risk sentence and sparkline (the dashboard card), the susceptibility warning, the quick date ranges (Past week to Last season), the CSV upload and export of sites, "Everything up to date" status.
- Improve: the Charts tab puts temperature, precipitation and cumulative precipitation on two y-axes in one plot; stacked panels instead. The model dropdown hides 30+ models; a filterable list by crop reads better on a phone.
- API: ✓; the dashboard makes one `/risk` per site, lazy-loaded as cards come into view (F4).

**[Potato volunteer risk](https://connect.doit.wisc.edu/potato-volunteer-risk/)** (Shiny): Wisconet stations colored by risk (Very high to Low), seasons 2023–24 onward, per station air and soil charts with 32 °F and 27 °F lines and a sentence: "Killing hours @2in: 0 - @4in: 0 - @8in: 0. Tuber survival likelihood: Very high". Season resets October 1.

- v2 maps the grid (HRRR soil temperature, D9) with the same sentence and charts at any location; the season window is November 1 to March 31 (D68), a change readers of the old map will notice, so the page says it.
- API: ✓.

**[Alfalfa tool](https://connect.doit.wisc.edu/alfalfa-tool/)** (Shiny): tabs Weather Map, Weather Charts, Growth Projection, Season Planning, Downloads, About. v2 must include all of it.

- Map: Wisconsin or Upper Midwest; Observed weather, Climate averages, Weather vs climate; weather year; display value (mean, min, max temperature; daily and cumulative GDD 41 and 50; for climate also frost, hard freeze and killing freeze probability on the day and cumulative); smoothing none, 7, 14 or 28 days; a date slider with −7, −1, +1, +7, Reset; autoscale legend; a "Selected grid" box with the value.
- Charts: a Weather plot (min, mean, max with frost, hard freeze and killing freeze lines, this year or last), a Climate plot (period 30-, 10- or 5-year; frost threshold; smoothing) and a Custom plot comparing any two of weather or climate temperature, GDD/day, cumulative GDD or frost probability.
- Growth Projection: GDD 41 since the last cut or killing freeze, projected by climate averages, with the 900–1100 cut window and the fall rule (<360 or >800 GDD before the killing freeze).
- Season Planning: weather year, climate period, target interval (GDD) or number of cuts (2–6); cut dates as editable, lockable and removable cards; a chart of cumulative GDD (observed and projected against the climate average), GDD since the last cut as a sawtooth, cut markers with days and GDD, the green cut window, and the cumulative killing freeze probability on a second axis.
- Downloads: the whole grid as shown, or one location's weather and climate.
- Take: all of the above. The planner is the strongest single tool among the peers; v2 keeps its interaction (lockable cut dates, target interval or count) and splits its chart into a GDD panel and a freeze-odds panel.
- API: map ✓ except climate layers ○; charts ✓ with normals and frost ○; growth ✓; planner ◐ (F5); downloads ✓.

### Other state and regional services

**[Wisconet](https://wisconet.wisc.edu/)**, Wisconsin's mesonet (5-minute data from ~80 stations).

- Station page: metadata, soil temperature and moisture at 2, 4, 8, 20 and 40 in, plant available water and its percent of maximum by depth, chill hours since October 1, reference ET yesterday, Cattle Comfort Index, Temperature Humidity Index, pressure; units toggles per quantity (°F/°C, in/mm, inHg/mb, mph/m/s, ft/m). Agricultural dashboard: a map of stations with values, a summary card (temperature, Drought Monitor category at the station, 24-hour rain, yesterday's ET, 4 in soil temperature, plant available water, "No active weather hazards"), and cards for Animal Comfort, Chill Hours, Drought, ET, Forecast, Growing Degree Days (start, end, lower and upper threshold, simple or sine), Pest & Disease Models (cherry leaf spot, spotted wing drosophila, links to NEWA and UW's Wisconsin Crop Disease Risk Forecast), Plant Available Water, Soil Conditions. Meteograms and an archive download (5-minute, hourly or daily, a 100,000-value limit stated up front).
- Take: the summary card's mix for the site page (rain, ET, soil temperature, drought category, NWS alerts); chill hours and livestock heat stress as new derived values; per-quantity units; stating a download's size limit before it fails.
- API: drought category at a point — (the Drought Monitor's feature service, as WISP 3 queries it); NWS alerts — (api.weather.gov); chill hours ✓ (`/chill`, the `chill_hours`, `utah_chill_units` and `chill_portions` layers); THI and cattle comfort ✓ (daily features and hourly layers); plant available water ✗ (we hold no soil moisture). Station observations beside the grid wait for the station-network enhancement (D59).

**[Enviroweather](https://enviroweather.msu.edu/)** (Michigan State).

- Station-first: a map and a dropdown of about 100 stations (retired Wisconsin ones included), a station page with current conditions (leaf wetness, wet hours today), the NWS 7-day forecast, links to hourly and daily reports, and Weather Models and Crop Models menus. Crops grouped as Fruits, Vegetables, Landscape & Nursery, Livestock, Field Crops; a mobile app. Its legacy tools are offline after a security shutdown, which leaves few models reachable today.
- Take: crop-first grouping in the catalog. The PHP source dump in `tmp/enviroweather_src` is the model mine (PLAN.md, Enhancement: model review).
- Avoid: a long station dropdown as the way in.

**[NEWA](https://newa.cornell.edu/)** (Cornell): station-based IPM models for the Northeast.

- Catalog page: crops (Apples, Berries, Field crops, Grapes, Ornamentals, Vegetables) split into diseases, insects and other, one sentence per tool naming the pest, the degree-day base and what it times. Model page: station selector, "Date of Interest" calendar, results for the station (who maintains it, last download), a results table of the past days then five forecast days with daily, 2-day, 14-day, 21-day and season values, a risk key (Low 0–3, Moderate 4–6, High >6), CSV, and More Info, Acknowledgments and References tabs. Profiles store biofix dates and preferred stations; help pages explain default biofix dates and degree days; a disclaimer on data accuracy.
- Take: the results table as a model's "Table" view; the date-of-interest picker (look back at any day's result); the one-sentence catalog entries; a page on how default biofix dates are set; Acknowledgments as a section of each model page.
- API: ✓ (windowed sums in the browser or as model outputs).

**[MRCC](https://mrcc.purdue.edu/)** (Midwestern Regional Climate Center): many climate tools to replicate.

- U2U Corn GDD (`/tools/corngdd`): click a county, then a chart of this year's GDD (from a chosen start date), the 1991–2020 average with the range of years shaded, the projection to the year's end, silking and black layer lines from corn maturity days (85 → 1074 and 2038 GDD), a histogram of first fall freeze dates at a chosen temperature, up to three comparison years from 1981, a Data tab and downloads. The reference for the crop GDD outlook.
- Freeze tools: current-season freeze maps (date of first 28 or 32 °F freeze, date of the most recent, days since, nights below in the past 14 days, lowest minimum), freeze probabilities (on, before or after a date, at 32 or 28 °F), the Freeze Date Tool (Tableau: average first fall and last spring freeze, growing season length and their trends by county, from ACIS gridded data).
- Also: modified GDD from April 1 and May 1 with departures, corn stress degree days (base 86 °F), ET and water balance maps (precipitation minus ET over 7 to 90 days, observed and 3-day forecast), chilling hours (any lower and upper bound), 4 in soil temperature maps, heating and cooling degree days, the winter severity index (AWSSI), the Ag Climate Dashboard grouping all of these as Recent conditions, Forecasts, Climatologies, Products & Tools.
- Take: the crop GDD outlook; the freeze maps as layers; the water balance layer; modified GDD and stress degree days with departures (both are running totals we already keep); the Ag Climate Dashboard's grouping as the Climate section's landing page.
- API: GDD and stress DD ✓; projection ✓ (from the archive's years, not 30); normals, departures and freeze odds ✓ (`/climate/*`, `climate=` on maps); years before the archive from Open-Meteo at points (D87); current-season freeze maps ✓ (lowest minimum as `stat=min`, nights below as `count=days_below_32`, freeze dates as `first=frost`, `last=`, `since=`, D78); water balance ✓ (a computed layer); chill hours ✓ (`/chill`, any bounds at points).

**[U.S. Drought Monitor](https://droughtmonitor.unl.edu/)**: weekly map (released Thursday, data valid Tuesday), categories D0–D4, KMZ, shapefile, GeoJSON and WMS per week, statistics by state and county. WISP 3's overlay (the current map from the ArcGIS feature service, with the categories' legend) ports as is; add the map's valid date to the legend. A location's category comes from the same service. —

**[ISU FACTS Weather Tool](https://facts.extension.iastate.edu/weather-tool)**: pick a crop reporting district on a map of 12 states, a variable, a month or the whole year, and a benchmark (most recent 10-, 20- or 30-year average, or a custom range from 1984). Variables are counts and sums with stated thresholds: heat days (max >93.2 °F), cold days (mean <50 °F), warm nights, freeze days (min <32 °F), dry days (rain <0.25 mm), extreme rain days (>25 mm), sunny (>20 MJ/m²) and cloudy (<10 MJ/m²) days, GDD base 50, precipitation, radiation, and NASS corn and soybean yields. Its graphs didn't render in the headless browser, so the output wasn't seen.

- Take: the threshold-count variables and the benchmark choice, as a "This month against normal" section of the climate explorer and, by county, as a map. Stating each threshold beside its name is a good practice to copy.
- API: ✗ (count statistics over a window, monthly rollups at points and by county; F7).

**[HPRCC Agroclimate](https://hprcc.unl.edu/agroclimate/)**: a list of tools, several from partners. CliGrow is the one to take: location, planting date, crop presets with base and upper (alfalfa 41/77, corn 50/86, dry beans, grass 32/77, potatoes 45/97, sorghum, soybeans, sugarbeets, sunflower 50/99, wheat 32/77, custom), maturity GDD, freeze temperature, a comparison year, and a bookmarkable graph. Also the Cattle Comfort Index (past and forecast), wet bulb globe temperature forecasts, Climate Perspectives (recent weather against prior periods at a station) and links to drought tools.

- Take: crop presets for the degree-day calculator and the crop GDD outlook (each preset naming its source); a bookmarkable result. Heat stress for livestock is a candidate (F8).
- API: ✓ for degree days at any setting; presets are frontend data.

### Patterns across the peers

- **Station → tool** (NEWA, Enviroweather, Wisconet, Veg Path) against **map → site → tool** (VDIFN, U2U, the Shiny apps). Ours is the second; the first's strength, a page per place with everything about it, is the site page.
- **Dual-axis charts are everywhere**, and every one of them was harder to read than it needed to be. Stacked panels on one time axis.
- **Projection to the end of the season** (U2U, alfalfa, CliGrow) is what readers plan with; ours exists (D63) and should show on every cumulative chart.
- **Guidance beside the number** (NEWA's management tabs, the Crop Risk Tool's susceptibility warning, Veg Path's interpretation) is what makes a model usable.
- **Freshness is stated** on every good page ("Latest Collection 3:15 PM CST", "Everything up to date").

## Feature ideas against the API

Ideas from the review that aren't already in the feature tables, and what each needs.

<!-- prettier-ignore -->
| Idea | From | API | Work |
| --- | --- | --- | --- |
| Chill hours (hours between two temperatures, from a start date such as October 1; Utah and 0–7.2 °C variants) at locations and as a map | Wisconet, MRCC | ✓ | New daily features and a running total in the catalog (hourly temperature is stored); S–M |
| Livestock heat stress: Temperature Humidity Index and its hours above thresholds; cattle comfort index | Wisconet, HPRCC | ✓ | Derived hourly variable from temperature, humidity (and wind, sun for CCI) with daily features; S |
| Water balance: precipitation minus ET0 over a window, as a layer and at locations | MRCC | ✗ (◐ at points: both totals ✓) | A derived layer computed from two stored running totals; S |
| Current-season freeze maps: first fall freeze date, days since the last freeze, nights below a threshold in the last N days | MRCC | ✓ (`/freeze` at points, `count=days_below_32`, `stat=min`, `first=frost`/`last=`/`since=`, D78) | Built in Phase 6 C steps 2 and 4 |
| Monthly or seasonal threshold counts against normal (heat days, warm nights, dry days, heavy-rain days) by location and county | FACTS | ✗ | Count statistics (above), `interval=month` at points, county summaries (below), normals of counts from the climatology (D61 keeps daily data, so they're computable); M |
| County and crop-district summaries (mean, min, max of a layer over an area) | FACTS, U2U, Drought Monitor statistics | ✗ | A zonal statistics endpoint over `agdata.regions`' counties and states; M |
| Trends in freeze dates and season length (1951 on) | MRCC Freeze Date Tool | ✗ | Not planned (D87): maps cover the archive's 11 years only, and gridMET's years build the normals, not daily maps |
| Drought category at a location; NWS watches and warnings at a location | Wisconet | — | Browser fetches from the Drought Monitor feature service and api.weather.gov, as WISP 3 does for overlays; S |
| Station observations beside the cell's values | Wisconet, Enviroweather, NEWA | ✗ | The station-network enhancement (D59), after launch |
| Soil moisture and plant available water | Wisconet, FACTS | ✗ | No source in the archive; HRRR's soil moisture or Open-Meteo's could be a new variable; L, P2 (F9) |
| Leaf wetness | Enviroweather, NEWA | ✗ | No measured source; models use RH ≥ 90 hours (D50). Leave out, and say so on the models that would use it |
| Date of interest: any past day's model result and forecast-at-the-time | NEWA | ◐ | Results for a past day ✓ (`/risk?date=`); "as forecast then" needs stored forecasts we don't keep; leave out |
| Comparison years on any cumulative chart | U2U, CliGrow, alfalfa | ✓ the archive's years; earlier from Open-Meteo | Several `/degree-days` requests; years before the archive come from Open-Meteo (ERA5), so the chart names their source beside the archive's (D87) |
| Crop presets for degree days (crop, base, upper, method, source) | CliGrow | — | Frontend data, reviewed against the cited sources; S |
| Map animation through a range | U2U Animations | ◐ | Prefetch tiles; cap the frame count; S |
| Embeddable chart or table for partner sites (Veg Path's WordPress) | Veg Path | ✗ | An embed route with a minimal layout, or the API and static maps alone (F6) |
| Help: short how-to videos or a guided first visit | NEWA | — | Content, after launch |

## API and data work the frontend needs

Rolled up as PLAN.md Phase 6 B (the work list, by priority, with sizes). All of it, P0 to P2 and the climatology, is built in Phase 6 before the pages (Phase 7): several sites per request (F4), the changelog and API-use form, methods data, model guidance, degree-day presets; the climatology and climate endpoints, the alfalfa planner (F5), the crop GDD outlook, count statistics, freeze layers, chill hours, water balance, insect timing layers, cropland fractions; county summaries, livestock heat stress, frost-odds and freeze-trend maps, soil moisture. Station networks (D59) stay after launch.

## Open questions

Ben answered F1–F13 on 2026-11-06; they're kept here with the answers, as decisions to carry into Phase 7.

<!-- prettier-ignore -->
| # | Question | Answer or recommendation |
| --- | --- | --- |
| F1 | Site page URL and the word for a place | **Settled:** "sites", as v1. Every point is `/sites/{lat},{lng}`, saved or not, so v1's bookmarks work; an unsaved site offers to save itself. Saved sites are keyed by coordinates, so a shared link opens the same page for anyone. Other pages under `/sites/` (`/sites/models/{id}`) can't collide, since the site route matches numbers only |
| F2 | Should the map explorer be the home page? | **Settled:** no. A short home page that routes by task; VDIFN's URL lands on the map |
| F3 | Which models a site's "Risk now" shows | **Settled:** preferences inherited all sites > group > site: the reader picks crops and models once; a group or site overrides only what it changes, with "Reset to my defaults". Without preferences, in-season and in-region models (as `/risk` does) |
| F4 | One request per site, or `points=`? | **Settled:** `points=` on `/models/{id}/run` (many sites, one model: the feed), up to 50 (10 with a projection), which is also the saved-site limit; one site and many models is `/risk` or `/models/run` per site, lazy-loaded (Ben, 2026-11-06: many sites × many models isn't a use case) |
| F5 | The alfalfa planner's logic | **Settled:** a pure function in `agmodels`, served by a small endpoint; the page only edits dates |
| F6 | Partner embeds | **Settled:** the API and static maps at launch; an embed route only if partners ask |
| F7 | Count statistics and monthly benchmarks | **Settled:** P1 at points, P2 by county and on the grid |
| F8 | Chill hours, water balance, livestock heat stress | **Settled:** chill hours and water balance P1, heat stress P2 |
| F9 | Soil moisture | **Settled (P2, M):** easier than first written. The sources soil temperature already comes from carry it (ERA5-Land's `swvl1`–`swvl3` in the same CDS request, IFS's soil moisture in Open-Meteo's open data, HRRR's in the box), and Wisconet's sensors at 2–40 in check it as `docs/validation-soil.md` checked temperature. The limits are what it means: modeled soil water is for the model's soil at ~9 km, not the field's, so it's shown as water content and as a percentile against other years, and plant available water waits for the field's soil (SSURGO) |
| F10 | Units | **Settled:** one US or metric switch, in a settings dialog opened from the header on every page |
| F11 | A site in two groups whose preferences differ: which does it inherit? | **Settled:** the union. The settings are likely show/hide choices for crops and models, so a site in a "corn" group and a "soybean" group shows both crops' models, unless the site sets its own |
| F12 | What a group's map view is | **Settled:** the map framed to the group's sites, with them labeled; its layer and settings from the group's preferences |
| F13 | Save image: client-side only, or also server-rendered at print size? | **Settled:** client-side (as on screen, labels as placed); `/maps/{layer}.png` stays the server image for links and email |
