# TODO (Ben)

Things only you can do, by phase. Where things stand and why: [PLAN.md](the plans, `docs/plans/`), [docs/decisions.md](docs/decisions.md) and [docs/plans/](docs/plans/). In progress marked [-]; finished items are deleted (git history keeps them).

## Phase 3: Model library (the insects now wait on `docs/plans/models.md` part H)

- [ ] **Two insect papers still missing** from `tmp/references/insects/` (the rest of D8 step 4's list arrived 2026-11-17):
  - Eckenrode and Chapman 1971, cabbage maggot lab development, [10.1093/aesa/64.5.1079](https://doi.org/10.1093/aesa/64.5.1079)
  - Harcourt 1981, alfalfa weevil (USPest's source), [10.4039/Ent113601-7](https://doi.org/10.4039/Ent113601-7)
  - The rest (asparagus beetle, corn rootworm, crucifer flea beetle, Lygus, SWD lab data) are under "Papers to find" in [docs/insect-models.md](docs/insect-models.md).
- [ ] **Reports with no DOI** (cited by USPest; probably Oregon State or USDA reports): Coop 1987 (a thesis; see part H's papers below); Berry et al. (mint flea beetle and mint root borer); Simko 2000 (Lygus in alfalfa seed); Hartstack et al. 1976 (MOTHZV-2, corn earworm).
- [ ] **Questions on the insects** (answers go in `docs/insect-models.md`):
  - What is "XHT1087", the spreadsheet's source for imported cabbageworm and onion maggot?
  - Aphid PVY vectors and Colorado potato beetle (your analyses): which degree-day method, biofix and data did each fit use? Are VDIFN's CPB adult and larval models (50/86 °F) yours too, as cited now?
  - Variegated cutworm: the events are Coop and Berry's at 41/88 °F, but VDIFN runs them at Simonet's 45/80.1. Keep Coop and Berry's pair, or rebuild on Simonet?
  - Tarnished plant bug: the model is for _Lygus hesperus_ (Oregon and Idaho alfalfa seed). Keep it, or look for an _L. lineolaris_ model?
  - Cabbage maggot: the Wisconsin source (Eckenrode and Chapman, modified average at 43 °F) or USPest's Oregon State model (sine at 39.7/86 °F)?
  - Black cutworm, cabbage looper, corn earworm: their biofixes stand for trap catches or first silk. Default dates with a user-set biofix (as now), or something else?
- [ ] **UW Vegetable Entomology's seedcorn maggot page** still says to count from spring ground thaw at 39/86 °F, with VDIFN's 360 + 720n peaks. Update it to match seedcorn maggot 2.0 (average method, 39 °F with an 84 °F cap, from January 1) once the new model is reviewed.

## Phase 5: API v2 (callers of v1)

- [ ] Name the callers still unknown (the two .NET clients), and send each caller the new URLs before launch (from the nginx logs of 2026-10-19 to 11-02, `tmp/v1-logs/access.log`):

  - `165.189.65.24` (State of Wisconsin; was `165.189.255.59` in 2024): DATCP. Unchanged: 8 degree-day settings × 23 points, 184 requests every morning at 08:00–09:00, January 1 to yesterday.
  - `52.36.85.186` (AWS, "Ruby"): the current AgWeather website (12,868). v2 replaces it.
  - `216.105.223.230` ("RestSharp", .NET): ET at one point (44.1188, −89.5333), last 30 days, both classic and `method=adjusted` (Desai & Talib's emissivity), ~93 a day around the clock (1,392). Polls far more than daily data needs.
  - `71.13.161.79` ("RestSharp"): ET at 28 points, last 10 days, daily at 09:00 (420). An irrigation scheduler?
  - **Nortera** ("Nortera-Production-Tracker/1.0", through Cloudflare 104.23.160.x): sine 50/86 degree days from May 1, and precip, at 8 points daily at 06:00 (109 in 7 days). A vegetable processor: worth a direct email.
  - `waunakee-lawn-notifier (eli@solow.org)`: `dd_table` (`dd_50_86`, `dd_32`) and precip at one point, twice a day (68). Has a contact address in its user agent.
  - Veg Path (`pest_forecasts/vegpath` from AWS 3.19.85.241 and 18.221.246.67; 753): Ben's WordPress site for the UW Vegetable Pathology lab, through wpDataTables (weather and early/late blight charts for 7 Wisconsin locations).
  - `144.92.74.104` ("httr2", UW campus Posit Connect): Ben's alfalfa Shiny app, `/api/weather/grid?date=…` about once a day. Replaced by v2's alfalfa tool.
  - UW Insect Diagnostic Lab (https://insectlab.russell.wisc.edu/): links "Today's Growing Degree Day Map" to v1's `/api/degree_days/map.png`. Once v2 is live, ask them to switch to `/api/v2/maps/dd_modified_50_86.png` (v1's path redirects to the legacy host for a year, D62).
  - `146.151.193.173` ("python-requests", 2026-10-28 and 29): our own Phase 2 comparisons of v2 against the old API.
  - The rest is scanners (`/api/.env`, `/api/mcp`) and a few one-off browsers.

## Phase 6: Frontend plan and the data behind it

- [ ] **Ask the model authors** (2026-11-18; questions in `tmp/crt-model-audit.md`): Smith and Webster on gray leaf spot (the intercept, the units, the missing second model, the data: the spec's equation reads ~99 % all summer) and on soybean Cercospora's wind unit (m/s in the spec, km/h in the fit); Paul's group at Ohio State on DON (15-day windows, the rain-day threshold, the risk bands); Webster on tar spot's moving-average alignment and RH > 90 % against ≥ 90 %.
- [ ] **Your UW sites' corrections** (2026-11-18): the checklist `tmp/vegsites-corrections.md` (88+ items: errors, dated text, dead links, pages to add, and what changes when AgWeather launches). A few need your call: late blight's spore temperatures (54–75 °F, as you said), cabbage maggot transplant timing (your pages against A3422), the Colorado potato beetle generation names, the PVY page's oil trigger and its 2024 guidelines.
- [x] **The PVY index's weighting** (2026-11-18): settled 2026-11-21, each species weighted by its transmission efficiency (`aphid-pvy-vectors` 0.3, D101).

- [ ] **Rebuild the models' stored inputs on the dev archive** (2026-11-19): white mold 0.2 dropped one, DON 0.2 added one, and other models changed today; `uv run app/manage.py ingredients --check` lists 19 stale per year (2016–2026). Run `uv run app/manage.py ingredients --background` when the machine is free (maps of those models read the stale ones until then).
- [ ] **Part H's papers** (decisions answered 2026-11-23). Into `tmp/references/insects/`; DOIs checked on Crossref and resolved at doi.org on 2026-11-23. Wisconsin trap or scouting counts for cabbage maggot, cabbage looper or cabbageworm would also test the rebuilt models.
  - **First (they'd change a model):**
    - Apple 1952, European corn borer and temperature on canning corn (corn borer's `trained` years rest on it), *J. Econ. Entomol.* 45: 877–879, [10.1093/jee/45.5.877](https://doi.org/10.1093/jee/45.5.877)
    - Hoard and Weiss 1995, corn borer's postdiapause development and voltinism in North Dakota (the univoltine north), *Environ. Entomol.* 24: 564–570, [10.1093/ee/24.3.564](https://doi.org/10.1093/ee/24.3.564)
    - Showers et al. 1975, ecotypes of the European corn borer in North America, *Environ. Entomol.* 4: 753–760, [10.1093/ee/4.5.753](https://doi.org/10.1093/ee/4.5.753)
    - Nealis, Jones and Wellington 1984, temperature and development, *Pieris rapae* and its parasitoid (would replace cabbageworm's judgments), *Oecologia* 61: 224–229, [10.1007/BF00396765](https://doi.org/10.1007/BF00396765)
    - Apple, Walgenbach and Knee 1971, northern corn rootworm egg hatch, *J. Econ. Entomol.* 64: 853–856, [10.1093/jee/64.4.853](https://doi.org/10.1093/jee/64.4.853)
    - Eckenrode and Chapman 1972, cabbage maggot flights and thermal units in Wisconsin, *Ann. Entomol. Soc. Am.* 65: 151–156, [10.1093/aesa/65.1.151](https://doi.org/10.1093/aesa/65.1.151)
    - Jyoti, Shelton and Barnard 2003, cabbage maggot emergence models in New York (NEWA's table), *J. Entomol. Sci.* 38: 525–532, [10.18474/0749-8004-38.4.525](https://doi.org/10.18474/0749-8004-38.4.525)
  - **Then:**
    - Chiang and Sisson 1968, northern corn rootworm eggs and temperature, *J. Econ. Entomol.* 61: 1406–1410, [10.1093/jee/61.5.1406](https://doi.org/10.1093/jee/61.5.1406)
    - Jackson and Elliott 1988, western corn rootworm development, *Environ. Entomol.* 17: 166–171, [10.1093/ee/17.2.166](https://doi.org/10.1093/ee/17.2.166)
    - Davis, Brenes and Allee 1996, corn rootworm phenology models, *Environ. Entomol.* 25: 767–775, [10.1093/ee/25.4.767](https://doi.org/10.1093/ee/25.4.767)
    - Funderburk, Higley and Pedigo 1984, seedcorn maggot phenology in Iowa, *Environ. Entomol.* 13: 105–109, [10.1093/ee/13.1.105](https://doi.org/10.1093/ee/13.1.105)
    - Throne and Eckenrode 1985, seedcorn maggot emergence, *Environ. Entomol.* 14: 182–186, [10.1093/ee/14.2.182](https://doi.org/10.1093/ee/14.2.182)
    - Sanborn, Wyman and Chapman 1982, seedcorn maggot thresholds and heat units, *Ann. Entomol. Soc. Am.* 75: 103–106, [10.1093/aesa/75.1.103](https://doi.org/10.1093/aesa/75.1.103)
    - Kaster and Showers 1984, black cutworm field development in Iowa, *Environ. Entomol.* 13: 384–389, [10.1093/ee/13.2.384](https://doi.org/10.1093/ee/13.2.384)
    - Story, Keaster, Showers and Shaw 1984, cutworms in Midwest field corn, *J. Econ. Entomol.* 77: 491–494, [10.1093/jee/77.2.491](https://doi.org/10.1093/jee/77.2.491)
    - Coop, Croft and Drapek 1993, corn earworm in sweet corn, *J. Econ. Entomol.* 86: 906–916, [10.1093/jee/86.3.906](https://doi.org/10.1093/jee/86.3.906)
    - Lasack and Pedigo 1986, stalk borer larvae moving into corn, *J. Econ. Entomol.* 79: 1697–1702, [10.1093/jee/79.6.1697](https://doi.org/10.1093/jee/79.6.1697) (its development curves: Lasack, Bailey and Pedigo 1987, [10.1093/ee/16.1.296](https://doi.org/10.1093/ee/16.1.296))
    - Taylor and Harcourt 1978, asparagus beetle development and temperature, *Can. Entomol.* 110: 57–62, [10.4039/Ent11057-1](https://doi.org/10.4039/Ent11057-1)
    - Kinoshita, Svec, Harris and McEwen 1979, crucifer flea beetle in Ontario, *Can. Entomol.* 111: 1395–1407, [10.4039/Ent1111395-12](https://doi.org/10.4039/Ent1111395-12)
    - Ulmer and Dosdall 2006, crucifer flea beetle emergence, *Crop Protection* 25: 23–30, [10.1016/j.cropro.2005.03.003](https://doi.org/10.1016/j.cropro.2005.03.003)
    - Tatchell 1981, granulosis virus, temperature and *Pieris rapae*'s feeding, *Entomophaga* 26: 291–299, [10.1007/BF02371879](https://doi.org/10.1007/BF02371879)
  - **Lower now that `tarnished-plant-bug` is retired:** Ugine 2012, [10.1603/EN10210](https://doi.org/10.1603/EN10210); Fleischer and Gaylor 1988, [10.1093/ee/17.2.246](https://doi.org/10.1093/ee/17.2.246).
  - **No DOI (library or the authors):**
    - Sanborn 1981, PhD dissertation, UW–Madison (seedcorn maggot; ProQuest or UW's library).
    - Coop 1987, *Management of Variegated Cutworm in Peppermint*, PhD thesis, Oregon State University (the 41/88 °F model; abstract at uspest.org/mint/coop1987.htm). There is no Coop and Berry paper on the model; their 1986 paper is on parasitoids.
    - Berry, Takeyasu and Morris 1997 (mint root borer): probably an Oregon State progress report; ask OSU Entomology or the Oregon Mint Commission.
    - Andaloro, Rose and Eckenrode 1984 (onion maggot, NEWA's source): probably a Cornell/Geneva bulletin; Cornell's eCommons.
    - Hartstack et al. 1976, MOTHZV-2, USDA ARS-S-127 (NAL's catalog).
    - NCR 327, *European Corn Borer: Ecology and Management*, 2018 revision (Iowa State Extension store, $8).
- [ ] **On the server after part H is deployed** (2026-11-21): `uv run app/manage.py rebuild --check`, then `uv run app/manage.py rebuild --stale --background` (the new simple averages at 40 and 48 °F, ~45 min over Wisconsin's 11 years), then `uv run app/manage.py ingredients --check` and `uv run app/manage.py ingredients --background` (western bean cutworm's own degree days). Done on the dev archive 2026-11-21.
- [ ] **Wisconsin codling moth trap records** (optional now): DATCP's trap network (weekly counts at 25–29 orchards, 2020–2025, in its published summaries) already checks the default first catch; UW's records would add daily-checked sites, if the fruit program has them.
- [ ] **Email NEWA** (newa@cornell-ipm.org) as a courtesy: Part H adds (2026-11-21, `docs/plans/models.md` handoff, Next item 2): the maggot pages' "BE" labels (the code runs the simple average); western bean cutworm's deployed code (caps the maximum, swaps two arguments); seedcorn maggot's °F studies read as °C·d; the cabbage maggot table's 75 % (547 against Jyoti et al.'s 536) and "ends 809"; the 404 More Info images. our validation reports (`docs/validation/models/`) publish comparisons with its models on its stations' public data, with credit (D98). Worth telling them too, as a courtesy: some Wisconsin stations' rain gauges recorded almost nothing in 2024–2025 while the archive had a normal spring (Gays Mills about 10 % of the archive's April–June rain in 2024 and 2 % in 2025, Genoa City 2025 about 1 %, Fort Atkinson 2024 about 26 %), which keeps their apple scab season open. The request: we'd like to read the Wisconsin stations' hours (one request per station-season, 2024–2026, kept) to validate AgWeather's apple models against NEWA's, and publish the comparison with credit. Ask them to confirm the points we read from their site's code: the single sine uses `Math.sin` where Baskerville–Emin has `asin`; Cougarblight counts no hour below 60 °F though Smith's 2010 version starts at 50 °F; fire blight's default first blossom is 230 DD43 though their stage table puts bloom at 346; Cougarblight's "no blight nearby" threshold of 300 (Smith and Pusey 2011 give 500, WSU 400); and codling moth's default first catch at 404 DD and second flight at 1501 DD (published first catches in the Northeast and Michigan run 230–280 DD°F).
- [ ] **Optional: check chill against chillR itself** (2026-11-10). The Dynamic model is tested against a line-by-line port of chillR's code; Claude wasn't allowed to run code it downloaded, so a direct comparison waits for you. chillR needn't be installed: its model functions are plain R.

  ```bash
  cd /tmp && curl -LO https://cran.r-project.org/src/contrib/Archive/chillR/chillR_0.75.tar.gz && tar xzf chillR_0.75.tar.gz
  cd ~/code/agweather2
  Rscript packages/agmodels/tests/fixtures/make_chillr_reference.R /tmp/chillR/R/temp_models.R \
    packages/agmodels/tests/fixtures/chillr_reference.csv
  uv run pytest packages/agmodels/tests/test_chill_livestock.py   # test_all_three_match_chillr_itself then runs
  ```

  Commit the CSV if it passes.

## Backburner (time-consuming; not soon)

- [ ] **Onion thrips data** (2026-11-19, for the planned model in `docs/plans/models.md` part G): your lab's untreated-check onion thrips counts by date and site, with spray dates and irrigation records, to fit a base and test a heavy-rain term.
- [ ] **Spotted wing drosophila refit** (2026-11-19): check three trap-seasons that look copied (P Mulch and P Plant Path 2016 and 2018; P Fence and Seaq Hiland 2017) against the field sheets; decide whether the model holds at its peak after it (rather than the fitted decline, which rests on 2015 alone); newer trap counts (berries, into October, outside Door County) when you find them.

## Phase 8: On the server, and launch

- [ ] **Pecan scab's daily feature at 88 %** (2026-11-19, D100): `hours_rh_over_90_temperature_over_70f` went to version 2, so `uv run app/manage.py rebuild --check`, then `uv run app/manage.py rebuild --stale --background` until nothing is stale (one daily variable in every year).
- [ ] **The apple models' daily features** (2026-11-18, D96): after the code is deployed, `uv run app/manage.py rebuild --check`, then `uv run app/manage.py rebuild --stale --background` until nothing is stale (ten new daily variables for apple scab and fire blight in every year; over an hour and a half a pass on the dev archive over Wisconsin, so much longer over the launch box).
- [ ] **Copernicus key:** put `COPERNICUS_API_KEY` in the server's `infra/.env` before the ERA5-Land job runs there.
- [ ] **The season-read copy:** run `uv run app/manage.py timecopy` once after the archive is copied to the server.
- [ ] **Water and terrain** (2026-11-11; Phase 6 D6): `uv run app/manage.py terrain --check`, then `uv run app/manage.py terrain --background`. It downloads NHDPlus V2.1's archives for the service box (~2.3 GB for Wisconsin's units 04, 07 and 09; the launch box needs more units added to `agdata.terrain.UNITS` first, with their extents measured from the rasters) and builds `data/terrain.zarr` (~3 min and 153 MB over Wisconsin). The web process picks it up without a restart.
- [ ] **The 30-year climatology** (2026-11-11; Phase 6 D3–D4). Once the server's archive is full from 2016: `uv run app/manage.py climatology --check`, then `uv run app/manage.py climatology --background`. It downloads gridMET's 1996–2025 over the service box (the box's part of each file; ~1.8 h over Wisconsin, so expect much longer over the launch box), fits the adjustment, derives 1996–2015 and builds the `last5`, `last10` and `last30` normal maps (~9 GB a period at the launch box, several hours each). A monthly job (`update_climatology`, the 15th at 06:00) keeps it current after that.
- [ ] **The legacy host** (D62), with IT: DNS for `legacy.agweather.cals.wisc.edu` pointing at the old server, its TLS certificate, and nginx's `server_name` on the old server answering to it. Check v1 serves its API there before `agweather.cals.wisc.edu` moves to v2.

## Any time

- [ ] Optional: tell your department (or WARF) that AgWeather v2 and WISP 3 are public under AGPL-3.0, since the Regents hold the copyright.
