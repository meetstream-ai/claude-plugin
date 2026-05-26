# MeetStream API Reference

Base URL: `https://api.meetstream.ai/api/v1/`
Auth: `Authorization: Token YOUR_API_KEY`

OpenAPI spec: https://docs.meetstream.ai/openapi.json
Any docs page is available as clean markdown by appending `.md` to the URL.

---

## Bot Endpoints

### POST `/bots/create_bot`
Creates a bot and sends it to a meeting. Returns HTTP 201.

**Required:**
- `meeting_link` (string) — Zoom, Google Meet, or Teams meeting URL
- `bot_name` (string) — name shown in the meeting

**Optional:**
- `video_required` (bool, default `true`) — record video. Set `false` for transcript-only workflows.
- `zoom` (object) — Zoom-specific config: `{ "use_zoom_obf": true }` to enable OBF.
- `audio_separate_streams` (bool) — capture per-participant audio streams (Google Meet + Zoom).
- `video_separate_streams` (bool) — capture per-participant video streams (all 3 platforms).
- `bot_message` (string) — message posted in meeting chat on join.
- `bot_image_url` (string) — profile image URL (jpeg/png/gif). Must be a **publicly accessible URL** that MeetStream can fetch without auth. Base64 / data URIs are not accepted.
- `join_at` (string, ISO-8601) — schedule future join.
- `callback_url` (string) — HTTPS endpoint for lifecycle webhook events.
- `agent_config_id` (string) — MIA agent configuration ID.
- `custom_attributes` (object) — arbitrary key-value tags echoed in webhooks. **All values must be strings** — numbers, booleans, and nested objects will be rejected.
- `workflow_config_ids` (string[]) — post-meeting workflow IDs.
- `socket_connection_url` (object) — `{ "websocket_url": "wss://..." }` for two-way bot control.
- `live_audio_required` (object) — `{ "websocket_url": "wss://..." }` for live raw audio.
- `live_video_required` (object) — `{ "websocket_url": "wss://..." }` for live raw video.
- `live_transcription_required` (object) — `{ "webhook_url": "https://..." }` for live transcript chunks via HTTPS POST. **Not a WebSocket.**
- `recording_config` (object) — transcript provider, retention, realtime endpoints (see schema below).
- `automatic_leave` (object) — timeout rules in seconds (see schema below).

> There is **no `audio_required` field**. Audio is recorded by default. `audio_separate_streams` is a different feature (per-participant tracks).

**Response (201):**
```json
{
  "bot_id": "...",
  "transcript_id": "..." | null,
  "meeting_url": "...",
  "status": "..."
}
```

Docs: https://docs.meetstream.ai/api-reference/api-endpoints/bot-endpoints/create-bot

---

### GET `/bots/{bot_id}/status`
Current bot status. Returns `{ bot_id, status, custom_attributes }`. `status` values: `Joining`, `InMeeting`, `Stopped`, `NotAllowed`, `Denied`, `Error`.

---

### GET `/bots/{bot_id}/detail`
Full session metadata. Returns `{ bot_details: { BotID, BotImageURL, BotMessage, BotProfile, BotUsername, CreatedAt, Duration, EndTime, LastUpdatedAt, ManifestStatus, MeetingLink, NativeSTT, OfferingType, Platform, StartTime, Status, UserID, RequestPayload, StatusTimeline, custom_attributes, caption_file } }`.

---

### GET `/bots/{bot_id}/get_summary`
Returns the generated meeting summary, if a summary workflow was configured.

---

### GET `/bots/{bot_id}/get_audio`
Returns `{ "audio_url": "<pre-signed S3 URL valid 1 hr>" }`. Available after `audio.processed` webhook.

---

### GET `/bots/{bot_id}/get_video`
Returns `{ "video_url": "<pre-signed S3 URL valid 10 min>", "video_info": { duration, size_mb, resolution, fps, frames_processed, corrupted_frames } }`. Available after `video.processed` webhook.

---

### GET `/bots/{bot_id}/get_audio_streams`
Per-participant audio stream URLs (when `audio_separate_streams: true`).

---

