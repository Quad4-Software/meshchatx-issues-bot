from meshchatx_issues_bot.config import Settings
from meshchatx_issues_bot.messaging import grant_admin_tickets, wrap_bot_outbound


def apply_stamp_policy(bot, settings: Settings) -> None:
    if bot.config.test_mode or bot.router is None or bot.local is None:
        return

    cost = settings.stamp_cost
    bot.config.stamp_cost = cost

    if cost is None:
        bot.router.set_inbound_stamp_cost(bot.local.hash, None)
        return

    if not bot.router.set_inbound_stamp_cost(bot.local.hash, cost):
        print(f"Warning: could not set inbound stamp cost to {cost}")

    try:
        bot.local.announce()
    except Exception as exc:
        print(f"Warning: re-announce after stamp policy failed: {exc}")

    wrap_bot_outbound(bot, settings)
    granted = grant_admin_tickets(bot, settings)
    if granted:
        print(f"Stamp tickets ready for {granted} admin(s)")
