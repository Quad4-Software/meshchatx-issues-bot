import os
import re
from dataclasses import dataclass
from pathlib import Path

import LXMF
from lxmfy.attachments import Attachment, AttachmentType

from meshchatx_issues_bot.config import Settings
from meshchatx_issues_bot.models import IssueAttachment

_UNSAFE_NAME = re.compile(r"[^a-zA-Z0-9._-]+")


@dataclass
class ParsedAttachment:
    kind: str
    name: str
    data: bytes
    format: str | None = None


def message_fields(message) -> dict:
    if message is None:
        return {}
    if hasattr(message, "get_fields"):
        fields = message.get_fields()
        return fields if isinstance(fields, dict) else {}
    raw = getattr(message, "fields", None)
    return raw if isinstance(raw, dict) else {}


def parse_incoming(
    message,
    settings: Settings,
    *,
    max_count: int | None = None,
) -> list[ParsedAttachment]:
    fields = message_fields(message)
    parsed: list[ParsedAttachment] = []
    remaining = (
        max_count if max_count is not None else settings.max_attachments_per_issue
    )

    file_items = fields.get(LXMF.LXMF.FIELD_FILE_ATTACHMENTS)
    if isinstance(file_items, list) and remaining > 0:
        for item in file_items:
            if remaining <= 0:
                break
            att = _parse_file_item(item)
            if att is not None:
                parsed.append(att)
                remaining -= 1

    image_val = fields.get(LXMF.LXMF.FIELD_IMAGE)
    if image_val is not None and remaining > 0:
        att = _parse_image_item(image_val)
        if att is not None:
            parsed.append(att)

    audio_val = fields.get(LXMF.LXMF.FIELD_AUDIO)
    if audio_val is not None and remaining > 0:
        att = _parse_audio_item(audio_val)
        if att is not None:
            parsed.append(att)

    return _enforce_size_limit(parsed, settings.max_attachment_bytes)


def _parse_file_item(item) -> ParsedAttachment | None:
    if not isinstance(item, (list, tuple)) or len(item) < 2:
        return None
    name = _safe_name(str(item[0]) if item[0] else "file")
    data = item[1]
    if not isinstance(data, (bytes, bytearray)):
        return None
    return ParsedAttachment(kind="file", name=name, data=bytes(data))


def _parse_image_item(value) -> ParsedAttachment | None:
    if not isinstance(value, (list, tuple)) or len(value) < 2:
        return None
    fmt = _field_text(value[0]) or "webp"
    data = value[1]
    if not isinstance(data, (bytes, bytearray)):
        return None
    name = f"image.{fmt.lstrip('.')}"
    return ParsedAttachment(kind="image", name=name, data=bytes(data), format=fmt)


def _parse_audio_item(value) -> ParsedAttachment | None:
    if not isinstance(value, (list, tuple)) or len(value) < 2:
        return None
    mode = value[0]
    data = value[1]
    if not isinstance(data, (bytes, bytearray)):
        return None
    return ParsedAttachment(
        kind="audio",
        name="audio.bin",
        data=bytes(data),
        format=str(mode),
    )


def _field_text(value) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _safe_name(name: str) -> str:
    base = os.path.basename(name.strip()) or "file"
    cleaned = _UNSAFE_NAME.sub("_", base)
    return cleaned[:120] or "file"


def _enforce_size_limit(
    items: list[ParsedAttachment],
    max_bytes: int,
) -> list[ParsedAttachment]:
    out: list[ParsedAttachment] = []
    for item in items:
        if len(item.data) > max_bytes:
            continue
        out.append(item)
    return out


def save_for_issue(
    settings: Settings,
    issue_id: int,
    items: list[ParsedAttachment],
    *,
    start_index: int = 0,
) -> list[IssueAttachment]:
    if not items:
        return []

    base = Path(settings.storage_path) / "attachments" / str(issue_id)
    base.mkdir(parents=True, exist_ok=True)
    stored: list[IssueAttachment] = []

    for offset, item in enumerate(items):
        index = start_index + offset
        filename = f"{index:02d}_{item.name}"
        path = base / filename
        path.write_bytes(item.data)
        stored.append(
            IssueAttachment(
                kind=item.kind,
                name=item.name,
                path=str(path.relative_to(settings.storage_path)),
                format=item.format,
                size=len(item.data),
            ),
        )
    return stored


def load_bytes(meta: IssueAttachment, settings: Settings) -> bytes | None:
    path = Path(settings.storage_path) / meta.path
    if not path.is_file():
        return None
    return path.read_bytes()


def to_lxmfy_attachment(meta: IssueAttachment, settings: Settings) -> Attachment | None:
    data = load_bytes(meta, settings)
    if data is None:
        return None
    if meta.kind == "image":
        return Attachment(
            type=AttachmentType.IMAGE,
            name=meta.name,
            data=data,
            format=meta.format or "webp",
        )
    if meta.kind == "audio":
        return Attachment(
            type=AttachmentType.AUDIO,
            name=meta.name,
            data=data,
            format=meta.format or "0",
        )
    return Attachment(
        type=AttachmentType.FILE,
        name=meta.name,
        data=data,
    )
