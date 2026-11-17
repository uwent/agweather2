# Models plan: more models, and a write-up for each

PLAN.md Phase 6 step 4 (Ben, 2026-11-17: all of it before the frontend; L–XL, research more than code). This document holds the step's handoff, rules, learnings and parts, so PLAN.md stays short; PLAN.md's step 4 points here. Decisions that change the architecture, the API or a rule go to PLAN.md as D# as usual; choices within one model are recorded in its part here and in the model's changelog. Each part is planned in full for Ben's go-ahead before it starts; parts not yet started are stubs, expanded when they come up.

---

## Handoff

**Updated 2026-11-17.** Branch `phase-6`.

- **Where things stand:** Part A (the Enviroweather inventory, `docs/enviroweather-models.md`) is done. Part B (apple) is planned and Ben answered its questions (2026-11-17, "Ben's answers" under B): NEWA is the standard where sources conflict (D95), fire blight's wetness from dew point depression as well as RH, codling moth by D36 curves, no harvest dates, our own validation against NEWA.
- **Next:** part B in its order: B5's validation data first (can we read NEWA's station hours and model results for Wisconsin stations?), then B1 crop and stages, B2 scab, B3 fire blight, B4 codling moth, each landing with tests, docs and its changelog notes. Papers: B needs the sources under "Sources to get" (TODO.md asks Ben for the ones behind paywalls; find the free ones first).
- **Waiting on Ben (TODO.md, Phase 6):** the apple papers. MSU won't share its newer code or database tables (they told Ben they're too busy), so every table missing from the dump is rebuilt from its published source.
- **Read first in a new session:** this handoff and part B; `docs/enviroweather-models.md`'s "What we found" and "Priorities"; CLAUDE.md's model rules ("One model, one file", "Legacy code", "Evaluate ported logic critically", "Gaps"); PLAN.md D31 (model docs as Markdown), D33 (disease gated by crop stage), D36 (insect phenology as curves), D37 (each model counts degree days by its source's method), D45 (gaps), D46 (versions 0.x until launch), D93 (crop ids), D94 (events on model results).

---

## Rules for every model in this step

From PLAN.md step 4 and CLAUDE.md:

- Each model is ported or built as Phase 3's were: the published source found and the code checked against it (a port's numbers are what to look for, not the authority), citations with DOIs checked against Crossref (`test_citations --network`), a version (0.x, D46), status, region, season and sweep, tests against the source's own numbers, and intended differences recorded in its part here and in its changelog.
- One model, one file in `agmodels`, a pure function run the same on a point and the grid; degree days by its source's method (D37); missing data stays missing, and estimates are named and flagged (D45).
- Crops by id from `agmodels.croplist` (D93); a new crop is added there with its model.
- **NEWA is the standard where sources conflict** (D95, Ben 2026-11-17): where NEWA (Cornell) runs a model of the same pest, crop or disease, its method and thresholds win over Enviroweather's, VDIFN's and the Crop Risk Tool's, unless a newer published source shows NEWA's wrong; a difference we keep is recorded with its reason. Wisconsin's fruit growers use NEWA, so our numbers should agree with it on the same weather.
- **Credit Enviroweather** on every model that draws on their code by citing their website as a source (Ben has their permission, 2026-11-17; no further terms): a `Citation` with the model page's URL on enviroweather.msu.edu, beside the published sources.
- **Validate ourselves:** reviews by colleagues are welcome but uncertain (Ben: mixed results getting feedback from UW colleagues), so each model is checked against independent results: NEWA's on the same station weather where it has the model, then observations (scouting reports, trap catches).
- Public text (model descriptions, messages) follows CLAUDE.md's "Writing for the public".

## Process for each part

1. Plan: the models, the published sources, the choices (method, thresholds, inputs, maps or points), the questions, size and risks; Ben's go-ahead.
2. Sources: get and read each paper (Ben adds paywalled ones to `tmp/references/`); record the numbers to port with their page and table.
3. Build: the model, its front matter (D31), its tests against the source's numbers and against the legacy code where they should agree (a parity test limited to those cases), its sweep and snapshot.
4. Check on real data: run it on the dev archive at Wisconsin locations and compare with what growers see elsewhere (NEWA, Enviroweather, scouting reports), recording differences and their reasons.
5. Record: the part's notes here, the changelog, PLAN.md D# for anything general, the handoff.

