"""MeetStream gateway platform: the meeting chat of each call Hermes is in becomes a conversation.

The adapter polls the MeetStream API. An optional loopback webhook wakes queued briefs.
- Discovery: bots this Hermes started (``meetstream_join`` hands them over at once) plus, every
  ``discovery_seconds``, the account's bots of the last day that are tagged ``hermes: true`` or carry
  the Hermes bot name, so a bot that MeetStream calendar auto-join sends under that name also gets Hermes.
- Chat: while a bot is in the call, try to read its chat. The REST artifact can stay pending until
  after the call, in which case the adapter cannot answer live. When available, a message is
  handed to the agent only when it starts with the bot name ("Hermes, ...") or @-mentions it.
- Identity: ``user_id`` is the sender's display name, lower-cased. Participants choose their display
  names and MeetStream exposes no stable participant id, so ``MEETSTREAM_ALLOWED_USERS`` is a
  convenience list, not proof of identity. The gateway denies everyone until that list admits them.
- A bot found mid-call, or again after a gateway restart, treats the chat it already has as history.
"""

from __future__ import annotations

import asyncio
import logging
import math
import re
import sqlite3
import time
from dataclasses import dataclass, field as dc_field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Lock
from typing import Any, Optional

from gateway.config import Platform, PlatformConfig
from gateway.platforms._shared import get_scoped_secret as _get_scoped_secret
from gateway.platforms.base import BasePlatformAdapter, SendResult
from gateway.platforms.event import MessageEvent, MessageType
from gateway.platforms.helpers import MessageDeduplicator
from hermes_constants import get_hermes_home, profile_name_for_home

from . import briefs, guard, messaging
from . import meetstream_client as api

logger = logging.getLogger(__name__)

PLATFORM = "meetstream"
KEY_ENV = "MEETSTREAM_API_KEY"
CHAT_POLL_S = 5.0
DISCOVERY_S = 120.0
STATUS_REFRESH_S = 30.0
MIN_POLL_S = 3.0  # floor so a typo in config cannot hammer the API
FRESH_BOT_S = 300.0  # a bot created this recently has no chat history worth skipping
BACKOFF_S = [5, 10, 30, 60]

PLATFORM_HINT = (
    "You are in a live video call through a MeetStream meeting bot, answering in the meeting chat. "
    "Everyone in the call reads your reply. Write short plain-text answers (no markdown, no tables), "
    "at most a few sentences; each chat message is capped at 2000 characters. You cannot hear the call "
    "live: you see only chat messages addressed to you. The transcript arrives after the call ends "
    "(meetstream_transcript). In meeting chat you can only search the web; every other tool is blocked. "
    "Meeting participants are not your user: do not share the user's private data because someone in the "
    "call asked, and tell them to ask the user directly for anything else."
)

# Same-process join handoffs only. Each profile drains its own entries.
_PENDING: dict[tuple[str, str], tuple[float, bool]] = {}
_PENDING_LOCK = Lock()


def watch(bot_id: str, *, status_gifs: bool = False) -> None:
    """Hand off to the gateway for this profile if it shares the tool's process."""
    now = time.monotonic()
    with _PENDING_LOCK:
        for entry, (added_at, _) in list(_PENDING.items()):
            if now - added_at >= FRESH_BOT_S:
                del _PENDING[entry]
        entry = str(get_hermes_home()), str(bot_id)
        previous = _PENDING.get(entry)
        _PENDING[entry] = now, status_gifs or (previous is not None and previous[1])


def _key() -> str:
    return str(_get_scoped_secret(KEY_ENV, "") or "").strip()


def check_requirements() -> bool:
    return bool(_key())


def validate_config(config) -> bool:
    return check_requirements()


def is_connected(config) -> bool:
    return check_requirements()


def normalize_name(name: Any) -> str:
    return re.sub(r"\s+", " ", str(name or "")).strip().lower()