### GET `/bots/{bot_id}/get_recording_streams`
Per-participant recording stream URLs (when `video_separate_streams: true`).

---

### GET `/bots/{bot_id}/get_speaker_timeline`
Timeline of who spoke and when.

---

### GET `/bots/{bot_id}/get_chats`
In-meeting chat messages captured by the bot.

---

### GET `/bots/{bot_id}/get_screenshots`
Screenshots captured during the meeting.

---

### GET `/bots/{bot_id}/get_participants`
List of participants detected in the meeting. Returns a direct JSON array (not an envelope) of participant objects, each with `fullName` and related fields.

---

### GET `/bots/{bot_id}/remove_bot`
Removes the bot from an active meeting. (Note: this is GET, not DELETE.)

---

### DELETE `/bots/{bot_id}/delete`
Permanently deletes audio, video, and transcript data for a bot. Triggers `data_deletion` webhook event. Returns `{ message, bot_id, deleted_objects }`.

---

### GET `/bots`
Lists all bots for the account. (Endpoint path is `/bots`, not `/bots/list_bots`.)

---

### POST `/bots/{bot_id}/send_message`
Send a chat message into the meeting as the bot.

**Body:**
```json
{
  "message": "Hello from the bot",
  "metadata": { "message_type": "text" }
}
```

---

### POST `/bots/{bot_id}/send_image`
Send an image (including animated GIF) into the meeting.

**Body:**
```json
{
  "image_url": "https://...",
  "metadata": { "message_type": "image" }
}
```

---

### PATCH `/calendar/scheduled_bots/{bot_id}`
Reschedule a future bot. Body: `{ "scheduled_join_time": "<ISO-8601>" }`.

---

### DELETE `/calendar/scheduled_bots/{bot_id}`
Delete a scheduled bot that hasn't joined yet.

---

## Transcription Endpoints

### GET `/transcript/{transcript_id}/get_transcript`
Returns the processed transcript by `transcript_id`. The `transcript_id` is in the `create_bot` response, also retrievable via `GET /bots/{bot_id}/transcriptions` or `bot_details.transcript_id` on `GET /bots/{bot_id}/detail`.

Query: `?raw=true` to retrieve the raw unformatted transcript from the provider.

**Alternate path:** `GET /bots/{bot_id}/get_bot_transcript/{transcript_id}` has been observed to return transcripts in production deployments. Use this as a fallback if the canonical path 404s.

---

### GET `/bots/{bot_id}/transcriptions`
Lists all transcription runs for a bot. Returns `{ transcriptions: [{ transcript_id, provider, status: "Success" | "Processing" | "Failed", created_at, config, download_urls: { raw_transcript, processed_transcript } }] }`. URLs are pre-signed S3, valid 1 hour.

---

### POST `/bots/{bot_id}/transcribe`
Trigger a new transcription run on the bot's audio (re-transcribe, or transcribe with a different provider). Body uses the same provider schema as `recording_config.transcript.provider`.

---

## Calendar Endpoints

### POST `/calendar/create_calendar`
Connects a Google Calendar via OAuth credentials. Bots auto-schedule for upcoming events on the linked calendar.

**Body (all required):**
```json
{
  "google_refresh_token": "...",
  "google_client_id": "...",
  "google_client_secret": "..."
}
```

> Field names use the `google_` prefix. Plain `refresh_token`, `client_id`, `client_secret` will be rejected.

**Response:** `{ calendar_id, platform, user_email, user_name, primary_calendar_id, message, calendars: [...], watch_setup: {...} }`.

---

### GET `/calendar`
List connected calendars. Returns `{ total, user_id, calendars: [...] }`.

---

### GET `/calendar/events`
List upcoming events from the connected calendar. Paginated: `{ next, previous, has_more, results: [{ id, start_time, end_time, calendar_id, platform, platform_id, ical_uid, meeting_platform, meeting_url, created_at, updated_at, is_deleted, raw, bots }] }`.

---

### POST `/calendar/schedule/{event_id}`
Manually schedule a bot for a specific calendar event. `event_id` is the event ID returned from `/calendar/events`.

**Response:** `{ scheduled, schedule_id, bot_id, schedule_group, event_id, scheduled_time, existing_schedules, occurrence_date, is_recurring_occurrence, bot_config: { ... } }`.

