# MeetStream API Reference

Base URL: `https://api.meetstream.ai/api/v1`
Auth: `Authorization: Token YOUR_API_KEY`

OpenAPI spec: https://docs.meetstream.ai/openapi.json
Any docs page is available as clean markdown by appending `.md` to its URL.
Full docs dump: https://docs.meetstream.ai/llms-full.txt

> **Source of truth:** every endpoint, field, and constraint below is from the live OpenAPI spec or the prose guides at docs.meetstream.ai. Items marked "observed behavior" are runtime gotchas not codified in the OpenAPI. Nothing in this file is invented.

---

## Bot Endpoints

### POST `/bots/create_bot`
Creates a bot and sends it to a meeting.

**Required (per OpenAPI `CreateBotRequest`):**
- `meeting_link` (string) — Zoom, Google Meet, or Teams meeting URL
- `bot_name` (string) — name shown in the meeting

**Optional fields in the schema:**
- `video_required` (bool, **default `true`**) — record video. Set `false` for transcript-only.
- `zoom` (object) — Zoom-specific config, e.g. `{ "use_zoom_obf": true }`.
- `audio_separate_streams` (bool) — per-participant audio tracks (Google Meet + Zoom only). Can also be set under `recording_config`.
- `video_separate_streams` (bool) — per-participant video tracks (all 3 platforms). Can also be set under `recording_config`.
- `bot_message` (string) — initial chat message posted on join.
- `bot_image_url` (string) — bot avatar URL. **Must be publicly accessible per the prose docs.**
- `callback_url` (string) — HTTPS endpoint for lifecycle webhook events.
- `join_at` (string, ISO-8601) — schedule future join.
- `agent_config_id` (string) — MIA agent configuration ID (see MIA section).
- `custom_attributes` (object) — `additionalProperties: { description: Any type }` in the schema. **Observed behavior:** server may reject non-string values; stringify defensively.
- `socket_connection_url` (object) — `{ "websocket_url": "wss://..." }` for two-way bot control (Pattern 3).
- `live_audio_required` (object) — `{ "websocket_url": "wss://..." }` for live raw audio frames (Pattern 7).
- `live_video_required` (object) — `{ "websocket_url": "wss://..." }` for live fMP4 video (Pattern 8). Google Meet + Teams only.
- `live_transcription_required` (object) — `{ "webhook_url": "https://..." }` for live transcript chunks via HTTPS POST. **Not a WebSocket.**
- `workflow_config_ids` (string[]) — post-meeting workflow IDs.
- `recording_config` (object) — transcript provider, retention, realtime endpoints (see schema below).
- `automatic_leave` (object) — timeout rules in seconds (see schema below).

**Not in OpenAPI but documented in prose guides (also accepted):**
- `google_meet` (object) — for Google Signed-In Bots: `{ "login_required": true, "google_login_domain": "your-domain.com" }`.

> **Important:** `audio_required` is **not** in the `CreateBotRequest` schema. Audio is captured by default. The field DOES exist in calendar-scheduled `bot_config` (different schema).

**Response — live-verified HTTP 201 Created** (OpenAPI documents 200 but live returns 201) — `BotResponse`:
```json
{
  "bot_id": "string",
  "transcript_id": "string | null",
  "meeting_url": "string",
  "status": "Active"
}
```

`transcript_id` is **null** when provider is `meeting_captions` or no provider is configured. Otherwise populated.

Docs: https://docs.meetstream.ai/api-reference/api-endpoints/bot-endpoints/create-bot

---

### GET `/bots/{bot_id}/status`
Current bot status. Returns `{ bot_id, status, custom_attributes }`. Status values match webhook `bot_status`: `Joining`, `InMeeting`, `Stopped`, `NotAllowed`, `Denied`, `Error`.

---

### GET `/bots/{bot_id}/detail`
Full session metadata. Returns `{ bot_details: { ... } }`. The live API returns the following fields (verified by direct API test — the OpenAPI `BotDetailsResponseBotDetails` schema is incomplete):

```
BotID, BotImageURL, BotMessage, BotProfile, BotUsername,
CreatedAt, Duration, EndTime, LastUpdatedAt, ManifestStatus,
MediaS3Bucket, MeetingLink, NativeSTT, OfferingType, Platform,
PlatformCreatedAt, PlatformStatusCreatedAt, RequestPayload,
StartTime, Status, StatusCreatedAt, StatusTimeline, UserID,
AudioStatus, caption_file, participant_events, custom_attributes,
transcript_id
```

