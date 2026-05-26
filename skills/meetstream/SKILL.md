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

> **Source of truth:** every endpoint, field, and payload in this skill is verified against `docs.meetstream.ai`. If you need something that isn't here, fetch it from `https://docs.meetstream.ai/<path>.md` (append `.md` to any docs page URL for clean markdown) or via the MCP server at `https://docs.meetstream.ai/_mcp/server`. Do not invent endpoints or fields.

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

## Setup

All MeetStream API calls need this header:
```
Authorization: Token YOUR_API_KEY
```

API keys are created at https://app.meetstream.ai/api-keys.

Base URL: `https://api.meetstream.ai/api/v1` (no trailing slash in canonical examples).

Default language: **Python** unless the user specifies otherwise.

---

## Gathering Requirements

Before planning or building, ask:
1. **API key** — if not provided, ask. Link: https://app.meetstream.ai/api-keys
2. **Platform** — Google Meet, Teams, Zoom, or all? (Zoom needs extra setup; see Platform Notes)
3. **Language** — Python or Node.js/TypeScript?
4. **Use case** — match to one of the patterns below

---

## Required Fields on `create_bot`

Per the OpenAPI `CreateBotRequest` schema, only two fields are required:

- `meeting_link` (string) — Zoom, Google Meet, or Teams URL
- `bot_name` (string) — the display name shown in the meeting

`video_required` defaults to **`true`** (the bot records video unless you opt out). Set `video_required: false` for transcript-only workflows.

There is **no `audio_required` field** on `CreateBotRequest`. Audio is recorded by default. (`audio_separate_streams` is a different feature that enables per-participant audio tracks.)

> **Note:** `audio_required` DOES exist for **calendar-scheduled** bots — inside `bot_config` on `POST /calendar/schedule/{event_id}`, the auto-schedule `default_bot_config`, etc. The "doesn't exist" rule only applies to `create_bot`.

---

## Use Case Patterns

Map the user's request to one of these, then read the relevant code pattern file for the full implementation.

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

**How to fetch the transcript — canonical pattern:**

1. Wait for the `transcription.processed` webhook (signals readiness — but does **not** contain `transcript_id`)
2. Call `GET /bots/{bot_id}/detail` → read `bot_details.transcript_id`
3. Call `GET /transcript/{transcript_id}/get_transcript`

This is **stateless** — no need to store `transcript_id` from `create_bot`. The webhook gives you `bot_id`; you derive the rest. Use this everywhere unless you have a specific reason to track ids manually.

```python
# The whole flow, after webhook fires:
detail = requests.get(f"{BASE}/bots/{bot_id}/detail", headers=H).json()
tid = detail["bot_details"]["transcript_id"]
segments = requests.get(f"{BASE}/transcript/{tid}/get_transcript", headers=H).json()
```

**Where `transcript_id` lives — all four live-verified sources:**

| Source | When to use |
|---|---|
| `bot_details.transcript_id` on `GET /bots/{bot_id}/detail` | **Canonical / default path.** Stateless — `bot_id` from webhook is all you need. |
| `BotResponse.transcript_id` in `create_bot` response | Available immediately on bot creation if you want to log it; not required. |
| `GET /bots/{bot_id}/transcriptions` | Only when you've called `POST /bots/{bot_id}/transcribe` to re-transcribe with a different provider and need to list all runs. |
| `POST /bots/{bot_id}/transcribe` response | When triggering a fresh transcription run. |

For provider `meeting_captions`, all four give `transcript_id: null` — fetch the S3 caption file from `bot_details.caption_file` on `/detail` instead.

**`transcript_id` is NOT in any webhook payload.** The `transcription.processed` webhook contains only `bot_id`, `event`, `transcript_status`, `message`, `status_code`. Use the canonical `/detail` pattern above to resolve it.

Once you receive the `transcription.processed` webhook, fetch:
```
GET /transcript/{transcript_id}/get_transcript
```

The response is a **top-level JSON array** of segment objects:
```json
[
  {
    "speaker": "Alice",
    "transcript": "Hello everyone, let's get started.",
    "start_time": 0.5,
    "end_time": 3.2,
    "absolute_start_time": "2026-04-22T10:00:00.500Z",
    "absolute_end_time": "2026-04-22T10:00:03.200Z",
    "words": [{ "word": "Hello", "punctuated_word": "Hello,", "start": 0.5, "end": 0.8, "confidence": 0.99, "speaker": 0, "speaker_confidence": 0.95 }]
  }
]
```

