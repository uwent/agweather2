"""The "Tell us how you use the API" form (D112) and its protections against spam, without a CAPTCHA.

- A honeypot: `website`, a field people never see (off-screen, out of the tab order, hidden from screen readers).
  A form with it filled is dropped as if it had been sent.
- A signed token in the page's props (`form_token`): a form sent under `MIN_SECONDS` after the page was made is
  dropped the same way; one older than `MAX_AGE` asks the reader to reload the page.
- Limits counted in the database (no shared cache is configured): `PER_CLIENT_PER_HOUR` reports from one address
  (an IPv4 address or IPv6 /64, as the API's rate limits count them) and `PER_DAY` from everyone.
- Length caps on every text field.
"""

import time
from datetime import timedelta
from typing import ClassVar

from django import forms
from django.core import signing
from django.utils import timezone

from updates.models import ApiUseReport

SALT = "updates.api-use"
MIN_SECONDS = 3
MAX_AGE = timedelta(days=1)
PER_CLIENT_PER_HOUR = 5
PER_DAY = 100

RELOAD = "This form has expired. Reload the page and send it again."
TOO_MANY = "We've received several reports from your address in the last hour. Please try again later."
BUSY = "We've received more reports than usual today. Please try again tomorrow."


def areas() -> list[str]:
    """The groups of endpoints on the API's docs page, as a reader picks the parts they use."""
    from api import docs

    return list(docs.parameters()["tags"])


def form_token() -> str:
    return signing.dumps(time.time(), salt=SALT)


def token_age(token: str) -> float | None:
    """Seconds since the token was made, or None if it isn't ours or is older than `MAX_AGE`."""
    try:
        made = signing.loads(token, salt=SALT, max_age=MAX_AGE)
    except signing.BadSignature:
        return None
    return time.time() - float(made)


def over_limit(client: str, *, exempt: bool = False) -> str | None:
    """The message for a sender over a limit, or None. An `exempt` sender (the API's exempt addresses: loopback, so
    local scripts and the browser tests) skips the per-address limit, not the daily one."""
    now = timezone.now()
    reports = ApiUseReport.objects
    recent = reports.filter(client=client, submitted_at__gt=now - timedelta(hours=1))
    if client and not exempt and recent.count() >= PER_CLIENT_PER_HOUR:
        return TOO_MANY
    if reports.filter(submitted_at__gt=now - timedelta(days=1)).count() >= PER_DAY:
        return BUSY
    return None


class ApiUseForm(forms.ModelForm):
    areas = forms.MultipleChoiceField(required=False, choices=())
    website = forms.CharField(required=False)  # the honeypot

    class Meta:
        model = ApiUseReport
        fields: ClassVar = ["name", "organization", "email", "uses", "areas", "endpoints", "frequency", "notify"]
        error_messages: ClassVar = {
            "name": {"required": "Tell us your name.", "max_length": "Shorten your name to 200 characters or fewer."},
            "organization": {"max_length": "Shorten the organization's name to 200 characters or fewer."},
            "email": {"invalid": "Check your email address. It should look like 'name@example.org'."},
            "uses": {
                "required": "Tell us what you use the API for.",
                "max_length": "Shorten your description to 5,000 characters or fewer.",
            },
            "endpoints": {"max_length": "Shorten this answer to 2,000 characters or fewer."},
            "frequency": {"invalid_choice": "Choose how often you send requests from the list."},
        }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fields["areas"].choices = [(a, a) for a in areas()]  # pyright: ignore[reportAttributeAccessIssue]
        self.fields["areas"].error_messages["invalid_choice"] = "Choose the parts of the API from the list."

    def clean(self):
        data = super().clean() or {}
        if data.get("notify") and not data.get("email"):
            self.add_error(
                "email", "Add your email address so we can tell you about changes, or clear the box asking us to."
            )
        return data

    @property
    def is_bot(self) -> bool:
        return bool(self.data.get("website"))
