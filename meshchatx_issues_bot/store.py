import time

from meshchatx_issues_bot.lxmf_hash import normalize_lxmf_hash
from meshchatx_issues_bot.models import Issue, IssueAttachment

_COUNTER_KEY = "issue_counter"
_ISSUE_PREFIX = "issue:"
_BLOCKED_KEY = "blocked_hashes"


class IssueStore:
    def __init__(self, storage):
        self._storage = storage

    def create(
        self,
        reporter: str,
        title: str,
        body: str,
        attachments: list[IssueAttachment] | None = None,
    ) -> Issue:
        issue_id = int(self._storage.get(_COUNTER_KEY, 0)) + 1
        issue = Issue(
            id=issue_id,
            reporter=reporter,
            title=title,
            body=body,
            created_at=time.time(),
            attachments=list(attachments or []),
        )
        self._storage.set(_COUNTER_KEY, issue_id)
        self._storage.set(f"{_ISSUE_PREFIX}{issue_id}", issue.to_dict())
        return issue

    def save(self, issue: Issue) -> None:
        self._storage.set(f"{_ISSUE_PREFIX}{issue.id}", issue.to_dict())

    def get(self, issue_id: int) -> Issue | None:
        raw = self._storage.get(f"{_ISSUE_PREFIX}{issue_id}")
        if not raw:
            return None
        return Issue.from_dict(raw)

    def list_issues(
        self,
        *,
        reporter: str | None = None,
        status: str | None = "open",
        limit: int = 20,
    ) -> list[Issue]:
        keys = self._storage.scan(_ISSUE_PREFIX)
        issues: list[Issue] = []
        for key in keys:
            raw = self._storage.get(key)
            if not raw:
                continue
            issue = Issue.from_dict(raw)
            if status is not None and issue.status != status:
                continue
            if reporter is not None and issue.reporter != reporter:
                continue
            issues.append(issue)
        issues.sort(key=lambda i: i.id, reverse=True)
        return issues[:limit]

    def close(
        self,
        issue_id: int,
        *,
        closed_by: str,
        close_message: str = "closed",
    ) -> Issue | None:
        issue = self.get(issue_id)
        if issue is None:
            return None
        if issue.status == "closed":
            return issue
        issue.status = "closed"
        issue.closed_at = time.time()
        issue.closed_by = closed_by
        issue.close_message = close_message.strip() or "closed"
        self._storage.set(f"{_ISSUE_PREFIX}{issue_id}", issue.to_dict())
        return issue

    def append_to_issue(
        self,
        issue_id: int,
        reporter: str,
        *,
        text: str | None = None,
        new_attachments: list[IssueAttachment] | None = None,
    ) -> tuple[Issue | None, str | None]:
        issue = self.get(issue_id)
        if issue is None:
            return None, "not_found"
        if issue.reporter != reporter:
            return None, "forbidden"
        if issue.status != "open":
            return None, "closed"

        if new_attachments:
            issue.attachments.extend(new_attachments)

        if text:
            stamp = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())
            block = f"--- Update {stamp} ---\n{text}"
            if issue.body.strip():
                issue.body = f"{issue.body.rstrip()}\n\n{block}"
            else:
                issue.body = block

        self.save(issue)
        return issue, None


class BlockStore:
    def __init__(self, storage):
        self._storage = storage

    def _load(self) -> set[str]:
        raw = self._storage.get(_BLOCKED_KEY, [])
        if not isinstance(raw, list):
            return set()
        out: set[str] = set()
        for item in raw:
            h = normalize_lxmf_hash(item)
            if h:
                out.add(h)
        return out

    def _save(self, blocked: set[str]) -> None:
        self._storage.set(_BLOCKED_KEY, sorted(blocked))

    def is_blocked(self, lxmf_hash: str) -> bool:
        h = normalize_lxmf_hash(lxmf_hash)
        if not h:
            return False
        return h in self._load()

    def block(self, lxmf_hash: str) -> bool:
        h = normalize_lxmf_hash(lxmf_hash)
        if not h:
            return False
        blocked = self._load()
        if h in blocked:
            return False
        blocked.add(h)
        self._save(blocked)
        return True

    def unblock(self, lxmf_hash: str) -> bool:
        h = normalize_lxmf_hash(lxmf_hash)
        if not h:
            return False
        blocked = self._load()
        if h not in blocked:
            return False
        blocked.remove(h)
        self._save(blocked)
        return True

    def list_blocked(self) -> list[str]:
        return sorted(self._load())
