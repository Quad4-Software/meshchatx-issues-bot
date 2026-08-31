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


def _has_propagation_node(bot) -> bool:
    if bot.config.propagation_node or bot.config.autopeer_propagation:
        return True
    if bot.config.enable_propagation_node:
        return True
    if bot.router is None:
        return False
    return bot.router.get_outbound_propagation_node() is not None


def _desired_method(bot, destination: str, *, opportunistic: bool | None):
    attempts = bot.delivery_attempts.get(destination, 0)
    max_retries = bot.config.direct_delivery_retries
    use_opportunistic = (
        bot.config.opportunistic_sending if opportunistic is None else opportunistic
    )

    if attempts >= max_retries and bot.config.propagation_fallback_enabled:
        return LXMessage.PROPAGATED
    if use_opportunistic:
        return LXMessage.OPPORTUNISTIC
    return LXMessage.DIRECT


def _ensure_path(dest_hash_bytes: bytes, destination: str) -> bool:
    """Request a path if needed. Returns whether Transport currently has one."""
    if RNS.Transport.has_path(dest_hash_bytes):
        return True
    RNS.Transport.request_path(dest_hash_bytes)
    RNS.log(
        f"Requested path to {destination}",
        RNS.LOG_INFO,
    )
    return False


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
    opportunistic: bool | None = None,
) -> bool:
    """Send an LXMF message, optionally attaching an admin stamp ticket.

    Outbound stamp generation defaults to off. Inbound stamp cost is enforced
    separately via the LXMF router, not by taxing every reply.
    """
    if bot.config.test_mode:
        original = getattr(bot, "_original_send", bot.send)
        original(
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
        identity_instance = RNS.Identity.recall(
            dest_hash_bytes,
            from_identity_hash=True,
        )
    if identity_instance is None:
        RNS.Transport.request_path(dest_hash_bytes)
        RNS.log(
            f"No identity for {destination}; reply deferred until announce",
            RNS.LOG_WARNING,
        )
        return False

    has_path = _ensure_path(dest_hash_bytes, destination)

    lxmf_destination_obj = RNS.Destination(
        identity_instance,
        RNS.Destination.OUT,
        RNS.Destination.SINGLE,
        "lxmf",
        "delivery",
    )

    desired_method = _desired_method(
        bot,
        destination,
        opportunistic=opportunistic,
    )

    lxm = LXMessage(
        lxmf_destination_obj,
        bot.local,
        message.encode("utf-8"),
        title=title.encode("utf-8") if title else None,
        desired_method=desired_method,
        fields=lxmf_fields,
        stamp_cost=stamp_cost,
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
        RNS.Transport.request_path(dest_hash_bytes)
        RNS.log(
            f"Delivery failed to {destination}, attempt {current + 1} "
            f"(has_path={RNS.Transport.has_path(dest_hash_bytes)}, "
            f"method={desired_method})",
            RNS.LOG_WARNING,
        )

    lxm.register_delivery_callback(on_delivery_success)
    lxm.register_failed_callback(on_delivery_failure)
    lxm = sign_outgoing_message(bot, lxm)

    allow_prop_fallback = (
        desired_method in (LXMessage.DIRECT, LXMessage.OPPORTUNISTIC)
        and (
            bot.config.propagation_fallback_enabled
            or desired_method == LXMessage.OPPORTUNISTIC
        )
        and _has_propagation_node(bot)
    )
    if allow_prop_fallback:
        lxm.try_propagation_on_fail = True

    if not bot._enqueue_outbound(lxm):
        RNS.log(
            f"Failed to queue message for {destination}: outbound queue full",
            RNS.LOG_ERROR,
        )
        return False

    RNS.log(
        f"Message queued for {destination} "
        f"(method: {desired_method}, has_path={has_path}, "
        f"prop_fallback={allow_prop_fallback})",
        RNS.LOG_INFO,
    )
    return True


def wrap_bot_outbound(bot, settings: Settings) -> None:
    """Prefer LXMFy opportunistic send; only custom-path when tickets are needed."""
    original_send = bot.send
    bot._original_send = original_send

    def send(
        destination,
        message,
        title="Reply",
        lxmf_fields=None,
        stamp_cost=None,
        include_ticket=None,
        opportunistic=None,
        method=None,
    ):
        use_ticket = (
            include_ticket
            if include_ticket is not None
            else should_include_ticket(destination, settings)
        )
        try:
            dest_hash_bytes = bytes.fromhex(destination)
        except ValueError:
            dest_hash_bytes = None
        if dest_hash_bytes is not None:
            _ensure_path(dest_hash_bytes, destination)

        if use_ticket:
            return deliver_message(
                bot,
                settings,
                destination,
                message,
                title=title,
                lxmf_fields=lxmf_fields,
                stamp_cost=stamp_cost,
                include_ticket=True,
                opportunistic=opportunistic,
            )
        return original_send(
            destination,
            message,
            title=title,
            lxmf_fields=lxmf_fields,
            stamp_cost=stamp_cost,
            opportunistic=opportunistic,
            method=method,
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
