# MeetStream — Python Code Patterns

Complete, runnable implementations for common MeetStream use cases.

All endpoint paths, field names, response shapes, and WebSocket protocols are verified against `docs.meetstream.ai`. Nothing here is invented.

---

## Pattern 1: Record a Meeting and Get the Transcript (Flask)

```python
# pip install flask requests
import os
import requests
import threading
from flask import Flask, request, jsonify

app = Flask(__name__)

MEETSTREAM_API_KEY = os.environ["MEETSTREAM_API_KEY"]
BASE_URL = "https://api.meetstream.ai/api/v1"
HEADERS = {
    "Authorization": f"Token {MEETSTREAM_API_KEY}",
    "Content-Type": "application/json"
}

# Idempotency dedup for webhooks (no automatic retries, but defense in depth)
SEEN_EVENTS: set[str] = set()
SEEN_EVENTS_LOCK = threading.Lock()


def create_bot(meeting_link: str, callback_url: str) -> str:
    """Send a bot to a meeting. Returns bot_id.

    Note: BotResponse also includes transcript_id, but we don't need to store it.
    The canonical fetch flow uses bot_details.transcript_id which gives the same
    value statelessly when we need it later.
    """
    resp = requests.post(f"{BASE_URL}/bots/create_bot", headers=HEADERS, json={
        "meeting_link": meeting_link,
        "bot_name": "Recorder",
        "video_required": False,
        "callback_url": callback_url,
        "recording_config": {
            "transcript": {
                "provider": {"deepgram": {"language": "en", "model": "nova-3"}}
            },
            "retention": {"type": "timed", "hours": 48}
        },
        "automatic_leave": {
            "waiting_room_timeout": 600,
            "everyone_left_timeout": 600,
            "voice_inactivity_timeout": 600,
            "in_call_recording_timeout": 14400,
            "recording_permission_denied_timeout": 300
        }
    })
    resp.raise_for_status()
    data = resp.json()
    print(f"Bot created: {data['bot_id']} (HTTP {resp.status_code}, status={data.get('status')})")
    return data["bot_id"]


def get_transcript(bot_id: str) -> list[dict]:
    """Stateless transcript fetch. Call only after transcription.processed fires.

    Live-verified safe flow — handles all 3 status disagreements:
      1. GET /bots/{bot_id}/detail → check bot_details.TranscriptStatus (authoritative)
         and read bot_details.transcript_id
      2. GET /transcript/{transcript_id}/get_transcript
         - HTTP 200 → top-level array (success path)
         - HTTP 202 → dict {"message": "still processing"} — back off
      3. If TranscriptStatus == 'Failed', raise — get_transcript otherwise returns 202 forever

    Returns a list of segment dicts. Per-segment text field is 'transcript' (not 'text').
    """
    detail_resp = requests.get(f"{BASE_URL}/bots/{bot_id}/detail", headers=HEADERS)
    detail_resp.raise_for_status()
    bd = detail_resp.json().get("bot_details") or {}

    # Authoritative status check — TranscriptStatus is the source of truth
    ts = bd.get("TranscriptStatus")
    if ts == "Failed":
        raise RuntimeError(f"Transcript failed for {bot_id} — check transcription.failed webhook for details")

    transcript_id = bd.get("transcript_id")
    if not transcript_id:
        # meeting_captions or streaming-only provider — no post-call fetch path
        raise RuntimeError(f"No transcript_id for {bot_id} — likely meeting_captions or streaming-only provider")

    resp = requests.get(f"{BASE_URL}/transcript/{transcript_id}/get_transcript", headers=HEADERS)
    if resp.status_code == 202:
        # Transcript not ready — caller should retry after delay
        raise RuntimeError(f"Transcript not yet ready (HTTP 202): {resp.json().get('message')}")
    resp.raise_for_status()
    return resp.json()  # list[{speaker, transcript, start_time, end_time, words[]}]


def get_native_captions(bot_id: str) -> str | None:
    """For meeting_captions provider — transcript_id is null; fetch via /detail.

    Returns the S3 caption_file URL, or None if not available.
    """
    resp = requests.get(f"{BASE_URL}/bots/{bot_id}/detail", headers=HEADERS)
    resp.raise_for_status()
    return resp.json().get("bot_details", {}).get("caption_file")


@app.route("/webhook", methods=["POST"])
def webhook():
    """ALWAYS return 2xx — webhooks are NOT retried."""
    try:
        event = request.json or {}
        bot_id = event.get("bot_id")
        event_type = event.get("event")
        bot_status = event.get("bot_status")
        timestamp = event.get("timestamp")

        # Idempotency dedup
        # Lifecycle events lack timestamp — fall back to message which is unique enough
        dedupe_key = f"{bot_id}:{event_type}:{timestamp or event.get('message','')}"
        with SEEN_EVENTS_LOCK:
            if dedupe_key in SEEN_EVENTS:
                return jsonify({"status": "duplicate"}), 200
            SEEN_EVENTS.add(dedupe_key)

        print(f"Event: {event_type} | Bot: {bot_id} | Status: {bot_status or '-'}")

        # Lifecycle events (in order — all live-verified)
        if event_type == "bot.joining":
            print(f"Bot {bot_id} connecting...")
        elif event_type == "bot.error":
            # Live-verified: streaming-provider upstream error (e.g. AssemblyAI insufficient funds).
            # The bot continues; only live transcription is impacted.
            print(f"Bot {bot_id} streaming-provider error: {event.get('message')}")
        elif event_type == "bot.inmeeting":
            print(f"Bot {bot_id} joined the meeting")
        elif event_type == "bot.recording":
            print(f"Bot {bot_id} started recording")
        elif event_type == "bot.leaving":
            print(f"Bot {bot_id} is leaving")
        elif event_type == "bot.stopped":
            if bot_status == "Stopped":
                print(f"Bot {bot_id} exited normally — waiting for processing events...")
            else:
                # NotAllowed / Denied / Error surfaced via bot_status here
                print(f"Bot {bot_id} did not join cleanly: {bot_status} — {event.get('message')}")

        # Post-call processing events
        elif event_type == "manifest.completed":
            print(f"Manifest uploaded for bot {bot_id}")
        elif event_type == "audio.processed":
            print(f"Audio ready for bot {bot_id}")
        elif event_type == "video.processed":
            print(f"Video ready for bot {bot_id}")
        elif event_type == "transcription.processed":
            # transcript_id is NOT in this payload — resolve via bot_details.transcript_id
            segments = get_transcript(bot_id)
            for seg in segments:
                # Per-segment text field is 'transcript', NOT 'text'
                print(f"[{seg['speaker']}] {seg['transcript']}")
        elif event_type == "transcription.failed":
            # Live-verified failure event with status_code=500
            print(f"Transcription FAILED for bot {bot_id}: {event.get('message')}")

        # Terminal
        elif event_type == "bot.done":
            if event.get("status_code") == 200:
                print(f"Bot {bot_id} done successfully")
            else:
                print(f"Bot {bot_id} done with error: {event.get('message')}")

        elif event_type == "data_deletion":
            print(f"Bot {bot_id} data deleted ({event.get('deleted_objects', 0)} objects)")

        elif event_type and event_type.startswith("participant_events."):
            # Different payload shape — bot_id is under data.bot.id
            inner = event.get("data", {}).get("data", {})
            p = inner.get("participant", {})
            print(f"{inner.get('action')}: {p.get('full_name')} ({p.get('platform')})")

    except Exception as e:
        # Log but still return 200 — no retries on non-2xx
        print(f"Webhook handler error (already returning 200): {e}")

    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    app.run(port=3000)
```

