"""The changelog page and the "Tell us how you use the API" form (D112). Phase 7 designs both pages; these serve the
data and the form's round trip."""

import json
from typing import Any

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.views.decorators.http import require_http_methods

from api.ratelimit import address_key, client_key
from updates import forms
from updates.models import ApiUseReport, ChangelogEntry
from updates.props import ApiUseProps, ChangelogEntryProps, ChangelogKind, ChangelogProps, FrequencyChoice
from web.inertia import redirect_with_errors, render

THANKS = "Thank you. We've received your answers."


def changelog(request: HttpRequest) -> HttpResponse:
    entries = [ChangelogEntryProps.of(e) for e in ChangelogEntry.objects.visible()]
    kinds = [ChangelogKind(value=v, label=str(label)) for v, label in ChangelogEntry.Kind.choices]
    return render(request, "Updates/Changelog", ChangelogProps(entries=entries, kinds=kinds))


def _sent(request: HttpRequest) -> dict[str, Any]:
    """The form's fields: Inertia sends JSON, a plain form (and the tests) form data."""
    if request.content_type == "application/json":
        try:
            body = json.loads(request.body or b"{}")
        except ValueError:
            return {}
        return body if isinstance(body, dict) else {}
    return {key: request.POST.getlist(key) if key == "areas" else request.POST.get(key) for key in request.POST}


@require_http_methods(["GET", "POST"])
def api_use(request: HttpRequest) -> HttpResponse:
    if request.method == "GET":
        return render(
            request,
            "Updates/ApiUse",
            ApiUseProps(
                areas=forms.areas(),
                frequencies=[FrequencyChoice(value=v, label=str(label)) for v, label in ApiUseReport.Frequency.choices],
                form_token=forms.form_token(),
            ),
        )
    data = _sent(request)
    form = forms.ApiUseForm(data=data)
    age = forms.token_age(str(data.get("form_token") or ""))
    if form.is_bot or (age is not None and age < forms.MIN_SECONDS):
        # Dropped quietly: a bot sees what a person would
        messages.success(request, THANKS)
        return redirect("api-use")
    if age is None:
        return redirect_with_errors(request, "/api-use", {"form": [forms.RELOAD]})
    if not form.is_valid():
        return redirect_with_errors(request, "/api-use", {k: [str(m) for m in v] for k, v in form.errors.items()})
    address = request.META.get("REMOTE_ADDR")
    client = address_key(address) or ""
    limited = forms.over_limit(client, exempt=client_key(address) is None)
    if limited:
        return redirect_with_errors(request, "/api-use", {"form": [limited]})
    report = form.save(commit=False)
    report.client = client
    report.save()
    messages.success(request, THANKS)
    return redirect("api-use")
