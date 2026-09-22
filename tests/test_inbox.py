from types import SimpleNamespace

import LXMF
from meshchatx_issues_bot.attachments import (
    ParsedAttachment,
    fit_byte_budget,
    has_attachments,
)
from meshchatx_issues_bot.commands.inbox import resolve_target, split_issue_ref
from meshchatx_issues_bot.ratelimit import RateLimiter
from meshchatx_issues_bot.store import IssueStore

OTHER_HASH = "dddddddddddddddddddddddddddddddd"


def test_split_issue_ref():
    assert split_issue_ref("") == (None, "")
    assert split_issue_ref("#5") == (5, "")
    assert split_issue_ref("#5 here is the log") == (5, "here is the log")
    assert split_issue_ref("7") == (7, "")
    assert split_issue_ref("a caption") == (None, "a caption")
    assert split_issue_ref("issue 5 broke") == (None, "issue 5 broke")


def test_has_attachments():
    assert has_attachments(None) is False
    assert has_attachments(SimpleNamespace(fields={})) is False
    assert (
        has_attachments(
            SimpleNamespace(fields={LXMF.LXMF.FIELD_IMAGE: ["webp", b"x"]}),
        )
        is True
    )
    assert (
        has_attachments(
            SimpleNamespace(
                fields={LXMF.LXMF.FIELD_FILE_ATTACHMENTS: [["a.txt", b"x"]]},
            ),
        )
        is True
    )


def test_fit_byte_budget():
    items = [
        ParsedAttachment(kind="file", name="a", data=b"1234"),
        ParsedAttachment(kind="file", name="b", data=b"5678"),
        ParsedAttachment(kind="file", name="c", data=b"9"),
    ]
    kept = fit_byte_budget(items, 8)
    assert [i.name for i in kept] == ["a", "b"]
    assert fit_byte_budget(items, 0) == []


def test_resolve_target_explicit(issue_store: IssueStore, reporter_hash: str):
    issue = issue_store.create(reporter_hash, "t", "body")

    found, err = resolve_target(issue_store, reporter_hash, issue.id)
    assert err is None
    assert found.id == issue.id

    found, err = resolve_target(issue_store, reporter_hash, 999)
    assert found is None
    assert "not found" in err

    found, err = resolve_target(issue_store, OTHER_HASH, issue.id)
    assert found is None
    assert "own issues" in err

    issue_store.close(issue.id, closed_by="admin")
    found, err = resolve_target(issue_store, reporter_hash, issue.id)
    assert found is None
    assert "closed" in err


def test_resolve_target_active_and_fallback(
    issue_store: IssueStore,
    reporter_hash: str,
):
    found, err = resolve_target(issue_store, reporter_hash, None)
    assert found is None
    assert err == "no_issue"

    first = issue_store.create(reporter_hash, "t", "first")
    second = issue_store.create(reporter_hash, "t", "second")

    issue_store.set_active(reporter_hash, first.id)
    found, err = resolve_target(issue_store, reporter_hash, None)
    assert err is None
    assert found.id == first.id

    issue_store.close(first.id, closed_by="admin")
    found, err = resolve_target(issue_store, reporter_hash, None)
    assert err is None
    assert found.id == second.id


def test_active_issue_roundtrip(issue_store: IssueStore, reporter_hash: str):
    assert issue_store.active_issue(reporter_hash) is None
    issue_store.set_active(reporter_hash, 3)
    assert issue_store.active_issue(reporter_hash) == 3
    assert issue_store.active_issue("not-a-hash") is None


def test_reopen(issue_store: IssueStore, reporter_hash: str):
    issue = issue_store.create(reporter_hash, "t", "body")
    assert issue_store.reopen(issue.id) is None

    issue_store.close(issue.id, closed_by="admin", close_message="done")
    reopened = issue_store.reopen(issue.id)
    assert reopened is not None
    assert reopened.status == "open"
    assert reopened.closed_at is None
    assert reopened.closed_by is None
    assert reopened.close_message is None
    assert issue_store.reopen(999) is None


def test_rate_limiter(memory_storage, reporter_hash: str):
    limiter = RateLimiter(memory_storage, "t", limit=2, window=60)
    assert limiter.allow(reporter_hash, now=1000.0) is True
    assert limiter.allow(reporter_hash, now=1001.0) is True
    assert limiter.allow(reporter_hash, now=1002.0) is False
    assert limiter.allow(reporter_hash, now=2000.0) is True
    limiter.reset(reporter_hash)
    assert limiter.allow(reporter_hash, now=2001.0) is True
    assert limiter.allow("bad-hash") is False


def test_pending_store(memory_storage, reporter_hash: str):
    from meshchatx_issues_bot.pending import PendingStore

    pending = PendingStore(memory_storage)
    assert pending.count() == 0
    assert pending.add("bad-hash", "t", "x") is None

    entry_id = pending.add(reporter_hash, "Issue #1", "hello")
    assert entry_id is not None
    assert pending.count() == 1

    entries = pending.for_destination(reporter_hash)
    assert len(entries) == 1
    assert entries[0]["text"] == "hello"
    assert pending.for_destination("c" * 32) == []

    pending.bump_attempts(entry_id)
    assert pending.all()[0]["attempts"] == 1

    pending.remove(entry_id)
    assert pending.count() == 0


def test_flush_pending(memory_storage, settings, reporter_hash, monkeypatch):
    from meshchatx_issues_bot.pending import (
        MAX_ATTEMPTS,
        PendingStore,
        flush_pending,
    )

    pending = PendingStore(memory_storage)
    bot = SimpleNamespace(
        config=SimpleNamespace(test_mode=True),
        send=lambda *a, **k: True,
    )

    pending.add(reporter_hash, "Issue #1", "hi")
    sent, dropped = flush_pending(bot, settings, pending)
    assert (sent, dropped) == (1, 0)
    assert pending.count() == 0

    import meshchatx_issues_bot.messaging as messaging

    def fake_fail(*args, **kwargs):
        cb = kwargs.get("on_failure")
        if cb:
            cb()
        return False

    monkeypatch.setattr(messaging, "deliver_message", fake_fail)
    pending.add(reporter_hash, "t", "x")
    sent, dropped = flush_pending(bot, settings, pending)
    assert (sent, dropped) == (0, 0)
    assert pending.all()[0]["attempts"] == 1

    pending.add(reporter_hash, "t", "old", attempts=MAX_ATTEMPTS)
    sent, dropped = flush_pending(bot, settings, pending)
    assert dropped == 1
    assert pending.count() == 1
