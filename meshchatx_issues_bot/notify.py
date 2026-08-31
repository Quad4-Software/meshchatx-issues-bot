from lxmfy.attachments import pack_attachment

from meshchatx_issues_bot.attachments import to_lxmfy_attachment
from meshchatx_issues_bot.config import Settings
from meshchatx_issues_bot.messaging import deliver_message, should_include_ticket
from meshchatx_issues_bot.models import Issue


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
        sent = deliver_message(
            bot,
            settings,
            admin_hash,
            text,
            title=f"Issue #{issue.id} update",
            include_ticket=should_include_ticket(admin_hash, settings),
        )
        if sent:
            admins_sent += 1
        else:
            failures.append(admin_hash)
            print(
                f"Could not send issue #{issue.id} update to {admin_hash} "
                "(destination unknown; try messaging the bot once from that client)",
            )

        if not settings.forward_attachments:
            continue

        for meta in new_attachments:
            attachment = to_lxmfy_attachment(meta, settings)
            if attachment is None:
                continue
            body = f"Issue #{issue.id} update: {meta.name}"
            if deliver_message(
                bot,
                settings,
                admin_hash,
                body,
                title=f"Issue #{issue.id} file",
                lxmf_fields=pack_attachment(attachment),
                include_ticket=should_include_ticket(admin_hash, settings),
            ):
                attachments_sent += 1

    return admins_sent, attachments_sent, failures


def notify_admins(
    bot,
    settings: Settings,
    issue: Issue,
    *,
    icon_field=None,
) -> tuple[int, int, list[str]]:
    text = format_admin_message(issue)
    admins_sent = 0
    attachments_sent = 0
    failures: list[str] = []

    for admin_hash in settings.notify_hashes:
        sent = deliver_message(
            bot,
            settings,
            admin_hash,
            text,
            title=f"Issue #{issue.id}",
            include_ticket=should_include_ticket(admin_hash, settings),
        )
        if sent:
            admins_sent += 1
        else:
            failures.append(admin_hash)
            print(
                f"Could not send issue #{issue.id} alert to {admin_hash} "
                "(destination unknown; try messaging the bot once from that client)",
            )

        if not settings.forward_attachments or not issue.attachments:
            continue

        for meta in issue.attachments:
            attachment = to_lxmfy_attachment(meta, settings)
            if attachment is None:
                print(f"Issue #{issue.id}: missing attachment file {meta.path}")
                continue
            body = f"Issue #{issue.id} attachment: {meta.name}"
            if deliver_message(
                bot,
                settings,
                admin_hash,
                body,
                title=f"Issue #{issue.id} file",
                lxmf_fields=pack_attachment(attachment),
                include_ticket=should_include_ticket(admin_hash, settings),
            ):
                attachments_sent += 1
            else:
                print(f"Could not forward {meta.name} to {admin_hash}")

    return admins_sent, attachments_sent, failures


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
) -> bool:
    if issue.reporter == closer_hash:
        return True
    text = format_close_notice(
        issue,
        closer_label=closer_label,
        closer_address=closer_hash,
    )
    return deliver_message(
        bot,
        settings,
        issue.reporter,
        text,
        title=f"Issue #{issue.id} closed",
        include_ticket=False,
    )
