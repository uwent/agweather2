import os

from django.conf import settings
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_asgi_application()

if settings.SERVE_STATIC:
    from django.contrib.staticfiles.handlers import ASGIStaticFilesHandler  # pyright: ignore[reportAttributeAccessIssue]

    application = ASGIStaticFilesHandler(application)
