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
- `meeting_link` (string) - Zoom, Google Meet, or Teams meeting URL
- `bot_name` (string) - name shown in the meeting

**Optional fields in the schema:**
- `video_required` (bool, **API default `false`**) - record video. **Send it explicitly on every bot** (`false` unless the user asked to record video). When it is `true`, pair it with `recording_config.video_layout` (below).
- `audio_required` (bool, default `true`) - record the mixed meeting audio. Must be `true` when `audio_mixed_mp3` is `true`. Leave it at the default.
- `zoom` (object): Zoom bots join through the user's Zoom app with an OBF token (on behalf of a user in the meeting) or a ZAK token (a signed-in bot), the way Zoom asks Meeting SDK apps to join since 2 March 2026. `{ "obf_url": "https://..." }` or `{ "zak_url": "https://..." }`, each an HTTPS endpoint on your server that returns a fresh token. `use_own_app` (bool or null): `true` requires the user's own Zoom app (400 without one), `false` joins without it, omitted/`null` uses the app when one is saved or connected. Not echoed in bot details; no fallback when Zoom refuses the app. OBF and ZAK: neither works with `use_own_app: false` (400). `use_zoom_obf` and `zoom_oauth_connection_user_id` are rejected.
- `storage_id` (string, `^[A-Za-z0-9_-]{1,80}$`) - one of the workspace's storage destinations (set up in the dashboard; no public API). Omitted: the workspace default destination, or MeetStream storage. Bad format: 400 `storage_id must contain 1-80 letters, numbers, underscores or hyphens`. Unknown ID or failed validation: 400 with the storage error text; 503 when validation is unavailable. Scheduled bots recheck it at join time and end `Error` / `StorageValidationFailed` on failure.
- `bot_camera_stream` (object) - `{ "websocket_url": "wss://..." }`: publish live WebRTC video/audio INTO the bot's camera and mic. Google Meet (ws:// or wss://), Teams and Zoom (wss:// only). The signaling host must resolve to a public address. 400 on other platforms, for a bad URL, for `ws://` on Teams/Zoom, and with `agent_config_id` on Zoom. Not available on Zoom bots that join without the user's own Zoom app. Guide: https://docs.meetstream.ai/guides/websockets/bot-camera-streaming
- `audio_separate_streams` (bool) - per-participant audio tracks (Google Meet + Zoom only). Can also be set under `recording_config`.
- `video_separate_streams` (bool) - per-participant video tracks (all 3 platforms). Can also be set under `recording_config`. **Opt-in only: never set it unless the user explicitly asked for per-participant video.** Per-participant audio is not affected by that rule.
- `bot_message` (string) - initial chat message posted on join.
- `bot_image_url` (string) - bot avatar URL. Must be a public `https://` URL to a PNG, JPEG, GIF or WebP image (a URL without one of those extensions: at most 2048 characters). `http://`, `data:` and other unusable values return 400. The host must resolve to a public address.
- `callback_url` (string) - HTTPS endpoint for lifecycle webhook events.
- `join_at` (string, ISO-8601) - schedule future join.
- `agent_config_id` (string) - MIA agent configuration ID (see MIA section).
- `custom_attributes` (object) - `additionalProperties: { description: Any type }` in the schema. **Observed behavior:** server may reject non-string values; stringify defensively.
- `socket_connection_url` (object) - `{ "websocket_url": "wss://..." }` for two-way bot control (Pattern 3).
- `live_audio_required` (object) - `{ "websocket_url": "wss://..." }` for live raw audio frames (Pattern 7).
- `live_video_required` (object) - `{ "websocket_url": "wss://..." }` for live fMP4 video (Pattern 8). Google Meet + Teams only.
- `live_transcription_required` (object) - `{ "webhook_url": "https://..." }` for live transcript chunks via HTTPS POST. **Not a WebSocket.**
- `workflow_config_ids` (string[]) - post-meeting workflow IDs.
- `recording_config` (object) - transcript provider, retention, realtime endpoints (see schema below).
- `automatic_leave` (object) - timeout rules in seconds (see schema below).