---

## Pattern 2: Real-Time Transcription (HTTPS Webhook)

Live transcription is delivered as HTTPS POSTs to your `webhook_url` — **not** over WebSocket.

```python
# pip install flask requests
import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

MEETSTREAM_API_KEY = os.environ["MEETSTREAM_API_KEY"]
BASE_URL = "https://api.meetstream.ai/api/v1"
HEADERS = {
    "Authorization": f"Token {MEETSTREAM_API_KEY}",
    "Content-Type": "application/json"
}


def create_realtime_bot(meeting_link: str, webhook_url: str) -> str:
    """Create a bot with live transcription delivered via HTTPS webhook."""
    resp = requests.post(f"{BASE_URL}/bots/create_bot", headers=HEADERS, json={
        "meeting_link": meeting_link,
        "bot_name": "AI Assistant",
        "video_required": False,
        # webhook_url, NOT websocket_url
        "live_transcription_required": {"webhook_url": webhook_url},
        "recording_config": {
            "transcript": {
                "provider": {
                    "deepgram_streaming": {
                        "transcription_mode": "sentence",
                        "model": "nova-2",
                        "language": "en",
                        "punctuate": True,
                        "smart_format": True,
                        "endpointing": 300,
                        "vad_events": True,
                        "utterance_end_ms": 1000,
                        "encoding": "linear16",
                        "channels": 1
                    }
                }
            }
        },
        "automatic_leave": {
            "waiting_room_timeout": 600,
            "everyone_left_timeout": 600,
            "in_call_recording_timeout": 14400,
            "recording_permission_denied_timeout": 300
        }
    })
    resp.raise_for_status()
    return resp.json()["bot_id"]


@app.route("/live-transcript", methods=["POST"])
def live_transcript():
    """Receive streaming transcript chunks. Return 2xx fast."""
    try:
        chunk = request.json or {}
        bot_id = chunk.get("bot_id")
        speaker = chunk.get("speakerName", "Unknown")
        text = chunk.get("transcript", "")
        ts = chunk.get("timestamp", "")
        # Live payload has two boolean flags (live-captured):
        #   - is_final: provider-level — interim chunk vs final committed text
        #   - end_of_turn: speaker-level — speaker finished their utterance
        # Use whichever fits your use case. For "commit to UI on turn end", check end_of_turn.
        is_final = chunk.get("is_final", False)
        end_of_turn = chunk.get("end_of_turn", False)
        marker = " (final)" if is_final else (" (turn-end)" if end_of_turn else "")
        print(f"[{ts}] {speaker}: {text}{marker}")

        if end_of_turn and ("action item" in text.lower() or "follow up" in text.lower()):
            print(f"  ACTION ITEM detected from {speaker}")

    except Exception as e:
        print(f"Live transcript handler error: {e}")

    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    app.run(port=3000)
```

---

## Pattern 3: Interactive Bot — All 5 WebSocket Commands

The bot connects to your WS as a client, sends a `ready` handshake, then accepts JSON commands.

