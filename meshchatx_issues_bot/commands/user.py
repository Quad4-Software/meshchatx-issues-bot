from meshchatx_issues_bot.attachments import parse_incoming, save_for_issue
from meshchatx_issues_bot.commands.helpers import (
    parse_report_body,
    parse_update_args,
    reply,
    sender_hash,
    title_from_body,
)
from meshchatx_issues_bot.context import AppContext
from meshchatx_issues_bot.formatting import (
    format_issue,
    format_issue_list,
    format_report_confirmation,
    format_update_confirmation,
)
from meshchatx_issues_bot.identity import is_verified_admin
from meshchatx_issues_bot.notify import (
    format_admin_message,
    notify_admins,
    notify_admins_issue_updated,
)


def register_user_commands(app: AppContext) -> None:
    bot = app.bot
    settings = app.settings

    @bot.command(
        name=settings.cmd_report,
        description="Report an issue",
        threaded=True,
    )
    def report_command(ctx):
        reporter = sender_hash(ctx)
        if not reporter:
            reply(ctx, app, "Could not determine your address.")
            return
        if app.blocks.is_blocked(reporter):
            reply(ctx, app, "You are blocked from reporting issues.")
            return

        lxmf_message = getattr(ctx, "lxmf", None)
        incoming = (
            parse_incoming(lxmf_message, settings)
            if settings.forward_attachments
            else []
        )
        body = parse_report_body(ctx.args)

        if not body and not incoming:
            reply(
                ctx,
                app,
                f"Usage: {settings.cmd(settings.cmd_report)} <description>\n"
                "Attach files or images to the same message.",
            )
            return

        if not body:
            body = "See attached file(s)."

        if len(body) > settings.max_issue_body:
            reply(
                ctx,
                app,
                f"Description too long (max {settings.max_issue_body} chars).",
            )
            return

        title = title_from_body(body)
        issue = app.issues.create(reporter, title, body)
        if incoming:
            issue.attachments = save_for_issue(
                settings,
                issue.id,
                incoming,
                start_index=0,
            )
            app.issues.save(issue)

        admins_notified, attachments_forwarded, failures = notify_admins(
            bot,
            settings,
            issue,
            icon_field=app.icon_field,
        )

        admin_copy = None
        if reporter in settings.notify_hashes and reporter in failures:
            admin_copy = format_admin_message(issue)

        reply(
            ctx,
            app,
            format_report_confirmation(
                issue,
                admins_notified,
                attachments_forwarded,
                settings,
                notify_failures=failures,
                admin_copy=admin_copy,
            ),
        )

    @bot.command(
        name=settings.cmd_update,
        description="Add text or attachments to your open issue",
        threaded=True,
    )
    def update_command(ctx):
        reporter = sender_hash(ctx)
        if not reporter:
            reply(ctx, app, "Could not determine your address.")
            return
        if app.blocks.is_blocked(reporter):
            reply(ctx, app, "You are blocked from reporting issues.")
            return

        parsed = parse_update_args(ctx.args)
        if parsed is None:
            reply(
                ctx,
                app,
                f"Usage: {settings.cmd(settings.cmd_update)} <id> [more text]\n"
                "Attach files or images to the same message.",
            )
            return

        issue_id, add_text = parsed
        lxmf_message = getattr(ctx, "lxmf", None)
        slots_left = settings.max_attachments_per_issue
        issue_existing = app.issues.get(issue_id)
        if issue_existing is not None:
            slots_left = max(
                0,
                settings.max_attachments_per_issue - len(issue_existing.attachments),
            )

        incoming = (
            parse_incoming(
                lxmf_message,
                settings,
                max_count=slots_left,
            )
            if settings.forward_attachments
            else []
        )

        if not add_text and not incoming:
            reply(
                ctx,
                app,
                f"Usage: {settings.cmd(settings.cmd_update)} <id> [more text]\n"
                "Attach files or images to the same message.",
            )
            return

        if issue_existing is None:
            reply(ctx, app, f"Issue #{issue_id} not found.")
            return
        if issue_existing.reporter != reporter:
            reply(ctx, app, "You can only update your own issues.")
            return
        if issue_existing.status != "open":
            reply(ctx, app, f"Issue #{issue_id} is closed and cannot be updated.")
            return

        update_block = None
        if add_text:
            if len(issue_existing.body) + len(add_text) + 64 > settings.max_issue_body:
                reply(
                    ctx,
                    app,
                    f"Issue would exceed max size ({settings.max_issue_body} chars).",
                )
                return
            update_block = add_text

        new_attachments = []
        if incoming:
            if not slots_left:
                reply(
                    ctx,
                    app,
                    f"Issue #{issue_id} already has the maximum number of attachments.",
                )
                return
            new_attachments = save_for_issue(
                settings,
                issue_id,
                incoming,
                start_index=len(issue_existing.attachments),
            )

        issue, err = app.issues.append_to_issue(
            issue_id,
            reporter,
            text=update_block,
            new_attachments=new_attachments,
        )
        if err == "not_found":
            reply(ctx, app, f"Issue #{issue_id} not found.")
            return
        if err == "forbidden":
            reply(ctx, app, "You can only update your own issues.")
            return
        if err == "closed":
            reply(ctx, app, f"Issue #{issue_id} is closed and cannot be updated.")
            return

        admins_notified, _attachments_forwarded, failures = notify_admins_issue_updated(
            bot,
            settings,
            issue,
            update_text=update_block,
            new_attachments=new_attachments,
            icon_field=app.icon_field,
        )

        reply(
            ctx,
            app,
            format_update_confirmation(
                issue,
                added_text=bool(update_block),
                added_attachments=len(new_attachments),
                admins_notified=admins_notified,
                settings=settings,
                notify_failures=failures,
            ),
        )

    @bot.command(
        name=settings.cmd_myissues,
        description="List your open issues",
        threaded=True,
    )
    def myissues_command(ctx):
        reporter = sender_hash(ctx)
        if not reporter:
            reply(ctx, app, "Could not determine your address.")
            return
        items = app.issues.list_issues(
            reporter=reporter,
            status=None,
            limit=settings.list_issues_limit,
        )
        reply(ctx, app, format_issue_list(items, settings, admin_view=False))

    @bot.command(
        name=settings.cmd_issue,
        description="Show an issue you filed",
        threaded=True,
    )
    def issue_command(ctx):
        reporter = sender_hash(ctx)
        if not reporter:
            reply(ctx, app, "Could not determine your address.")
            return
        if not ctx.args:
            reply(ctx, app, f"Usage: {settings.cmd(settings.cmd_issue)} <id>")
            return
        try:
            issue_id = int(ctx.args[0])
        except ValueError:
            reply(ctx, app, "Issue id must be a number.")
            return

        issue = app.issues.get(issue_id)
        if issue is None:
            reply(ctx, app, f"Issue #{issue_id} not found.")
            return
        if issue.reporter != reporter and not is_verified_admin(ctx, settings):
            reply(ctx, app, "You can only view your own issues.")
            return
        reply(
            ctx,
            app,
            format_issue(
                issue,
                include_reporter=is_verified_admin(ctx, settings),
            ),
        )
