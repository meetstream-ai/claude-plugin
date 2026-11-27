# Use case patterns: Use Case Patterns

> Part of [`use-case-patterns.md`](use-case-patterns.md), split so each file stays under 20 KB.

## Use Case Patterns

Map the user's request to one of these. Each gives the calls and payloads; build them into the user's code.

### Pattern 1: Record + Transcript (most common)

Bot joins, records audio, transcript fetched post-meeting.

```json
POST /bots/create_bot
{
  "meeting_link": "https://zoom.us/j/123456789",
  "bot_name": "Recorder",
  "video_required": false,
  "callback_url": "https://your-server.com/webhook",
  "recording_config": {
    "transcript": {
      "provider": { "deepgram": { "language": "en", "model": "nova-3" } }
    },
    "retention": { "type": "timed", "hours": 48 }
  }
}
```

Returns **HTTP 201 Created** with `BotResponse`:
```json
{
  "bot_id": "...",
  "transcript_id": "..." | null,
  "meeting_url": "...",
  "status": "Active"
}
```

**How to fetch the transcript - canonical pattern:**

1. Wait for the `transcription.processed` webhook (signals readiness - but does **not** contain `transcript_id`)
2. Call `GET /bots/{bot_id}/detail` → read `bot_details.transcript_id`
3. Call `GET /transcript/{transcript_id}/get_transcript`

This is **stateless** - no need to store `transcript_id` from `create_bot`. The webhook gives you `bot_id`; you derive the rest.

```python
# The whole flow, after the transcription.processed webhook fires:
detail = requests.get(f"{BASE}/bots/{bot_id}/detail", headers=H).json()
tid = detail["bot_details"]["transcript_id"]
resp = requests.get(f"{BASE}/transcript/{tid}/get_transcript", headers=H)
if resp.status_code == 200:
    segments = resp.json()        # ← list (top-level array)
elif resp.status_code == 202:
    msg = resp.json()             # ← dict: {"message": "Transcript is still being processed. ..."}
    # transcript not ready yet - back off and retry, or wait for next webhook
```

> **Live-verified response shapes from `/transcript/{tid}/get_transcript`:**
> - **HTTP 200** → top-level JSON **array** of segment objects (success case)
> - **HTTP 202** → JSON **object** `{"message": "Transcript is still being processed. Current status: <state>"}` - transcript_id exists but isn't ready. Always check status code before iterating.
> - **HTTP 422** → the transcript run failed (API v1.10.0). The body gives the status and the reason: `{"message": "Transcript processing failed: <reason>", "transcript_status": "Failed", "transcript_id": "..."}` (for example the provider rejected the API key, or the usage limit was reached). It is final: do not retry it. Show the reason, fix the cause, then start a new run with `POST /bots/{bot_id}/transcribe`. Provider rejections are not retried by MeetStream either.
> - Streaming-only providers never make a post-call transcript; for them the fetch keeps returning 202, so every polling loop needs a cap.
>
> **Three status indicators disagree on failure** (live-verified, treat the first as authoritative):
> | Source | Value on transcript failure |
> |---|---|
> | `bot_details.TranscriptStatus` | `"Failed"` ← **authoritative** |
> | `/transcriptions[].status` | `"Not started"` (stale) |
> | `/transcript/{tid}/get_transcript` HTTP | `422` with the reason |
>
> **Always check `bot_details.TranscriptStatus` before retrying, or watch for the `transcription.failed` webhook** to break out of the polling loop:
>
> ```python
> def fetch_transcript_safely(bot_id: str, max_polls: int = 30):
>     for _ in range(max_polls):
>         detail = requests.get(f"{BASE}/bots/{bot_id}/detail", headers=H).json()
>         ts = detail["bot_details"].get("TranscriptStatus")
>         if ts == "Failed":
>             raise RuntimeError(f"Transcript failed for {bot_id}")
>         if ts == "Success":
>             tid = detail["bot_details"]["transcript_id"]
>             resp = requests.get(f"{BASE}/transcript/{tid}/get_transcript", headers=H)
>             if resp.status_code == 200:
>                 return resp.json()  # top-level array
>             if resp.status_code == 422:  # final failure: stop, show the reason
>                 raise RuntimeError(resp.json().get("message"))
>         time.sleep(2)
>     raise TimeoutError("Transcript not ready")
> ```

**Where `transcript_id` lives - all four live-verified sources:**

