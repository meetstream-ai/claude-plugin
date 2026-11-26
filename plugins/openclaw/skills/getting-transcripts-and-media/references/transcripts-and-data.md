# Transcripts, media and data after the meeting

Moved from the core `meetstream` skill (3.3.1): response shapes, the post-call strategy, providers, data available after the meeting, retention and deletion.

## Contents

- [Response shapes (the calls apps use most)](#response-shapes-the-calls-apps-use-most)
- [Recommended Implementation Strategy](#recommended-implementation-strategy)
- [Transcription Providers](#transcription-providers)
- [Data Available After Meeting](#data-available-after-meeting)
- [Data Retention](#data-retention)

## Response shapes (the calls apps use most)

Field names to read, so code does not guess. REST paths are under
`https://api.meetstream.ai/api/v1`.

- `POST /bots/create_bot` → 201 `{"bot_id", "transcript_id", "meeting_url", "status"}`.
  Keep `bot_id`; every other call takes it.
- `GET /bots/{bot_id}/status` → `{"bot_id", "status", "custom_attributes"}`.
  `GET /bots/{bot_id}/detail` → `{"bot_details": {"Status", "ErrorReason", "TranscriptStatus", "transcript_id", ...}}`.
- `GET /transcript/{transcript_id}/get_transcript` → a top-level array of segments, by
  default participant-keyed:
  `[{"participant": {"id": 100, "name": "Alice", ...}, "words": [{"text": "the words", "start_timestamp": {"relative": 0.5}}], "language_code": "en"}]`.
  Speaker = `participant.name`; text = `words[].text` joined with spaces. Some providers
  return the segment-list format (`speaker`, `transcript`, `start_time`); read both. The MCP
  `get_transcript` tool takes the `bot_id` and returns the same segments.
- `GET /bots?status=<status>&platform=GMeet&from=YYYY-MM-DD&limit=50` → `{"bots": [...], "hasNextPage", "nextCursor"}`.
  `limit` is at most 50 (above it: 400); send `nextCursor` back as `cursor`. Filter by
  `status`, `platform` (`GMeet`, `Zoom`, `Teams`), `from` / `to`, `custom_attr[key]`;
  never page through the whole history. Statuses and polling: `meetstream-cli`.
- `GET /bots/{bot_id}/get_chats` → `{"metadata": {...}, "speakers": [...], "chatMessages": [{"text", "speakerName", "speakerDisplayName", "timestamp", "messageId"}], "messagesBySpeaker": {...}}`.
  Messages are in `chatMessages`; the sender is `speakerName`.
- `GET /bots/{bot_id}/get_participants` → a top-level array:
  `[{"displayName", "fullName", "deviceId", "status", ...}]`.
- `GET /bots/{bot_id}/get_speaker_timeline` → `{"chunks": [{"speakerName", "speakerId", "timestamp", "startByte", "endByte", ...}], ...}`,
  or for a large timeline `{"bot_id", "speaker_timeline_url", "size_bytes", "truncated": false}`:
  download that URL (no API key, valid 1 hour); the file has the inline format.
- `GET /bots/{bot_id}/get_audio_streams` → a flat array, one item per segment:
  `[{"participant": {"id", "name", ...}, "download_url", "download_url_mp3", "start_timestamp": {"absolute", "relative"}, "duration", ...}]`.
  The speaker is `participant.name`. `get_recording_streams` adds `"type": "webcam" | "screenshare"`.
- `GET /bots/{bot_id}/screenshots` → `{"screenshots": [{"id", "recorded_at", "url", "filename", "size_bytes"}]}`.
- `GET /calendar/events` → `{"results": [{"id", "start_time", "end_time", "meeting_platform", "meeting_url", "bots": [...]}], "next", "has_more"}`.
  The event's link is `meeting_url`; send it to `create_bot` as `meeting_link`.

## Recommended Implementation Strategy

Pick the pattern that matches what the user actually needs. The first two are the **primary** workflows; the third is a fallback for specific cases.

### Primary patterns

| Need | What to configure | Lifecycle terminal event | Where the transcript lives |
|---|---|---|---|
| **Post-call transcript** (notetaker, recordings, summaries) - the most common use case | `recording_config.transcript.provider` set to a post-call provider (`deepgram` / `assemblyai` / `sarvam` / `jigsawstack` / `meetstream`) + a `callback_url` for webhooks | `bot.done` (after `transcription.processed`) | `GET /transcript/{tid}/get_transcript` after `transcription.processed` fires - fetched via the canonical `bot_details.transcript_id` flow |
| **Live transcript chunks during the meeting** (AI coaching, live captions, real-time agents) | `live_transcription_required.webhook_url` + a streaming provider in `recording_config.transcript.provider` (`meetstream_streaming` works free on stock accounts; `*_streaming` for external providers) | `bot.done` (after `audio.processed`; no `transcription.processed` ever fires) | Each chunk POSTed to your webhook in real time; nothing is saved server-side for post-call fetch |

**For the standard post-call notetaker workflow (95% of integrations):**
1. `create_bot` with `recording_config.transcript.provider: {deepgram: {...}}` (or assemblyai, etc.) and `callback_url`
2. Wait for the `transcription.processed` webhook
3. `GET /bots/{bot_id}/detail` → read `bot_details.transcript_id`
4. `GET /transcript/{transcript_id}/get_transcript` → top-level array of segments

No `/transcribe` call needed. The bot was configured with a post-call provider up front, so the transcript is generated automatically.

### Backup / fallback pattern (`POST /bots/{bot_id}/transcribe`)

`/transcribe` is **not the primary path** - it's a backup option for these specific cases:

- **You used a streaming-only provider at meeting time** (live transcription) but now want a post-call transcript too. Audio is saved, so you can transcribe on demand.
- **The original post-call provider failed** (e.g. `transcription.failed` because credits ran out). Retry with a different provider that does have credit, without re-running the meeting.
- **You want to re-transcribe with a higher-quality / different-language provider** after the fact.

In all other cases, configure the right provider on `create_bot` up front. `/transcribe` is a recovery tool, not a default.

---

## Transcription Providers

Specified under `recording_config.transcript.provider`. Use **exactly one** provider per bot.

| Provider key | Mode | Notes |
|---|---|---|
| `meetstream` | Post-call | MeetStream's in-house post-call engine. OpenAPI marks `language` and `translate` as required. |
| `deepgram` | Post-call | `nova-3` is the only model enum. Requires Deepgram key in account. `language` defaults to `"en"` (free string per spec). |
| `assemblyai` | Post-call | Speaker diarization, redaction, chapters. Requires AssemblyAI key in account. 9 fields marked required per OpenAPI. |
| `sarvam` | Post-call | Indic languages, e.g. `model: "saaras:v3"`, `language_code: "en-IN"`. Requires Sarvam key. |
| `jigsawstack` | Post-call | Auto language detect, optional translation. Requires Interfaze key. |
| `meeting_captions` | Live, native | **Free** - uses Meet / Teams native captions. No external key needed. `transcript_id` is **null** - fetch captions via `bot_details.caption_file` on `/detail`. |
| `meetstream_streaming` | Live | MeetStream in-house streaming - **works without external keys**. Live-verified. Use this for live transcription on stock accounts. Empty config `{}` accepted. No post-call transcript fetch (returns HTTP 202 forever). |
| `deepgram_streaming` | Live | Real-time. All ~12 fields marked required per OpenAPI. Needs Deepgram key. |
| `assemblyai_streaming` | Live | Real-time English. All ~10 fields marked required per OpenAPI. Needs AssemblyAI key. |
| `jigsawstack_streaming` | Live | Live-verified existence (referenced in API error message); schema not yet documented in OpenAPI. |
| `smallest` | Post-call | Smallest AI Pulse. `model`: `pulse` (default) or `pulse-pro` (English only). `language` default `"en"`. Options: `diarize` (`pulse` only, default true), `keywords`, `redact_pii`, `redact_pci`, `emotion_detection`, `gender_detection`. Also accepted by `POST /bots/{bot_id}/transcribe`. |
| `smallest_streaming` | Live | Smallest AI streaming. `model`: `pulse` (default) or `pulse-2` (English only). Counts as a streaming provider for `live_transcription_required`. |

> **Smallest AI key:** one key, saved in the dashboard under voice integrations (Smallest AI), serves both `smallest` / `smallest_streaming` and MIA voice. Without it `create_bot` returns 400 `SmallestAPIKey not configured in user profile`. A bad `model` returns 400 `Invalid smallest model: ... Allowed values: ...`. An unsupported `language` is not caught at create time; it arrives as `transcription.failed`.

> **Account configuration matters.** Provider keys must be added to your MeetStream account dashboard before use. If a key is missing or invalid, the `transcription.failed` event fires with `status_code: 500` and a `message` describing the upstream auth failure (e.g. `"Deepgram API error: 401"` or `"Unauthorized Connection: Insufficient funds"`). **Test your account's provider configuration before relying on a post-call provider in production.**

> **Required-vs-default:** the OpenAPI marks many sub-fields as `required` even when they have natural defaults. Pass full provider configs when in doubt - see `skills/meetstream/references/api-reference.md` for the full schema of each provider.

---

## Data Available After Meeting

After the relevant `*.processed` event fires:

| Data | Endpoint | Notes |
|---|---|---|
| Transcript (formatted) | `GET /transcript/{transcript_id}/get_transcript` | Response is a top-level array of segments |
| Raw transcript | `GET /transcript/{transcript_id}/get_transcript?raw=true` | Raw provider output |
| List transcripts for a bot | `GET /bots/{bot_id}/transcriptions` | Returns `{bot_id, transcriptions: [{transcript_id, provider, status, created_at, config, download_urls}]}` |
| Trigger a new transcription run | `POST /bots/{bot_id}/transcribe` | Body: `{provider: {<key>: {...}}, callback_url?}` |
| Speaker timeline | `GET /bots/{bot_id}/get_speaker_timeline` | Returns chunks with **byte offsets** into the audio file (not time). **Large timelines (about 5 MB or more) come back as a download link instead:** `{bot_id, speaker_timeline_url, size_bytes, truncated: false}`. The URL is pre-signed (no API key), valid 1 hour, and the file has the same format as the inline body. Always check for `speaker_timeline_url`. 404 `Manifest file not found. It may still be processing.` until the bot leaves |
| In-meeting chat | `GET /bots/{bot_id}/get_chats` | |
| Audio file | `GET /bots/{bot_id}/get_audio` | Pre-signed S3 URL, **valid 1 hour** |
| Video file | `GET /bots/{bot_id}/get_video` | Pre-signed URL, **valid 1 hour** |
| Per-participant audio streams | `GET /bots/{bot_id}/get_audio_streams` | Flat top-level array of items (`participant`, `download_url`, ...); URLs **valid 1 hour**; 202 while the bot is still in the meeting |
| Per-participant recording streams | `GET /bots/{bot_id}/get_recording_streams` | Same flat item shape plus `type` (`webcam` or `screenshare`); URLs **valid 1 hour** |
| Participant list | `GET /bots/{bot_id}/get_participants` | Returns a top-level array of `{deviceId, displayName, fullName, profilePicture, status, humanized_status, streamIds[], lastUpdated, parentDeviceId?}` |
| Session metadata | `GET /bots/{bot_id}/detail` | Returns `bot_details` with (live-verified): BotID, BotImageURL, BotMessage, BotProfile, BotUsername, CreatedAt, Duration, EndTime, LastUpdatedAt, ManifestStatus, MediaS3Bucket, MeetingLink, NativeSTT, OfferingType, Platform, PlatformCreatedAt, PlatformStatusCreatedAt, RequestPayload, StartTime, Status, StatusCreatedAt, **StatusTimeline** (per-stage `{message, status, timestamp}` map), AudioStatus, TranscriptStatus, UserID, caption_file (S3 link for native captions), participant_events, custom_attributes, **and `transcript_id`** (top-level - populated when a post-call provider is set, not enumerated in OpenAPI but returned live). |
| Screenshots | `GET /bots/{bot_id}/screenshots` | `{"screenshots": [{"id", "recorded_at", "url", "filename", "size_bytes"}]}`; one by id: `GET /bots/{bot_id}/screenshots/{id}` |
| Summary | not available | The API has no summary route; summarize the transcript yourself. |

Bot management:
- Status: `GET /bots/{bot_id}/status`
- List bots: `GET /bots` - returns `{bots: [...], hasNextPage: bool, nextCursor: string|null}` (note camelCase pagination keys)
- Remove from active meeting: `POST /bots/{bot_id}/remove_bot` (the GET form behaves the same). Call it when your app exits or gets Ctrl-C.
- Delete data: `DELETE /bots/{bot_id}/delete` → fires `data_deletion` webhook

### Per-participant audio/video - concurrency & platform limits

- **Per-participant audio** captures up to **16 concurrent speaker streams**. Supported on **Google Meet + Zoom only**, NOT Teams. Files: WebM container, Opus codec, 48 kbps, 48 kHz, mono.
- **Per-participant video** captures up to **6 concurrent webcam streams**. Supported on all 3 platforms. Files: WebM container, VP8 codec, 15 FPS, video-only (audio fetched separately).
- Both flags (`audio_separate_streams`, `video_separate_streams`) can be set at the top level of `create_bot` OR nested inside `recording_config`.
- **Never set `video_separate_streams` (at either level) unless the user explicitly asked for per-participant video.** Per-participant audio is unaffected by that rule.

---

## Data Retention

If you omit `retention`, media is **kept permanently** until you delete it (`DELETE /api/v1/bots/{bot_id}/delete`). A timed window deletes it automatically; `hours` defaults to 720 when `type` is `timed`. Override on `create_bot`:

```json
{ "recording_config": { "retention": { "type": "timed", "hours": 168 } } }
```

### ⚠️ `DELETE /bots/{bot_id}/delete` - DESTRUCTIVE

**Do not call this casually.** It **permanently deletes** the recording data for a bot:

- The audio recording (MP3/WAV)
- The video recording (MP4)
- Per-participant audio/video streams
- The transcript
- Any associated S3 objects

**There is no recovery.** Once deleted, no API call (including the transcript endpoint) will return the data - every subsequent fetch will 404.

Live test response confirms scope: `{"message": "Successfully deleted 7 objects for bot ...", "bot_id": "...", "deleted_objects": 7}` - that "7 objects" includes audio, video, transcript, and metadata blobs.

**Rules:**

1. **Never call `/delete` automatically in webhook handlers, agents, or polling loops.** If you wire this into automated code, you will eventually wipe a session you needed.
2. **Never call `/delete` to "clean up" a test bot until you've verified you don't need its outputs.** Use `/delete` only for explicit test bots the user asked to remove.
3. **Prefer retention-based expiry.** Set `recording_config.retention` to the shortest acceptable window for your use case (omitted means kept permanently) and let MeetStream's scheduler clean up.
4. **Confirm with the user before running `/delete` interactively.** Treat it like `rm -rf` - if the user didn't explicitly ask to delete, don't.
5. **The `data_deletion` webhook fires after deletion** - receiving it means data is already gone, not "about to be deleted."

```python
# DESTRUCTIVE - only with explicit confirmation
def delete_bot_data(bot_id: str, confirmed: bool = False) -> dict:
    """Deletes audio, video, transcript permanently. Requires confirmed=True."""
    if not confirmed:
        raise ValueError("Refusing destructive delete without explicit confirmed=True flag")
    resp = requests.delete(f"{BASE_URL}/bots/{bot_id}/delete", headers=HEADERS)
    resp.raise_for_status()
    return resp.json()  # {message, bot_id, deleted_objects}
```

---
