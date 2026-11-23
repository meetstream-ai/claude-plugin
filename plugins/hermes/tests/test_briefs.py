"""Decision-brief recovery against a real Hermes SessionDB and simulated MeetStream."""

import asyncio
import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

import httpx
from hermes_state import SessionDB

from test_plugin import adapter_mod, api, KEY, plugin, ROOT, tools

briefs = plugin.adapter.briefs
ORIGINAL = "desktop-original"
OTHER = "desktop-other"
BOT = "qa-bot"
TRANSCRIPT = [
    {"speaker": "Priya", "start_time": 29.2, "transcript": "We decided to use the blue cover."},
    {"participant": {"name": "Priya"}, "words": [
        {"text": word, "start_timestamp": {"relative": 44.0 + i / 3}}
        for i, word in enumerate("I'll deliver the first edit Thursday.".split())
    ]},
    {"participant": {"name": "Sam"}, "words": [
        {"text": word, "start_timestamp": {"relative": 47.0 + i / 3}}
        for i, word in enumerate("I'll check captions on Friday.".split())
    ]},
]


class Model:
    async def acomplete_structured(self, *, input, **kwargs):
        evidence = json.loads(input[0]["text"])
        assert evidence["2"]["speaker"] == "Priya"
        return SimpleNamespace(parsed={
            "decisions": [{"text": "Use the blue cover.", "ref": 1, "quote": "use the blue cover"}],
            "actions": [
                {"text": "Deliver the first edit.", "owner": "Priya", "due": "Thursday", "ref": 2, "quote": "deliver the first edit Thursday"},
                {"text": "Check captions.", "owner": "Sam", "due": "Friday", "ref": 3, "quote": "check captions on Friday"},
                {"text": "Check captions", "owner": "Sam", "due": "Friday", "ref": 3, "quote": "check captions on Friday"},
            ],
            "questions": [],
        })


async def worker(mode: str, home: Path):
    requests = []

    def respond(request):
        path = request.url.path
        requests.append(path)
        if path.endswith("/status"):
            return httpx.Response(200, json={"status": "InWaitingRoom" if mode == "lobby" else "Done"})
        if path.endswith("/detail"):
            return httpx.Response(200, json={"transcript_id": "qa-transcript"})
        if path.endswith("/transcriptions"):
            return httpx.Response(200, json={"transcriptions": []})
        if path.endswith("/get_transcript"):
            if mode == "pending":
                return httpx.Response(202, json={"message": "Processing"})
            return httpx.Response(200, json=TRANSCRIPT)
        raise AssertionError(path)

    ledger = briefs.Briefs(home)
    if mode == "lobby":
        with SessionDB(home / "state.db") as db:
            db.create_session(ORIGINAL, source="desktop")
            db.create_session(OTHER, source="desktop")
        ledger.prepare()
        assert ledger.queue(BOT, ORIGINAL, "Join requested")
        assert ledger.queue(BOT, ORIGINAL, "Join requested")
        assert not ledger.queue(BOT, OTHER, "Join requested")
    if mode == "crash":
        # The history append is committed before this callback. End the process
        # before its acknowledgement reaches the plugin ledger.
        def crash_after_history(*_):
            os._exit(42)

        briefs.Briefs.finish = crash_after_history
    with ledger.db() as db:
        db.execute("UPDATE briefs SET due = 0")
    async with httpx.AsyncClient(base_url=api.BASE_URL, transport=httpx.MockTransport(respond)) as client:
        await briefs.poll(home, client, KEY, Model())
    if mode in {"resume", "replay"}:
        assert requests == [], "Staged briefs must survive without another transcript/model call"


