# MeetStream — Python Code Patterns

Complete, runnable implementations for common MeetStream use cases.

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


def create_bot(meeting_link: str, callback_url: str) -> str:
    """Send a bot to a meeting. Returns bot_id."""
    resp = requests.post(f"{BASE_URL}/bots/create_bot", headers=HEADERS, json={
        "meeting_link": meeting_link,
        "bot_name": "Recorder",
        "audio_required": True,
        "video_required": False,
        "callback_url": callback_url,
        "recording_config": {
            "transcript": {
                "provider": {"deepgram": {"language": "en", "model": "nova-3"}}
            },
            "retention": {"type": "timed", "hours": 48}
        },
        "automatic_leave": {
            "waiting_room_timeout": 300,
            "everyone_left_timeout": 60,
            "in_call_recording_timeout": 7200,
            "recording_permission_denied_timeout": 10
        }
    })
    resp.raise_for_status()
    data = resp.json()
    print(f"Bot created: {data['bot_id']}")
    return data["bot_id"]


def get_transcript(bot_id: str) -> dict:
    """Fetch full transcript. Call only after transcription.processed fires."""
    resp = requests.get(f"{BASE_URL}/bots/{bot_id}/get_bot_transcript", headers=HEADERS)
    resp.raise_for_status()
    return resp.json()


@app.route("/webhook", methods=["POST"])
def webhook():
    """Handle MeetStream lifecycle callbacks."""
    event = request.json
    bot_id = event.get("bot_id")
    event_type = event.get("event")
    print(f"Event: {event_type} | Bot: {bot_id}")

    if event_type == "bot.inmeeting":
        print(f"Bot {bot_id} joined the meeting")

    elif event_type == "bot.stopped":
        print(f"Bot {bot_id} left the meeting — waiting for transcript...")

    elif event_type == "transcription.processed":
        print(f"Transcript ready for bot {bot_id}")
        transcript = get_transcript(bot_id)
        # Process transcript here
        for segment in transcript.get("transcript", []):
            print(f"[{segment['speaker']}] {segment['text']}")

    elif event_type == "transcription.failed":
        print(f"Transcription failed for bot {bot_id}: {event.get('message')}")

    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    # Start: create_bot("https://zoom.us/j/123456789", "https://your-ngrok-url.ngrok.io/webhook")
    app.run(port=3000)
```

---

## Pattern 2: Real-Time Transcription (WebSocket)

Streams transcript chunks as words are spoken. Good for AI coaching, live note-taking.

```python
# pip install websockets flask requests asyncio
import asyncio
import json
import os
import requests
import threading
import websockets
from flask import Flask, request, jsonify

app = Flask(__name__)

MEETSTREAM_API_KEY = os.environ["MEETSTREAM_API_KEY"]
BASE_URL = "https://api.meetstream.ai/api/v1"
HEADERS = {
    "Authorization": f"Token {MEETSTREAM_API_KEY}",
    "Content-Type": "application/json"
}

# Store connected WebSocket clients
transcript_clients = set()


def create_realtime_bot(meeting_link: str) -> str:
    """Create a bot with live transcription via WebSocket."""
    resp = requests.post(f"{BASE_URL}/bots/create_bot", headers=HEADERS, json={
        "meeting_link": meeting_link,
        "bot_name": "AI Assistant",
        "audio_required": True,
        "video_required": False,
        "live_transcription_required": {
            "websocket_url": "wss://your-server.com/transcripts"
        },
        "automatic_leave": {
            "waiting_room_timeout": 300,
            "everyone_left_timeout": 60,
            "in_call_recording_timeout": 7200,
            "recording_permission_denied_timeout": 10
        }
    })
    resp.raise_for_status()
    return resp.json()["bot_id"]


async def transcript_handler(websocket):
    """Handle incoming transcript chunks from MeetStream."""
    transcript_clients.add(websocket)
    try:
        async for message in websocket:
            chunk = json.loads(message)
            speaker = chunk.get("speakerName", "Unknown")
            text = chunk.get("transcript", "")
            timestamp = chunk.get("timestamp", "")
            print(f"[{timestamp}] {speaker}: {text}")

            # Add your AI processing here:
            # - Detect questions/objections
            # - Trigger coaching cues
            # - Build live summary
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        transcript_clients.discard(websocket)


async def main():
    async with websockets.serve(transcript_handler, "0.0.0.0", 8765):
        print("WebSocket server running on ws://localhost:8765")
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())
```

---

## Pattern 3: Interactive Bot (Send Messages to the Meeting)

Bot joins and responds to transcript keywords by posting chat messages.

```python
# pip install websockets asyncio
import asyncio
import json
import os
import requests
import websockets

MEETSTREAM_API_KEY = os.environ["MEETSTREAM_API_KEY"]
BASE_URL = "https://api.meetstream.ai/api/v1"
HEADERS = {
    "Authorization": f"Token {MEETSTREAM_API_KEY}",
    "Content-Type": "application/json"
}


