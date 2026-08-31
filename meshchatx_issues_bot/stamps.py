from meshchatx_issues_bot.config import Settings
from meshchatx_issues_bot.messaging import grant_admin_tickets, wrap_bot_outbound


def apply_stamp_policy(bot, settings: Settings) -> None:
    if bot.config.test_mode or bot.router is None or bot.local is None:
        return

    cost = settings.stamp_cost

    if cost is None:
        bot.config.stamp_cost = None
        bot.router.set_inbound_stamp_cost(bot.local.hash, None)
        wrap_bot_outbound(bot, settings)
        return

    if not bot.router.set_inbound_stamp_cost(bot.local.hash, cost):
        print(f"Warning: could not set inbound stamp cost to {cost}")

    # Keep inbound cost on the router only. Clearing config.stamp_cost stops
    # LXMFy from generating expensive stamps on every outbound reply.
    bot.config.stamp_cost = None

    try:
        bot.local.announce()
    except Exception as exc:
        print(f"Warning: re-announce after stamp policy failed: {exc}")

    wrap_bot_outbound(bot, settings)
    granted = grant_admin_tickets(bot, settings)
    if granted:
        print(f"Stamp tickets ready for {granted} admin(s)")
