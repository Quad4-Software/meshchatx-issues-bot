from contextlib import suppress

from lxmfy.events import EventPriority

from meshchatx_issues_bot.context import AppContext
from meshchatx_issues_bot.identity import verify_sender


def register_identity_gate(app: AppContext) -> None:
    if not app.settings.require_identity_verification:
        return

    bot = app.bot

    @bot.events.on("message_received", priority=EventPriority.HIGHEST)
    def verify_incoming(event):
        message = event.data.get("message")
        sender = event.data.get("sender")
        if message is None or not sender:
            return

        ok, _, _ = verify_sender(message, sender, app.settings)
        if ok:
            return

        event.cancel()
        with suppress(Exception):
            bot.send(
                sender,
                "Message rejected: could not verify sender identity.",
            )
