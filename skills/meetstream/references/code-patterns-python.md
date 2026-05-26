# MeetStream — Python Code Patterns

Complete, runnable implementations for common MeetStream use cases.

All endpoint paths and field names are verified against `docs.meetstream.ai`.

---

## Pattern 1: Record a Meeting and Get the Transcript

A complete Flask webhook server that handles the full lifecycle.

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

# Map bot_id -> transcript_id, captured from create_bot response
TRANSCRIPT_IDS: dict[str, str] = {}


def create_bot(meeting_link: str, callback_url: str) -> tuple[str, str | None]:
    """Send a bot to a meeting. Returns (bot_id, transcript_id)."""
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
            "everyone_left_timeout": 300,
            "voice_inactivity_timeout": 100,
            "in_call_recording_timeout": 14400,
            "recording_permission_denied_timeout": 60
        }
    })
    resp.raise_for_status()
    data = resp.json()
    bot_id = data["bot_id"]
    transcript_id = data.get("transcript_id")
    if transcript_id:
        TRANSCRIPT_IDS[bot_id] = transcript_id
    print(f"Bot created: {bot_id} (transcript_id: {transcript_id or 'pending'})")
    return bot_id, transcript_id


def resolve_transcript_id(bot_id: str) -> str:
    """Get transcript_id from cache, /transcriptions, or /detail (fallback)."""
    if bot_id in TRANSCRIPT_IDS:
        return TRANSCRIPT_IDS[bot_id]

    # Try /transcriptions first
    try:
        resp = requests.get(f"{BASE_URL}/bots/{bot_id}/transcriptions", headers=HEADERS)
        resp.raise_for_status()
        for t in resp.json().get("transcriptions", []):
            if t.get("status") == "Success":
                TRANSCRIPT_IDS[bot_id] = t["transcript_id"]
                return t["transcript_id"]
    except requests.HTTPError:
        pass

    # Fall back to /detail — some deployments expose transcript_id under bot_details
    resp = requests.get(f"{BASE_URL}/bots/{bot_id}/detail", headers=HEADERS)
    resp.raise_for_status()
    detail = resp.json()
    transcript_id = (detail.get("bot_details") or {}).get("transcript_id") or detail.get("transcript_id")
    if not transcript_id:
        raise RuntimeError(f"No transcript_id found for bot {bot_id}")
    TRANSCRIPT_IDS[bot_id] = transcript_id
    return transcript_id


def get_transcript(bot_id: str) -> dict:
    """Fetch full transcript. Call only after transcription.processed fires.

    Canonical docs path: /transcript/{transcript_id}/get_transcript
    Alternate path observed in production (fallback if above 404s):
        /bots/{bot_id}/get_bot_transcript/{transcript_id}
    """
    transcript_id = resolve_transcript_id(bot_id)
    resp = requests.get(f"{BASE_URL}/transcript/{transcript_id}/get_transcript", headers=HEADERS)
    resp.raise_for_status()
    return resp.json()


@app.route("/webhook", methods=["POST"])
def webhook():
    """Handle MeetStream lifecycle callbacks. ALWAYS return 2xx — webhooks are NOT retried."""
    try:
        event = request.json or {}
        bot_id = event.get("bot_id")
        event_type = event.get("event")
        bot_status = event.get("bot_status")
        print(f"Event: {event_type} | Bot: {bot_id} | Status: {bot_status or '-'}")

        if event_type == "bot.inmeeting":
            print(f"Bot {bot_id} joined the meeting")

        elif event_type == "bot.stopped":
            if bot_status == "Stopped":
                print(f"Bot {bot_id} exited normally — waiting for transcript...")
            else:
                # NotAllowed / Denied / Error are surfaced here, not as *.failed events
                print(f"Bot {bot_id} did not join cleanly: {bot_status} — {event.get('message')}")

        elif event_type == "transcription.processed":
            print(f"Transcript ready for bot {bot_id}")
            transcript = get_transcript(bot_id)
            for segment in transcript.get("transcript", []):
                print(f"[{segment['speaker']}] {segment['text']}")

        elif event_type == "audio.processed":
            print(f"Audio ready for bot {bot_id}")

        elif event_type == "data_deletion":
            print(f"Bot {bot_id} data deleted ({event.get('deleted_objects', 0)} objects)")

    except Exception as e:
        # Log but still return 200 — no retries on non-2xx
        print(f"Webhook handler error: {e}")

    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    # Start: create_bot("https://zoom.us/j/123456789", "https://your-ngrok-url.ngrok.io/webhook")
    app.run(port=3000)
