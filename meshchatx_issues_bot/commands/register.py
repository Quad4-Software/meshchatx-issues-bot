from meshchatx_issues_bot.commands.admin import register_admin_commands
from meshchatx_issues_bot.commands.help import register_help
from meshchatx_issues_bot.commands.identity_gate import register_identity_gate
from meshchatx_issues_bot.commands.user import register_user_commands
from meshchatx_issues_bot.context import AppContext


def register_commands(app: AppContext) -> None:
    register_identity_gate(app)
    register_blocked_middleware(app)
    register_welcome(app)
    register_user_commands(app)
    register_admin_commands(app)
    register_help(app)


def register_blocked_middleware(app: AppContext) -> None:
    bot = app.bot

    @bot.on_message()
    def reject_blocked(sender, message):
        h = app.blocks.is_blocked(sender)
        if not h:
            return False
        content = message.content.decode("utf-8", errors="replace").strip()
        prefix = app.settings.command_prefix
        if prefix is not None and not content.startswith(prefix):
            return False
        if prefix is None:
            cmd = content.split()[0] if content else ""
        else:
            cmd = (
                content[len(prefix) :].split()[0] if content.startswith(prefix) else ""
            )
        if cmd and cmd not in bot.commands:
            return False
        bot.send(
            sender,
            "You are blocked from using this bot.",
            lxmf_fields=app.icon_field,
        )
        return True


def register_welcome(app: AppContext) -> None:
    if not app.settings.first_message_enabled:
        return

    bot = app.bot
    settings = app.settings

    @bot.on_first_message()
    def welcome(sender, _message):
        if app.blocks.is_blocked(sender):
            bot.send(
                sender,
                "You are blocked from using this bot.",
                lxmf_fields=app.icon_field,
            )
            return True
        stamp_note = ""
        if settings.stamp_cost is not None:
            stamp_note = (
                f"Stamp cost: {settings.stamp_cost} (required to message this bot)\n\n"
            )
        text = (
            f"{settings.bot_name}\n\n"
            f"{stamp_note}"
            f"{settings.cmd(settings.cmd_report)} <description>\n"
            "(attach files or images to the same message)\n"
            f"{settings.cmd(settings.cmd_update)} <id> [more text]\n"
            f"{settings.cmd(settings.cmd_myissues)}\n"
            f"{settings.cmd(settings.cmd_issue)} <id>\n"
            f"whoami - your address\n"
            f"{settings.cmd('help')} - commands"
        )
        bot.send(sender, text, lxmf_fields=app.icon_field)
        return True
