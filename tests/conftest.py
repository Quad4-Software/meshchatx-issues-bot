import pytest
from lxmfy.storage import MemoryStorage, Storage
from meshchatx_issues_bot.config import Settings
from meshchatx_issues_bot.store import BlockStore, IssueStore

ADMIN_HASH = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
ADMIN2_HASH = "cccccccccccccccccccccccccccccccc"
REPORTER_HASH = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"


@pytest.fixture
def admin_hash() -> str:
    return ADMIN_HASH


@pytest.fixture
def reporter_hash() -> str:
    return REPORTER_HASH


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch, tmp_path) -> Settings:
    monkeypatch.setenv("ADMIN_LXMF", ADMIN_HASH)
    monkeypatch.setenv("NOTIFY_LXMF", f"{ADMIN_HASH},{ADMIN2_HASH}")
    monkeypatch.setenv("STORAGE_PATH", str(tmp_path))
    monkeypatch.setenv("COMMAND_PREFIX", "/")
    monkeypatch.setenv("STAMP_COST", "6")
    monkeypatch.setenv("GRANT_ADMIN_TICKETS", "true")
    monkeypatch.setenv("REQUIRE_IDENTITY_VERIFICATION", "false")
    monkeypatch.setenv("TEST_MODE", "true")
    return Settings.from_env()


@pytest.fixture
def memory_storage() -> Storage:
    return Storage(MemoryStorage())


@pytest.fixture
def issue_store(memory_storage: Storage) -> IssueStore:
    return IssueStore(memory_storage)


@pytest.fixture
def block_store(memory_storage: Storage) -> BlockStore:
    return BlockStore(memory_storage)
