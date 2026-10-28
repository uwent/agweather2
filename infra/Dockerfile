# AgWeather v2: one image for the web server and the job worker (infra/compose.yaml picks the command).
# Build from the repo root: docker build -f infra/Dockerfile --build-arg APP_VERSION=$(git rev-parse --short HEAD) .

# 1. The frontend: Vite builds app/static/vite (Node is only needed here)
FROM node:24-slim AS frontend
WORKDIR /src
RUN corepack enable
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY vite.config.ts svelte.config.js tsconfig.json ./
COPY frontend frontend
# Tailwind scans app/ for classes in Django templates
COPY app app
RUN pnpm build

# 2. The Python app
FROM python:3.13-slim-trixie AS app
# GRIB decoding uses the system ecCodes (CLAUDE.md)
RUN apt-get update \
  && apt-get install -y --no-install-recommends libeccodes0 \
  && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:0.13 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never UV_PROJECT_ENVIRONMENT=/venv
WORKDIR /srv

# Dependencies first, so code changes don't reinstall them
COPY pyproject.toml uv.lock .python-version ./
COPY packages/agmodels/pyproject.toml packages/agmodels/pyproject.toml
COPY packages/agdata/pyproject.toml packages/agdata/pyproject.toml
COPY app/pyproject.toml app/pyproject.toml
RUN mkdir -p packages/agmodels/src/agmodels packages/agdata/src/agdata \
  && touch packages/agmodels/src/agmodels/__init__.py packages/agdata/src/agdata/__init__.py \
  && uv sync --frozen --no-dev --no-install-workspace

COPY packages packages
COPY app app
COPY --from=frontend /src/app/static/vite app/static/vite
RUN uv sync --frozen --no-dev

ARG APP_VERSION=dev
ENV PATH=/venv/bin:$PATH \
  PYTHONUNBUFFERED=1 \
  DJANGO_ENV=production \
  APP_VERSION=$APP_VERSION \
  DATA_DIR=/data \
  STATIC_ROOT=/srv/static

# /data holds the Zarr archive; /srv/static the static files the web container collects at start for Caddy
RUN useradd --system --uid 1000 --home /srv agweather \
  && mkdir -p /data /srv/static && chown agweather /data /srv/static
USER agweather
EXPOSE 8000
CMD ["uvicorn", "--app-dir", "app", "config.asgi:application", "--host", "0.0.0.0", "--port", "8000", "--lifespan", "off", "--proxy-headers", "--forwarded-allow-ips", "*"]