**Not in OpenAPI but documented in prose guides (also accepted):**
- `google_meet` (object) - Google Signed-In Bots: `{ "login_required": true, "google_login_domain": "your-domain.com", "sign_in_email"?: "bot@your-domain.com", "strict_email"?: true }`.
- `teams` (object) - Microsoft Teams Signed-In Bots: `{ "login_required": true, "teams_login_domain": "bots.your-domain.com", "sign_in_email"?: "bot1@bots.your-domain.com", "strict_email"?: true }`. Name and avatar come from the Microsoft account (`bot_name` / `bot_image_url` are not applied). A malformed `teams` block is dropped silently (guest join).
- For both: `login_required: true` opts in; the `*_login_domain` is required when it is set. `sign_in_email` pins one registered account. `strict_email` (default `true`): with `sign_in_email`, `true` fails if that account is busy or unhealthy, `false` falls back to any available account in the domain. See [Signed-In Bot Endpoints](#google-signed-in-bot-endpoints).

> **400 rule:** A bot with `audio_required: false` and `video_required: false` and nothing else to do (no `realtime_endpoints`, live audio/video/transcription stream, `socket_connection_url`, `bot_message` or `agent_config_id`) is rejected with 400 `audio_required and video_required are both false, so the bot would record nothing.`

**Response - HTTP 201 Created** (per OpenAPI spec and live-verified) - `BotResponse`:
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
Current bot status. Returns `{ bot_id, status, custom_attributes }`. Status values match webhook `bot_status`: `Joining`, `InMeeting`, `Recording`, `Leaving`, `Stopped`, `NotAllowed`, `Denied`, `Error`, `Done`.

---

### GET `/bots/{bot_id}/detail`
Full session metadata. Returns `{ bot_details: { ... } }`. The live API returns the following fields (verified by direct API test - the OpenAPI `BotDetailsResponseBotDetails` schema is incomplete):

```
BotID, BotImageURL, BotMessage, BotProfile, BotUsername,
CreatedAt, Duration, EndTime, LastUpdatedAt, ManifestStatus,
MediaS3Bucket, MeetingLink, NativeSTT, OfferingType, Platform,
PlatformCreatedAt, PlatformStatusCreatedAt, RequestPayload,
StartTime, Status, StatusCreatedAt, StatusTimeline,
AudioStatus, TranscriptStatus, UserID,
caption_file, participant_events, custom_attributes,
transcript_id
```

`StatusTimeline` contains entries for these lifecycle stages (each is `{message, status: bool, timestamp}`): `Scheduled`, `Joining`, `WaitingRoom`, `InMeeting`, `Recording`, `Leaving`, `Stopped`, `BotNotAllowed`, `BotRejected`, `Error`, `AudioProcessing`, `VideoProcessing`, `TranscriptionReady`, `Done`, `MediaExpired`. `status: true` means the stage was reached.

> **`transcript_id` IS at the top level of `bot_details` (live-verified).** Populated when a post-call provider (assemblyai / deepgram / jigsawstack / sarvam / meetstream) is configured; `null` for `meeting_captions` or no provider. This field is **not** listed in the OpenAPI schema but is returned by the live API. Use this as one of three ways to retrieve `transcript_id`:
> 1. The `create_bot` response (`BotResponse.transcript_id`)
> 2. `bot_details.transcript_id` on this endpoint
> 3. `GET /bots/{bot_id}/transcriptions`

`caption_file` is an S3 link to native captions when provider is `meeting_captions`. `RequestPayload` echoes the exact create_bot body. `StatusTimeline` is a map of lifecycle stages each with `{message, status, timestamp}`. `AudioStatus` mirrors the `audio.processed` event.

---

### ~~GET `/bots/{bot_id}/summary`~~ (not available)
The API has no summary route (checked on the live route table, 2026-11-17); calls return 404. Fetch the transcript and summarize it with your own model.

---

### GET `/bots/{bot_id}/get_audio`
Returns `{ "audio_url": "<pre-signed S3 URL valid 1 hour>" }`. Available after `audio.processed` webhook.

---

### GET `/bots/{bot_id}/get_video`
Returns `{ "video_url": "<pre-signed S3 URL valid 10 minutes>", "video_info": { duration, size_mb, resolution, fps, frames_processed, corrupted_frames } }`. Available after `video.processed` webhook.

---

### GET `/bots/{bot_id}/get_audio_streams`
Per-participant audio (when `audio_separate_streams: true`). HTTP **202** with `{audio_status: "in_progress" | "processing", message}` while the bot is in the meeting or processing; `[]` when nothing was recorded per participant.

Completed response, a **flat top-level array**, one item per segment:
```json
[
  {
    "id": "<bot_id>-<stream_id>-0",
    "created_at": "2026-11-19T14:30:05Z",
    "is_bot": false,
    "participant": { "id": 123456, "name": "John Doe", "is_host": false, "is_bot": false, "platform": "desktop",
                     "extra_data": { "google_meet": { "static_participant_id": "..." } } },
    "start_timestamp": { "absolute": "2026-11-19T14:30:05Z", "relative": 4.2 },
    "duration": 125.5,
    "download_url": "https://...",
    "download_url_mp3": "https://..."
  }
]
```

The speaker is `participant.name`; group by `participant.id`. URLs are pre-signed, **valid 1 hour**. `download_url_mp3` is present only when an MP3 copy exists. **Not supported on Microsoft Teams.**

---

### GET `/bots/{bot_id}/get_recording_streams`
Per-participant video (when `video_separate_streams: true`). Same 202 pattern. Same flat item shape as `get_audio_streams` (without `is_bot` / `download_url_mp3`), plus `"type": "webcam" | "screenshare"`. URLs valid 1 hour. File format: WebM container, VP8 codec, 15 FPS, video-only. Supported on all 3 platforms.

---

### GET `/bots/{bot_id}/get_speaker_timeline`
Returns `{chunks: [{chunkIndex, timestamp, sampleRate, speakerId, speakerName, startByte, endByte}], lastUpdated, audioFilePath, totalFileSize}`. The `startByte`/`endByte` are **byte offsets into the audio file**, not time offsets.

**Large timelines return a download link instead.** When the timeline is about 5 MB or more, the response is still 200 but the body is:

```json
{ "bot_id": "abc-123", "speaker_timeline_url": "https://...", "size_bytes": 8421337, "truncated": false }
```

`speaker_timeline_url` is a pre-signed URL (no API key needed), valid for 1 hour; call the endpoint again for a fresh link. `truncated` is always `false`: the file is the complete timeline in the same format as the inline body. Always check for `speaker_timeline_url` before you parse. Before the bot leaves: 404 `{"message": "Manifest file not found. It may still be processing."}`.

---

### GET `/bots/{bot_id}/get_chats`
In-meeting chat messages captured by the bot: `{"metadata": {...}, "speakers": [...], "chatMessages": [{"messageId", "deviceId", "timestamp", "text", "speakerName", "speakerDisplayName"}], "messagesBySpeaker": {...}}`.

---

### GET `/bots/{bot_id}/screenshots`
Screenshots captured during the meeting: `{"screenshots": [{"id", "recorded_at", "url", "filename", "size_bytes"}]}`. One screenshot: `GET /bots/{bot_id}/screenshots/{id}`.

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

### POST (or GET) `/bots/{bot_id}/remove_bot`

Both forms behave the same and take no body. Apps call it on shutdown (Ctrl-C) so the bot does not stay in the meeting.

Removes the bot from an active meeting. **GET per the OpenAPI spec.** (The Quickstart docs page shows `curl -X POST` which contradicts the spec; trust the OpenAPI.)

---

### DELETE `/bots/{bot_id}/delete`
Permanently deletes audio, video, and transcript data. Triggers `data_deletion` webhook event. Returns `{ message, bot_id, deleted_objects }`.

---

### GET `/bots`
Lists all bots for the account. Returns `{bots: [...], hasNextPage: bool, nextCursor: string|null}` - note camelCase pagination keys.

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

- **`img_url`** (string, **required**) - NOT `image_url`. Must resolve to a public address on every redirect hop, or the bot refuses to download it.
- `display_duration` (integer, optional) - how long to display.
- `metadata` (object, optional) - `{message_type: string}`.

Response: `{status, bot_id, command}`.

---

### POST `/bots/{bot_id}/pause_recording`

Pause recording mid-meeting. Empty body - no parameters. The bot stays in the meeting; recording (and any live transcription) is suspended until you resume.

```bash
curl -X POST "https://api.meetstream.ai/api/v1/bots/{bot_id}/pause_recording" \
  -H "Authorization: Token $MEETSTREAM_API_KEY"
```

Use for privacy windows (break, off-record discussion). Returns 200 on success.

### POST `/bots/{bot_id}/resume_recording`

Resume a paused recording. Empty body - no parameters. Pairs with `pause_recording` for mid-meeting recording control.

```bash
curl -X POST "https://api.meetstream.ai/api/v1/bots/{bot_id}/resume_recording" \
  -H "Authorization: Token $MEETSTREAM_API_KEY"
```

### POST `/bots/{bot_id}/send_command`
Run one command on a live bot. Body: `{ "command": "<name>", ... }`.

**`raise_hand` / `lower_hand`** (Google Meet, Zoom, Microsoft Teams). Body `{"command": "raise_hand"}` or `{"command": "lower_hand"}`; no other fields are used.

Response 200:
```json
{ "status": "accepted", "bot_id": "83acdd72-3257-4b06-a2e9-0d879dc571ff", "command": "raise_hand", "hand_raised": true }
```

- The bot **must be in the meeting** (`InMeeting` or `Recording`). Joining, lobby or left: **409**.
- `hand_raised` is the state the bot read back from the meeting after acting. Repeats are no-ops that return the current state.
- The bot answers within 10 seconds; allow that before you treat the request as failed. Retry a 5xx once.
- 400 for WhatsApp (`unsupported_on_whatsapp`) and Zoom RTMS (`unsupported_on_zoom_rtms`) bots. 501 for bots that run outside the US region.
- Guide: https://docs.meetstream.ai/guides/features/raise-lower-hand

**`update_mia`** - see [POST `/bots/{bot_id}/update_mia`](#post-botsbot_idupdate_mia); the same body plus `"command": "update_mia"` works here.

Other commands: `screenshot` (MCP tool `take_screenshot`; on Zoom only for bots that join without the user's own Zoom app), `pause_recording`, `resume_recording`, `sendmsg`, `sendimg`, `sendimg_url`, `interrupt`. On Zoom and Teams, chat sent while the bot is in the lobby is held and posted on admission; Google Meet returns 409.

---

### POST `/bots/{bot_id}/update_mia`
Change a running MIA agent mid-meeting. Body: at least one of `agent_config_params` (object, merged into the current params), `system_prompt` (string, replaces the instructions), `wake_word_enabled` (bool), `wake_words` (string array), plus optional `wait_for_ack` (bool, default `false`).

- Without `wait_for_ack`: `{ "status": "accepted", "bot_id": "...", "command": "update_mia" }` means accepted for delivery, not applied.
- With `"wait_for_ack": true`: `status` is `applied`, `partially_applied`, `failed` or `accepted`, plus `applied` (fields applied), `errors` (`[{field, reason}]`, for example `session_not_started`) and `ack_timeout: true` when the agent did not answer in time (the update may still apply).
- Non-boolean `wait_for_ack`: 400 `wait_for_ack must be a boolean (true or false)`.

---

### POST `/bots/{bot_id}/transcribe`
Trigger a new post-call transcription run on the bot's stored audio. **Live-verified behaviors:**

- Works on any bot with stored audio - including bots that originally used a **streaming-only** provider (which have `transcript_id: null` and empty `/transcriptions`). This is the **only way** to get a post-call transcript from a streaming-only bot.
- Returns immediately with a new `transcript_id` and starts processing in the background
- **Overwrites `bot_details.transcript_id`** with the new id (canonical fetch always returns the latest run)
- Adds an entry to `GET /bots/{bot_id}/transcriptions` with `status: "Processing"` → `"Success"` or `"Failed"`
- Fires **exactly one** `transcription.processed` or `transcription.failed` event on the `callback_url` passed in the body
- Payload shape is identical to a Path-A bot's transcription event (same `event` name, `transcript_status`, `status_code` 200/500)
- **Does NOT fire `bot.done`** - `/transcribe` is single-event fire-and-forget, not a lifecycle restart
- **Does NOT include `custom_attributes`** in the webhook payload (unlike original lifecycle events). Correlate by `bot_id`.

Body (`TranscribeRequest`):

```json
{
  "provider": {
    "deepgram": { "model": "nova-3", "language": "en" }
  },
  "callback_url": "https://your-server.com/webhook"
}
```

- `provider` (object, **required**) - top-level. Pick exactly one sub-key: `deepgram`, `meetstream`, `jigsawstack`, `sarvam`, `assemblyai`, or `smallest`. (Same shape as `recording_config.transcript.provider` but `provider` is the top-level body key.)
- `callback_url` (string, optional) - where to send the transcription.processed/.failed webhook for this run.

Response (`TranscribeResponse`): `{ bot_id, transcript_id, provider, message }`.

> **When to use `/transcribe` (it's a fallback, not the default):**
> - The bot used a streaming-only provider and you also want a post-call transcript
> - The original `create_bot` provider failed (out of credit, wrong config) and you want to retry with a different provider
> - You want to re-transcribe with a higher-quality / different-language provider
>
> For standard post-call transcripts, configure the provider on `create_bot` up front and use the canonical fetch flow - no `/transcribe` call needed.

---

## Transcription Endpoints

### GET `/transcript/{transcript_id}/get_transcript`
Returns the processed transcript by `transcript_id`. The `transcript_id` comes from any of four places:
1. The `create_bot` response (for assemblyai/deepgram/jigsawstack/sarvam/meetstream providers - null for `meeting_captions`)
2. **`GET /bots/{bot_id}/detail` → `bot_details.transcript_id`** (live-verified, not in OpenAPI schema)
3. `GET /bots/{bot_id}/transcriptions` (lists every run)
4. The `POST /bots/{bot_id}/transcribe` response

Query: `?raw=true` to retrieve raw unformatted provider output.

**Response is a top-level JSON array.** By default it is participant-keyed (`GetTranscriptionV2Schema`):
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
The `meetstream` engine can add a lone "Thank you." segment on silence; treat it as filler.

The segment-list format (`GetTranscriptionSchema`), when a provider returns it:
`[{"speaker": "Alice", "transcript": "...", "start_time": 0.5, "end_time": 3.2, "absolute_start_time": "...", "words": [{"word", "punctuated_word", "start", "end", "confidence", "speaker"}]}]`.

- Response is the array itself, not `{transcript: [...]}`.

`?raw=true` returns a different shape (`GetRawTranscriptionSchema`) with `id` and provider-specific structure.

Other status codes:
- **202** `{"message": "Transcript is still being processed. ..."}`: poll again with a cap (a streaming-only bot never gets a post-call transcript).
- **422** (API v1.10.0): the run failed. Body `{"message": "Transcript processing failed: <reason>", "transcript_status": "Failed", "transcript_id": "..."}`, for example the provider rejected the API key or the usage limit was reached. Final: do not retry. Fix the cause, then `POST /bots/{bot_id}/transcribe`.

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
List connected calendars (alternate path). Same shape as above.

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
Same as `/calendar/events` but reads from MeetStream's local DB only (no Google API call - faster).

---

### POST `/calendar/schedule/{event_id}`
Manually schedule a bot for a specific event. `event_id` is the `id` from `/calendar/events`.

**Body.** `bot_config` takes the `create_bot` fields. The transcript provider goes under `recording_config.transcript.provider`, as on `create_bot`; a top-level `transcription` key is ignored and the scheduled bot gets no transcript.
```json
{
  "bot_config": {
    "bot_name": "My Meeting Bot",
    "audio_required": true,
    "video_required": false,
    "bot_message": "Joining to record",
    "callback_url": "https://...",
    "automatic_leave": { "no_one_joined_timeout": 600, "everyone_left_timeout": 600 },
    "recording_config": { "transcript": { "provider": { "meetstream": { "language": "en" } } } }
  },
  "occurrence_date": "2026-04-14T10:00:00Z",
  "schedule_all_occurrences": false,
  "occurrence_limit": 52,
  "recurring_event": false
}
```

| Field | Type | Default | Description |
|---|---|---|---|
| `bot_config` | object | - | Same shape as `create_bot` body (`audio_required` IS valid here) |
| `occurrence_date` | ISO-8601 | - | Specific recurring occurrence to schedule |
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

**Body** (from docs guide; calendar `default_bot_config` schema not live-tested by this skill - see note on `/calendar/schedule/{event_id}` above for caveats):
```json
{
  "default_bot_config": {
    "bot_name": "MeetStream Auto Bot",
    "audio_required": true,
    "video_required": false,
    "callback_url": "https://...",
    "recording_config": { "transcript": { "provider": { "meetstream": { "language": "en" } } } },
    "automatic_leave": { "no_one_joined_timeout": 600, "everyone_left_timeout": 600 }
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

### DELETE `/calendar/disconnect`
Disconnects the calendar - irreversible. Stops Google Calendar watch channels, cancels pending bot schedules, deletes all synced event data, and removes stored Google OAuth credentials.

```bash
curl -X DELETE "https://api.meetstream.ai/api/v1/calendar/disconnect" \
  -H "Authorization: Token <YOUR_API_KEY>"
```

**Response:**
```json
{
  "disconnected": true,
  "user_id": "usr_abc123",
  "watch_channel_stopped": true,
  "events_deleted": 42,
  "schedules_cancelled": 5,
  "message": "Calendar disconnected successfully. All events and scheduled bots have been removed."
}
```

> The OpenAPI spec shows this as `POST` with a `CalendarCreateRequest` body - that's a quirk in the spec. The docs guide, cURL example, and response example all use `DELETE` with no body. Follow the docs guide.

---

## Google Signed-In Bot Endpoints

For bots that authenticate to Google Meet as a real user. Setup involves Google Workspace SSO (Legacy SSO profile) + an OpenSSL key/certificate; see https://docs.meetstream.ai/guides/app-integrations/google-signed-in-bots

### POST `/google-login-domains`
Register a Google Workspace domain. Body: `{ "sso_workspace_domain": "your-company.com", "name"?: "...", "login_mode"?: "always" | "if_required" }` (default `always`). Returns 201 `{ sso_workspace_domain, name, login_mode, max_concurrent_per_login, created_at }`; 409 if already registered.

### GET `/google-login-domains`
`{ domains: [{ sso_workspace_domain, name, login_mode, max_concurrent_per_login, login_count, active_login_count, created_at }] }`

### GET `/google-login-domains/{domain}`
Fetch one domain with its `logins`. **`{domain}` is the workspace domain string** (e.g. `your-company.com`), not an opaque id.

### PATCH `/google-login-domains/{domain}`
`{ name?, login_mode? }`

### DELETE `/google-login-domains/{domain}`
Deletes the domain and its logins. Refused (400) while any login is active; disable them first.

### POST `/google-logins`
`{ "domain": "your-company.com", "email": "bot@your-company.com", "sso_private_key_pem": "<contents of key.pem>", "sso_cert_pem": "<contents of cert.pem>", "is_active"?: true }` → 201 `{ login_id, domain, email, is_active, created_at }`

### GET `/google-logins?domain=<d>`
`{ logins: [{ login_id, email, is_active, active_sessions, last_test_status, last_tested_at, created_at }] }`. There is **no** `GET /google-logins/{login_id}`.

### PATCH `/google-logins/{login_id}`
Body **must include `domain`**, plus any of `is_active`, `email`, `sso_private_key_pem`, `sso_cert_pem`. Credential changes and deactivation are refused while the login has active sessions.

### DELETE `/google-logins/{login_id}?domain=<d>`
Refused while the login has active sessions.

### Then on `create_bot`, attach via:
```json
{
  "google_meet": {
    "login_required": true,
    "google_login_domain": "your-company.com",
    "sign_in_email": "bot@your-company.com",
    "strict_email": true
  }
}
```

(`google_meet` is documented in the Google Signed-In Bots guide; it isn't in the OpenAPI `CreateBotRequest` schema but is the canonical activation payload.)

---

## Microsoft Teams Signed-In Bot Endpoints

For bots that join Teams as a real Microsoft 365 account (meetings that block anonymous join). Requires a dedicated M365 tenant with security defaults disabled and self-service password reset set to None for the bot accounts. Microsoft 365 work/school Teams only (not `teams.live.com`). Guide: https://docs.meetstream.ai/guides/app-integrations/teams-signed-in-bots

### POST `/teams-login-domains`
`{ "domain": "bots.your-company.com", "name"?: "...", "login_mode": "always" }` (`domain` required; `if_required` is not supported for Teams yet) → 201 `{ domain, name, login_mode, created_at }`

### GET `/teams-login-domains`
`{ domains: [{ domain, name, login_mode, login_count, active_login_count, created_at }] }`

### GET `/teams-login-domains/{domain}`
`{ domain, name, login_mode, logins: [{ login_id, email, is_active, lease_status, last_session_result }], created_at, updated_at }`; 404 `{ "error": "Domain not found" }`

### PATCH `/teams-login-domains/{domain}`
`{ name?, login_mode? }` → `{ success, domain: { domain, name, login_mode, updated_at } }`

### DELETE `/teams-login-domains/{domain}`
Deletes the domain **and all associated logins** → `{ success, message }`

### POST `/teams-logins`
`{ "domain": "bots.your-company.com", "email": "bot1@bots.your-company.com", "password": "<ACCOUNT_PASSWORD>", "is_active"?: true }` → 201 login object. The password is write-only (never returned); load it from a secret store, never hardcode it.

### GET `/teams-logins?domain=<d>`
`domain` is required (400 without it) → `{ logins: [login] }`; 404 `{ "error": "Domain <d> not registered" }`

### GET `/teams-logins/{login_id}`
Login object; 404 `{ "error": "Login not found" }`

### PATCH `/teams-logins/{login_id}`
`{ password?, is_active? }` → `{ success, login }`. A new password also reactivates an account that was deactivated after a failed sign-in.

### DELETE `/teams-logins/{login_id}`
→ `{ success, message: "Login deleted successfully" }`

Login object: `{ login_id, domain, email, is_active, lease_status, last_session_result, last_login_error, created_at, updated_at }`

### Then on `create_bot`, attach via:
```json
{
  "teams": {
    "login_required": true,
    "teams_login_domain": "bots.your-company.com",
    "sign_in_email": "bot1@bots.your-company.com",
    "strict_email": true
  }
}
```

- **One concurrent bot per account.** Register N accounts for N concurrent signed-in Teams bots.
- `bot_name` / `bot_image_url` are not applied: the Microsoft account's display name and picture are used.

| `create_bot` error | Meaning |
|---|---|
| 400 `teams.teams_login_domain '<d>' is not registered...` | Register the domain first |
| 403 | Domain or account belongs to another MeetStream account |
| 404 | `sign_in_email` not registered under the domain |
| 409 | Pinned account busy/deactivated with `strict_email: true`, or no account both active and free |
| 429 `all Teams logins ... in use` | Every account in the domain is leased |

---

## MIA (MeetStream Infrastructure Agents) Endpoints

All MIA operations use the same path `/api/v1/mia` (singular). The HTTP method distinguishes the operation.

MCP tools for the same operations (use them when the MeetStream MCP is connected): `list_agents` (`GET`, with `mia_managed`, no prices), `get_agent`, `create_agent` (`POST`), `update_agent` (`PUT`; a `mode` change needs the full config), `delete_agent` (`DELETE`, `confirm: true`), `check_local_agent` (`?check=local_agent`, for the coming-soon track 3d only). `create_agent` refuses `key_source: "meetstream"` in realtime mode.

### POST `/api/v1/mia` - Create

**Required:**
- `agent_name` (string)
- `mode` (string) - `"pipeline"` or `"realtime"`
- `model` (object) - see below. `model.system_prompt` is required except with `local_agent`: without it the API returns `400` `{"message": "Missing model.system_prompt."}`

**Optional:**
- `voice` (object, **pipeline only**; `voice.voice_id` is required in pipeline mode: `400` `{"message": "Missing voice.voice_id."}`)
- `transcriber` (object, **pipeline only**)
- `agent` (object) - `response_type` (`"voice"` / `"chat"` / `"action"`, default `"voice"`), `first_message` (string), `mcp_servers` (array), `tools` (`current_time`, `weather_now`, `screen`: Google Meet only, vision-capable model), `desktop` (Google Meet, with `screen`, opt-in), `chat_input`, `quiet_actions`, `speak_only_when_asked` (pipeline) - all default `false`
- `audio` (object) - `sample_rate`, `num_channels`
- `wake_word` (object, **pipeline only**) - `enabled` (bool), `words` (array or comma-separated string), `timeout` (seconds, default 30)
- `avatar` (object) - `enabled` (bool), `provider` (`"anam"`), `avatar_id` (required when provider is anam)

**Keys (`key_source`, pipeline sections `transcriber`, `model`, `voice`):** `"meetstream"` = MeetStream's inbuilt key (pipeline mode only, no `api_key` in that section; inbuilt keys cover OpenAI and Deepgram today); `"user"` or not sent = the user's own key from dashboard Integrations. `400 MeetStream-managed keys are not available for <section>. Use your own key.` means inbuilt keys are not on for the account yet: use own keys, do not retry. Price: bot + $0.25 per hour agent infrastructure + the models picked. https://docs.meetstream.ai/guides/mia/pricing-and-keys . This is track 3 (Agents API infra, hosted: 3a default keys, 3c own keys); an agent on the user's own stack uses a bridge server (track 2) instead (both `live_audio_required` and `socket_connection_url` on the bot, the bot price only): https://docs.meetstream.ai/guides/websockets/bridge-server-architecture

**`model` schema (pipeline):**
- `provider` - `"openai"`, `"anthropic"`, `"google"`, `"xai"`, or `"local_agent"` (track 3d, COMING SOON, not in production: do not give it as a working option; the user's own coding agent through `meetstream setup` once the relay is live: `model.local_agent` = `url` (https, required), `label`, `access` (`readonly` default, `confirm`, `full`), `require_code` (default true), `owner_only` (default true), `owner_names` / `owner_ids`, `timeout_s` (10-600, default 120); `model.model` and `system_prompt` optional; test with `GET /api/v1/mia?agent_config_id=<id>&check=local_agent`)
- `model` - e.g. `"gpt-4.1"`, `"gpt-4.1-mini"`; for Anthropic e.g. `"claude-haiku-5-5"`, `"claude-sonnet-5-5"`, `"claude-opus-5-5"`
- `system_prompt` - defines personality
- `temperature` (optional, 0–2; 0–1 for Anthropic)
- `max_tokens` (optional)

**Anthropic (`provider: "anthropic"`) constraints:**
- Pipeline mode only. Uses the Anthropic key saved in the dashboard under model integrations (provider `anthropic`).
- `reasoning_effort` optional (`"low"` when omitted; `"low"`, `"medium"`, `"high"`, and `"xhigh"` / `"max"` on models that keep thinking on).
- `tool_choice` only `"auto"` or `"none"`.
- `top_p`, `frequency_penalty`, `presence_penalty`, `logit_bias` → 400 `Anthropic models do not support: ...`.
- Anthropic is a MIA LLM provider only, not a transcription provider.

**`model` schema (realtime):**
- `provider` - `"openai"`, `"xai"`, or `"google"`
- `model` - required for OpenAI only
- `system_prompt`
- `voice` - required; valid values:
  - OpenAI: `alloy, ash, ballad, coral, echo, fable, nova, onyx, sage, shimmer, verse`
  - xAI: `Ara, Eve, Leo, Rex, Sal`
  - Google: `Puck, Charon, Kore, Fenrir, Aoede, Leda, Orus, Zephyr`
- `temperature` (optional)
- `max_response_output_tokens` (optional, OpenAI only)
- `thinking_config` (Google Gemini, optional) - `{include_thoughts: bool, thinking_budget: int}`

**`voice` schema (pipeline TTS):**
- `provider` - `"openai"` or `"elevenlabs"`
- `voice_id` - required
- `model` - e.g. `"tts-1"`, `"eleven_turbo_v2_5"`

**`transcriber` schema (pipeline STT):**
- `provider` - `"openai"`, `"deepgram"`, or `"assemblyai"`
- `model` - e.g. `"nova-3"`, `"whisper-1"`
- `language` - e.g. `"en"`, `"es"`
- `boostwords` - array of strings

**`agent.mcp_servers[]`:**
- `url` (HTTPS, required)
- `headers` (object, e.g. `{Authorization: "Bearer ..."}`)
- `allowed_tools` (array, whitelist)
- `timeout` (seconds, default 10)

**Response (200):** `{ message, agent_config_id, agent_config: {...} }`

### GET `/api/v1/mia`
Lists all or returns one (`?agent_config_id=...` query param). Secrets in the response are masked (`****` + last four characters): `api_key`-like fields and header values in `mcp_servers` / custom functions. Sending a masked value back on `PUT` keeps the stored secret.

Returns `{ agent_configs: [...], count }` or `{ agent_config: {...} }`.

### PUT `/api/v1/mia` - Update
Body requires `agent_config_id` plus any subset of: `agent_name`, `mode`, `model`, `voice`, `transcriber`, `agent`, `wake_word`, `audio`, `avatar`. Only included fields are updated.

> Changing `mode` triggers full re-validation. Updating individual sections (model/voice/transcriber) only validates required API keys exist.

### DELETE `/api/v1/mia?agent_config_id=...`
**Query param**, not path id. Returns `{ message }`.

### Error codes
- `400` - missing required field, invalid value, unsupported provider, provider API key not configured
- `403` - not the owner
- `404` - not found
- `405` - method not allowed
- `500` - server error

### Using a MIA agent on a bot

Pass only the `agent_config_id` - MeetStream runs the agent on its own hosted bridge.

```json
POST /bots/create_bot
{
  "meeting_link": "...",
  "agent_config_id": "<id>"
}
```

Do **not** send `socket_connection_url` or `live_audio_required` for MIA (a silent agent); those are for the bridge server flow and the real-time patterns, point at your own server, and go on a separate bot.

---

## Webhook Events (sent to `callback_url`)

HTTP POST. Your endpoint MUST return 2xx - **webhooks are not retried on non-2xx**.

**Full event list (verified against 4,139 captured webhook deliveries, Jun 2026):**

Every delivery carries `event`, `bot_id` and `timestamp`. Most also carry `bot_event`, which equals `event` except on terminals.

| # | event | bot_status | status_code | When | Extra payload fields |
|---|---|---|---|---|---|
| 0 | `bot.scheduled` | | 200 | Created with a future `join_at` | |
| 1 | `bot.joining` | `Joining` | 200 | Bot is connecting | |
| 1a | `bot.in_waiting_room` | `InWaitingRoom` | 200 | Held in the lobby | |
| 1b | `bot.error` | `InMeeting` | omitted | Streaming-provider upstream error during the meeting (e.g. AssemblyAI insufficient funds). Bot continues; only live transcription is impacted. Seen in May 2026 testing. | `message` (upstream error) |
| 2 | `bot.inmeeting` | `InMeeting` | 200 | Bot joined the meeting | |
| 3 | `bot.recording` | `Recording` | 200 | Recording started | |
| 4 | `participant_events.join` / `.leave` | | | Participants join/leave (requires `recording_config.realtime_endpoints` with `events: [...]`) | Nested under `data.data.{action,participant,timestamp}` and `data.bot.{id,metadata}`. No top-level `bot_id`, `bot_status` or `bot_event`. |
| 4a | `participant_events.raise_hand` / `.lower_hand` | | | A participant raised or lowered their hand (Google Meet, Zoom). Sent **only** to `realtime_endpoints` entries that list the event; never to workspace webhooks or `callback_url`. Transitions only; the bot's own hand is never reported | Same nested shape as `participant_events.join`; `data.data.action` is `raise_hand` / `lower_hand` |
| 5 | `bot.leaving` | `Leaving` | 200 | Bot is leaving the meeting | |
| 6 | `bot.stopped` | varies | 200 or 500 | Bot exited or never got in (fires once per bot). **Reason is in `bot_event`**, see below | |
| 6a | `bot.uploading` | | 200 | Media upload in progress | |
| 7 | `manifest.completed` | | 200 | Platform manifest uploaded | `status: "success"`, `manifest_status: "Success"` |
| 8 | `audio.processed` | | 200 | Audio ready to fetch | `status: "success"`, `audio_status: "Success"` |
| 9 | `transcription.processed` | | 200 | Transcript ready. **Post-call providers only** | `transcript_status: "Success"` |
| 9a | `bot.transcriptionready` | | 200 | Follows `transcription.processed` | |
| 9b | `transcription.failed` | | **500** | Transcript run failed. **Post-call providers only** | `status: "error"`, `transcript_status: "Failed"`, `message` (error detail) |
| 9c | `audio.skipped` / `manifest.skipped` / `transcription.skipped` | | | That stage had nothing to process (e.g. the bot never recorded) | |
| 10 | `video.processed` | | 200 | Video ready (only when `video_required: true`) | `video_status: "Success"` |
| 11 | `bot.done` | `Done` | 200 | All processing complete. **Final event on every path**, streaming-only bots included | `message` |
| 12 | `data_deletion` | | 200 | Data deleted (manual `/delete` or retention expiry) | `status: "success"`, `deleted_objects: <int>`. No `custom_attributes` |

**Terminals are two-layer.** Every ending arrives once with `event: "bot.stopped"`; `bot_event` gives the reason:

| `bot_event` | `status_code` | `bot_status` |
|---|---|---|
| `bot.stopped` (clean exit) | 200 | `Stopped` |
| `bot.kicked` (removed by a participant) | 200 | `Stopped` |
| `bot.notallowed` (lobby timeout) | 500 | `NotAllowed` |
| `bot.denied` (host refused) | 500 | `Denied` |
| `bot.failed` | usually 500 | `FAILED` / `ERROR` / `Failed` |

Branch on `bot_event`. A kick and a clean exit both report `Stopped`, and failure casing varies.

> **Streaming-only providers (`meetstream_streaming`, `assemblyai_streaming`, `deepgram_streaming`, `jigsawstack_streaming`, `meeting_captions`) never fire events 9, 9a or 9b.** They still get `bot.done` (50 of 50 streaming bots that recorded, in the captures). Use `bot.done` as the "session finished" signal on both paths.

Each event fires **at most once** per bot, except `bot.joining` (up to 3× if server-side join retries kick in) and `bot.inmeeting`, which can repeat.

> **Common envelope**: `bot_id`, `event`, `bot_event`, `message`, `status_code`, `custom_attributes`, `timestamp`. Exceptions:
> - `participant_events.*` has a completely different shape (nested under `data.bot.id`, no top-level `bot_id`)
> - `manifest.completed`, `manifest.skipped`, `bot.transcriptionready` and `bot.uploading` have no `bot_event`; read `payload.bot_event ?? payload.event`
> - `data_deletion` has no `custom_attributes`
> - **`status_code` is 500** for `transcription.failed` and failing terminals (`bot.notallowed`, `bot.denied`, most `bot.failed`). All captured `bot.done` deliveries were 200.

### `transcript_id` is NOT in the webhook payload

`transcription.processed` only signals timing. Fetch `transcript_id` via the canonical path - `GET /bots/{bot_id}/detail` → `bot_details.transcript_id` (also available in the `create_bot` response and `GET /bots/{bot_id}/transcriptions`).

### Sample payloads (live-captured)

**Lifecycle (`bot.joining` / `bot.in_waiting_room` / `bot.inmeeting` / `bot.recording` / `bot.leaving` / `bot.done`):**
```json
{
  "event": "bot.joining",
  "bot_event": "bot.joining",
  "bot_id": "dd451299-1471-49ae-b407-c91541242748",
  "bot_status": "Joining",
  "message": "Bot is joining the meeting",
  "status_code": 200,
  "custom_attributes": {"your_keys": "echoed back"},
  "timestamp": "2026-06-16T06:28:14.445Z"
}
```

**Terminal (bot never admitted):**
```json
{
  "event": "bot.stopped",
  "bot_event": "bot.notallowed",
  "bot_id": "...",
  "bot_status": "NotAllowed",
  "status_code": 500,
  "message": "...",
  "custom_attributes": {...},
  "timestamp": "..."
}
```

**Recording:**
```json
{
  "event": "bot.recording",
  "bot_event": "bot.recording",
  "bot_id": "...",
  "bot_status": "Recording",
  "message": "Bot started recording",
  "status_code": 200,
  "custom_attributes": {...},
  "timestamp": "..."
}
```

**`participant_events.leave`** - different shape:
```json
{
  "event": "participant_events.leave",
  "timestamp": "2026-05-26T10:11:14.990Z",
  "data": {
    "data": {
      "action": "leave",
      "participant": {
        "id": "spaces/.../devices/290",
        "name": "Unknown",
        "full_name": "Skill Audit Bot",
        "platform": "gmeet"
      },
      "timestamp": {"relative": 50.792, "absolute": "2026-05-26T10:11:14.990Z"}
    },
    "bot": {"id": "...", "metadata": {}}
  },
  "custom_attributes": {...}
}
```

**Post-call (`manifest.completed`, `audio.processed`, `transcription.processed`, `video.processed`)** - includes `timestamp` and `status`:
```json
{
  "event": "audio.processed",
  "bot_id": "...",
  "status": "success",
  "audio_status": "Success",
  "message": "Audio processing completed successfully",
  "status_code": 200,
  "custom_attributes": {...},
  "timestamp": "2026-05-26T10:11:23.018672+00:00"
}
```

**Failure (`transcription.failed`)** - `status_code: 500`:
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

**Terminal (`bot.done`)** - fires last:
```json
{
  "event": "bot.done",
  "bot_id": "...",
  "bot_status": "Done",
  "message": "Error: Transcript processing failed: Deepgram API error: 401",
  "status_code": 500,
  "timestamp": "2026-05-26T10:11:26.248022+00:00",
  "custom_attributes": {...}
}
```

**Data deletion** - fires after manual `DELETE /bots/{id}/delete` or retention expiry:
```json
{
  "event": "data_deletion",
  "bot_id": "...",
  "status": "success",
  "message": "Successfully deleted 7 objects for bot ...",
  "deleted_objects": 7,
  "timestamp": "2026-05-26T10:12:31.488763+00:00",
  "status_code": 200
}
```

### Delivery rules

- Every delivery sends `User-Agent: MeetStream-Webhook/1.0`.
- Webhooks from post-call processing (`manifest.completed`, `audio.processed`, `transcription.*`, `video.processed` and the other post-call events) are delivered only to URLs that resolve to public addresses, on every redirect hop. A private, loopback or metadata address is not delivered to.

### Webhook signature (optional)

Only deliveries to **workspace webhook endpoints** (added in the MeetStream dashboard with
a signing secret) are signed. Per-bot `callback_url` deliveries are **not signed**: if you
need signatures, add the URL as a workspace webhook endpoint. Signed requests include:
- `X-MeetStream-Signature: sha256=<hex>` - `HMAC-SHA256(secret, raw_body)`
- `X-MeetStream-Timestamp: <iso8601>`: an ISO 8601 UTC string such as `2026-11-19T14:30:00Z`. Parse it as a time, not as a number.

### Idempotency

Dedupe on `{bot_id, bot_event ?? event, timestamp}`. Every event carries a `timestamp` (verified on all 4,139 captured deliveries, lifecycle events included).

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
        "events": ["participant_events.join", "participant_events.leave", "participant_events.raise_hand", "participant_events.lower_hand"]
      }
    ],
    "video_layout": "speaker_view",
    "audio_separate_streams": true,
    "video_separate_streams": true
  }
}
```

Default retention: `{ "type": "timed", "hours": 24 }`.

`audio_separate_streams` and `video_separate_streams` can also be set at the top level of `create_bot`. `video_separate_streams` is opt-in only: never set it unless the user explicitly asked for per-participant video.

### `video_layout`

- Values: `"speaker_view"` and `"grid_view"` (Google Meet, Teams, Zoom). Google Meet and Teams also accept `"speaker_view_default"` and `"grid_view_default"`, where the bot records the platform's own speaker or grid view in the call as one finished file (Teams `grid_view_default` shows at most 9 tiles). The old names `video_speaker_default` / `video_grid_default` are accepted as aliases. Any other value returns 400 `invalid video_layout value. Allowed values: ...` with the values for that platform.
- **API default is `"grid_view"`** when `video_required: true`, so `"speaker_view"` must be sent explicitly. Send `"speaker_view"` whenever video is enabled unless the user explicitly asked for grid or gallery view or for the platform's own layout.
- Ignored when `video_required` is `false`. An audio-only bot never runs the compositor.
- WhatsApp accepts only `"grid_view"`. Any other platform rejects the field.
- Speaker view follows the active speaker. Grid view is a composited mosaic of everyone. Google Meet speaker view recordings are 1600x900.

### `realtime_endpoints[].events`

`participant_events.join`, `participant_events.leave`, `participant_events.raise_hand`, `participant_events.lower_hand`. Hand events reach only the endpoints that list them.

### Transcription providers (use exactly one under `transcript.provider`)

> **OpenAPI marks many sub-fields as `required` even when defaults exist.** Pass the full config rather than minimal payloads when in doubt.

| Provider | Mode | Example |
|---|---|---|
| `meetstream` | Post-call | `{ "language": "auto", "translate": false }` - both fields required per spec |
| `deepgram` | Post-call | `{ "model": "nova-3", "language": "en", "punctuate": true, "smart_format": true, "diarize": true, "paragraphs": true, "numerals": true, "filler_words": false, "keywords": [], "utterances": true, "search": [], "tag": [] }` - `model` enum is `["nova-3"]` |
| `assemblyai` | Post-call | `{ "speech_models": ["universal-2"], "language_code": "en_us", "speaker_labels": true, "punctuate": true, "format_text": true, "filter_profanity": false, "redact_pii": false, "keyterms_prompt": [], "auto_chapters": false, "entity_detection": false }` |
| `sarvam` | Post-call | `{ "model": "saaras:v3", "language_code": "en-IN", "mode": "transcribe", "with_diarization": true }` |
| `jigsawstack` | Post-call | `{ "language": "auto", "translate": false, "by_speaker": true }` |
| `meeting_captions` | Live (native) | `{}` - Google Meet + Teams native captions. **No `transcript_id`.** Fetch via `bot_details.caption_file`. |
| `deepgram_streaming` | Live | `{ "transcription_mode": "sentence", "model": "nova-2", "language": "en", "punctuate": true, "smart_format": true, "endpointing": 300, "vad_events": true, "utterance_end_ms": 1000, "encoding": "linear16", "channels": 1 }` |
| `assemblyai_streaming` | Live | `{ "transcription_mode": "raw", "sample_rate": 48000, "speech_model": "universal-streaming-english", "format_turns": false, "encoding": "pcm_s16le", "vad_threshold": "0.4", "end_of_turn_confidence_threshold": "0.4", "inactivity_timeout": 300, "min_end_of_turn_silence_when_confident": "400", "max_turn_silence": "1280" }` |
| `smallest` | Post-call | `{ "model": "pulse", "language": "en", "diarize": true }` - Smallest AI. `model`: `pulse` (default) or `pulse-pro` (English only). `diarize` only for `pulse` (default true). Optional: `keywords` (string or list), `redact_pii`, `redact_pci`, `emotion_detection`, `gender_detection`. `language` default `"en"`, not checked at create time |
| `smallest_streaming` | Live | `{ "model": "pulse", "language": "en" }` - `model`: `pulse` (default) or `pulse-2` (English only). Works with `live_transcription_required` |

Smallest AI needs one key saved in the dashboard under voice integrations (Smallest AI); it also serves MIA voice. Missing key: 400 `SmallestAPIKey not configured in user profile`. Bad model: 400 `Invalid <key> model: <m>. Allowed values: ...`.

---

## `automatic_leave` Schema - Recommended Defaults

```json
{
  "automatic_leave": {
    "waiting_room_timeout": 600,
    "everyone_left_timeout": 600,
    "voice_inactivity_timeout": 600,
    "in_call_recording_timeout": 14400,
    "recording_permission_denied_timeout": 600
  }
}
```

All values in seconds. Use these defaults unless you have a specific reason to deviate.

- `in_call_recording_timeout`: **14400 (4 hours)** - the canonical default for full-length real meetings. Anything less risks the bot dropping out during long sessions.
- All other timeouts: **600 seconds (10 min)** - prevents premature exit when someone is presenting silently, in the waiting room, or slow to grant Zoom recording permission.
- `recording_permission_denied_timeout` is **Zoom-only**: 60–600 seconds, default **600**.

> **Live-tested constraints (not in OpenAPI):**
> - `in_call_recording_timeout` minimum is **600 seconds** - the API returns `HTTP 400: "in_call_recording_timeout must be at least 600 seconds"` for any value below 600. Verified by live API test.
> - `recording_permission_denied_timeout` accepted range is **60–600 seconds**, default **600** (was 60–300, default 60). Below 60 returns HTTP 400; above 600 returns `HTTP 400: "recording_permission_denied_timeout must not exceed 600 seconds (got N)"`. Use 600 for max patience. A Zoom bot that joins without the user's own Zoom app keeps recording whatever the host answers, so the timeout does not apply to it.

---

## Errors and Rate Limits

**Error body:** most errors are `{"message": "..."}`. So do the bot data endpoints (`get_audio`, `get_video`, `get_speaker_timeline`, `get_chats`, `get_participants`, screenshots), `remove_bot`, `stop_status` and `GET /bots/{bot_id}/transcriptions`. In-meeting commands, the credit check and the 429 below use `error`. Read `message`, then `error`, then the raw body.

**Prepaid rate limit:** prepaid (pay-as-you-go) accounts can create 5 bots per rolling minute and 50 per rolling hour (invoice accounts are not limited). Not counted: `join_at` 10+ minutes ahead, calendar bots for meetings 10+ minutes away, the scheduled join itself, idempotent replays. Over the limit: no bot is created, and

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 37

{"error": "rate_limit_exceeded", "message": "...", "limit": 5, "window": "minute", "retry_after": 37}
```

**Credits:** `create_bot` returns 403 `{"error": "Low credits please recharge", "active_bots": 1}` when credits run out; add credits at https://app.meetstream.ai/billing and do not retry before that. `GET /api/v1/billing/balance` (API v1.10.0, read only) returns the prepaid balance where it is on; "not available" or 404 means it is not on for the account yet, so use the billing page.

`window` is `"minute"` or `"hour"`. Wait `Retry-After` seconds and resend. Concurrent creates with the same `Idempotency-Key` or `deduplication_key` make one bot; a loser may get 409 with `Retry-After: 2` while the first is still saving.

**400s on `create_bot`:** a bot with `audio_required: false` and `video_required: false` and no other job; Google Meet / Teams `video_separate_streams: true` without `video_required: true`; a `bot_image_url` that is not an https:// image URL; a Zoom link with no meeting number (`invalid_meeting_link: ...`); Zoom `meeting_captions` on a bot that uses the user's own Zoom app; bad `zoom.use_own_app`, `storage_id`, `bot_camera_stream` or Smallest `model` values; `recording_permission_denied_timeout` outside 60–600. A `meeting_link` with `http://` is upgraded to `https://`.

**Failure reasons on bots:** `bot_details.ErrorReason` on `/detail` (and `failure_reason` on Google Meet `bot.failed` webhooks). `MeetingRestricted` / `meeting_restricted` (Google Meet, Teams: the meeting admits only the organization or invitees), `SignInRequired` / `sign_in_required` (now also on Teams), `InvalidMeetingLink` (now also on Teams). Reference: https://docs.meetstream.ai/guides/reference/bot-status-and-error-codes

Full error reference: https://docs.meetstream.ai/errors

---

## Live Transcription Webhook Payload

POST'd to `live_transcription_required.webhook_url`. **Live-captured shape** (from a real Google Meet bot with `meetstream_streaming` provider):

```json
{
  "bot_id": "305e708e-d0b5-4081-b982-fb9af84a716b",
  "speakerName": "Sidhdharth Sivasubramanian",
  "timestamp": "2026-05-26T10:21:43.681Z",
  "transcript": "Uh, not in detail",
  "utterance": "",
  "words": [
    {
      "word": "Uh",
      "start": 26.136,
      "end": 26.416,
      "confidence": 0,
      "speaker": "Sidhdharth Sivasubramanian",
      "punctuated_word": "Uh",
      "speech_confidence": 0
    }
  ],
  "is_final": false,
  "end_of_turn": false,
  "turn_is_formatted": false,
  "transcription_mode": "raw",
  "custom_attributes": { "your_keys": "echoed back" }
}
```

**Field reference:**
- `speakerName` - display name of the speaker in the meeting
- `transcript` - current buffer (may be partial / interim)
- `utterance` - empty in `meetstream_streaming`; populated by some providers
- `words[]` - per-word breakdown with `start` / `end` (seconds), `confidence`, `speaker`, `punctuated_word`, `speech_confidence`. **Note: `confidence` and `speech_confidence` are 0 from `meetstream_streaming`** - only Deepgram/AssemblyAI populate these meaningfully.
- `is_final` - top-level boolean: false for interim, true for final committed text. Live-verified.
- `end_of_turn` - true when speaker stops talking; useful for committing UI segments
- `turn_is_formatted` - true after punctuation/formatting pass applied
- `transcription_mode` - observed value `"raw"` from `meetstream_streaming`
- `custom_attributes` - echoed from create_bot payload
- `timestamp` - ISO-8601 of when this chunk was generated

> Note: word objects often carry `word_is_final` (10,604 of 14,020 captured words, Jun 2026), but not every provider sends it. Treat it as optional and use the top-level `is_final` to decide whether a chunk is committed.

---

## WebSocket Control Commands

Provided via `socket_connection_url: { "websocket_url": "wss://..." }` on `create_bot`. The bot **connects to your server as a client** when it joins the meeting.

### Handshake (from bot to you)

```json
{ "type": "ready", "bot_id": "bot_abc123", "message": "Ready to receive messages" }
```

Connection closes with normal code `1000` when the bot leaves.

### `sendaudio` - play audio through bot's mic

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

### `sendmsg` - chat message

**Both `message` AND `msg` must be set to the same value** for cross-platform compatibility.

```json
{
  "command": "sendmsg",
  "bot_id": "bot_abc123",
  "message": "Hello!",
  "msg": "Hello!"
}
```

### `interrupt` - stop playback

```json
{
  "command": "interrupt",
  "bot_id": "bot_abc123",
  "action": "clear_audio_queue"
}
```

**Platform support:** stops playback and clears the queue on every platform. On Zoom and Teams the bot then holds further `sendaudio` until you send `resume_audio`; on Google Meet the next `sendaudio` plays normally.

### `resume_audio` - allow audio again after an interrupt

```json
{
  "command": "resume_audio",
  "bot_id": "bot_abc123",
  "resume_id": "turn-42"
}
```

`resume_id` is any string. Zoom answers `resume_audio_ack` (`success`, `error`). Google Meet ignores it, so send it before the first `sendaudio` of each reply on every platform.

### `sendimg` - set video frame to image (base64)

```json
{
  "command": "sendimg",
  "bot_id": "bot_abc123",
  "img": "<base64-encoded JPEG or PNG>"
}
```

### `sendimg_url` - set video frame to image (URL)

```json
{
  "command": "sendimg_url",
  "bot_id": "bot_abc123",
  "img_url": "https://example.com/bot-avatar.png"
}
```

The URL must be publicly accessible.

> These two set the **bot's camera feed** to a static image (the bot's video). They are different from `POST /bots/{bot_id}/send_image` which posts to the meeting chat.

Docs: https://docs.meetstream.ai/guides/websockets/meeting-control-patterns

---

## Live Audio Binary Frame Format

Provided via `live_audio_required: { "websocket_url": "wss://..." }`. Bot connects to your WSS, sends a JSON `{type: "ready", bot_id, message}` handshake, then streams **binary frames**:

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

Connection closes with code `1000` when bot leaves.

Decoder implementations in Python / Node.js / Go / Java: https://docs.meetstream.ai/guides/websockets/real-time-audio-streaming

---

## Live Video Streaming (fMP4 over WebSocket)

Provided via `live_video_required: { "websocket_url": "wss://..." }`. Supported on **Google Meet and Microsoft Teams only - NOT Zoom**.

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

Docs: https://docs.meetstream.ai/guides/websockets/bridge-server-architecture
