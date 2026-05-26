---
name: meetstream
description: >
  Build meeting intelligence with MeetStream's bot API. Use this skill whenever a developer
  wants to: join a meeting with a bot, record or transcribe meetings, stream live audio/video,
  build AI coaching tools, note-taking agents, CRM auto-update pipelines, calendar automation,
  or anything that processes meeting data programmatically. Supports Zoom, Google Meet, and
  Microsoft Teams. Activate on any mention of MeetStream, meeting bots, recording meetings
  via API, live transcription, "joining a meeting programmatically", or "build me a notetaker".
  When the user asks to BUILD or CREATE an integration, always enter plan mode first using the
  superpowers:writing-plans skill before writing any code.
mcp_server: https://docs.meetstream.ai/_mcp/server
---

# MeetStream Developer Skill

You are a MeetStream integration expert. Your job is to build **complete, production-ready implementations** — not outlines or pseudocode.

All endpoints and schemas in this skill are verified against `docs.meetstream.ai`. When in doubt, fetch the latest from `https://docs.meetstream.ai/<path>.md` (append `.md` to any docs page URL for clean markdown) or use the MCP server.

---

## Step 0: Before Writing Any Code

**If the user asks you to BUILD, CREATE, IMPLEMENT, or SET UP a MeetStream integration:**

1. Invoke the `superpowers:writing-plans` skill first
2. Create the project folder if it doesn't exist
3. Read `references/code-patterns-node.md` or `references/code-patterns-python.md` for the relevant patterns
4. Write the full plan to `docs/superpowers/plans/YYYY-MM-DD-<feature-name>.md`
5. Offer subagent-driven vs inline execution

**Skip plan mode only if** the user explicitly says "quick snippet", "just show me", or "skip planning".

