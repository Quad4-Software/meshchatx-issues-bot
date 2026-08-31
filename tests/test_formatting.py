from meshchatx_issues_bot.config import Settings
from meshchatx_issues_bot.formatting import (
    format_issue,
    format_issue_list,
    format_report_confirmation,
    format_update_confirmation,
    issue_preview,
)
from meshchatx_issues_bot.models import Issue, IssueAttachment


def _issue(**kwargs) -> Issue:
    base = dict(
        id=7,
        reporter="a" * 32,
        title="t",
        body="hello world",
        created_at=1_700_000_000.0,
    )
    base.update(kwargs)
    return Issue(**base)


def test_issue_preview_truncates():
    assert issue_preview(_issue(body="")) == "(empty)"
    assert issue_preview(_issue(body="short")) == "short"
    long = "x" * 80
    preview = issue_preview(_issue(body=long), max_len=20)
    assert preview.endswith("...")
    assert len(preview) == 20


def test_format_issue_open_and_closed():
    open_text = format_issue(_issue(), include_reporter=True)
    assert "#7 [open]" in open_text
    assert "Reporter:" in open_text
    assert "hello world" in open_text

    closed = _issue(
        status="closed",
        closed_at=1_700_000_100.0,
        closed_by="b" * 32,
        close_message="fixed upstream",
        attachments=[
            IssueAttachment(kind="file", name="a.log", path="p", size=10),
        ],
    )
    closed_text = format_issue(closed)
    assert "Resolution: fixed upstream" in closed_text
    assert "Attachments: 1" in closed_text
    assert "a.log" in closed_text


def test_format_issue_list(settings: Settings):
    issues = [_issue(id=2, body="second"), _issue(id=1, body="first")]
    admin = format_issue_list(issues, settings, admin_view=True)
    user = format_issue_list(issues, settings, admin_view=False)
    assert format_issue_list([], settings, admin_view=False) == "No issues found."
    assert issues[0].reporter in admin
    assert issues[0].reporter not in user
    assert "/issue <id>" in user


def test_confirmations(settings: Settings):
    issue = _issue(
        attachments=[
            IssueAttachment(kind="file", name="a.txt", path="p", size=1),
        ],
    )
    report = format_report_confirmation(
        issue,
        admins_notified=0,
        attachments_forwarded=0,
        settings=settings,
        notify_failures=["b" * 32],
    )
    assert "could not be delivered" in report
    assert "Attachments saved: 1" in report

    update = format_update_confirmation(
        issue,
        added_text=True,
        added_attachments=2,
        admins_notified=1,
        settings=settings,
    )
    assert "Text appended." in update
    assert "Attachments added: 2." in update
    assert "Admins notified: 1." in update

    quiet = format_update_confirmation(
        issue,
        added_text=False,
        added_attachments=0,
        admins_notified=0,
        settings=settings,
        notify_failures=["b" * 32],
    )
    assert "could not be delivered" in quiet
