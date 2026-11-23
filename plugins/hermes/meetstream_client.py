"""Small async client for the MeetStream REST API (https://docs.meetstream.ai).

Every call authenticates with the user's own key as ``Authorization: Token <key>``. Nothing here
logs request or response bodies above DEBUG: meeting chats and transcripts are user data.
"""

from __future__ import annotations

import base64
import logging
import re
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://api.meetstream.ai/api/v1"
BILLING_URL = "https://app.meetstream.ai/billing"  # where the account owner adds prepaid credits
TIMEOUT_S = 20.0
MAX_LIST_PAGES = 4
MAX_CHAT = 2000  # send_message rejects longer bodies (SendMessageRequest.maxLength)
JOIN_ATTR = "hermes_join_target"
BRIEF_TRANSCRIPTION_ATTR = "hermes_post_call_transcription"
GIF_ATTR = "hermes_status_gifs"
GIF_DURATION = 10
EVENT_ATTR = "hermes_calendar_event_id"
TITLE_ATTR = "hermes_meeting_title"
HERMES_ATTR = "hermes"  # custom attribute that marks a bot as one Hermes speaks through

# Meeting hosts MeetStream can join. Anything else is refused before a bot is billed.
MEETING_HOSTS = ("zoom.us", "zoom.com", "meet.google.com", "teams.microsoft.com", "teams.live.com")

# Bot lifecycle. Chat can be read and written only while the bot is in the call.
CHAT_READY = frozenset({"inmeeting", "recording", "recordingpermissionallowed"})
ENDED = frozenset({"stopped", "kicked", "notallowed", "denied", "error", "done", "failed",
                   "cancelled", "removed", "mediaexpired"})
JOIN_FINISHED = ENDED | {"mediaprocessing", "audioprocessing", "videoprocessing", "uploading", "transcriptionready"}
JOIN_FAILED = frozenset({"notallowed", "denied", "error", "failed", "cancelled", "recordingpermissiondenied"})

BRIEF_TRANSCRIPTION_PROVIDERS = frozenset({"meetstream", "deepgram", "assemblyai"})

TRANSCRIPTION_PROVIDERS = {
    "meetstream": {"meetstream": {"language": "auto", "translate": False}},
    "meeting_captions": {"meeting_captions": {}},
    "deepgram": {"deepgram": {"model": "nova-3", "language": "en", "diarize": True}},
    "assemblyai": {"assemblyai": {"speech_models": ["best"], "language_code": "en_us", "speaker_labels": True}},
    "none": None,
}

# Same safety timeouts as the MeetStream CLI and MCP server, so a bot never sits in an empty call.
AUTOMATIC_LEAVE = {
    "waiting_room_timeout": 300,
    "everyone_left_timeout": 60,
    "in_call_recording_timeout": 14400,
    "recording_permission_denied_timeout": 60,
}


class MeetStreamError(Exception):
    """A non-2xx answer from MeetStream (``status`` 0 means the request never got an answer)."""

    def __init__(self, status: int, detail: str):
        super().__init__(f"MeetStream HTTP {status}: {detail}" if status else detail)
        self.status = status
        self.detail = detail


def new_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT_S)


def _detail(resp: httpx.Response) -> str:
    try:
        data = resp.json()
    except ValueError:
        return resp.text[:200]
    if isinstance(data, dict):
        # MeetStream error bodies are {"message": ...}; older answers used "error" or "detail".
        for key in ("message", "error", "detail"):
            if data.get(key):
                return str(data[key])[:200]
    return str(data)[:200]


async def request(client: httpx.AsyncClient, key: str, method: str, path: str, *,
                  params: Optional[dict] = None, body: Optional[dict] = None,
                  idempotency_key: str = "", pending_as_none: bool = False) -> Any:
    if not key:
        raise MeetStreamError(0, "MEETSTREAM_API_KEY is not set (create one at https://app.meetstream.ai/api-key)")
    headers = {"Authorization": f"Token {key}", "Accept": "application/json"}
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    try:
        resp = await client.request(method, path, params=params, json=body, headers=headers)
    except httpx.HTTPError as e:
        raise MeetStreamError(0, f"MeetStream unreachable: {type(e).__name__}") from e
    logger.debug("MeetStream %s %s -> %s", method, path, resp.status_code)
    if pending_as_none and resp.status_code == 202:
        return None
    if idempotency_key and resp.status_code == 507:
        try:
            data = resp.json()
        except ValueError:
            data = None
        if not isinstance(data, dict) or not data.get("bot_id"):
            raise MeetStreamError(507, "MeetStream did not return the original bot ID")
        return {**data, "reused": True}
    if resp.status_code >= 400:
        detail = _detail(resp)
        retry_after = resp.headers.get("Retry-After", "").strip()
        if retry_after.isascii() and retry_after.isdecimal():
            detail += f" (retry after {retry_after} s)"
        raise MeetStreamError(resp.status_code, detail)
    if not resp.content:
        return {}
    try:
        return resp.json()
    except ValueError:
        return {"text": resp.text}


