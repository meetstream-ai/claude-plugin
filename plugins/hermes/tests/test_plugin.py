"""Behaviour tests against a fake MeetStream API (httpx.MockTransport). No network, no real key."""

import asyncio
import importlib.util
import json
import sys
import time
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest import mock

import httpx

ROOT = Path(__file__).resolve().parents[1]
PKG = "meetstream_plugin_under_test"


def _load_plugin():
    if PKG in sys.modules:
        return sys.modules[PKG]
    spec = importlib.util.spec_from_file_location(PKG, ROOT / "__init__.py", submodule_search_locations=[str(ROOT)])
    module = importlib.util.module_from_spec(spec)
    sys.modules[PKG] = module
    spec.loader.exec_module(module)
    return module


plugin = _load_plugin()
api = sys.modules[f"{PKG}.meetstream_client"]
adapter_mod = sys.modules[f"{PKG}.adapter"]
tools = sys.modules[f"{PKG}.meetstream_tools"]
guard = sys.modules[f"{PKG}.guard"]

from gateway.config import PlatformConfig  # noqa: E402
from gateway.platform_registry import PlatformEntry, platform_registry  # noqa: E402

if not platform_registry.is_registered("meetstream"):
    platform_registry.register(PlatformEntry(name="meetstream", label="MeetStream", adapter_factory=lambda c: None,
                                             check_fn=lambda: True))

KEY = "ms_test_key"
SETTINGS = {"bot_name": "Hermes", "transcription": "meetstream", "join_message": "Hi, I'm {name}."}


class FakeMeetStream:
    """In-memory MeetStream: bots, their status and chat."""

    def __init__(self):
        self.bots: dict[str, dict] = {}
        self.sent: list[tuple[str, str]] = []
        self.created: list[dict] = []
        self.join_keys: dict[str, str] = {}
        self.hide_list = False
        self.transcript_responses: list[httpx.Response] = []
        self.requests: list[httpx.Request] = []
        self.reject_key = False
        self.create_error: httpx.Response | None = None
        self.list_error = 0
        self.chat_send_error_after: int | None = None
        self.page_size = 50
        self.broken: dict[str, int] = {}  # bot_id -> HTTP status its per-bot endpoints return
        self.bot_display = "Hermes"  # how the meeting shows the bot's own chat messages
        self.create_error: httpx.Response | None = None  # answer create_bot with this instead

    def add_bot(self, bot_id, status="InMeeting", hermes=True, chats=(), name="Hermes", attrs=None, age_s=3600):
        if attrs is None:
            attrs = {"hermes": True} if hermes else {}
        self.bots[bot_id] = {"status": status, "attrs": attrs, "chats": list(chats),
                             "name": name if hermes or attrs else "MeetStream Bot",
                             "created_at": time.time() - age_s}

    def say(self, bot_id, who, text):
        chats = self.bots[bot_id]["chats"]
        chats.append({"messageId": f"m{len(chats)}", "speakerDisplayName": who, "text": text,
                      "timestamp": "2026-11-12T10:00:00Z"})

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.reject_key or request.headers.get("Authorization") != f"Token {KEY}":
            return httpx.Response(401, json={"detail": "Invalid token."})
        path = request.url.path.removeprefix("/api/v1")
        parts = path.strip("/").split("/")
        if path == "/bots/create_bot" and self.create_error is not None:
            return self.create_error
        if path == "/bots/create_bot":
            if self.create_error is not None:
                return self.create_error
            body = json.loads(request.content)
            retry_key = request.headers.get("Idempotency-Key")
            if retry_key in self.join_keys:
                bot_id = self.join_keys[retry_key]
                return httpx.Response(507, json={"bot_id": bot_id, "status": self.bots[bot_id]["status"]})
            self.created.append(body)
            bot_id = "bot-new" if len(self.created) == 1 else f"bot-new-{len(self.created)}"
            self.add_bot(bot_id, status="Joining", attrs=body["custom_attributes"], age_s=0)
            if retry_key:
                self.join_keys[retry_key] = bot_id
            return httpx.Response(201, json={"bot_id": bot_id, "status": "Active",
                                             "meeting_url": body["meeting_link"], "transcript_id": None})
        if path == "/transcript/t1/get_transcript" and self.transcript_responses:
            return self.transcript_responses.pop(0)
        if path == "/bots":
            if self.list_error:
                return httpx.Response(self.list_error, json={"message": "Bot list temporarily unavailable"})
            rows = [{"bot_id": b, "status": v["status"], "bot_username": v["name"], "custom_attributes": v["attrs"],
                     "created_at": v["created_at"]} for b, v in self.bots.items()]
            if self.hide_list:
                rows = []
            target = request.url.params.get(f"custom_attr[{api.JOIN_ATTR}]")
            if target:
                rows = [row for row in rows if row["custom_attributes"].get(api.JOIN_ATTR) == target]
            start = int(request.url.params.get("cursor") or 0)
            page = rows[start:start + self.page_size]
            more = start + self.page_size < len(rows)
            return httpx.Response(200, json={"bots": page, "hasNextPage": more,
                                             "nextCursor": str(start + self.page_size) if more else None})
        bot = self.bots.get(parts[1]) if len(parts) > 2 else None
        if parts[1:2] and parts[1] in self.broken:
            return httpx.Response(self.broken[parts[1]], json={"detail": "broken"})
        if bot is None:
            return httpx.Response(404, json={"detail": "Bot not found."})
        action = parts[2]
        if action == "status":
            return httpx.Response(200, json={"bot_id": parts[1], "status": bot["status"]})
        if action == "detail":
            return httpx.Response(200, json={"bot_details": bot.get("detail", {})})
        if action == "get_chats":
            if "chat_error" in bot:
                return httpx.Response(bot["chat_error"], json={"message": "Chat unavailable"})
            if bot.get("chat_pending"):
                return httpx.Response(202, json="Manifest is still being processed. Current status: None")
            return httpx.Response(200, json={"chatMessages": bot["chats"]})
        if action == "transcriptions":
            return httpx.Response(200, json={"transcriptions": []})
        if action == "get_transcript" and self.transcript_responses:
            return self.transcript_responses.pop(0)
        if action == "send_message":
            if self.chat_send_error_after is not None and len(self.sent) >= self.chat_send_error_after:
                return httpx.Response(429, json={"message": "Rate limited"})
            text = json.loads(request.content)["message"]
            self.sent.append((parts[1], text))
            bot["chats"].append({"messageId": f"m{len(bot['chats'])}", "speakerDisplayName": self.bot_display,
                                 "text": text})
            return httpx.Response(200, json={"status": "sent", "bot_id": parts[1]})
        if action == "remove_bot":
            bot["status"] = "Stopped"
            return httpx.Response(200, json={"bot_id": parts[1], "status": "stop_requested"})
        return httpx.Response(404, json={"detail": "unknown"})


