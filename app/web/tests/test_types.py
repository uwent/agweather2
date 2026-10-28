from django.core.management import call_command

from web.management.commands.export_types import all_props
from web.props import HomeProps, SharedProps


def test_every_props_class_is_exported(capsys):
    call_command("export_types")
    schema = capsys.readouterr().out
    for cls in (HomeProps, SharedProps):
        assert f'"{cls.__name__}"' in schema
    assert len(all_props()) >= 3
