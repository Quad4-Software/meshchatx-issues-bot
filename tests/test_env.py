import os

from meshchatx_issues_bot.env import load_env_file


def test_load_env_file_from_cwd(tmp_path, monkeypatch):
    env_path = tmp_path / ".env"
    env_path.write_text("BOT_NAME=FromDotEnv\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("BOT_NAME", raising=False)
    found = load_env_file()
    assert found == env_path
    assert os.environ["BOT_NAME"] == "FromDotEnv"


def test_load_env_file_does_not_override_shell(tmp_path, monkeypatch):
    env_path = tmp_path / ".env"
    env_path.write_text("BOT_NAME=FromDotEnv\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("BOT_NAME", "FromShell")
    load_env_file()
    assert os.environ["BOT_NAME"] == "FromShell"
