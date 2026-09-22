from lxmfy.attachments import pack_attachment

from meshchatx_issues_bot.attachments import to_lxmfy_attachment
from meshchatx_issues_bot.config import Settings
from meshchatx_issues_bot.messaging import deliver_message, should_include_ticket
from meshchatx_issues_bot.models import Issue, IssueAttachment


def _send_or_hold(
    bot,
    settings: Settings,
    pending,
    dest: str,
    text: str,
    *,
    title: str,
    attachment: IssueAttachment | None = None,
) -> bool:
    fields = None
    if attachment is not None:
        packed = to_lxmfy_attachment(attachment, settings)
        if packed is None:
            return False
        fields = pack_attachment(packed)

    def fail():
        pending.add(
            dest,
            title,
            text,
            attachments=[attachment.to_dict()] if attachment else None,
        )

    return deliver_message(
        bot,
        settings,
        dest,
        text,
        title=title,
        lxmf_fields=fields,
        include_ticket=should_include_ticket(dest, settings),
        on_failure=fail if pending is not None else None,
    )


def format_admin_message(issue: Issue) -> str:
    lines = [
        f"New issue #{issue.id}",
        f"From: {issue.reporter}",
        "",
        issue.body,
    ]
    if issue.attachments:
        names = ", ".join(a.name for a in issue.attachments)
        lines.append("")
        lines.append(f"Attachments ({len(issue.attachments)}): {names}")
    return "\n".join(lines)


def format_admin_update(
    issue: Issue,
    *,
    update_text: str | None,
    new_attachment_names: list[str],
) -> str:
    lines = [
        f"Issue #{issue.id} updated",
        f"From: {issue.reporter}",
        "",
    ]
    if update_text:
        lines.append(update_text)
    if new_attachment_names:
        lines.append("")
        lines.append(f"New attachments: {', '.join(new_attachment_names)}")
    elif not update_text:
        lines.append("(attachments added)")
    return "\n".join(lines)


def notify_admins_issue_updated(
    bot,
    settings: Settings,
    issue: Issue,
    *,
    update_text: str | None,
    new_attachments: list,
    icon_field=None,
    pending=None,
) -> tuple[int, int, list[str]]:
    names = [a.name for a in new_attachments]
    text = format_admin_update(
        issue,
        update_text=update_text,
        new_attachment_names=names,
    )
    admins_sent = 0
    attachments_sent = 0
    failures: list[str] = []

    for admin_hash in settings.notify_hashes:
        sent = _send_or_hold(
            bot,
            settings,
            pending,
            admin_hash,
            text,
            title=f"Issue #{issue.id} update",
        )
        if sent:
            admins_sent += 1
        else:
            failures.append(admin_hash)
            print(
                f"Could not send issue #{issue.id} update to {admin_hash} "
                "(queued for retry once reachable)",
            )

        if not settings.forward_attachments:
            continue

        for meta in new_attachments:
            body = f"Issue #{issue.id} update: {meta.name}"
            if _send_or_hold(
                bot,
                settings,
                pending,
                admin_hash,
                body,
                title=f"Issue #{issue.id} file",
                attachment=meta,
            ):
                attachments_sent += 1

    return admins_sent, attachments_sent, failures


def notify_admins_text(
    bot,
    settings: Settings,
    text: str,
    *,
    title: str,
    pending=None,
) -> int:
    sent = 0
    for admin_hash in settings.notify_hashes:
        if _send_or_hold(
            bot,
            settings,
            pending,
            admin_hash,
            text,
            title=title,
        ):
            sent += 1
    return sent


def notify_admins(
    bot,
    settings: Settings,
    issue: Issue,
    *,
    icon_field=None,
    pending=None,
) -> tuple[int, int, list[str]]:
    text = format_admin_message(issue)
    admins_sent = 0
    attachments_sent = 0
    failures: list[str] = []

    for admin_hash in settings.notify_hashes:
        sent = _send_or_hold(
            bot,
            settings,
            pending,
            admin_hash,
            text,
            title=f"Issue #{issue.id}",
        )
        if sent:
            admins_sent += 1
        else:
            failures.append(admin_hash)
            print(
                f"Could not send issue #{issue.id} alert to {admin_hash} "
                "(queued for retry once reachable)",
            )

        if not settings.forward_attachments or not issue.attachments:
            continue

        for meta in issue.attachments:
            body = f"Issue #{issue.id} attachment: {meta.name}"
            if _send_or_hold(
                bot,
                settings,
                pending,
                admin_hash,
                body,
                title=f"Issue #{issue.id} file",
                attachment=meta,
            ):
                attachments_sent += 1
            else:
                print(f"Could not forward {meta.name} to {admin_hash}")

    return admins_sent, attachments_sent, failures


def notify_reporter(
    bot,
    settings: Settings,
    issue: Issue,
    text: str,
    *,
    title: str,
    pending=None,
) -> bool:
    def fail():
        if pending is not None:
            pending.add(issue.reporter, title, text)

    return deliver_message(
        bot,
        settings,
        issue.reporter,
        text,
        title=title,
        include_ticket=False,
        on_failure=fail if pending is not None else None,
    )


def format_close_notice(
    issue: Issue,
    *,
    closer_label: str,
    closer_address: str,
) -> str:
    message = issue.close_message or "closed"
    return (
        f"Your issue #{issue.id} has been closed by {closer_label} - {closer_address}\n\n"
        f"{message}"
    )


def notify_issue_closed(
    bot,
    settings: Settings,
    issue: Issue,
    *,
    closer_hash: str,
    closer_label: str,
    pending=None,
) -> bool:
    if issue.reporter == closer_hash:
        return True
    text = format_close_notice(
        issue,
        closer_label=closer_label,
        closer_address=closer_hash,
    )
    return notify_reporter(
        bot,
        settings,
        issue,
        text,
        title=f"Issue #{issue.id} closed",
        pending=pending,
    )
