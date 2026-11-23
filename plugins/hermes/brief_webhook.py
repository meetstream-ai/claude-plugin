"""An optional signed MeetStream workspace webhook for waking the brief worker."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import re
from pathlib import Path

from .briefs import Briefs

_POST_CALL_EVENTS = {
    "bot.done": 1,
    "transcription.processed": 2,
    "transcription.skipped": 4,
    "transcription.failed": 8,
}
_MAX_BODY = 64 * 1024
_BODY_TIMEOUT = 3
_SIGNATURE = re.compile(r"sha256=[a-fA-F0-9]{64}")


def create_app(home: Path, wake: asyncio.Event, secret: str):
    from aiohttp import web

    if not secret:
        raise ValueError("Set MEETSTREAM_BRIEF_WEBHOOK_SECRET to enable the webhook")
    key = secret.encode("utf-8")
    store = Briefs(home)

    async def receive(request):
        signature = request.headers.get("X-MeetStream-Signature", "")
        if not _SIGNATURE.fullmatch(signature):
            return web.Response(status=401)
        try:
            async with asyncio.timeout(_BODY_TIMEOUT):
                raw = await request.read()
        except TimeoutError:
            return web.Response(status=408)
        expected = "sha256=" + hmac.new(key, raw, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature.lower(), expected):
            return web.Response(status=401)
        try:
            event = json.loads(raw)
        except (UnicodeDecodeError, ValueError, RecursionError):
            return web.Response(status=400)
        if not isinstance(event, dict):
            return web.Response(status=400)
        event_type = event.get("bot_event")
        bot_id = event.get("bot_id")
        if (isinstance(event_type, str) and event_type in _POST_CALL_EVENTS and isinstance(bot_id, str)
                and re.fullmatch(r"[A-Za-z0-9_-]{1,128}", bot_id)
                and await asyncio.to_thread(store.wake, bot_id, _POST_CALL_EVENTS[event_type])):
            wake.set()
        return web.Response(status=204)

    async def prepare_ledger(_app):
        if store.path.is_file():
            await asyncio.to_thread(store.prepare)

    app = web.Application(client_max_size=_MAX_BODY)
    app.on_startup.append(prepare_ledger)
    app.router.add_post("/meetstream/briefs", receive)
    return app


async def start_listener(home: Path, wake: asyncio.Event, port: int, secret: str):
    from aiohttp import web

    if not 1 <= port <= 65535:
        raise ValueError("brief_webhook_port must be between 1 and 65535")
    runner = web.AppRunner(create_app(home, wake, secret), access_log=None, shutdown_timeout=2)
    await runner.setup()
    try:
        await web.TCPSite(runner, "127.0.0.1", port).start()
    except BaseException:
        await runner.cleanup()
        raise
    return runner
