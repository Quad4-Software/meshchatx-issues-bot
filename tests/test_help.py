from meshchatx_issues_bot.commands.help import (
    _admin_commands,
    _find_command,
    _user_commands,
)
from meshchatx_issues_bot.config import Settings


def test_command_catalogs(settings: Settings):
    users = _user_commands(settings)
    admins = _admin_commands(settings)
    assert any(name == "report" for name, _, _ in users)
    assert any(name == "close" for name, _, _ in admins)


def test_find_command(settings: Settings):
    assert _find_command("report", settings, include_admin=False) is not None
    assert _find_command("close", settings, include_admin=False) is None
    assert _find_command("close", settings, include_admin=True) is not None
    assert _find_command("nope", settings, include_admin=True) is None
