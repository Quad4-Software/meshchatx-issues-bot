import re

_HASH_RE = re.compile(r"^[0-9a-f]{32}$")


def normalize_lxmf_hash(value: str | bytes | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, bytes):
        h = value.hex()
    else:
        h = str(value).strip().lower()
        h = h.replace(" ", "").replace("<", "").replace(">", "")
    if len(h) != 32 or not _HASH_RE.match(h):
        return None
    return h