---

### DELETE `/calendar/schedule/{event_id}` (remove-schedule-event)
Cancel a scheduled bot for an event.

---

### POST `/calendar/toggle-recurring/{event_id}` (toggle-recurring-event)
Toggle whether a recurring event auto-schedules a bot.

---

### POST `/calendar/setup-cron`
Set up automatic event sync cron.

---

### POST `/calendar/disable-cron`
Disable the event sync cron.

---

### DELETE `/calendar/disconnect`
Disconnect the linked Google Calendar.

---

## Google Signed-In Bot Endpoints

For bots that need to authenticate to Google as a real user (for paywalled meetings, etc.).

| Endpoint | Purpose |
|---|---|
| `POST /google-domains` | Register a Google Workspace domain |
| `GET /google-domains` | List domains |
| `GET /google-domains/{id}` | Get a domain |
| `PUT /google-domains/{id}` | Update a domain |
| `DELETE /google-domains/{id}` | Delete a domain |
| `POST /google-logins` | Add a Google login under a domain |
| `GET /google-logins` | List Google logins |
| `PUT /google-logins/{id}` | Update a login |
| `DELETE /google-logins/{id}` | Delete a login |

See docs index for exact paths: https://docs.meetstream.ai/llms.txt

---

## MIA (MeetStream Infrastructure Agents) Endpoints

| Endpoint | Purpose |
|---|---|
| `POST /agent-configs` | Create an agent configuration |
| `GET /agent-configs` | List agent configurations |
| `PUT /agent-configs/{id}` | Update an agent configuration |
| `DELETE /agent-configs/{id}` | Delete an agent configuration |

Pass `agent_config_id` on `create_bot` to enable MIA on a session.

---

## Webhook Events (sent to `callback_url`)

All payloads are HTTP POST. Your endpoint MUST return 2xx — **webhooks are not retried** on non-2xx responses.

Every payload includes: `bot_id`, `event`, `message`, `status_code` (always `200`), `timestamp`, `custom_attributes`. Additional fields per event.

### Bot lifecycle events

| event | bot_status values | Notes |
|---|---|---|
| `bot.joining` | `Joining` | Fires at start. May repeat up to 3× if join retries are enabled. |
| `bot.inmeeting` | `InMeeting` | Fires when join succeeds. Sent at most once. |
| `bot.stopped` | `Stopped` / `NotAllowed` / `Denied` / `Error` | Terminal event. Sent exactly once. Failures are surfaced via `bot_status`. |

### Post-call processing events (asynchronous, after `bot.stopped`)

| event | Extra payload fields |
|---|---|
| `audio.processed` | `audio_status: "Success"` |
| `transcription.processed` | `transcript_status: "Success"` |
| `video.processed` | `video_status: "Success"` |
| `data_deletion` | `status: "success"`, `deleted_objects: <int>` |

Each post-call event is sent **at most once**. There are no separate `*.failed` events — failures show up in `bot_status` on `bot.stopped`.

### Sample payloads

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

```json
{
  "bot_id": "5b0ff6e7-3cea-4c9f-a6b4-851c5f11cf4f",
  "event": "transcription.processed",
  "transcript_status": "Success",
  "message": "Transcript processing completed successfully",
  "status_code": 200
}
```

### Webhook signature (optional)

If a webhook secret is configured, requests include:
- `X-MeetStream-Signature: sha256=<hex>` — `HMAC-SHA256(secret, raw_body)`
- `X-MeetStream-Timestamp: <iso8601>`

---

## `recording_config` Schema

```json
{
  "recording_config": {
    "transcript": {
      "provider": {
        "deepgram": { "model": "nova-3", "language": "en", "punctuate": true, "smart_format": true, "diarize": true }
      }
    },
    "retention": {
      "type": "timed",
      "hours": 24
    },
    "realtime_endpoints": [
      {
        "type": "webhook",
        "url": "https://your-server.com/events",
        "events": ["participant_events.join", "participant_events.leave"]
      }
    ]
  }
}
```

Default retention: `{ "type": "timed", "hours": 24 }`.

