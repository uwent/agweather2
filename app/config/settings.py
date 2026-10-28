"""Django settings. Every value comes from the environment (.env in development), with defaults that work
locally; DJANGO_ENV picks development, test or production."""

import os
import sys
from pathlib import Path

import dj_database_url
from django.utils.csp import CSP  # pyright: ignore[reportMissingImports]  (new in Django 6; not in django-types yet)
from dotenv import load_dotenv

APP_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = APP_DIR.parent

load_dotenv(REPO_DIR / ".env")

ENV = os.environ.get("DJANGO_ENV") or ("test" if "pytest" in sys.modules else "development")
DEBUG = ENV == "development"
TESTING = ENV == "test"
# uvicorn doesn't serve static files: Django does in development and tests (bin/e2e), Caddy in production
SERVE_STATIC = DEBUG or TESTING

SECRET_KEY = os.environ.get("SECRET_KEY") or ("dev-only-insecure-key" if ENV != "production" else "")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY must be set in production")

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# The deployed commit, shown by /up and the API status
APP_VERSION = os.environ.get("APP_VERSION", "dev")

# The grid window the archive covers (PLAN.md D20): a preset name or south,west,north,east
SERVICE_BOX = os.environ.get("SERVICE_BOX", "wisconsin")
DATA_DIR = Path(os.environ.get("DATA_DIR", REPO_DIR / "data"))

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_vite",
    "inertia",
    "ninja",
    "procrastinate.contrib.django",
    "web",
    "ops",
    "api",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.csp.ContentSecurityPolicyMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "inertia.middleware.InertiaMiddleware",
    "web.middleware.SharedPropsMiddleware",
]

ROOT_URLCONF = "config.urls"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.template.context_processors.csp",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATABASES = {
    "default": dj_database_url.parse(
        os.environ.get("DATABASE_URL", "postgres://postgres:password@localhost:5432/agweather2_development"),
        conn_max_age=60,
    )
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/Chicago"
USE_I18N = False
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = Path(os.environ.get("STATIC_ROOT", REPO_DIR / "staticfiles"))
STATICFILES_DIRS = [APP_DIR / "static"]

# Inertia v3's client sends the CSRF token from the XSRF-TOKEN cookie in an X-XSRF-TOKEN header
CSRF_COOKIE_NAME = "XSRF-TOKEN"
CSRF_HEADER_NAME = "HTTP_X_XSRF_TOKEN"

# Vite: in development and unit tests the dev server's URLs (nothing is fetched in tests); otherwise the
# build in app/static/vite. bin/e2e builds and sets VITE_DEV_MODE=0
VITE_DEV_MODE = os.environ.get("VITE_DEV_MODE", "1" if ENV in ("development", "test") else "0") == "1"
VITE_DEV_SERVER_PORT = int(os.environ.get("VITE_PORT", "5173"))
VITE_MANIFEST = APP_DIR / "static" / "vite" / "manifest.json"
DJANGO_VITE = {
    "default": {
        "dev_mode": VITE_DEV_MODE,
        "dev_server_port": VITE_DEV_SERVER_PORT,
        "static_url_prefix": "vite",
        "manifest_path": VITE_MANIFEST,
    }
}

INERTIA_LAYOUT = "base.html"
INERTIA_VERSION = APP_VERSION

# Content Security Policy: scripts only from our origin, plus the nonce for the theme script in base.html.
# Map tiles and overlays come from many public services, so images and connections allow any https source.
# Svelte, MapLibre and ECharts set inline styles. The smoke tests fail on any console error, a violation included.
SECURE_CSP = {
    "default-src": [CSP.SELF],
    "script-src": [CSP.SELF, CSP.NONCE],
    "style-src": [CSP.SELF, CSP.UNSAFE_INLINE],
    "img-src": [CSP.SELF, "data:", "blob:", "https:"],
    "font-src": [CSP.SELF, "data:"],
    "connect-src": [CSP.SELF, "https:"],
    "worker-src": [CSP.SELF, "blob:"],
    "object-src": [CSP.NONE],
    "base-uri": [CSP.SELF],
    "form-action": [CSP.SELF],
    "frame-ancestors": [CSP.NONE],
}
if DEBUG:
    # The Vite dev server: its client, hot reloading over a websocket, and the modules and fonts it serves
    vite = f"http://localhost:{VITE_DEV_SERVER_PORT}"
    for directive in ("script-src", "style-src", "font-src", "img-src", "connect-src", "worker-src"):
        SECURE_CSP[directive].append(vite)
    SECURE_CSP["connect-src"].append(f"ws://localhost:{VITE_DEV_SERVER_PORT}")

if ENV == "production":
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    CSRF_TRUSTED_ORIGINS = [f"https://{host}" for host in ALLOWED_HOSTS]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": os.environ.get("LOG_LEVEL", "INFO")},
    # Procrastinate logs every task registration at INFO
    "loggers": {"procrastinate": {"level": "WARNING"}},
}
