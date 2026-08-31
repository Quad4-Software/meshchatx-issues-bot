from meshchatx_issues_bot.models import Issue, IssueAttachment


def test_issue_attachment_roundtrip():
    att = IssueAttachment(
        kind="file",
        name="log.txt",
        path="attachments/1/00_log.txt",
        format=None,
        size=12,
    )
    restored = IssueAttachment.from_dict(att.to_dict())
    assert restored == att


def test_issue_roundtrip_with_attachments():
    issue = Issue(
        id=3,
        reporter="a" * 32,
        title="Crash",
        body="Details",
        created_at=1_700_000_000.0,
        attachments=[
            IssueAttachment(
                kind="image",
                name="shot.webp",
                path="attachments/3/00_shot.webp",
                format="webp",
                size=99,
            ),
        ],
        status="closed",
        closed_at=1_700_000_100.0,
        closed_by="b" * 32,
        close_message="fixed",
    )
    restored = Issue.from_dict(issue.to_dict())
    assert restored.id == 3
    assert restored.status == "closed"
    assert restored.close_message == "fixed"
    assert len(restored.attachments) == 1
    assert restored.attachments[0].name == "shot.webp"


def test_issue_from_dict_skips_bad_attachments():
    raw = {
        "id": 1,
        "reporter": "a" * 32,
        "title": "t",
        "body": "b",
        "created_at": 1.0,
        "attachments": ["nope", {"kind": "file", "name": "ok", "path": "p"}],
    }
    issue = Issue.from_dict(raw)
    assert len(issue.attachments) == 1
    assert issue.attachments[0].name == "ok"
