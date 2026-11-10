# TODO (Ben)

Things only you can do, by phase. Details are in [PLAN.md](PLAN.md). In progress marked [-], completed marked [x].

## Phase 1: Foundations

- [x] **Install uv** (Python and the workspace; it downloads Python 3.13 itself):
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- [x] **Install Docker** in WSL, either Docker Desktop on Windows with WSL integration turned on for this distro, or Docker Engine inside WSL (`sudo apt install docker.io docker-compose-v2`, then `sudo usermod -aG docker $USER`). Only needed for Phase 1 E (containers); day-to-day development runs natively.
  - [x] The socket still says "permission denied": open a new WSL terminal (or `newgrp docker`) so the `docker` group applies, then check with `docker run --rm hello-world`.
- [x] **Create the GitHub repo** (`uwent/agweather2`, public; PLAN.md Q3), then add it as `origin`.
- [x] Answer PLAN.md Q1–Q3 (now D17–D19).
- [x] ~~**Server request to IT**~~ superseded by Phase 5's `docs/server-sizing.md` item below (2026-11-02). (Phase 1 gate; IT is setting up infrastructure as of 2026-10-27): the Server requirements section of `docs/project-plan.md`, with EC2, the EBS data volume and RDS in the same region and AZ. The pilot (`docs/pilot.md`) confirms the sizes:
  - Data volume: **1 TB gp3** holds the Upper Midwest's 11 years (about 510 GB: 342 GB hourly, the rest daily, cumulative and climatology). CONUS later needs 2–3 TB, or older years in S3.
  - The 11-year backfill downloads about 4 TB from NOAA's bucket; from inside AWS that takes hours, not the ~5 days it would take from campus or home. A temporary scale-up for it (16–32 vCPU for a day or two) still stands.
  - Hourly ingest is light: about 40 MB downloaded and under a minute of work per hour for the Upper Midwest.
- [x] Optional: put the Open-Meteo API key in `.env` as `OPEN_METEO_API_KEY` (needed from Phase 4).

## Phase 2: Hourly archive