The per-segment text field is **`transcript`**, not `text`. The response is the array itself, not `{transcript: [...]}`.

For raw provider output (unformatted), add `?raw=true`.

### Pattern 2: Real-Time Transcription (AI agents, live coaching)

Live transcription is delivered via **HTTPS webhook** (POST) — not WebSocket.

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

For raw live audio bytes (binary frames over WebSocket), see Pattern 7 below. For raw live video (fMP4 over WebSocket), see Pattern 8.

### Pattern 3: Interactive Bot (chat, TTS audio, dynamic video frame)

Bot opens a WebSocket back to your server for two-way control:

```json
{ "socket_connection_url": { "websocket_url": "wss://your-server.com/bot-control" } }
```

On join the bot sends a JSON handshake:
```json
{ "type": "ready", "bot_id": "...", "message": "Ready to receive messages" }
```

Then you push **JSON commands** over that WebSocket. There are five documented commands:

| Command | Purpose |
|---|---|
| `sendaudio` | Play raw PCM16 LE audio (48 kHz mono, base64-encoded) through the bot's mic |
| `sendmsg` | Post a chat message (requires BOTH `message` AND `msg` fields with the same value, for cross-platform compat) |
| `sendchat` | Chat with role tagging + streaming support (`role`, `text`, `is_final`) |
| `interrupt` | Stop bot audio playback (`{action: "clear_audio_queue"}`) — Google Meet only; Zoom/Teams accept but don't clear |
| `sendimg` / `sendimg_url` | Set bot's **video frame** to an image (base64 via `img`, or URL via `img_url`) |

For chat / images **into the chat panel only** (not video frame), there are also REST endpoints:
```
POST /bots/{bot_id}/send_message    body: { "message": "...", "metadata": { "message_type": "text" } }
POST /bots/{bot_id}/send_image      body: { "img_url": "https://...", "display_duration": 5, "metadata": {...} }
```

> **`send_image` field is `img_url`** (not `image_url`). `display_duration` (integer seconds) is optional.

See `references/code-patterns-python.md` Pattern 3 and `references/code-patterns-node.md` Pattern 3 for full implementations of every command including chunked audio streaming, barge-in, and streaming chat.

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

> **Disconnect calendar method mismatch:** the prose docs say `DELETE /calendar/disconnect` but the OpenAPI spec says `POST /calendar/disconnect` (with `CalendarCreateRequest` body). Try `POST` first; if it returns 405, fall back to `DELETE`.

**Auto-scheduling behavior:** job runs every 24h at midnight UTC, schedules bots for the next 24h, joins 1 minute before meeting start. Real-time push notifications from Google Calendar handle reschedules and cancellations. Watch channels auto-renew every ~6 days (a daily background job renews any expiring within 2 days).

**Recurring events / RRULE:** standard iCalendar rules supported (DAILY/WEEKLY/MONTHLY, BYDAY, COUNT, UNTIL). Schedule with `recurring_event: true` to auto-reschedule after each occurrence, or `schedule_all_occurrences: true` (with optional `occurrence_limit`, default 52) to batch-schedule.

**Deduplication:** scheduling the same event twice returns **HTTP 409** with the existing bot's ID. Use `PATCH /calendar/scheduled_bots/{bot_id}` to update.

### Pattern 5: Note-Taker (full pipeline)

Webhook server + bot creation + transcript fetch + AI summary + delivery (email/Slack/Notion).

See `references/code-patterns-node.md` Pattern 4 (Next.js) or `references/code-patterns-python.md` Pattern 5 (Flask + OpenAI). Build plan should include: webhook handler (returns 200 fast, idempotent), transcript fetch via `transcript_id`, LLM summary, delivery layer.

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

### Pattern 7: Live Audio Streaming (binary frames)

Real-time PCM audio with embedded speaker metadata over a WebSocket you host:

```json
{ "live_audio_required": { "websocket_url": "wss://your-server.com/audio" } }
```

The bot connects to your WSS, sends a JSON `ready` handshake, then streams **binary frames** with this exact wire format:

```
┌──────────┬────────────┬────────────┬──────────────┬──────────────┬──────────────────┐
│ msg_type │ sid_length │ speaker_id │ sname_length │ speaker_name │  pcm_audio_data  │
│ 1 byte   │ 2 bytes    │ L1 bytes   │ 2 bytes      │ L2 bytes     │  remaining bytes │
└──────────┴────────────┴────────────┴──────────────┴──────────────┴──────────────────┘
```

