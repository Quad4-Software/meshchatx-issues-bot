import RNS
from LXMF import LXMessage
from lxmfy.signatures import sign_outgoing_message

from meshchatx_issues_bot.config import Settings
from meshchatx_issues_bot.lxmf_hash import normalize_lxmf_hash


def should_include_ticket(destination: str, settings: Settings) -> bool:
    if not settings.grant_admin_tickets or settings.stamp_cost is None:
        return False
    h = normalize_lxmf_hash(destination)
    return h is not None and h in settings.ticket_recipients


def deliver_message(
    bot,
    settings: Settings,
    destination: str,
    message: str,
    *,
    title: str = "Reply",
    lxmf_fields: dict | None = None,
    stamp_cost: int | None = None,
    include_ticket: bool = False,
) -> bool:
    if bot.config.test_mode:
        bot.send(
            destination,
            message,
            title=title,
            lxmf_fields=lxmf_fields,
            stamp_cost=stamp_cost,
        )
        return True

    try:
        dest_hash_bytes = bytes.fromhex(destination)
    except ValueError:
        RNS.log(f"Invalid destination hash format: {destination}", RNS.LOG_ERROR)
        return False

    identity_instance = RNS.Identity.recall(dest_hash_bytes)
    if identity_instance is None:
        RNS.Transport.request_path(dest_hash_bytes)
        RNS.log(
            f"No path to {destination}; notification queued after announce",
            RNS.LOG_WARNING,
        )
        return False

    lxmf_destination_obj = RNS.Destination(
        identity_instance,
        RNS.Destination.OUT,
        RNS.Destination.SINGLE,
        "lxmf",
        "delivery",
    )

    attempts = bot.delivery_attempts.get(destination, 0)
    max_retries = bot.config.direct_delivery_retries
    if attempts >= max_retries and bot.config.propagation_fallback_enabled:
        desired_method = LXMessage.PROPAGATED
    else:
        desired_method = LXMessage.DIRECT

    final_stamp_cost = stamp_cost if stamp_cost is not None else bot.config.stamp_cost

    lxm = LXMessage(
        lxmf_destination_obj,
        bot.local,
        message.encode("utf-8"),
        title=title.encode("utf-8") if title else None,
        desired_method=desired_method,
        fields=lxmf_fields,
        stamp_cost=final_stamp_cost,
        include_ticket=include_ticket,
    )

    def on_delivery_success(_message):
        if destination in bot.delivery_attempts:
            bot.delivery_attempts[destination] = 0
            bot._save_delivery_attempts()

    def on_delivery_failure(_message):
        current = bot.delivery_attempts.get(destination, 0)
        bot.delivery_attempts[destination] = current + 1
        bot._save_delivery_attempts()

    lxm.register_delivery_callback(on_delivery_success)
    lxm.register_failed_callback(on_delivery_failure)
    lxm = sign_outgoing_message(bot, lxm)
    if (
        lxm.desired_method == LXMessage.DIRECT
        and bot.config.propagation_fallback_enabled
    ):
        lxm.try_propagation_on_fail = True
    bot.queue.put(lxm)
    return True


def wrap_bot_outbound(bot, settings: Settings) -> None:
    def send(
        destination,
        message,
        title="Reply",
        lxmf_fields=None,
        stamp_cost=None,
        include_ticket=None,
    ):
        use_ticket = (
            include_ticket
            if include_ticket is not None
            else should_include_ticket(destination, settings)
        )
        return deliver_message(
            bot,
            settings,
            destination,
            message,
            title=title,
            lxmf_fields=lxmf_fields,
            stamp_cost=stamp_cost,
            include_ticket=use_ticket,
        )

    bot.send = send


def grant_admin_tickets(bot, settings: Settings) -> int:
    if (
        not settings.grant_admin_tickets
        or settings.stamp_cost is None
        or bot.router is None
    ):
        return 0

    granted = 0
    for lxmf_hash in settings.ticket_recipients:
        try:
            ticket = bot.router.generate_ticket(bytes.fromhex(lxmf_hash))
        except ValueError:
            print(f"Warning: invalid LXMF hash for ticket grant: {lxmf_hash}")
            continue
        if ticket:
            granted += 1
    return granted