### Supported transcription providers (use exactly one under `transcript.provider`)

| Provider | Mode | Example config |
|---|---|---|
| `meetstream` | Post-call | `{ "language": "auto", "translate": false }` |
| `deepgram` | Post-call | `{ "model": "nova-3", "language": "en", "punctuate": true, "smart_format": true, "diarize": true, "paragraphs": true, "numerals": true, "filler_words": false, "keywords": [], "utterances": true, "search": [], "tag": [] }` — **`nova-3` requires `language: "en"`** |
| `assemblyai` | Post-call | `{ "speech_models": ["universal-2"], "language_code": "en_us", "speaker_labels": true, "punctuate": true, "format_text": true, "filter_profanity": false, "redact_pii": false, "keyterms_prompt": [], "auto_chapters": false, "entity_detection": false }` |
| `sarvam` | Post-call | `{ "model": "saaras:v3", "language_code": "en-IN", "mode": "transcribe", "with_diarization": true }` |
| `jigsawstack` | Post-call | `{ "language": "auto", "translate": false, "by_speaker": true }` |
| `meeting_captions` | Live (native) | `{}` (Google Meet / Teams native captions) |
| `deepgram_streaming` | Live | `{ "transcription_mode": "sentence", "model": "nova-2", "language": "en", "punctuate": true, "smart_format": true, "endpointing": 300, "vad_events": true, "utterance_end_ms": 1000, "encoding": "linear16", "channels": 1 }` |
| `assemblyai_streaming` | Live | `{ "transcription_mode": "raw", "sample_rate": 48000, "speech_model": "universal-streaming-english", "format_turns": false, "encoding": "pcm_s16le", "vad_threshold": "0.4", "end_of_turn_confidence_threshold": "0.4", "inactivity_timeout": 300, "min_end_of_turn_silence_when_confident": "400", "max_turn_silence": "1280" }` |

---

## `automatic_leave` Schema

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

All values in seconds. Defaults shown above. `recording_permission_denied_timeout` is Zoom-only and has been observed to reject values below 60 with HTTP 400 in production — stick with 60+.

---

## Live Transcription Webhook Payload

POST'd to `live_transcription_required.webhook_url`:

```json
{
  "bot_id": "8ceabf49-d392-4c04-8e91-bd9601a0df6e",
  "speakerName": "Alice",
  "timestamp": "2026-01-24T17:00:30.354452",
  "new_text": "hear",
  "transcript": "hear",
  "utterance": "",
  "words": [
    {
      "word": "hear",
      "start": 2,
      "end": 2.08,
      "confidence": 0.999955,
      "speaker": "Alice",
      "punctuated_word": "hear",
      "speech_confidence": 0.999955,
      "word_is_final": false
    }
  ],
  "end_of_turn": false,
  "turn_is_formatted": false,
  "transcription_mode": "word_level",
  "custom_attributes": {}
}
```

- `new_text` — incremental delta (useful for streaming UI)
- `transcript` — current buffer (may be partial)
- `word_is_final` — `false` means interim, may change
- `end_of_turn` — useful for committing phrases

---

## WebSocket Control Commands

Provided via `socket_connection_url: { "websocket_url": "wss://..." }` on `create_bot`. The bot **connects to your server as a client** when it joins the meeting.

### Handshake

Bot sends:
```json
{ "type": "ready", "bot_id": "bot_abc123", "message": "Ready to receive messages" }
```

### `sendaudio` — play audio through the bot's mic

Audio must be **raw PCM16 signed little-endian** at 48000 Hz mono, base64-encoded. No WAV header, no MP3.

```json
{
  "command": "sendaudio",
  "bot_id": "bot_abc123",
  "audiochunk": "<base64-encoded raw PCM16 LE bytes>",
  "sample_rate": 48000,
  "encoding": "pcm16",
  "channels": 1,
  "endianness": "little"
}
```

For chat messages and images, prefer the REST endpoints (`/send_message`, `/send_image`) instead of WebSocket commands.

Connection closes with normal code `1000` when the bot leaves.

Docs: https://docs.meetstream.ai/guides/web-sockets/meeting-control-and-command-patterns
