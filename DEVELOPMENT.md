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
| eccodes | 2.34 or newer (`libeccodes0`, `libeccodes-tools`) | GRIB decoding |
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
uv run ruff format . && uv run ruff check --fix .
pnpm typecheck:py                     # pyright
pnpm check                            # svelte-check and TypeScript
pnpm test                             # Vitest
```

The browser tests fail on any console error (a CSP violation included) and run axe on every page in light and dark. GitHub Actions runs `bin/ci` on every push to `main` and on pull requests. Tests never use the network: pytest-socket blocks it, and fixtures are recorded.

## 4. Scratch and data

- `tmp/` is gitignored scratch (downloads, one-off scripts). The Shiny apps used for model parity are in `tmp/shiny/`.
- `data/` (gitignored, or `DATA_DIR`) holds the local Zarr archive and GRIB downloads.
