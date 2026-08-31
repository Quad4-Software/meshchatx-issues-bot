from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class IssueAttachment:
    kind: str
    name: str
    path: str
    format: str | None = None
    size: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "IssueAttachment":
        return cls(
            kind=str(data["kind"]),
            name=str(data["name"]),
            path=str(data["path"]),
            format=data.get("format"),
            size=int(data.get("size", 0)),
        )


@dataclass
class Issue:
    id: int
    reporter: str
    title: str
    body: str
    created_at: float
    status: str = "open"
    attachments: list[IssueAttachment] = field(default_factory=list)
    closed_at: float | None = None
    closed_by: str | None = None
    close_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["attachments"] = [a.to_dict() for a in self.attachments]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Issue":
        raw_attachments = data.get("attachments") or []
        attachments = [
            IssueAttachment.from_dict(item)
            for item in raw_attachments
            if isinstance(item, dict)
        ]
        closed_at = data.get("closed_at")
        return cls(
            id=int(data["id"]),
            reporter=str(data["reporter"]),
            title=str(data["title"]),
            body=str(data["body"]),
            created_at=float(data["created_at"]),
            status=str(data.get("status", "open")),
            attachments=attachments,
            closed_at=float(closed_at) if closed_at is not None else None,
            closed_by=data.get("closed_by"),
            close_message=data.get("close_message"),
        )
