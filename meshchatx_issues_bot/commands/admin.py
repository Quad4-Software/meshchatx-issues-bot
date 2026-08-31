from meshchatx_issues_bot.commands.helpers import reply, sender_hash
from meshchatx_issues_bot.context import AppContext
from meshchatx_issues_bot.formatting import format_issue_list, issue_preview
from meshchatx_issues_bot.identity import display_name_for_address, is_verified_admin
from meshchatx_issues_bot.lxmf_hash import normalize_lxmf_hash
from meshchatx_issues_bot.notify import notify_issue_closed


def _require_admin(ctx, app: AppContext) -> bool:
    if is_verified_admin(ctx, app.settings):
        return True
    reply(ctx, app, "Admin access denied.")
    return False


def _parse_close_args(args: list[str]) -> tuple[int, str] | None:
    if not args:
        return None
    try:
        issue_id = int(args[0])
    except ValueError:
        return None
    if len(args) == 1:
        return issue_id, "closed"
    message = " ".join(args[1:]).strip()
    return issue_id, message or "closed"


def register_admin_commands(app: AppContext) -> None:
    bot = app.bot
    settings = app.settings

    @bot.command(
        name=settings.cmd_issues,
        description="List all issues",
        threaded=True,
    )
    def issues_command(ctx):
        if not _require_admin(ctx, app):
            return
        status = None
        if ctx.args and ctx.args[0] in ("open", "closed", "all"):
            arg = ctx.args[0]
            status = None if arg == "all" else arg
        items = app.issues.list_issues(status=status, limit=settings.list_issues_limit)
        reply(ctx, app, format_issue_list(items, settings, admin_view=True))

    @bot.command(
        name=settings.cmd_close,
        description="Close an issue and notify the reporter",
        threaded=True,
    )
    def close_command(ctx):
        if not _require_admin(ctx, app):
            return
        closer = sender_hash(ctx)
        if not closer:
            reply(ctx, app, "Could not determine your address.")
            return

        parsed = _parse_close_args(ctx.args)
        if parsed is None:
            reply(
                ctx,
                app,
                f"Usage: {settings.cmd(settings.cmd_close)} <id> [message]\n"
                f"Example: {settings.cmd(settings.cmd_close)} 3 Fixed in the next release",
            )
            return

        issue_id, close_message = parsed
        issue = app.issues.get(issue_id)
        if issue is None:
            reply(ctx, app, f"Issue #{issue_id} not found.")
            return
        if issue.status == "closed":
            reply(
                ctx,
                app,
                f"Issue #{issue_id} is already closed.\n"
                f"Resolution: {issue.close_message or 'closed'}",
            )
            return

        issue = app.issues.close(
            issue_id,
            closed_by=closer,
            close_message=close_message,
        )
        closer_label = display_name_for_address(closer, settings)
        notified = notify_issue_closed(
            bot,
            settings,
            issue,
            closer_hash=closer,
            closer_label=closer_label,
        )

        preview = issue_preview(issue)
        lines = [
            f"Closed issue #{issue.id}: {preview}",
            f"Resolution: {issue.close_message}",
        ]
        if issue.reporter != closer:
            if notified:
                lines.append(f"Reporter notified ({issue.reporter}).")
            else:
                lines.append(
                    f"Could not notify reporter ({issue.reporter}); no path yet.",
                )
        reply(ctx, app, "\n".join(lines))

    @bot.command(
        name=settings.cmd_block,
        description="Block an address from using the bot",
    )
    def block_command(ctx):
        if not _require_admin(ctx, app):
            return
        if not ctx.args:
            reply(ctx, app, f"Usage: {settings.cmd(settings.cmd_block)} <address>")
            return
        target = normalize_lxmf_hash(ctx.args[0])
        if not target:
            reply(ctx, app, "Invalid address.")
            return
        if target in settings.admin_hashes:
            reply(ctx, app, "Cannot block a configured admin.")
            return
        if app.blocks.block(target):
            reply(ctx, app, f"Blocked {target}")
        else:
            reply(ctx, app, f"{target} is already blocked.")

    @bot.command(
        name=settings.cmd_unblock,
        description="Unblock an address",
    )
    def unblock_command(ctx):
        if not _require_admin(ctx, app):
            return
        if not ctx.args:
            reply(ctx, app, f"Usage: {settings.cmd(settings.cmd_unblock)} <address>")
            return
        target = normalize_lxmf_hash(ctx.args[0])
        if not target:
            reply(ctx, app, "Invalid address.")
            return
        if app.blocks.unblock(target):
            reply(ctx, app, f"Unblocked {target}")
        else:
            reply(ctx, app, f"{target} is not blocked.")

    @bot.command(
        name=settings.cmd_blocked,
        description="List blocked addresses",
    )
    def blocked_command(ctx):
        if not _require_admin(ctx, app):
            return
        blocked = app.blocks.list_blocked()
        if not blocked:
            reply(ctx, app, "No blocked users.")
            return
        lines = ["Blocked addresses:", ""]
        lines.extend(blocked)
        reply(ctx, app, "\n".join(lines))

    @bot.command(
        name="whoami",
        description="Show your address",
    )
    def whoami_command(ctx):
        h = sender_hash(ctx)
        if not h:
            reply(ctx, app, "Could not determine your address.")
            return
        reply(ctx, app, f"Your address: {h}")