```

---

## Pattern 2: Real-Time Transcription (HTTPS Webhook)

Live transcription is delivered as HTTPS POSTs to your `webhook_url`, **not** over WebSocket.

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
        "live_transcription_required": {
            "webhook_url": webhook_url  # HTTPS POST endpoint, NOT a WebSocket
        },
        "recording_config": {
            "transcript": {
                "provider": {
                    "deepgram_streaming": {
                        "model": "nova-2",
                        "language": "en",
                        "punctuate": True,
                        "smart_format": True,
                        "endpointing": 300,
                        "utterance_end_ms": 1000,
                        "encoding": "linear16",
                        "channels": 1
                    }
                }
            }
        },
        "automatic_leave": {
            "waiting_room_timeout": 600,
            "everyone_left_timeout": 300,
            "in_call_recording_timeout": 14400,
            "recording_permission_denied_timeout": 60
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
        is_final = chunk.get("end_of_turn", False)
        print(f"[{ts}] {speaker}: {text}" + (" (final)" if is_final else ""))

        # Hook in your AI processing here:
        # - Detect questions/objections
        # - Trigger coaching cues
        # - Build live summary
        if "action item" in text.lower() or "follow up" in text.lower():
            print(f"  ↳ ACTION ITEM detected")

    except Exception as e:
        print(f"Live transcript handler error: {e}")

    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    app.run(port=3000)
```

---

## Pattern 3: Interactive Bot (Control via WebSocket)

The bot **dials into** your WebSocket server when it joins the meeting. Chat messages and images go over REST (`send_message`, `send_image`). The `sendaudio` WebSocket command is for TTS / pre-recorded audio.

```python
# pip install websockets requests
import asyncio
import base64
import json
import os
import wave
import requests
import websockets

MEETSTREAM_API_KEY = os.environ["MEETSTREAM_API_KEY"]
BASE_URL = "https://api.meetstream.ai/api/v1"
HEADERS = {
    "Authorization": f"Token {MEETSTREAM_API_KEY}",
    "Content-Type": "application/json"
}

# Track active bot sockets
BOT_SOCKETS: dict[str, websockets.WebSocketServerProtocol] = {}


def create_interactive_bot(meeting_link: str, control_ws_url: str) -> str:
    """Create a bot that connects back to your WebSocket for control commands."""
    resp = requests.post(f"{BASE_URL}/bots/create_bot", headers=HEADERS, json={
        "meeting_link": meeting_link,
        "bot_name": "Meeting Assistant",
        "video_required": False,
        "socket_connection_url": {"websocket_url": control_ws_url},  # field is websocket_url, not url
        "automatic_leave": {
            "waiting_room_timeout": 600,
            "everyone_left_timeout": 300,
            "recording_permission_denied_timeout": 60
        }
    })
    resp.raise_for_status()
    return resp.json()["bot_id"]


def send_chat_message(bot_id: str, message: str) -> None:
    """Send a chat message in the meeting via REST (not the WebSocket)."""
    resp = requests.post(
        f"{BASE_URL}/bots/{bot_id}/send_message",
        headers=HEADERS,
        json={"message": message, "metadata": {"message_type": "text"}}
    )
    resp.raise_for_status()


def send_image(bot_id: str, image_url: str) -> None:
    """Send an image (incl. animated GIF) in the meeting via REST."""
    resp = requests.post(
        f"{BASE_URL}/bots/{bot_id}/send_image",
        headers=HEADERS,
        json={"image_url": image_url, "metadata": {"message_type": "image"}}
    )
    resp.raise_for_status()


async def send_audio_chunk(bot_id: str, pcm16_le_bytes: bytes) -> None:
    """
    Play raw PCM16 LE audio through the bot's virtual mic.
    Audio MUST be: signed 16-bit, little-endian, 48000 Hz, mono. No WAV header.
    """
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


async def send_wav_file(bot_id: str, wav_path: str) -> None:
    """Read a 16-bit mono WAV at 48kHz and stream it through the bot."""
    with wave.open(wav_path, "rb") as wf:
        assert wf.getsampwidth() == 2, "WAV must be 16-bit"
        assert wf.getnchannels() == 1, "WAV must be mono"
        assert wf.getframerate() == 48000, "WAV must be 48000 Hz (resample first if needed)"
        pcm_bytes = wf.readframes(wf.getnframes())
    await send_audio_chunk(bot_id, pcm_bytes)


async def bot_control_handler(websocket):
    """Handle the bot control WebSocket connection."""
    bot_id = None
    try:
        async for message in websocket:
            data = json.loads(message)

            if data.get("type") == "ready":
                bot_id = data["bot_id"]
                BOT_SOCKETS[bot_id] = websocket
                print(f"Bot {bot_id} connected: {data.get('message', '')}")

                # Greet the meeting via REST (chat goes via REST, not the WS)
                send_chat_message(
                    bot_id,
                    "Hi everyone! I'm your meeting assistant. I'll be taking notes today."
                )
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

## Pattern 4: Calendar Auto-Scheduling

Connect Google Calendar so bots auto-join every upcoming meeting.

```python
# pip install google-auth google-auth-oauthlib requests
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
    """Run OAuth flow to get a refresh token. Run once, save the token."""
    flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, SCOPES)
    creds = flow.run_local_server(port=0)
    return creds.refresh_token