| Offset | Size | Type | Field |
|---|---|---|---|
| 0 | 1 | uint8 | `msg_type` — always `0x01` for PCM audio |
| 1 | 2 | uint16 LE | `sid_length` |
| 3 | L1 | UTF-8 | `speaker_id` |
| 3+L1 | 2 | uint16 LE | `sname_length` |
| 5+L1 | L2 | UTF-8 | `speaker_name` |
| 5+L1+L2 | remaining | int16 LE | raw PCM audio samples |

Audio properties: **signed 16-bit PCM, little-endian, 48 kHz, mono, no container**. Duration = `len(pcm)/2 / 48000` seconds.

When MeetStream can't attribute audio to a participant, `speaker_name` comes through as `"NoSpeaker"`. Filter or label these in your pipeline.

Full decoders for Python, Node.js, Go, and Java are in `references/code-patterns-python.md` and `references/code-patterns-node.md`.

### Pattern 8: Live Video Streaming (fMP4 over WebSocket)

Supported on **Google Meet and Microsoft Teams only — not Zoom**.

```json
{
  "video_required": true,
  "live_video_required": { "websocket_url": "wss://your-server.com/video" }
}
```

Protocol (all messages from MeetStream to you, except where noted):

| Message type | Direction | Description |
|---|---|---|
| `video_stream_start` (JSON text) | MS → you | Once on connect. Carries `codec`, `audio_codec`, `container: "fmp4"`, `width`, `height`, `framerate`, `audio_sample_rate`, `audio_bitrate`. |
| binary frames | MS → you | Raw fMP4 (fragmented MP4) bytes. **Append in order** to build the stream/file. |
| `video_latency_ping` (JSON text) | MS → you | Periodic. Carries `seq` and `sent_at_ms`. |
| `video_latency_pong` (JSON text) | **you → MS** | Echo `seq`, `sent_at_ms`, `bot_id`. Add `server_received_at_ms` (your wall-clock ms when you handled the ping). |
| `video_stream_end` (JSON text) | MS → you | Sent when stream stops. Carries `duration_seconds`. Connection closes after. |

Production tips: terminate TLS in front of your app (expose `wss://`), allow large WS frames, process writes sequentially per stream so chunk order is preserved.

### Pattern 9: MIA — AI Agent in a Meeting

MIA (MeetStream Infrastructure Agents) creates a server-configured AI agent that joins meetings via a hosted bridge. Two modes:

- **`pipeline`**: mix STT + LLM + TTS providers (configurable per layer)
- **`realtime`**: a single realtime model (OpenAI realtime, xAI, Google Gemini) — lower latency

**Create the agent config first:**
```
POST /api/v1/mia
{
  "agent_name": "Meeting Assistant",
  "mode": "pipeline",
  "model": { "provider": "openai", "model": "gpt-4.1", "system_prompt": "..." },
  "voice": { "provider": "openai", "voice_id": "nova" },
  "transcriber": { "provider": "deepgram", "model": "nova-3", "language": "en" },
  "agent": { "response_type": "voice", "first_message": "Hello!" }
}
```

Returns `{ message, agent_config_id, agent_config: {...} }`.

**Then attach to a bot using the hosted MeetStream bridge:**
```json
POST /bots/create_bot
{
  "meeting_link": "https://meet.google.com/...",
  "bot_name": "Assistant",
  "agent_config_id": "<from above>",
  "socket_connection_url":  { "websocket_url": "wss://agent-meetstream-prd-main.meetstream.ai/bridge" },
  "live_audio_required":   { "websocket_url": "wss://agent-meetstream-prd-main.meetstream.ai/bridge/audio" }
}
```

All three — `agent_config_id`, `socket_connection_url`, `live_audio_required` (pointing at the hosted bridge) — are required together for MIA.

**Other MIA operations:**
- `GET /api/v1/mia` — list all (no params) or fetch one (`?agent_config_id=...`)
- `PUT /api/v1/mia` — update; body requires `agent_config_id` + fields to change
- `DELETE /api/v1/mia?agent_config_id=...` — delete (query param, not path)

Supported providers: see `references/api-reference.md` MIA section.

---

## Bot Lifecycle — Live-Verified

Captured end-to-end from a real Google Meet bot run against `webhook.site`. The skill previously documented 7 events; **the live API actually emits 11+ events** in a richer sequence.

