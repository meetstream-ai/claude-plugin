# Bot configuration details

Moved from the core `meetstream` skill (3.3.1): required fields, recording defaults, timeouts, identity, metadata and in-meeting commands.

## Contents

- [Required Fields on `create_bot`](#required-fields-on-create_bot)
- [Recording Defaults - apply to every bot you build](#recording-defaults---apply-to-every-bot-you-build)
- [`automatic_leave` Timeouts - Recommended Defaults](#automatic_leave-timeouts---recommended-defaults)
- [`bot_image_url`](#bot_image_url)
- [`custom_attributes`](#custom_attributes)

## Required Fields on `create_bot`

Per the OpenAPI `CreateBotRequest` schema, only two fields are required:

- `meeting_link` (string) - Zoom, Google Meet, or Teams URL
- `bot_name` (string) - the display name shown in the meeting

`video_required` defaults to **`false`** in the API (an omitted field records audio only). **House policy: still send `video_required` explicitly on every bot** (`false` unless the user asked to record video), so the intent is visible in the request and does not depend on a default. Audio only is faster to process and smaller to store, and transcripts, summaries, diarization and speaker timelines all work without video.

When the user does want video, send `recording_config.video_layout: "speaker_view"` alongside it. The API default layout is `grid_view`, so speaker view only happens if you ask for it.

`audio_required` (bool, default **`true`**) is an optional `CreateBotRequest` field: whether the bot records the mixed meeting audio. Leave it at the default. It must be `true` when `audio_mixed_mp3` is `true`, and it also appears in calendar-scheduled `bot_config` / `default_bot_config`. (`audio_separate_streams` is a different feature that enables per-participant audio tracks.)

> **400 rule:** A bot with `audio_required: false` and `video_required: false` and nothing else to do (no `realtime_endpoints`, live audio/video/transcription stream, `socket_connection_url`, `bot_message` or `agent_config_id`) is rejected with 400 `audio_required and video_required are both false, so the bot would record nothing.`

---

## Recording Defaults - apply to every bot you build

These three rules are product policy, not API behaviour. The API defaults differ, which is exactly why each field has to be sent explicitly.

| Setting | What you send by default | When to change it |
|---|---|---|
| `video_required` | `false`, sent explicitly | Only `true` when the user explicitly asks to record video. The API default is also `false`; send it anyway so the request states the intent. |
| `recording_config.video_layout` | `"speaker_view"` whenever video is on | Only `"grid_view"` when the user explicitly asks for grid or gallery view. The API default is `grid_view`, so speaker view must be sent. |
| `video_separate_streams` | never set it | Only `true` when the user explicitly asks for per-participant (per-speaker) video streams. It multiplies storage and processing per participant. |

Per-participant **audio** (`audio_separate_streams`) is unaffected by this policy. Keep the existing guidance for it.

### `recording_config.video_layout`

- Values on every platform: `"speaker_view"` and `"grid_view"`. Google Meet and Microsoft Teams also accept `"speaker_view_default"` and `"grid_view_default"`: the bot records the platform's own speaker or grid view in the call as one finished file. Zoom accepts only `"speaker_view"` and `"grid_view"`. Any other value returns 400 `invalid video_layout value. Allowed values: ...` listing the values for that platform.
- `"grid_view"` is the API default when `video_required: true`, so send `"speaker_view"` explicitly to get it. Use a `_default` value only when the user asks for the platform's own layout.
- Ignored when `video_required` is `false`. An audio-only bot never runs the compositor.
- WhatsApp accepts only `"grid_view"`. Any other platform rejects `video_layout`.
- Speaker view follows the active speaker, which is what people want for review and clipping. Grid view is a composited mosaic of everyone. Teams `grid_view_default` shows at most 9 tiles.
- Google Meet speaker view recordings are 1600x900. Do not hard-code 1280x720 when you process the video.

Existing per-participant video templates and options stay as they are. They are explicit opt-ins by design.

---

## `automatic_leave` Timeouts - Recommended Defaults

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

All values in seconds. Use these defaults unless you have a specific reason to change them - they prevent the bot from dropping out of long real meetings.

- `waiting_room_timeout` - wait in waiting room before leaving - **600s (10 min)**
- `everyone_left_timeout` - stay after everyone else leaves - **600s (10 min)**
- `voice_inactivity_timeout` - wait if no audio detected (someone could be presenting silently) - **600s (10 min)**
- `in_call_recording_timeout` - max recording duration - **14400s (4 hours)**, the canonical default for full-length meetings
- `recording_permission_denied_timeout` - wait if recording permission denied (**Zoom-only**) - **600s (10 min)** - this is the max the API allows and also the API default (range is 60–600)

> **Live-tested constraints (not in OpenAPI spec):**
> - `in_call_recording_timeout` minimum is **600 seconds** - the live API returns `HTTP 400: "in_call_recording_timeout must be at least 600 seconds"` below that.
> - `recording_permission_denied_timeout` accepted range is **60–600 seconds**, default **600** (the limit was 300 and the default 60 before November 2026). Below 60 returns HTTP 400; above 600 returns `HTTP 400: "recording_permission_denied_timeout must not exceed 600 seconds (got N)"`. Use 600 (the max) for maximum patience.
> - A Zoom bot that joins without the user's own Zoom app records from admission whatever the host answers to the recording prompt, so this timeout does not apply to it.

**Why 14400 for `in_call_recording_timeout` specifically:** real meetings often run longer than 30 minutes. Defaulting to anything less risks the bot disconnecting while people are still talking. 4 hours is the canonical safe value for full-length sales / interview / workshop sessions.

Without these defaults, a stuck bot can sit in a meeting indefinitely.

---

## `bot_image_url`

Custom profile picture must be a **publicly accessible URL** - MeetStream fetches it externally. The image must be reachable without authentication.

```json
{ "bot_image_url": "https://your-server.com/avatar.png" }
```

- Must be `https://` and point to a PNG, JPEG, GIF or WebP image. A URL without one of those extensions is accepted only up to 2048 characters.
- `http://`, `data:` URIs and other unusable values return **400** `bot_image_url must be an https:// URL to a PNG, JPEG, GIF or WebP image; ...`.
- The host must resolve to a public address on every redirect hop. A private, loopback or metadata address is refused when the bot downloads the image (no 400; the bot just has no avatar).

---

## `custom_attributes`

The OpenAPI schema allows `additionalProperties: { description: Any type }`. Arbitrary key-value metadata; values are echoed back in webhook payloads.

> **Observed behavior:** in practice the server has been seen to reject non-string values. The OpenAPI doesn't enforce string-only, but stringifying values defensively is safer:
> ```json
> { "custom_attributes": { "deal_id": "12345", "active": "true", "score": "0.87" } }
> ```

---

### In-Meeting Commands (`send_command`)

`POST /bots/{bot_id}/send_command` runs one command on a live bot. Body: `{"command": "<name>", ...}`.

**Raise / lower hand** (Google Meet, Zoom, Microsoft Teams):

```bash
curl -X POST "https://api.meetstream.ai/api/v1/bots/$BOT_ID/send_command" \
  -H "Authorization: Token $MEETSTREAM_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"command": "raise_hand"}'
```

Response 200:

```json
{ "status": "accepted", "bot_id": "83acdd72-...", "command": "raise_hand", "hand_raised": true }
```

- **The bot must be in the meeting** (`InMeeting` or `Recording`). Joining, in the lobby, or already left: **409**. Wait for `bot.inmeeting` before you send it.
- `hand_raised` is the state the bot read back from the meeting **after** acting, not an echo of the request. Repeating a command is a no-op that returns the current state. The host (and, on Google Meet, the meeting itself once that person speaks) can lower the hand, so send `lower_hand` first if you are not sure of the state.
- `{"command": "lower_hand"}` returns `"hand_raised": false`. No other body fields are used.
- Allow up to 10 seconds for the response. Retry a 5xx once.
- WhatsApp bots and Zoom RTMS sessions return 400 (`unsupported_on_whatsapp` / `unsupported_on_zoom_rtms`). Bots that run outside the US region return 501.
- Guide: https://docs.meetstream.ai/guides/features/raise-lower-hand

**`update_mia` with `wait_for_ack`** (`POST /bots/{bot_id}/update_mia` with this body, or `send_command` with `"command": "update_mia"` added):

```json
{ "agent_config_params": { "customer_name": "Sarah" }, "wait_for_ack": true }
```

- Without `wait_for_ack`, 200 means "accepted for delivery", not "applied".
- With `"wait_for_ack": true`, the response carries the agent's result: `status` is `applied`, `partially_applied`, `failed` (with `errors: [{field, reason}]`) or `accepted` (with `ack_timeout: true` when the agent did not answer in time; the update may still apply). `applied` lists the fields that were applied.
- A non-boolean `wait_for_ack` returns 400 `wait_for_ack must be a boolean (true or false)`.

Other commands on the same endpoint: `screenshot` (Zoom: only on bots that join without your own Zoom app), `pause_recording`, `resume_recording`, and chat (`sendmsg`). On Zoom and Teams, chat is accepted while the bot waits in the lobby and is posted on admission; Google Meet returns 409 in the lobby.

---