```python
# pip install websockets requests numpy
import asyncio
import base64
import json
import os
import wave
import numpy as np
import requests
import websockets

MEETSTREAM_API_KEY = os.environ["MEETSTREAM_API_KEY"]
BASE_URL = "https://api.meetstream.ai/api/v1"
HEADERS = {
    "Authorization": f"Token {MEETSTREAM_API_KEY}",
    "Content-Type": "application/json"
}

BOT_SOCKETS: dict[str, websockets.WebSocketServerProtocol] = {}


def create_interactive_bot(meeting_link: str, control_ws_url: str) -> str:
    """Create a bot that dials INTO your WebSocket for control commands."""
    resp = requests.post(f"{BASE_URL}/bots/create_bot", headers=HEADERS, json={
        "meeting_link": meeting_link,
        "bot_name": "Meeting Assistant",
        "video_required": False,
        "socket_connection_url": {"websocket_url": control_ws_url},
        "automatic_leave": {
            "waiting_room_timeout": 600,
            "everyone_left_timeout": 600,
            "recording_permission_denied_timeout": 300
        }
    })
    resp.raise_for_status()
    return resp.json()["bot_id"]


# ─── PCM utilities ─────────────────────────────────────────────────────────
def float32_to_pcm16_bytes(samples: np.ndarray) -> bytes:
    """Convert float32 (-1.0 to 1.0) → PCM16 LE bytes."""
    clipped = np.clip(samples, -1.0, 1.0)
    return (clipped * 32767).astype(np.int16).tobytes()


def resample_to_48k(pcm_bytes: bytes, source_rate: int) -> bytes:
    """Linear-interp resample PCM16 LE to 48 kHz."""
    if source_rate == 48000:
        return pcm_bytes
    samples = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32)
    num_out = int(len(samples) * 48000 / source_rate)
    t_in = np.linspace(0, 1, len(samples), endpoint=False)
    t_out = np.linspace(0, 1, num_out, endpoint=False)
    resampled = np.interp(t_out, t_in, samples)
    return np.clip(resampled, -32768, 32767).astype(np.int16).tobytes()


# ─── COMMAND 1: sendaudio ──────────────────────────────────────────────────
async def send_audio_chunk(bot_id: str, pcm16_le_bytes: bytes) -> None:
    """Play raw PCM16 LE audio @ 48 kHz mono. base64-encoded. No WAV header."""
    ws = BOT_SOCKETS.get(bot_id)
    if not ws:
        raise RuntimeError(f"No active socket for bot {bot_id}")
    await ws.send(json.dumps({
        "command": "sendaudio",
        "bot_id": bot_id,
        "audiochunk": base64.b64encode(pcm16_le_bytes).decode("utf-8"),
        "sample_rate": 48000,
        "encoding": "pcm16",
        "channels": 1,
        "endianness": "little"
    }))


async def stream_audio_chunked(bot_id: str, pcm_48k_bytes: bytes) -> None:
    """Stream long audio in 1-second chunks, paced slightly below real-time."""
    CHUNK_SAMPLES = 48000
    CHUNK_BYTES = CHUNK_SAMPLES * 2  # int16 = 2 bytes/sample
    for i in range(0, len(pcm_48k_bytes), CHUNK_BYTES):
        await send_audio_chunk(bot_id, pcm_48k_bytes[i:i + CHUNK_BYTES])
        await asyncio.sleep(0.8)  # 0.8s per 1s of audio


async def send_wav_file(bot_id: str, wav_path: str) -> None:
    """Read a 16-bit mono WAV and stream it. Resamples to 48 kHz if needed."""
    with wave.open(wav_path, "rb") as wf:
        assert wf.getsampwidth() == 2, "WAV must be 16-bit"
        assert wf.getnchannels() == 1, "WAV must be mono"
        pcm = wf.readframes(wf.getnframes())
        rate = wf.getframerate()
    pcm_48k = resample_to_48k(pcm, rate)
    await stream_audio_chunked(bot_id, pcm_48k)


# ─── COMMAND 2: sendmsg (both `message` AND `msg` required) ────────────────
async def send_chat_message_ws(bot_id: str, text: str) -> None:
    ws = BOT_SOCKETS.get(bot_id)
    if not ws:
        raise RuntimeError(f"No active socket for bot {bot_id}")
    await ws.send(json.dumps({
        "command": "sendmsg",
        "bot_id": bot_id,
        "message": text,
        "msg": text  # both fields required for cross-platform compat
    }))


# ─── COMMAND 3: sendchat (role + streaming) ────────────────────────────────
async def send_chat_with_role(bot_id: str, role: str, text: str, is_final: bool) -> None:
    """role: 'assistant' or 'user'. is_final: False for streaming tokens, True for final."""
    ws = BOT_SOCKETS.get(bot_id)
    if not ws:
        raise RuntimeError(f"No active socket for bot {bot_id}")
    await ws.send(json.dumps({
        "command": "sendchat",
        "bot_id": bot_id,
        "role": role,
        "text": text,
        "is_final": is_final
    }))


async def stream_assistant_reply(bot_id: str, token_stream) -> None:
    """Stream LLM tokens as they arrive, then commit final message."""
    accumulated = ""
    async for token in token_stream:
        accumulated += token
        await send_chat_with_role(bot_id, "assistant", accumulated, is_final=False)
    await send_chat_with_role(bot_id, "assistant", accumulated, is_final=True)


# ─── COMMAND 4: interrupt (barge-in) ───────────────────────────────────────
# Google Meet only fully clears the queue. Zoom/Teams accept but no-op.
async def interrupt_bot(bot_id: str) -> None:
    ws = BOT_SOCKETS.get(bot_id)
    if not ws:
        raise RuntimeError(f"No active socket for bot {bot_id}")
    await ws.send(json.dumps({
        "command": "interrupt",
        "bot_id": bot_id,
        "action": "clear_audio_queue"
    }))


# ─── COMMAND 5: sendimg / sendimg_url (set bot's video frame) ──────────────
async def set_bot_video_frame_from_url(bot_id: str, img_url: str) -> None:
    """Set bot's camera to a publicly accessible image URL."""
    ws = BOT_SOCKETS.get(bot_id)
    if not ws:
        raise RuntimeError(f"No active socket for bot {bot_id}")
    await ws.send(json.dumps({
        "command": "sendimg_url",
        "bot_id": bot_id,
        "img_url": img_url
    }))


async def set_bot_video_frame_from_file(bot_id: str, image_path: str) -> None:
    """Set bot's camera from a local JPEG or PNG file (base64-encoded)."""
    ws = BOT_SOCKETS.get(bot_id)
    if not ws:
        raise RuntimeError(f"No active socket for bot {bot_id}")
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode("utf-8")
    await ws.send(json.dumps({
        "command": "sendimg",
        "bot_id": bot_id,
        "img": img_b64
    }))


# ─── REST equivalents for chat / image into the chat panel ─────────────────
def post_chat_via_rest(bot_id: str, message: str) -> None:
    resp = requests.post(
        f"{BASE_URL}/bots/{bot_id}/send_message",
        headers=HEADERS,
        json={"message": message, "metadata": {"message_type": "text"}}
    )
    resp.raise_for_status()


def post_image_via_rest(bot_id: str, img_url: str, display_duration: int | None = None) -> None:
    # IMPORTANT: field is `img_url`, NOT `image_url`
    payload: dict = {"img_url": img_url, "metadata": {"message_type": "image"}}
    if display_duration is not None:
        payload["display_duration"] = display_duration
    resp = requests.post(f"{BASE_URL}/bots/{bot_id}/send_image", headers=HEADERS, json=payload)
    resp.raise_for_status()


# ─── WebSocket server ──────────────────────────────────────────────────────
async def bot_control_handler(websocket):
    bot_id = None
    try:
        async for message in websocket:
            data = json.loads(message)
            if data.get("type") == "ready":
                bot_id = data["bot_id"]
                BOT_SOCKETS[bot_id] = websocket
                print(f"Bot {bot_id} connected: {data.get('message', '')}")
                await send_chat_message_ws(bot_id, "Hi everyone! I'm taking notes today.")
    finally:
        if bot_id:
            BOT_SOCKETS.pop(bot_id, None)


async def main():
    async with websockets.serve(bot_control_handler, "0.0.0.0", 8766):
        print("Bot control: ws://localhost:8766")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
```

