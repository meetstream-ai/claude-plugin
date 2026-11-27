# MeetStream API Reference: Bot Endpoints

> Part of [`api-reference.md`](api-reference.md), split so each file stays under 20 KB.

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
- `live_video_required` (object) - not implemented on meeting bots: accepted, ignored, and it moves the bot to the larger video tier. Do not send it. Only Zoom Meeting Direct Connect (RTMS) sessions stream video.
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
  -H "Authorization: Token YOUR_API_KEY"
```

Use for privacy windows (break, off-record discussion). Returns 200 on success.

### POST `/bots/{bot_id}/resume_recording`

Resume a paused recording. Empty body - no parameters. Pairs with `pause_recording` for mid-meeting recording control.

```bash
curl -X POST "https://api.meetstream.ai/api/v1/bots/{bot_id}/resume_recording" \
  -H "Authorization: Token YOUR_API_KEY"
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
