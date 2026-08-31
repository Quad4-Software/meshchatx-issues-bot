from lxmfy import IconAppearance, LXMFBot, pack_icon_appearance_field

from meshchatx_issues_bot.commands import register_commands
from meshchatx_issues_bot.config import Settings
from meshchatx_issues_bot.context import AppContext
from meshchatx_issues_bot.stamps import apply_stamp_policy
from meshchatx_issues_bot.store import BlockStore, IssueStore


def build_app() -> AppContext:
    settings = Settings.from_env()
    for warning in settings.validate():
        print(f"Warning: {warning}")

    bot_kwargs: dict = {
        "name": settings.bot_name,
        "announce": settings.announce_seconds,
        "announce_immediately": settings.announce_immediately,
        "admins": set(settings.admin_hashes),
        "command_prefix": settings.command_prefix,
        "cogs_enabled": False,
        "storage_type": "json" if not settings.test_mode else "memory",
        "storage_path": settings.storage_path,
        "rate_limit": settings.rate_limit,
        "cooldown": settings.cooldown,
        "first_message_enabled": settings.first_message_enabled,
        "signature_verification_enabled": settings.require_identity_verification,
        "require_message_signatures": False,
        "test_mode": settings.test_mode,
    }
    if settings.reticulum_config_dir:
        bot_kwargs["reticulum_config_dir"] = settings.reticulum_config_dir
    if settings.stamp_cost is not None:
        bot_kwargs["stamp_cost"] = settings.stamp_cost

    bot = LXMFBot(**bot_kwargs)
    if not settings.test_mode:
        apply_stamp_policy(bot, settings)

    icon = IconAppearance(
        icon_name="bug_report",
        fg_color=b"\xff\xb7\x4d",
        bg_color=b"\x1e\x3a\x5f",
    )
    icon_field = pack_icon_appearance_field(icon)

    app = AppContext(
        bot=bot,
        settings=settings,
        issues=IssueStore(bot.storage),
        blocks=BlockStore(bot.storage),
        icon_field=icon_field,
    )
    register_commands(app)
    return app