## Learnings so far

- **Wisconsin's apple and grape growers use NEWA** (Cornell's Network for Environment and Weather Applications): about 30 NEWA stations at Wisconsin orchards and vineyards, installed with a DATCP Specialty Crop Block Grant to the Wisconsin Apple Growers Association; the UW Fruit Program (Amaya Atucha) leads the work, and UW Extension's fruit updates cite NEWA's scab and fire blight models ([UW–Madison news](https://news.wisc.edu/uw-madison-apple-growers-bring-data-to-the-orchard/), [UW Extension](https://cropsandsoils.extension.wisc.edu/wisconsin-apple-disease-update-high-risk-conditions-in-wisconsin/)). Our value for fruit is the grid between stations and one place for every crop; where NEWA and MSU differ, a Wisconsin grower will compare us with NEWA.
- **NEWA's apple models:** apple stages and the scab and insect models by degree days base 43 °F (Baskerville-Emin) from January 1; apple scab with Gadoury and MacHardy's ascospore maturity and the Revised Mills infection events; fire blight with Cougarblight (2010) and MaryBlyt's EIP, with the orchard's blight history and first blossom date as inputs; trauma blight as its own tool ([UMass on NEWA 3.0](https://www.umass.edu/agriculture-food-environment/fruit/news/newa-30-what-you-need-to-know), [UVM on NEWA's scab model](https://blog.uvm.edu/fruit/2021/05/12/vt-apple-ipm-newa-apple-scab-model/)). MSU uses base 42 °F and a MaryBlyt-style model only.
- **Enviroweather's code** (inventory): almost nothing cited; single sine with no upper from a fixed March 1 nearly everywhere; missing days add 0; several tables are in MSU's database, not the dump; a list of likely bugs in the inventory's "What we found".
- **The apple scab sources:** MacHardy and Gadoury (1989), "A revision of Mills's criteria for predicting apple scab infection periods", Phytopathology 79:304–310, doi:10.1094/Phyto-79-304 (ascospore infection about 3 h shorter than Mills; night rain counted from 07:00); Stensvand et al. (1997), Phytopathology 87:1046 (low temperatures; conidia like ascospores at 2–8 °C); Gadoury and MacHardy (1982), "A model to estimate the maturity of ascospores of Venturia inaequalis", Phytopathology 72:901–904, doi:10.1094/Phyto-72-901 (probit of maturity linear in degree days base 0 °C; MSU's 2.51 + 0.01 × DD°C is this). None read in full yet.
- **Fire blight sources:** Steiner (1990), "Predicting apple blossom infections by Erwinia amylovora using the MARYBLYT model", Acta Horticulturae 273:139–148 (EIP ≥ 100; a mean of at least 15.6 °C; OMAFRA describes the trigger as 110 degree hours above 18.3 °C from first open bloom, which makes MSU's divisor of 1.95 for °F degree-hours worth checking); Smith's Cougarblight (WSU): the 2010 version sums hourly risk values over 4 days (96 hours, a flower's susceptible life), its lower threshold lowered from 60 to 50 °F, thresholds from 30 years of Washington and Oregon infections ([WSU overview](https://extension.wsu.edu/chelan-douglas/agriculture/treefruit/pestmanagement/cougarblightmodeloverview), [CougarBlight 2010](https://extension.wsu.edu/chelan-douglas/agriculture/treefruit/pestmanagement/cb2010fireblightriskmodel)).
- **WSU's Decision Aid System (DAS)** ([WSU](https://treefruit.wsu.edu/tools-resources/wsu-das/)) runs 11 insect, 7 horticultural and 5 disease models for Washington tree fruit: apple maggot, campylomma, codling moth, lacanobia fruitworm, obliquebanded and pandemis leafrollers, oriental fruit moth, peach twig borer, San Jose scale, western cherry fruit fly; apple scab, fire blight (Cougarblight), cherry powdery mildew; bloom and fruit growth by variety; sunburn and storage scald. Its codling moth model (Jones et al.) is the source of D36-style emergence and hatch curves. Added to `docs/landscape.md` (missed in Phase 3's survey). Where NEWA has no model of a pest (codling moth curves, obliquebanded leafroller, apple maggot), DAS is the next reference, with care: it's fitted in central Washington.
- **Leaf wetness from weather data:** RH ≥ 90 % hours (our proxy, as in late blight and TOMCAST) and dew point depression (Gillespie et al. 1993: wetness when air temperature less dew point falls below a threshold, about 2 °C for onset in their model, with separate onset and drying limits) are the two published empirical estimates; Sentelhas et al. (2008, Agricultural and Forest Meteorology 148:392–400, "Suitability of relative humidity as an estimator of leaf wetness duration") compared RH ≥ 90 %, dew point depression and an extended RH threshold, and Montone et al. (2016) compared CART, dew point depression, RH hours and Penman–Monteith across four US states. Neither read yet. Our hourly data has dew point, and the catalog already rolls up dew point depression.
- **NEWA's data:** no public API documentation found; a third-party R package reads NEWA 3.0's hourly station data from NRCC (`hrly.nrcc.cornell.edu/stnHrly`), and RCC-ACIS serves station data. Whether NEWA's model results can be read the same way is B5's first question.
- **Codling moth:** base 50 °F, upper 88 °F, single sine with a horizontal cutoff, from a biofix at first sustained trap catch (Riedl and Croft 1974; Riedl, Croft and Howitt 1976, developed at Michigan State); UC IPM's biofix needs catches on two successive nights with sunset temperatures above 62 °F. MSU's code uses no upper, and counts generation 2 from March 1, not the biofix (likely a bug). Washington's newer model (Jones et al.) gives cumulative egg hatch curves, which would fit D36.

---

## Parts

### A. Enviroweather's models: inventory (done 2026-11-17)

`docs/enviroweather-models.md`: all 60 folders (44 models, 16 displays), what each predicts, its inputs against our data, method, sources, overlap with ours, likely bugs, Upper Midwest relevance, and a ranked list. Read by four parallel readers, assembled and ranked by hand. Its priorities set the order of parts B–E.

From PLAN.md (moved here 2026-11-17, verbatim):

> **Enviroweather's models.** Ben received permission from MSU Enviroweather (2026-11-17) to use their source code as a basis for new models; credit Enviroweather on each model page that draws on it. The dump is in `tmp/enviroweather_src/enviroweather-rm-api-master/app/ResultModels/` (PHP, 60 folders and `models_with_multiple_start_dates.txt`). First an inventory, `docs/enviroweather-models.md`: each folder's model, what it predicts, its inputs (and whether our data has them: leaf wetness, for one, we have only as RH hours), method and cited source, how it overlaps ours, and a priority by Wisconsin and Upper Midwest crops. About 15 folders are displays rather than models (`Meteogram`, `Rainfall*`, `DegreeDay*`, `WeatherSummary`, `Inversion3m`, `OvernightTemperatures`, `LatestObsRegional`, `Regional`, `SoilConditions`): note any feature they suggest. Then the ports in priority order: fruit (apple scab, fire blight, codling moth, oriental fruit moth, plum curculio, apple maggot, obliquebanded leafroller, cherry leaf spot and fruitworm, grape berry moth, blueberry maggot and gall wasp, cranberry fruitworm, mummy berry, sooty blotch, apple, cherry and blueberry phenology), vegetables (cucurbit downy mildew, asparagus miner, potato heat and moisture), trees (spruce gall adelgids, Fraser fir growth, pine sawfly and needle scale, tussock moth, Fletcher scale) and **winter wheat phenology** (our wheat gap, D7). Where it overlaps ours (seedcorn maggot, Colorado potato beetle, European corn borer, cabbage maggot, alfalfa weevil, variegated cutworm, squash vine borer, spotted wing drosophila, TOMCAST, alfalfa cutting), compare thresholds and methods and record which we keep. (Moved here from the model review's Enviroweather item, 2026-11-17.)

(The inventory found winter wheat a stub with no thresholds, so it moved to part J; "D7" there means Phase 3 D's step 7, not decision D7.)

### B. Apple: stages, scab, fire blight, codling moth (planned 2026-11-17; waiting for Ben)

Apples are Wisconsin's main tree fruit (about 4,000 acres in nearly 300 commercial orchards in 57 counties, per the State Climatology Office; Michigan is the third US state). Scab and fire blight are the sprays growers time by weather; codling moth is the key internal fruit pest; apple stages feed all three. **Size: L** (four models, two with hourly wetness rules; mostly sources and checking). Existing code that changes: `croplist` (a crop), `agmodels.models` and `insects` (new modules), the ingredients for maps, topic and model pages; no API change beyond new model ids.

**B0. The crop.** `apple` in `croplist` (category fruit). Model ids by D93's convention: `apple-stages`, `apple-scab`, `fire-blight`, `codling-moth`.

**B1. `apple-stages`** (a crop stage model, like `corn-stages`).

- Degree days from January 1, single sine (Baskerville-Emin), no upper; stages by thresholds: green tip, half-inch green, tight cluster, pink, king bloom, full bloom, petal fall, and the cover sprays MSU lists (first to ninth). MSU's numbers are base 42 °F (inventory: 127 first green, 242 tight cluster, 367 pink, 422 full bloom, 511 petal fall, 749 first cover…); NEWA and UW's scouting reports use base 43 °F (a New York table gives McIntosh tight cluster 228 ± 27, pink 289 ± 26, full bloom 378 ± 35, petal fall 479 ± 42 at base 43).
- Source to find: a published table of McIntosh (or general apple) stages by degree days. Candidates: the NEWA/Cornell table behind its stage predictions, Michigan's (MSU's numbers), Penn State's phenology reports.
- Outputs: `stage` (index) and its code, `dd_total`. Maps from the stored degree days, as `corn-stages`. A stage anchors other apple models (`biofix_stage`, as early blight starts at potato emergence): green tip for scab, first bloom to petal fall for fire blight.
- Checked against observed stage dates in UW's Wisconsin fruit crop scouting reports (2025 and 2026 give DD43 and stages by site).
- Left out: MSU's harvest maturity for McIntosh, Jonathan and Red Delicious (Ben: beyond AgWeather's scope; one of its three McIntosh formulas also has its temperature sign reversed since 2008, with no publication).

**B2. `apple-scab`** (primary season: from green tip until the season's ascospores are all discharged).

- **Ascospore maturity:** Gadoury and MacHardy (1982): probit of the percent mature = a + b × degree days base 0 °C from green tip (MSU: 2.51 + 0.01 × DD°C, 100 % forced at 950 DD°F base 32). Discharge: MSU's "Jones" logit (−25.33 + 3.934 ln DD°F, forced at 2050): find its source, or leave discharge out.
- **Infection events:** the Revised Mills table (MacHardy and Gadoury 1989; Stensvand et al. 1997 at low temperatures): hours of wetness needed for light, moderate and heavy infection at the wet period's mean temperature, ascospores counted from 07:00 when rain starts at night. MSU's own table is missing from the dump; we build ours from the papers (and compare with MSU's when it comes).
- **Wetness:** an hour is wet with rain ≥ 0.01 in or RH ≥ 90 % (MSU's no-sensor rule, which NEWA also accepts in place of a sensor); a wet period starts on rain and ends after a dry spell of the length the source gives (MSU uses 8 hours; check against MacHardy and Gadoury's rule for interrupted wet periods). Missing hours end nothing silently: an hour missing inside a period is counted as missing and flagged (MSU's skips the rest of the day).
- **Outputs, daily:** percent of ascospores mature (and discharged, if kept), the infection level of any wet period ending that day (none, light, moderate, heavy), its hours and mean temperature, and risk = that level while ascospores remain. At points, each wet period in `meta.summary` as well.
- **Maps:** a daily ingredient computed in the hourly rollup: the infection level of each wet period ending that day, looking back over the hours before it (bounded, e.g. 72 h, as "from 6 pm" features already look into the day before). Option: points first and maps later, if the rollup's lookback is more than this part should carry (question 2).
- Checked against NEWA's results at Wisconsin stations for 2025–2026 (if we can read them; question 6) and MSU's no-sensor table at a Michigan station.

**B3. `fire-blight`** (blossom blight, from first bloom to petal fall).

- **Cougarblight 2010** (Smith, WSU) as the risk: hourly risk values from temperature, summed over the last 96 hours, against thresholds that depend on the orchard's fire blight history (an option: none nearby, nearby last year, in the orchard last year, active now), with wetting (rain or dew) needed for infection. Maps from a daily ingredient (the day's hourly risk sum); the 4-day total is a running window.
- **MaryBlyt's EIP** (Steiner 1990) as a second output: degree hours above 65 °F over the blossoms' life (80 DD°F base 40), with its cold-day carry-overs, EIP ≥ 100 as a condition, and the four conditions (blossoms open, EIP ≥ 100, wetting, mean ≥ 60 °F). EIP carries state from day to day, so it's points first; maps if it can be written as a kernel over the window.
- **Wetting:** rain ≥ 0.01 in that day (or ≥ 0.10 in the day before, MaryBlyt's), or dew estimated from the weather (Ben: dew point depression as well as RH; the leaf wetness estimate shared with scab, above).
- **Bloom window:** from `apple-stages` (first bloom to petal fall; MSU uses pink to first cover, which runs ~240 DD past petal fall) or the grower's first blossom date at points.
- Left out: trauma blight (a grower's event: hail, a storm); the symptom date (103 DD°F base 55 after infection) can be an output if Steiner gives it.
- Checked against NEWA's Cougarblight and EIP at Wisconsin stations, and MSU's.

**B4. `codling-moth`** (an insect, D36 if the source allows).

- Degree days base 50 °F, upper 88 °F, single sine with a horizontal cutoff, from a biofix at first sustained trap catch (Riedl et al. 1976); without one, an estimated biofix (MSU: 200 DD°F base 50 from March 1; find a published estimate).
- Stages from the biofix: first generation egg laying, first hatch, 20 % hatch, peak egg laying; second generation from the same biofix (MSU counts it from March 1, likely a bug; check its numbers against the source).
- **D36 curves or a stage table:** Washington's model (Jones et al.) gives cumulative egg hatch and adult emergence curves, which fit D36's life stages with action windows (first hatch to 20 %, the usual spray window); MSU's is a stage table (question 4).
- Checked against UW's codling moth trap reports where they give biofix and flights, and WSU DAS's curves on the same weather.

**Sources to get** (Ben, for those behind paywalls; into `tmp/references/apple/`): MacHardy and Gadoury 1989; Stensvand et al. 1997; Gadoury and MacHardy 1982; the "Jones" ascospore discharge paper; Steiner 1990 and its companion (Acta Hort. 273:149–158); Smith's Cougarblight 2010 documentation (WSU, free); Riedl and Croft 1974, Riedl et al. 1976; Jones et al.'s codling moth model; a published apple stage table at base 43 °F (or 42).

**Risks:** the papers (tables have to be read from them exactly); hourly wetness rules on the grid (the rollup's lookback); Wisconsin users comparing with NEWA station by station (differences have to be explainable); fire blight's thresholds come from the Pacific Northwest (Cougarblight) and the mid-Atlantic (MaryBlyt).

**Sources to get (added 2026-11-17):** Gillespie, Srivastava and Pitblado (1993) on dew point depression; Sentelhas et al. (2008); Montone et al. (2016); WSU DAS's documentation of its codling moth, fire blight and scab models.

**Alternatives weighed:** follow MSU's code throughout (simplest to port, but base 42 °F and MaryBlyt only would differ from what Wisconsin growers see in NEWA); points only for every model (simpler, but the grid between stations is our reason to exist for fruit growers).

**Ben's answers (2026-11-17):**

- NEWA is the gold standard where sources conflict, above Enviroweather's code and even above VDIFN (Ben's own): recorded as D95 and in this plan's rules. So: base 43 °F stages, Revised Mills, Cougarblight with EIP, as NEWA runs them.
- Fire blight's wetting: look at dew point depression (air temperature against dew point) as well as RH to identify likely leaf wetness; find what's published (above: Gillespie et al. 1993, Sentelhas et al. 2008, Montone et al. 2016). Plan: estimate wet hours by the method the comparisons favour for humid continental climates, use the same estimate in scab and fire blight, and check it against leaf wetness sensors if any Wisconsin network has them (Wisconet, NEWA's stations).
- Codling moth by smooth emergence curves (D36), from WSU's model.
- Harvest dates: out of scope.
- Review: ask UW's fruit team, but don't depend on it; validate against NEWA ourselves (B5).
- MSU won't share tables or newer code: rebuild from the papers.
- Credit Enviroweather by citing its website as a source.

**B5. Validation against NEWA** (first, since it decides what "right" means for B1–B4): find whether NEWA's hourly station data and model results for Wisconsin's ~30 stations can be read (NRCC's hourly service, NEWA's pages, or asking NRCC); if so, run each of our models on a station's own hours (`POST /models/{id}/run` takes station weather) and compare with NEWA's results there for 2024–2026, then compare our grid's results at the station's cell. Differences on the same weather are ours to explain or fix; differences between station and grid are the weather's (the validation docs' kind). Recorded in `docs/validation-apple.md`.

**Questions for Ben (answered above):**

1. **NEWA or MSU where they differ:** recommend NEWA's methods (base 43 °F stages, Revised Mills, Cougarblight with EIP) since Wisconsin growers and UW Extension use NEWA, with MSU's code as the structure and credit where we use it.
2. **Scab on maps:** a daily ingredient with a bounded lookback in this part (recommended), or points first?
3. **Fire blight wetting:** rain only, as MaryBlyt and MSU have it, or RH ≥ 90 % hours standing in for dew?
4. **Codling moth:** D36 curves from Washington's model (recommended, if the paper gives them), or MSU's stage table?
5. **Harvest maturity** left out of this part?
6. **Checking against NEWA:** may we read NEWA's published results for Wisconsin stations to compare (their terms), and should UW's fruit team (Amaya Atucha) review the apple models before they're marked stable?

### C. Cranberry fruitworm (stub)

Priority 1 in the inventory: Wisconsin grows most of the US crop. MSU's thresholds (biofix 350 DD°F base 50 from March 1; egg laying 85–485 DD after) may come from blueberry, and the egg-laying curve is in MSU's database. Plan: find Wisconsin cranberry research (UW's cranberry entomology) before porting anything.

### D. Tart cherry (stub)

Cherry phenology, cherry leaf spot (its table missing; Eisensmith and Jones to verify), plum curculio, cherry fruitworm: Door County. `cherry` is in `croplist`; tart and sweet may need separating.

### E. The rest of Enviroweather's ports (stub)

In the inventory's order: plum curculio in apple, apple maggot, obliquebanded leafroller, oriental fruit moth, sooty blotch; grape berry moth (day length at 1620 DD); Christmas trees (Fraser fir growth, Cooley and eastern spruce gall adelgids, pine sawfly and pine needle scale); spongy moth egg hatch; then priority 3 (blueberry, tussock moth, SWD fruit susceptibility, peach harvest, berry weight, landscape scales, asparagus miner).

### F. Where Enviroweather overlaps our models (stub)

Compare and record which thresholds we keep (with the 25 insects' review, part H): alfalfa cutting (MSU: average base 41 °F, no upper, from March 1, 680/750/970 by silo type; ours: sine 41/86 from January 1 or the last cut, 900–1100), alfalfa weevil (MSU 300/439/596/820 base 48 from January 1, with stage resets; ours 300/440/595/815), Colorado potato beetle (MSU base 52 from March 1, generation 2 numbers inconsistent with its own table; ours base 50), European corn borer (MSU flights 450–950, 1450–1950, 2450–2950 base 50 from March 1, "rough numbers"), seedcorn maggot (MSU base 39 from March 1, first peak 342 as ours, generation 1 peak 892 DD later against our 720), squash vine borer (MSU flight to 2000 DD; ours ends at 1000), variegated cutworm (900 DD in both; MSU from March 1, ours May 1), cabbage maggot (MSU base 43 from March 1, spring peak 565–716), TOMCAST (MSU sums DSV per wet period, a period ending after two dry hours, 0 above 29 °C, a total since the last spray; ours RH ≥ 90 % hours from 6 pm, the 26–29 °C row above 29, a 7-day total; MSU's RH fallback never runs and 21- or 23-hour periods score 0), spotted wing drosophila (MSU's is tart cherry susceptibility with spray wash-off; complements ours).

### G. Other insect models (stub)

From PLAN.md (moved here 2026-11-17, verbatim):

> **Other insect models.** A survey of published degree-day models for Upper Midwest pests that neither we nor Enviroweather have (USPest/DDRP, UC IPM, NEWA, USA-NPN, state extension, the journals), listed in `docs/insect-models.md` with each source and its method, ranked by the crops readers grow; then the ports in that order.

### H. The other 25 insects' review (stub)

From PLAN.md (moved here 2026-11-17, verbatim):

> **The other 25 insects' review** (moved here from the model review, 2026-11-17, since this step reads the same sources): each with a version bump and its source's degree-day method checked (Phase 3 D 8, D37; `docs/insect-models.md`).

Also from step 3 (D94): the 24 insects on VDIFN's rounded sine ramp move to D36's curves where their sources allow; life stages get ids (events take stage numbers until then).

### I. A write-up for each model (stub)

From PLAN.md (moved here 2026-11-17, verbatim):

> **A write-up for each model** (a research project; moved here from Phase 7's "Model page content" and the model review's content item, 2026-11-17). For every model, old and new: what it predicts and for whom; the pest or disease (identification, life cycle, damage, conditions that favour it, monitoring, management); how to read the model and what to do at each risk level; its research basis, validation and limits (the region and season it was developed for); acknowledgments. Synthesized across extension publications and trusted sources (university extension, USDA, peer-reviewed work), cited, and never copied from one source: each fact traceable to a citation, the wording our own, in CLAUDE.md's "Writing for the public". Kept as structured content beside each model (D31's Markdown with front matter: the risk-level guidance, susceptible stages and valid-use warning as fields, served by `/models/{id}`); the method itself still comes from the spec (Methods derived from the code). Process, planned first: a template and one worked example (seedcorn maggot's drafts are a start) for Ben to approve; then batches, each write-up with its source list, a check of every claim against its source, and a review by Ben or the topic's specialist before it's marked done. Batches can run as forks or a workflow if Ben opts in.

### J. Winter wheat (stub)

Enviroweather's is a stub (no thresholds; only a plan for base 0 °C from planting and green-up as the first 7 days in a row with degree days above 0). Leads from Phase 3: McMaster's PhenologyMMS and McMaster and Wilhelm (base 0 °C, a 25 °C cap); also spring wheat's grain fill and wheat scab's gate at flowering (PLAN.md's model review, "Wheat").

### K. Features the displays suggest (for Phase 7 or 9; not this step)

A frost-night view and alert at saved sites (hourly temperature and dew point at or below 32, 30 and 28 °F); heat index (Rothfusz, T ≥ 80 °F, RH ≥ 40 %, dew point ≥ 60 °F) and wind chill; spray conditions (an inversion needs two heights; a proxy from clear, calm evenings); totals over the last 7, 14 and 30 days; rain-hour counts; comparing saved sites side by side; a days-ahead-of-normal map (points only now); a potato field stress view (hot days at 88 °F, heavy rain at 1.5 in, high ET at 0.25 in, warm nights) once soil moisture lands (step 6).
