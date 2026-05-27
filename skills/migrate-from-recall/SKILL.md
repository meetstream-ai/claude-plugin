---
name: migrate-from-recall
description: >
  Migrate a codebase from Recall.ai to MeetStream — scans for Recall API calls,
  maps every endpoint/field to its MeetStream equivalent, rewrites the code,
  and produces a diff plus a manual-review checklist. Use when the user says
  "migrate from recall", "switch from recall.ai to meetstream", "recall to
  meetstream", "replace recall", "cheaper alternative to recall", or has
  recall-sdk / recall-ai imports in their codebase. Migration typically cuts
  per-meeting cost ~30%.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Migrate from Recall.ai → MeetStream

Scan the user's codebase for Recall.ai API usage and rewrite it to use MeetStream. Surface anything that needs manual review (semantics that differ).

## Why migrate

| | Recall.ai | MeetStream |
|---|---|---|
| Per-meeting cost | $0.50/hr | $0.35/hr ($0.25 at volume) |
| Per-participant audio | ✅ | ✅ (Google Meet + Zoom; not Teams) |
| Per-participant video | ✅ | ✅ (all 3 platforms) |
| Live transcription | ✅ | ✅ (5 streaming providers including free in-house) |
| In-house transcription | ❌ | ✅ `meetstream_streaming` is free, no external key |
| MIA (AI agents in meeting) | partial | ✅ pipeline + realtime modes |

## What this skill does

1. **Scan** the codebase for Recall.ai imports, fetches, and config strings
2. **Map** each call to its MeetStream equivalent (using the table below)
3. **Rewrite** files via Edit (one change at a time, easy to review)
4. **Produce a migration report** listing what was auto-translated and what needs human review

## Step 1: Discovery — find all Recall.ai usage

Run these in parallel:

```bash
# JS/TS
grep -rn "recall-ai\|recallai\|api\\.recall\\.ai\|recall\\.ai" --include="*.ts" --include="*.js" --include="*.tsx" --include="*.jsx" .

# Python
grep -rn "recall_ai\|recallai\|api\\.recall\\.ai\|recall\\.ai" --include="*.py" .

# Config / env
grep -rn "RECALL_API_KEY\|RECALL_API_TOKEN" --include="*.env*" --include="*.yaml" --include="*.yml" --include="*.json" .
```

Save the list. If empty, tell user "No Recall.ai usage detected; nothing to migrate" and exit.

## Step 2: Endpoint + field mapping table (use for each rewrite)

### Auth
| Recall | MeetStream |
|---|---|
| `Authorization: Token <RECALL_TOKEN>` | `Authorization: Token <MEETSTREAM_API_KEY>` |
| `api.recall.ai` | `api.meetstream.ai` |
| Path prefix `/api/v1/` | Same: `/api/v1/` |

### Create bot
| Recall | MeetStream | Notes |
|---|---|---|
| `POST /api/v1/bot/` | `POST /api/v1/bots/create_bot` | path differs |
| `meeting_url` | `meeting_link` | renamed |
| `bot_name` | `bot_name` | same |
| `recording_mode` (`speaker_view`, etc.) | `video_required` (bool) | semantics differ — see "Manual review" below |
| `transcription_options.provider` | `recording_config.transcript.provider` | nested differently |
| Provider names: `deepgram`, `assembly_ai`, `meeting_captions` | `deepgram`, `assemblyai`, `meeting_captions` | `assembly_ai` → `assemblyai` (no underscore) |
| `real_time_transcription.destination_url` | `live_transcription_required.webhook_url` | renamed |
| `automatic_leave.waiting_room_timeout` | same | same field name and semantics |
| `automatic_leave.noone_joined_timeout` | `automatic_leave.no_one_joined_timeout` (calendar only) OR none on create_bot | underscore in MS |
| `metadata` | `custom_attributes` | renamed |
| `webhook_url` (top level) | `callback_url` | renamed |

### Fetch transcript
| Recall | MeetStream |
|---|---|
| `GET /api/v1/bot/{id}/transcript/` | Stateless 2-call flow: `GET /bots/{id}/detail` → read `bot_details.transcript_id` → `GET /transcript/{tid}/get_transcript` |
| Response: array of utterances with `words`, `speaker` | Same shape (top-level array) but per-segment text field is `transcript` not `text` |

