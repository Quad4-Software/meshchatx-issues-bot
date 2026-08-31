from dataclasses import replace
from types import SimpleNamespace

import LXMF
from meshchatx_issues_bot.attachments import (
    ParsedAttachment,
    _enforce_size_limit,
    _safe_name,
    load_bytes,
    message_fields,
    parse_incoming,
    save_for_issue,
)
from meshchatx_issues_bot.config import Settings
from meshchatx_issues_bot.models import IssueAttachment


def test_safe_name():
    assert _safe_name("../../etc/passwd") == "passwd"
    assert _safe_name("weird name!!.txt") == "weird_name_.txt"
    assert _safe_name("   ") == "file"


def test_enforce_size_limit():
    items = [
        ParsedAttachment(kind="file", name="ok", data=b"abc"),
        ParsedAttachment(kind="file", name="big", data=b"x" * 10),
    ]
    kept = _enforce_size_limit(items, max_bytes=5)
    assert [i.name for i in kept] == ["ok"]


def test_message_fields():
    assert message_fields(None) == {}
    assert message_fields(SimpleNamespace(fields={"a": 1})) == {"a": 1}
    assert message_fields(SimpleNamespace(get_fields=lambda: {"b": 2})) == {"b": 2}


def test_parse_incoming_and_save(settings: Settings, tmp_path):
    settings = replace(
        settings,
        storage_path=str(tmp_path),
        max_attachments_per_issue=2,
        max_attachment_bytes=100,
    )
    message = SimpleNamespace(
        fields={
            LXMF.LXMF.FIELD_FILE_ATTACHMENTS: [
                ["notes.txt", b"hello"],
                ["skip.bin", object()],
            ],
            LXMF.LXMF.FIELD_IMAGE: ["webp", b"imgdata"],
            LXMF.LXMF.FIELD_AUDIO: [0, b"audiodata"],
        },
    )
    parsed = parse_incoming(message, settings)
    assert len(parsed) == 2
    assert parsed[0].kind == "file"
    assert parsed[1].kind == "image"

    stored = save_for_issue(settings, 1, parsed)
    assert len(stored) == 2
    assert load_bytes(stored[0], settings) == b"hello"
    missing = IssueAttachment(kind="file", name="x", path="missing.bin", size=0)
    assert load_bytes(missing, settings) is None