```
create_bot
  → bot.joining          (Joining, 200)
  → bot.inmeeting        (InMeeting, 200)
  → bot.recording        (Recording, 200)        ← skill missed this
  → participant_events.* (if realtime_endpoints configured; different payload shape)
  → bot.leaving          (Leaving, 200)          ← skill missed this
  → bot.stopped          (Stopped|NotAllowed|Denied|Error, 200)
  → manifest.completed   (200; manifest_status=Success)   ← skill missed this
  → audio.processed      (200; audio_status=Success)
  → transcription.processed  OR  transcription.failed  ← skill said *.failed didn't exist; it DOES
  → video.processed      OR  video.failed (presumed by symmetry)
  → bot.done             (Done, 200|500)        ← skill missed this — TRUE terminal event
  → data_deletion        (200) — only after DELETE /bots/{id}/delete or retention expiry
```

Notes:
- `bot.joining` may fire up to 3 times if server-side join retries kick in.
- `bot.inmeeting`, `bot.recording`, `bot.leaving`, `bot.stopped`, `bot.done` each fire at most once per bot.
- If the bot fails to join (NotAllowed / Denied), you may skip straight from `bot.joining` → `bot.stopped` with no `bot.inmeeting`, `bot.recording`, or `bot.leaving`.
- **`bot.done` is the TRUE terminal event**, fired after all post-call processing completes (or fails). Use this — not `bot.stopped` — to mark a session fully done.
- **Never fetch the transcript before `transcription.processed` fires.** Always set `callback_url`.

### Full event reference

| event | bot_status | status_code | When | Extra payload fields |
|---|---|---|---|---|
| `bot.joining` | `Joining` | 200 | Bot is connecting | — |
| `bot.inmeeting` | `InMeeting` | 200 | Bot joined the meeting | — |
| `bot.recording` | `Recording` | 200 | Recording started | — |
| `participant_events.join` / `.leave` | — | — | Participants join/leave (requires `recording_config.realtime_endpoints`) | Nested: `data.data.action`, `data.data.participant.{id,name,full_name,platform}`, `data.data.timestamp.{relative,absolute}`, `data.bot.{id,metadata}`. No top-level `bot_id` or `bot_status`. |
| `bot.leaving` | `Leaving` | 200 | Bot is leaving (e.g. removed by host, meeting ended) | — |
| `bot.stopped` | `Stopped` / `NotAllowed` / `Denied` / `Error` | 200 | Bot exited the meeting | — |
| `manifest.completed` | — | 200 | Platform manifest uploaded | `status: "success"`, `manifest_status: "Success"`, `timestamp` |
| `audio.processed` | — | 200 | Audio ready to fetch | `status: "success"`, `audio_status: "Success"`, `timestamp` |
| `transcription.processed` | — | 200 | Transcript ready (post-call providers) | `transcript_status: "Success"`, `timestamp` |
| `transcription.failed` | — | **500** | Transcript failed (e.g. provider auth error) | `status: "error"`, `transcript_status: "Failed"`, `message` (error detail), `timestamp` |
| `video.processed` | — | 200 | Video ready to fetch (`video_required: true`) | `video_status: "Success"`, `timestamp` |
| `bot.done` | `Done` | 200 (or 500 if processing failed) | All processing complete — **terminal event** | `timestamp`, `message` (error detail if status_code=500) |
| `data_deletion` | — | 200 | Data deleted (manual `/delete` or retention) | `status: "success"`, `deleted_objects: <int>`, `timestamp` |

### `status_code` is NOT always 200

Previous versions of this skill claimed `status_code` is always 200. **That is wrong.** Failure events (`transcription.failed`, `video.failed`, `bot.done` when processing errored) carry `status_code: 500`. Always branch on `event` first; use `status_code` only as a quick error indicator.

### Lifecycle internal states (visible via `bot_details.StatusTimeline`)

`StatusTimeline` on `/bots/{bot_id}/detail` shows every stage the bot passed through. Per live observation, the full set of stages is:

`Scheduled`, `Joining`, `WaitingRoom`, `InMeeting`, `Recording`, `Leaving`, `Stopped`, `BotNotAllowed`, `BotRejected`, `Error`, `AudioProcessing`, `VideoProcessing`, `TranscriptionReady`, `Done`, `MediaExpired`

Each entry is `{message, status, timestamp}`. `status: true` means that stage was reached; `false` means it wasn't (e.g. `BotRejected.status: false` if the bot wasn't rejected).

---

## `automatic_leave` Timeouts — Recommended Defaults

```json
{
  "automatic_leave": {
    "waiting_room_timeout": 600,
    "everyone_left_timeout": 600,
    "voice_inactivity_timeout": 600,
    "in_call_recording_timeout": 14400,
    "recording_permission_denied_timeout": 300
  }
}
```

