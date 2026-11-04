#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    if len(sys.argv) == 1 and sys.stdin.isatty() and sys.stdout.isatty():
        # No command on a terminal: the data dashboard (ops.tui); `manage.py help` lists the commands
        import django

        django.setup()
        from ops.tui import main

        main()
        sys.exit(0)
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