| Source | When to use |
|---|---|
| `bot_details.transcript_id` on `GET /bots/{bot_id}/detail` | **Canonical / default path.** Stateless - `bot_id` from webhook is all you need. |
| `BotResponse.transcript_id` in `create_bot` response | Available immediately on bot creation if you want to log it; not required. |
| `GET /bots/{bot_id}/transcriptions` | Only when you've called `POST /bots/{bot_id}/transcribe` to re-transcribe with a different provider and need to list all runs. |
| `POST /bots/{bot_id}/transcribe` response | When triggering a fresh transcription run. |

For provider `meeting_captions`, all four give `transcript_id: null` - fetch the S3 caption file from `bot_details.caption_file` on `/detail` instead.

**`transcript_id` is NOT in any webhook payload.** The `transcription.processed` webhook contains only `bot_id`, `event`, `transcript_status`, `message`, `status_code`. Use the canonical `/detail` pattern above to resolve it.

Once you receive the `transcription.processed` webhook, fetch:
```
GET /transcript/{transcript_id}/get_transcript
```

The response is a **top-level JSON array** of segment objects (participant-keyed, the default):
```json
[
  {
    "participant": { "id": 100, "name": "Alice", "platform": "desktop", "extra_data": {} },
    "words": [
      { "text": "Hello everyone, let's get started.",
        "start_timestamp": { "relative": 0.5, "absolute": null },
        "end_timestamp": { "relative": 3.2, "absolute": null } }
    ],
    "language_code": "en"
  }
]
```

Read it this way: the speaker is `participant.name`, the text is the `words[].text` values
joined with spaces, and the start time is `words[0].start_timestamp.relative` (seconds).
This participant-keyed format is the default whenever it exists. Some providers return the
segment-list format instead (`speaker`, `transcript`, `start_time`, `end_time`, `words`
with `word` / `punctuated_word`), so a parser should read both. Skip segments with no text.
The `meetstream` engine can add a lone "Thank you." segment on silence; treat it as filler. The response is the array itself, not `{transcript: [...]}`.

For raw provider output (unformatted), add `?raw=true`.

### Pattern 2: Real-Time Transcription (AI agents, live coaching)

Live transcription is delivered via **HTTPS webhook** (POST) - not WebSocket.

> **Live-verified prerequisite:** `live_transcription_required.webhook_url` REQUIRES a streaming provider in `recording_config.transcript.provider`. The live API returns `HTTP 400: "live_transcription_required.webhook_url is provided but no streaming provider found. Please provide at least one streaming provider (deepgram_streaming, assemblyai_streaming, jigsawstack_streaming, meetstream_streaming, or meeting_captions)."` if you set the webhook URL without one.

Five known streaming providers (live-verified from server error message):
- `deepgram_streaming` (requires external Deepgram API key in your MeetStream account)
- `assemblyai_streaming` (requires external AssemblyAI API key)
- `jigsawstack_streaming`
- `meetstream_streaming` - MeetStream in-house, no external key required (works on stock accounts)
- `meeting_captions` - Google Meet / Teams native captions (free)

```json
{
  "live_transcription_required": { "webhook_url": "https://your-server.com/live-transcript" },
  "recording_config": {
    "transcript": {
      "provider": {
        "deepgram_streaming": {
          "transcription_mode": "sentence",
          "model": "nova-2",
          "language": "en",
          "punctuate": true,
          "smart_format": true,
          "endpointing": 300,
          "vad_events": true,
          "utterance_end_ms": 1000,
          "encoding": "linear16",
          "channels": 1
        }
      }
    }
  }
}
```

For accounts without external provider keys, swap in `meetstream_streaming: {}` - empty config is accepted.

**Note:** Streaming-only providers (`meetstream_streaming`, `meeting_captions`, the `_streaming` variants) do NOT produce a post-call transcript via `/transcript/{tid}/get_transcript`. `create_bot` returns `transcript_id: null` (for `meeting_captions`) or a transcript_id that fetch returns HTTP 202 forever (for `meetstream_streaming`). Use the live webhook stream as the canonical record - don't expect a post-call fetch.

Each POST to your `webhook_url`:
```json
{
  "bot_id": "305e708e-...",
  "speakerName": "Alice",
  "timestamp": "2026-05-26T10:21:43.681Z",
  "transcript": "Can you walk me through",
  "utterance": "",
  "words": [{ "word": "Can", "start": 0.2, "end": 0.5, "confidence": 0.99, "speaker": "Alice", "punctuated_word": "Can", "speech_confidence": 0.99 }],
  "is_final": false,
  "end_of_turn": false,
  "turn_is_formatted": false,
  "transcription_mode": "raw",
  "custom_attributes": {}
}
```

