"""Read recent meeting metadata and resolve individual synced calendar occurrences."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import time
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta, tzinfo
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from . import briefs
from . import meetstream_client as api

RESULT_LIMIT = 20
PREVIEW_TTL = 600
UNSUCCESSFUL_BOT = api.JOIN_FAILED | {"mediaexpired"}


def mapping(value) -> dict:
    return value if isinstance(value, dict) else {}


def rows(value) -> list[dict]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def label(value) -> str:
    return " ".join(value.split())[:200] if isinstance(value, str) else ""


def parse_date(value: str) -> date:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("Use a calendar date in YYYY-MM-DD format.")
    return date.fromisoformat(value)


def parse_time(value) -> datetime | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        if isinstance(value, str) and "T" in value:
            parsed = datetime.fromisoformat(value)
            return parsed if parsed.utcoffset() is not None else None
        epoch = float(value)
        return datetime.fromtimestamp(epoch, UTC) if epoch > 0 else None
    except (ValueError, TypeError, OverflowError, OSError):
        return None


def day_bounds(first: date, last: date, zone: tzinfo | None) -> tuple[datetime, datetime]:
    start = datetime.combine(first, datetime.min.time(), zone)
    end = datetime.combine(last + timedelta(days=1), datetime.min.time(), zone)
    return start.astimezone(UTC), end.astimezone(UTC)


def timezone_for(name: str = "") -> tzinfo | None:
    if not name:
        from hermes_cli.config import load_config_readonly

        name = str(load_config_readonly().get("timezone") or "").strip()
        if not name:
            return None
    try:
        return ZoneInfo(name)
    except (ValueError, ZoneInfoNotFoundError) as exc:
        raise ValueError("Use an IANA time zone such as America/New_York or Asia/Kolkata.") from exc


def title_matches(query: str, title: str) -> bool:
    if not query:
        return True
    query_words = set(re.findall(r"[^\W_]+", query.casefold()))
    return bool(query_words) and query_words.issubset(re.findall(r"[^\W_]+", title.casefold()))


@dataclass(frozen=True)
class Event:
    event_id: str
    title: str
    start: datetime
    end: datetime | None
    calendar_id: str
    timezone: str
    meeting_url: str
    blocked: str
    bots: list[dict]

    def metadata(self) -> dict:
        return {
            "event_id": self.event_id,
            "title": self.title,
            "start": self.start.isoformat(),
            "end": self.end.isoformat() if self.end else None,
            "time_zone": self.timezone,
            "calendar": self.calendar_id,
        }

    def scheduled_bot(self) -> str | None:
        for bot in self.bots:
            state = api.norm_status(api.field(bot, "status", "Status"))
            if state in (api.JOIN_FINISHED | UNSUCCESSFUL_BOT):
                continue
            if state == "scheduled" or bot.get("is_scheduled") is True or state in api.CHAT_READY | {
                "joining", "active", "inwaitingroom"
            }:
                return str(api.field(bot, "id", "bot_id", "BotID") or "")
        return None


def parse_event(row: dict) -> Event | None:
    raw = mapping(row.get("raw"))
    start = parse_time(row.get("start_time"))
    if not start or not isinstance(row.get("id"), str) or not row["id"] or len(row["id"]) > 256:
        return None
    if (row.get("is_deleted") is True or raw.get("isCancelled") is True
            or api.norm_status(raw.get("status")) in {"cancelled", "canceled"}):
        return None
    title = label(raw.get("summary") or raw.get("subject") or row.get("title") or row.get("summary"))
    zone_name = label(mapping(raw.get("start")).get("timeZone") or raw.get("originalStartTimeZone")
                      or row.get("timezone"))
    end = parse_time(row.get("end_time"))
    if zone_name:
        try:
            zone = ZoneInfo(zone_name)
        except (ValueError, ZoneInfoNotFoundError):
            zone = None
        if zone:
            start = start.astimezone(zone)
            end = end.astimezone(zone) if end else None
        else:
            zone_name = ""
    zone_name = zone_name or ("UTC" if start.utcoffset() == timedelta(0) else f"UTC{start:%z}")
    blocked = ""
    outlook_reply = mapping(raw.get("responseStatus")).get("response")
    if api.norm_status(outlook_reply) == "declined" or any(
        item.get("self") is True and api.norm_status(item.get("responseStatus")) == "declined"
        for item in rows(raw.get("attendees"))
    ):
        blocked = "You declined this calendar occurrence."
    elif mapping(raw.get("start")).get("date") or raw.get("isAllDay") is True:
        blocked = "This is an all-day event."
    try:
        url = api.validate_meeting_url(row["meeting_url"]) if isinstance(row.get("meeting_url"), str) else ""
    except ValueError:
        url = ""
    if not url and not blocked:
        blocked = "This event has no supported meeting link."
    return Event(row["id"], title or "(Untitled calendar event)", start, end, label(row.get("calendar_id")),
                 zone_name, url, blocked, rows(row.get("bots")))


async def calendar_events(client, key: str, start: datetime, end: datetime, *,
                          sync: bool = False) -> tuple[list[Event], bool]:
    params = {"time_min": start.isoformat(), "time_max": end.isoformat(), "limit": 100}
    if sync:
        params["sync"] = "true"
    seen = set()
    events: dict[str, Event] = {}
    for _ in range(api.MAX_LIST_PAGES):
        data = await api.request(client, key, "GET", "/calendar/events", params=params)
        if not isinstance(data, dict) or not isinstance(data.get("results"), list):
            raise api.MeetStreamError(0, "MeetStream returned an unexpected calendar response.")
        for item in rows(data["results"]):
            event = parse_event(item)
            if event and start <= event.start < end:
                events[event.event_id] = event
        cursor = data.get("next")
        if not cursor and not data.get("has_more"):
            return list(events.values()), False
        if not isinstance(cursor, str) or not cursor or cursor in seen:
            raise api.MeetStreamError(0, "MeetStream did not provide a fresh calendar cursor.")
        seen.add(cursor)
        params = {key: value for key, value in params.items() if key != "sync"}
        params["cursor"] = cursor
    return list(events.values()), True


def is_google_meet(url: str) -> bool:
    return urlsplit(url).hostname == "meet.google.com"


def infer_occurrence(bot: dict, events_by_link: dict[str, list[Event]]) -> Event | None:
    """Associate older ad-hoc bots only when one occurrence matches the room and actual start."""
    at = parse_time(api.field(bot, "start_time", "StartTime", "StartedAt"))
    url = api.field(bot, "meeting_url", "MeetingURL", "MeetingLink")
    if not at or not isinstance(url, str):
        return None
    try:
        key = api.meeting_identity(api.validate_meeting_url(url))
    except ValueError:
        return None
    matches = [event for event in events_by_link.get(key, ())
               if abs((event.start.astimezone(UTC) - at).total_seconds()) <= 10 * 60]
    return matches[0] if len(matches) == 1 else None


def bot_metadata(row: dict, event: Event | None, zone: tzinfo | None, *, calendar_attachment: bool = False) -> dict:
    attrs = mapping(api.field(row, "custom_attributes", "CustomAttributes"))
    state = api.norm_status(api.field(row, "status", "Status"))
    result = event.metadata() if event else {
        "title": label(attrs.get(api.TITLE_ATTR) or api.field(row, "meeting_title", "MeetingTitle", "title")),
        "event_id": None,
    }
    if event is None:
        for fields, source in (
            (("start_time", "StartTime", "StartedAt"), "meeting_start"),
            (("scheduled_join_time", "ScheduledJoinTime", "join_at"), "scheduled_start"),
            (("created_at", "CreatedAt"), "bot_created"),
        ):
            at = parse_time(api.field(row, *fields))
            if at:
                result.update(start=at.astimezone(zone).isoformat(), date_source=source)
                break
    else:
        result["date_source"] = "calendar_occurrence"
    result.update(
        bot_id=api.field(row, "bot_id", "BotID", "id"),
        meeting_status=briefs.meeting_status(state),
        platform=api.field(row, "platform", "Platform"),
        calendar_recording=calendar_attachment,
    )
    return result


def plan_token(key: str, session_id: str, data: dict) -> str:
    body = base64.urlsafe_b64encode(json.dumps(data, sort_keys=True, separators=(",", ":")).encode()).decode()
    mac = hmac.digest(key.encode(), f"meetstream.calendar.v1\n{session_id}\n{body}".encode(), "sha256")
    return f"{body}.{mac.hex()}"


def read_plan(key: str, session_id: str, token: str) -> dict:
    error = "This scheduling preview is invalid or expired for this chat. Preview the event again."
    try:
        if not isinstance(token, str) or len(token) > 4096:
            raise ValueError(error)
        body, _ = token.split(".", 1)
        plan = json.loads(base64.b64decode(body, altchars=b"-_", validate=True))
        if (isinstance(plan, dict)
                and hmac.compare_digest(plan_token(key, session_id, plan), token)
                and plan["expires"] >= time.time()):
            return plan
    except (KeyError, TypeError, ValueError):
        pass
    raise ValueError(error)


def event_revision(event: Event) -> str:
    snapshot = {**event.metadata(), "meeting_url": event.meeting_url}
    return hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode()).hexdigest()
