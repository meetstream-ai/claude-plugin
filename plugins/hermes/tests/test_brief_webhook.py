"""Exercise the signed webhook over loopback without exposing the gateway."""

import asyncio
import hmac
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from aiohttp.test_utils import TestClient, TestServer

from test_plugin import plugin


class WebhookTests(unittest.IsolatedAsyncioTestCase):
    async def test_signed_event_wakes_one_queued_bot_once_after_restart(self):
        from importlib import import_module

        webhook = import_module(f"{plugin.__name__}.brief_webhook")
        home = Path(self.enterContext(tempfile.TemporaryDirectory()))
        ledger = webhook.Briefs(home)
        with ledger.db() as db:
            db.execute("ALTER TABLE briefs ADD COLUMN origin TEXT")
            db.execute("ALTER TABLE briefs ADD COLUMN send_started INTEGER NOT NULL DEFAULT 0")
        ledger.queue("queued", "session", "In meeting", start_check=4_000_000_000)
        ledger.queue("other", "session", "Scheduled", start_check=4_000_000_000)
        wake = asyncio.Event()
        secret = "test-secret"

        async def post(client, data, sign=True):
            signature = "sha256=" + hmac.digest(secret.encode(), data, "sha256").hex() if sign else ""
            response = await client.post("/meetstream/briefs", data=data, headers={"X-MeetStream-Signature": signature})
            return response.status

        body = json.dumps({"bot_id": "queued", "bot_event": "transcription.processed"}).encode()
        async with TestClient(TestServer(webhook.create_app(home, wake, secret))) as client:
            self.assertEqual(await post(client, body, sign=False), 401)
            self.assertEqual(await post(client, b"{}"), 204)
            self.assertEqual(await post(client, b"x" * 65537), 413)
            self.assertFalse(wake.is_set())
            self.assertEqual(ledger.due(), [])
            self.assertEqual(await post(client, body), 204)
            self.assertTrue(wake.is_set())
            self.assertEqual([row["bot_id"] for row in ledger.due()], ["queued"])

        [queued] = ledger.due()
        ledger.defer(queued, "Processing transcript")
        wake.clear()
        async with TestClient(TestServer(webhook.create_app(home, wake, secret))) as client:
            self.assertEqual(await post(client, body), 204)
            self.assertFalse(wake.is_set())
            self.assertEqual(ledger.due(), [])


    async def test_invalid_signature_header_never_reads_body_and_slow_read_times_out(self):
        from importlib import import_module

        webhook = import_module(f"{plugin.__name__}.brief_webhook")
        home = Path(self.enterContext(tempfile.TemporaryDirectory()))
        app = webhook.create_app(home, asyncio.Event(), "test-secret")
        handler = next(iter(app.router.routes())).handler
        request = mock.Mock(headers={}, read=mock.AsyncMock())
        self.assertEqual((await handler(request)).status, 401)
        request.headers = {"X-MeetStream-Signature": "sha256=bad"}
        self.assertEqual((await handler(request)).status, 401)
        request.read.assert_not_awaited()

        async def stalled_body():
            await asyncio.Event().wait()

        request.headers = {"X-MeetStream-Signature": f"sha256={'0' * 64}"}
        request.read.side_effect = stalled_body
        with mock.patch.object(webhook, "_BODY_TIMEOUT", 0.01):
            self.assertEqual((await handler(request)).status, 408)
        request.read.assert_awaited_once()

    def test_stale_poll_preserves_webhook_wake_across_restart(self):
        ledger = plugin.tools.briefs.Briefs(Path(self.enterContext(tempfile.TemporaryDirectory())))
        ledger.prepare()
        ledger.queue("queued", "session", "In meeting")
        [snapshot] = ledger.due()
        self.assertTrue(ledger.wake("queued", 2))
        ledger.defer(snapshot, "Processing transcript", processing=True)
        reopened = plugin.tools.briefs.Briefs(ledger.home)
        [woken] = reopened.due()
        self.assertEqual(woken["webhook_events"], 2)
        self.assertIsNotNone(woken["processing_since"])
        reopened.defer(woken, "Processing transcript", processing=True)
        self.assertEqual(reopened.due(), [])