class BriefTests(unittest.TestCase):
    def test_one_brief_survives_worker_restart_and_unacknowledged_delivery(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            ledger = briefs.Briefs(home)

            def run(mode, expected=0):
                result = subprocess.run(
                    [sys.executable, __file__, mode, str(home)],
                    capture_output=True, text=True, timeout=30,
                )
                self.assertEqual(result.returncode, expected, result.stdout + result.stderr)

            run("lobby")
            self.assertEqual(ledger.status(BOT, ORIGINAL), "Waiting for host admission")
            self.assertIsNone(ledger.status(BOT, OTHER))
            run("pending")
            self.assertEqual(ledger.status(BOT, ORIGINAL), "Processing transcript")
            run("crash", expected=42)
            self.assertEqual(ledger.status(BOT, ORIGINAL), "Brief ready · delivering")
            run("resume")
            run("replay")
            self.assertEqual(ledger.status(BOT, ORIGINAL), "Result posted to this chat")
            with SessionDB(home / "state.db", read_only=True) as db:
                notes = db.get_messages(ORIGINAL, include_compacted=True)
                self.assertEqual(len(notes), 1)
                self.assertEqual(notes[0]["display_kind"], "process_complete")
                self.assertEqual(db.get_messages(OTHER, include_compacted=True), [])
            note = notes[0]["content"]
            for citation in ("[00:29 · Priya]", "[00:44 · Priya]", "[00:47 · Sam]"):
                self.assertIn(citation, note)
            self.assertEqual(note.count("Check captions"), 1)


class FeatureTests(unittest.IsolatedAsyncioTestCase):
    async def test_join_queues_for_private_hermes_session_and_marks_gif(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            with SessionDB(home / "state.db") as db:
                db.create_session(ORIGINAL, source="desktop")
                db.create_session(OTHER, source="meetstream")
            create = mock.AsyncMock(return_value={"bot_id": BOT, "status": "Active"})
            opts = {"meeting_url": "https://meet.google.com/abc-defg-hij",
                    "decision_brief": True, "status_gifs": True}
            with (mock.patch.object(tools, "get_hermes_home", return_value=home),
                  mock.patch.object(tools, "settings", return_value=dict(tools.DEFAULTS)),
                  mock.patch.object(tools, "api_key", return_value=KEY),
                  mock.patch.object(adapter_mod, "watch") as watch,
                  mock.patch.object(api, "create_bot", create)):
                invalid = json.loads(await tools.handle_join(opts, session_id=OTHER))
                self.assertIn("saved private", invalid["error"])
                create.assert_not_awaited()
                result = json.loads(await tools.handle_join(opts, session_id=ORIGINAL))
                self.assertEqual(result["meeting_status"], "Join requested")
                self.assertIn("Queued for this chat", result["decision_brief"])
                self.assertTrue(create.call_args.args[2]["custom_attributes"][api.GIF_ATTR])
                watch.assert_called_once_with(BOT, status_gifs=True)

    async def test_poll_migrates_older_pending_ledger_before_recovery(self):
        home = Path(self.enterContext(tempfile.TemporaryDirectory()))
        ledger = briefs.Briefs(home)
        with ledger.db() as db:
            db.execute("ALTER TABLE briefs ADD COLUMN origin TEXT")
            db.execute("ALTER TABLE briefs ADD COLUMN send_started INTEGER NOT NULL DEFAULT 0")
        ledger.queue(BOT, ORIGINAL, "Join requested")

        with mock.patch.object(api, "bot_status", return_value={"status": "InMeeting"}):
            await briefs.poll(home, None, KEY, Model())

        self.assertEqual(ledger.status(BOT, ORIGINAL), "In the meeting")
        self.assertTrue(ledger.wake(BOT, 1))

    async def test_generation_failure_retries_across_polls_and_delivers_one_notice(self):
        home = Path(self.enterContext(tempfile.TemporaryDirectory()))
        with SessionDB(home / "state.db") as db:
            db.create_session(ORIGINAL, source="desktop")
        ledger = briefs.Briefs(home)
        ledger.prepare()
        ledger.queue(BOT, ORIGINAL, "In the meeting")
        with (mock.patch.object(api, "bot_status", return_value={"status": "Done"}),
              mock.patch.object(api, "transcript", return_value=("transcript", TRANSCRIPT)),
              mock.patch.object(briefs, "summarize", side_effect=ValueError("invalid model output")) as summarize):
            for _ in range(4):
                with ledger.db() as db:
                    db.execute("UPDATE briefs SET due = 0")
                await briefs.poll(home, None, KEY, Model())
        self.assertEqual(summarize.await_count, 3)
        with SessionDB(home / "state.db", read_only=True) as db:
            notes = db.get_messages(ORIGINAL)
        self.assertEqual(len(notes), 1)
        self.assertIn("Decision brief unavailable", notes[0]["content"])
        self.assertIn("transcript is available", notes[0]["content"])

    async def test_reused_bots_only_queue_when_transcription_is_verified(self):
        home = Path(self.enterContext(tempfile.TemporaryDirectory()))
        with SessionDB(home / "state.db") as db:
            db.create_session(ORIGINAL, source="desktop")
        opts = {"meeting_url": "https://meet.google.com/abc-defg-hij", "decision_brief": True}
        result = {"bot_id": BOT, "status": "InMeeting", "reused": True}
        with (mock.patch.object(tools, "get_hermes_home", return_value=home),
              mock.patch.object(tools, "settings", return_value=dict(tools.DEFAULTS)),
              mock.patch.object(tools, "api_key", return_value=KEY),
              mock.patch.object(adapter_mod, "watch"),
              mock.patch.object(api, "create_bot", return_value=result),
              mock.patch.object(api, "bot_status", return_value={"custom_attributes": {}}) as status,
              mock.patch.object(api, "bot_detail", return_value={"bot_details": {}}) as detail):
            unverified = json.loads(await tools.handle_join(opts, session_id=ORIGINAL))
            self.assertTrue(unverified["reused"])
            self.assertFalse(unverified["decision_brief_queued"])
            self.assertIn("could not verify", unverified["decision_brief"])
            status.return_value = {"custom_attributes": {api.BRIEF_TRANSCRIPTION_ATTR: False}}
            detail.reset_mock()
            disabled = json.loads(await tools.handle_join(opts, session_id=ORIGINAL))
            self.assertFalse(disabled["decision_brief_queued"])
            self.assertIn("without a post-call transcription provider", disabled["decision_brief"])
            detail.assert_not_awaited()

            status.return_value = {"custom_attributes": {}}
            detail.return_value = {"bot_details": {"transcript_id": "ready"}}
            verified = json.loads(await tools.handle_join(opts, session_id=ORIGINAL))
            self.assertTrue(verified["decision_brief_queued"])

    async def test_repeat_join_reports_a_completed_brief_without_queuing_again(self):
        home = Path(self.enterContext(tempfile.TemporaryDirectory()))
        with SessionDB(home / "state.db") as db:
            db.create_session(ORIGINAL, source="desktop")
        ledger = briefs.Briefs(home)
        ledger.prepare()
        ledger.queue(BOT, ORIGINAL, "In the meeting")
        ledger.finish(BOT, "Result posted to this chat")
        with (mock.patch.object(tools, "get_hermes_home", return_value=home),
              mock.patch.object(tools, "settings", return_value=dict(tools.DEFAULTS)),
              mock.patch.object(api, "create_bot", return_value={
                  "bot_id": BOT, "status": "InMeeting", "reused": True,
                  "custom_attributes": {api.BRIEF_TRANSCRIPTION_ATTR: True},
              }),
              mock.patch.object(adapter_mod, "watch")):
            result = json.loads(await tools.handle_join(
                {"meeting_url": "https://meet.google.com/abc-defg-hij", "decision_brief": True}, session_id=ORIGINAL,
            ))
        self.assertFalse(result["decision_brief_queued"])
        self.assertEqual(result["decision_brief_status"], "Result posted to this chat")
        self.assertEqual(ledger.due(), [])

    async def test_only_actual_activity_sends_the_supplied_animated_gifs(self):
        sent = []

        def respond(request):
            command = request.url.path.rsplit("/", 1)[-1]
            if command == "get_chats":
                return httpx.Response(202, json={"message": "Processing"})
            if command == "send_image":
                payload = json.loads(request.content)
                sent.append(base64.b64decode(payload["img"], validate=True))
            return httpx.Response(200, json={"status": "accepted"})

        a = adapter_mod.MeetStreamAdapter(adapter_mod.PlatformConfig())
        async with httpx.AsyncClient(base_url=api.BASE_URL, transport=httpx.MockTransport(respond)) as a._client:
            w = adapter_mod._Watch(BOT, status="inwaitingroom", status_gifs=True,
                                   checked_at=adapter_mod.time.monotonic())
            a._bots[BOT] = w
            with mock.patch.object(adapter_mod, "_key", return_value=KEY):
                await a._poll_bot(w)
                self.assertEqual(sent, [])
                w.status = "recording"
                await a._poll_bot(w)
                self.assertTrue(w.chat_pending)
                self.assertEqual(sent, [])
                await a.send_typing(BOT)
                await a.send_typing(BOT)
                w.typing_since -= api.GIF_DURATION
                await a.send_typing(BOT)
                await a.stop_typing(BOT)
                self.assertIsNone(w.typing_since)
                self.assertTrue((await a.send(BOT, "QA reply")).success)
        self.assertEqual(sent, [(ROOT / "assets" / name).read_bytes() for name in (
            "hermes-agent-thinking.gif", "hermes-agent-nous-research.gif", "hermes-agent-working.gif",
        )])
        self.assertTrue(all(gif.startswith(b"GIF89a") and b"NETSCAPE2.0" in gif for gif in sent))

    async def test_hosted_gif_uses_meetstream_url_playback(self):
        calls = []

        def respond(request):
            calls.append(json.loads(request.content))
            return httpx.Response(200, json={"status": "accepted"})

        async with httpx.AsyncClient(base_url=api.BASE_URL, transport=httpx.MockTransport(respond)) as client:
            await api.send_status_gif(client, KEY, BOT, "activity", base_url="https://assets.example.com/hermes/")
            with self.assertRaises(ValueError):
                await api.send_status_gif(client, KEY, BOT, "activity", base_url="http://assets.example.com/hermes/")
        self.assertEqual(calls, [{
            "img_url": "https://assets.example.com/hermes/hermes-agent-nous-research.gif",
            "display_duration": api.GIF_DURATION,
        }])

    def test_action_restatements_preserve_distinct_work(self):
        rows = [
            ("Own the first edit by Thursday", "Priya", "Thursday", "00:36"),
            ("Deliver the first edit", "Priya", "Thursday", "00:38"),
            ("Review the first edit", "Priya", "Thursday", "00:44"),
            ("Check the captions", "Sam", "Friday", "00:45"),
            ("Check captions on Friday", "Sam", "Friday", "00:49"),
        ]
        self.assertEqual(briefs.unique_actions(rows), [rows[1], rows[2], rows[3]])

    async def test_invalid_model_timestamp_is_never_published(self):
        llm = mock.Mock()
        llm.acomplete_structured = mock.AsyncMock(return_value=SimpleNamespace(parsed={
            "decisions": [{"text": "Invented source", "ref": 90}],
            "actions": [],
            "questions": [],
        }))
        with self.assertRaisesRegex(ValueError, "valid transcript reference"):
            await briefs.summarize(llm, TRANSCRIPT)


    async def test_action_owner_and_due_need_evidence_in_the_cited_fragment(self):
        llm = SimpleNamespace(acomplete_structured=mock.AsyncMock(return_value=SimpleNamespace(parsed={
            "decisions": [], "questions": [],
            "actions": [
                {"text": "Deliver the first edit", "owner": "Priya", "due": "Thursday",
                 "ref": 2, "quote": "deliver the first edit Thursday"},
                {"text": "Check captions", "owner": "Taylor", "due": "Monday",
                 "ref": 3, "quote": "check captions on Friday"},
            ],
        })))
        text = await briefs.summarize(llm, TRANSCRIPT)
        self.assertIn("Owner: Priya · Due: Thursday", text)
        self.assertIn("Owner: unassigned · Due: not stated", text)
        self.assertNotIn("Taylor", text)
        self.assertNotIn("Monday", text)

    async def test_matching_timestamp_without_supporting_quote_is_omitted(self):
        llm = mock.Mock()
        llm.acomplete_structured = mock.AsyncMock(return_value=SimpleNamespace(parsed={
            "decisions": [
                {"text": "Use the blue cover", "ref": 1, "quote": "use the blue cover"},
                {"text": "Cancel the launch", "ref": 1, "quote": "cancel the launch"},
            ],
            "actions": [],
            "questions": [],
        }))
        text = await briefs.summarize(llm, TRANSCRIPT)
        self.assertIn("Use the blue cover [00:29 · Priya]", text)
        self.assertNotIn("Cancel the launch", text)
        self.assertIn("supporting quotes could not be verified", text)


if __name__ == "__main__":
    asyncio.run(worker(sys.argv[1], Path(sys.argv[2])))