All values in seconds. Use these defaults unless you have a specific reason to change them — they prevent the bot from dropping out of long real meetings.

- `waiting_room_timeout` — wait in waiting room before leaving — **600s (10 min)**
- `everyone_left_timeout` — stay after everyone else leaves — **600s (10 min)**
- `voice_inactivity_timeout` — wait if no audio detected (someone could be presenting silently) — **600s (10 min)**
- `in_call_recording_timeout` — max recording duration — **14400s (4 hours)**, the canonical default for full-length meetings
- `recording_permission_denied_timeout` — wait if recording permission denied (**Zoom-only**) — **300s (5 min)** — this is the max the API allows (range is 60–300)

> **Live-tested constraints (not in OpenAPI spec):**
> - `in_call_recording_timeout` minimum is **600 seconds** — the live API returns `HTTP 400: "in_call_recording_timeout must be at least 600 seconds"` below that.
> - `recording_permission_denied_timeout` accepted range is **60–300 seconds** (live-verified). Below 60 returns HTTP 400; above 300 returns `HTTP 400: "recording_permission_denied_timeout must not exceed 300 seconds"`. Use 300 (the max) for maximum patience.

**Why 14400 for `in_call_recording_timeout` specifically:** real meetings often run longer than 30 minutes. Defaulting to anything less risks the bot disconnecting while people are still talking. 4 hours is the canonical safe value for full-length sales / interview / workshop sessions.

Without these defaults, a stuck bot can sit in a meeting indefinitely.

---

## `bot_image_url`

Custom profile picture must be a **publicly accessible URL** — MeetStream fetches it externally. The OpenAPI schema describes it as a URL string. Base64 / data URIs are not supported by the docs guide; the image must be reachable without authentication.

```json
{ "bot_image_url": "https://your-server.com/avatar.png" }
```

---

## `custom_attributes`

The OpenAPI schema allows `additionalProperties: { description: Any type }`. Arbitrary key-value metadata; values are echoed back in webhook payloads.

> **Observed behavior:** in practice the server has been seen to reject non-string values. The OpenAPI doesn't enforce string-only, but stringifying values defensively is safer:
> ```json
> { "custom_attributes": { "deal_id": "12345", "active": "true", "score": "0.87" } }
> ```

---

## Platform Notes (per-feature, not just per-bot)

| Feature | Google Meet | Zoom | Microsoft Teams |
|---|---|---|---|
| Basic bot (`create_bot`) | ✓ | ✓ (setup required) | ✓ |
| Recording + post-call transcript | ✓ | ✓ | ✓ |
| Live transcription webhook | ✓ | ✓ | ✓ |
| Live audio (`live_audio_required`) | ✓ | ✓ | ✓ |
| **Live video (`live_video_required`)** | ✓ | **✗** | ✓ |
| **Per-participant audio streams** | ✓ | ✓ | **✗** |
| Per-participant video streams | ✓ | ✓ | ✓ |
| MIA agents | ✓ | ✓ | ✓ |
| `interrupt` WS command (clears audio queue) | ✓ | ✗ (accepted, no-op) | ✗ (accepted, no-op) |
| Native captions (`meeting_captions`) | ✓ | ✗ | ✓ |

### Zoom setup

Register a Zoom app + add credentials to MeetStream dashboard. Guide: https://docs.meetstream.ai/guides/zoom/zoom-marketplace-app-setup

**Zoom dev mode** restricts bots to meetings hosted by the app owner's account. For external meetings, follow the production submission guide: https://docs.meetstream.ai/guides/zoom/zoom-production-app-submission

For Zoom OBF (On-Behalf-Of), pass `"zoom": { "use_zoom_obf": true }` on `create_bot`.

The Zoom OAuth callback URL to register in your Zoom app is: `https://api.meetstream.ai/api/v1/admin/zoom/oauth/callback`

### Google Signed-In Bots

To have the bot join Google Meet using a Google identity (for paywalled / signed-in-only meetings), configure SSO in your Google Workspace admin and register domain/login certificates via:

- `POST /google-login-domains` — register a Google Workspace domain
- `GET /google-login-domains` — list domains
- `GET /google-login-domains/{domain}` — fetch one (path param is the workspace **domain string**)
- `PUT /google-login-domains/{domain}` / `DELETE /google-login-domains/{domain}` — update / delete
- `POST /google-logins` / `GET /google-logins` / `PUT/DELETE /google-logins/{id}` — manage logins

Then, on `create_bot`, pass the `google_meet` field (documented in the Google Signed-In Bots guide):
```json
{
  "google_meet": {
    "login_required": true,
    "google_login_domain": "your-domain.com"
  }
}
```