> **`transcript_id` IS at the top level of `bot_details` (live-verified).** Populated when a post-call provider (assemblyai / deepgram / jigsawstack / sarvam / meetstream) is configured; `null` for `meeting_captions` or no provider. This field is **not** listed in the OpenAPI schema but is returned by the live API. Use this as one of three ways to retrieve `transcript_id`:
> 1. The `create_bot` response (`BotResponse.transcript_id`)
> 2. `bot_details.transcript_id` on this endpoint
> 3. `GET /bots/{bot_id}/transcriptions`

`caption_file` is an S3 link to native captions when provider is `meeting_captions`. `RequestPayload` echoes the exact create_bot body. `StatusTimeline` is a map of lifecycle stages each with `{message, status, timestamp}`. `AudioStatus` mirrors the `audio.processed` event.

---

### GET `/bots/{bot_id}/summary`
Returns the generated meeting summary if a summary workflow was configured. Response shape is `BotDetailsResponse` (same as `/detail`). **Path is `/summary`, not `/get_summary`.**

---

### GET `/bots/{bot_id}/get_audio`
Returns `{ "audio_url": "<pre-signed S3 URL valid 1 hour>" }`. Available after `audio.processed` webhook.

---

### GET `/bots/{bot_id}/get_video`
Returns `{ "video_url": "<pre-signed S3 URL valid 10 minutes>", "video_info": { duration, size_mb, resolution, fps, frames_processed, corrupted_frames } }`. Available after `video.processed` webhook.

---

### GET `/bots/{bot_id}/get_audio_streams`
Per-participant audio streams (when `audio_separate_streams: true`). Returns HTTP **202** with `{audio_status: "in_progress", message}` while bot is still in meeting.

Completed response:
```json
{
  "bot_id": "...",
  "audio_status": "Success",
  "audio_streams_available": true,
  "participants": [
    {
      "participant_name": "John Doe",
      "streams": [{
        "stream_id": "JohnDoe_abc123",
        "segments": [{
          "segment_index": 0,
          "url": "https://s3.amazonaws.com/...",
          "filename": "John_Doe_abc123_0.webm",
          "duration_seconds": 125.5,
          "sample_rate": 48000,
          "channels": 1,
          "codec": "opus"
        }]
      }]
    }
  ],
  "summary": { "total_participants": 2, "total_segments": 2 }
}
```

URLs in `segments[].url` are pre-signed S3, **valid 10 minutes**. File format: WebM container, Opus codec, 48 kbps, 48 kHz, mono. Up to 16 concurrent speakers. **Not supported on Microsoft Teams.**

---

### GET `/bots/{bot_id}/get_recording_streams`
Per-participant video streams (when `video_separate_streams: true`). Same 202-while-processing pattern. Returns both `participants[]` and `screenshares[]` (each with the same `streams[].segments[]` shape):

```json
{
  "bot_id": "...",
  "video_status": "Success",
  "recording_streams_available": true,
  "participants": [{
    "participant_name": "Jane",
    "streams": [{
      "stream_id": "user_456",
      "segments": [{
        "segment_index": 0,
        "url": "https://s3.amazonaws.com/...",
        "filename": "Jane_456_0.webm",
        "duration_seconds": 125.5,
        "width": 640, "height": 360,
        "codec": "vp8"
      }]
    }]
  }],
  "screenshares": [ /* same shape as participants[] */ ],
  "summary": { "total_participants": 2, "total_screenshares": 1, "total_segments": 3 }
}
```

URLs **valid 10 minutes**. File format: WebM container, VP8 codec, 15 FPS, video-only. Up to 6 concurrent webcams. Supported on all 3 platforms.

---

### GET `/bots/{bot_id}/get_speaker_timeline`
Returns `{chunks: [{chunkIndex, timestamp, sampleRate, speakerId, speakerName, startByte, endByte}], lastUpdated, audioFilePath, totalFileSize}`. The `startByte`/`endByte` are **byte offsets into the audio file**, not time offsets.

---

### GET `/bots/{bot_id}/get_chats`
In-meeting chat messages captured by the bot.

---

### GET `/bots/{bot_id}/get_screenshots`
Screenshots captured during the meeting.

