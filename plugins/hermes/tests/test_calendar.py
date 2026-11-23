"""Exercise named meetings at the MeetStream HTTP boundary without booking live calls."""

import json
import tempfile
import unittest
from contextlib import ExitStack
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo

import httpx
from hermes_state import SessionDB
from gateway.session_context import clear_session_vars, set_session_vars

from test_plugin import KEY, api, tools

SESSION = "calendar-origin"
OTHER = "another-desktop-chat"
ROOM = "https://meet.google.com/abc-defg-hij"


def event(event_id, start, title="Launch Sync", **extra):
    return {
        "id": event_id,
        "start_time": start.isoformat(),
        "end_time": (start + timedelta(minutes=30)).isoformat(),
        "meeting_url": ROOM,
        "calendar_id": "Product",
        "raw": {"summary": title, "start": {"timeZone": "America/New_York"}},
        **extra,
    }


class CalendarTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        stack = self.enterContext(ExitStack())
        home = Path(stack.enter_context(tempfile.TemporaryDirectory()))
        self.home = home
        with SessionDB(home / "state.db") as db:
            db.create_session(SESSION, source="desktop")
            db.create_session(OTHER, source="desktop")
            db.create_session("meeting", source="meetstream")
        self.future = (datetime.now(UTC) + timedelta(days=2)).replace(hour=14, minute=0, second=0, microsecond=0)
        self.past = self.future - timedelta(days=5)
        self.event_records = []
        self.bots = []
        self.calls = []
        self.created = []
        self.calendar_missing = False
        self.config = dict(tools.DEFAULTS)
        stack.enter_context(mock.patch.object(tools, "get_hermes_home", return_value=home))
        stack.enter_context(mock.patch.object(tools, "api_key", return_value=KEY))
        stack.enter_context(mock.patch.object(tools, "settings", return_value=self.config))
        stack.enter_context(mock.patch.object(api, "new_client", side_effect=lambda: httpx.AsyncClient(
            base_url=api.BASE_URL, transport=httpx.MockTransport(self.respond))))

    def respond(self, request):
        self.calls.append(request)
        path = request.url.path
        if path.endswith("/calendar/events"):
            if self.calendar_missing:
                return httpx.Response(400, json={"message": "No calendar connected"})
            page = request.url.params.get("cursor")
            return httpx.Response(200, json={
                "results": self.event_records[1:] if page else self.event_records[:1],
                "has_more": not page and len(self.event_records) > 1,
                "next": "second" if not page and len(self.event_records) > 1 else None,
            })
        if path.endswith("/bots"):
            target = request.url.params.get(f"custom_attr[{api.JOIN_ATTR}]")
            bots = [b for b in self.bots if not target or b.get("custom_attributes", {}).get(api.JOIN_ATTR) == target]
            return httpx.Response(200, json={"bots": bots})
        if path.endswith("/bots/create_bot"):
            payload = json.loads(request.content)
            self.assertTrue(request.headers["Idempotency-Key"])
            self.created.append(payload)
            record = {
                "bot_id": "scheduled-bot", "status": "Scheduled", "bot_username": "Hermes",
                "scheduled_join_time": payload["join_at"], "custom_attributes": payload["custom_attributes"],
            }
            self.bots.append(record)
            return httpx.Response(201, json=record)
        raise AssertionError(f"Unexpected endpoint: {request.method} {path}")

    async def tool(self, handler, args, session=SESSION):
        return json.loads(await handler(args, session_id=session))

    def options(self, at=None):
        return {"date": (at or self.future).date().isoformat(), "timezone": "America/New_York"}

    async def preview(self, event_id, **extra):
        return await self.tool(tools.handle_calendar, {**self.options(), "event_id": event_id, **extra})

    async def test_title_lookup_matches_reused_room_by_occurrence_without_fetching_transcripts(self):
        tuesday = self.past
        next_week = tuesday + timedelta(days=1)
        self.event_records = [event("first", tuesday), event("second", next_week)]
        self.bots = [
            {"bot_id": "first-bot", "status": "Done", "bot_username": "Hermes",
             "start_time": (tuesday + timedelta(minutes=1)).isoformat(), "meeting_url": ROOM + "?authuser=0"},
            {"bot_id": "second-bot", "status": "Done", "bot_username": "Hermes",
             "start_time": next_week.isoformat(), "meeting_url": ROOM},
            {"bot_id": "unrelated", "status": "Done", "bot_username": "Other",
             "start_time": next_week.isoformat(), "meeting_url": ROOM},
        ]
        search = {**self.options(tuesday), "title": "launch sync", "end_date": next_week.date().isoformat()}
        result = await self.tool(tools.handle_find_meetings, search)
        self.assertTrue(result["ambiguous"])
        self.assertFalse(result["incomplete"])
        self.assertEqual([m["bot_id"] for m in result["matches"]], ["second-bot", "first-bot"])
        selected = await self.tool(tools.handle_find_meetings, {**search, "event_id": "first"})
        self.assertEqual([m["bot_id"] for m in selected["matches"]], ["first-bot"])
        self.assertEqual({r.method for r in self.calls}, {"GET"})

    async def test_calendar_read_failure_preserves_date_and_title_search_of_known_bots(self):
        self.calendar_missing = True
        self.bots = [{"bot_id": "unlinked", "status": "Done", "bot_username": "Hermes",
                      "start_time": self.past.isoformat(), "custom_attributes": {api.TITLE_ATTR: "Launch Sync"}}]
        result = await self.tool(tools.handle_find_meetings, {**self.options(self.past), "title": "launch"})
        self.assertTrue(result["incomplete"])
        self.assertEqual(result["matches"][0]["bot_id"], "unlinked")
        self.assertIn("No calendar connected", result["issues"][0])

    async def test_named_preview_is_read_only_then_selected_event_schedules_once(self):
        self.event_records = [
            event("review-a", self.future, "Design Review"),
            event("review-b", self.future + timedelta(hours=2), "Design Review"),
        ]
        options = {**self.options(), "title": "design review"}
        matches = await self.tool(tools.handle_calendar, options)
        self.assertEqual([m["event_id"] for m in matches["events"]], ["review-a", "review-b"])
        self.assertNotIn("preview_token", matches)
        selected = await self.preview("review-b", status_gifs=True)
        preview = selected["preview"]
        self.assertEqual(preview["time_zone"], "America/New_York")
        local_start = (self.future + timedelta(hours=2)).astimezone(ZoneInfo("America/New_York"))
        self.assertEqual(preview["start"], local_start.isoformat())
        self.assertIn("decision brief", preview["output"])
        self.assertEqual(self.created, [])
        args = {"preview_token": selected["preview_token"]}
        directive = tools.schedule_approval("meetstream_schedule_event", args, session_id=SESSION)
        self.assertEqual(directive["action"], "approve")
        for expected in ("Design Review", "America/New_York", "decision brief"):
            self.assertIn(expected, directive["message"])
        self.assertEqual(tools.schedule_approval("meetstream_schedule_event", args, session_id=OTHER)["action"], "block")
        blocked = await self.tool(tools.handle_schedule_event, args, session=OTHER)
        self.assertIn("invalid or expired", blocked["error"])
        saved = await self.tool(tools.handle_schedule_event, args)
        duplicate = await self.tool(tools.handle_schedule_event, args)
        self.assertEqual(saved["event"]["event_id"], "review-b")
        self.assertEqual(saved["meeting_status"], "Scheduled")
        self.assertEqual(saved["bot_id"], duplicate["bot_id"])
        self.assertTrue(duplicate["reused"])
        [payload] = self.created
        self.assertEqual(payload["join_at"], (self.future + timedelta(hours=2)).isoformat().replace("+00:00", "Z"))
        self.assertEqual(payload["custom_attributes"][api.EVENT_ATTR], "review-b")
        self.assertIn("transcript", payload["recording_config"])
        self.assertNotIn("recurring_event", payload)
        self.assertTrue(any(r.url.params.get("sync") == "true" for r in self.calls))
        self.assertEqual(tools.briefs.Briefs(self.home).status("scheduled-bot", SESSION), "Scheduled")

    async def test_hermes_native_approval_can_deny_before_dispatch(self):
        from hermes_cli.plugins import resolve_pre_tool_block

        self.event_records = [event("review", self.future, "Design Review")]
        selected = await self.preview("review")
        args = {"preview_token": selected["preview_token"]}

        def run_hooks(_hook, **kwargs):
            return [tools.schedule_approval(**kwargs)]

        with (mock.patch("hermes_cli.lifecycle.invoke_hook", side_effect=run_hooks),
              mock.patch("tools.approval.request_tool_approval", return_value={
                  "approved": False, "message": "The user denied the schedule.",
              }) as approve):
            result = resolve_pre_tool_block("meetstream_schedule_event", args, session_id=SESSION)
        self.assertIn("denied", result)
        self.assertIn("Design Review", approve.call_args.args[1])
        self.assertEqual(self.created, [])

    async def test_stale_changed_declined_or_existing_occurrences_cannot_schedule(self):
        original = event("review", self.future, "Design Review")
        self.event_records = [original]
        selected = await self.preview("review")
        args = {"preview_token": selected["preview_token"]}
        self.event_records = [event("review", self.future + timedelta(minutes=10), "Design Review")]
        self.assertIn("changed", (await self.tool(tools.handle_schedule_event, args))["error"])
        declined = {**original, "raw": {**original["raw"], "attendees": [{"self": True, "responseStatus": "declined"}]}}
        self.event_records = [declined]
        self.assertIn("declined", (await self.preview("review"))["error"])
        self.event_records = [{**original, "bots": [{"id": "existing", "status": "Scheduled"}]}]
        self.assertIn("already", (await self.preview("review"))["error"])
        self.event_records = [original]
        with mock.patch.object(tools.calendar.time, "time", return_value=datetime.now(UTC).timestamp() + 9999):
            self.assertIn("invalid or expired", (await self.tool(tools.handle_schedule_event, args))["error"])
        self.assertEqual(self.created, [])

    async def test_meeting_chat_cannot_read_calendar_or_schedule(self):
        for handler in (tools.handle_calendar, tools.handle_find_meetings, tools.handle_schedule_event):
            self.assertIn("saved private", (await self.tool(handler, self.options(), session="meeting"))["error"])
        self.assertEqual(self.calls, [])

    def test_day_bounds_handle_dst(self):
        bounds = tools.calendar.day_bounds(date(2026, 11, 1), date(2026, 11, 1), ZoneInfo("America/New_York"))
        self.assertEqual(bounds[1] - bounds[0], timedelta(hours=25))


    async def test_caption_only_calendar_event_can_schedule_recording_without_promising_a_brief(self):
        self.config["transcription"] = "meeting_captions"
        self.event_records = [event("review", self.future)]
        blocked = await self.preview("review")
        self.assertIn("error", blocked)
        self.assertNotIn("preview_token", blocked)
        allowed = await self.preview("review", decision_brief=False)
        self.assertIn("captions", allowed["preview"]["output"])

    async def test_search_uses_meetstream_epoch_start_and_creation_dates(self):
        self.bots = [
            {"BotID": "started", "Status": "Done", "BotUsername": "Hermes",
             "StartTime": int(self.past.timestamp()), "CreatedAt": 1},
            {"BotID": "created", "Status": "Done", "BotUsername": "Hermes",
             "CreatedAt": str(int(self.past.timestamp()))},
        ]
        result = await self.tool(tools.handle_find_meetings, self.options(self.past))
        self.assertEqual({item["bot_id"]: item["date_source"] for item in result["matches"]},
                         {"started": "meeting_start", "created": "bot_created"})

    @unittest.skipUnless(tools.messaging.capture_private_origin, "Hermes private delivery SDK is unavailable")
    async def test_telegram_calendar_search_and_approved_schedule_keep_the_original_route(self):
        with SessionDB(self.home / "state.db") as db:
            db.create_session("telegram-origin", source="telegram")
        self.event_records = [event("review", self.future, "Design Review")]
        args = {**self.options(), "title": "Design Review"}
        unbound = await self.tool(tools.handle_calendar, args, session="telegram-origin")
        self.assertIn("error", unbound)
        for chat_type in ("group", "dm"):
            tokens = set_session_vars(platform="telegram", chat_id="12345", chat_type=chat_type, user_id="12345",
                                      thread_id="7", session_key="bound", session_id="telegram-origin")
            try:
                found = await self.tool(tools.handle_calendar, args, session="telegram-origin")
                if chat_type == "group":
                    self.assertIn("error", found)
                    continue
                self.assertEqual(found["events"][0]["event_id"], "review")
                historical = await self.tool(tools.handle_find_meetings, self.options(self.past),
                                             session="telegram-origin")
                self.assertIn("matches", historical)
                preview = await self.tool(tools.handle_calendar, {**args, "event_id": "review"},
                                          session="telegram-origin")
                self.assertIn("this Telegram chat", preview["preview"]["output"])
                requested = {"preview_token": preview["preview_token"]}
                directive = tools.schedule_approval("meetstream_schedule_event", requested, session_id="telegram-origin")
                self.assertEqual(directive["action"], "approve")
                self.assertEqual(self.created, [])
                from hermes_cli.plugins import resolve_pre_tool_block

                with (mock.patch("hermes_cli.lifecycle.invoke_hook", return_value=[directive]),
                      mock.patch("tools.approval.request_tool_approval", return_value={"approved": True})):
                    self.assertIsNone(resolve_pre_tool_block("meetstream_schedule_event", requested,
                                                              session_id="telegram-origin"))
                result = await self.tool(tools.handle_schedule_event, requested, session="telegram-origin")
                self.assertEqual(result["meeting_status"], "Scheduled")
                ledger = tools.briefs.Briefs(self.home)
                with ledger.db() as db:
                    row = db.execute("SELECT origin FROM briefs WHERE bot_id = ?", (result["bot_id"],)).fetchone()
                origin = json.loads(row[0])
                self.assertEqual((origin["platform"], origin["chat_id"], origin["thread_id"]),
                                 ("telegram", "12345", "7"))
            finally:
                clear_session_vars(tokens)
        self.assertEqual(len(self.created), 1)
