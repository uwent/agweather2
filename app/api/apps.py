from django.apps import AppConfig


class ApiConfig(AppConfig):
    name = "api"
    verbose_name = "Public API"

    def ready(self):
        from django.conf import settings

        from agdata import regions

        # Open water for summaries, model maps and land_only from the terrain store where it's built (D6)
        regions.use_terrain(lambda: settings.DATA_DIR)