def create_interactive_bot(meeting_link: str) -> str:
    resp = requests.post(f"{BASE_URL}/bots/create_bot", headers=HEADERS, json={
        "meeting_link": meeting_link,
        "bot_name": "Meeting Assistant",
        "audio_required": True,
        "video_required": False,
        "socket_connection_url": {"url": "wss://your-server.com/bot-control"},
        "live_transcription_required": {
            "websocket_url": "wss://your-server.com/transcripts"
        },
        "automatic_leave": {
            "everyone_left_timeout": 60,
            "recording_permission_denied_timeout": 10
        }
    })
    resp.raise_for_status()
    return resp.json()["bot_id"]


async def bot_control_handler(websocket):
    """Handle the bot control WebSocket connection."""
    async for message in websocket:
        data = json.loads(message)

        if data.get("type") == "ready":
            bot_id = data["bot_id"]
            print(f"Bot {bot_id} connected and ready")

            # Send a welcome message to the meeting
            await websocket.send(json.dumps({
                "command": "sendmsg",
                "message": "Hi everyone! I'm your meeting assistant. I'll be taking notes today.",
                "bot_id": bot_id
            }))


async def transcript_handler(websocket):
    """Process live transcript and react to keywords."""
    bot_ws = None  # In a real app, maintain a reference to bot_control_handler ws

    async for message in websocket:
        chunk = json.loads(message)
        text = chunk.get("transcript", "").lower()
        speaker = chunk.get("speakerName", "")

        # React to keywords
        if "action item" in text or "follow up" in text:
            print(f"Action item detected from {speaker}: {chunk['transcript']}")
            # Could trigger a message back to the meeting or save to Notion/Jira


async def main():
    control_server = websockets.serve(bot_control_handler, "0.0.0.0", 8766)
    transcript_server = websockets.serve(transcript_handler, "0.0.0.0", 8765)

    async with control_server, transcript_server:
        print("Bot control: ws://localhost:8766")
        print("Transcripts: ws://localhost:8765")
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

# Google OAuth scopes needed
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


def get_google_refresh_token(client_secrets_file: str) -> str:
    """Run OAuth flow to get a refresh token. Run once, save the token."""
    flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, SCOPES)
    creds = flow.run_local_server(port=0)
    return creds.refresh_token


def connect_calendar(refresh_token: str, client_id: str, client_secret: str):
    """Connect Google Calendar to MeetStream."""
    resp = requests.post(f"{BASE_URL}/calendar/create-calendar", headers=HEADERS, json={
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret
    })
    resp.raise_for_status()
    print("Calendar connected! Bots will auto-join all upcoming meetings.")
    return resp.json()


def list_upcoming_events():
    """List upcoming calendar events with their scheduled bot status."""
    resp = requests.get(f"{BASE_URL}/calendar/events", headers=HEADERS)
    resp.raise_for_status()
    events = resp.json()
    for event in events.get("events", []):
        print(f"{event['start']} — {event['title']} ({event['meeting_platform']})")
    return events


def list_scheduled_bots():
    """View all bots scheduled from calendar."""
    resp = requests.get(f"{BASE_URL}/calendar/scheduled", headers=HEADERS)
    resp.raise_for_status()
    return resp.json()


if __name__ == "__main__":
    # Step 1: Get refresh token (run once)
    # token = get_google_refresh_token("client_secrets.json")
    # print(f"Refresh token: {token}")

    # Step 2: Connect calendar
    connect_calendar(
        refresh_token=os.environ["GOOGLE_REFRESH_TOKEN"],
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"]
    )

    # Step 3: View upcoming events
    list_upcoming_events()
```

---

## Pattern 5: Full Note-Taking Agent (Transcript + AI Summary)

Complete server: bot joins, transcribes, generates AI summary after meeting ends.

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


def join_meeting(meeting_link: str) -> str:
    resp = requests.post(f"{BASE_URL}/bots/create_bot", headers=MEETSTREAM_HEADERS, json={
        "meeting_link": meeting_link,
        "bot_name": "Note Taker",
        "audio_required": True,
        "video_required": False,
        "callback_url": "https://your-server.com/webhook",
        "recording_config": {
            "transcript": {
                "provider": {"assemblyai": {"language": "en", "model": "universal"}}
            },
            "retention": {"type": "timed", "hours": 72}
        },
        "automatic_leave": {
            "waiting_room_timeout": 300,
            "everyone_left_timeout": 60,
            "in_call_recording_timeout": 7200,
            "recording_permission_denied_timeout": 10
        }
    })
    resp.raise_for_status()
    return resp.json()["bot_id"]


def fetch_and_summarize(bot_id: str):
    # Fetch transcript
    resp = requests.get(
        f"{BASE_URL}/bots/{bot_id}/get_bot_transcript",
        headers=MEETSTREAM_HEADERS
    )
    resp.raise_for_status()
    transcript_data = resp.json()

    # Format for LLM
    formatted = "\n".join(
        f"{seg['speaker']}: {seg['text']}"
        for seg in transcript_data.get("transcript", [])
    )

    # Generate summary
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

    # Save to file or send to Notion/Slack/email
    with open(f"summary_{bot_id}.txt", "w") as f:
        f.write(summary)

    return summary


@app.route("/webhook", methods=["POST"])
def webhook():
    event = request.json
    event_type = event.get("event")
    bot_id = event.get("bot_id")

    if event_type == "transcription.processed":
        print(f"Generating summary for bot {bot_id}...")
        fetch_and_summarize(bot_id)

    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    app.run(port=3000)
```
