from meshchatx_issues_bot.app import build_app
from meshchatx_issues_bot.env import load_env_file


def run() -> None:
    env_path = load_env_file()
    if env_path is not None:
        print(f"Loaded environment from {env_path}")

    app = build_app()
    settings = app.settings
    bot = app.bot

    print(f"Starting bot: {settings.bot_name}")
    print(f"Command prefix: {settings.command_prefix!r}")
    print(f"Notify admins: {len(settings.notify_hashes)}")
    print(f"Bot admins: {len(settings.admin_hashes)}")
    if settings.stamp_cost is not None:
        print(
            f"LXMF stamp cost: {settings.stamp_cost} (inbound required, outbound replies)",
        )
        if settings.grant_admin_tickets:
            print(
                f"Admin stamp tickets: enabled for {len(settings.ticket_recipients)} address(es)",
            )
    else:
        print("LXMF stamps: disabled")

    local = getattr(bot, "local", None)
    if local is not None and getattr(local, "hash", None) is not None:
        raw = local.hash
        hx = raw.hex() if isinstance(raw, (bytes, bytearray)) else str(raw)
        print(f"Bot LXMF address: {hx.strip().lower()}")

    bot.run()
