from meshchatx_issues_bot.models import Issue
from meshchatx_issues_bot.notify import (
    format_admin_message,
    format_admin_update,
    format_close_notice,
)


def test_format_admin_message_with_attachments():
    issue = Issue(
        id=1,
        reporter="a" * 32,
        title="t",
        body="body text",
        created_at=1.0,
        attachments=[],
    )
    text = format_admin_message(issue)
    assert "New issue #1" in text
    assert "body text" in text

    from meshchatx_issues_bot.models import IssueAttachment

    issue.attachments = [
        IssueAttachment(kind="file", name="a.txt", path="p", size=1),
        IssueAttachment(kind="image", name="b.webp", path="p2", size=2),
    ]
    text = format_admin_message(issue)
    assert "Attachments (2): a.txt, b.webp" in text


def test_format_admin_update_variants():
    issue = Issue(
        id=2,
        reporter="a" * 32,
        title="t",
        body="b",
        created_at=1.0,
    )
    with_text = format_admin_update(
        issue,
        update_text="more info",
        new_attachment_names=[],
    )
    assert "more info" in with_text

    with_files = format_admin_update(
        issue,
        update_text=None,
        new_attachment_names=["shot.webp"],
    )
    assert "New attachments: shot.webp" in with_files

    empty = format_admin_update(
        issue,
        update_text=None,
        new_attachment_names=[],
    )
    assert "(attachments added)" in empty


def test_format_close_notice():
    issue = Issue(
        id=9,
        reporter="a" * 32,
        title="t",
        body="b",
        created_at=1.0,
        close_message="duplicate",
    )
    notice = format_close_notice(
        issue,
        closer_label="Ops",
        closer_address="b" * 32,
    )
    assert "#9" in notice
    assert "Ops" in notice
    assert "duplicate" in notice
