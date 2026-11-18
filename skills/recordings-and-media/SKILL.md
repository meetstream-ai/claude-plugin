---
name: recordings-and-media
description: >
  Get media out of a MeetStream meeting - audio, video, per-participant
  streams, screenshots - and control recording and retention. Use when the
  user says "download the recording", "get the audio", "per-participant
  audio", "separate speaker tracks", "screenshots", "pause recording",
  "how long are recordings kept", "delete the recording", or "store
  recordings in my own S3 bucket".
---

# Recordings and media

## Getting files

**`get_media_urls`** (MCP tool) returns presigned URLs for audio, video,
per-participant streams and screenshots. That is the one call for most needs.

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

These endpoints return **HTTP 202 while the bot is still in the meeting**. That is
"not finished yet", not an error. Poll with a cap.

## Video

**Video is off by default.** Only turn it on when the user explicitly asks to record
video. Audio only is faster to process and smaller to store, and transcripts, summaries,
diarization and speaker timelines all work without it.

The surfaces differ. The MCP `create_bot` tool records **audio only** unless you pass
`record_video: true`. The REST API's `video_required` **defaults to `true`**, so send
`"video_required": false` explicitly; an omitted field records video.

### Layout: send `speaker_view` when video is on

| | MCP `create_bot` tool | REST `create_bot` body |
|---|---|---|
| Layout | `video_layout: "speaker_view"` | `recording_config: { "video_layout": "speaker_view" }` |

- Values are exactly `"speaker_view"` or `"grid_view"`. Nothing else validates.
- **The REST API defaults to `"grid_view"`**, so `"speaker_view"` has to be sent
  explicitly. Only use `"grid_view"` when the user asks for grid or gallery view.
- Ignored when video is off: an audio-only bot never runs the compositor.
- Google Meet, Teams and Zoom accept both values. WhatsApp accepts only `"grid_view"`,
  and any other platform rejects the field.
- Speaker view follows the active speaker, which is what people want for review and
  clipping. Grid view is a composited mosaic of everyone.

## Pausing mid-meeting

```
POST /api/v1/bots/{bot_id}/pause_recording     (empty body)
POST /api/v1/bots/{bot_id}/resume_recording    (empty body)
```

REST only, not MCP tools. Use these for privacy windows - a break, an off-record
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

## Reference

- [Retrieve recordings](https://docs.meetstream.ai/guides/transcription-recordings/retrieve-recordings)
- [Per-participant audio](https://docs.meetstream.ai/guides/transcription-recordings/per-participant-audio) · [Per-participant video](https://docs.meetstream.ai/guides/transcription-recordings/per-participant-video)
- [Pause and resume recording](https://docs.meetstream.ai/guides/features/pause-resume-recording)
- [Usage and retention](https://docs.meetstream.ai/guides/features/usage-and-retention)
- [Custom storage configurations](https://docs.meetstream.ai/guides/features/custom-storage-configurations/amazon-s3)