def field(record: dict, *names: str, default: Any = None) -> Any:
    """First present value among ``names``. List items come back in DynamoDB casing
    (``BotID``, ``Status``) while single-bot endpoints use snake_case (``bot_id``, ``status``)."""
    for name in names:
        value = record.get(name)
        if value not in (None, ""):
            return value
    return default


def norm_status(value: Any) -> str:
    return re.sub(r"[^a-z]", "", str(value or "").lower())


def bot_created_at(record: dict) -> float:
    value = field(record, "created_at", "CreatedAt")
    try:
        return float(value)
    except (TypeError, ValueError):
        try:
            return datetime.fromisoformat(str(value)).timestamp()
        except (ValueError, OverflowError, OSError):
            return 0.0


def validate_meeting_url(url: str) -> str:
    """The meeting link rebuilt from its parsed parts, so the host checked here is the host the bot
    opens. Raises ``ValueError`` for anything that is not a plain https Zoom / Meet / Teams link."""
    url = (url or "").strip()
    if not url or re.search(r"[\s\\\x00-\x1f\x7f]", url):
        raise ValueError("meeting_url must be an https:// Zoom, Google Meet or Microsoft Teams link")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not host or "@" in parsed.netloc:
        raise ValueError("meeting_url must be an https:// Zoom, Google Meet or Microsoft Teams link")
    if not any(host == h or host.endswith("." + h) for h in MEETING_HOSTS):
        raise ValueError(f"{host} is not a Zoom, Google Meet or Microsoft Teams host")
    if parsed.port not in (None, 443):
        raise ValueError("Meeting links must use the standard HTTPS port")
    rebuilt = f"https://{host}{parsed.path}"
    return rebuilt + (f"?{parsed.query}" if parsed.query else "") + (f"#{parsed.fragment}" if parsed.fragment else "")


_BOT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


def bot_path(bot_id: str, action: str = "") -> str:
    """``/bots/<id>[/action]`` for a well-formed bot id; ``ValueError`` otherwise (no path injection)."""
    bot_id = str(bot_id or "").strip()
    if not _BOT_ID_RE.fullmatch(bot_id):
        raise ValueError(f"invalid bot_id {bot_id[:40]!r}")
    return f"/bots/{bot_id}/{action}" if action else f"/bots/{bot_id}"


def build_join_payload(meeting_url: str, *, bot_name: str, message: str = "", join_at: str = "",
                       transcription: str = "meetstream", image_url: str = "") -> dict:
    payload: dict[str, Any] = {
        "meeting_link": validate_meeting_url(meeting_url),
        "bot_name": bot_name,
        "video_required": False,
        "custom_attributes": {
            HERMES_ATTR: True,
            BRIEF_TRANSCRIPTION_ATTR: transcription in BRIEF_TRANSCRIPTION_PROVIDERS,
        },
        "automatic_leave": dict(AUTOMATIC_LEAVE),
    }
    if message:
        payload["bot_message"] = message[:MAX_CHAT]
    if join_at:
        try:
            when = datetime.fromisoformat(join_at)
            if when.utcoffset() is None:
                raise ValueError
            payload["join_at"] = when.astimezone(UTC).isoformat().replace("+00:00", "Z")
        except (ValueError, OverflowError) as e:
            raise ValueError("join_at must be an ISO-8601 time with a timezone") from e
    if image_url:
        payload["bot_image_url"] = image_url
    if transcription not in TRANSCRIPTION_PROVIDERS:
        raise ValueError(f"transcription must be one of {', '.join(TRANSCRIPTION_PROVIDERS)}")
    provider = TRANSCRIPTION_PROVIDERS[transcription]
    if provider:
        payload["recording_config"] = {"transcript": {"provider": provider}}
    return payload


def chunks(text: str, size: int = MAX_CHAT) -> list[str]:
    """Split on paragraph, then line, then word boundaries so each part fits one chat message."""
    text = (text or "").strip()
    parts: list[str] = []
    while len(text) > size:
        cut = max(text.rfind("\n\n", 0, size), text.rfind("\n", 0, size), text.rfind(" ", 0, size))
        cut = cut if cut > size // 2 else size
        parts.append(text[:cut].rstrip())
        text = text[cut:].lstrip()
    if text:
        parts.append(text)
    return parts


