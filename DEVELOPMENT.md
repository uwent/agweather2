# Development

How to set up a machine to work on AgWeather v2 and the day-to-day commands. Conventions are in [CLAUDE.md](CLAUDE.md); the design and phases in [PLAN.md](PLAN.md).

## 1. Prerequisites

Written for Ubuntu 24.04 under WSL2.

| Tool       | Version                                           | Why                                                                               |
| ---------- | ------------------------------------------------- | --------------------------------------------------------------------------------- |
| uv         | latest                                            | Python 3.13 (`.python-version`, downloaded by uv), the workspace and its lockfile |
| Node.js    | 24 (`.node-version`)                              | Vite, the frontend tests, pyright                                                 |
| pnpm       | from `packageManager` in `package.json`           | JavaScript packages                                                               |
| PostgreSQL | 18                                                | App data and the job queue (CI uses 18)                                           |
| ecCodes    | 2.34 or newer (`libeccodes0`, `libeccodes-tools`) | GRIB decoding, through the system library (not the eccodeslib wheel; CLAUDE.md)   |
| Docker     | Engine or Desktop with WSL integration            | Only for the container build (`infra/`)                                           |

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
sudo apt install -y libeccodes0 libeccodes-tools postgresql
sudo service postgresql start        # WSL doesn't start services on boot
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'password';"
```

## 2. The app

```bash
git clone https://github.com/uwent/agweather2.git && cd agweather2
cp .env.example .env     # every value has a default
uv sync                  # Python 3.13 and the workspace into .venv
pnpm install             # JavaScript packages and the pre-commit hook
pnpm exec playwright install --with-deps chromium     # the browser for bin/e2e
createdb -h localhost -U postgres agweather2_development
uv run app/manage.py migrate
bin/dev                  # http://localhost:8000
bin/ci                   # everything CI runs
```

`pnpm install` installs a Husky pre-commit hook that runs lint-staged: ESLint and Prettier on frontend files, `ruff format` and `ruff check --fix` on Python.

## 3. Day to day

```bash
bin/dev                               # Django on :8000, Vite on :5173, the job worker
bin/agwx                              # the data dashboard (section 6); bin/agwx <command> runs any manage.py command
bin/ci                                # every check, in CI's order; stops at the first failure
bin/e2e                               # Playwright on a production build and the agweather2_e2e database
bin/e2e smoke.spec.ts --project desktop
bin/types                             # after changing a props.py; commit frontend/types/generated
uv run app/manage.py createsuperuser  # for /admin
uv run pytest packages/agmodels       # one package's tests
uv run pytest --network               # also the tests that read NOAA's bucket (not run in CI)
uv run ruff format . && uv run ruff check --fix .
pnpm typecheck:py                     # pyright
pnpm check                            # svelte-check and TypeScript
pnpm test                             # Vitest
```

The browser tests fail on any console error (a CSP violation included) and run axe on every page in light and dark. GitHub Actions runs `bin/ci` on every push to `main` and on pull requests. Tests never use the network: pytest-socket blocks it, and fixtures are recorded.

## 4. Containers

The production image and stack are in `infra/` (PLAN.md §13). To try them on a laptop, with a Postgres container
in place of RDS:

```bash
SECRET_KEY=anything docker compose -f infra/compose.yaml --profile local up --build    # http://localhost:8080
SECRET_KEY=anything docker compose -f infra/compose.yaml --profile local down -v       # stop and delete its volumes
```

On a server, settings go in `infra/.env` (gitignored): `SECRET_KEY`, `DATABASE_URL` (RDS), `ALLOWED_HOSTS`,
`SITE_ADDRESS` (the hostname, so Caddy gets a certificate), `HTTP_PORT=80`, `HTTPS_PORT=443`, `APP_VERSION`.

## 5. Scratch and data

- `tmp/` is gitignored scratch (downloads, one-off scripts). The Shiny apps used for model parity are in `tmp/shiny/`.
- `data/` (gitignored, or `DATA_DIR`) holds the local Zarr archive and GRIB downloads, the write lock (`write.lock`, `write.waiting/`) and the data commands' run records and logs (`runs/`).

## 6. Managing data from the console

### The dashboard

```bash
bin/agwx                              # or `uv run app/manage.py` with no command, or `manage.py dashboard`
```

A full-screen view of the data, kept live:

- **Years**: each year of the archive: hours with an analysis (URMA and RTMA), precip and shortwave coverage, days with ERA5-Land soil, days rolled up, and whether its past-years copy is current; ✓ when complete.
- **Status**: who holds the write lock (pid, command and since when) and who's waiting for it; whether the worker is running; how far behind the archive and forecast are; each job's last run; problems.
- **Runs**: every data command running, wherever it was started (the dashboard, a shell, a script), and the last few finished: command, pid, since, elapsed, progress and time left, CPU, memory, and bytes read per second (for a backfill, the download rate). Below the table, the picked run's bars and a spinner for each hour or CDS request in flight.
- **Log**: the picked run's lines: each file read (`2023-06-01 05Z  GET noaa-urma-pds/…: 7 msgs, 43.1 MB in 13.7 s, decoded in 0.3 s`), each hour and block written.

Tab moves between the sections; click a run (or ↑/↓) to pick it. Keys:

| Key | Does                                                                      |
| --- | ------------------------------------------------------------------------- |
| `f` | fill years (`archive fill`), e.g. `2016-2025`                             |
| `b` | backfill a range of hours (`backfill`)                                    |
| `e` | ERA5-Land soil and snow for a range (`era5land`)                          |
| `r` | recompute stale derived variables (`rebuild --stale`)                     |
| `p` | build the past-years copies that are missing or out of date (`pastyears`) |
| `i` | build the models' ingredients that are missing or stale (`ingredients`)   |
| `s` | stop the picked run after its current block (press again to interrupt)    |
| `c` | clear finished runs and their logs, and stop counting failed jobs so far  |
| `q` | quit; runs carry on, and reopening the dashboard picks them up            |

Commands started here run detached, with their output in `data/runs/<started>-<command>.log`.

### The same from a shell

```bash
bin/agwx archive                                   # the years, the lock and the runs, as text
bin/agwx archive fill --from 2016 --dry-run        # what filling 2016 to last year would fetch, and about how long
bin/agwx archive fill --from 2016 --background     # do it, detached; prints its pid and log
bin/agwx archive runs                              # the runs lately; `archive log [PID]` shows one's last lines
bin/agwx archive stop [PID]                        # stop a run (or every run) after its current block
bin/agwx archive clear                             # forget finished runs and their logs (they go after 14 days anyway)
bin/agwx jobs                                      # the worker's jobs, the archive's and forecast's health
```

Every data command (`backfill`, `era5land`, `rollup`, `rebuild`, `pastyears`, `ingredients`, `downloads`, `refetch_precip`, `forecast`, `archive fill`) takes `--background`, and `--quiet` to print only warnings, failures and the summary. On a terminal it draws its progress in place; in a log it writes timestamped lines. Each exits nonzero if anything failed.

### Filling years

`archive fill --from YEAR [--to YEAR]` fills whole years, newest first, so each finished year is usable at once. For each year:

1. Its hours from NOAA's AWS buckets (URMA, RTMA, HRRR) for the `SERVICE_BOX` window (`backfill`).
2. Its December 31, which needs the next year's first UTC hours.
3. Its ERA5-Land soil temperature and snow depth from the Copernicus CDS (`era5land`; needs `COPERNICUS_API_KEY` in `.env`, or `--no-soil`). This runs alongside the next year's hours, since CDS requests sit in a queue for 10–20 minutes each.
4. Its models' ingredients, from which model maps are finished (`ingredients`).
5. Its past-years copy for the projection (`pastyears`).

Everything resumes: a rerun skips hours, days and copies that are already there, so stopping and restarting (or a WSL restart) loses at most the block in hand.

The hours are what take the time: about 11.5 hours a year here. Each URMA analysis is a whole CONUS field (~43 MB an hour, ~50 MB with precip and HRRR), and the connection is the limit (~100 Mbit/s), not the CPU: decoding a file takes 0.1–0.4 s of its 8–35 s. `--workers` (default 4) is how many hours download at once; memory peaks under 2 GB.

`backfill --start --end` does the hours alone for a range (`--end` is the day after the last; days are UTC). It works in 5-day blocks (`--block-days`), downloading the next block while it writes this one. Hours RTMA filled because URMA wasn't out yet are fetched again once URMA is. After each block it rolls up the local days the block finished into `data/daily/<year>.zarr` and rebuilds that year's running totals in `data/cumulative/<year>.zarr`.

### The write lock

Only one process writes to the archive at a time (`data/write.lock`). Commands download without it and take it only to write. A command that finds it held waits, saying whose it is, rather than failing. A long run that takes it block after block, like a backfill, lets anything waiting go first, so the worker's hourly jobs and your one-off commands run between its blocks.

### Other data commands

`rollup` redoes the daily stores and running totals for a range of grid days (CST) from the hourly archive, e.g. after changing a daily statistic:

```bash
uv run app/manage.py rollup --start 2025-01-01 --end 2025-01-30    # grid days, inclusive; about 17 s a month here
```

`rebuild --check` lists derived variables written by an older version of their code, and `rebuild --stale` recomputes them (run it after a deploy, like `migrate`). `pastyears --check` lists the years whose past-years copy (`data/daily-by-point/<year>.zarr`, ~0.3 GB a year, read by the projection past the forecast, D63) is missing or out of date; a weekly job keeps them current.

`ingredients --check` lists the years whose models' ingredients (`data/ingredients/<year>.zarr`, ~0.5 GB a year over Wisconsin: what model maps are finished from, and each crop's stages per planting tier) are missing, stale or behind the daily store, and `ingredients` builds them (`--year` for one, whatever its state). The hourly jobs keep the current year's after that.

`downloads --check` lists the yearly NetCDF downloads (`data/downloads/daily/<year>/`) that are missing or older than their daily store, and `downloads` builds them (`--variables` for some). A weekly job keeps them current, but a new server's first build is long, so run the command once.

`latency` times the requests PLAN.md §3 sets targets for (a map's first tile and a kept one, a point's hourly season, every model at a point) on this archive, and says which are over (`--lat --lng --day` to choose the place and day).

When a variable's stored scale changes in the catalog, stores written before refuse to open until they're repacked (`GridStore.rescale`). For precip, `refetch_precip --start --end --rescale` repacks and fetches the hours again at the new precision (precip files are small: about 2 minutes a month).

Stored hours and days are raw: a missing hour or an incomplete day stays missing. Only the running totals estimate across gaps (up to 7 days), and they count the estimated and missing days (PLAN.md D25).

### Keeping current

The worker in `bin/dev` keeps the archive current:

| Job                   | When           | What it does                                                 |
| --------------------- | -------------- | ------------------------------------------------------------ |
| `ingest_recent`       | hourly, at :40 | the last week's missing and RTMA-only hours, then their days |
| `ingest_forecast`     | :15 and :45    | the newest NBM run                                           |
| `ingest_ifs`          | hourly, at :50 | the provisional soil and snow                                |
| `ingest_era5land`     | every 6 hours  | ERA5-Land, about 5 days behind                               |
| `update_crop_tiers`   | hourly, at :55 | each crop's stages per planting tier, while in season        |
| `build_past_years`    | Mondays        | the past-years copies                                        |
| `build_downloads`     | Mondays        | the yearly NetCDF downloads                                  |
| `housekeeping`        | daily, at 4:10 | drops API rate-limit counts over a week old and map images unused for 14 days |

`bin/agwx jobs` lists them and their last runs, and `jobs run NAME` runs one now. Each ingest run and backfill block is listed in Django admin under Operations → Ingest records, and `/up` shows how far behind the archive is:

```bash
curl -s localhost:8000/up | python3 -m json.tool    # status ok, degraded (with problems) or down
```
