# TODO (Ben)

Things only you can do, by phase. Details are in [PLAN.md](PLAN.md).

## Phase 1: Foundations

- [x] **Install uv** (Python and the workspace; it downloads Python 3.13 itself):
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- [x] **Install Docker** in WSL, either Docker Desktop on Windows with WSL integration turned on for this distro, or Docker Engine inside WSL (`sudo apt install docker.io docker-compose-v2`, then `sudo usermod -aG docker $USER`). Only needed for Phase 1 E (containers); day-to-day development runs natively.
  - [x] The socket still says "permission denied": open a new WSL terminal (or `newgrp docker`) so the `docker` group applies, then check with `docker run --rm hello-world`.
- [x] **Create the GitHub repo** (`uwent/agweather2`, public; PLAN.md Q3), then add it as `origin`.
- [x] Answer PLAN.md Q1–Q3 (now D17–D19).
- [ ] **Server request to IT** (Phase 1 gate; IT is setting up infrastructure as of 2026-10-27): the Server requirements section of `docs/project-plan.md`, with EC2, the EBS data volume and RDS in the same region and AZ. The pilot (`docs/pilot.md`) confirms the sizes:
  - Data volume: **1 TB gp3** holds the Upper Midwest's 11 years (about 510 GB: 342 GB hourly, the rest daily, cumulative and climatology). CONUS later needs 2–3 TB, or older years in S3.
  - The 11-year backfill downloads about 4 TB from NOAA's bucket; from inside AWS that takes hours, not the ~5 days it would take from campus or home. A temporary scale-up for it (16–32 vCPU for a day or two) still stands.
  - Hourly ingest is light: about 40 MB downloaded and under a minute of work per hour for the Upper Midwest.
- [ ] Optional: put the Open-Meteo API key in `.env` as `OPEN_METEO_API_KEY` (needed from Phase 4).

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
- [ ] **Phase 2 exit review:** once Claude has rerun `docs/validation-archive.md` over the whole backfill, read it (tolerances agreed 2026-10-31, D54). Leave `bin/dev` running for a week afterwards so the hourly job and `/up` can be checked. Not running as of 2026-10-29 (nothing on :8000). It needs to outlive Claude's sessions, so start it from your own terminal:
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

- [ ] **Start `bin/dev` and leave it running** (Phase 2 above): it now runs the forecast job too (`ingest_forecast` at :15 and :45), and the Phase 4 exit needs a week of it. `curl -s localhost:8000/up` shows both `ingest` and `forecast`.
- [ ] **Decide** (details in PLAN.md Phase 4 D and E):
  - Red crown rot's vegetative-period rain fills missing days with the mean of the others. Keep it, or leave the total missing when any day is?
  - ~~Open-Meteo's ECMWF IFS soil forecast~~ decided: D44, then D52 (IFS for the whole forecast).
- [x] **Agree the Phase 2 tolerances** proposed under PLAN.md Phase 2 H (2026-10-31, D54).
- [ ] **Restart `bin/dev`** once the ERA5-Land backfill has finished (`tail tmp/era5land/backfill.log` ends in "Done"), so the worker picks up D52: the hourly ingest stops writing soil, and the new `ingest_era5land` (every 6 h) and `ingest_ifs` (hourly; reads only when a new IFS run is out) tasks start. Then `uv run app/manage.py rebuild --check` (soil's daily variables are version 2 and `snow_depth` is new, so expect them stale), and `uv run app/manage.py rebuild --stale`.
- [ ] Optional, dev only: clear the Open-Meteo archive-endpoint cache so old entries' ERA5 soil gives way to ERA5-Land's: `uv run app/manage.py shell -c "from ops.models import WeatherCellCache; WeatherCellCache.objects.filter(endpoint='archive').delete()"`.
- [x] Copernicus CDS key in `.env` as `COPERNICUS_API_KEY`, ERA5-Land licence accepted (2026-10-31). The server's `infra/.env` needs the same key before the ERA5-Land job runs there.
- [x] Q22 decided: Open-Meteo's 9 km IFS, `omfiles` optional (D53).
- [ ] Optional, in the Crop Risk Tool (`tmp/shiny/`'s source repo): don't show model outputs until the on-demand weather has loaded; today they flash on incomplete data first (Ben, 2026-11-01). v2 doesn't need this: jobs fetch weather before a page asks.
- [ ] Optional: tell your department (or WARF) that AgWeather v2 and WISP 3 are public under AGPL-3.0, since the Regents hold the copyright.