def _norm_name(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().lower()


def is_hermes_bot(record: dict, bot_name: str) -> bool:
    """A bot Hermes speaks through: tagged ``hermes: true`` by ``meetstream_join``, or named like the
    Hermes bot. The name rule covers calendar auto-join, which replaces ``custom_attributes`` with
    its own scheduling metadata, so a tag set in the default bot config does not survive."""
    attrs = field(record, "custom_attributes", "CustomAttributes", default={}) or {}
    value = attrs.get(HERMES_ATTR) if isinstance(attrs, dict) else None
    if value is True or str(value).lower() == "true":
        return True
    name = _norm_name(field(record, "bot_username", "BotUsername", "bot_name"))
    return bool(name) and name == _norm_name(bot_name)


# -- Endpoints -------------------------------------------------------------------------------------

def meeting_identity(url: str) -> str:
    parsed = urlparse(url)
    if parsed.netloc == "meet.google.com" and re.fullmatch(r"/[a-z]{3}-[a-z]{4}-[a-z]{3}/?", parsed.path):
        # Google Meet's sharing and account-selection parameters do not change the room code.
        url = f"https://meet.google.com{parsed.path.rstrip('/')}"
    return url


def _join_target(payload: dict) -> str:
    url = meeting_identity(payload["meeting_link"])
    return sha256(f"{url}\n{payload.get('join_at', '')}".encode()).hexdigest()


async def create_bot(client, key, payload: dict) -> dict:
    target = _join_target(payload)
    params = {f"custom_attr[{JOIN_ATTR}]": target, "limit": 50}
    previous: tuple[float, str] = (float("-inf"), "")
    async for records, more in bot_pages(client, key, params):
        for record in records:
            attrs = field(record, "custom_attributes", "CustomAttributes", default={})
            bot_id = field(record, "bot_id", "BotID")
            if not bot_id or not isinstance(attrs, dict) or attrs.get(JOIN_ATTR) != target:
                continue
            status = field(record, "status", "Status")
            if norm_status(status) not in JOIN_FINISHED:
                return {"bot_id": bot_id, "status": status, "reused": True, "custom_attributes": attrs}
            previous = max(previous, (bot_created_at(record), str(bot_id)))
    if more:
        raise MeetStreamError(0, "Could not verify whether a bot is already in this meeting. Try again later.")

    # Concurrent callers seeing the same prior bot use the same retry key. When that bot has
    # finished, its ID makes the next occurrence use a fresh key even for a recurring link.
    retry_key = f"hermes:{target}:{previous[1] or 'first'}"
    body = {**payload, "custom_attributes": {**payload["custom_attributes"], JOIN_ATTR: target}}
    for _ in range(MAX_LIST_PAGES):
        result = await request(client, key, "POST", "/bots/create_bot", body=body, idempotency_key=retry_key)
        if not isinstance(result, dict):
            raise MeetStreamError(0, "MeetStream returned an unexpected join response. Check bot status before retrying.")
        if not result.get("reused") or norm_status(result.get("status")) not in JOIN_FINISHED:
            return result
        # The create endpoint can see an ended bot before it is visible in the list.
        retry_key = f"hermes:{target}:{result['bot_id']}"
    raise MeetStreamError(0, "MeetStream's bot list is catching up. Try the join again shortly.")


async def bot_status(client, key, bot_id: str) -> dict:
    return await request(client, key, "GET", bot_path(bot_id, "status"))


async def bot_detail(client, key, bot_id: str) -> dict:
    return await request(client, key, "GET", bot_path(bot_id, "detail"))


async def list_bots(client, key, params: Optional[dict] = None) -> dict:
    return await request(client, key, "GET", "/bots", params=params)


async def bot_pages(client, key, params: dict):
    seen_cursors = set()
    for _ in range(MAX_LIST_PAGES):
        data = await list_bots(client, key, params)
        records = data.get("bots") if isinstance(data, dict) else None
        if not isinstance(records, list) or any(not isinstance(row, dict) for row in records):
            raise MeetStreamError(0, "MeetStream returned an unexpected bot list. Try again later.")
        more = bool(data.get("hasNextPage"))
        yield records, more
        if not more:
            return
        cursor = data.get("nextCursor")
        if not isinstance(cursor, str) or not cursor or cursor in seen_cursors:
            raise MeetStreamError(0, "MeetStream bot list did not provide a fresh cursor")
        seen_cursors.add(cursor)
        params = {**params, "cursor": cursor}


async def get_chats(client, key, bot_id: str) -> list[dict] | None:
    """Return None while MeetStream is still assembling the post-call chat artifact."""
    data = await request(client, key, "GET", bot_path(bot_id, "get_chats"), pending_as_none=True)
    if data is None:
        return None
    if not isinstance(data, dict):
        raise MeetStreamError(0, "MeetStream returned an unexpected chat response")
    return [m for m in (data.get("chatMessages") or []) if isinstance(m, dict)]


async def send_message(client, key, bot_id: str, text: str) -> dict:
    return await request(client, key, "POST", bot_path(bot_id, "send_message"), body={"message": text[:MAX_CHAT]})


async def send_status_gif(client, key: str, bot_id: str, state: str, *, base_url: str = "") -> dict:
    name = {
        "thinking": "hermes-agent-thinking.gif",
        "activity": "hermes-agent-nous-research.gif",
        "working": "hermes-agent-working.gif",
    }[state]
    if base_url:
        parsed = urlparse(base_url)
        if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
                or parsed.query or parsed.fragment or parsed.params):
            raise ValueError("The status GIF base URL must be a public HTTPS directory without credentials or query parameters.")
        image = {"img_url": base_url.rstrip("/") + "/" + name}
    else:
        data = (Path(__file__).resolve().parent / "assets" / name).read_bytes()
        image = {"img": base64.b64encode(data).decode("ascii")}
    return await request(client, key, "POST", bot_path(bot_id, "send_image"),
                         body={**image, "display_duration": GIF_DURATION})


