from meshchatx_issues_bot.app import build_app
from meshchatx_issues_bot.config import Settings


def test_build_app_test_mode(monkeypatch, tmp_path):
    monkeypatch.setenv("ADMIN_LXMF", "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb")
    monkeypatch.setenv("STORAGE_PATH", str(tmp_path / "data"))
    monkeypatch.setenv("TEST_MODE", "true")
    monkeypatch.setenv("REQUIRE_IDENTITY_VERIFICATION", "false")
    monkeypatch.setenv("STAMP_COST", "0")
    monkeypatch.setenv("FIRST_MESSAGE_ENABLED", "false")

    app = build_app()
    assert isinstance(app.settings, Settings)
    assert app.settings.test_mode is True
    assert app.bot.config.test_mode is True
    assert "report" in app.bot.commands or app.settings.cmd_report in app.bot.commands
