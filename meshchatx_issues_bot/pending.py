import threading
import time
import uuid
from typing import Any

import RNS
from lxmfy.attachments import pack_attachment

from meshchatx_issues_bot.attachments import to_lxmfy_attachment
from meshchatx_issues_bot.lxmf_hash import normalize_lxmf_hash
from meshchatx_issues_bot.models import IssueAttachment
from meshchatx_issues_bot.store import KeyValueStorage

_PENDING_KEY = "pending_notifications"
MAX_ATTEMPTS = 48
MAX_AGE_SECONDS = 7 * 24 * 3600


class PendingStore:
    """Outbound notifications that could not be sent, retried later."""

    def __init__(self, storage: KeyValueStorage) -> None:
        self._storage = storage

    def _load(self) -> list[dict[str, Any]]:
        raw = self._storage.get(_PENDING_KEY, [])
        if not isinstance(raw, list):
            return []
        return [e for e in raw if isinstance(e, dict)]

    def _save(self, entries: list[dict[str, Any]]) -> None:
        self._storage.set(_PENDING_KEY, entries)

    def add(
        self,
        dest: str,
        title: str,
        text: str,
        attachments: list[dict] | None = None,
        attempts: int = 0,
    ) -> str | None:
        h = normalize_lxmf_hash(dest)
        if not h:
            return None
        entries = self._load()
        entry = {
            "id": uuid.uuid4().hex[:12],
            "dest": h,
            "title": title,
            "text": text,
            "attachments": list(attachments or []),
            "attempts": attempts,
            "queued_at": time.time(),
        }
        entries.append(entry)
        self._save(entries)
        return entry["id"]

    def remove(self, entry_id: str) -> None:
        self._save([e for e in self._load() if e.get("id") != entry_id])

    def bump_attempts(self, entry_id: str) -> None:
        entries = self._load()
        for e in entries:
            if e.get("id") == entry_id:
                e["attempts"] = int(e.get("attempts", 0)) + 1
        self._save(entries)

    def for_destination(self, dest: str) -> list[dict[str, Any]]:
        h = normalize_lxmf_hash(dest)
        if not h:
            return []
        return [e for e in self._load() if e.get("dest") == h]

    def all(self) -> list[dict[str, Any]]:
        return self._load()

    def count(self) -> int:
        return len(self._load())


def flush_pending(
    bot, settings, pending: PendingStore, dest: str | None = None
) -> tuple[int, int]:
    """Retry queued notifications. Returns (sent, dropped)."""
    from meshchatx_issues_bot.messaging import deliver_message, should_include_ticket

    entries = pending.for_destination(dest) if dest else pending.all()
    sent = 0
    dropped = 0
    now = time.time()

    for entry in entries:
        entry_id = entry.get("id")
        attempts = int(entry.get("attempts", 0))
        queued_at = float(entry.get("queued_at", now))
        if attempts >= MAX_ATTEMPTS or now - queued_at > MAX_AGE_SECONDS:
            pending.remove(entry_id)
            dropped += 1
            continue

        fields = None
        metas = entry.get("attachments") or []
        if metas:
            att = to_lxmfy_attachment(
                IssueAttachment.from_dict(metas[0]),
                settings,
            )
            if att is None:
                pending.remove(entry_id)
                dropped += 1
                continue
            fields = pack_attachment(att)

        def fail(entry_id=entry_id):
            pending.bump_attempts(entry_id)

        ok = deliver_message(
            bot,
            settings,
            entry["dest"],
            entry["text"],
            title=entry.get("title") or "Notification",
            lxmf_fields=fields,
            include_ticket=should_include_ticket(entry["dest"], settings),
            on_failure=fail,
        )
        if ok:
            pending.remove(entry_id)
            sent += 1
    return sent, dropped


def start_flush_thread(
    bot,
    settings,
    pending: PendingStore,
    interval: float = 600.0,
) -> threading.Thread:
    """Retry queued notifications on a daemon thread.

    Runs outside lxmfy's cron scheduler, which dies permanently if any
    task expression is malformed.
    """

    def loop():
        while True:
            time.sleep(interval)
            try:
                sent, dropped = flush_pending(bot, settings, pending)
                if sent or dropped:
                    RNS.log(
                        f"Flushed {sent} pending notification(s)"
                        + (f", dropped {dropped}" if dropped else ""),
                        RNS.LOG_INFO,
                    )
            except Exception as e:
                RNS.log(f"Pending notification flush failed: {e}", RNS.LOG_ERROR)

    thread = threading.Thread(target=loop, daemon=True, name="pending-flush")
    thread.start()
    return thread


class PendingAnnounceHandler:
    aspect_filter = "lxmf.delivery"

    def __init__(self, bot, settings, pending: PendingStore) -> None:
        self._bot = bot
        self._settings = settings
        self._pending = pending

    def received_announce(self, destination_hash, announced_identity, app_data):
        dest = (
            destination_hash.hex()
            if isinstance(destination_hash, (bytes, bytearray))
            else str(destination_hash)
        )
        if not self._pending.for_destination(dest):
            return
        sent, dropped = flush_pending(
            self._bot,
            self._settings,
            self._pending,
            dest=dest,
        )
        if sent or dropped:
            RNS.log(
                f"Flushed {sent} pending notification(s) to {dest}"
                + (f", dropped {dropped}" if dropped else ""),
                RNS.LOG_INFO,
            )
