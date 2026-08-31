import pytest
from meshchatx_issues_bot.lxmf_hash import normalize_lxmf_hash


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        ("", None),
        ("not-a-hash", None),
        ("abcd", None),
        ("g" * 32, None),
        ("A" * 32, "a" * 32),
        ("a" * 32, "a" * 32),
        ("<" + "b" * 32 + ">", "b" * 32),
        ("  " + "c" * 32 + "  ", "c" * 32),
        ("zz" + "c" * 30, None),
        (bytes.fromhex("d" * 32), "d" * 32),
    ],
)
def test_normalize_lxmf_hash(value, expected):
    assert normalize_lxmf_hash(value) == expected


def test_normalize_strips_spaces_inside_hex():
    spaced = " ".join(["ab"] * 16)
    assert normalize_lxmf_hash(spaced) == "ab" * 16
