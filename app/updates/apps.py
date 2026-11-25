from django.apps import AppConfig


class UpdatesConfig(AppConfig):
    """What we tell the people who use AgWeather (the changelog) and what they tell us (API-use reports), D112."""

    name = "updates"
    verbose_name = "Updates and feedback"