class PluginTestCase(unittest.TestCase):
    def setUp(self):
        self.fake = FakeMeetStream()
        transport = httpx.MockTransport(self.fake.handler)
        patches = [
            mock.patch.object(api, "new_client",
                              lambda: httpx.AsyncClient(base_url=api.BASE_URL, transport=transport)),
            mock.patch.object(tools, "api_key", lambda: KEY),
            mock.patch.object(tools, "settings", lambda: dict(SETTINGS)),
            mock.patch.object(adapter_mod, "_key", lambda: KEY),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        adapter_mod._PENDING.clear()

    def run_async(self, coro):
        return asyncio.run(coro)

    def make_adapter(self, **extra):
        a = adapter_mod.MeetStreamAdapter(PlatformConfig(enabled=True, extra=extra))
        a._client = api.new_client()
        a._running = True
        a.handle_message = mock.AsyncMock()
        return a


class TestAddressing(unittest.TestCase):
    def test_messages_that_address_the_bot(self):
        a = adapter_mod.addressed
        self.assertEqual(a("Hermes, what did we decide?", "Hermes"), "what did we decide?")
        self.assertEqual(a("@hermes summarize so far", "Hermes"), "summarize so far")
        self.assertEqual(a("hey Hermes: next steps?", "Hermes"), "next steps?")
        self.assertEqual(a("can you check this @Hermes", "Hermes"), "can you check this")
        self.assertEqual(a("Acme  AI, hello there", "acme ai"), "hello there")
        self.assertEqual(a("Notes Bot! what is next", "Notes Bot"), "what is next")

    def test_messages_that_do_not(self):
        a = adapter_mod.addressed
        for text in ("let's ask Hermes later", "Hermesville is a town", "Hermes", "Hermes-ville is a town",
                     "Hermes's notes are good", "mail me at me@hermes.com", "write to @hermes.com today"):
            self.assertIsNone(a(text, "Hermes"), text)
        self.assertIsNone(a("Hermes, hi", ""))


class TestPayload(unittest.TestCase):
    def test_join_payload_tags_bot_and_sets_safe_leave_timeouts(self):
        p = api.build_join_payload("https://meet.google.com/abc-defg-hij", bot_name="Hermes", message="hi")
        self.assertEqual(p["custom_attributes"], {"hermes": True, api.BRIEF_TRANSCRIPTION_ATTR: True})
        self.assertEqual(p["automatic_leave"]["everyone_left_timeout"], 60)
        self.assertEqual(p["recording_config"]["transcript"]["provider"], {"meetstream": {"language": "auto", "translate": False}})
        self.assertFalse(p["video_required"])

    def test_rejects_non_meeting_links(self):
        for url in ("http://meet.google.com/x", "https://evil.example/zoom.us", "https://zoom.us.evil.com/j/1", "file:///etc"):
            with self.assertRaises(ValueError, msg=url):
                api.build_join_payload(url, bot_name="Hermes")
        api.build_join_payload("https://us02web.zoom.us/j/123", bot_name="Hermes")
        api.build_join_payload("https://teams.microsoft.com/l/meetup-join/x", bot_name="Hermes")

    def test_link_that_parsers_read_differently_is_refused(self):
        for url in ("https://evil.example\\@meet.google.com/x", "https://user@meet.google.com/x",
                    "https://meet.google.com/x y", "https://meet.google.com\t.evil.example/x"):
            with self.assertRaises(ValueError, msg=url):
                api.validate_meeting_url(url)
        self.assertEqual(api.validate_meeting_url(" https://MEET.google.com/abc-defg-hij?authuser=1 "),
                         "https://meet.google.com/abc-defg-hij?authuser=1")

    def test_bot_id_cannot_change_the_api_path(self):
        for bad in ("../users", "a/b", "x?y=1", "", "a" * 200):
            with self.assertRaises(ValueError, msg=bad):
                api.bot_path(bad, "status")
        self.assertEqual(api.bot_path("604c0a0b-973d-4eb1-a5bf-2c7513f6bbe0", "status"),
                         "/bots/604c0a0b-973d-4eb1-a5bf-2c7513f6bbe0/status")

    def test_chunks_fit_meeting_chat(self):
        parts = api.chunks(("word " * 1000).strip())
        self.assertTrue(all(len(p) <= api.MAX_CHAT for p in parts))
        self.assertEqual(" ".join(parts), ("word " * 1000).strip())


class TestTools(PluginTestCase):
    def test_create_error_preserves_provider_message_and_retry_delay(self):
        self.fake.create_error = httpx.Response(
            429, headers={"Retry-After": "37"},
            json={"error": "rate_limit_exceeded", "message": "Too many bots created"},
        )
        out = json.loads(self.run_async(tools.handle_join({"meeting_url": "https://meet.google.com/abc-defg-hij"})))
        self.assertEqual(out["status_code"], 429)
        self.assertEqual(out["error"], "Too many bots created (retry after 37 s)")

    def test_low_credit_join_error_links_to_billing(self):
        self.fake.create_error = httpx.Response(403, json={"message": "Low credits please recharge"})
        out = json.loads(self.run_async(tools.handle_join({"meeting_url": "https://meet.google.com/abc-defg-hij"})))
        self.assertEqual(out["status_code"], 403)
        self.assertIn(api.BILLING_URL, out["hint"])

    def test_join_creates_tagged_bot_and_hands_it_to_the_adapter(self):
        out = json.loads(self.run_async(tools.handle_join({"meeting_url": "https://meet.google.com/abc-defg-hij"})))
        self.assertEqual(out["bot_id"], "bot-new")
        body = self.fake.created[0]
        self.assertEqual(body["bot_name"], "Hermes")
        self.assertIn("recording and transcribing", body["bot_message"])
        self.assertTrue(body["bot_message"].endswith("Hi, I'm Hermes."))
        self.assertIs(body["custom_attributes"]["hermes"], True)
        self.assertFalse(out["joined"])
        self.assertIn((str(adapter_mod.get_hermes_home()), "bot-new"), adapter_mod._PENDING)

    def test_duplicate_join_reuses_bot_and_finished_call_can_rejoin_same_link(self):
        url = "https://meet.google.com/abc-defg-hij"
        first = json.loads(self.run_async(tools.handle_join({"meeting_url": url})))
        self.fake.bots[first["bot_id"]]["status"] = "InWaitingRoom"
        again = json.loads(self.run_async(tools.handle_join({"meeting_url": url + "?authuser=0"})))
        self.assertTrue(again["reused"])
        self.assertEqual(again["bot_id"], first["bot_id"])
        self.assertEqual(again["status"], "InWaitingRoom")
        self.assertEqual(len(self.fake.created), 1)

        self.fake.bots[first["bot_id"]]["status"] = "MediaProcessing"
        later = json.loads(self.run_async(tools.handle_join({"meeting_url": url})))
        self.assertFalse(later["reused"])
        self.assertNotEqual(later["bot_id"], first["bot_id"])
        self.assertEqual(len(self.fake.created), 2)

    def test_scheduled_occurrences_are_distinct_but_equivalent_times_reuse_the_bot(self):
        url = "https://meet.google.com/abc-defg-hij"
        times = ("2026-11-20T15:00:00Z", "2026-11-20T20:30:00+05:30", "2026-11-27T15:00:00Z")
        outs = [json.loads(self.run_async(tools.handle_join({"meeting_url": url, "join_at": when})))
                for when in times]
        self.assertEqual(outs[0]["bot_id"], outs[1]["bot_id"])
        self.assertNotEqual(outs[0]["bot_id"], outs[2]["bot_id"])
        self.assertEqual(len(self.fake.created), 2)

    def test_replayed_create_reuses_bot_when_it_is_not_visible_in_list(self):
        self.fake.hide_list = True
        args = {"meeting_url": "https://meet.google.com/abc-defg-hij"}
        outs = [json.loads(self.run_async(tools.handle_join(args))) for _ in range(2)]
        self.assertEqual([out["bot_id"] for out in outs], ["bot-new", "bot-new"])
        self.assertTrue(outs[1]["reused"])
        self.assertEqual(len(self.fake.created), 1)

    def test_stale_list_and_finished_replay_still_allow_a_new_occurrence(self):
        self.fake.hide_list = True
        args = {"meeting_url": "https://meet.google.com/abc-defg-hij"}
        first = json.loads(self.run_async(tools.handle_join(args)))
        self.fake.bots[first["bot_id"]]["status"] = "Done"
        second = json.loads(self.run_async(tools.handle_join(args)))
        again = json.loads(self.run_async(tools.handle_join(args)))
        self.assertNotEqual(first["bot_id"], second["bot_id"])
        self.assertEqual(second["bot_id"], again["bot_id"])
        self.assertEqual(len(self.fake.created), 2)

    def test_disabled_transcription_and_custom_notice_are_reported_accurately(self):
        with mock.patch.object(tools, "settings", return_value={**SETTINGS, "transcription": "none"}):
            result = json.loads(self.run_async(tools.handle_join({
                "meeting_url": "https://meet.google.com/abc-defg-hij",
                "message": "Welcome from {name}.",
            })))
        body = self.fake.created[0]
        self.assertFalse(result["transcription_requested"])
        self.assertIn("recording this call", body["bot_message"])
        self.assertNotIn("transcribing", body["bot_message"])
        self.assertIn("Welcome from Hermes.", body["bot_message"])
        self.assertNotIn("recording_config", body)

    def test_status_includes_join_failure_reason(self):
        self.fake.add_bot("b1", status="NotAllowed")
        self.fake.bots["b1"]["detail"] = {"ErrorReason": "WaitingRoomTimeout", "message": "Bot was not admitted"}
        out = json.loads(self.run_async(tools.handle_status({"bot_id": "b1"})))
        self.assertEqual(out["status"], "NotAllowed")
        self.assertEqual(out["error_reason"], "WaitingRoomTimeout")
        self.assertIn("host admit", out["hint"])

    def test_transcript_after_host_removal_waits_for_ready_even_if_chat_fails(self):
        self.fake.add_bot("b1", status="Kicked")
        self.fake.bots["b1"].update(detail={"transcript_id": "t1"}, chat_error=404)
        segments = [{"speaker": "Priya", "transcript": "I'll finish the edit Thursday."}]
        self.fake.transcript_responses = [
            httpx.Response(202, json={"message": "Still processing"}),
            httpx.Response(200, json=segments),
        ]
        with mock.patch.object(tools, "TRANSCRIPT_POLL_SECONDS", 0):
            out = json.loads(self.run_async(tools.handle_transcript({"bot_id": "b1", "wait_seconds": 1})))
        self.assertEqual(out["transcript_state"], "ready")
        self.assertEqual(out["untrusted_meeting_content"]["transcript"], segments)
        self.assertEqual(out["chat_status_code"], 404)

    def test_http_202_returns_pending_without_transcript_content(self):
        self.fake.add_bot("b1", status="MediaProcessing")
        self.fake.bots["b1"]["detail"] = {"transcript_id": "t1"}
        self.fake.transcript_responses = [httpx.Response(202, json={"message": "Still processing"})]
        out = json.loads(self.run_async(tools.handle_transcript({"bot_id": "b1"})))
        self.assertEqual(out["transcript_state"], "pending")
        self.assertIsNone(out["untrusted_meeting_content"]["transcript"])

    def test_malformed_bot_list_stops_join_without_creating_a_duplicate(self):
        def respond(request):
            if request.method == "GET":
                return httpx.Response(200, json={"bots": {"unexpected": "object"}})
            raise AssertionError("Must confirm bot list before creating a bot")

        with mock.patch.object(api, "new_client", side_effect=lambda: httpx.AsyncClient(
            base_url=api.BASE_URL, transport=httpx.MockTransport(respond)
        )):
            result = json.loads(self.run_async(tools.handle_join({"meeting_url": "https://meet.google.com/abc-defg-hij"})))
        self.assertIn("unexpected bot list", result["error"])

    def test_billing_conflict_is_pending_rather_than_permanently_unavailable(self):
        self.fake.add_bot("b1", status="Done")
        self.fake.bots["b1"]["detail"] = {"transcript_id": "t1"}
        self.fake.transcript_responses = [httpx.Response(
            409, json={"error": "Session billing is still in progress. Retry after the meeting is billed."}
        )]
        out = json.loads(self.run_async(tools.handle_transcript({"bot_id": "b1"})))
        self.assertEqual(out["transcript_state"], "pending")

    def test_pending_primary_uses_completed_retranscription(self):
        segments = [{"speaker": "Priya", "transcript": "We approved the plan.", "start_time": 12}]

        def respond(request):
            path = request.url.path.removeprefix("/api/v1")
            if path == "/bots/b1/detail":
                return httpx.Response(200, json={"bot_details": {"transcript_id": "primary"}})
            if path == "/transcript/primary/get_transcript":
                return httpx.Response(202)
            if path == "/bots/b1/transcriptions":
                return httpx.Response(200, json={"transcriptions": [
                    {"provider": "meetstream", "transcript_id": "primary", "status": "Not started"},
                    {"provider": "meeting_captions", "transcript_id": None, "status": "Success"},
                    {"provider": "deepgram", "transcript_id": "stale", "status": "Success"},
                    {"provider": "deepgram", "transcript_id": "recovered", "status": "Success"},
                ]})
            if path == "/transcript/stale/get_transcript":
                return httpx.Response(404)
            if path == "/transcript/recovered/get_transcript":
                return httpx.Response(200, json=segments)
            raise AssertionError(path)

        async def read():
            async with httpx.AsyncClient(base_url=api.BASE_URL, transport=httpx.MockTransport(respond)) as client:
                return await api.transcript(client, KEY, "b1")

        self.assertEqual(self.run_async(read()), ("recovered", segments))

    def test_empty_transcript_and_pending_chat_are_distinct(self):
        self.fake.add_bot("b1", status="Done")
        self.fake.bots["b1"].update(detail={"transcript_id": "t1"}, chat_pending=True)
        self.fake.transcript_responses = [httpx.Response(200, json=[])]
        out = json.loads(self.run_async(tools.handle_transcript({"bot_id": "b1"})))
        self.assertEqual(out["transcript_state"], "ready")
        self.assertTrue(out["transcript_empty"])
        self.assertEqual(out["chat_state"], "pending")

    def test_transcript_by_bot_id_reports_disabled_transcription(self):
        self.fake.add_bot("b1", status="Done")
        self.fake.transcript_responses = [httpx.Response(409, json={"message": "Transcription was not enabled"})]
        out = json.loads(self.run_async(tools.handle_transcript({"bot_id": "b1"})))
        self.assertEqual(out["transcript_state"], "unavailable")
        self.assertIn("not enabled", out["hint"])

    def test_chat_error_reports_how_much_was_sent(self):
        self.fake.add_bot("b1")
        self.fake.chat_send_error_after = 1
        out = json.loads(self.run_async(tools.handle_chat({"bot_id": "b1", "message": "x " * 1500})))
        self.assertEqual(out["sent"], 1)
        self.assertEqual(out["parts"], 2)
        self.assertEqual(out["status_code"], 429)

    def test_join_refuses_bad_link_without_calling_meetstream(self):
        out = json.loads(self.run_async(tools.handle_join({"meeting_url": "https://example.com/meeting"})))
        self.assertIn("error", out)
        self.assertEqual(self.fake.requests, [])

    def test_rejected_key_gives_actionable_error(self):
        self.fake.reject_key = True
        out = json.loads(self.run_async(tools.handle_leave({"bot_id": "x"})))
        self.assertEqual(out["status_code"], 401)
        self.assertIn("MEETSTREAM_API_KEY", out["hint"])

    def test_low_credit_gives_top_up_link_not_key_hint(self):
        self.fake.create_error = httpx.Response(403, json={"message": "Low credits please recharge"})
        out = json.loads(self.run_async(tools.handle_join({"meeting_url": "https://meet.google.com/abc-defg-hij"})))
        self.assertEqual(out["status_code"], 403)
        self.assertIn("app.meetstream.ai/billing", out["hint"])
        self.assertNotIn("MEETSTREAM_API_KEY", out["hint"])

    def test_error_reads_message_first_and_keeps_retry_after(self):
        self.fake.create_error = httpx.Response(
            429, headers={"Retry-After": "37"},
            json={"error": "rate_limit_exceeded", "message": "Too many bots created in the last minute"})
        out = json.loads(self.run_async(tools.handle_join({"meeting_url": "https://meet.google.com/abc-defg-hij"})))
        self.assertEqual(out["status_code"], 429)
        self.assertEqual(out["error"], "Too many bots created in the last minute (retry after 37 s)")

    def test_status_lists_only_hermes_bots(self):
        self.fake.page_size = 1
        self.fake.add_bot("b2", hermes=False)
        self.fake.add_bot("b1", hermes=True)
        out = json.loads(self.run_async(tools.handle_status({})))
        self.assertEqual([b["bot_id"] for b in out["bots"]], ["b1"])

    def test_chat_and_leave(self):
        self.fake.add_bot("b1")
        out = json.loads(self.run_async(tools.handle_chat({"bot_id": "b1", "message": "Agenda: pricing"})))
        self.assertEqual(out["sent"], 1)
        self.assertEqual(self.fake.sent, [("b1", "Agenda: pricing")])
        self.run_async(tools.handle_leave({"bot_id": "b1"}))
        self.assertEqual(self.fake.bots["b1"]["status"], "Stopped")


class TestAdapter(PluginTestCase):
    def test_bot_started_by_hermes_answers_from_the_first_question(self):
        async def go():
            a = self.make_adapter(discovery_seconds=0)
            adapter_mod.watch("bot-new")
            self.fake.add_bot("bot-new", status="InMeeting")
            self.fake.say("bot-new", "Sid", "Hermes, what is on the agenda?")
            self.fake.say("bot-new", "Nav", "unrelated chatter")
            await a._tick()
            await a._tick()  # nothing new: no second dispatch
            await a._client.aclose()
            return a
        a = self.run_async(go())
        a.handle_message.assert_awaited_once()
        event = a.handle_message.await_args.args[0]
        self.assertEqual(event.text, "what is on the agenda?")
        self.assertEqual(event.source.chat_id, "bot-new")
        self.assertEqual(event.source.user_id, "sid")

    def test_discovered_mid_call_does_not_answer_old_chat(self):
        async def go():
            a = self.make_adapter()
            self.fake.add_bot("cal-1", status="InMeeting")
            self.fake.add_bot("other", status="InMeeting", hermes=False)
            self.fake.say("cal-1", "Sid", "Hermes, old question")
            await a._tick()
            self.assertNotIn("other", a._bots)
            self.fake.say("cal-1", "Sid", "Hermes, new question")
            await a._tick()
            await a._client.aclose()
            return a
        a = self.run_async(go())
        a.handle_message.assert_awaited_once()
        self.assertEqual(a.handle_message.await_args.args[0].text, "new question")

    def test_calendar_auto_join_bot_is_found_by_name(self):
        # MeetStream auto-schedule replaces custom_attributes, so the name is the only marker left.
        async def go():
            a = self.make_adapter()
            self.fake.add_bot("cal-2", name="Hermes", attrs={"source": "auto_schedule_cron"})
            self.fake.add_bot("plain", name="Notetaker", attrs={"source": "auto_schedule_cron"})
            await a._tick()
            await a._client.aclose()
            return a
        a = self.run_async(go())
        self.assertIn("cal-2", a._bots)
        self.assertNotIn("plain", a._bots)

    def test_one_broken_bot_does_not_starve_the_others(self):
        async def go():
            a = self.make_adapter(discovery_seconds=0)
            for b in ("gone", "ok"):
                adapter_mod.watch(b)
                self.fake.add_bot(b)
            self.fake.broken["gone"] = 404
            self.fake.say("ok", "Sid", "Hermes, are you there?")
            await a._tick()
            await a._client.aclose()
            return a
        a = self.run_async(go())
        self.assertNotIn("gone", a._bots)
        a.handle_message.assert_awaited_once()
        self.assertFalse(a.has_fatal_error)

    def test_forbidden_bot_is_dropped_without_stopping_the_platform(self):
        async def go():
            a = self.make_adapter(discovery_seconds=0)
            adapter_mod.watch("other-account")
            self.fake.add_bot("other-account")
            self.fake.broken["other-account"] = 403
            await a._tick()
            await a._client.aclose()
            return a
        a = self.run_async(go())
        self.assertNotIn("other-account", a._bots)
        self.assertFalse(a.has_fatal_error)

    def test_discovery_reads_every_page(self):
        async def go():
            a = self.make_adapter()
            self.fake.page_size = 2
            for i in range(5):
                self.fake.add_bot(f"plain-{i}", hermes=False)
            self.fake.add_bot("late-hermes")
            await a._discover()
            await a._client.aclose()
            return a
        a = self.run_async(go())
        self.assertIn("late-hermes", a._bots)

    def test_fresh_bot_found_by_discovery_answers_early_questions(self):
        async def go():
            a = self.make_adapter()
            a._started_at -= 60
            self.fake.add_bot("cli-bot", age_s=30)
            bot = self.fake.bots["cli-bot"]
            bot["created_at"] = datetime.fromtimestamp(bot["created_at"], UTC).isoformat().replace("+00:00", "Z")
            self.fake.say("cli-bot", "Sid", "Hermes, first question")
            await a._tick()
            await a._client.aclose()
            return a
        a = self.run_async(go())
        a.handle_message.assert_awaited_once()

    def test_recent_bot_chat_is_not_replayed_on_restart(self):
        async def go():
            self.fake.add_bot("b1", age_s=10)
            self.fake.say("b1", "Sid", "Hermes, previous question")
            a = self.make_adapter()
            await a._tick()
            a.handle_message.assert_not_awaited()
            self.fake.say("b1", "Sid", "Hermes, new question")
            await a._tick()
            a.handle_message.assert_awaited_once()
            await a._client.aclose()
        self.run_async(go())

    def test_zoom_chat_polling_continues_during_discovery_failure(self):
        async def go():
            a = self.make_adapter()
            self.fake.list_error = 503
            adapter_mod.watch("zoom")
            self.fake.add_bot("zoom", status="RecordingPermissionAllowed")
            self.fake.say("zoom", "Hermes Johnson", "Hermes, are you there?")
            await a._tick()
            a.handle_message.assert_awaited_once()
            await a._client.aclose()
        self.run_async(go())

    def test_http_202_does_not_seed_history_and_slows_polling(self):
        async def go():
            a = self.make_adapter(discovery_seconds=0)
            self.fake.add_bot("b1")
            self.fake.say("b1", "Sid", "Hermes, are you there?")
            self.fake.bots["b1"]["chat_pending"] = True
            a._consider({"bot_id": "b1", "status": "InMeeting", "bot_username": "Hermes"})
            await a._tick()
            self.assertTrue(a._bots["b1"].chat_pending)
            self.assertFalse(a._bots["b1"].seeded)
            attempts = len(self.fake.requests)
            await a._tick()
            self.assertEqual(len(self.fake.requests), attempts)
            a.handle_message.assert_not_awaited()
            await a._client.aclose()
        self.run_async(go())

    def test_join_handoff_is_consumed_only_by_its_profile(self):
        async def go():
            self.fake.add_bot("b1")
            with mock.patch.object(adapter_mod, "get_hermes_home", return_value="/profile-A"):
                owner = self.make_adapter(discovery_seconds=0)
                adapter_mod.watch("b1")
            with mock.patch.object(adapter_mod, "get_hermes_home", return_value="/profile-B"):
                other = self.make_adapter(discovery_seconds=0)
                await other._tick()
            self.assertNotIn("b1", other._bots)
            await owner._tick()
            self.assertIn("b1", owner._bots)
            await owner._client.aclose()
            await other._client.aclose()
        self.run_async(go())

    def test_expired_key_is_fatal_when_discovery_is_disabled(self):
        async def go():
            a = self.make_adapter(discovery_seconds=0)
            self.fake.reject_key = True
            adapter_mod.watch("b1")
            await a._run()
            self.assertTrue(a.has_fatal_error)
            await a._client.aclose()
        self.run_async(go())

    def test_reply_is_not_read_back_when_meeting_renames_the_bot(self):
        async def go():
            a = self.make_adapter(discovery_seconds=0)
            adapter_mod.watch("b1")
            self.fake.add_bot("b1")
            self.fake.bot_display = "Meeting Notetaker"
            await a._tick()
            await a.send("b1", "Hermes, here is the answer")
            await a._tick()
            await a._client.aclose()
            return a
        a = self.run_async(go())
        a.handle_message.assert_not_awaited()

    def test_send_refuses_a_bot_hermes_is_not_in(self):
        async def go():
            a = self.make_adapter()
            result = await a.send("someone-elses-bot", "hello")
            await a._client.aclose()
            return result
        self.fake.add_bot("someone-elses-bot")
        result = self.run_async(go())
        self.assertFalse(result.success)
        self.assertEqual(self.fake.sent, [])

    def test_first_tick_discovers_even_right_after_boot(self):
        async def go():
            a = self.make_adapter()
            self.fake.add_bot("cal-3")
            with mock.patch.object(adapter_mod.time, "monotonic", return_value=5.0):
                await a._tick()
            await a._client.aclose()
            return a
        self.assertIn("cal-3", self.run_async(go())._bots)

    def test_bad_poll_setting_falls_back_to_default(self):
        a = adapter_mod.MeetStreamAdapter(PlatformConfig(enabled=True, extra={"chat_poll_seconds": "fast"}))
        self.assertEqual(a._chat_poll, adapter_mod.CHAT_POLL_S)

    def test_own_replies_are_not_read_back_as_questions(self):
        async def go():
            a = self.make_adapter(discovery_seconds=0)
            adapter_mod.watch("b1")
            self.fake.add_bot("b1")
            await a._tick()
            result = await a.send("b1", "Hermes, here is the answer")
            await a._tick()
            await a._client.aclose()
            return a, result
        a, result = self.run_async(go())
        self.assertTrue(result.success)
        a.handle_message.assert_not_awaited()

    def test_long_reply_is_split_into_chat_sized_messages(self):
        async def go():
            a = self.make_adapter()
            a._bots["b1"] = adapter_mod._Watch("b1")
            await a.send("b1", "x " * 1500)
            await a._client.aclose()
        self.fake.add_bot("b1")
        self.run_async(go())
        self.assertEqual(len(self.fake.sent), 2)
        self.assertTrue(all(len(t) <= api.MAX_CHAT for _, t in self.fake.sent))

    def test_ended_bot_is_dropped(self):
        async def go():
            a = self.make_adapter(discovery_seconds=0)
            adapter_mod.watch("b1")
            self.fake.add_bot("b1", status="Done")
            await a._tick()
            await a._client.aclose()
            return a
        a = self.run_async(go())
        self.assertNotIn("b1", a._bots)

    def test_rejected_key_stops_the_loop_with_a_fatal_error(self):
        async def go():
            a = self.make_adapter()
            self.fake.reject_key = True
            await a._run()
            await a._client.aclose()
            return a
        a = self.run_async(go())
        self.assertFalse(a._running)
        self.assertTrue(a.has_fatal_error)

    def test_poll_interval_has_a_floor(self):
        a = adapter_mod.MeetStreamAdapter(PlatformConfig(enabled=True, extra={"chat_poll_seconds": 0.1}))
        self.assertGreaterEqual(a._chat_poll, adapter_mod.MIN_POLL_S)


class TestMeetingGuard(unittest.TestCase):
    """Meeting chat senders are display names anyone can type, so meeting turns get web search only."""

    def setUp(self):
        guard._MEETING_IDS.clear()

    def test_meeting_turn_blocks_everything_but_web_search(self):
        guard.on_pre_llm_call(session_id="s-meet", task_id="t-meet", platform="meetstream")
        for tool in ("terminal", "write_file", "patch", "execute_code", "delegate_task", "memory",
                     "mcp__fs__read_file", "meetstream_join", "meetstream_transcript", "send_message"):
            verdict = guard.on_pre_tool_call(tool_name=tool, session_id="s-meet", task_id="t-meet")
            self.assertEqual((verdict or {}).get("action"), "block", tool)
        for tool in ("web_search", "web_extract"):
            self.assertIsNone(guard.on_pre_tool_call(tool_name=tool, session_id="s-meet"))

    def test_platform_object_and_enum_spellings_count(self):
        from gateway.config import Platform

        guard.on_pre_llm_call(session_id="s-obj", platform=Platform("meetstream"))
        guard.on_pre_llm_call(session_id="s-enum", platform="Platform.MEETSTREAM")
        guard.on_pre_llm_call(session_id="s-pad", platform=" MeetStream ")
        for sid in ("s-obj", "s-enum", "s-pad"):
            self.assertEqual(guard.on_pre_tool_call(tool_name="terminal", session_id=sid)["action"], "block", sid)
        guard.on_pre_llm_call(session_id="s-near", platform="meetstream-like")
        self.assertIsNone(guard.on_pre_tool_call(tool_name="terminal", session_id="s-near"))

    def test_active_meeting_session_is_not_evicted(self):
        guard.on_pre_llm_call(session_id="s-live", platform="meetstream")
        for i in range(guard._MAX_TRACKED - 1):
            guard._remember(f"filler-{i}")
        guard.on_pre_tool_call(tool_name="terminal", session_id="s-live")  # refreshes s-live
        guard._remember("one-more")
        self.assertTrue(guard.is_meeting_turn(session_id="s-live"))

    def test_task_id_alone_identifies_the_meeting_turn(self):
        guard.on_pre_llm_call(session_id="", task_id="t-only", platform="meetstream")
        self.assertEqual(guard.on_pre_tool_call(tool_name="terminal", task_id="t-only")["action"], "block")

    def test_other_platforms_are_untouched(self):
        guard.on_pre_llm_call(session_id="s-cli", platform="cli")
        guard.on_pre_llm_call(session_id="s-tg", platform="telegram")
        for sid in ("s-cli", "s-tg", "", "unknown"):
            self.assertIsNone(guard.on_pre_tool_call(tool_name="terminal", session_id=sid))

    def test_meeting_requests_are_directed_to_the_registered_runtime_skill(self):
        context = guard.on_pre_llm_call(session_id="private-chat", platform="telegram")
        self.assertIn('skill_view("meetstream:hermes-in-meetings")', context["context"])
        self.assertIsNone(guard.on_pre_llm_call(session_id="in-call", platform="meetstream"))

    def test_tracking_is_bounded(self):
        for i in range(guard._MAX_TRACKED + 50):
            guard.on_pre_llm_call(session_id=f"s{i}", platform="meetstream")
        self.assertLessEqual(len(guard._MEETING_IDS), guard._MAX_TRACKED)
        self.assertTrue(guard.is_meeting_turn(session_id=f"s{guard._MAX_TRACKED + 49}"))

    def test_adapter_pins_meeting_turns_to_web_without_mcp(self):
        a = adapter_mod.MeetStreamAdapter(PlatformConfig(enabled=True, extra={}))
        self.assertEqual(a.toolsets_for_source(None), ["web", "no_mcp"])

    def test_hermes_resolves_the_override_without_shell_files_or_mcp(self):
        # The gateway feeds toolsets_for_source() through this same resolver (gateway/run_turn.py).
        from hermes_cli.tools_config import _get_platform_tools

        cfg = {"platform_toolsets": {"meetstream": ["web", "no_mcp"]},
               "mcp_servers": {"localfs": {"command": "npx", "args": ["fs-server"]}}}
        enabled = _get_platform_tools(cfg, "meetstream")
        self.assertIn("web", enabled)
        self.assertFalse({"terminal", "file", "code_execution", "delegation", "localfs"} & enabled, enabled)


class TestRegistration(unittest.TestCase):
    def test_registers_declared_tools_platform_and_skill(self):
        ctx = mock.MagicMock()
        plugin.register(ctx)
        names = [c.kwargs["name"] for c in ctx.register_tool.call_args_list]
        manifest = (ROOT / "plugin.yaml").read_text().split("provides_tools:\n", 1)[1]
        declared = []
        for line in manifest.splitlines():
            if not line.startswith("  - "):
                break
            declared.append(line[4:].strip())
        self.assertEqual(sorted(names), sorted(declared))
        self.assertEqual(ctx.register_platform.call_args.kwargs["name"], "meetstream")
        hooks = {c.args[0] for c in ctx.register_hook.call_args_list}
        self.assertEqual(hooks, {"pre_llm_call", "pre_tool_call"})
        self.assertEqual(ctx.register_skill.call_args.args[0], "hermes-in-meetings")


if __name__ == "__main__":
    unittest.main()
