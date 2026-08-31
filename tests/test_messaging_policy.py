from meshchatx_issues_bot.config import Settings
from meshchatx_issues_bot.identity import is_admin_address
from meshchatx_issues_bot.messaging import should_include_ticket
from tests.conftest import ADMIN_HASH, REPORTER_HASH


def test_is_admin_address(settings: Settings):
    assert is_admin_address(ADMIN_HASH, None, settings) is True
    assert is_admin_address(None, ADMIN_HASH, settings) is True
    assert is_admin_address(REPORTER_HASH, None, settings) is False
    assert is_admin_address(None, None, settings) is False


def test_should_include_ticket(settings: Settings, monkeypatch):
    assert should_include_ticket(ADMIN_HASH, settings) is True
    assert should_include_ticket(REPORTER_HASH, settings) is False

    monkeypatch.setenv("GRANT_ADMIN_TICKETS", "false")
    disabled = Settings.from_env()
    assert should_include_ticket(ADMIN_HASH, disabled) is False

    monkeypatch.setenv("GRANT_ADMIN_TICKETS", "true")
    monkeypatch.setenv("STAMP_COST", "0")
    no_stamps = Settings.from_env()
    assert should_include_ticket(ADMIN_HASH, no_stamps) is False
