---
name: recordings-and-media
description: >
  Get media out of a MeetStream meeting - audio, video, per-participant
  streams, screenshots - and control recording and retention. Use when the
  user says "download the recording", "get the audio", "per-participant
  audio", "separate speaker tracks", "screenshots", "pause recording",
  "how long are recordings kept", "delete the recording", "store
  recordings in my own S3 bucket", "storage_id", or "grid_view_default".
---

# Recordings and media

## Getting files

**`get_media_urls`** (MCP tool) returns presigned URLs for audio, video,
per-participant streams and screenshots. That is the one call for most needs.
From a terminal, the `meetstream` CLI does the same: `meetstream recordings <bot-id> --json
--no-input` (`{bot_id, audio, video, streams?, audio_streams?}`) and `meetstream bots get
<bot-id> --part audio-streams|screenshots --json --no-input` (run it with
`npx -y @meetstream/cli` if it is not installed; sign in with `meetstream login`).

Media is only ready after the matching webhook fires: `audio.processed` for audio,
`video.processed` for video. Asking earlier returns "not ready" - wait, do not retry
in a tight loop.

## Per-participant streams

Separate tracks per speaker are far more useful than a mixed recording for diarization,
per-speaker analysis, or re-mixing. Ask for them **at bot creation**:

| | MCP `create_bot` tool | REST `create_bot` body |
|---|---|---|
| One audio track per participant | `separate_audio_streams: true` | `audio_separate_streams: true` |
| One video track per participant | `separate_video_streams: true` | `video_separate_streams: true` |

The names differ between the two surfaces; use the one that matches how you are calling.

**Per-participant video is opt-in only.** Never set `video_separate_streams` /
`separate_video_streams` unless the user explicitly asked for per-participant or
per-speaker video; it multiplies storage and processing per participant. Per-participant
audio is unaffected by that rule and stays a good default suggestion.

You cannot add this after the fact; the bot has to be told before it records.

Per-participant audio works on Zoom, Google Meet and Microsoft Teams (up to 16 speakers,
WebM/Opus files). On Teams the bot separates speakers from one mixed track, so overlapping
speech goes to one speaker. Zoom bots join through your Zoom app with an OBF or ZAK token;
set that up before the first Zoom bot (`platform-setup`). WhatsApp calls (Beta) have no
per-participant files. Recording audio only for your own transcription: send
`"video_required": false`, then fetch the files after `audio.processed`.

`GET /bots/{bot_id}/get_audio_streams` (REST) returns a **flat top-level array**, one item
per audio segment. The speaker is `participant.name`; the file is `download_url`:

```json
[
  {
    "id": "<bot_id>-<stream_id>-0",
    "created_at": "2026-11-19T14:30:05Z",
    "is_bot": false,
    "participant": { "id": 123456, "name": "Priya Shah", "is_host": true, "is_bot": false, "platform": "desktop", "extra_data": {} },
    "start_timestamp": { "absolute": "2026-11-19T14:30:05Z", "relative": 4.2 },
    "duration": 125.5,
    "download_url": "https://...",
    "download_url_mp3": "https://..."
  }
]
```

A participant can have several segments: group them by `participant.id` and order them by
`start_timestamp.relative`. `download_url_mp3` is present only when an MP3 copy exists.
URLs are valid for 1 hour. `GET /bots/{bot_id}/get_recording_streams` (per-participant video)
has the same item shape plus `"type": "webcam" | "screenshare"`. Both return 202 while the
bot is in the meeting and `[]` when nothing was recorded per participant.

These endpoints return **HTTP 202 while the bot is still in the meeting**. That is
"not finished yet", not an error. Poll with a cap.

## Video

**Video is off by default.** Only turn it on when the user explicitly asks to record
video. Audio only is faster to process and smaller to store, and transcripts, summaries,
diarization and speaker timelines all work without it.

The surfaces differ. The MCP `create_bot` tool records **audio only** unless you pass
`record_video: true`. The REST API's `video_required` also **defaults to `false`**; send
`"video_required": false` explicitly anyway so the request states the intent.
`audio_required` (default `true`) records the mixed audio; `audio_required: false` with
`video_required: false` and nothing else to do (no live stream, `realtime_endpoints`,
`socket_connection_url`, `bot_message` or `agent_config_id`) returns 400.

### Layout: send `speaker_view` when video is on

| | MCP `create_bot` tool | REST `create_bot` body |
|---|---|---|
| Layout | `video_layout: "speaker_view"` | `recording_config: { "video_layout": "speaker_view" }` |

