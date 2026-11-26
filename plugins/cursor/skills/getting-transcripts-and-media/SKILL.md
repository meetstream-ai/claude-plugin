---
name: getting-transcripts-and-media
description: >
  Get everything out of a finished MeetStream meeting: the transcript (post-call
  providers, get_transcript, 202 pending, 422 final, re-run with transcribe),
  languages and translation, recordings (get_audio, get_video), per-participant
  audio and video, participants, speaker timeline (format=unified), chat log,
  screenshots, pause and resume, retention and deletion. Use when the user says
  "get the transcript", "transcript never arrives", "re-transcribe", "which
  transcription provider", "Hindi transcript", "download the recording", "get the
  audio", "per-participant audio", "separate speaker tracks", "who spoke when",
  "speaker timeline", "chat log", "screenshots", "pause recording", "how long are
  recordings kept", "delete the recording", "store recordings in my own S3
  bucket", "storage_id", or "grid_view_default". Formerly recordings-and-media
  (and the transcript parts of meeting-brief).
---

# Transcripts and media after the meeting

Everything is keyed on the `bot_id`. Artifacts are ready only after their webhook
(`transcription.processed`, `audio.processed`, `video.processed`, then `bot.done`); presigned
links last 1 hour, so fetch fresh ones and never store them. Hard rules: the `meetstream` router.

## Transcripts

1. Pick the provider **at creation** under `recording_config.transcript.provider` (the only place
   read; an old top-level `transcription` field is ignored). Post-call: `meetstream` (no provider
   key) or your own key saved in the dashboard (Integrations > Transcription) for `deepgram`,
   `assemblyai`, `jigsawstack` (Interfaze), `sarvam`, `smallest`. `meeting_captions` uses the
   platform's captions (Google Meet, Teams; on Zoom only for the no-app join). A missing key gives
   400 on `create_bot`.
2. Wait for `transcription.processed` (or `transcription.failed`). `transcript_id` is not in the
   webhook: take it from the `create_bot` response or `GET /bots/{bot_id}/detail`.
3. Fetch: `GET /api/v1/transcript/{transcript_id}/get_transcript`, or
   `GET /api/v1/bots/{bot_id}/get_transcript` (the first transcript of the bot, no id lookup).
   `raw=true` adds word timings. The MCP `get_transcript` tool takes the `bot_id`.
   - 200: a top-level array, participant-keyed by default: speaker `participant.name`, text
     `words[].text` joined. Some providers return `speaker` / `transcript` segments; read both.
   - 202: still processing; poll with a cap. A streaming-only provider never makes a post-call
     transcript, so it stays 202: stop on `bot.done`.
   - 422: the run failed (`transcript_status: "Failed"` and the reason). Final: do not retry.
4. Re-run on a finished recording: `POST /api/v1/bots/{bot_id}/transcribe` with exactly one
   `provider` object (no server default: 400 without one). Each run gets a new `transcript_id` and
   one `transcription.processed` or `.failed` (no `bot.done`, no `custom_attributes`).
   `meetstream` runs once per bot. List runs with `GET /api/v1/bots/{bot_id}/transcriptions`
   (provider, status, download links). MCP: `transcribe_audio`, `list_transcriptions`.

| Provider | Guide |
|---|---|
| Overview and keys | https://docs.meetstream.ai/guides/transcription-recordings/providers/transcription-providers |
| Deepgram (`deepgram`, live `deepgram_streaming`) | https://docs.meetstream.ai/guides/transcription-recordings/providers/deepgram and https://docs.meetstream.ai/guides/transcription-recordings/providers/deepgram-streaming |
| AssemblyAI (`assemblyai`, live `assemblyai_streaming`) | https://docs.meetstream.ai/guides/transcription-recordings/providers/assemblyai and https://docs.meetstream.ai/guides/transcription-recordings/providers/assemblyai-streaming |
| Interfaze, formerly JigsawStack (`jigsawstack`) | https://docs.meetstream.ai/guides/transcription-recordings/providers/jigsawstack |
| Sarvam (`sarvam`, Indic languages) | https://docs.meetstream.ai/guides/transcription-recordings/providers/sarvam |
| Smallest AI (`smallest`) | https://docs.meetstream.ai/guides/transcription-recordings/providers/smallest |
| Platform captions (`meeting_captions`) | https://docs.meetstream.ai/guides/transcription-recordings/providers/meeting-captions |