> **Note:** `google_meet` is documented in the prose guide but isn't in the OpenAPI `CreateBotRequest` schema. The Google Signed-In Bots guide is the canonical reference: https://docs.meetstream.ai/guides/google-signed-in-bots

---

## Transcription Providers

Specified under `recording_config.transcript.provider`. Use **exactly one** provider per bot.

| Provider key | Mode | Notes |
|---|---|---|
| `meetstream` | Post-call | MeetStream's in-house engine. OpenAPI marks `language` and `translate` as required. |
| `deepgram` | Post-call | `nova-3` is the only model enum. `language` defaults to `"en"` (free string per spec). |
| `assemblyai` | Post-call | Speaker diarization, redaction, chapters. 9 fields marked required per OpenAPI. |
| `sarvam` | Post-call | Indic languages, e.g. `model: "saaras:v3"`, `language_code: "en-IN"`. |
| `jigsawstack` | Post-call | Auto language detect, optional translation. |
| `meeting_captions` | Live, native | Free; uses Meet / Teams native captions. **No `transcript_id`** — fetch via `bot_details.caption_file` on `/detail`. |
| `deepgram_streaming` | Live | Real-time. All ~12 fields marked required per OpenAPI. |
| `assemblyai_streaming` | Live | Real-time English. All ~10 fields marked required per OpenAPI. |

> **Required-vs-default:** the OpenAPI marks many sub-fields as `required` even when they have natural defaults. Pass full provider configs when in doubt — see `references/api-reference.md` for the full schema of each provider.

---

## Webhook Handler Requirements