---

### GET `/bots/{bot_id}/get_participants`
Returns a **top-level JSON array** (not an envelope) of participant objects:
```json
[
  {
    "deviceId": "...",
    "displayName": "...",
    "fullName": "...",
    "profilePicture": "...",
    "status": 1,
    "humanized_status": "...",
    "streamIds": ["..."],
    "lastUpdated": "...",
    "parentDeviceId": "..."
  }
]
```

---

### GET `/bots/{bot_id}/remove_bot`
Removes the bot from an active meeting. **GET per the OpenAPI spec.** (The Quickstart docs page shows `curl -X POST` which contradicts the spec; trust the OpenAPI.)

---

### DELETE `/bots/{bot_id}/delete`
Permanently deletes audio, video, and transcript data. Triggers `data_deletion` webhook event. Returns `{ message, bot_id, deleted_objects }`.

---

### GET `/bots`
Lists all bots for the account. Returns `{bots: [...], hasNextPage: bool, nextCursor: string|null}` — note camelCase pagination keys.

---

### POST `/bots/{bot_id}/send_message`
Send a chat message into the meeting as the bot (REST equivalent of the `sendmsg` WebSocket command).

```json
{
  "message": "Hello from the bot",
  "metadata": { "message_type": "text" }
}
```

---

### POST `/bots/{bot_id}/send_image`
Send an image (including animated GIF) into the meeting chat. Body schema (`SendImageRequest`):

```json
{
  "img_url": "https://...",
  "display_duration": 5,
  "metadata": { "message_type": "image" }
}
```

- **`img_url`** (string, **required**) — NOT `image_url`.
- `display_duration` (integer, optional) — how long to display.
- `metadata` (object, optional) — `{message_type: string}`.

Response: `{status, bot_id, command}`.

---

### POST `/bots/{bot_id}/transcribe`
Trigger a new transcription run on the bot's audio. Body (`TranscribeRequest`):

```json
{
  "provider": {
    "deepgram": { "model": "nova-3", "language": "en" }
  },
  "callback_url": "https://your-server.com/webhook"
}
```

- `provider` (object, **required**) — top-level. Pick exactly one sub-key: `deepgram`, `meetstream`, `jigsawstack`, `sarvam`, or `assemblyai`. (Same shape as in `recording_config.transcript.provider` but here `provider` is the top-level key.)
- `callback_url` (string, optional).

Response (`TranscribeResponse`): `{ bot_id, transcript_id, provider, message }`.

---

## Transcription Endpoints

### GET `/transcript/{transcript_id}/get_transcript`
Returns the processed transcript by `transcript_id`. The `transcript_id` comes from any of four places:
1. The `create_bot` response (for assemblyai/deepgram/jigsawstack/sarvam/meetstream providers — null for `meeting_captions`)
2. **`GET /bots/{bot_id}/detail` → `bot_details.transcript_id`** (live-verified, not in OpenAPI schema)
3. `GET /bots/{bot_id}/transcriptions` (lists every run)
4. The `POST /bots/{bot_id}/transcribe` response

Query: `?raw=true` to retrieve raw unformatted provider output.

**Response is a top-level JSON array** (`GetTranscriptionSchema`) of segments:
```json
[
  {
    "speaker": "Alice",
    "transcript": "the text of this segment",
    "start_time": 0.5,
    "end_time": 3.2,
    "absolute_start_time": "2026-04-22T10:00:00.500Z",
    "absolute_end_time": "2026-04-22T10:00:03.200Z",
    "words": [
      {
        "word": "Hello",
        "punctuated_word": "Hello,",
        "start": 0.5,
        "end": 0.8,
        "confidence": 0.99,
        "speaker": 0,
        "speaker_confidence": 0.95
      }
    ]
  }
]
```

- Per-segment text field is **`transcript`**, not `text`.
- Response is the array itself, not `{transcript: [...]}`.

`?raw=true` returns a different shape (`GetRawTranscriptionSchema`) with `id` and provider-specific structure.

---

### GET `/bots/{bot_id}/transcriptions`
Lists every transcription run for a bot. Returns:

```json
{
  "bot_id": "...",
  "transcriptions": [
    {
      "transcript_id": "...",
      "provider": "deepgram",
      "status": "Success" | "Processing" | "Failed",
      "created_at": "2026-...",
      "config": { /* the provider config used */ },
      "download_urls": {
        "raw_transcript": "https://s3...",
        "processed_transcript": "https://s3..."
      }
    }
  ]
}
```