For raw live audio bytes (binary frames over WebSocket), see Pattern 7 below. Live video out of a meeting bot is not available (Pattern 8).

### Pattern 3: Interactive Bot (chat, TTS audio, dynamic video frame)

Bot opens a WebSocket back to your server for two-way control:

```json
{ "socket_connection_url": { "websocket_url": "wss://your-server.com/bot-control" } }
```

On join the bot sends a JSON handshake:
```json
{ "type": "ready", "bot_id": "...", "message": "Ready to receive messages" }
```

Then you push **JSON commands** over that WebSocket (each carries `bot_id`). The documented commands:

| Command | Purpose |
|---|---|
| `sendaudio` | Play raw PCM16 LE audio (48 kHz mono, base64-encoded) through the bot's mic |
| `sendmsg` | Post a chat message (requires BOTH `message` AND `msg` fields with the same value, for cross-platform compat) |
| `interrupt` | Stop bot audio playback and clear the queue (`{action: "clear_audio_queue"}`). On Zoom and Teams it then holds further audio until `resume_audio` |
| `resume_audio` | Allow audio again after an interrupt (`resume_id`, any string). Google Meet ignores it, so send it before each new reply on every platform |
| `sendimg` / `sendimg_url` | Set bot's **video frame** to an image (base64 via `img`, or URL via `img_url`). Zoom and Teams; on Google Meet use `send_image` |

For chat / images **into the chat panel only** (not video frame), there are also REST endpoints:
```
POST /bots/{bot_id}/send_message    body: { "message": "...", "metadata": { "message_type": "text" } }
POST /bots/{bot_id}/send_image      body: { "img_url": "https://...", "display_duration": 5, "metadata": {...} }
POST /bots/{bot_id}/pause_recording   (empty body - suspend recording mid-meeting; bot stays in the call)
POST /bots/{bot_id}/resume_recording  (empty body - resume a paused recording)
```

> **`send_image` field is `img_url`** (not `image_url`). `display_duration` (integer seconds) is optional.

Image URLs the bot downloads (`img_url`, `sendimg_url`, `bot_image_url`, `initial_audio.url`) must resolve to public addresses on every redirect hop. A URL that resolves to a private, loopback or metadata address is refused when the bot fetches it (no 400 at request time, the image just never appears).

To make the bot raise or lower its hand, use the REST `send_command` endpoint (see In-Meeting Commands in `skills/sending-bots/references/bot-config.md`), not the WebSocket.

Message formats for every command (chunked audio, barge-in, streaming chat): https://docs.meetstream.ai/guides/websockets/meeting-control-patterns

### Pattern 4: Calendar-Automated Bot

Connect Google Calendar so MeetStream auto-handles event sync, scheduling, recurring events, change detection, and watch channel renewal.

**Connect:**
```
POST /calendar/create_calendar
{
  "google_refresh_token": "...",
  "google_client_id": "...",
  "google_client_secret": "..."
}
```

Field names use the `google_` prefix. All three are required. Plain `refresh_token` / `client_id` / `client_secret` will be rejected by the OpenAPI schema.

**Endpoints (full list from docs):**

| Method | Path | Purpose |
|---|---|---|
| POST | `/calendar/create_calendar` | Connect a Google Calendar |
| GET | `/calendar/calendars` | List connected calendars (live from Google) |
| GET | `/calendar/events` | Sync + list events with pagination + bot info |
| GET | `/calendar/get_events` | List events from local DB only (faster, no Google call) |
| POST | `/calendar/schedule/{event_id}` | Schedule a bot for an event (body: `bot_config`, `occurrence_date`, `schedule_all_occurrences`, `occurrence_limit`, `recurring_event`) |
| DELETE | `/calendar/schedule/{event_id}` | Unschedule an event (body: `cancel_all_occurrences`, `from_date`) |
| GET | `/calendar/scheduled_bots` | List all upcoming scheduled bots |
| PATCH | `/calendar/scheduled_bots/{bot_id}` | Update a scheduled bot (`scheduled_join_time`, `bot_username`, `custom_attributes`) |
| DELETE | `/calendar/scheduled_bots/{bot_id}` | Delete a single scheduled bot |
| POST | `/calendar/auto-schedule/enable` | Enable auto-scheduling (body: `default_bot_config`) |
| POST | `/calendar/auto-schedule/disable` | Disable auto-scheduling |
| GET | `/calendar/auto-schedule/settings` | Read current auto-schedule settings |
| POST | `/calendar/auto-reschedule` | Trigger reschedule for next recurring occurrence |
| POST | `/calendar/toggle-recurrence` | Enable/disable auto-rescheduling per event (body: `{event_id, recurring_enabled}`) |

