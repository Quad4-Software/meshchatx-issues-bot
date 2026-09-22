import re

from lxmfy import unpack_commands

from meshchatx_issues_bot.attachments import (
    fit_byte_budget,
    has_attachments,
    message_fields,
    parse_incoming,
    save_for_issue,
)
from meshchatx_issues_bot.context import AppContext
from meshchatx_issues_bot.formatting import (
    format_issue,
    format_update_confirmation,
)
from meshchatx_issues_bot.lxmf_hash import normalize_lxmf_hash
from meshchatx_issues_bot.models import Issue
from meshchatx_issues_bot.notify import notify_admins_issue_updated
from meshchatx_issues_bot.ratelimit import RateLimiter

_ISSUE_REF = re.compile(r"^#(\d+)(?:\s+(.*))?$", re.S)


def split_issue_ref(content: str) -> tuple[int | None, str]:
    text = content.strip()
    if not text:
        return None, ""
    match = _ISSUE_REF.match(text)
    if match:
        return int(match.group(1)), (match.group(2) or "").strip()
    if text.isdigit():
        return int(text), ""
    return None, text


def message_is_actionable(bot, prefix: str | None, message, content: str) -> bool:
    fields = message_fields(message)
    if unpack_commands(fields) or has_attachments(message):
        return True
    if not content:
        return False
    if prefix is not None:
        if not content.startswith(prefix):
            return False
        body = content[len(prefix) :]
        cmd = body.split()[0] if body.split() else ""
        return cmd in bot.commands
    first = content.split()[0] if content.split() else ""
    return first in bot.commands


def resolve_target(
    issues,
    sender: str,
    issue_id: int | None,
) -> tuple[Issue | None, str | None]:
    if issue_id is not None:
        issue = issues.get(issue_id)
        if issue is None:
            return None, f"Issue #{issue_id} not found."
        if issue.reporter != sender:
            return None, "You can only attach files to your own issues."
        if issue.status != "open":
            return None, f"Issue #{issue_id} is closed."
        return issue, None

    active_id = issues.active_issue(sender)
    if active_id is not None:
        issue = issues.get(active_id)
        if issue is not None and issue.status == "open" and issue.reporter == sender:
            return issue, None

    open_issues = issues.list_issues(reporter=sender, status="open", limit=1)
    if open_issues:
        return open_issues[0], None
    return None, "no_issue"


def register_inbox(app: AppContext) -> None:
    bot = app.bot
    settings = app.settings
    prefix = settings.command_prefix
    limiter = RateLimiter(
        bot.storage,
        "inbox",
        limit=settings.inbox_rate_limit,
        window=settings.inbox_rate_window,
    )
    notice_limiter = RateLimiter(
        bot.storage, "inbox_notice", limit=1, window=settings.inbox_rate_window
    )

    def send(sender: str, text: str) -> None:
        kwargs = {}
        if app.icon_field is not None:
            kwargs["lxmf_fields"] = app.icon_field
        bot.send(sender, text, **kwargs)

    def usage_hint() -> str:
        return (
            f"{settings.cmd(settings.cmd_report)} <description> - file an issue\n"
            "Send files, images or a note to add them to your latest open "
            "issue. Start with #<id> to pick one, or send #<id> alone to "
            "view it.\n"
            f"{settings.cmd('help')} - all commands"
        )

    @bot.on_message()
    def inbox_handler(sender, message):
        h = normalize_lxmf_hash(sender)
        if h is None:
            return False

        content = ""
        raw_content = getattr(message, "content", None)
        if isinstance(raw_content, (bytes, bytearray)):
            content = bytes(raw_content).decode("utf-8", errors="replace").strip()

        fields = message_fields(message)
        if unpack_commands(fields):
            return False

        if content:
            if prefix is not None and content.startswith(prefix):
                body = content[len(prefix) :]
                cmd = body.split()[0] if body.split() else ""
                if cmd in bot.commands:
                    return False
            elif prefix is None:
                first = content.split()[0] if content.split() else ""
                if first in bot.commands:
                    return False

        if app.blocks.is_blocked(h):
            if notice_limiter.allow(h):
                send(h, "You are blocked from using this bot.")
            return True

        if content and prefix is not None and content.startswith(prefix):
            if notice_limiter.allow(h):
                send(h, f"Unknown command. Try {settings.cmd('help')}.")
            return True

        attachments_present = has_attachments(message)
        if not attachments_present and not content:
            return False

        if attachments_present and not settings.forward_attachments:
            if notice_limiter.allow(h):
                send(h, "This bot does not accept attachments.")
            return True

        if not limiter.allow(h):
            if notice_limiter.allow(h):
                send(h, "Too many messages. Try again later.")
            return True

        issue_id, note = split_issue_ref(content)
        issue, err = resolve_target(app.issues, h, issue_id)
        if issue is None:
            if err == "no_issue":
                send(h, usage_hint())
            else:
                send(h, err)
            return True

        if not attachments_present:
            if issue_id is not None and not note:
                send(h, format_issue(issue))
                return True
            if len(issue.body) + len(note) + 64 > settings.max_issue_body:
                send(
                    h,
                    f"Issue would exceed max size ({settings.max_issue_body} chars).",
                )
                return True
            file_update(issue, h, note, None)
            return True

        slots_left = max(
            0,
            settings.max_attachments_per_issue - len(issue.attachments),
        )
        parsed = []
        if slots_left > 0:
            parsed = parse_incoming(message, settings, max_count=slots_left)
            used_bytes = sum(a.size for a in issue.attachments)
            budget = max(0, settings.max_issue_attachment_bytes - used_bytes)
            parsed = fit_byte_budget(parsed, budget)

        dropped = not parsed
        if dropped and not note:
            if slots_left <= 0:
                send(
                    h,
                    f"Issue #{issue.id} already has the maximum "
                    f"{settings.max_attachments_per_issue} attachments.",
                )
            else:
                send(
                    h,
                    "Attachment rejected: over the size limit "
                    f"({settings.max_attachment_bytes} bytes per file).",
                )
            return True

        if note and len(issue.body) + len(note) + 64 > settings.max_issue_body:
            note = ""

        if not parsed and not note:
            send(h, "Nothing to add: attachments were over the limits.")
            return True

        file_update(issue, h, note, parsed)
        return True

    def file_update(issue: Issue, sender: str, note: str, parsed: list | None) -> None:
        stored = []
        if parsed:
            stored = save_for_issue(
                settings,
                issue.id,
                parsed,
                start_index=len(issue.attachments),
            )
        updated, err = app.issues.append_to_issue(
            issue.id,
            sender,
            text=note or None,
            new_attachments=stored or None,
        )
        if err is not None or updated is None:
            send(sender, "Could not update that issue.")
            return
        app.issues.set_active(sender, updated.id)

        admins_notified, _forwarded, failures = notify_admins_issue_updated(
            bot,
            settings,
            updated,
            update_text=note or None,
            new_attachments=stored,
            icon_field=app.icon_field,
            pending=app.pending,
        )
        confirmation = format_update_confirmation(
            updated,
            added_text=bool(note),
            added_attachments=len(stored),
            admins_notified=admins_notified,
            settings=settings,
            notify_failures=failures,
        )
        if parsed is not None and not stored:
            confirmation += "\nAttachments skipped: over the limits."
        send(sender, confirmation)