`download_urls` pre-signed S3 URLs are valid for 1 hour. `download_urls` can also be `null`.

---

## Calendar Endpoints

### POST `/calendar/create_calendar`
Connect a Google Calendar via OAuth credentials.

**Body (all three required per `CalendarCreateRequest`):**
```json
{
  "google_refresh_token": "...",
  "google_client_id": "...",
  "google_client_secret": "..."
}
```

Field names use the `google_` prefix. Plain `refresh_token` / `client_id` / `client_secret` are rejected.

**Response:** `{ calendar_id, platform, user_email, user_name, primary_calendar_id, message, calendars: [{id, summary, description, isPrimary, accessRole, timeZone, backgroundColor, foregroundColor, selected}], watch_setup: {...} }`.

---

### GET `/calendar/calendars`
List connected calendars (live from Google API). Returns `{ total, user_id, calendars: [...] }`.

---

### GET `/calendar`
List connected calendars (alternate path from older docs). Same shape as above.

---

### GET `/calendar/events`
Sync + list upcoming events. Paginated:
```json
{
  "next": "...",
  "previous": "...",
  "has_more": true,
  "results": [
    {
      "id": "evt_...",
      "start_time": "2026-...",
      "end_time": "2026-...",
      "calendar_id": "...",
      "platform": "google_calendar",
      "platform_id": "...",
      "ical_uid": "...",
      "meeting_platform": "google_meet|zoom|teams|...",
      "meeting_url": "...",
      "created_at": "...",
      "updated_at": "...",
      "is_deleted": false,
      "raw": { /* raw Google event */ },
      "bots": [ /* scheduled bots for this event */ ]
    }
  ]
}
```

---

### GET `/calendar/get_events`
Same as `/calendar/events` but reads from MeetStream's local DB only (no Google API call — faster).

---

### POST `/calendar/schedule/{event_id}`
Manually schedule a bot for a specific event. `event_id` is the `id` from `/calendar/events`.

**Body:**
```json
{
  "bot_config": {
    "bot_name": "My Meeting Bot",
    "audio_required": true,
    "video_required": false,
    "bot_message": "Joining to record",
    "callback_url": "https://...",
    "transcription": { "deepgram": { "model": "nova-3", "language": "en" } },
    "automatic_leave": { "no_one_joined_timeout": 300, "everyone_left_timeout": 60 },
    "recording_config": { "video_recording": false }
  },
  "occurrence_date": "2026-04-14T10:00:00Z",
  "schedule_all_occurrences": false,
  "occurrence_limit": 52,
  "recurring_event": false
}
```

| Field | Type | Default | Description |
|---|---|---|---|
| `bot_config` | object | — | Same shape as `create_bot` body (`audio_required` IS valid here) |
| `occurrence_date` | ISO-8601 | — | Specific recurring occurrence to schedule |
| `schedule_all_occurrences` | bool | `false` | Batch-schedule all future occurrences |
| `occurrence_limit` | int | `52` | Max occurrences when batch-scheduling |
| `recurring_event` | bool | `false` | After this occurrence, auto-schedule the next one |

**Response:** `{ scheduled, schedule_id, bot_id, schedule_group, event_id, scheduled_time, bot_config: {...}, is_recurring_occurrence }`.

**Deduplication:** scheduling the same event twice returns **HTTP 409** with the existing bot's ID. To update, use `PATCH /calendar/scheduled_bots/{bot_id}`.

---

### DELETE `/calendar/schedule/{event_id}`
Unschedule the bot for an event.

**Body (optional):**
```json
{
  "cancel_all_occurrences": false,
  "from_date": "2026-05-01T00:00:00Z"
}
```

**Response:** `{ unscheduled, event_id, cancelled_schedules, schedules_cancelled, bots_deleted, cancel_all_occurrences, is_recurring_series }`.

---

### GET `/calendar/scheduled_bots`
List all upcoming scheduled bots.

---

### PATCH `/calendar/scheduled_bots/{bot_id}`
Reschedule / update a future bot.

**Body:**
```json
{
  "scheduled_join_time": "2026-04-22T15:00:00Z",
  "bot_username": "Updated Name",
  "custom_attributes": { "deal_id": "12345" }
}
```

