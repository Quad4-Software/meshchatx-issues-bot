"""Workarounds for upstream lxmfy quirks."""


def fix_delivery_link_callback(bot) -> None:
    """Restore LXMF delivery handling on inbound links.

    lxmfy registers its own link-established callback on the delivery
    destination, replacing the LXMF router's delivery_link_established
    handler. Inbound links then never receive packet or resource callbacks,
    so direct link-based deliveries stall and the link dies. This chains
    both handlers so LXMF delivery and lxmfy link tracking both run.
    """
    local = getattr(bot, "local", None)
    router = getattr(bot, "router", None)
    if local is None or router is None:
        return
    current = getattr(local.callbacks, "link_established", None)
    if current != bot._link_established:
        return
    lxmf_cb = router.delivery_link_established
    lxmfy_cb = bot._link_established

    def on_link_established(link):
        lxmf_cb(link)
        lxmfy_cb(link)

    local.set_link_established_callback(on_link_established)