async def remove_bot(client, key, bot_id: str) -> dict:
    return await request(client, key, "GET", bot_path(bot_id, "remove_bot"))


async def verify_reused_transcription(client, key, bot: dict) -> bool | None:
    """Read the original bot's metadata, using a transcript ID as evidence for older bots."""
    bot_id = bot["bot_id"]
    attrs = bot.get("custom_attributes")
    if not isinstance(attrs, dict) or BRIEF_TRANSCRIPTION_ATTR not in attrs:
        status = await bot_status(client, key, bot_id)
        attrs = status.get("custom_attributes") if isinstance(status, dict) else None
    enabled = attrs.get(BRIEF_TRANSCRIPTION_ATTR) if isinstance(attrs, dict) else None
    if isinstance(enabled, bool):
        return enabled
    tid = _transcript_id(await bot_detail(client, key, bot_id))
    return True if tid and _BOT_ID_RE.fullmatch(str(tid)) else None


def _transcript_id(detail: Any):
    if not isinstance(detail, dict):
        return None
    bot = detail.get("bot_details")
    nested = field(bot, "transcript_id") if isinstance(bot, dict) else None
    return nested or field(detail, "transcript_id")


async def transcript(client, key, bot_id: str) -> tuple[Optional[str], Any]:
    """Return a readable transcript, preferring the bot's primary transcript."""
    tid = _transcript_id(await bot_detail(client, key, bot_id))
    if tid:
        segments = await _read_transcript(client, key, bot_id, tid)
        if segments is not None:
            return tid, segments

    listing = await request(client, key, "GET", bot_path(bot_id, "transcriptions"))
    runs = listing.get("transcriptions", []) if isinstance(listing, dict) else []
    runs = [row for row in runs or [] if isinstance(row, dict) and isinstance(row.get("transcript_id"), str)
            and _BOT_ID_RE.fullmatch(row["transcript_id"])]
    # Media processing may finish while the original run is stuck. A completed post-call
    # re-transcription has its own ID and may be readable even while the primary returns 202.
    done = [row["transcript_id"] for row in runs
            if str(row.get("status", "")).strip().casefold() in {"success", "completed"}
            and row["transcript_id"] != tid]
    for candidate in list(dict.fromkeys(done))[:MAX_LIST_PAGES]:
        recovered = await _read_transcript(client, key, bot_id, candidate)
        if recovered is not None:
            return candidate, recovered
    if tid or done:
        return tid or done[0], None
    first = runs[0]["transcript_id"] if runs else None
    return first, await _read_transcript(client, key, bot_id, first)


async def _read_transcript(client, key, bot_id: str, tid: str | None) -> Any:
    if tid:
        if not _BOT_ID_RE.fullmatch(str(tid)):
            raise MeetStreamError(0, "MeetStream returned a malformed transcript_id")
        path = f"/transcript/{tid}/get_transcript"
    else:
        path = bot_path(bot_id, "get_transcript")
    try:
        data = await request(client, key, "GET", path, pending_as_none=True)
    except MeetStreamError as e:
        if e.status == 404 or (e.status == 409 and "session billing is still in progress" in e.detail.casefold()):
            return None
        raise
    return data.get("message") if isinstance(data, dict) and isinstance(data.get("message"), list) else data