def connect_calendar(google_refresh_token: str, google_client_id: str, google_client_secret: str):
    """Connect Google Calendar to MeetStream. Field names MUST use google_ prefix."""
    resp = requests.post(f"{BASE_URL}/calendar/create_calendar", headers=HEADERS, json={
        "google_refresh_token": google_refresh_token,
        "google_client_id": google_client_id,
        "google_client_secret": google_client_secret
    })
    resp.raise_for_status()
    data = resp.json()
    print(f"Calendar connected for {data.get('user_email')}")
    return data


def list_calendars():
    """List all connected calendars."""
    resp = requests.get(f"{BASE_URL}/calendar", headers=HEADERS)
    resp.raise_for_status()
    return resp.json()


def list_upcoming_events():
    """List upcoming calendar events."""
    resp = requests.get(f"{BASE_URL}/calendar/events", headers=HEADERS)
    resp.raise_for_status()
    data = resp.json()
    for ev in data.get("results", []):
        print(f"{ev['start_time']} — {ev.get('meeting_platform')} — {ev.get('meeting_url')}")
    return data


def schedule_bot_for_event(event_id: str):
    """Manually schedule a bot for a specific event from /calendar/events."""
    resp = requests.post(f"{BASE_URL}/calendar/schedule/{event_id}", headers=HEADERS)
    resp.raise_for_status()
    data = resp.json()
    print(f"Scheduled bot {data['bot_id']} at {data['scheduled_time']}")
    return data


def reschedule_bot(bot_id: str, new_join_time_iso: str):
    """Reschedule a future bot to a different join time."""
    resp = requests.patch(
        f"{BASE_URL}/calendar/scheduled_bots/{bot_id}",
        headers=HEADERS,
        json={"scheduled_join_time": new_join_time_iso}
    )
    resp.raise_for_status()
    return resp.json()


def delete_scheduled_bot(bot_id: str):
    """Cancel a scheduled bot that hasn't joined yet."""
    resp = requests.delete(
        f"{BASE_URL}/calendar/scheduled_bots/{bot_id}",
        headers=HEADERS
    )
    resp.raise_for_status()
    return resp.json()


if __name__ == "__main__":
    # Step 1 (run once): token = get_google_refresh_token("client_secrets.json")
    connect_calendar(
        google_refresh_token=os.environ["GOOGLE_REFRESH_TOKEN"],
        google_client_id=os.environ["GOOGLE_CLIENT_ID"],
        google_client_secret=os.environ["GOOGLE_CLIENT_SECRET"]
    )
    list_upcoming_events()
```

---

## Pattern 5: Full Note-Taking Agent (Transcript + AI Summary)

Complete server: bot joins, transcribes, generates AI summary after the meeting ends.

```python
# pip install flask requests openai
import os
import requests
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

