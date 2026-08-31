from datetime import UTC, datetime

from meshchatx_issues_bot.config import Settings
from meshchatx_issues_bot.models import Issue


def issue_preview(issue: Issue, max_len: int = 50) -> str:
    line = issue.body.replace("\n", " ").strip()
    if not line:
        return "(empty)"
    if len(line) <= max_len:
        return line
    return line[: max_len - 3] + "..."


def format_issue(issue: Issue, *, include_reporter: bool = False) -> str:
    created = datetime.fromtimestamp(issue.created_at, tz=UTC).strftime(
        "%Y-%m-%d %H:%M UTC",
    )
    lines = [
        f"#{issue.id} [{issue.status}]",
        f"Created: {created}",
    ]
    if include_reporter:
        lines.append(f"Reporter: {issue.reporter}")
    if issue.status == "closed" and issue.close_message:
        closed = ""
        if issue.closed_at is not None:
            closed = datetime.fromtimestamp(issue.closed_at, tz=UTC).strftime(
                "%Y-%m-%d %H:%M UTC",
            )
        if closed:
            lines.append(f"Closed: {closed}")
        if issue.closed_by:
            lines.append(f"Closed by: {issue.closed_by}")
        lines.append(f"Resolution: {issue.close_message}")
    if issue.attachments:
        lines.append(f"Attachments: {len(issue.attachments)}")
        for att in issue.attachments:
            lines.append(f"  - {att.name} ({att.kind}, {att.size} bytes)")
    lines.extend(["", issue.body])
    return "\n".join(lines)


def format_issue_list(
    issues: list[Issue],
    settings: Settings,
    *,
    admin_view: bool,
) -> str:
    if not issues:
        return "No issues found."
    lines = ["Issues:", ""]
    for issue in issues:
        preview = issue_preview(issue)
        if admin_view:
            lines.append(
                f"#{issue.id} [{issue.status}] {preview} ({issue.reporter})",
            )
        else:
            lines.append(f"#{issue.id} [{issue.status}] {preview}")
    lines.append("")
    lines.append(f"Use {settings.cmd(settings.cmd_issue)} <id> for details.")
    return "\n".join(lines)


def format_update_confirmation(
    issue: Issue,
    *,
    added_text: bool,
    added_attachments: int,
    admins_notified: int,
    settings: Settings,
    notify_failures: list[str] | None = None,
) -> str:
    parts: list[str] = [f"Issue #{issue.id} updated."]
    if added_text:
        parts.append("Text appended.")
    if added_attachments:
        parts.append(f"Attachments added: {added_attachments}.")
    if admins_notified:
        parts.append(f"Admins notified: {admins_notified}.")
    elif notify_failures:
        parts.append("Admin alert could not be delivered (no path to admin yet).")
    parts.append(f"View with {settings.cmd(settings.cmd_issue)} {issue.id}")
    return "\n".join(parts)


def format_report_confirmation(
    issue: Issue,
    admins_notified: int,
    attachments_forwarded: int,
    settings: Settings,
    *,
    notify_failures: list[str] | None = None,
    admin_copy: str | None = None,
) -> str:
    lines = [
        f"Issue #{issue.id} recorded.",
        f"Your address: {issue.reporter}",
    ]
    if admins_notified:
        lines.append(f"Admins notified: {admins_notified}")
    elif notify_failures:
        lines.append("Admin alert could not be delivered (no path to admin yet).")
    if issue.attachments:
        lines.append(
            f"Attachments saved: {len(issue.attachments)}"
            f" ({attachments_forwarded} forwarded to admins)",
        )
    lines.append(f"View with {settings.cmd(settings.cmd_issue)} {issue.id}")
    if admin_copy:
        lines.extend(["", admin_copy])
    return "\n".join(lines)
