"""Test private origin capture and restart-safe delivery at the Hermes adapter boundary."""

import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from gateway.config import Platform
from gateway.session_context import clear_session_vars, set_session_vars
from hermes_state import SessionDB

from test_plugin import KEY, api, tools

briefs = tools.briefs
messaging = tools.messaging
SESSION = "private-mobile-origin"
BOT = "mobile-bot"
TEXT = "## Decision brief\n\n- Use the blue cover [00:32 · Alex]"


class MobileBriefTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.home = Path(self.enterContext(tempfile.TemporaryDirectory()))
        with SessionDB(self.home / "state.db") as db:
            db.create_session(SESSION, source="telegram")
            db.create_session("other", source="telegram")
            db.create_session("whatsapp", source="whatsapp")
        self.ledger = briefs.Briefs(self.home)
        self.ledger.prepare()
        self.origin = {"platform": "telegram", "chat_id": "12345", "chat_type": "dm", "user_id": "12345",
                       "thread_id": "7"}

    def queue(self, bot_id=BOT, session_id=SESSION, origin=None):
        self.assertTrue(self.ledger.queue(bot_id, session_id, "In the meeting", origin=origin or self.origin))
        self.ledger.save(bot_id, TEXT)

    def allow_now(self):
        with self.ledger.db() as db:
            db.execute("UPDATE briefs SET due = 0")

    @unittest.skipUnless(messaging.capture_private_origin, "Hermes private delivery SDK is unavailable")
    def test_capture_requires_trusted_dm_context_and_exact_session(self):
        def capture(chat_type, chat_id, *, platform="telegram", session_id=SESSION):
            tokens = set_session_vars(platform=platform, chat_id=chat_id, chat_type=chat_type, user_id="12345",
                                      thread_id="7", session_key="bound", session_id=session_id)
            try:
                return messaging.capture_origin(SESSION, "telegram")
            finally:
                clear_session_vars(tokens)

        self.assertEqual(capture("dm", "12345")["thread_id"], "7")
        self.assertIsNone(capture("group", "-12345"))
        self.assertIsNone(capture("dm", "-12345"))
        self.assertIsNone(capture("dm", "12345", session_id="other"))
        self.assertIsNone(capture("dm", "12345", platform="meetstream"))

    @unittest.skipUnless(messaging.capture_private_origin, "Hermes private delivery SDK is unavailable")
    async def test_join_captures_dm_without_accepting_a_model_supplied_destination(self):
        response = mock.AsyncMock(return_value={"bot_id": BOT, "status": "Active"})
        with (mock.patch.object(tools, "get_hermes_home", return_value=self.home),
              mock.patch.object(tools, "settings", return_value=dict(tools.DEFAULTS)),
              mock.patch.object(tools, "api_key", return_value=KEY),
              mock.patch.object(api, "create_bot", response)):
            tokens = set_session_vars(platform="telegram", chat_id="12345", chat_type="dm", user_id="12345",
                                      thread_id="7", session_key="bound", session_id=SESSION)
            try:
                result = json.loads(await tools.handle_join({
                    "meeting_url": "https://meet.google.com/abc-defg-hij", "decision_brief": True,
                    "chat_id": "99999",
                }, session_id=SESSION))
            finally:
                clear_session_vars(tokens)
        self.assertIn("Queued for this chat", result["decision_brief"])
        self.assertTrue(result["decision_brief_queued"])
        self.assertIn("finish this turn", result["next"])
        self.assertEqual(json.loads(self.ledger.due()[0]["origin"])["chat_id"], "12345")

    @unittest.skipUnless(messaging.capture_private_origin, "Hermes private delivery SDK is unavailable")
    async def test_offline_then_restart_delivers_once_to_exact_chat_and_topic(self):
        self.queue()
        await briefs.poll(self.home, None, KEY, None, lambda _origin: None)
        self.assertIn("Waiting", self.ledger.status(BOT, SESSION))
        self.allow_now()
        send = mock.AsyncMock(return_value=SimpleNamespace(success=True))
        adapter = SimpleNamespace(platform=Platform.TELEGRAM, send=send, is_connected=True)
        runner = SimpleNamespace(_delivery_adapter_for=mock.Mock(return_value=adapter),
                                 _is_user_authorized_for_source=mock.Mock(return_value=True))
        await briefs.poll(self.home, None, KEY, None, lambda origin: messaging.resolve_sender(runner, origin, "default"))
        await briefs.poll(self.home, None, KEY, None, lambda _: send)
        send.assert_awaited_once_with("12345", TEXT, metadata={"thread_id": "7", "telegram_dm_topic_created_for_send": True, "_interim_send": True})
        self.assertEqual(self.ledger.status(BOT, SESSION), "Result posted to this chat")
        with SessionDB(self.home / "state.db", read_only=True) as db:
            self.assertEqual(len(db.get_messages(SESSION)), 1)
            self.assertEqual(db.get_messages("other"), [])

    async def test_call_end_and_late_transcript_trigger_the_dm_without_a_prompt(self):
        self.ledger.queue(BOT, SESSION, "In the meeting", origin=self.origin)
        model = SimpleNamespace(acomplete_structured=mock.AsyncMock(return_value=SimpleNamespace(parsed={
            "decisions": [{"text": "Use the blue cover", "ref": 1, "quote": "Use the blue cover"}],
            "actions": [], "questions": [],
        })))
        send = mock.AsyncMock(return_value=SimpleNamespace(success=True))
        with (mock.patch.object(api, "bot_status", side_effect=[
                  {"status": "InMeeting"}, {"status": "Done"}, {"status": "Done"},
              ]),
              mock.patch.object(api, "transcript", side_effect=[
                  (None, None),
                  ("finished", [{"speaker": "Alex", "start_time": 32, "transcript": "Use the blue cover."}]),
              ])):
            for expected in ("In the meeting", "Processing transcript", "Result posted to this chat"):
                await briefs.poll(self.home, None, KEY, model, lambda _: send)
                self.assertEqual(self.ledger.status(BOT, SESSION), expected)
                self.allow_now()
        self.assertEqual(send.await_count, 1)
        self.assertIn("[00:32 · Alex]", send.call_args.args[0])

    async def test_uncertain_send_is_not_replayed_after_restart(self):
        self.queue()
        send = mock.AsyncMock(side_effect=asyncio.CancelledError)
        with self.assertRaises(asyncio.CancelledError):
            await briefs.poll(self.home, None, KEY, None, lambda _: send)
        await briefs.poll(self.home, None, KEY, None, lambda _: send)
        self.assertEqual(send.await_count, 1)
        self.assertIn("Delivery unconfirmed", self.ledger.status(BOT, SESSION))

    @unittest.skipUnless(messaging.capture_private_origin, "Hermes private delivery SDK is unavailable")
    async def test_whatsapp_receives_brief_only_while_origin_is_authorized(self):
        origin = {"platform": "whatsapp", "chat_id": "15551234567@s.whatsapp.net", "chat_type": "dm",
                  "user_id": "15551234567"}
        self.queue("whatsapp-notified", "whatsapp", origin)
        self.queue("whatsapp-revoked", "whatsapp", origin)
        send = mock.AsyncMock(return_value=SimpleNamespace(success=True))
        adapter = SimpleNamespace(platform=Platform.WHATSAPP, send=send, is_connected=True)
        runner = SimpleNamespace(_delivery_adapter_for=mock.Mock(return_value=adapter),
                                 _is_user_authorized_for_source=mock.Mock(side_effect=[True, False]))
        await briefs.poll(self.home, None, KEY, None, lambda route: messaging.resolve_sender(runner, route, "default"))
        send.assert_awaited_once_with(origin["chat_id"], TEXT, metadata={"_interim_send": True})
        self.assertIn("permission revoked", self.ledger.status("whatsapp-revoked", "whatsapp"))


    @unittest.skipUnless(messaging.resolve_private_delivery, "Hermes private delivery SDK is unavailable")
    def test_private_sdk_rejects_cross_profile_routes_and_degraded_adapter(self):
        adapter = SimpleNamespace(platform=Platform.TELEGRAM, is_connected=True, send_path_degraded=True)
        runner = SimpleNamespace(_delivery_adapter_for=mock.Mock(return_value=adapter),
                                 _is_user_authorized_for_source=mock.Mock(return_value=True))
        with self.assertRaises(PermissionError):
            messaging.resolve_sender(runner, {**self.origin, "profile": "another"}, "default")
        runner._delivery_adapter_for.assert_not_called()
        self.assertIsNone(messaging.resolve_sender(runner, self.origin, "default"))
        runner._is_user_authorized_for_source.assert_not_called()

    async def test_flood_refusal_retries_and_persists_receipt(self):
        self.queue()
        send = mock.AsyncMock(side_effect=[
            SimpleNamespace(success=False, retry_after=300),
            SimpleNamespace(success=True, message_id="191"),
        ])
        await briefs.poll(self.home, None, KEY, None, lambda _: send)
        self.assertEqual(self.ledger.status(BOT, SESSION), "Waiting to retry delivery")
        await briefs.poll(self.home, None, KEY, None, lambda _: send)
        self.assertEqual(send.await_count, 1)
        self.allow_now()
        await briefs.poll(self.home, None, KEY, None, lambda _: send)
        await briefs.poll(self.home, None, KEY, None, lambda _: send)
        self.assertEqual(send.await_count, 2)
        self.assertEqual(self.ledger.result(BOT, SESSION), {
            "state": "Result posted to this chat", "message_id": "191", "brief": TEXT,
        })
        self.assertIsNone(self.ledger.result(BOT, "other"))

    @unittest.skipUnless(messaging.capture_private_origin, "Hermes private delivery SDK is unavailable")
    async def test_long_telegram_brief_is_a_single_private_attachment(self):
        long_text = TEXT + "\n" + "More context. " * 200

        async def upload(chat_id, file_path, **_):
            self.assertEqual(chat_id, "12345")
            self.assertEqual(Path(file_path).read_text(), long_text)
            return SimpleNamespace(success=True)

        adapter = SimpleNamespace(platform=Platform.TELEGRAM, send=mock.AsyncMock(),
                                  send_document=mock.AsyncMock(side_effect=upload), is_connected=True)
        runner = SimpleNamespace(_delivery_adapter_for=mock.Mock(return_value=adapter),
                                 _is_user_authorized_for_source=mock.Mock(return_value=True))
        send = messaging.resolve_sender(runner, {**self.origin, "thread_id": None}, "default")
        self.assertTrue((await send(long_text)).success)
        adapter.send.assert_not_awaited()
        self.assertFalse(Path(adapter.send_document.call_args.args[1]).exists())
        send = messaging.resolve_sender(runner, self.origin, "default")
        await send(long_text)
        self.assertEqual(adapter.send_document.await_count, 1)
        self.assertIn("saved in Hermes history", adapter.send.call_args.args[1])
        self.assertEqual(adapter.send.call_args.kwargs["metadata"]["thread_id"], "7")

    @unittest.skipUnless(messaging.capture_private_origin, "Hermes private delivery SDK is unavailable")
    async def test_lost_ack_can_be_recovered_only_from_bound_origin(self):
        self.queue()
        send = mock.AsyncMock(side_effect=TimeoutError)
        await briefs.poll(self.home, None, KEY, None, lambda _: send)
        tokens = set_session_vars(platform="telegram", chat_id="12345", chat_type="dm", user_id="12345",
                                  thread_id="7", session_key="bound", session_id=SESSION)
        try:
            with mock.patch.object(tools, "get_hermes_home", return_value=self.home):
                recovered = json.loads(await tools.handle_recover_brief({"bot_id": BOT}, session_id=SESSION))
                other = json.loads(await tools.handle_recover_brief({"bot_id": BOT}, session_id="other"))
        finally:
            clear_session_vars(tokens)
        self.assertEqual(recovered["brief"], TEXT)
        self.assertIn("unconfirmed", recovered["state"])
        self.assertIn("error", other)
        self.assertEqual(send.await_count, 1)


    async def test_native_deferred_attachment_is_not_replayed_by_the_brief_worker(self):
        self.queue()
        send = mock.AsyncMock(return_value=SimpleNamespace(
            success=False, retry_after=30, raw_response={"deferred_upload": True},
        ))
        await briefs.poll(self.home, None, KEY, None, lambda _: send)
        self.allow_now()
        await briefs.poll(self.home, None, KEY, None, lambda _: send)
        self.assertEqual(send.await_count, 1)
        self.assertIn("unconfirmed", self.ledger.status(BOT, SESSION))