---

## Pattern 4: Calendar Auto-Scheduling (Full Surface)

```python
# pip install requests google-auth google-auth-oauthlib
import os
import requests
from google_auth_oauthlib.flow import InstalledAppFlow

MEETSTREAM_API_KEY = os.environ["MEETSTREAM_API_KEY"]
BASE_URL = "https://api.meetstream.ai/api/v1"
HEADERS = {
    "Authorization": f"Token {MEETSTREAM_API_KEY}",
    "Content-Type": "application/json"
}

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


def get_google_refresh_token(client_secrets_file: str) -> str:
    """Run OAuth flow once to get a refresh token. Save it."""
    flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, SCOPES)
    creds = flow.run_local_server(port=0)
    return creds.refresh_token


# ─── Connect / Disconnect ──────────────────────────────────────────────────
def connect_calendar(refresh_token: str, client_id: str, client_secret: str):
    """Field names MUST use google_ prefix per CalendarCreateRequest schema."""
    resp = requests.post(f"{BASE_URL}/calendar/create_calendar", headers=HEADERS, json={
        "google_refresh_token": refresh_token,
        "google_client_id": client_id,
        "google_client_secret": client_secret
    })
    resp.raise_for_status()
    return resp.json()


def disconnect_calendar(refresh_token: str, client_id: str, client_secret: str):
    """Docs method inconsistency — neither has been live-tested by this skill.

    OpenAPI says: POST /calendar/disconnect with CalendarCreateRequest body
    Prose docs say: DELETE /calendar/disconnect
    Try POST first; fall back to DELETE (without body) if rejected. Confirm
    against your account before relying on this in production.
    """
    body = {
        "google_refresh_token": refresh_token,
        "google_client_id": client_id,
        "google_client_secret": client_secret
    }
    resp = requests.post(f"{BASE_URL}/calendar/disconnect", headers=HEADERS, json=body)
    if resp.status_code == 405:
        resp = requests.delete(f"{BASE_URL}/calendar/disconnect", headers=HEADERS)
    resp.raise_for_status()
    return resp.json()


# ─── List calendars / events ───────────────────────────────────────────────
def list_calendars():
    """Live list from Google."""
    resp = requests.get(f"{BASE_URL}/calendar/calendars", headers=HEADERS)
    resp.raise_for_status()
    return resp.json()


def list_events_synced():
    """Sync from Google + list with pagination."""
    resp = requests.get(f"{BASE_URL}/calendar/events", headers=HEADERS)
    resp.raise_for_status()
    return resp.json()


def list_events_from_db():
    """Faster: read MeetStream's local DB only, no Google API call."""
    resp = requests.get(f"{BASE_URL}/calendar/get_events", headers=HEADERS)
    resp.raise_for_status()
    return resp.json()


# ─── Schedule per event with bot_config + recurring options ────────────────
def schedule_bot_for_event(
    event_id: str,
    bot_config: dict,
    *,
    occurrence_date: str | None = None,
    schedule_all_occurrences: bool = False,
    occurrence_limit: int = 52,
    recurring_event: bool = False
):
    body = {"bot_config": bot_config}
    if occurrence_date:
        body["occurrence_date"] = occurrence_date
    if schedule_all_occurrences:
        body["schedule_all_occurrences"] = True
        body["occurrence_limit"] = occurrence_limit
    if recurring_event:
        body["recurring_event"] = True

    resp = requests.post(f"{BASE_URL}/calendar/schedule/{event_id}", headers=HEADERS, json=body)
    if resp.status_code == 409:
        # Deduplication: existing bot for this event
        data = resp.json()
        print(f"Already scheduled. Existing bot_id: {data.get('bot_id')}")
        return data
    resp.raise_for_status()
    return resp.json()


def unschedule_event(
    event_id: str,
    *,
    cancel_all_occurrences: bool = False,
    from_date: str | None = None
):
    body: dict = {"cancel_all_occurrences": cancel_all_occurrences}
    if from_date:
        body["from_date"] = from_date
    resp = requests.delete(f"{BASE_URL}/calendar/schedule/{event_id}", headers=HEADERS, json=body)
    resp.raise_for_status()
    return resp.json()


# ─── Scheduled bot management ──────────────────────────────────────────────
def list_scheduled_bots():
    resp = requests.get(f"{BASE_URL}/calendar/scheduled_bots", headers=HEADERS)
    resp.raise_for_status()
    return resp.json()


def reschedule_bot(
    bot_id: str,
    *,
    scheduled_join_time: str | None = None,
    bot_username: str | None = None,
    custom_attributes: dict | None = None
):
    body: dict = {}
    if scheduled_join_time:
        body["scheduled_join_time"] = scheduled_join_time
    if bot_username:
        body["bot_username"] = bot_username
    if custom_attributes:
        body["custom_attributes"] = custom_attributes
    resp = requests.patch(f"{BASE_URL}/calendar/scheduled_bots/{bot_id}", headers=HEADERS, json=body)
    resp.raise_for_status()
    return resp.json()


def delete_scheduled_bot(bot_id: str):
    resp = requests.delete(f"{BASE_URL}/calendar/scheduled_bots/{bot_id}", headers=HEADERS)
    resp.raise_for_status()
    return resp.json()


# ─── Auto-scheduling ───────────────────────────────────────────────────────
def enable_auto_schedule(default_bot_config: dict):
    """Job runs daily at midnight UTC, schedules bots for next 24h."""
    resp = requests.post(f"{BASE_URL}/calendar/auto-schedule/enable", headers=HEADERS, json={
        "default_bot_config": default_bot_config
    })
    resp.raise_for_status()
    return resp.json()


def disable_auto_schedule():
    resp = requests.post(f"{BASE_URL}/calendar/auto-schedule/disable", headers=HEADERS, json={})
    resp.raise_for_status()
    return resp.json()


def get_auto_schedule_settings():
    resp = requests.get(f"{BASE_URL}/calendar/auto-schedule/settings", headers=HEADERS)
    resp.raise_for_status()
    return resp.json()


# ─── Recurring events ──────────────────────────────────────────────────────
def toggle_recurrence(event_id: str, recurring_enabled: bool):
    """Path has NO event_id — event_id goes in the body."""
    resp = requests.post(f"{BASE_URL}/calendar/toggle-recurrence", headers=HEADERS, json={
        "event_id": event_id,
        "recurring_enabled": recurring_enabled
    })
    resp.raise_for_status()
    return resp.json()


def auto_reschedule():
    resp = requests.post(f"{BASE_URL}/calendar/auto-reschedule", headers=HEADERS, json={})
    resp.raise_for_status()
    return resp.json()
```