**If the user just has a question** (how does X work, what's the API for Y) — answer directly, no plan needed.

---

## Setup: One Line of Config

All MeetStream API calls need this header:
```
Authorization: Token YOUR_API_KEY
```

API keys are created at https://app.meetstream.ai/api-keys.

Base URL: `https://api.meetstream.ai/api/v1/`

Default language: **Python** unless the user specifies otherwise.

---

## Gathering Requirements

Before planning or building, ask:
1. **API key** — if not provided, ask. Link: https://app.meetstream.ai/api-keys
2. **Platform** — Google Meet, Teams, Zoom, or all? (Zoom needs extra setup)
3. **Language** — Python or Node.js/TypeScript?
4. **Use case** — see patterns below

---

## Use Case Patterns

Map the user's request to one of these, then read the relevant code pattern file for the full implementation.

### Pattern 1: Record + Transcript (most common)
Bot joins, records, transcript fetched post-meeting.

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

Returns `{ "bot_id": "...", "transcript_id": "...", "meeting_url": "...", "status": "..." }` (HTTP 201).

Wait for the `transcription.processed` webhook, then:
```
GET /transcript/{transcript_id}/get_transcript
```

The `transcript_id` is returned in the create_bot response. You can also discover transcript IDs after the fact via `GET /bots/{bot_id}/transcriptions`, or read `bot_details.transcript_id` from `GET /bots/{bot_id}/detail`.

> **Alternate path observed in some deployments:** `GET /bots/{bot_id}/get_bot_transcript/{transcript_id}` has been seen to return transcripts as well. If `/transcript/{transcript_id}/get_transcript` 404s in your deployment, try this fallback.

### Pattern 2: Real-Time Transcription (AI agents, live coaching)
Live transcription is delivered via **HTTPS webhook** (POST), not WebSocket.

```json
{
  "live_transcription_required": { "webhook_url": "https://your-server.com/live-transcript" },
  "recording_config": {
    "transcript": {
      "provider": { "deepgram_streaming": { "model": "nova-2", "language": "en", "punctuate": true } }
    }
  }
}
```

Each POST to your `webhook_url`:
```json
{
  "bot_id": "8ceabf49-...",
  "speakerName": "Alice",
  "timestamp": "2026-01-24T17:00:30.354452",
  "new_text": "Can",
  "transcript": "Can you walk me through",
  "words": [{ "word": "Can", "start": 0.2, "end": 0.5, "confidence": 0.99, "speaker": "Alice", "word_is_final": false }],
  "end_of_turn": false,
  "transcription_mode": "word_level"
}
```

For raw live audio/video bytes, use the WebSocket endpoints:
```json
{
  "live_audio_required":  { "websocket_url": "wss://your-server.com/audio" },
  "live_video_required":  { "websocket_url": "wss://your-server.com/video" }
}
```

### Pattern 3: Interactive Bot (chat messages, TTS audio, images)
Bot opens a WebSocket back to your server for two-way control.

```json
{ "socket_connection_url": { "websocket_url": "wss://your-server.com/bot-control" } }
```

On join, the bot connects to your WSS and sends:
```json
{ "type": "ready", "bot_id": "...", "message": "Ready to receive messages" }
```

You then push commands. The `sendaudio` command requires raw PCM16 LE audio at 48000 Hz mono, base64-encoded (no WAV header):
```json
{
  "command": "sendaudio",
  "bot_id": "...",
  "audiochunk": "<base64-encoded raw PCM16 LE bytes>",
  "sample_rate": 48000,
  "encoding": "pcm16",
  "channels": 1,
  "endianness": "little"
}
```

For chat messages and images, use the REST endpoints (not the WebSocket):
```
POST /bots/{bot_id}/send_message    body: { "message": "...", "metadata": { "message_type": "..." } }
POST /bots/{bot_id}/send_image      body: { "image_url": "...", "metadata": { "message_type": "..." } }
```

### Pattern 4: Calendar-Automated Bot
Bot auto-joins every Google Calendar meeting — no per-meeting API calls.

```
POST /calendar/create_calendar
{
  "google_refresh_token": "...",
  "google_client_id": "...",
  "google_client_secret": "..."
}
```

> Field names use the `google_` prefix. Plain `refresh_token`, `client_id`, `client_secret` will be rejected.

List calendars: `GET /calendar`
List upcoming events: `GET /calendar/events`
Manually schedule a specific event: `POST /calendar/schedule/{event_id}`
Reschedule a scheduled bot: `PATCH /calendar/scheduled_bots/{bot_id}`
Delete a scheduled bot: `DELETE /calendar/scheduled_bots/{bot_id}`

### Pattern 5: Note-Taker (full pipeline)
Webhook server + bot creation + transcript fetch + AI summary + delivery (email/Slack/Notion).

Read `references/code-patterns-node.md` Pattern 4 for the complete Next.js implementation.
Build plan should include: webhook handler, transcript fetch, LLM summary, delivery layer.

### Pattern 6: Participant Tracking (real-time)
Real-time join/leave events during the meeting:

```json
{
  "recording_config": {
    "realtime_endpoints": [{
      "type": "webhook",
      "url": "https://your-server.com/participants",
      "events": ["participant_events.join", "participant_events.leave"]
    }]
  }
}
```

---

## Bot Lifecycle

```
create_bot → bot.joining → bot.inmeeting → [streams run]
→ bot.stopped → audio.processed → transcription.processed → fetch data
```

Notes:
- Every bot starts with `bot.joining`. If join succeeds you get `bot.inmeeting`; if it fails you may get `bot.stopped` directly (no `bot.inmeeting`).
- `bot.inmeeting` and `bot.stopped` are sent **at most once** each.
- Post-call events (`audio.processed`, `transcription.processed`, `video.processed`, `data_deletion`) arrive asynchronously after `bot.stopped`, each at most once.
- **Never fetch the transcript before `transcription.processed` fires.** Always set `callback_url`.

---

## Required Fields

`meeting_link` and `bot_name` are **required** on `create_bot`. Omitting `bot_name` returns HTTP 400.

`video_required` defaults to **`true`** (the bot records video unless you opt out). To save storage and bandwidth for transcript-only workflows, set `video_required: false`.

There is **no `audio_required` parameter** — audio is captured by default. (`audio_separate_streams` exists for per-participant audio and is a different feature.)

---

## Always Include These Timeouts

```json
{
  "automatic_leave": {
    "waiting_room_timeout": 600,
    "everyone_left_timeout": 300,
    "voice_inactivity_timeout": 100,
    "in_call_recording_timeout": 14400,
    "recording_permission_denied_timeout": 60
  }
}
```

All values in seconds. Defaults shown above:
- `waiting_room_timeout` — wait in waiting room before leaving (default 600 / 10 min)
- `everyone_left_timeout` — stay after everyone else leaves (default 300 / 5 min)
- `voice_inactivity_timeout` — wait if no audio is detected (default 100)
- `in_call_recording_timeout` — max recording duration (default 14400 / 4 hr)
- `recording_permission_denied_timeout` — wait if recording permission denied (default 60, **Zoom-only**)

**Live-tested gotcha:** `recording_permission_denied_timeout` has been observed to reject values below 60 with HTTP 400 in practice. Stick with 60 or higher.

Without these, a stuck bot can sit in a meeting indefinitely.

---

## Bot Avatar (`bot_image_url`)

Custom profile picture must be a **publicly accessible URL** — MeetStream fetches it externally. Base64 / data URIs are not supported, and the image must be reachable without authentication. If you store images in Firestore or another private store, serve them from a public HTTP endpoint first.

```json
{ "bot_image_url": "https://your-server.com/avatar.png" }
```

---

## `custom_attributes` Constraint

All `custom_attributes` values must be **strings**. Numbers, booleans, and nested objects will be rejected. Stringify before sending:

```json
{ "custom_attributes": { "deal_id": "12345", "active": "true", "score": "0.87" } }
```

---

## Platform Notes

| Platform | Extra Setup |
|----------|-------------|
| Google Meet | None |
| Microsoft Teams | None |
| Zoom | Register a Zoom app + add credentials to MeetStream dashboard → https://docs.meetstream.ai/guides/zoom/zoom-marketplace-app-setup |

**Zoom dev mode** restricts bots to meetings hosted by the app owner's account. For external meetings, submit the Zoom app to production.

For Zoom OBF (On-Behalf-Of), pass `"zoom": { "use_zoom_obf": true }` on `create_bot`.

---

## Transcription Providers

Specified under `recording_config.transcript.provider`. Use **exactly one** provider per bot.

| Provider key | Mode | Best for |
|---|---|---|
| `meetstream` | Post-call | MeetStream's in-house engine — speaker-labeled, low cost |
| `deepgram` | Post-call | High accuracy, `nova-3` model (requires `language: "en"`) |
| `assemblyai` | Post-call | Speaker diarization, redaction, chapters |
| `sarvam` | Post-call | Indic languages (`saaras:v3`) |
| `jigsawstack` | Post-call | Auto language detect, translation |
| `meeting_captions` | Live, native | Free; uses Meet / Teams native captions |
| `deepgram_streaming` | Live | Real-time, `nova-2` model |
| `assemblyai_streaming` | Live | Real-time English (`universal-streaming-english`) |

See `references/code-patterns-python.md` and the docs for each provider's full config schema (model, language, diarize, smart_format, vad_threshold, etc.).

---

## Webhook Handler Requirements

- Must use HTTPS (use ngrok / cloudflared for local dev: `ngrok http 3000`)
- Must respond `2xx` quickly to acknowledge receipt
- **No automatic retries.** If your endpoint returns non-2xx, the webhook is **not** retried. Build your handler to never fail (catch errors, queue work, return 200).
- `bot.joining` may fire up to 3 times if join retries are configured. `bot.inmeeting`, `bot.stopped`, `audio.processed`, `transcription.processed`, `video.processed`, and `data_deletion` are sent **at most once**.

### Webhook payload shape

```json
{
  "event": "bot.joining",
  "bot_id": "6667fd0c-0165-471a-a880-06a1180be377",
  "bot_status": "Joining",
  "message": "Bot is joining the meeting",
  "status_code": 200,
  "timestamp": "2026-02-27T07:11:51.863543+00:00",
  "custom_attributes": {}
}
```

`status_code` is **always 200** for every event. Don't branch on it — branch on `event` and `bot_status`.

### Event types

| event | When it fires |
|---|---|
| `bot.joining` | Bot is connecting |
| `bot.inmeeting` | Bot joined and is recording |
| `bot.stopped` | Bot lifecycle ended (read `bot_status` for reason) |
| `audio.processed` | Audio ready (`audio_status: "Success"`) |
| `transcription.processed` | Transcript ready (`transcript_status: "Success"`) |
| `video.processed` | Video ready (`video_status: "Success"`) |
| `data_deletion` | Bot data deleted (retention or manual) |

### `bot_status` values on `bot.stopped`

| bot_status | Meaning |
|---|---|
| `Stopped` | Normal exit (meeting ended, removed via API, everyone left, voice timeout, host removed) |
| `NotAllowed` | Could not join (typically waiting room / lobby timeout) |
| `Denied` | Host denied join or recording permission |
| `Error` | Unexpected error during lifecycle |

Failures are surfaced via `bot_status` on `bot.stopped` — there are no `audio.failed` / `transcription.failed` / `video.failed` events.

### Webhook signature verification (optional but recommended)

If a webhook secret is configured, MeetStream includes:
- `X-MeetStream-Signature: sha256=<hex_digest>`
- `X-MeetStream-Timestamp: <iso8601>`

Verify: compute `HMAC-SHA256(secret, raw_request_body)`, compare against the signature (strip `sha256=`), optionally check the timestamp is within an acceptable window.

---

## Data Available After Meeting

After the relevant `*.processed` event fires:

| Data | Endpoint |
|------|---------|
| Transcript (full, formatted) | `GET /transcript/{transcript_id}/get_transcript` |
| List transcripts for a bot | `GET /bots/{bot_id}/transcriptions` |
| Trigger a new transcription run | `POST /bots/{bot_id}/transcribe` |
| Speaker timeline | `GET /bots/{bot_id}/get_speaker_timeline` |
| In-meeting chat | `GET /bots/{bot_id}/get_chats` |
| Audio file | `GET /bots/{bot_id}/get_audio` (pre-signed S3 URL, 1 hr) |
| Video file | `GET /bots/{bot_id}/get_video` (pre-signed S3 URL, 10 min) |
| Per-participant audio streams | `GET /bots/{bot_id}/get_audio_streams` |
| Per-participant recording streams | `GET /bots/{bot_id}/get_recording_streams` |
| Participant list | `GET /bots/{bot_id}/get_participants` |
| Session metadata | `GET /bots/{bot_id}/detail` |
| Screenshots | `GET /bots/{bot_id}/get_screenshots` |
| Summary (if generated) | `GET /bots/{bot_id}/get_summary` |

Bot management:
- Status: `GET /bots/{bot_id}/status`
- List bots: `GET /bots`
- Remove from active meeting: `GET /bots/{bot_id}/remove_bot`
- Delete data: `DELETE /bots/{bot_id}/delete` → fires `data_deletion` webhook

---

## Data Retention

Default retention is **24 hours**. Override on `create_bot`:

```json
{ "recording_config": { "retention": { "type": "timed", "hours": 168 } } }
```

Manually delete: `DELETE /bots/{bot_id}/delete` — fires the `data_deletion` callback when complete.

---

## Common Mistakes

1. **Fetching transcript too early** — always wait for `transcription.processed`.
2. **HTTP callback URL** — must be HTTPS; use ngrok for local dev.
3. **Wrong calendar field names** — Calendar create requires `google_refresh_token` / `google_client_id` / `google_client_secret` (with the `google_` prefix).
4. **Using `audio_required`** — this field does not exist. Audio is captured by default.
5. **Skipping `bot_name`** — it's required, not optional.
6. **Assuming `video_required` defaults to false** — it defaults to `true`. Set it to `false` for transcript-only workflows or you'll burn storage.
7. **Branching on `status_code`** — it's always 200. Branch on `event` and `bot_status`.
8. **Expecting webhook retries** — there are none. Always return 2xx, queue work asynchronously.
9. **Using `websocket_url` for live transcription** — `live_transcription_required` accepts only `webhook_url` (HTTPS POST). The `websocket_url` field is for `live_audio_required`, `live_video_required`, and `socket_connection_url`.
10. **Sending WAV blobs over `sendaudio`** — bot expects raw PCM16 LE @ 48000 Hz mono, base64-encoded. No WAV header.

---

## Code Reference Files

Read these when building:
- `references/code-patterns-node.md` — complete Node.js/TypeScript implementations
- `references/code-patterns-python.md` — complete Python implementations
- `references/api-reference.md` — full endpoint map with params and return types

---

## MCP Server

For specific endpoint parameters, response schemas, or edge cases not covered above:
```
https://docs.meetstream.ai/_mcp/server
```

Or fetch any docs page as clean markdown by appending `.md` to its URL:
```
https://docs.meetstream.ai/api-reference/api-endpoints/bot-endpoints/create-bot.md
```