> **Disconnect:** use `DELETE /calendar/disconnect` - that's what the docs guide, cURL example, and response example all show. Returns `{disconnected, user_id, watch_channel_stopped, events_deleted, schedules_cancelled, message}`. Irreversible - stops watch channels, cancels pending schedules, deletes synced events, removes Google OAuth credentials. (The OpenAPI spec shows POST as a quirk; disregard.)

**Auto-scheduling behavior:** job runs every 24h at midnight UTC, schedules bots for the next 24h, joins 1 minute before meeting start. Real-time push notifications from Google Calendar handle reschedules and cancellations. Watch channels auto-renew every ~6 days (a daily background job renews any expiring within 2 days).

**Recurring events / RRULE:** standard iCalendar rules supported (DAILY/WEEKLY/MONTHLY, BYDAY, COUNT, UNTIL). Schedule with `recurring_event: true` to auto-reschedule after each occurrence, or `schedule_all_occurrences: true` (with optional `occurrence_limit`, default 52) to batch-schedule.

**Deduplication:** scheduling the same event twice returns **HTTP 409** with the existing bot's ID. Use `PATCH /calendar/scheduled_bots/{bot_id}` to update.

### Pattern 5: Note-Taker (full pipeline)

Webhook server + bot creation + transcript fetch + AI summary + email delivery.

Fastest path: Pattern 1 (create the bot with a `callback_url`, fetch the transcript after `transcription.processed`), then summarize in the user's app. The webhook handler returns 200 fast and is idempotent. Details in the `building-a-notetaker` skill. Full example apps (optional): https://docs.meetstream.ai/tutorials/sample-apps

### Pattern 6: Participant Tracking (real-time)

Real-time join/leave and raise/lower hand events during the meeting:

```json
{
  "recording_config": {
    "realtime_endpoints": [{
      "type": "webhook",
      "url": "https://your-server.com/participants",
      "events": [
        "participant_events.join",
        "participant_events.leave",
        "participant_events.raise_hand",
        "participant_events.lower_hand"
      ]
    }]
  }
}
```

**Hand events** (`participant_events.raise_hand` / `participant_events.lower_hand`, Google Meet and Zoom):
- Opt-in per bot: they go **only** to `realtime_endpoints` entries that list them. Workspace webhooks never receive them.
- Same nested shape as `participant_events.join`, with `data.data.action` set to `"raise_hand"` or `"lower_hand"`.
- Transitions only. The bot's own hand is never reported. "Lower all hands" sends one `lower_hand` per raised hand. A participant who leaves with a hand up gets no `lower_hand`, so clear their state on `participant_events.leave`.

### Pattern 7: Live Audio Streaming (binary frames)

Real-time PCM audio with embedded speaker metadata over a WebSocket you host:

```json
{ "live_audio_required": { "websocket_url": "wss://your-server.com/audio" } }
```

The bot connects to your WSS, sends a JSON `ready` handshake, then streams **binary frames** with this exact wire format:

Read byte 0 first; every platform can send either audio type (live Google Meet bots send
one `0x01` frame and then `0x04` frames):

| Type | Header | Speaker fields start at |
|---|---|---|
| `0x01` | `[type:1]`, PCM16 LE, 48 kHz mono | offset 1 |
| `0x04` | `[type:1][sample_rate:4, uint32 LE][channels:1]` | offset 6 |

Then `sid_length` (uint16 LE), `speaker_id`, `sname_length` (uint16 LE), `speaker_name`,
then raw PCM16 LE samples (no container). Skip any other type. Duration =
`len(pcm) / 2 / channels / sample_rate`.

```python
import struct
def decode(data: bytes):
    if data[0] == 0x01:
        rate, ch, off = 48000, 1, 1
    elif data[0] == 0x04:
        rate, ch, off = struct.unpack_from("<I", data, 1)[0], data[5], 6
    else:
        return None                      # unknown type: skip
    n = struct.unpack_from("<H", data, off)[0]; sid = data[off+2:off+2+n].decode(); off += 2 + n
    n = struct.unpack_from("<H", data, off)[0]; name = data[off+2:off+2+n].decode(); off += 2 + n
    return sid, name, rate, ch, data[off:]   # downmix if ch > 1, resample for your STT
```

`speaker_name` is `"NoSpeaker"` when MeetStream cannot attribute the audio (Google Meet
mixed audio often is), so you cannot drop the bot's own voice by name.

Decoders for Python, Node.js, Go and Java: https://docs.meetstream.ai/guides/websockets/real-time-audio-streaming