---

## Pattern 5: Full Note-Taking Agent (Transcript + AI Summary)

```python
# pip install flask requests openai
import os
import requests
import threading
from flask import Flask, request, jsonify
from openai import OpenAI

app = Flask(__name__)

MEETSTREAM_API_KEY = os.environ["MEETSTREAM_API_KEY"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
BASE_URL = "https://api.meetstream.ai/api/v1"
MEETSTREAM_HEADERS = {
    "Authorization": f"Token {MEETSTREAM_API_KEY}",
    "Content-Type": "application/json"
}
openai_client = OpenAI(api_key=OPENAI_API_KEY)

SEEN_EVENTS: set[str] = set()


def join_meeting(meeting_link: str, callback_url: str) -> str:
    resp = requests.post(f"{BASE_URL}/bots/create_bot", headers=MEETSTREAM_HEADERS, json={
        "meeting_link": meeting_link,
        "bot_name": "Note Taker",
        "video_required": False,
        "callback_url": callback_url,
        "recording_config": {
            "transcript": {
                "provider": {
                    # AssemblyAI: OpenAPI marks 9 fields required — pass full config
                    "assemblyai": {
                        "speech_models": ["universal-2"],
                        "language_code": "en_us",
                        "speaker_labels": True,
                        "punctuate": True,
                        "format_text": True,
                        "filter_profanity": False,
                        "redact_pii": False,
                        "auto_chapters": False,
                        "entity_detection": False
                    }
                }
            },
            "retention": {"type": "timed", "hours": 72}
        },
        "automatic_leave": {
            "waiting_room_timeout": 600,
            "everyone_left_timeout": 600,
            "voice_inactivity_timeout": 600,
            "in_call_recording_timeout": 14400,
            "recording_permission_denied_timeout": 300
        }
    })
    resp.raise_for_status()
    return resp.json()["bot_id"]


def get_transcript_id(bot_id: str) -> str:
    """Canonical stateless transcript_id lookup via bot_details."""
    resp = requests.get(f"{BASE_URL}/bots/{bot_id}/detail", headers=MEETSTREAM_HEADERS)
    resp.raise_for_status()
    tid = (resp.json().get("bot_details") or {}).get("transcript_id")
    if not tid:
        raise RuntimeError(f"No transcript_id on bot_details for {bot_id}")
    return tid


def fetch_and_summarize(bot_id: str) -> str:
    transcript_id = get_transcript_id(bot_id)
    resp = requests.get(
        f"{BASE_URL}/transcript/{transcript_id}/get_transcript",
        headers=MEETSTREAM_HEADERS
    )
    resp.raise_for_status()
    segments = resp.json()  # top-level array

    # Per-segment text field is 'transcript', NOT 'text'
    formatted = "\n".join(f"{seg['speaker']}: {seg['transcript']}" for seg in segments)

    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Extract: 1) Key decisions, 2) Action items with owners, 3) Open questions. Be concise."},
            {"role": "user", "content": f"Meeting transcript:\n\n{formatted}"}
        ]
    )
    summary = response.choices[0].message.content
    print(f"\n=== Summary (Bot {bot_id}) ===\n{summary}")
    with open(f"summary_{bot_id}.txt", "w") as f:
        f.write(summary)
    return summary


@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        event = request.json or {}
        event_type = event.get("event")
        bot_id = event.get("bot_id")
        # Lifecycle events lack timestamp — fall back to message
        dedupe_key = f"{bot_id}:{event_type}:{event.get('timestamp') or event.get('message','')}"
        if dedupe_key in SEEN_EVENTS:
            return jsonify({"status": "duplicate"}), 200
        SEEN_EVENTS.add(dedupe_key)

        if event_type == "transcription.processed":
            fetch_and_summarize(bot_id)
        elif event_type == "bot.stopped" and event.get("bot_status") != "Stopped":
            print(f"Bot {bot_id} failed: {event.get('bot_status')} — {event.get('message')}")
    except Exception as e:
        print(f"Webhook error: {e}")
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    app.run(port=3000)
```

---

## Pattern 6: Webhook Signature Verification