- Must use **HTTPS** (use ngrok or cloudflared for local dev — see https://docs.meetstream.ai/guides/webhooks/test-webhooks-locally)
- Must respond `2xx` quickly to acknowledge receipt
- **No automatic retries.** If your endpoint returns non-2xx, the webhook is **not** retried. Build your handler to never fail (catch errors, queue work, return 200).
- `bot.joining` may fire up to 3 times if join retries are configured. `bot.inmeeting`, `bot.stopped`, `audio.processed`, `transcription.processed`, `video.processed`, `data_deletion` are each sent **at most once**.
- Idempotency: dedupe by `{bot_id, event, timestamp}` per docs recommendation.

### Webhook payload shape

**Lifecycle events** (`bot.joining`/`bot.inmeeting`/`bot.recording`/`bot.leaving`/`bot.stopped`) — minimal envelope, **no `timestamp`**:
```json
{
  "event": "bot.joining",
  "bot_id": "dd451299-1471-49ae-b407-c91541242748",
  "bot_status": "Joining",
  "message": "Bot is joining the meeting",
  "status_code": 200,
  "custom_attributes": { "your_keys": "echoed back" }
}
```

**Post-call events** (`manifest.completed`, `audio.processed`, `transcription.processed`, `transcription.failed`, `video.processed`, `bot.done`, `data_deletion`) — include `timestamp` and may include `status: "success"|"error"`:
```json
{
  "event": "transcription.failed",
  "bot_id": "...",
  "status": "error",
  "transcript_status": "Failed",
  "message": "Transcript processing error: Deepgram API error: 401",
  "status_code": 500,
  "custom_attributes": {...},
  "timestamp": "2026-05-26T10:11:25.781273+00:00"
}
```

**Important — live-verified, contradicting earlier skill claims:**
- `timestamp` is NOT on every event. Only post-call events have it.
- `status_code` is NOT always 200. Failure events use 500.
- `participant_events.*` payload has a different structure — `bot_id` is nested under `data.bot.id`, no top-level `bot_status`.
- Branch on `event` first.

### Event types (see live-verified table in [Bot Lifecycle](#bot-lifecycle--live-verified))

12+ events: `bot.joining`, `bot.inmeeting`, **`bot.recording`**, `participant_events.*`, **`bot.leaving`**, `bot.stopped`, **`manifest.completed`**, `audio.processed`, `transcription.processed`, **`transcription.failed`**, `video.processed`, **`bot.done`**, `data_deletion`. Bold = added based on live testing.

### `bot_status` values

| bot_status | Event(s) | Meaning |
|---|---|---|
| `Joining` | `bot.joining` | Bot is connecting |
| `InMeeting` | `bot.inmeeting` | Bot is in the meeting |
| `Recording` | `bot.recording` | Recording active |
| `Leaving` | `bot.leaving` | Bot is leaving in progress |
| `Stopped` | `bot.stopped` | Normal exit (meeting ended, removed via API, voice timeout, host removed) |
| `NotAllowed` | `bot.stopped` | Could not join (waiting-room / lobby timeout) |
| `Denied` | `bot.stopped` | Host denied join or recording permission |
| `Error` | `bot.stopped` | Unexpected error during lifecycle |
| `Done` | `bot.done` | All processing complete — **terminal** |

### `*.failed` events DO exist (skill previously claimed they didn't)

Live-verified: `transcription.failed` is a real event with `status_code: 500`, `transcript_status: "Failed"`, and `message` carrying the upstream error (e.g. provider auth failure). Handle these in your router:

```python
elif event_type == "transcription.failed":
    log_error(f"Transcript failed for bot {bot_id}: {payload.get('message')}")
elif event_type == "bot.done" and payload.get("status_code") == 500:
    log_error(f"Bot finished with error: {payload.get('message')}")
```

Symmetric `audio.failed` and `video.failed` aren't yet observed but should be assumed to exist by the same pattern.

### Webhook signature verification (optional)

If a webhook secret is configured in the MeetStream dashboard, requests include:
- `X-MeetStream-Signature: sha256=<hex_digest>` — `HMAC-SHA256(secret, raw_body)`
- `X-MeetStream-Timestamp: <iso8601>`

Verify by computing `HMAC-SHA256(secret, raw_request_body)`, comparing against the signature (strip the `sha256=` prefix), and optionally checking the timestamp is within an acceptable replay window.

---

## Data Available After Meeting

After the relevant `*.processed` event fires:

| Data | Endpoint | Notes |
|---|---|---|
| Transcript (formatted) | `GET /transcript/{transcript_id}/get_transcript` | Response is a top-level array of segments |
| Raw transcript | `GET /transcript/{transcript_id}/get_transcript?raw=true` | Raw provider output |
| List transcripts for a bot | `GET /bots/{bot_id}/transcriptions` | Returns `{bot_id, transcriptions: [{transcript_id, provider, status, created_at, config, download_urls}]}` |
| Trigger a new transcription run | `POST /bots/{bot_id}/transcribe` | Body: `{provider: {<key>: {...}}, callback_url?}` |
| Speaker timeline | `GET /bots/{bot_id}/get_speaker_timeline` | Returns chunks with **byte offsets** into the audio file (not time) |
| In-meeting chat | `GET /bots/{bot_id}/get_chats` | |
| Audio file | `GET /bots/{bot_id}/get_audio` | Pre-signed S3 URL, **valid 1 hour** |
| Video file | `GET /bots/{bot_id}/get_video` | Pre-signed S3 URL, **valid 10 minutes** |
| Per-participant audio streams | `GET /bots/{bot_id}/get_audio_streams` | Per-segment URLs **valid 10 minutes**; returns 202 while bot is still in meeting |
| Per-participant recording streams | `GET /bots/{bot_id}/get_recording_streams` | Per-segment URLs **valid 10 minutes**; includes both `participants[]` and `screenshares[]` |
| Participant list | `GET /bots/{bot_id}/get_participants` | Returns a top-level array of `{deviceId, displayName, fullName, profilePicture, status, humanized_status, streamIds[], lastUpdated, parentDeviceId?}` |
| Session metadata | `GET /bots/{bot_id}/detail` | Returns `bot_details` with (live-verified): BotID, BotImageURL, BotMessage, BotProfile, BotUsername, CreatedAt, Duration, EndTime, LastUpdatedAt, ManifestStatus, MediaS3Bucket, MeetingLink, NativeSTT, OfferingType, Platform, PlatformCreatedAt, PlatformStatusCreatedAt, RequestPayload, StartTime, Status, StatusCreatedAt, **StatusTimeline** (per-stage `{message, status, timestamp}` map), AudioStatus, TranscriptStatus, UserID, caption_file (S3 link for native captions), participant_events, custom_attributes, **and `transcript_id`** (top-level — populated when a post-call provider is set, not enumerated in OpenAPI but returned live). |
| Screenshots | `GET /bots/{bot_id}/get_screenshots` | |
| Summary (if generated) | `GET /bots/{bot_id}/summary` | (Path is `/summary`, not `/get_summary`.) |

Bot management:
- Status: `GET /bots/{bot_id}/status`
- List bots: `GET /bots` — returns `{bots: [...], hasNextPage: bool, nextCursor: string|null}` (note camelCase pagination keys)
- Remove from active meeting: `GET /bots/{bot_id}/remove_bot` (it's GET in the OpenAPI; the Quickstart docs page shows `curl -X POST` but that contradicts the spec)
- Delete data: `DELETE /bots/{bot_id}/delete` → fires `data_deletion` webhook

### Per-participant audio/video — concurrency & platform limits

- **Per-participant audio** captures up to **16 concurrent speaker streams**. Supported on **Google Meet + Zoom only**, NOT Teams. Files: WebM container, Opus codec, 48 kbps, 48 kHz, mono.
- **Per-participant video** captures up to **6 concurrent webcam streams**. Supported on all 3 platforms. Files: WebM container, VP8 codec, 15 FPS, video-only (audio fetched separately).
- Both flags (`audio_separate_streams`, `video_separate_streams`) can be set at the top level of `create_bot` OR nested inside `recording_config`.

---

## Data Retention

Default retention is **24 hours**. Override on `create_bot`:

```json
{ "recording_config": { "retention": { "type": "timed", "hours": 168 } } }
```

Manually delete: `DELETE /bots/{bot_id}/delete` — fires the `data_deletion` callback when complete.

---

## Common Mistakes

1. **Looking for `transcript_id` in the webhook** — it's not there. The webhook only signals timing. Get the `transcript_id` from the `create_bot` response, `GET /bots/{bot_id}/detail` (`bot_details.transcript_id`), or `GET /bots/{bot_id}/transcriptions`.
2. **Iterating `transcript.transcript[]` with `seg.text`** — the response is a top-level array, and the per-segment text field is `transcript`, not `text`.
3. **`send_image` body using `image_url`** — the field is `img_url`.
4. **Fetching transcript before `transcription.processed`** — always wait for the webhook.
5. **HTTP callback URL** — must be HTTPS; use ngrok / cloudflared for local dev.
6. **Wrong calendar field names** — Calendar create requires `google_refresh_token` / `google_client_id` / `google_client_secret` (with the `google_` prefix).
7. **Using `audio_required` on `create_bot`** — not in the OpenAPI schema. Audio is captured by default. (It DOES exist for calendar-scheduled `bot_config`.)
8. **Skipping `bot_name`** — it's required, not optional.
9. **Assuming `video_required` defaults to false** — it defaults to `true`. Set it to `false` for transcript-only workflows or you'll burn storage.
10. **Assuming `status_code` is always 200** — it's 200 for success events, 500 for failure events (e.g. `transcription.failed`, `bot.done` when processing errored). Branch on `event` first.
11. **Expecting webhook retries** — there are none. Always return 2xx, queue work asynchronously, dedupe by `{bot_id, event, timestamp}`.
12. **Using `websocket_url` for live transcription** — `live_transcription_required` accepts only `webhook_url` (HTTPS POST). The `websocket_url` field is for `live_audio_required`, `live_video_required`, and `socket_connection_url`.
13. **Sending WAV blobs over `sendaudio`** — bot expects raw PCM16 LE @ 48000 Hz mono, base64-encoded. No WAV header. Resample if your source isn't 48 kHz.
14. **`/calendar/toggle-recurring/{event_id}` path** — actual path is `POST /calendar/toggle-recurrence` with body `{event_id, recurring_enabled}`. No path param.
15. **MIA endpoint paths** — they are `/api/v1/mia` (singular) for CRUD; DELETE uses `?agent_config_id=...` query param, not a path id.
16. **Live video on Zoom** — not supported. Google Meet and Teams only.
17. **`in_call_recording_timeout` under 600** — live API rejects with HTTP 400. Minimum 600 seconds.
18. **Expecting `create_bot` to return HTTP 200** — it returns **HTTP 201 Created** (live-verified). `status` field is typically `"Active"`.

---

## Code Reference Files

Read these when building:
- `references/code-patterns-node.md` — complete Node.js/TypeScript implementations
- `references/code-patterns-python.md` — complete Python implementations (including live audio decoder, MIA setup, fMP4 video receiver)
- `references/api-reference.md` — full endpoint map with params, request bodies, response shapes

---

## When to consult docs directly

For specific endpoint parameters, response schemas, or edge cases not covered here:
- MCP server: `https://docs.meetstream.ai/_mcp/server`
- OpenAPI: `https://docs.meetstream.ai/openapi.json`
- Any docs page as clean markdown: append `.md` to its URL, e.g. `https://docs.meetstream.ai/api-reference/api-endpoints/bot-endpoints/create-bot.md`
- Full single-file dump: `https://docs.meetstream.ai/llms-full.txt`

**Never invent endpoints or fields.** If the docs don't show it, don't put it in code.