TRANSCRIPT_IDS: dict[str, str] = {}


def join_meeting(meeting_link: str, callback_url: str) -> str:
    resp = requests.post(f"{BASE_URL}/bots/create_bot", headers=MEETSTREAM_HEADERS, json={
        "meeting_link": meeting_link,
        "bot_name": "Note Taker",
        "video_required": False,
        "callback_url": callback_url,
        "recording_config": {
            "transcript": {
                "provider": {
                    "assemblyai": {
                        "speech_models": ["universal-2"],
                        "language_code": "en_us",
                        "speaker_labels": True,
                        "punctuate": True,
                        "format_text": True
                    }
                }
            },
            "retention": {"type": "timed", "hours": 72}
        },
        "automatic_leave": {
            "waiting_room_timeout": 600,
            "everyone_left_timeout": 300,
            "voice_inactivity_timeout": 100,
            "in_call_recording_timeout": 14400,
            "recording_permission_denied_timeout": 60
        }
    })
    resp.raise_for_status()
    data = resp.json()
    if data.get("transcript_id"):
        TRANSCRIPT_IDS[data["bot_id"]] = data["transcript_id"]
    return data["bot_id"]


def resolve_transcript_id(bot_id: str) -> str:
    if bot_id in TRANSCRIPT_IDS:
        return TRANSCRIPT_IDS[bot_id]
    resp = requests.get(f"{BASE_URL}/bots/{bot_id}/transcriptions", headers=MEETSTREAM_HEADERS)
    resp.raise_for_status()
    for t in resp.json().get("transcriptions", []):
        if t.get("status") == "Success":
            TRANSCRIPT_IDS[bot_id] = t["transcript_id"]
            return t["transcript_id"]
    raise RuntimeError(f"No completed transcript for bot {bot_id}")


def fetch_and_summarize(bot_id: str):
    transcript_id = resolve_transcript_id(bot_id)
    resp = requests.get(
        f"{BASE_URL}/transcript/{transcript_id}/get_transcript",
        headers=MEETSTREAM_HEADERS
    )
    resp.raise_for_status()
    transcript_data = resp.json()

    formatted = "\n".join(
        f"{seg['speaker']}: {seg['text']}"
        for seg in transcript_data.get("transcript", [])
    )

    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a meeting analyst. Extract: 1) Key decisions, 2) Action items with owners, 3) Open questions. Be concise."},
            {"role": "user", "content": f"Meeting transcript:\n\n{formatted}"}
        ]
    )
    summary = response.choices[0].message.content

    print(f"\n=== Meeting Summary (Bot {bot_id}) ===")
    print(summary)

    with open(f"summary_{bot_id}.txt", "w") as f:
        f.write(summary)

    return summary


@app.route("/webhook", methods=["POST"])
def webhook():
    """ALWAYS return 2xx — webhooks are NOT retried."""
    try:
        event = request.json or {}
        event_type = event.get("event")
        bot_id = event.get("bot_id")

        if event_type == "transcription.processed":
            print(f"Generating summary for bot {bot_id}...")
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

## Pattern 6: Webhook Signature Verification (optional, recommended)

If you've configured a webhook secret in the MeetStream dashboard, verify each incoming webhook:

```python
import hashlib
import hmac
from flask import Flask, request, jsonify

app = Flask(__name__)
WEBHOOK_SECRET = os.environ["MEETSTREAM_WEBHOOK_SECRET"].encode()


def verify_signature(raw_body: bytes, signature_header: str) -> bool:
    """signature_header looks like 'sha256=<hex_digest>'"""
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    received = signature_header.split("=", 1)[1]
    expected = hmac.new(WEBHOOK_SECRET, raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(received, expected)


@app.route("/webhook", methods=["POST"])
def webhook():
    if not verify_signature(request.get_data(), request.headers.get("X-MeetStream-Signature", "")):
        return jsonify({"error": "invalid signature"}), 401

    # ts = request.headers.get("X-MeetStream-Timestamp")  # check replay window if you want
    event = request.json or {}
    print(f"Verified: {event.get('event')} for bot {event.get('bot_id')}")
    return jsonify({"status": "ok"}), 200
```