```python
# pip install flask
import hashlib
import hmac
import os
from flask import Flask, request, jsonify

app = Flask(__name__)
WEBHOOK_SECRET = os.environ["MEETSTREAM_WEBHOOK_SECRET"].encode()


def verify_signature(raw_body: bytes, signature_header: str | None) -> bool:
    """signature_header looks like 'sha256=<hex_digest>'"""
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    received = signature_header.split("=", 1)[1]
    expected = hmac.new(WEBHOOK_SECRET, raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(received, expected)


@app.route("/webhook", methods=["POST"])
def webhook():
    if not verify_signature(request.get_data(), request.headers.get("X-MeetStream-Signature")):
        return jsonify({"error": "invalid signature"}), 401
    # ts = request.headers.get("X-MeetStream-Timestamp")  # check replay window if you want
    event = request.json or {}
    print(f"Verified: {event.get('event')} for bot {event.get('bot_id')}")
    return jsonify({"status": "ok"}), 200
```

---

## Pattern 7: Live Audio Receiver (binary frame decoder)

`live_audio_required` streams binary frames over a WebSocket. Decode with this exact wire format.

```python
# pip install websockets numpy
import asyncio
import json
import struct
import wave
import numpy as np
import websockets


def decode_audio_frame(data: bytes) -> tuple[str, str, bytes] | None:
    """Decode a MeetStream binary audio frame.

    Wire format:
      [msg_type=0x01 (1B)][sid_length u16 LE (2B)][speaker_id UTF-8 (L1)]
      [sname_length u16 LE (2B)][speaker_name UTF-8 (L2)][raw PCM16 LE remainder]

    Returns: (speaker_id, speaker_name, pcm_bytes), or None if malformed.
    """
    if len(data) < 5 or data[0] != 0x01:
        return None

    # Speaker ID
    sid_len = int.from_bytes(data[1:3], "little")
    speaker_id = data[3:3 + sid_len].decode("utf-8")

    # Speaker Name
    off = 3 + sid_len
    sname_len = int.from_bytes(data[off:off + 2], "little")
    off += 2
    speaker_name = data[off:off + sname_len].decode("utf-8")
    off += sname_len

    # Remaining bytes = raw PCM16 LE @ 48kHz mono
    pcm_bytes = data[off:]
    return speaker_id, speaker_name, pcm_bytes


def pcm16_bytes_to_float32(pcm_bytes: bytes) -> np.ndarray:
    """Standard format for ML models."""
    samples = np.frombuffer(pcm_bytes, dtype=np.int16)
    return samples.astype(np.float32) / 32768.0


def resample_48k_to_16k(pcm_48k_bytes: bytes) -> bytes:
    """Many ASR models want 16 kHz."""
    samples = np.frombuffer(pcm_48k_bytes, dtype=np.int16).astype(np.float32)
    num_out = int(len(samples) * 16000 / 48000)
    t_in = np.linspace(0, 1, len(samples), endpoint=False)
    t_out = np.linspace(0, 1, num_out, endpoint=False)
    resampled = np.interp(t_out, t_in, samples)
    return np.clip(resampled, -32768, 32767).astype(np.int16).tobytes()


def write_wav_file(path: str, pcm_bytes: bytes, sample_rate: int = 48000) -> None:
    """Save accumulated PCM bytes as a WAV file."""
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)


async def audio_receiver(websocket):
    bot_id: str | None = None
    per_speaker: dict[str, bytearray] = {}

    async for message in websocket:
        if isinstance(message, str):
            # JSON handshake or control message
            msg = json.loads(message)
            if msg.get("type") == "ready":
                bot_id = msg["bot_id"]
                print(f"Live audio connected for bot {bot_id}")
            continue

        # Binary audio frame
        frame = decode_audio_frame(message)
        if not frame:
            continue
        speaker_id, speaker_name, pcm = frame

        # "NoSpeaker" sentinel: MeetStream couldn't attribute audio
        if speaker_name == "NoSpeaker":
            continue

        per_speaker.setdefault(speaker_name, bytearray()).extend(pcm)
        duration_sec = (len(pcm) / 2) / 48000
        print(f"{speaker_name} ({speaker_id}): {duration_sec:.2f}s")

    # On disconnect (code 1000 when bot leaves), persist per-speaker audio
    for name, buf in per_speaker.items():
        write_wav_file(f"audio_{bot_id}_{name}.wav", bytes(buf), sample_rate=48000)
        print(f"Wrote audio_{bot_id}_{name}.wav ({len(buf)} bytes)")


async def main():
    async with websockets.serve(audio_receiver, "0.0.0.0", 8765):
        print("Live audio receiver: ws://localhost:8765")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
```

Then on `create_bot`:
```python
requests.post(f"{BASE_URL}/bots/create_bot", headers=HEADERS, json={
    "meeting_link": "...",
    "bot_name": "Audio Listener",
    "live_audio_required": {"websocket_url": "wss://your-server.com/audio"}
})
```

---

## Pattern 8: Live Video Receiver (fMP4 over WebSocket)

Supported on **Google Meet + Teams only — NOT Zoom**.

```python
# pip install websockets
import asyncio
import json
import time
import websockets


async def video_receiver(websocket):
    bot_id: str | None = None
    output_file = None
    stream_info: dict | None = None

    try:
        async for message in websocket:
            if isinstance(message, bytes):
                # fMP4 chunk — append in order
                if output_file:
                    output_file.write(message)
                continue

            msg = json.loads(message)

            if msg.get("type") == "video_stream_start":
                bot_id = msg["bot_id"]
                stream_info = msg
                output_file = open(f"video_{bot_id}.mp4", "wb")
                print(f"Stream start for {bot_id}: {msg['width']}x{msg['height']}@{msg['framerate']}fps codec={msg['codec']}")

            elif msg.get("type") == "video_latency_ping":
                # MUST reply with video_latency_pong
                await websocket.send(json.dumps({
                    "type": "video_latency_pong",
                    "seq": msg["seq"],
                    "sent_at_ms": msg["sent_at_ms"],
                    "server_received_at_ms": int(time.time() * 1000),
                    "bot_id": msg["bot_id"]
                }))

            elif msg.get("type") == "video_stream_end":
                print(f"Stream end for {bot_id}: {msg['duration_seconds']}s")
                if output_file:
                    output_file.close()
                    output_file = None
    finally:
        if output_file:
            output_file.close()


async def main():
    async with websockets.serve(video_receiver, "0.0.0.0", 8767):
        print("Live video receiver: ws://localhost:8767")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
```