**Languages and translation** are per provider: Deepgram `language` (detects when unset),
AssemblyAI `language_code` (default `en_us`), Sarvam `language_code` (default `en-IN`;
`"mode": "translate"` for English output), `meetstream` and Interfaze `language` (default
`auto`; `"translate": true`), Smallest `language` (default `en`). Each provider has its own code
format (`en`, `en_us`, `en-IN`). For meetings that switch language, use an auto-detect provider.
Guides: https://docs.meetstream.ai/guides/transcription-recordings/post-call-transcription and
https://docs.meetstream.ai/guides/transcription-recordings/languages-and-translation

## Participants, speaker timeline, chat, screenshots

- `GET /api/v1/bots/{bot_id}/get_participants`: a top-level array (`deviceId`, `displayName` /
  `fullName`, `status`, `streamIds`, sometimes `isHost`). `deviceId` is the stable id; names
  collide. After processing, `calendar_email` is added from a connected calendar invite
  (`scheduling-and-calendars`). 404 means the bot never got in or the file is not uploaded yet.
- `GET /api/v1/bots/{bot_id}/get_speaker_timeline`: after the bot leaves (404 until then). Each
  platform has its own shape (Google Meet `chunks` of audio bytes, Zoom `sessions`, Teams short
  slices); add `?format=unified` for one shape on every platform (`format`, `platform`, `chunks`
  with `speakerName`, `startTime`, `endTime`). A large timeline returns `speaker_timeline_url`
  instead: download it (no key, valid 1 hour).
- `GET /api/v1/bots/{bot_id}/get_chats`: after the bot leaves (202 until then); messages are in
  `chatMessages` with the sender in `speakerName`. Live chat events: `handling-webhooks`.
- `GET /api/v1/bots/{bot_id}/screenshots` (newest first, 1-hour URLs; filters `recorded_at_after`,
  `recorded_at_before`, `limit`) and `GET /api/v1/bots/{bot_id}/screenshots/{id}`. Take one with
  `send_command` `{"command": "screenshot"}` (`sending-bots`) or the MCP `take_screenshot` tool.

Guides: https://docs.meetstream.ai/guides/features/participants-and-speaker-timeline and
https://docs.meetstream.ai/guides/transcription-recordings/unified-speaker-timeline

## Recordings

**`get_media_urls`** (MCP tool) returns presigned URLs for audio, video,
per-participant streams and screenshots. That is the one call for most needs.
From a terminal, the `meetstream` CLI does the same: `meetstream recordings <bot-id> --json
--no-input` (`{bot_id, audio, video, streams?, audio_streams?}`) and `meetstream bots get
<bot-id> --part audio-streams|screenshots --json --no-input` (run it with
`npx -y @meetstream/cli` if it is not installed; sign in with `meetstream login`).

REST: `GET /api/v1/bots/{bot_id}/get_audio` (mixed audio) and `GET /api/v1/bots/{bot_id}/get_video`
(full meeting video, when `video_required` was true) each return a download URL.

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
speech goes to one speaker. On Zoom, per-participant camera video needs the customer's own Zoom
app (recommended; OBF or ZAK, `setting-up-platforms`): the limited no-app fallback gives none. WhatsApp calls (Beta) have no
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

Omit it and media is kept permanently, until you delete it. For anything containing
customer conversations, set an explicit timed window.

## Deleting

**`delete_bot_data`** (MCP tool) permanently erases a bot's audio, video and
transcripts and fires a `data_deletion` webhook. It is irreversible. Always confirm
with the user first, and never call it to "clean up" without being asked.

`remove_bot` is different: it makes the bot leave the meeting and **keeps** the data.

More detail (response shapes, the post-call strategy, data after the meeting, deletion):
[`references/transcripts-and-data.md`](references/transcripts-and-data.md).

## Bring your own bucket

MeetStream can write media straight into your own bucket (Amazon S3, Alibaba Cloud OSS or
Cloudflare R2) instead of its storage. Storage destinations are set up **in the dashboard
only** (Configure > Storage); there is no public API for them, and customer API keys cannot
call the admin routes. Each destination gets an ID; pass it as `storage_id` on `create_bot`.

`create_bot` checks `storage_id`: 1-80 letters, numbers, `_` or `-`; an active destination
in your own account; and a live test write with the saved credentials (bad credentials:
400; the storage service down: 503).

Two things to tell the user before they set it up:

- This **stores cloud credentials on your MeetStream account**. Use a dedicated IAM user
  scoped to that one bucket, never a root or broad-permission key.
- With write-only access, MeetStream writes to your bucket but its own fetch endpoints
  return 403 for that media - you read it from your bucket, not from the API.

Docs: https://docs.meetstream.ai/guides/features/custom-storage-configurations/overview

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
