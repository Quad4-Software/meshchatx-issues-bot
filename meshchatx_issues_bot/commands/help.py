from meshchatx_issues_bot.commands.helpers import reply
from meshchatx_issues_bot.context import AppContext
from meshchatx_issues_bot.identity import is_verified_admin


def _user_commands(settings) -> list[tuple[str, str, str]]:
    return [
        (
            settings.cmd_report,
            "Report an issue",
            f"{settings.cmd(settings.cmd_report)} <description>",
        ),
        (
            settings.cmd_update,
            "Add text or attachments to your open issue",
            f"{settings.cmd(settings.cmd_update)} <id> [more text]",
        ),
        (
            settings.cmd_myissues,
            "List your issues",
            settings.cmd(settings.cmd_myissues),
        ),
        (
            settings.cmd_issue,
            "View an issue by id",
            f"{settings.cmd(settings.cmd_issue)} <id>",
        ),
        ("whoami", "Show your address", "whoami"),
        ("help", "Show this list", f"{settings.cmd('help')} [command]"),
    ]


def _admin_commands(settings) -> list[tuple[str, str, str]]:
    return [
        (
            settings.cmd_issues,
            "List issues (open, closed, or all)",
            f"{settings.cmd(settings.cmd_issues)} [open|closed|all]",
        ),
        (
            settings.cmd_close,
            "Close an issue and notify the reporter",
            f"{settings.cmd(settings.cmd_close)} <id> [message]",
        ),
        (
            settings.cmd_block,
            "Block an address",
            f"{settings.cmd(settings.cmd_block)} <address>",
        ),
        (
            settings.cmd_unblock,
            "Unblock an address",
            f"{settings.cmd(settings.cmd_unblock)} <address>",
        ),
        (
            settings.cmd_blocked,
            "List blocked addresses",
            settings.cmd(settings.cmd_blocked),
        ),
    ]


def _find_command(name: str, settings, *, include_admin: bool):
    for cmd_name, desc, usage in _user_commands(settings):
        if cmd_name == name:
            return desc, usage
    if include_admin:
        for cmd_name, desc, usage in _admin_commands(settings):
            if cmd_name == name:
                return desc, usage
    return None


def register_help(app: AppContext) -> None:
    bot = app.bot
    settings = app.settings

    @bot.command(name="help", description="Show available commands")
    def help_command(ctx):
        admin = is_verified_admin(ctx, app.settings)

        if ctx.args:
            name = ctx.args[0]
            prefix = settings.command_prefix
            if prefix and name.startswith(prefix):
                name = name[len(prefix) :]
            info = _find_command(name, settings, include_admin=admin)
            if info is None:
                reply(ctx, app, f"Unknown command: {ctx.args[0]}")
                return
            desc, usage = info
            reply(ctx, app, f"{name}\n{desc}\n\nUsage: {usage}")
            return

        lines = [f"{settings.bot_name}", "", "Commands:"]
        for _name, desc, usage in _user_commands(settings):
            lines.append(f"  {usage} - {desc}")

        if admin:
            lines.extend(["", "Admin:"])
            for _name, desc, usage in _admin_commands(settings):
                lines.append(f"  {usage} - {desc}")

        lines.append("")
        lines.append(f"Details: {settings.cmd('help')} <command>")
        reply(ctx, app, "\n".join(lines))
