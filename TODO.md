# TODO (Ben)

Things only you can do, by phase. Details are in [PLAN.md](PLAN.md). In progress marked [-]; finished items are deleted (git history keeps them).

## Phase 3: Model library (the insects now wait on `docs/models-plan.md` part H)

- [ ] **Two insect papers still missing** from `tmp/references/insects/` (the rest of D8 step 4's list arrived 2026-11-17):
  - Eckenrode and Chapman 1971, cabbage maggot lab development, [10.1093/aesa/64.5.1079](https://doi.org/10.1093/aesa/64.5.1079)
  - Harcourt 1981, alfalfa weevil (USPest's source), [10.4039/Ent113601-7](https://doi.org/10.4039/Ent113601-7)
  - The rest (asparagus beetle, corn rootworm, crucifer flea beetle, Lygus, SWD lab data) are under "Papers to find" in [docs/insect-models.md](docs/insect-models.md).
- [ ] **Reports with no DOI** (cited by USPest; probably Oregon State or USDA reports): Coop and Berry 1987 (variegated cutworm in peppermint); Berry et al. (mint flea beetle and mint root borer); Simko 2000 (Lygus in alfalfa seed); Hartstack et al. 1976 (MOTHZV-2, corn earworm).
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

- [ ] **Colorado potato beetle fits' predicted values** (2026-11-18): from each of the four GAMs in `tmp/cpb/CPB GAM fit - all.png` (adults, egg masses, larvae, adults + larvae), the fitted log count every 10 degree days (52/86 °F) from 0 to 2,400, with the standard error if handy, into one CSV in `tmp/cpb/` (columns `dd`, `adults`, `eggs`, `larvae`, `adults_larvae`). For example, `data.frame(dd = seq(0, 2400, 10)) |> transform(adults = predict(fit_adults, newdata = data.frame(x = dd)))` for each. The model's rebuild waits on it (`docs/models-plan.md` part H).

- [ ] **Wisconsin codling moth trap records** (optional now): DATCP's trap network (weekly counts at 25–29 orchards, 2020–2025, in its published summaries) already checks the default first catch; UW's records would add daily-checked sites, if the fruit program has them.
- [ ] **Email NEWA** (newa@cornell-ipm.org) as a courtesy: our validation reports (`docs/validation/models/`) publish comparisons with its models on its stations' public data, with credit (D98). Worth telling them too, as a courtesy: some Wisconsin stations' rain gauges recorded almost nothing in 2024–2025 while the archive had a normal spring (Gays Mills about 10 % of the archive's April–June rain in 2024 and 2 % in 2025, Genoa City 2025 about 1 %, Fort Atkinson 2024 about 26 %), which keeps their apple scab season open. The request: we'd like to read the Wisconsin stations' hours (one request per station-season, 2024–2026, kept) to validate AgWeather's apple models against NEWA's, and publish the comparison with credit. Ask them to confirm the points we read from their site's code: the single sine uses `Math.sin` where Baskerville–Emin has `asin`; Cougarblight counts no hour below 60 °F though Smith's 2010 version starts at 50 °F; fire blight's default first blossom is 230 DD43 though their stage table puts bloom at 346; Cougarblight's "no blight nearby" threshold of 300 (Smith and Pusey 2011 give 500, WSU 400); and codling moth's default first catch at 404 DD and second flight at 1501 DD (published first catches in the Northeast and Michigan run 230–280 DD°F).
- [ ] **Optional: check chill against chillR itself** (2026-11-10). The Dynamic model is tested against a line-by-line port of chillR's code; Claude wasn't allowed to run code it downloaded, so a direct comparison waits for you. chillR needn't be installed: its model functions are plain R.

  ```bash
  cd /tmp && curl -LO https://cran.r-project.org/src/contrib/Archive/chillR/chillR_0.75.tar.gz && tar xzf chillR_0.75.tar.gz
  cd ~/code/agweather2
  Rscript packages/agmodels/tests/fixtures/make_chillr_reference.R /tmp/chillR/R/temp_models.R \
    packages/agmodels/tests/fixtures/chillr_reference.csv
  uv run pytest packages/agmodels/tests/test_chill_livestock.py   # test_all_three_match_chillr_itself then runs
  ```

  Commit the CSV if it passes.

## Phase 8: On the server, and launch

- [ ] **The apple models' daily features** (2026-11-18, D96): after the code is deployed, `uv run app/manage.py rebuild --check`, then `uv run app/manage.py rebuild --stale --background` until nothing is stale (ten new daily variables for apple scab and fire blight in every year; over an hour and a half a pass on the dev archive over Wisconsin, so much longer over the launch box).
- [ ] **Copernicus key:** put `COPERNICUS_API_KEY` in the server's `infra/.env` before the ERA5-Land job runs there.
- [ ] **The season-read copy:** run `uv run app/manage.py timecopy` once after the archive is copied to the server.
- [ ] **Water and terrain** (2026-11-11; PLAN.md Phase 6 D6): `uv run app/manage.py terrain --check`, then `uv run app/manage.py terrain --background`. It downloads NHDPlus V2.1's archives for the service box (~2.3 GB for Wisconsin's units 04, 07 and 09; the launch box needs more units added to `agdata.terrain.UNITS` first, with their extents measured from the rasters) and builds `data/terrain.zarr` (~3 min and 153 MB over Wisconsin). The web process picks it up without a restart.
- [ ] **The 30-year climatology** (2026-11-11; PLAN.md Phase 6 D3–D4). Once the server's archive is full from 2016: `uv run app/manage.py climatology --check`, then `uv run app/manage.py climatology --background`. It downloads gridMET's 1996–2025 over the service box (the box's part of each file; ~1.8 h over Wisconsin, so expect much longer over the launch box), fits the adjustment, derives 1996–2015 and builds the `last5`, `last10` and `last30` normal maps (~9 GB a period at the launch box, several hours each). A monthly job (`update_climatology`, the 15th at 06:00) keeps it current after that.
- [ ] **The legacy host** (D62), with IT: DNS for `legacy.agweather.cals.wisc.edu` pointing at the old server, its TLS certificate, and nginx's `server_name` on the old server answering to it. Check v1 serves its API there before `agweather.cals.wisc.edu` moves to v2.

## Any time

- [ ] Optional: tell your department (or WARF) that AgWeather v2 and WISP 3 are public under AGPL-3.0, since the Regents hold the copyright.
