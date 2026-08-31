from meshchatx_issues_bot.commands.admin import _parse_close_args
from meshchatx_issues_bot.commands.helpers import (
    parse_report_body,
    parse_update_args,
    title_from_body,
)


def test_parse_report_body():
    assert parse_report_body([]) is None
    assert parse_report_body(["", "  "]) is None
    assert parse_report_body(["hello", "world"]) == "hello world"


def test_parse_update_args():
    assert parse_update_args([]) is None
    assert parse_update_args(["x"]) is None
    assert parse_update_args(["12"]) == (12, "")
    assert parse_update_args(["3", "more", "text"]) == (3, "more text")


def test_title_from_body():
    assert title_from_body("") == "Issue report"
    assert title_from_body("  line one\nline two") == "line one"
    long = "x" * 100
    title = title_from_body(long, max_len=20)
    assert title.endswith("...")
    assert len(title) == 20


def test_parse_close_args():
    assert _parse_close_args([]) is None
    assert _parse_close_args(["x"]) is None
    assert _parse_close_args(["5"]) == (5, "closed")
    assert _parse_close_args(["5", "  "]) == (5, "closed")
    assert _parse_close_args(["8", "not", "repro"]) == (8, "not repro")