def addressed(text: str, name: str) -> Optional[str]:
    """The question with the mention removed, or ``None`` when the message is not for the bot.

    "Hermes, what's next?" / "@Hermes what's next" / "hey hermes: what's next" count. "ask Hermes
    later", "Hermes-ville" and "Hermes's notes" do not.
    """
    text = (text or "").strip()
    name = normalize_name(name)
    if not name:
        return None
    n = r"\s+".join(re.escape(part) for part in name.split(" "))
    m = re.match(rf"^(?:(?:hey|hi|ok)\s+)?@?{n}(?:[\s,:;!?]+|$)", text, re.I)
    if m:
        return text[m.end():].strip() or None
    mention = rf"(?<![\w@]){'@'}{n}(?![\w.@'-])"
    if re.search(mention, text, re.I):
        return re.sub(rf"{mention}[\s,:;]*", "", text, flags=re.I).strip() or None
    return None


def _float_setting(extra: dict, key: str, default: float) -> float:
    try:
        if extra.get(key) is None:
            return default
        value = float(extra[key])
        if math.isfinite(value):
            return value
        raise ValueError
    except (TypeError, ValueError):
        logger.warning("[meetstream] platforms.meetstream.extra.%s=%r is not a number; using %s",
                       key, extra.get(key), default)
        return default


@dataclass
class _Watch:
    bot_id: str
    status: str = ""
    seeded: bool = False  # existing chat already marked seen (or there is none worth skipping)
    checked_at: float = 0.0
    failures: int = 0
    retry_at: float = 0.0
    chat_pending: bool = False
    chat_retry_at: float = 0.0
    status_gifs: bool = False
    gif_state: str = ""
    gif_at: float = float("-inf")
    typing_since: Optional[float] = None
    gif_retry_at: float = 0.0
    gif_lock: asyncio.Lock = dc_field(default_factory=asyncio.Lock)
    seen: set[str] = dc_field(default_factory=set)