Then on `create_bot`:
```python
requests.post(f"{BASE_URL}/bots/create_bot", headers=HEADERS, json={
    "meeting_link": "https://meet.google.com/...",  # Meet or Teams only — NOT Zoom
    "bot_name": "Video Listener",
    "video_required": True,
    "live_video_required": {"websocket_url": "wss://your-server.com/video"}
})
```

---

## Pattern 9: MIA — AI Agent in a Meeting

```python
import os
import requests

MEETSTREAM_API_KEY = os.environ["MEETSTREAM_API_KEY"]
BASE_URL = "https://api.meetstream.ai/api/v1"
HEADERS = {"Authorization": f"Token {MEETSTREAM_API_KEY}", "Content-Type": "application/json"}


# ─── 1. Create agent configurations ────────────────────────────────────────
def create_pipeline_agent() -> str:
    """Pipeline mode: separate STT, LLM, TTS providers."""
    resp = requests.post(f"{BASE_URL}/mia", headers=HEADERS, json={
        "agent_name": "Meeting Assistant",
        "mode": "pipeline",
        "model": {
            "provider": "openai",
            "model": "gpt-4.1",
            "system_prompt": "You are a helpful meeting assistant. Track action items."
        },
        "voice": {"provider": "openai", "voice_id": "nova"},
        "transcriber": {"provider": "deepgram", "model": "nova-3", "language": "en"},
        "agent": {"response_type": "voice", "first_message": "Hello!"}
    })
    resp.raise_for_status()
    return resp.json()["agent_config_id"]


def create_realtime_openai_agent() -> str:
    """Realtime mode: single OpenAI realtime model, low latency."""
    resp = requests.post(f"{BASE_URL}/mia", headers=HEADERS, json={
        "agent_name": "Fast Voice Agent",
        "mode": "realtime",
        "model": {
            "provider": "openai",
            "model": "gpt-4o-realtime-preview",
            "system_prompt": "You are concise and helpful.",
            "voice": "alloy"  # OpenAI voices: alloy/ash/ballad/coral/echo/fable/nova/onyx/sage/shimmer/verse
        }
    })
    resp.raise_for_status()
    return resp.json()["agent_config_id"]


def create_realtime_xai_agent() -> str:
    """xAI Grok — model is hardcoded server-side."""
    resp = requests.post(f"{BASE_URL}/mia", headers=HEADERS, json={
        "agent_name": "Grok Agent",
        "mode": "realtime",
        "model": {
            "provider": "xai",
            "system_prompt": "You are witty and helpful.",
            "voice": "Ara"  # xAI voices: Ara/Eve/Leo/Rex/Sal
        }
    })
    resp.raise_for_status()
    return resp.json()["agent_config_id"]


def create_realtime_gemini_agent() -> str:
    """Google Gemini with optional thinking."""
    resp = requests.post(f"{BASE_URL}/mia", headers=HEADERS, json={
        "agent_name": "Gemini Agent",
        "mode": "realtime",
        "model": {
            "provider": "google",
            "system_prompt": "You are thoughtful.",
            "voice": "Puck",  # Gemini voices: Puck/Charon/Kore/Fenrir/Aoede/Leda/Orus/Zephyr
            "thinking_config": {"include_thoughts": True, "thinking_budget": 1024}
        }
    })
    resp.raise_for_status()
    return resp.json()["agent_config_id"]


def create_wake_word_agent() -> str:
    """Pipeline mode with wake-word gating."""
    resp = requests.post(f"{BASE_URL}/mia", headers=HEADERS, json={
        "agent_name": "Wake Word Agent",
        "mode": "pipeline",
        "model": {
            "provider": "openai",
            "model": "gpt-4.1",
            "system_prompt": "Only respond when addressed."
        },
        "voice": {"provider": "elevenlabs", "voice_id": "21m00Tcm4TlvDq8ikWAM"},
        "transcriber": {"provider": "deepgram", "model": "nova-3"},
        "wake_word": {
            "enabled": True,
            "words": ["hey assistant", "hello bot"],
            "timeout": 30  # seconds active after wake
        }
    })
    resp.raise_for_status()
    return resp.json()["agent_config_id"]


def create_mcp_action_agent() -> str:
    """Pipeline mode with MCP tool calling."""
    resp = requests.post(f"{BASE_URL}/mia", headers=HEADERS, json={
        "agent_name": "Action Agent",
        "mode": "pipeline",
        "model": {
            "provider": "openai",
            "model": "gpt-4.1",
            "system_prompt": "Listen for action items. Use Linear MCP to create tickets. Don't speak unless asked."
        },
        "voice": {"provider": "elevenlabs", "voice_id": "21m00Tcm4TlvDq8ikWAM"},
        "transcriber": {"provider": "deepgram", "model": "nova-3"},
        "agent": {
            "response_type": "action",
            "mcp_servers": [{
                "url": "https://your-mcp-gateway.example.com/mcp",
                "headers": {"Authorization": "Bearer <MCP_TOKEN>"},
                "allowed_tools": ["create_issue", "list_issues"],
                "timeout": 10
            }]
        }
    })
    resp.raise_for_status()
    return resp.json()["agent_config_id"]


# ─── 2. List / get / update / delete ───────────────────────────────────────
def list_agents():
    resp = requests.get(f"{BASE_URL}/mia", headers=HEADERS)
    resp.raise_for_status()
    return resp.json()  # {agent_configs: [...], count}


def get_agent(agent_config_id: str):
    resp = requests.get(f"{BASE_URL}/mia", headers=HEADERS,
                        params={"agent_config_id": agent_config_id})
    resp.raise_for_status()
    return resp.json()


def update_agent(agent_config_id: str, **updates):
    body = {"agent_config_id": agent_config_id, **updates}
    resp = requests.put(f"{BASE_URL}/mia", headers=HEADERS, json=body)
    resp.raise_for_status()
    return resp.json()


def delete_agent(agent_config_id: str):
    # DELETE uses query param, NOT path id
    resp = requests.delete(f"{BASE_URL}/mia", headers=HEADERS,
                           params={"agent_config_id": agent_config_id})
    resp.raise_for_status()
    return resp.json()


# ─── 3. Attach to a bot using the hosted MeetStream bridge ─────────────────
def spawn_agent_bot(meeting_link: str, agent_config_id: str) -> str:
    """All three fields (agent_config_id + socket + live_audio) required together."""
    resp = requests.post(f"{BASE_URL}/bots/create_bot", headers=HEADERS, json={
        "meeting_link": meeting_link,
        "bot_name": "AI Agent",
        "agent_config_id": agent_config_id,
        "socket_connection_url": {
            "websocket_url": "wss://agent-meetstream-prd-main.meetstream.ai/bridge"
        },
        "live_audio_required": {
            "websocket_url": "wss://agent-meetstream-prd-main.meetstream.ai/bridge/audio"
        }
    })
    resp.raise_for_status()
    return resp.json()["bot_id"]
```

