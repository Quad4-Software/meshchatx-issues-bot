import time

from meshchatx_issues_bot.lxmf_hash import normalize_lxmf_hash
from meshchatx_issues_bot.store import KeyValueStorage


class RateLimiter:
    def __init__(
        self,
        storage: KeyValueStorage,
        prefix: str,
        *,
        limit: int,
        window: int,
    ) -> None:
        self._storage = storage
        self._prefix = prefix
        self._limit = max(1, limit)
        self._window = max(1, window)

    def _key(self, sender: str) -> str | None:
        h = normalize_lxmf_hash(sender)
        if not h:
            return None
        return f"{self._prefix}:{h}"

    def allow(self, sender: str, *, now: float | None = None) -> bool:
        key = self._key(sender)
        if key is None:
            return False
        now = time.time() if now is None else now
        raw = self._storage.get(key, [])
        stamps = (
            [t for t in raw if isinstance(t, (int, float))]
            if isinstance(raw, list)
            else []
        )
        stamps = [t for t in stamps if now - t < self._window]
        allowed = len(stamps) < self._limit
        if allowed:
            stamps.append(now)
        self._storage.set(key, stamps)
        return allowed

    def reset(self, sender: str) -> None:
        key = self._key(sender)
        if key is not None:
            self._storage.set(key, [])