### Webhook events
| Recall event | MeetStream event |
|---|---|
| `bot.joining_call` | `bot.joining` |
| `bot.in_waiting_room` | (no direct equivalent; check `bot_details.StatusTimeline.WaitingRoom`) |
| `bot.in_call_not_recording` | `bot.inmeeting` |
| `bot.in_call_recording` | `bot.recording` |
| `bot.recording_permission_allowed` | (no equivalent — recording permission is implicit) |
| `bot.recording_permission_denied` | `bot.stopped` with `bot_status: "Denied"` |
| `bot.call_ended` | `bot.leaving` then `bot.stopped` with `bot_status: "Stopped"` |
| `bot.done` | `bot.done` (same name, only fires for post-call providers — Path A) |
| `bot.fatal` | `bot.stopped` with `bot_status: "Error"` |
| `transcript.done` | `transcription.processed` |
| `transcript.failed` | `transcription.failed` (with `status_code: 500`) |
| `participant_events.join` / `.leave` | Same names; nested under `data.bot.id` |

### Remove bot
| Recall | MeetStream |
|---|---|
| `POST /api/v1/bot/{id}/leave_call/` | `GET /api/v1/bots/{id}/remove_bot` (GET, not POST) |

### Get audio/video URLs
| Recall | MeetStream |
|---|---|
| `GET /bot/{id}` → `recordings[]` | `GET /bots/{id}/get_audio` and `GET /bots/{id}/get_video` (separate calls) |
| Pre-signed URLs valid ~6 hours | MeetStream: `get_audio` valid 1 hour, `get_video` valid 10 min |

### Per-participant streams
| Recall | MeetStream |
|---|---|
| `recording_mode: "audio_only_speaker_view"` etc. | `audio_separate_streams: true` / `video_separate_streams: true` |
| Fetched via recording sub-resources | `GET /bots/{id}/get_audio_streams` / `get_recording_streams` |
| Per-segment URLs valid ~6h | MeetStream: 10 minutes |

### Scheduling
| Recall | MeetStream |
|---|---|
| `POST /api/v1/calendar/` | `POST /api/v1/calendar/create_calendar` |
| Body: `oauth_client_id`, `oauth_client_secret`, `oauth_refresh_token` | `google_client_id`, `google_client_secret`, `google_refresh_token` (`google_` prefix) |

## Step 3: Auto-rewrite

For each file in the discovery list, apply the mappings above using `Edit`. Show diffs as you go.

Common rewrites:

**Python (requests):**
```python
# Before (Recall):
resp = requests.post("https://api.recall.ai/api/v1/bot/", headers={
    "Authorization": f"Token {RECALL_TOKEN}",
}, json={
    "meeting_url": link,
    "bot_name": "My Bot",
    "recording_mode": "speaker_view",
    "transcription_options": {"provider": "deepgram"},
    "metadata": {"deal_id": "123"},
})

# After (MeetStream):
resp = requests.post("https://api.meetstream.ai/api/v1/bots/create_bot", headers={
    "Authorization": f"Token {MEETSTREAM_API_KEY}",
}, json={
    "meeting_link": link,
    "bot_name": "My Bot",
    "video_required": True,  # speaker_view → video on (or False for audio-only)
    "recording_config": {
        "transcript": {"provider": {"deepgram": {"model": "nova-3", "language": "en"}}},
    },
    "custom_attributes": {"deal_id": "123"},
    "automatic_leave": {
        "waiting_room_timeout": 600,
        "everyone_left_timeout": 600,
        "voice_inactivity_timeout": 600,
        "in_call_recording_timeout": 14400,
        "recording_permission_denied_timeout": 300,
    },
})
```

