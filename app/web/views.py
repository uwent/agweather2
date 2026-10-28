from django.http import HttpRequest
from django.urls import reverse

from web.inertia import render
from web.props import HomeProps


def home(request: HttpRequest):
    return render(request, "Home", HomeProps(api_docs_url=reverse("api-v2:openapi-view")))