**Response:** `{ message, bot_id, updated_fields: [...], schedule_updated: bool }`.

---

### DELETE `/calendar/scheduled_bots/{bot_id}`
Delete a single scheduled bot that hasn't joined yet.

---

### POST `/calendar/auto-schedule/enable`
Enable hands-free auto-scheduling.

**Body:**
```json
{
  "default_bot_config": {
    "bot_name": "MeetStream Auto Bot",
    "audio_required": true,
    "video_required": false,
    "callback_url": "https://...",
    "transcription": { "deepgram": { "model": "nova-3", "language": "en" } },
    "automatic_leave": { "no_one_joined_timeout": 300, "everyone_left_timeout": 60 }
  }
}
```

How it works: background job every 24h at midnight UTC scans next 24h, schedules bots 1 min before each meeting, skips events with existing bots (dedup).

**Response:** `{ message, auto_schedule_enabled: true, default_bot_config: {...} }`.

---

### POST `/calendar/auto-schedule/disable`
Disable auto-scheduling. No body required.

---

### GET `/calendar/auto-schedule/settings`
Returns `{ auto_schedule_enabled, default_bot_config }`.

---

### POST `/calendar/auto-reschedule`
Trigger reschedule of the next occurrence of a recurring event.

---

### POST `/calendar/toggle-recurrence`
Enable/disable auto-rescheduling per event.

**Body:**
```json
{ "event_id": "evt_...", "recurring_enabled": true }
```

> No path param. The earlier docs referenced `/calendar/toggle-recurring/{event_id}` is wrong.

---

### `/calendar/disconnect`
> **Method inconsistency in docs:** the OpenAPI spec says **`POST /calendar/disconnect`** with `CalendarCreateRequest` body. The prose docs (FAQ + API quick reference) say **`DELETE /calendar/disconnect`**. Try POST first; if 405, fall back to DELETE.

Disconnects the calendar. Per the prose docs, this stops watch channels, cancels pending bot schedules, deletes synced event data, and removes Google OAuth credentials (irreversible).

---

## Google Signed-In Bot Endpoints

For bots that authenticate to Google Meet as a real user (paywalled / signed-in-only meetings). Setup involves Google Workspace SSO + certificate registration; see https://docs.meetstream.ai/guides/google-signed-in-bots

### POST `/google-login-domains`
Register a Google Workspace domain. Body: `LoginGroupRequest` (see OpenAPI for full shape).

### GET `/google-login-domains`
List registered domains.

### GET `/google-login-domains/{domain}`
Fetch one domain. **`{domain}` is the workspace domain string** (e.g. `your-company.com`), not an opaque id.

### PUT `/google-login-domains/{domain}`
Update a domain.

### DELETE `/google-login-domains/{domain}`
Delete a domain.

### POST `/google-logins`
Add a Google login under a domain.

### GET `/google-logins`
List Google logins.

### PUT `/google-logins/{id}`
Update a login.

### DELETE `/google-logins/{id}`
Delete a login.

### Then on `create_bot`, attach via:
```json
{
  "google_meet": {
    "login_required": true,
    "google_login_domain": "your-domain.com"
  }
}
```

