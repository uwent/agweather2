# Development

How to set up a machine to work on AgWeather v2 and the day-to-day commands. Conventions are in [CLAUDE.md](CLAUDE.md); the design and phases in [PLAN.md](PLAN.md).

## 1. Prerequisites

Written for Ubuntu 24.04 under WSL2.

| Tool | Version | Why |
|---|---|---|
| uv | latest | Python 3.13 (`.python-version`, downloaded by uv), the workspace and its lockfile |
| Node.js | 24 (`.node-version`) | Vite, the frontend tests, pyright |
| pnpm | from `packageManager` in `package.json` | JavaScript packages |
| PostgreSQL | 18 | App data and the job queue (CI uses 18) |
| ecCodes | 2.34 or newer (`libeccodes0`, `libeccodes-tools`) | GRIB decoding, through the system library (not the eccodeslib wheel; CLAUDE.md) |
| Docker | Engine or Desktop with WSL integration | Only for the container build (`infra/`) |

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
- `data/` (gitignored, or `DATA_DIR`) holds the local Zarr archive and GRIB downloads.

## 6. Managing data from the console

`backfill` fills the hourly archive (`data/hourly/<year>.zarr`) for the `SERVICE_BOX` window from NOAA's AWS buckets
(URMA, RTMA, HRRR). It downloads about 50 MB per hour of data and runs at about 6 s per hour of data on a home
connection, so run it detached, so that it outlives the terminal:

```bash
setsid nohup uv run app/manage.py backfill --start 2025-01-01 --end 2026-10-28 > tmp/backfill.log 2>&1 < /dev/null &
tail -f tmp/backfill.log            # a line every 6 hours of data, with time left; Ctrl-C stops watching, not the backfill
pgrep -af 'manage.py backfill'      # is it running?
cat data/write.lock                 # its pid
kill $(cat data/write.lock)         # stop it; the current block is lost, finished blocks are kept
du -sh data/*                       # archive size
```

- `--end` is the day after the last one. Days are UTC.
- It works in 5-day blocks (`--block-days`) and writes each one when it's finished. Rerunning skips complete blocks,
  so restarting after a stop or a WSL restart is safe. `--redo` refetches them anyway.
- Only one backfill or rollup runs at a time (`data/write.lock`): a second one exits naming the first one's pid.
  Several at once would write the same Zarr chunks and run WSL out of memory.
- `--workers` (default 4) is how many hours download in parallel. The connection is the limit here, not the CPU.
  Memory peaks at about 1.8 GB.
- Blocks with hours URMA hasn't published yet use RTMA for them and aren't counted as complete, so a later rerun
  replaces those hours with URMA.
- After each block it rolls up the local days the block finished into `data/daily/<year>.zarr` and rebuilds that
  year's running totals in `data/cumulative/<year>.zarr` (about 20 s).

`rollup` redoes the daily stores and running totals for a range of local days from the hourly archive, e.g.
after changing a daily statistic or for days a backfill skipped:

```bash
uv run app/manage.py rollup --start 2025-01-01 --end 2025-01-30    # local days, inclusive; about 17 s a month here
```

Stored hours and days are raw: a missing hour or an incomplete day stays missing. Only the running totals
estimate across gaps (up to 7 days), and they count the estimated and missing days (PLAN.md D25).

Keeping the archive current is the `ingest_recent` job, which the worker in `bin/dev` runs at :40 each hour: it
fetches the last week's missing and RTMA-only hours (RTMA hours only once URMA has published them), then rolls
up their days. It skips while a backfill or rollup holds the lock. Each run and each backfill block is listed
in Django admin under Operations → Ingest records, and `/up` shows how far behind the archive is:

```bash
curl -s localhost:8000/up | python3 -m json.tool    # status ok, degraded (with problems) or down
```
