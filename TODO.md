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
- [ ] **Let the backfill finish** (started 2026-10-28). Only one runs at a time (a second one exits naming the first's pid), and rerunning resumes, skipping complete 5-day blocks:
  ```bash
  cd ~/code/agweather2
  setsid nohup uv run app/manage.py backfill --start 2025-01-01 --end 2026-10-28 > tmp/backfill.log 2>&1 < /dev/null &
  tail -f tmp/backfill.log            # a line every 6 hours of data, with time left; Ctrl-C stops watching, not the backfill
  pgrep -af 'manage.py backfill'      # is it running?
  cat data/write.lock                 # its pid
  kill $(cat data/write.lock)         # stop it; the current block is lost, finished blocks are kept
  ```
  After a WSL restart it isn't running: start it again with the same command.
- [ ] **Phase 2 exit review:** once Claude has rerun `docs/validation-archive.md` over the whole backfill, read it and agree the tolerances (PLAN.md Phase 2 H). Leave `bin/dev` running for a week afterwards so the hourly job and `/up` can be checked.

## Phase 3: Model library (ahead of time)

- [x] **Copy the Shiny apps in** from OneDrive, with their data and `.rds` fixtures, to `tmp/shiny/` (Crop Risk Tool, alfalfa, potato volunteer). The git repos alone lack the data the parity tests need.
