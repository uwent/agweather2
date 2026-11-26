"""The changelog and the API-use reports (D112).

A `ChangelogEntry` is written by staff in the admin and shown, once published, on `/changelog`, in its Atom feed and
at `GET /api/v2/changelog`. An `ApiUseReport` is what someone sent through the "Tell us how you use the API" form
(`/api-use`), kept for staff to read. Models' own version histories stay in their specs (`ModelSpec.changelog`,
served by `/models/{id}`); an entry here is for what's worth announcing.
"""

from datetime import datetime
from typing import Any, ClassVar

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

API_PREFIX = "/api/v2"


def api_paths() -> set[str]:
    """The API's endpoints as documented (`/degree-days`, `/models/{model_id}`), without the `/api/v2` prefix."""
    from api.api import api  # the API imports this app's models (its changelog route)

    return {path.removeprefix(API_PREFIX) for path in api.get_openapi_schema()["paths"]}


class ChangelogManager(models.Manager["ChangelogEntry"]):
    def visible(self) -> models.QuerySet["ChangelogEntry"]:
        """Published entries, newest first."""
        return self.filter(published=True)

    def banners(self, *, now: datetime | None = None) -> models.QuerySet["ChangelogEntry"]:
        """Published entries whose banner is still up at `now` (default: now)."""
        return self.visible().filter(banner_until__gt=now or timezone.now())


class ChangelogEntry(models.Model):
    class Kind(models.TextChoices):
        API = "api", "API change"
        MODEL = "model", "Models"
        DATA = "data", "Data and sources"
        OUTAGE = "outage", "Outage or delay"
        ANNOUNCEMENT = "announcement", "Announcement"

    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.ANNOUNCEMENT)
    date = models.DateField(default=timezone.localdate, help_text="The date shown with the entry.")
    title = models.CharField(max_length=120)
    body = models.TextField(
        blank=True,
        help_text="Markdown (links, lists, emphasis; HTML is shown as text). Write for the public: plain, complete sentences.",
    )
    published = models.BooleanField(
        default=False, help_text="Only published entries are shown. Leave it off for a draft."
    )
    banner_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Show the entry as a banner on the site until this time. Leave it empty for no banner.",
    )
    model_id = models.CharField(
        max_length=64, blank=True, help_text="The model this entry is about, by its id (late-blight-dsv), if any."
    )
    endpoint = models.CharField(
        max_length=120, blank=True, help_text="The API endpoint this entry is about (/degree-days), if any."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects: ClassVar[ChangelogManager] = ChangelogManager()

    class Meta:
        ordering = ["-date", "-id"]
        indexes = [models.Index(fields=["published", "-date"])]
        verbose_name = "changelog entry"
        verbose_name_plural = "changelog entries"

    def __str__(self) -> str:
        return f"{self.date} {self.title}"

    def clean(self) -> None:
        """Checks the model id against the registry and the endpoint against the API's paths (not `choices`, which
        would make a migration for every new model or endpoint)."""
        from agmodels.registry import all_models

        problems: dict[str, Any] = {}
        if self.model_id and self.model_id not in all_models():
            problems["model_id"] = f"There's no model with the id '{self.model_id}'."
        if self.endpoint:
            self.endpoint = "/" + self.endpoint.strip().removeprefix(API_PREFIX).strip("/")
            if self.endpoint not in api_paths():
                problems["endpoint"] = (
                    f"The API has no endpoint '{self.endpoint}'. Write it as on the API's docs page, as '/degree-days'."
                )
        if problems:
            raise ValidationError(problems)


class ApiUseReport(models.Model):
    class Frequency(models.TextChoices):
        OCCASIONALLY = "occasionally", "Now and then"
        WEEKLY = "weekly", "About once a week"
        DAILY = "daily", "Every day"
        HOURLY = "hourly", "Every hour"
        MORE = "more", "More often than every hour"

    name = models.CharField(max_length=200)
    organization = models.CharField(max_length=200, blank=True)
    email = models.EmailField(blank=True)
    uses = models.TextField(max_length=5000, verbose_name="What you use the API for")
    areas = models.JSONField(default=list, blank=True, help_text="The parts of the API used (its docs' groups)")
    endpoints = models.TextField(max_length=2000, blank=True, verbose_name="Endpoints and anything you'd like added")
    frequency = models.CharField(max_length=16, choices=Frequency.choices, blank=True)
    notify = models.BooleanField(default=False, verbose_name="Email before changes that affect the API")
    client = models.CharField(
        max_length=64, blank=True, help_text="The sender's IPv4 address or IPv6 /64, for limiting reports"
    )
    submitted_at = models.DateTimeField(default=timezone.now)
    reviewed = models.BooleanField(default=False)
    notes = models.TextField(blank=True, help_text="Staff notes; never shown to the sender")

    class Meta:
        ordering = ["-submitted_at"]
        indexes = [models.Index(fields=["client", "submitted_at"])]
        verbose_name = "API use report"

    def __str__(self) -> str:
        return f"{self.name} ({self.submitted_at:%Y-%m-%d})"
