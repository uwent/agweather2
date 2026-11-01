"""config.settings' start-up checks, tested in a subprocess so this process's own settings are left alone."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

APP = Path(__file__).parents[2]


def import_settings(**env: str) -> subprocess.CompletedProcess:
    """Imports config.settings with only the given variables set ("": empty), as a fresh Python would."""
    environment = {k: v for k, v in os.environ.items() if k not in {"DJANGO_ENV", "SECRET_KEY", "DATABASE_URL"}}
    environment.pop("PYTEST_CURRENT_TEST", None)
    environment.update(env)  # "" rather than unset: a developer's .env can't fill in a variable that's already set
    return subprocess.run(
        [sys.executable, "-c", "import config.settings as s; print(s.ENV, s.DEBUG)"],
        env=environment,
        cwd=APP,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_an_unknown_environment_name_is_refused():
    result = import_settings(DJANGO_ENV="prod")
    assert result.returncode != 0
    assert "DJANGO_ENV must be development, test or production, not 'prod'" in result.stderr


@pytest.mark.parametrize(("name", "debug"), [("development", "True"), ("test", "False")])
def test_the_non_production_environments_load(name, debug):
    result = import_settings(DJANGO_ENV=name)
    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == [name, debug]


def test_production_requires_a_database_url():
    result = import_settings(DJANGO_ENV="production", SECRET_KEY="a-real-secret", DATABASE_URL="")
    assert result.returncode != 0
    assert "DATABASE_URL must be set in production" in result.stderr


def test_production_requires_a_secret_key():
    result = import_settings(DJANGO_ENV="production", SECRET_KEY="", DATABASE_URL="postgres://u:p@db/app")
    assert result.returncode != 0
    assert "SECRET_KEY must be set in production" in result.stderr


def test_production_loads_with_both_and_turns_debug_off():
    result = import_settings(DJANGO_ENV="production", SECRET_KEY="a-real-secret", DATABASE_URL="postgres://u:p@db/app")
    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == ["production", "False"]