---

## Pattern 10: Google Signed-In Bots

For Google Meet meetings that require a signed-in identity.

```python
import os
import requests

MEETSTREAM_API_KEY = os.environ["MEETSTREAM_API_KEY"]
BASE_URL = "https://api.meetstream.ai/api/v1"
HEADERS = {"Authorization": f"Token {MEETSTREAM_API_KEY}", "Content-Type": "application/json"}


# Setup (one-time): register your Google Workspace domain + login certs
# See https://docs.meetstream.ai/guides/google-signed-in-bots for the full SSO flow.

def list_google_domains():
    resp = requests.get(f"{BASE_URL}/google-login-domains", headers=HEADERS)
    resp.raise_for_status()
    return resp.json()


def get_google_domain(domain: str):
    """Path param is the DOMAIN STRING (e.g. 'your-company.com'), not an opaque id."""
    resp = requests.get(f"{BASE_URL}/google-login-domains/{domain}", headers=HEADERS)
    resp.raise_for_status()
    return resp.json()


def list_google_logins():
    resp = requests.get(f"{BASE_URL}/google-logins", headers=HEADERS)
    resp.raise_for_status()
    return resp.json()


# Then on create_bot, activate signed-in mode via the google_meet field
# (documented in the guide, not in the OpenAPI CreateBotRequest schema):
def create_signed_in_bot(meeting_link: str, domain: str) -> str:
    resp = requests.post(f"{BASE_URL}/bots/create_bot", headers=HEADERS, json={
        "meeting_link": meeting_link,
        "bot_name": "Signed-In Agent",
        "video_required": False,
        "google_meet": {
            "login_required": True,
            "google_login_domain": domain  # e.g. "your-company.com"
        },
        "automatic_leave": {
            "waiting_room_timeout": 600,
            "everyone_left_timeout": 600,
            "voice_inactivity_timeout": 600,
            "in_call_recording_timeout": 14400,
            "recording_permission_denied_timeout": 300
        }
    })
    resp.raise_for_status()
    return resp.json()["bot_id"]
```

---

## Pattern 11: `/transcribe` (Backup / Fallback Path)

> This is a **fallback** pattern — not the primary post-call workflow. For standard post-call notetaking, configure the post-call provider on `create_bot` up front (Pattern 1 / Pattern 5). Use `/transcribe` only when:
> - The bot used a streaming-only provider and you now need a post-call transcript too
> - The original provider failed (out of credit, wrong config) and you want to retry with a different provider
> - You want to re-transcribe with a higher-quality / different-language provider after the fact

```python
import os
import requests

KEY = os.environ["MEETSTREAM_API_KEY"]
BASE_URL = "https://api.meetstream.ai/api/v1"
HEADERS = {"Authorization": f"Token {KEY}", "Content-Type": "application/json"}


def trigger_post_call_transcription(bot_id: str, callback_url: str, provider: dict | None = None) -> str:
    """Request a new post-call transcript run on the bot's stored audio.

    Live-verified flow:
      1. POST returns immediately with new transcript_id
      2. Server processes in background
      3. Exactly one transcription.processed OR transcription.failed fires on callback_url
      4. bot_details.transcript_id is OVERWRITTEN with this new run's id
      5. NO bot.done event after — fire-and-forget
      6. NO custom_attributes in the webhook payload (unlike original lifecycle events)

    Default provider is deepgram nova-3 if not specified. Pick whichever provider
    your MeetStream account has API keys for.
    """
    payload = {
        "provider": provider or {"deepgram": {"model": "nova-3", "language": "en"}},
        "callback_url": callback_url,
    }
    resp = requests.post(f"{BASE_URL}/bots/{bot_id}/transcribe", headers=HEADERS, json=payload)
    resp.raise_for_status()
    data = resp.json()
    # data: {bot_id, transcript_id, provider, message}
    print(f"Re-transcription started for {bot_id} | new transcript_id={data['transcript_id']}")
    return data["transcript_id"]


# Use case: a bot ran with meetstream_streaming (live only, no post-call transcript).
# After bot.stopped, request a post-call transcript with assemblyai.
def add_post_call_transcript_to_streaming_bot(bot_id: str, callback_url: str):
    trigger_post_call_transcription(bot_id, callback_url, provider={
        "assemblyai": {
            "speech_models": ["universal-2"],
            "language_code": "en_us",
            "speaker_labels": True,
            "punctuate": True,
            "format_text": True,
            "filter_profanity": False,
            "redact_pii": False,
            "auto_chapters": False,
            "entity_detection": False,
        }
    })
    # Wait for transcription.processed webhook, then use the canonical get_transcript()
    # pattern (Pattern 1) — bot_details.transcript_id will already point at the new run.