- `"speaker_view"` and `"grid_view"` work on Google Meet, Teams and Zoom. Google Meet
  and Teams also accept `"speaker_view_default"` and `"grid_view_default"`: the bot
  records the platform's own speaker or grid view in the call as one finished file
  (Teams `grid_view_default` shows at most 9 tiles). Zoom returns 400 for the `_default`
  values. Any other value returns 400 `invalid video_layout value. Allowed values: ...`.
- **The REST API defaults to `"grid_view"`**, so `"speaker_view"` has to be sent
  explicitly. Only use `"grid_view"` when the user asks for grid or gallery view, and a
  `_default` value only when they ask for the platform's own layout.
- Ignored when video is off: an audio-only bot never runs the compositor.
- WhatsApp accepts only `"grid_view"`, and any other platform rejects the field.
- Speaker view follows the active speaker, which is what people want for review and
  clipping. Grid view is a composited mosaic of everyone. Google Meet speaker view
  recordings are 1600x900; do not hard-code 1280x720.
- On Google Meet and Teams, `video_separate_streams: true` needs `video_required: true`,
  otherwise `create_bot` returns 400.

## Pausing mid-meeting

```
POST /api/v1/bots/{bot_id}/pause_recording     (empty body)
POST /api/v1/bots/{bot_id}/resume_recording    (empty body)
```

With the MCP connected, the `pause_recording` / `resume_recording` tools do the same. Use these for privacy windows - a break, an off-record
discussion, someone reading out a credential. The bot stays in the meeting.

## Retention

Set on `create_bot`: `retention_hours` on the MCP tool, or on the REST body:

```json
"recording_config": { "retention": { "type": "timed", "hours": 72 } }
```

Omit it and media is kept for the default 30 days (720 hours). For anything containing
customer conversations, set an explicit, shorter window.

## Deleting

**`delete_bot_data`** (MCP tool) permanently erases a bot's audio, video and
transcripts and fires a `data_deletion` webhook. It is irreversible. Always confirm
with the user first, and never call it to "clean up" without being asked.

`remove_bot` is different: it makes the bot leave the meeting and **keeps** the data.

## Bring your own bucket

MeetStream can write media straight into your own S3 (or S3-compatible) bucket instead
of its storage:

```
PUT    /api/v1/admin/configs?config_type=storage
GET    /api/v1/admin/configs
DELETE /api/v1/admin/configs?key_name=aws
```

The body needs `provider`, `bucket_name`, `region`, `access_key_id`, `secret_key`, plus
optional `access_mode`, `prefix`/`prefixes` and `endpoint_url` (for R2/MinIO).

Two things to tell the user before they run it:

- This **stores cloud credentials on your MeetStream account**. Use a dedicated IAM user
  scoped to that one bucket, never a root or broad-permission key.
- With `access_mode: write_only`, MeetStream writes to your bucket but its own fetch
  endpoints return 403 for that media - you read it from your bucket, not from the API.

Objects land under `{prefix}/{bot_id}_<file>`.

### Picking a destination per bot: `storage_id`

A workspace can save up to 10 storage destinations in the dashboard. Pick one per bot with
`storage_id` on the REST `create_bot` body:

```json
{ "meeting_link": "...", "bot_name": "Recorder", "storage_id": "eu-archive" }
```

- 1-80 letters, numbers, underscores or hyphens, else 400
  `storage_id must contain 1-80 letters, numbers, underscores or hyphens`.
- Omitted: the workspace default destination, or MeetStream storage when none is set.
- Unknown ID, another workspace's ID, or a destination that fails validation: 400 with
  the storage error text (503 when validation is temporarily unavailable).
- Scheduled bots recheck the destination at join time and end `Error` /
  `StorageValidationFailed` if it no longer passes.

## Latest docs

- Retrieve recordings: https://docs.meetstream.ai/guides/transcription-recordings/retrieve-recordings
- Per-participant audio: https://docs.meetstream.ai/guides/transcription-recordings/per-participant-audio
- Per-participant video: https://docs.meetstream.ai/guides/transcription-recordings/per-participant-video
- Usage and retention: https://docs.meetstream.ai/guides/features/usage-and-retention
- Custom storage: https://docs.meetstream.ai/guides/features/custom-storage-configurations/overview

For the latest details, fetch the page with `.md` appended, read https://docs.meetstream.ai/llms.txt, or connect the docs MCP server at https://docs.meetstream.ai/_mcp/server.
