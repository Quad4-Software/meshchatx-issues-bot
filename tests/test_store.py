from meshchatx_issues_bot.models import IssueAttachment
from meshchatx_issues_bot.store import BlockStore, IssueStore


def test_create_get_and_list(issue_store: IssueStore, reporter_hash: str):
    first = issue_store.create(reporter_hash, "One", "body one")
    second = issue_store.create(reporter_hash, "Two", "body two")
    assert first.id == 1
    assert second.id == 2
    assert issue_store.get(1).title == "One"
    listed = issue_store.list_issues(reporter=reporter_hash)
    assert [i.id for i in listed] == [2, 1]


def test_close_and_append(issue_store: IssueStore, reporter_hash: str, admin_hash: str):
    issue = issue_store.create(reporter_hash, "Bug", "initial")
    updated, err = issue_store.append_to_issue(
        issue.id,
        reporter_hash,
        text="more details",
        new_attachments=[
            IssueAttachment(kind="file", name="a.txt", path="p", size=1),
        ],
    )
    assert err is None
    assert updated is not None
    assert "more details" in updated.body
    assert len(updated.attachments) == 1

    closed = issue_store.close(issue.id, closed_by=admin_hash, close_message="done")
    assert closed is not None
    assert closed.status == "closed"
    assert closed.close_message == "done"

    again, err = issue_store.append_to_issue(issue.id, reporter_hash, text="nope")
    assert again is None
    assert err == "closed"

    other, err = issue_store.append_to_issue(issue.id, "c" * 32, text="nope")
    assert other is None
    assert err == "forbidden"


def test_append_forbidden_and_missing(issue_store: IssueStore, reporter_hash: str):
    issue = issue_store.create(reporter_hash, "Bug", "body")
    _, err = issue_store.append_to_issue(issue.id, "d" * 32, text="x")
    assert err == "forbidden"
    missing, err = issue_store.append_to_issue(999, reporter_hash, text="x")
    assert missing is None
    assert err == "not_found"


def test_block_store(block_store: BlockStore, reporter_hash: str):
    assert block_store.is_blocked(reporter_hash) is False
    assert block_store.block(reporter_hash) is True
    assert block_store.block(reporter_hash) is False
    assert block_store.is_blocked(reporter_hash) is True
    assert block_store.list_blocked() == [reporter_hash]
    assert block_store.unblock(reporter_hash) is True
    assert block_store.unblock(reporter_hash) is False
    assert block_store.block("not-a-hash") is False