(`google_meet` is documented in the Google Signed-In Bots guide; it isn't in the OpenAPI `CreateBotRequest` schema but is the canonical activation payload.)

---

## MIA (MeetStream Infrastructure Agents) Endpoints

All MIA operations use the same path `/api/v1/mia` (singular). The HTTP method distinguishes the operation.

### POST `/api/v1/mia` — Create

**Required:**
- `agent_name` (string)
- `mode` (string) — `"pipeline"` or `"realtime"`
- `model` (object) — see below

**Optional:**
- `voice` (object, **pipeline only**)
- `transcriber` (object, **pipeline only**)
- `agent` (object) — `response_type` (`"voice"` / `"chat"` / `"action"`, default `"voice"`), `first_message` (string), `mcp_servers` (array)
- `audio` (object) — `sample_rate`, `num_channels`
- `wake_word` (object, **pipeline only**) — `enabled` (bool), `words` (array or comma-separated string), `timeout` (seconds, default 30)
- `avatar` (object) — `enabled` (bool), `provider` (`"anam"`), `avatar_id` (required when provider is anam)

**`model` schema (pipeline):**
- `provider` — `"openai"` or `"anthropic"`
- `model` — e.g. `"gpt-4.1"`, `"gpt-4.1-mini"`
- `system_prompt` — defines personality
- `temperature` (optional, 0–2)
- `max_tokens` (optional)

**`model` schema (realtime):**
- `provider` — `"openai"`, `"xai"`, or `"google"`
- `model` — required for OpenAI only
- `system_prompt`
- `voice` — required; valid values:
  - OpenAI: `alloy, ash, ballad, coral, echo, fable, nova, onyx, sage, shimmer, verse`
  - xAI: `Ara, Eve, Leo, Rex, Sal`
  - Google: `Puck, Charon, Kore, Fenrir, Aoede, Leda, Orus, Zephyr`
- `temperature` (optional)
- `max_response_output_tokens` (optional, OpenAI only)
- `thinking_config` (Google Gemini, optional) — `{include_thoughts: bool, thinking_budget: int}`

**`voice` schema (pipeline TTS):**
- `provider` — `"openai"` or `"elevenlabs"`
- `voice_id` — required
- `model` — e.g. `"tts-1"`, `"eleven_turbo_v2_5"`

**`transcriber` schema (pipeline STT):**
- `provider` — `"openai"`, `"deepgram"`, or `"assemblyai"`
- `model` — e.g. `"nova-3"`, `"whisper-1"`
- `language` — e.g. `"en"`, `"es"`
- `boostwords` — array of strings

**`agent.mcp_servers[]`:**
- `url` (HTTPS, required)
- `headers` (object, e.g. `{Authorization: "Bearer ..."}`)
- `allowed_tools` (array, whitelist)
- `timeout` (seconds, default 10)

**Response (200):** `{ message, agent_config_id, agent_config: {...} }`

### GET `/api/v1/mia`
Lists all or returns one (`?agent_config_id=...` query param).

Returns `{ agent_configs: [...], count }` or `{ agent_config: {...} }`.

### PUT `/api/v1/mia` — Update
Body requires `agent_config_id` plus any subset of: `agent_name`, `mode`, `model`, `voice`, `transcriber`, `agent`, `wake_word`, `audio`, `avatar`. Only included fields are updated.

> Changing `mode` triggers full re-validation. Updating individual sections (model/voice/transcriber) only validates required API keys exist.

### DELETE `/api/v1/mia?agent_config_id=...`
**Query param**, not path id. Returns `{ message }`.

### Error codes
- `400` — missing required field, invalid value, unsupported provider, provider API key not configured
- `403` — not the owner
- `404` — not found
- `405` — method not allowed
- `500` — server error

### Using a MIA agent on a bot

```json
POST /bots/create_bot
{
  "meeting_link": "...",
  "agent_config_id": "<id>",
  "socket_connection_url": { "websocket_url": "wss://agent-meetstream-prd-main.meetstream.ai/bridge" },
  "live_audio_required": { "websocket_url": "wss://agent-meetstream-prd-main.meetstream.ai/bridge/audio" }
}
```

All three fields are required together to enable MIA.

---

## Webhook Events (sent to `callback_url`)

HTTP POST. Your endpoint MUST return 2xx — **webhooks are not retried on non-2xx**.

Every payload includes: `bot_id`, `event`, `message`, `status_code` (always `200`), `timestamp`, `custom_attributes`. Additional per-event fields below.

### Bot lifecycle events

| event | bot_status | Notes |
|---|---|---|
| `bot.joining` | `Joining` | Fires at start. Up to 3× if MeetStream's server-side join retries kick in. |
| `bot.inmeeting` | `InMeeting` | Fires when join succeeds. **At most once.** |
| `bot.stopped` | `Stopped` / `NotAllowed` / `Denied` / `Error` | Terminal event. **Exactly once.** Failures surfaced via `bot_status`. |

### Post-call processing events (after `bot.stopped`)

| event | Extra payload fields |
|---|---|
| `audio.processed` | `audio_status: "Success"` |
| `transcription.processed` | `transcript_status: "Success"` |
| `video.processed` | `video_status: "Success"` |
| `data_deletion` | `status: "success"`, `deleted_objects: <int>`, `timestamp` |

Each post-call event sent **at most once**. No separate `*.failed` events — failures show up in `bot_status` on `bot.stopped`.

### `transcript_id` is NOT in the webhook payload

`transcription.processed` only signals timing. Fetch `transcript_id` from one of: the `create_bot` response, `bot_details.transcript_id` on `GET /bots/{bot_id}/detail`, or `GET /bots/{bot_id}/transcriptions`.

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

```json
{
  "bot_id": "5b0ff6e7-3cea-4c9f-a6b4-851c5f11cf4f",
  "event": "data_deletion",
  "status": "success",
  "message": "Bot data deleted successfully",
  "deleted_objects": 5,
  "timestamp": "2024-01-15T14:30:00Z",
  "status_code": 200
}
```

### Webhook signature (optional)

If a webhook secret is configured in the MeetStream dashboard, requests include:
- `X-MeetStream-Signature: sha256=<hex>` — `HMAC-SHA256(secret, raw_body)`
- `X-MeetStream-Timestamp: <iso8601>`

### Idempotency

Dedupe by `{bot_id, event, timestamp}`.

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
    "retention": { "type": "timed", "hours": 24 },
    "realtime_endpoints": [
      {
        "type": "webhook",
        "url": "https://your-server.com/events",
        "events": ["participant_events.join", "participant_events.leave"]
      }
    ],
    "audio_separate_streams": true,
    "video_separate_streams": true
  }
}
```

Default retention: `{ "type": "timed", "hours": 24 }`.

`audio_separate_streams` and `video_separate_streams` can also be set at the top level of `create_bot`.

### Transcription providers (use exactly one under `transcript.provider`)

> **OpenAPI marks many sub-fields as `required` even when defaults exist.** Pass the full config rather than minimal payloads when in doubt.

| Provider | Mode | Example |
|---|---|---|
| `meetstream` | Post-call | `{ "language": "auto", "translate": false }` — both fields required per spec |
| `deepgram` | Post-call | `{ "model": "nova-3", "language": "en", "punctuate": true, "smart_format": true, "diarize": true, "paragraphs": true, "numerals": true, "filler_words": false, "keywords": [], "utterances": true, "search": [], "tag": [] }` — `model` enum is `["nova-3"]` |
| `assemblyai` | Post-call | `{ "speech_models": ["universal-2"], "language_code": "en_us", "speaker_labels": true, "punctuate": true, "format_text": true, "filter_profanity": false, "redact_pii": false, "keyterms_prompt": [], "auto_chapters": false, "entity_detection": false }` |
| `sarvam` | Post-call | `{ "model": "saaras:v3", "language_code": "en-IN", "mode": "transcribe", "with_diarization": true }` |
| `jigsawstack` | Post-call | `{ "language": "auto", "translate": false, "by_speaker": true }` |
| `meeting_captions` | Live (native) | `{}` — Google Meet + Teams native captions. **No `transcript_id`.** Fetch via `bot_details.caption_file`. |
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

All values in seconds. Defaults shown above. `recording_permission_denied_timeout` is Zoom-only per the prose docs.

> **Live-tested constraints (not in OpenAPI):**
> - `in_call_recording_timeout` minimum is **600 seconds** — the API returns `HTTP 400: "in_call_recording_timeout must be at least 600 seconds"` for any value below 600. Verified by live API test.
> - `recording_permission_denied_timeout` below 60 has been observed to return HTTP 400. Stick with 60+.

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

- `new_text` — incremental delta (for streaming UI)
- `transcript` — current buffer (may be partial / interim)
- `word_is_final` — `false` means interim, may change
- `end_of_turn` — commit phrases on `true`

---

## WebSocket Control Commands

Provided via `socket_connection_url: { "websocket_url": "wss://..." }` on `create_bot`. The bot **connects to your server as a client** when it joins the meeting.

### Handshake (from bot to you)

```json
{ "type": "ready", "bot_id": "bot_abc123", "message": "Ready to receive messages" }
```

Connection closes with normal code `1000` when the bot leaves.

### `sendaudio` — play audio through bot's mic

Audio must be **raw PCM16 signed little-endian** at 48000 Hz mono, base64-encoded. No WAV header.

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

For chunked streams: 0.5–2 second chunks, pace slightly below real-time (e.g. sleep 0.8s per 1s chunk) to avoid queue gaps.

### `sendmsg` — chat message

**Both `message` AND `msg` must be set to the same value** for cross-platform compatibility.

```json
{
  "command": "sendmsg",
  "bot_id": "bot_abc123",
  "message": "Hello!",
  "msg": "Hello!"
}
```

### `sendchat` — chat with role + streaming

```json
{
  "command": "sendchat",
  "bot_id": "bot_abc123",
  "role": "assistant",
  "text": "Here is my response...",
  "is_final": true
}
```

| Field | Type | Notes |
|---|---|---|
| `role` | string | `"assistant"` or `"user"` |
| `text` | string | Message text |
| `is_final` | bool | `false` for interim streaming tokens, `true` for the committed message |

Streaming pattern: send `is_final: false` repeatedly with growing `text`, then `is_final: true` with the final committed text.

### `interrupt` — stop playback

```json
{
  "command": "interrupt",
  "bot_id": "bot_abc123",
  "action": "clear_audio_queue"
}
```

**Platform support:** Google Meet only fully clears the queue. Zoom and Teams accept the command but do not clear.

### `sendimg` — set video frame to image (base64)

```json
{
  "command": "sendimg",
  "bot_id": "bot_abc123",
  "img": "<base64-encoded JPEG or PNG>"
}
```

### `sendimg_url` — set video frame to image (URL)

```json
{
  "command": "sendimg_url",
  "bot_id": "bot_abc123",
  "img_url": "https://example.com/bot-avatar.png"
}
```

The URL must be publicly accessible.

> These two set the **bot's camera feed** to a static image (the bot's video). They are different from `POST /bots/{bot_id}/send_image` which posts to the meeting chat.

Docs: https://docs.meetstream.ai/guides/web-sockets/meeting-control-and-command-patterns

---

## Live Audio Binary Frame Format

Provided via `live_audio_required: { "websocket_url": "wss://..." }`. Bot connects to your WSS, sends a JSON `{type: "ready", bot_id, message}` handshake, then streams **binary frames**:

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

**Audio properties:** signed 16-bit PCM, little-endian, 48 kHz, mono, no container. Duration = `len(pcm_audio_data) / 2 / 48000` seconds.

**`"NoSpeaker"`** appears as `speaker_name` when MeetStream can't attribute audio. Filter or label these.

Connection closes with code `1000` when bot leaves.

Decoder implementations in Python / Node.js / Go / Java are in the docs and `code-patterns-*.md`.

---

## Live Video Streaming (fMP4 over WebSocket)

Provided via `live_video_required: { "websocket_url": "wss://..." }`. Supported on **Google Meet and Microsoft Teams only — NOT Zoom**.

### Protocol

| Message | Direction | Format | Description |
|---|---|---|---|
| `video_stream_start` | MS → you | JSON text | Once on connect. Has `codec`, `audio_codec`, `container: "fmp4"`, `width`, `height`, `framerate`, `audio_sample_rate`, `audio_bitrate`. |
| binary frames | MS → you | bytes | fMP4 chunks. **Append in order.** |
| `video_latency_ping` | MS → you | JSON text | Periodic. Has `seq`, `sent_at_ms`. |
| `video_latency_pong` | **you → MS** | JSON text | Echo `seq`, `sent_at_ms`, `bot_id`, plus `server_received_at_ms`. |
| `video_stream_end` | MS → you | JSON text | Sent before close. Has `duration_seconds`. |

### Example payloads

```json
// video_stream_start
{
  "type": "video_stream_start",
  "bot_id": "bot-123",
  "codec": "h264",
  "audio_codec": "aac",
  "container": "fmp4",
  "width": 1920,
  "height": 1080,
  "framerate": 25,
  "audio_sample_rate": 44100,
  "audio_bitrate": "128k"
}

// video_latency_ping (incoming)
{ "type": "video_latency_ping", "bot_id": "bot-123", "seq": 42, "sent_at_ms": 1743500000123 }

// your reply
{ "type": "video_latency_pong", "seq": 42, "sent_at_ms": 1743500000123, "server_received_at_ms": 1743500000189, "bot_id": "bot-123" }

// video_stream_end
{ "type": "video_stream_end", "bot_id": "bot-123", "duration_seconds": 152.7 }
```

Production tips: terminate TLS in front of your app (expose `wss://`), allow large WS frames, process writes sequentially per bot_id so chunk order is preserved.

Docs: https://docs.meetstream.ai/guides/live-video-stream
