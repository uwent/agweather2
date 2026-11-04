from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "The data dashboard (also `manage.py` with no command): each year of the archive, the lock, the worker, and "
        "every data command running, live; keys start and stop commands in the background."
    )

    def handle(self, *args, **options):
        from ops.tui import main

        main()
