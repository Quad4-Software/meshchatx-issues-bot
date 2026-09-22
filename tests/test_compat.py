import threading
import time
from types import SimpleNamespace

from meshchatx_issues_bot.compat import fix_delivery_link_callback
from meshchatx_issues_bot.pending import PendingStore, start_flush_thread


def _bot():
    calls = []
    local = SimpleNamespace(
        callbacks=SimpleNamespace(link_established=None),
    )
    local.set_link_established_callback = lambda cb: setattr(
        local.callbacks,
        "link_established",
        cb,
    )
    router = SimpleNamespace(
        delivery_link_established=lambda link: calls.append("lxmf"),
    )
    bot = SimpleNamespace(local=local, router=router)
    bot._link_established = lambda link: calls.append("lxmfy")
    return bot, calls


def test_fix_delivery_link_callback_chains():
    bot, calls = _bot()
    bot.local.set_link_established_callback(bot._link_established)

    fix_delivery_link_callback(bot)

    cb = bot.local.callbacks.link_established
    assert cb != bot._link_established
    cb(object())
    assert calls == ["lxmf", "lxmfy"]


def test_fix_delivery_link_callback_leaves_other_wiring():
    bot, _ = _bot()
    bot.local.set_link_established_callback(bot.router.delivery_link_established)

    fix_delivery_link_callback(bot)

    assert bot.local.callbacks.link_established == bot.router.delivery_link_established


def test_fix_delivery_link_callback_missing_parts():
    fix_delivery_link_callback(SimpleNamespace(local=None, router=None))
    fix_delivery_link_callback(SimpleNamespace())


def test_flush_thread_runs(monkeypatch, memory_storage, settings):
    import meshchatx_issues_bot.pending as pending_mod

    ran = threading.Event()

    def fake_flush(bot, s, p):
        ran.set()
        return 0, 0

    monkeypatch.setattr(pending_mod, "flush_pending", fake_flush)
    start_flush_thread(
        object(),
        settings,
        PendingStore(memory_storage),
        interval=0.02,
    )
    assert ran.wait(2)


def test_flush_thread_survives_errors(monkeypatch, memory_storage, settings):
    import meshchatx_issues_bot.pending as pending_mod

    calls = []

    def boom(*args):
        calls.append(1)
        raise RuntimeError("nope")

    monkeypatch.setattr(pending_mod, "flush_pending", boom)
    start_flush_thread(
        object(),
        settings,
        PendingStore(memory_storage),
        interval=0.02,
    )
    deadline = time.time() + 2
    while len(calls) < 2 and time.time() < deadline:
        time.sleep(0.02)
    assert len(calls) >= 2
