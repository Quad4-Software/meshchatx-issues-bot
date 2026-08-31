from meshchatx_issues_bot.config import Settings
from tests.conftest import ADMIN2_HASH, ADMIN_HASH


def test_from_env_defaults(settings: Settings):
    assert settings.bot_name == "MeshChatX Issues"
    assert settings.command_prefix == "/"
    assert settings.admin_hashes == frozenset({ADMIN_HASH})
    assert settings.notify_hashes == frozenset({ADMIN_HASH, ADMIN2_HASH})
    assert settings.stamp_cost == 8
    assert settings.test_mode is True
    assert settings.cmd("report") == "/report"


def test_notify_falls_back_to_admins(monkeypatch):
    monkeypatch.setenv("ADMIN_LXMF", ADMIN_HASH)
    monkeypatch.delenv("NOTIFY_LXMF", raising=False)
    settings = Settings.from_env()
    assert settings.notify_hashes == frozenset({ADMIN_HASH})
    assert settings.ticket_recipients == frozenset({ADMIN_HASH})


def test_empty_command_prefix(monkeypatch):
    monkeypatch.setenv("ADMIN_LXMF", ADMIN_HASH)
    monkeypatch.setenv("COMMAND_PREFIX", "")
    settings = Settings.from_env()
    assert settings.command_prefix is None
    assert settings.cmd("help") == "help"


def test_stamp_cost_disabled(monkeypatch):
    monkeypatch.setenv("ADMIN_LXMF", ADMIN_HASH)
    for raw in ("0", "none", "off", "false", ""):
        monkeypatch.setenv("STAMP_COST", raw)
        assert Settings.from_env().stamp_cost is None


def test_stamp_cost_capped(monkeypatch):
    monkeypatch.setenv("ADMIN_LXMF", ADMIN_HASH)
    monkeypatch.setenv("STAMP_COST", "255")
    assert Settings.from_env().stamp_cost == 254


def test_admin_names_and_validate(monkeypatch):
    monkeypatch.setenv("ADMIN_LXMF", ADMIN_HASH)
    monkeypatch.setenv("ADMIN_NAMES", f"{ADMIN_HASH}:Ops,{ADMIN2_HASH}:Other")
    settings = Settings.from_env()
    assert settings.admin_display_names[ADMIN_HASH] == "Ops"
    assert settings.validate() == []


def test_validate_warns_without_admins(monkeypatch):
    monkeypatch.setenv("ADMIN_LXMF", "")
    monkeypatch.setenv("NOTIFY_LXMF", "")
    warnings = Settings.from_env().validate()
    assert any("ADMIN_LXMF" in w for w in warnings)
    assert any("NOTIFY_LXMF" in w for w in warnings)


def test_bool_parsing(monkeypatch):
    monkeypatch.setenv("ADMIN_LXMF", ADMIN_HASH)
    monkeypatch.setenv("ANNOUNCE_IMMEDIATELY", "yes")
    monkeypatch.setenv("GRANT_ADMIN_TICKETS", "0")
    settings = Settings.from_env()
    assert settings.announce_immediately is True
    assert settings.grant_admin_tickets is False