**Node/TS (axios):**
```typescript
// Before (Recall):
await axios.post('https://api.recall.ai/api/v1/bot/', {
  meeting_url: link,
  bot_name: 'My Bot',
  recording_mode: 'speaker_view',
  transcription_options: { provider: 'assembly_ai' },
}, { headers: { Authorization: `Token ${process.env.RECALL_TOKEN}` } })

// After (MeetStream):
await axios.post('https://api.meetstream.ai/api/v1/bots/create_bot', {
  meeting_link: link,
  bot_name: 'My Bot',
  video_required: true,
  recording_config: {
    transcript: {
      provider: {
        assemblyai: {
          speech_models: ['universal-2'],
          language_code: 'en_us',
          speaker_labels: true,
          punctuate: true,
          format_text: true,
          filter_profanity: false,
          redact_pii: false,
          auto_chapters: false,
          entity_detection: false,
        },
      },
    },
  },
  automatic_leave: {
    waiting_room_timeout: 600,
    everyone_left_timeout: 600,
    voice_inactivity_timeout: 600,
    in_call_recording_timeout: 14400,
    recording_permission_denied_timeout: 300,
  },
}, { headers: { Authorization: `Token ${process.env.MEETSTREAM_API_KEY}` } })
```

**Webhook handler:**
```python
# Before (Recall events):
if event == "transcript.done": ...
elif event == "bot.fatal": ...

# After (MeetStream events):
if event == "transcription.processed": ...
elif event == "transcription.failed": ...   # NEW: explicit failure event
elif event == "bot.stopped" and bot_status == "Error": ...
elif event == "bot.done" and status_code == 500: ...   # NEW: terminal error
```

**Transcript iteration (subtle gotcha):**
```python
# Before (Recall — same array shape, different field):
for utterance in transcript:
    print(f"{utterance['speaker']}: {utterance['text']}")  # 'text' field

# After (MeetStream):
for segment in transcript:
    print(f"{segment['speaker']}: {segment['transcript']}")  # 'transcript' field
```

## Step 4: Manual review checklist

Emit at the end. These need a human eye:

```
🔍 Manual review required:

[ ] recording_mode → video_required mapping
    Recall's `speaker_view`, `gallery_view`, `audio_only` all collapse to a
    boolean here. Decide whether you want video on/off.

[ ] Transcript per-segment field rename: text → transcript
    Auto-grep any iteration over the transcript array and update field access.

[ ] Webhook URL split:
    Recall used `webhook_url` (top-level) for lifecycle AND
    `real_time_transcription.destination_url` for live chunks.
    MeetStream uses `callback_url` (lifecycle) AND `live_transcription_required.webhook_url`
    (live chunks). Make sure both are wired to the right handlers in your server.

[ ] Pre-signed URL TTL differences:
    Recall's URLs were valid hours; MeetStream's are 10 min (video) or 1 hr (audio).
    If you stored URLs and reused them later, refactor to re-fetch on demand.

[ ] New event types to handle:
    - bot.recording (recording started — separate from bot.inmeeting)
    - bot.leaving (in-progress exit, before bot.stopped)
    - bot.error (streaming provider upstream error, non-fatal)
    - manifest.completed (platform manifest upload)
    - bot.done (true terminal event for post-call providers)

[ ] If using streaming-only providers, NOTE:
    transcription.processed / .failed / bot.done WILL NOT fire.
    Lifecycle ends at audio.processed. If your old Recall code waited for
    transcript.done, you'll need to either:
      a) Switch to a post-call provider on create_bot, OR
      b) Call POST /bots/{bot_id}/transcribe after bot.stopped (recommended)

[ ] custom_attributes value type:
    All values must be strings (live-tested). Stringify defensively:
      "custom_attributes": {k: str(v) for k, v in metadata.items()}

[ ] Update env var:
    RECALL_API_KEY / RECALL_TOKEN → MEETSTREAM_API_KEY
    Audit deployment configs, secret managers, .env files.
```

## Step 5: Test the migration

Suggest running `verify-account` against the new MEETSTREAM_API_KEY, then `test-bot` against a real meeting to confirm parity. Don't ship until both pass.

## What this skill won't do automatically

- Calendar integration code (different shape; needs walkthrough)
- Real-time WebSocket protocols (binary frame format differs; surface the change but don't auto-rewrite)
- Database schema if the user persisted Recall-shaped event payloads (different field set in MS)

For those, point at the relevant code patterns in the main `meetstream` skill.