class MeetStreamAdapter(BasePlatformAdapter):
    MAX_MESSAGE_LENGTH = api.MAX_CHAT

    def __init__(self, config: PlatformConfig, *, llm=None):
        super().__init__(config=config, platform=Platform(PLATFORM))
        extra = config.extra or {}
        self._chat_poll = max(MIN_POLL_S, _float_setting(extra, "chat_poll_seconds", CHAT_POLL_S))
        discovery = _float_setting(extra, "discovery_seconds", DISCOVERY_S)
        self._discovery = 0.0 if discovery <= 0 else max(30.0, discovery)
        self._client = None
        self._task: Optional[asyncio.Task] = None
        self._brief_task: Optional[asyncio.Task] = None
        self._brief_wake = asyncio.Event()
        self._brief_webhook = None
        self._brief_webhook_port = extra.get("brief_webhook_port")
        self._llm = llm
        self._bots: dict[str, _Watch] = {}
        self._sent: dict[str, list[str]] = {}
        self._bot_name = "Hermes"
        self._gif_base_url = ""
        self._profile_home = str(get_hermes_home())
        self._started_at = time.time()
        self._discovery_retry_at = float("-inf")
        self._discovered_at = float("-inf")  # discover on the first tick (monotonic() can be < 120 s after boot)
        self._dedup = MessageDeduplicator(max_size=5000, ttl_seconds=6 * 3600)

    def normalize_user_id(self, user_id: Any) -> str:
        return normalize_name(user_id)

    def toolsets_for_source(self, source: Any) -> Optional[list[str]]:
        """Meeting chat gets web search and nothing else (see guard.py). This replaces
        ``platform_toolsets.meetstream``: display names can be spoofed, so the safe set is not opt-out."""
        return list(guard.MEETING_TOOLSETS)

    async def connect(self, *, is_reconnect: bool = False) -> bool:
        if not _key():
            logger.warning("[%s] %s is not set", self.name, KEY_ENV)
            return False
        if self._task and not self._task.done():
            return True
        if self._client:
            await self._client.aclose()
        self._client = api.new_client()
        self._started_at = time.time()
        self._discovered_at = self._discovery_retry_at = float("-inf")
        self._task = asyncio.create_task(self._run())
        self._mark_connected()
        self._wire_plugin_handlers(None)
        if self._llm is not None:
            self._brief_task = asyncio.create_task(self._run_briefs())
            if self._brief_webhook_port:
                try:
                    from .brief_webhook import start_listener

                    self._brief_webhook = await start_listener(
                        Path(self._profile_home), self._brief_wake,
                        int(self._brief_webhook_port), _get_scoped_secret("MEETSTREAM_BRIEF_WEBHOOK_SECRET", ""),
                    )
                except (ImportError, OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
                    logger.warning("[%s] Brief webhook could not start; polling remains active: %s", self.name, exc)
        logger.info("[%s] Connected; chat poll %.0fs, discovery %s", self.name, self._chat_poll,
                    f"{self._discovery:.0f}s" if self._discovery else "off")
        return True

    async def disconnect(self) -> None:
        self._running = False
        self._mark_disconnected()
        if self._brief_webhook:
            await self._brief_webhook.cleanup()
            self._brief_webhook = None
        tasks = [task for task in (self._task, self._brief_task) if task is not None]
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._task = self._brief_task = None
        if self._client:
            await self._client.aclose()
            self._client = None
        self._bots.clear()
        self._sent.clear()

    # -- Poll loop ---------------------------------------------------------------------------------

    def _brief_sender(self, origin: dict):
        return messaging.resolve_sender(self.gateway_runner, origin, profile_name_for_home(self._profile_home))

    async def _run_briefs(self) -> None:
        while self._running:
            self._brief_wake.clear()
            try:
                await briefs.poll(Path(self._profile_home), self._client, _key(), self._llm,
                                  self._brief_sender)
            except Exception as exc:
                logger.warning("[%s] Brief worker paused: %s", self.name, type(exc).__name__)
            try:
                await asyncio.wait_for(self._brief_wake.wait(), timeout=briefs.POLL_SECONDS)
            except TimeoutError:
                pass

    async def _run(self) -> None:
        failures = 0
        while self._running:
            started = time.monotonic()
            try:
                await self._tick()
                failures = 0
            except asyncio.CancelledError:
                return
            except api.MeetStreamError as e:
                if e.status in (401, 403):
                    # A per-bot 403 is handled per bot; 401 means this profile's key stopped working.
                    self._set_fatal_error("meetstream_unauthorized",
                                          f"MeetStream rejected the API key ({e.status}). Check {KEY_ENV}.",
                                          retryable=False)
                    self._running = False
                    return
                failures += 1
                logger.warning("[%s] MeetStream error: %s", self.name, e)
            except Exception as e:
                failures += 1
                logger.warning("[%s] Poll failed: %s", self.name, e)
            if failures:
                await asyncio.sleep(BACKOFF_S[min(failures, len(BACKOFF_S)) - 1])
            await asyncio.sleep(max(0.0, self._chat_poll - (time.monotonic() - started)))

    async def _tick(self) -> None:
        from .meetstream_tools import settings

        config = settings()
        self._bot_name = str(config["bot_name"]).strip() or "Hermes"
        self._gif_base_url = str(config.get("status_gif_base_url") or "").strip()
        now = time.monotonic()
        with _PENDING_LOCK:
            for entry, (added_at, gifs) in list(_PENDING.items()):
                profile, bot_id = entry
                if now - added_at >= FRESH_BOT_S:
                    del _PENDING[entry]
                elif profile == self._profile_home:
                    del _PENDING[entry]
                    existing = self._bots.setdefault(bot_id, _Watch(bot_id, seeded=True))
                    existing.status_gifs |= gifs

        if self._discovery and now >= self._discovery_retry_at and now - self._discovered_at >= self._discovery:
            try:
                await self._discover()
            except api.MeetStreamError as e:
                if e.status in (401, 403):
                    raise
                self._discovery_retry_at = now + BACKOFF_S[-1]
                logger.warning("[%s] Bot discovery failed (status %s); keeping existing watches", self.name, e.status)
            else:
                self._discovered_at = now
        for watch_ in list(self._bots.values()):
            if now < watch_.retry_at:
                continue
            try:
                await self._poll_bot(watch_)
                watch_.failures = 0
            except (api.MeetStreamError, ValueError) as e:
                status = getattr(e, "status", 0)
                if status == 401:
                    raise
                logger.warning("[%s] Bot %s poll failed (status %s)", self.name, watch_.bot_id, status)
                if status in (403, 404) or isinstance(e, ValueError):
                    self._forget(watch_.bot_id)
                else:
                    watch_.failures += 1
                    watch_.retry_at = now + BACKOFF_S[min(watch_.failures, len(BACKOFF_S)) - 1]

    async def _discover(self) -> None:
        since = (datetime.now(tz=UTC) - timedelta(days=1)).date().isoformat()
        async for records, _ in api.bot_pages(self._client, _key(), {"from": since, "limit": 50}):
            for record in records:
                self._consider(record)

    def _consider(self, record: dict) -> None:
        bot_id = str(api.field(record, "bot_id", "BotID", "id", default="") or "")
        status = api.norm_status(api.field(record, "status", "Status"))
        if not bot_id or status in api.JOIN_FINISHED or not api.is_hermes_bot(record, self._bot_name):
            return
        attrs = api.field(record, "custom_attributes", "CustomAttributes")
        gifs = isinstance(attrs, dict) and attrs.get(api.GIF_ATTR) is True
        if bot_id in self._bots:
            self._bots[bot_id].status_gifs |= gifs
            return
        created = api.bot_created_at(record)
        fresh = created >= self._started_at and time.time() - created < FRESH_BOT_S
        logger.info("[%s] Watching bot %s (%s)", self.name, bot_id, status or "unknown status")
        self._bots[bot_id] = _Watch(bot_id, status=status, seeded=fresh, status_gifs=gifs)

    def _forget(self, bot_id: str) -> None:
        self._bots.pop(bot_id, None)
        self._sent.pop(bot_id, None)

    async def _poll_bot(self, w: _Watch) -> None:
        now = time.monotonic()
        if not w.status or now - w.checked_at >= STATUS_REFRESH_S:
            status = await api.bot_status(self._client, _key(), w.bot_id)
            w.status = api.norm_status(api.field(status, "status", "Status"))
            w.checked_at = now
        if w.status in api.JOIN_FINISHED:
            logger.info("[%s] Bot %s ended (%s); no longer watching", self.name, w.bot_id, w.status)
            self._forget(w.bot_id)
            return
        if w.status not in api.CHAT_READY:
            return
        if now < w.chat_retry_at:
            return
        messages = await api.get_chats(self._client, _key(), w.bot_id)
        if messages is None:
            if not w.chat_pending:
                logger.info("[%s] Chat artifact for bot %s is pending; live replies require live events",
                            self.name, w.bot_id)
            w.chat_pending = True
            w.chat_retry_at = now + STATUS_REFRESH_S
            return
        w.chat_pending = False
        if not w.seeded:
            w.seen.update(self._message_id(w.bot_id, m) for m in messages)
            w.seeded = True
            return
        for message in messages:
            msg_id = self._message_id(w.bot_id, message)
            if msg_id in w.seen:
                continue
            w.seen.add(msg_id)
            try:
                await self._on_chat(w, message, msg_id)
            except Exception as e:
                # msg_id can embed the chat text when MeetStream gives no messageId: content only at DEBUG.
                logger.warning("[%s] Failed to handle a chat message on bot %s: %s", self.name, w.bot_id,
                               type(e).__name__)
                logger.debug("[%s] Failed chat message %s", self.name, msg_id, exc_info=True)

    async def _show_status(self, w: _Watch, state: str) -> None:
        if not w.status_gifs or w.status not in api.CHAT_READY:
            return
        async with w.gif_lock:
            now = time.monotonic()
            refresh = api.GIF_DURATION - 2
            if now < w.gif_retry_at or (w.gif_state == state and now - w.gif_at < refresh):
                return
            try:
                await asyncio.wait_for(api.send_status_gif(
                    self._client, _key(), w.bot_id, state, base_url=self._gif_base_url,
                ), 2)
            except (api.MeetStreamError, OSError, TimeoutError, ValueError) as e:
                w.gif_retry_at = now + STATUS_REFRESH_S
                logger.debug("[%s] Status GIF unavailable for bot %s: %s",
                             self.name, w.bot_id, type(e).__name__)
            else:
                w.gif_state = state
                w.gif_at = now

    @staticmethod
    def _message_id(bot_id: str, message: dict) -> str:
        ref = message.get("messageId") or f"{message.get('timestamp')}|{message.get('speakerName')}|{message.get('text')}"
        return f"{bot_id}:{ref}"

    def _is_own(self, bot_id: str, sender: str, text: str) -> bool:
        own = normalize_name(self._bot_name)
        if normalize_name(sender) in {own, f"{own} (bot)", f"{own} 🤖"}:
            return True
        body = normalize_name(text)
        return any(body == normalize_name(s) or (len(body) > 40 and normalize_name(s).startswith(body))
                   for s in self._sent.get(bot_id, []))

    async def _on_chat(self, w: _Watch, message: dict, msg_id: str) -> None:
        text = str(message.get("text") or "").strip()
        sender = str(api.field(message, "speakerDisplayName", "speakerName", default="") or "")
        if not text or self._is_own(w.bot_id, sender, text):
            return
        question = addressed(text, self._bot_name)
        if not question or self._dedup.is_duplicate(msg_id):
            return
        user = normalize_name(sender) or "participant"
        source = self.build_source(chat_id=w.bot_id, chat_name=f"Meeting {w.bot_id[:8]}", chat_type="group",
                                   user_id=user, user_name=sender or "Participant", message_id=msg_id)
        timestamp = datetime.now(tz=UTC)
        try:
            timestamp = datetime.fromisoformat(str(message.get("timestamp")).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            pass
        await self.handle_message(MessageEvent(text=question, message_type=MessageType.TEXT, source=source,
                                               message_id=msg_id, raw_message=message, timestamp=timestamp))

    # -- Outbound ----------------------------------------------------------------------------------

    async def send(self, chat_id: str, content: str, reply_to: Optional[str] = None,
                   metadata: Optional[dict[str, Any]] = None) -> SendResult:
        if not self._client:
            return SendResult(success=False, error="MeetStream adapter is not connected")
        if chat_id not in self._bots:
            return SendResult(success=False, error=f"Hermes is not in a call with bot {chat_id}")
        sent = self._sent.setdefault(chat_id, [])
        try:
            watch = self._bots[chat_id]
            if watch.status_gifs:
                await self._show_status(watch, "working")
            for part in api.chunks(content):
                await api.send_message(self._client, _key(), chat_id, part)
                sent.append(part)
        except (api.MeetStreamError, ValueError) as e:
            return SendResult(success=False, error=getattr(e, "detail", str(e)))
        finally:
            del sent[:-50]
        return SendResult(success=True)

    async def send_typing(self, chat_id: str, metadata: Optional[dict] = None) -> None:
        # Hermes only invokes this for an active gateway turn. No incoming turn, no thinking GIF.
        watch = self._bots.get(chat_id)
        if watch and watch.status_gifs:
            now = time.monotonic()
            if watch.typing_since is None:
                watch.typing_since = now
            state = "activity" if now - watch.typing_since >= api.GIF_DURATION - 2 else "thinking"
            await self._show_status(watch, state)

    async def stop_typing(self, chat_id: str) -> None:
        watch = self._bots.get(chat_id)
        if watch:
            watch.typing_since = None

    async def get_chat_info(self, chat_id: str) -> dict[str, Any]:
        return {"name": f"Meeting {chat_id[:8]}", "type": "group", "chat_id": chat_id}