- [x] **Decide the local backfill range:** 2025-01-01 to now (decided 2026-10-28). About 0.8 TB of downloads; it runs at about 6 s per hour of data here (about 27 hours in all) with 1.3 GB of memory.
- [x] **Let the backfill finish** (started 2026-10-28; finished 2026-10-28 20:05, before the 2026-10-29 WSL crash; `data/write.lock` still names its pid, which is harmless). Only one runs at a time (a second one exits naming the first's pid), and rerunning resumes, skipping complete 5-day blocks:

  ```bash
  cd ~/code/agweather2
  setsid nohup uv run app/manage.py backfill --start 2025-01-01 --end 2026-10-28 > tmp/backfill.log 2>&1 < /dev/null &
  tail -f tmp/backfill.log            # a line every 6 hours of data, with time left; Ctrl-C stops watching, not the backfill
  pgrep -af 'manage.py backfill'      # is it running?
  cat data/write.lock                 # its pid
  kill $(cat data/write.lock)         # stop it; the current block is lost, finished blocks are kept
  ```

  After a WSL restart it isn't running: start it again with the same command.

- [x] **Next (heavy, so pick a time the other session is idle):** fetch the 30 cm soil level added 2026-10-28 (HRRR's TSOIL at 30 cm, for the potato model's 8 in) over the backfilled hours; about 15,900 hours at ~3 MB each (~48 GB), then it rolls those days up. It holds the write lock, like the backfill. Claude can run it:

  ```bash
  setsid nohup uv run app/manage.py refetch_soil --start 2025-01-01 --end 2026-10-29 > tmp/refetch_soil.log 2>&1 < /dev/null &
  ```

- [x] **Then:** `uv run app/manage.py rebuild --stale` (about an hour for 2025–2026: rolls the days up again for the model features and the 48.2 °F DD cube added 2026-10-28); `uv run app/manage.py rebuild --check` should then print nothing. Claude can run it.
- [ ] **Phase 2 exit review:** `docs/validation-archive.md` covers the whole backfill (2026-10-29) but predates the shortwave correction (D48), ERA5-Land soil (D52) and ET0 v2: ask Claude to rerun it, then read it (tolerances agreed 2026-10-31, D54). Leave `bin/dev` running for a week afterwards so the hourly job and `/up` can be checked. Not running as of 2026-10-29 (nothing on :8000). It needs to outlive Claude's sessions, so start it from your own terminal:

  ```bash
  bin/dev                             # Django, Vite and the Procrastinate worker; the hourly ingest runs at :40
  curl -s localhost:8000/up           # should say ok; Claude can check it and the ingest records from here
  ```

## Phase 3: Model library (ahead of time)

- [x] **Copy the Shiny apps in** from OneDrive, with their data and `.rds` fixtures, to `tmp/shiny/` (Crop Risk Tool, alfalfa, potato volunteer). The git repos alone lack the data the parity tests need.
- [ ] **Insect model sources (D8 step 4).** The full list, with DOIs, is in [docs/insect-models.md](docs/insect-models.md). Put each PDF in `tmp/references/insects/<insect-id>/` (for example `cabbage-maggot/`); Claude converts an insect once its papers are in. Wisconsin sources first:
  - Eckenrode and Chapman 1972, cabbage maggot field thermal units, [10.1093/aesa/65.1.151](https://doi.org/10.1093/aesa/65.1.151); and 1971, lab development, [10.1093/aesa/64.5.1079](https://doi.org/10.1093/aesa/64.5.1079)
  - Litsinger and Apple 1973, alfalfa weevil in Wisconsin, [10.1093/jee/66.2.309](https://doi.org/10.1093/jee/66.2.309); Harcourt 1981 (USPest's source), [10.4039/Ent113601-7](https://doi.org/10.4039/Ent113601-7)
  - Hanson et al. 2015, western bean cutworm flight, [10.1093/jee/tov110](https://doi.org/10.1093/jee/tov110)
  - Luckmann et al. 1976, black cutworm, [10.1093/jee/69.3.386](https://doi.org/10.1093/jee/69.3.386); Story et al. 1984, [10.1093/jee/77.2.491](https://doi.org/10.1093/jee/77.2.491)
  - Toba et al. 1973, cabbage looper, [10.1093/aesa/66.5.965](https://doi.org/10.1093/aesa/66.5.965)
  - Levine 1983, stalk borer, [10.1093/aesa/76.5.892](https://doi.org/10.1093/aesa/76.5.892)
  - Simonet et al. 1981, variegated cutworm, [10.4039/Ent113891-10](https://doi.org/10.4039/Ent113891-10)
  - Régnière et al. 1981, Japanese beetle, [10.1093/ee/10.3.290](https://doi.org/10.1093/ee/10.3.290)
  - Matteson and Decker 1965, European corn borer, [10.1093/jee/58.2.344](https://doi.org/10.1093/jee/58.2.344); Anderson et al. 1982, [10.1093/ee/11.6.1307](https://doi.org/10.1093/ee/11.6.1307)
  - Eckenrode et al. 1975, onion maggot, [10.1093/ee/4.5.785](https://doi.org/10.1093/ee/4.5.785); Liu et al. 1982, [10.1093/ee/11.3.751](https://doi.org/10.1093/ee/11.3.751)
  - The rest (asparagus beetle, corn rootworm, crucifer flea beetle, Lygus, SWD lab data) are under "Papers to find" in the doc.
- [ ] **Reports with no DOI** (cited by USPest; probably Oregon State or USDA reports): Coop and Berry 1987 (variegated cutworm in peppermint); Berry et al. (mint flea beetle and mint root borer); Simko 2000 (Lygus in alfalfa seed); Hartstack et al. 1976 (MOTHZV-2, corn earworm).
- [ ] **Questions on the insects** (answers go in `docs/insect-models.md`):
  - What is "XHT1087", the spreadsheet's source for imported cabbageworm and onion maggot?
  - Aphid PVY vectors and Colorado potato beetle (your analyses): which degree-day method, biofix and data did each fit use? Are VDIFN's CPB adult and larval models (50/86 °F) yours too, as cited now?
  - Variegated cutworm: the events are Coop and Berry's at 41/88 °F, but VDIFN runs them at Simonet's 45/80.1. Keep Coop and Berry's pair, or rebuild on Simonet?
  - Tarnished plant bug: the model is for _Lygus hesperus_ (Oregon and Idaho alfalfa seed). Keep it, or look for an _L. lineolaris_ model?
  - Cabbage maggot: the Wisconsin source (Eckenrode and Chapman, modified average at 43 °F) or USPest's Oregon State model (sine at 39.7/86 °F)?
  - Black cutworm, cabbage looper, corn earworm: their biofixes stand for trap catches or first silk. Default dates with a user-set biofix (as now), or something else?
- [ ] **UW Vegetable Entomology's seedcorn maggot page** still says to count from spring ground thaw at 39/86 °F, with VDIFN's 360 + 720n peaks. Update it to match seedcorn maggot 2.0 (average method, 39 °F with an 84 °F cap, from January 1) once the new model is reviewed.

## Phase 4: Forecast and blending

- [ ] **Start `bin/dev` and leave it running** (Phase 2 above; restarted 2026-11-02, so the week runs to 2026-11-09 if it stays up; `uv run app/manage.py jobs` shows how it's doing): it now runs the forecast job too (`ingest_forecast` at :15 and :45), and the Phase 4 exit needs a week of it. `curl -s localhost:8000/up` shows both `ingest` and `forecast`.
- [x] **Decide** (details in PLAN.md Phase 4 D and E):
  - ~~Red crown rot's vegetative-period rain fills missing days with the mean of the others~~ decided: missing days count as no rain, and their number is reported (D45; built as `red-crown-rot` 0.2 on 2026-10-30, confirmed by Ben 2026-11-02).
  - ~~Open-Meteo's ECMWF IFS soil forecast~~ decided: D44, then D52 (IFS for the whole forecast).
- [x] **Agree the Phase 2 tolerances** proposed under PLAN.md Phase 2 H (2026-10-31, D54).
- [x] **Restart `bin/dev`** once the ERA5-Land backfill has finished (`tail tmp/era5land/backfill.log` ends in "Done"), so the worker picks up D52: the hourly ingest stops writing soil, and the new `ingest_era5land` (every 6 h) and `ingest_ifs` (hourly; reads only when a new IFS run is out) tasks start. Then `uv run app/manage.py rebuild --check` (soil's daily variables are version 2 and `snow_depth` is new, so expect them stale), and `uv run app/manage.py rebuild --stale`.
- [x] (Nothing to clear: no archive-endpoint entries were cached, checked 2026-11-02.) Optional, dev only: clear the Open-Meteo archive-endpoint cache so old entries' ERA5 soil gives way to ERA5-Land's: `uv run app/manage.py shell -c "from ops.models import WeatherCellCache; WeatherCellCache.objects.filter(endpoint='archive').delete()"`.
- [x] Copernicus CDS key in `.env` as `COPERNICUS_API_KEY`, ERA5-Land licence accepted (2026-10-31). The server's `infra/.env` needs the same key before the ERA5-Land job runs there.
- [x] Q22 decided: Open-Meteo's 9 km IFS, `omfiles` optional (D53).
- [x] Optional, in the Crop Risk Tool (`tmp/shiny/`'s source repo): don't show model outputs until the on-demand weather has loaded; today they flash on incomplete data first (Ben, 2026-11-01). v2 doesn't need this: jobs fetch weather before a page asks.
- [ ] Optional: tell your department (or WARF) that AgWeather v2 and WISP 3 are public under AGPL-3.0, since the Regents hold the copyright.

## Phase 5: API v2

- [x] **Move the dev archive to grid days (D74, 2026-11-06)** (done 2026-11-06 except `downloads`, which is best run once after the backfill), before restarting the backfill so its years roll up once. Stop `bin/dev` and start it again first (its worker runs the hourly rollup, and the old code would write local days). Then:

  ```bash
  uv run app/manage.py rebuild --check                 # every daily year: "(local days, D74)"
  uv run app/manage.py rebuild --stale --background    # each year's days on CST, then its running totals and ingredients
  uv run app/manage.py pastyears                       # the past-years copies (their daily variables changed)
  uv run app/manage.py downloads                       # the yearly NetCDF files
  ```

  Roughly 4 minutes a year for the days plus 3 for the ingredients here (2020–2026: under an hour). `rebuild --check` should then print nothing. Then restart the backfill (`f` in `bin/agwx`). Afterwards, today's GDD map (`/api/v2/maps/degree_days.png?dd=modified_50_86&scale=auto`) should have no line down Lake Michigan.

- [-] **Backfill the dev archive to 2016** (its follow-ups are under Phase 6) (Ben, 2026-11-03: more past years for the projection, D63). Running since 2026-11-04 14:26 as `archive fill --from 2016 --to 2025` (each year's hours, December 31, ERA5-Land and past-years copy, newest first; about 11.5 hours a year here). Watch it in `bin/agwx`; if it stops, start it again there with `f` (it resumes). When it's done, `uv run app/manage.py rebuild --check` should print nothing.
- [x] **Restart the dev backfill** (stopped 2026-11-05 for the latency checks, in 2021): `f` in `bin/agwx` (it resumes), or `uv run app/manage.py archive fill --from 2016 --to 2023 --background`. When it's done: `uv run app/manage.py ingredients --check` then `ingredients` (its years lack the corn and potato tiers, D70), `uv run app/manage.py pastyears`, and `uv run app/manage.py downloads`.
- [x] **Restart bin/dev's worker** (Phase 5 H, 2026-11-05) for the new jobs `build_downloads` (the yearly NetCDF downloads, Mondays at 05:00) and `prune_api_usage` (daily at 04:10), and for the API's rate limit (`api.ratelimit`; requests from this machine are exempt). The dev database already has the new table (`migrate` ran). Claude built the dev downloads with `manage.py downloads`; the backfill's years get theirs from the weekly job, or run `uv run app/manage.py downloads` once it's done.
- [x] **Open a yearly download in R** (Phase 5 H2, 2026-11-05): Ben found terra on Windows lost the CRS and scale with an absolute path; fixed by D71 (one variable a file, the grid in `daily/grid.nc`). Ben's no-lat/lon copy opened correctly both ways; the rebuilt files have that layout.
- [x] **Restart bin/dev's worker** (Phase 5 G3, 2026-11-05) for the new `render_default_maps` job (removed 2026-11-07: maps are drawn on first request; the daily `housekeeping` job, once renamed from `prune_api_usage`, now also prunes kept maps).
- [ ] **Ask the UW Insect Diagnostic Lab to switch their "Today's Growing Degree Day Map" link** from v1's `/api/degree_days/map.png` to `/api/v2/maps/dd_modified_50_86.png` once v2 is live (Phase 8; v1's path redirects to the legacy host for a year, D62).
- [x] **Rebuild potato volunteer's ingredients** (Phase 4 H, 2026-11-05): version 0.2 marks them stale, so its map is a 503 until then. `uv run app/manage.py ingredients --check`, then `uv run app/manage.py ingredients` (or `i` in `bin/agwx`); it rebuilds each stale year whole, about 3 minutes a year over Wisconsin.
- [x] **Restart bin/dev's worker** (Phase 5 F3, 2026-11-05) so it picks up the new `update_crop_tiers` job (soybean and spring wheat stages per planting tier, hourly at :55): stop `bin/dev` and start it again. `uv run app/manage.py jobs` should then list it.
- [ ] ~~**Build the models' ingredients for the past years**~~ moved to Phase 6's "After the backfill" below (2026-11-06). (Phase 5 F2): 2023–2026 are built (2022 through Oct 9, 2026-11-05); the running backfill started before F2, so it won't build the years it fills. When it's done (or sooner, if you don't mind them sharing the disk): `uv run app/manage.py ingredients --check`, then `uv run app/manage.py ingredients` (about 3 minutes a year over Wisconsin; or `i` in `bin/agwx`). It takes the write lock politely, a block at a time.
- [x] Compile the Veg Path newsletters' potato tables (early/mid/late planting and 50% emergence by location, every season on vegpath.plantpath.wisc.edu, as in 2026-08-23's) into a spreadsheet in `tmp/`, for a GDD-based planting and emergence model (PLAN.md Phase 5 D, D64). Done 2026-11-03 (2020–2026); `potato-stages` is fitted to it.
- [x] **Open a v2 grid in the tools agencies use** (GeoTIFF in QGIS: fine, 2026-11-04. NetCDF in R: failed to reproject, fixed the same day; rerun your main.R on a fresh `tmax.nc` to confirm) (Phase 5 E, 2026-11-04): Claude checked the GeoTIFF with GDAL (rasterio) and the NetCDF with xarray, but not in QGIS or R. With `bin/dev` running:

  ```bash
  curl -o /tmp/gdd.tif "localhost:8000/api/v2/grids/degree_days?dd=modified_50_86&start=2026-05-01&end=2026-10-31&stat=sum&region=WI&format=geotiff"
  curl -o /tmp/tmax.nc "localhost:8000/api/v2/grids/air_temperature_max?start=2026-07-01&end=2026-07-07&format=netcdf"
  ```

  QGIS: drag `/tmp/gdd.tif` in over an OpenStreetMap layer; Wisconsin should line up with its borders (a 2.5 km cell is visible at county zoom). R: `terra::rast("/tmp/tmax.nc")` should have 7 layers and a Lambert CRS, and `terra::project(r, "EPSG:4326")` should land on Wisconsin. Tell Claude if either is off.

- [ ] Send `docs/server-sizing.md` to IT (Q4): r7i.2xlarge, 1.5 TB gp3 data volume (500 MB/s), 200 GB scratch, RDS PostgreSQL db.t4g.medium, us-east-1, and a temporary resize for the backfill.
- [ ] Before launch (Phase 8), with IT: DNS for `legacy.agweather.cals.wisc.edu` pointing at the old server, its TLS certificate, and nginx's `server_name` on the old server answering to it (D62). Check v1 serves its API there before `agweather.cals.wisc.edu` moves to v2.
- [x] DATCP's v1 query: confirmed by DATCP (2026-11-02) and in the logs (8 settings × 23 points daily).
- [x] DATCP's normals spreadsheet (2026-11-02): mean cumulative modified 50/86 GDD at their 23 points, from the State Climatology Office. Drop a copy in `tmp/` if Phase 6 should compare our gridded normals with it.
- [x] Who else calls v1: the nginx access logs for 2026-10-19 to 11-02 (`tmp/v1-logs/access.log`, 21,760 API requests in 15 days) summarized 2026-11-02; December 2024's Rails log (`tmp/agwx-production.log`) agrees. The Rails log has been empty since the Rails 8 upgrade (December 2024) sent it to STDOUT, which Passenger writes to nginx's error log; left as is, since v1 is being retired.
- [ ] Name the callers still unknown (the two .NET clients), and send each caller the new URLs once Phase 5 C is done:

  - `165.189.65.24` (State of Wisconsin; was `165.189.255.59` in 2024): DATCP. Unchanged: 8 degree-day settings × 23 points, 184 requests every morning at 08:00–09:00, January 1 to yesterday.
  - `52.36.85.186` (AWS, "Ruby"): the current AgWeather website (12,868). v2 replaces it.
  - `216.105.223.230` ("RestSharp", .NET): ET at one point (44.1188, −89.5333), last 30 days, both classic and `method=adjusted` (Desai & Talib's emissivity), ~93 a day around the clock (1,392). Polls far more than daily data needs.
  - `71.13.161.79` ("RestSharp"): ET at 28 points, last 10 days, daily at 09:00 (420). An irrigation scheduler?
  - **Nortera** ("Nortera-Production-Tracker/1.0", through Cloudflare 104.23.160.x): sine 50/86 degree days from May 1, and precip, at 8 points daily at 06:00 (109 in 7 days). A vegetable processor: worth a direct email.
  - `waunakee-lawn-notifier (eli@solow.org)`: `dd_table` (`dd_50_86`, `dd_32`) and precip at one point, twice a day (68). Has a contact address in its user agent.
  - Veg Path (`pest_forecasts/vegpath` from AWS 3.19.85.241 and 18.221.246.67; 753): Ben's WordPress site for the UW Vegetable Pathology lab, through wpDataTables (weather and early/late blight charts for 7 Wisconsin locations).
  - `144.92.74.104` ("httr2", UW campus Posit Connect): Ben's alfalfa Shiny app, `/api/weather/grid?date=…` about once a day. Replaced by v2's alfalfa tool.
  - UW Insect Diagnostic Lab (https://insectlab.russell.wisc.edu/): links "Today's Growing Degree Day Map" to v1's `/api/degree_days/map.png`. Ask them to switch to v2's `/maps/…png` (D60) once it exists.
  - `146.151.193.173` ("python-requests", 2026-10-28 and 29): our own Phase 2 comparisons of v2 against the old API.
  - The rest is scanners (`/api/.env`, `/api/mcp`) and a few one-off browsers.

- [x] Optional, to see v1's use until the switch: keep more nginx history on the old server. `/etc/logrotate.d/nginx` rotates daily and keeps 14 (Ubuntu's default); `sudo sed -i 's/rotate 14/rotate 400/' /etc/logrotate.d/nginx` keeps about 13 months (~2 MB a day before compression, ~120 KB after).

## Phase 6: Frontend plan and the data behind it

- [ ] **Optional: check chill against chillR itself** (2026-11-10). The Dynamic model is tested against a line-by-line port of chillR's code; Claude wasn't allowed to run code it downloaded, so a direct comparison waits for you. chillR needn't be installed: its model functions are plain R.

  ```bash
  cd /tmp && curl -LO https://cran.r-project.org/src/contrib/Archive/chillR/chillR_0.75.tar.gz && tar xzf chillR_0.75.tar.gz
  cd ~/code/agweather2
  Rscript packages/agmodels/tests/fixtures/make_chillr_reference.R /tmp/chillR/R/temp_models.R \
    packages/agmodels/tests/fixtures/chillr_reference.csv
  uv run pytest packages/agmodels/tests/test_chill_livestock.py   # test_all_three_match_chillr_itself then runs
  ```

  Commit the CSV if it passes.

- [ ] **Don't run `rebuild --stale` yet** (2026-11-10). Chill and heat stress (C6) added eight daily features and three running totals, so every year is stale; the rebuild waits for the pipeline work (PLAN.md C, "Streamlining rebuilds"), which will compute only what's new instead of re-rolling every daily variable. `rebuild --check` lists them meanwhile. Until then (D29) points compute the new features from the hours, maps of up to 7 days do too (a day's map ~4 s), and a longer range answers 503 `stale`.

- [x] **Restart `bin/dev` before Monday, November 16** (2026-11-09; done that evening). Its worker started at 21:37, before past-years builds took turns (a lock added that evening, after two builds at once broke 2017's copy). Ctrl-C in its terminal, then `bin/dev`.

- [ ] **`/tmp` is now a 9.8 GB tmpfs** (Ubuntu 26.04 mounts it in memory by default; found 2026-11-09). The test suite in parallel fills it ("No space left on device" in a dozen tests), and whatever's there uses WSL's 19 GB of RAM. Either give `/tmp` back to the disk, as on 24.04:

  ```bash
  sudo systemctl mask tmp.mount
  # then from Windows: wsl --shutdown, and reopen
  findmnt /tmp     # should print nothing (it's part of /)
  ```

  or keep the tmpfs and point the tests elsewhere (`TMPDIR=$PWD/tmp/pytest-tmp uv run pytest -n auto --dist loadfile`), which Claude can make the default in `bin/ci` and the root conftest if you'd rather. CI on GitHub isn't affected.

- [ ] **Derive soil and snow again with the B-spline** (D80, 2026-11-09). ERA5-Land and IFS now reach the grid by a cubic B-spline instead of bilinear, which removes the 0.1° grid's creases and squares from soil maps. Ben restarted `bin/dev` (2026-11-09), so the worker's daily ERA5-Land and hourly IFS jobs use it, and the re-derive is running. Derive every year from what's kept (local, no download; about 20 s a month over Wisconsin, so roughly 45 minutes), and rebuild what's made from the daily store:

  ```bash
  uv run app/manage.py era5land --rederive --start 2016-01-01 --end 2026-11-03
  uv run app/manage.py rebuild --check       # should print nothing
  uv run app/manage.py ingredients --check   # then `ingredients` if it lists anything
  uv run app/manage.py downloads --check     # then `downloads` if it lists anything
  uv run app/manage.py timecopy --check      # then `timecopy` if it lists anything
  ```

  Then look at `/api/v2/maps/soil_temperature_4cm_mean.png?stat=min&start=2025-07-01&end=2026-07-01`: no grid lines, though ERA5-Land's own patches (its 0.1° cells differ by several degrees under snow) remain as soft blobs.

- [x] **ERA5-Land kept as received, and the coast of soil and snow** (D79, 2026-11-07; done by 2026-11-09: every month of 2016–2026 has soil on Washington Island, the Door Peninsula's tip and Madeline Island, so the re-derive isn't needed). Claude started the download of 2016 through October 2026 into `data/era5land/` (`era5land --start 2016-01-01 --end 2026-11-03`, 130 monthly requests, 3 at a time: likely a day or two at the CDS; it resumes where it stopped if run again, since a day counts as missing until it's kept). It writes each month's soil and snow by the new coast rule as it arrives.

  1. Restart `bin/dev` now, so the worker's daily ERA5-Land and hourly IFS jobs keep files and use the new coast (Ctrl-C, then `bin/dev`).
  2. The `archive fill` running since this morning has the old code, and its ERA5-Land step for each year writes soil the old way. Stop and resume it at a convenient point (`uv run app/manage.py archive stop`, wait until `archive` no longer lists it, then `f` in `bin/agwx`).
  3. When both have finished, derive every year's soil and snow once more from what's kept, so no month is left from the old code (local, a few hours, no download), and check:

  ```bash
  uv run app/manage.py era5land --rederive --start 2016-01-01 --end 2026-11-03
  uv run app/manage.py archive        # each year's soil should be ERA5-Land's
  du -sh data/era5land                # roughly 0.5–1 GB a year over the launch box; less over Wisconsin
  ```

  Then look at `/api/v2/maps/soil_temperature_10cm_mean.png?date=2026-05-01&region=55029` (Door County): soil to the tip, on Washington Island, and on the Apostle Islands (`region=55007`).

- [x] **After the backfill** (done 2026-11-09: Ben ran the checks; Claude rebuilt 2016–2019's crop tiers, the downloads and the season-read copy) (PLAN.md Phase 6, "After the backfill"; moved from Phase 5, 2026-11-06). When `archive fill` finishes in `bin/agwx`:

  ```bash
  uv run app/manage.py rebuild --check       # should print nothing
  uv run app/manage.py ingredients --check   # the backfill's years: missing or lacking the crop tiers (D70)
  uv run app/manage.py ingredients           # about 3–7 minutes a year over Wisconsin; or i in bin/agwx
  uv run app/manage.py downloads             # the yearly NetCDF files (300 stale after D74's rebuild, plus the new years)
  ```

  Then tell Claude, who removes the old season search (`_first_day_at`) and times the ten-year projection. Monday's job builds the downloads if you don't run them.

- [x] **Restart `bin/dev` and the backfill for water balance's running total** (2026-11-07; done, `rebuild --check` clean 2026-11-09). The worker (running since 00:30) and `archive fill` (writing 2019) run code from before `water_balance_total` existed, so the days they roll up get no water balance running total. Claude rebuilt every year's at about 10:00. Restart both soon: within a week of new days, the next rollups fill the gap themselves (each rewrites from 7 days back).

  ```bash
  # in bin/dev's terminal: Ctrl-C, then
  bin/dev
  # the backfill: ask it to stop after its current block, wait until `archive` no longer lists it, then resume (or f in bin/agwx)
  uv run app/manage.py archive stop
  uv run app/manage.py archive fill --from 2016 --to 2025 --background
  ```

  If the backfill had already moved past 2019 by the restart, mark 2019's three arrays stale and rebuild them (about 4 minutes):

  ```bash
  uv run python -c "import zarr; g = zarr.open_group('data/cumulative/2019.zarr', mode='r+'); [g[n].attrs.update(version=0) for n in ('water_balance', 'water_balance_estimated_days', 'water_balance_missing_days')]"
  uv run app/manage.py rebuild --stale
  ```

- [x] **Restart `bin/dev` and the dashboard** (2026-11-06; done, `timecopy` filled 2026-11-09) so they load the day's changes: the worker's rollups then keep the season-read copy of daily min and max (`agdata.timecopy`) current, and the dashboard uses about a third of the CPU it did. Until then nothing is wrong: maps read any day the copy lacks from the daily store.

  ```bash
  # in bin/dev's terminal: Ctrl-C, then
  bin/dev
  # in the dashboard's: q, then
  bin/agwx
  uv run app/manage.py timecopy --check   # should say every year's copy is current; if not, run it without --check
  ```

  After `archive fill` resumes and finishes, the new years' copies are made as they roll up; `timecopy --check` confirms it. On the server (Phase 8), run `uv run app/manage.py timecopy` once after the archive is copied there.
