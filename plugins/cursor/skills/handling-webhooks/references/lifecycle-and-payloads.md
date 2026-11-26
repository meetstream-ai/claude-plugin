# Bot lifecycle and webhook payloads

Moved from the core `meetstream` skill (3.3.1): the live-verified lifecycle paths, terminal events, failure reasons and the handler requirements.

## Contents

- [Path A: Post-call provider (`deepgram`, `assemblyai`, `sarvam`, `jigsawstack`, `meetstream`, `smallest`)](#path-a-post-call-provider-deepgram-assemblyai-sarvam-jigsawstack-meetstream-smallest)
- [Path B: Streaming-only provider (`meetstream_streaming`, `assemblyai_streaming`, `deepgram_streaming`, `jigsawstack_streaming`, `smallest_streaming`, `meeting_captions`)](#path-b-streaming-only-provider-meetstream_streaming-assemblyai_streaming-deepgram_streaming-jigsawstack_streaming-smallest_streaming-meeting_captions)
- [Path C: Backup / fallback - `/transcribe`](#path-c-backup--fallback---transcribe)
- [Full event reference](#full-event-reference)
- [Terminal events: `event` vs `bot_event`](#terminal-events-event-vs-bot_event)
- [Failure reasons (`ErrorReason`)](#failure-reasons-errorreason)
- [`status_code` is NOT always 200](#status_code-is-not-always-200)
- [Lifecycle internal states (visible via `bot_details.StatusTimeline`)](#lifecycle-internal-states-visible-via-bot_detailsstatustimeline)
- [Webhook payload shape](#webhook-payload-shape)
- [Event types](#event-types)
- [`bot_status` values](#bot_status-values)
- [`*.failed` events](#failed-events)
- [Webhook signature verification](#webhook-signature-verification)

## Bot Lifecycle - Live-Verified, Two Distinct Paths

**Lifecycle depends on whether you configured a post-call provider or a streaming-only provider.** This is the most important architectural distinction in the entire API - and it's not in the official docs.

### Path A: Post-call provider (`deepgram`, `assemblyai`, `sarvam`, `jigsawstack`, `meetstream`, `smallest`)

```
create_bot (returns transcript_id)
  → bot.joining              (Joining, 200)
  → bot.in_waiting_room      (InWaitingRoom, 200)   ← when the platform holds it in a lobby
  → bot.inmeeting            (InMeeting, 200)
  → bot.recording            (Recording, 200)
  → participant_events.*     (if realtime_endpoints configured)
  → bot.leaving              (Leaving, 200)
  → bot.stopped              (bot_event says why; see "Terminal events" below)
  → audio.processed / manifest.completed   (order varies)
  → transcription.processed  OR  transcription.failed
  → bot.transcriptionready
  → video.processed          (if video_required: true)
  → bot.done                 (Done, 200)            ← final event
  → data_deletion            (200), only after DELETE /bots/{id}/delete or retention expiry
```

### Path B: Streaming-only provider (`meetstream_streaming`, `assemblyai_streaming`, `deepgram_streaming`, `jigsawstack_streaming`, `smallest_streaming`, `meeting_captions`)

```
create_bot (returns transcript_id: null)
  → bot.joining → [bot.in_waiting_room] → bot.inmeeting → bot.recording
  → [live chunks stream to live_transcription_required.webhook_url]
  → bot.leaving
  → bot.stopped
  → manifest.completed, audio.processed
  → bot.done                 ← still fires
```

**Key difference (verified against 4,139 captured webhooks, Jun 2026):** streaming-only bots never receive `transcription.processed` or `transcription.failed`, because no post-call transcript is produced. They **do** receive `bot.done` (50 of 50 streaming bots that recorded). Use `bot.done` as the single "session finished" signal for both paths, and never block on `transcription.processed` for a streaming bot.

### Path C: Backup / fallback - `/transcribe`

> Use Path C only as a recovery / fallback. The primary post-call workflow is Path A (configure the post-call provider on `create_bot` up front). Reach for Path C when:
> - You used a streaming-only provider at meeting time and now want a post-call transcript too
> - The original `create_bot` provider failed (e.g. `transcription.failed`) and you want to retry with a different provider that has credit
> - You want to re-transcribe with a higher-quality / different-language provider

If you used a streaming-only provider at meeting time, **a post-call transcript does NOT exist automatically** - `transcript_id` stays `null`, `/transcriptions` is empty, `bot_details.transcript_id` is `None`. The audio recording IS saved (`AudioStatus: Success`), so you can request transcription whenever you want.

Call `POST /bots/{bot_id}/transcribe` with a post-call provider any time after `bot.stopped`:

```bash
POST /bots/{bot_id}/transcribe
{
  "provider": { "deepgram": { "model": "nova-3", "language": "en" } },
  "callback_url": "https://your-server.com/webhook"
}
```

Live-verified behavior:
- Returns immediately with a new `transcript_id` and starts processing in the background
- **Overwrites `bot_details.transcript_id`** with the new id (canonical fetch always returns the latest run)
- Adds an entry to `GET /bots/{bot_id}/transcriptions` with `status: "Processing"` → `"Success"` or `"Failed"`
- Fires **exactly one** `transcription.processed` or `transcription.failed` event on the `callback_url` you pass (single fire-and-forget - NOT a full lifecycle restart)
- The webhook payload shape is identical to a Path-A bot's transcription event (same `event` name, same `transcript_status`, same `status_code` 200/500)
- **Does NOT fire another `bot.done` after it**: the bot's lifecycle already ended
- **Does NOT include `custom_attributes`** in the payload (unlike original lifecycle events). Correlate by `bot_id` instead.

This is the recommended pattern when you need BOTH live and post-call output, or when your account only has streaming-capable providers configured at bot-creation time but you want to add a paid post-call transcript later.

Notes:
- `bot.joining` may fire up to 3 times if server-side join retries kick in.
- `bot.inmeeting`, `bot.recording`, `bot.leaving`, `bot.stopped`, `bot.done` each fire at most once per bot.
- If the bot never gets in, the sequence is typically `bot.joining` → `bot.in_waiting_room` → `bot.leaving` → `bot.stopped` (`bot_event: "bot.notallowed"`) → `bot.done`, with no `bot.inmeeting` or `bot.recording`.
- **`bot.done` is the final event on every path**, fired after all post-call processing completes (or fails). Use this, not `bot.stopped`, to mark a session fully done.
- **Never fetch the transcript before `transcription.processed` fires.** Always set `callback_url`.

### Full event reference

Every delivery carries `event`, `bot_id` and `timestamp`. Most also carry `bot_event`, which equals `event` except on terminals (see below).

| event | bot_status | status_code | When | Extra payload fields |
|---|---|---|---|---|
| `bot.scheduled` | | 200 | Bot created with a future `join_at` | |
| `bot.joining` | `Joining` | 200 | Bot is connecting | |
| `bot.in_waiting_room` | `InWaitingRoom` | 200 | Held in the lobby / waiting room | |
| `bot.error` | `InMeeting` | omitted | Streaming-provider upstream error during the meeting (e.g. AssemblyAI "Insufficient funds"). Not fatal: the bot keeps recording, only live transcription stops. Seen in May 2026 testing. | `message` (upstream error) |
| `bot.inmeeting` | `InMeeting` | 200 | Bot joined the meeting | |
| `bot.recording` | `Recording` | 200 | Recording started | |
| `participant_events.join` / `.leave` | | | Participants join/leave (requires `recording_config.realtime_endpoints`) | Nested: `data.data.action`, `data.data.participant.{id,name,full_name,platform}`, `data.data.timestamp.{relative,absolute}`, `data.bot.{id,metadata}`. No top-level `bot_id`, `bot_status` or `bot_event`. |
| `participant_events.raise_hand` / `.lower_hand` | | | A participant raised or lowered their hand (Google Meet, Zoom). Sent **only** to `realtime_endpoints` that list the event, never to workspace webhooks | Same nested shape as `participant_events.join`; `data.data.action` is `raise_hand` / `lower_hand` |
| `bot.leaving` | `Leaving` | 200 | Bot is leaving | |
| `bot.stopped` | varies | 200 or 500 | Bot exited or never got in. **Read `bot_event` for the reason** | see "Terminal events" |
| `bot.uploading` | | 200 | Media upload in progress | |
| `manifest.completed` | | 200 | Platform manifest uploaded | `status: "success"`, `manifest_status: "Success"` |
| `audio.processed` | | 200 | Audio ready to fetch | `status: "success"`, `audio_status: "Success"` |
| `transcription.processed` | | 200 | Transcript ready. **Post-call providers only** | `transcript_status: "Success"` |
| `transcription.failed` | | **500** | Transcript failed. **Post-call providers only** | `status: "error"`, `transcript_status: "Failed"`, `message` (error detail) |
| `bot.transcriptionready` | | 200 | Follows `transcription.processed` | |
| `video.processed` | | 200 | Video ready to fetch (`video_required: true`) | `video_status: "Success"` |
| `audio.skipped` / `manifest.skipped` / `transcription.skipped` | | | That stage had nothing to process (e.g. the bot never recorded) | |
| `bot.done` | `Done` | 200 | All post-call processing complete. **Final event on every path** | `message` |
| `data_deletion` | | 200 | Data deleted (manual `/delete` or retention) | `status: "success"`, `deleted_objects: <int>`. No `custom_attributes` |

### Terminal events: `event` vs `bot_event`

Every ending arrives **once**, with `event: "bot.stopped"`. `bot_event` carries the specific reason:

| `bot_event` | `status_code` | `bot_status` | Meaning |
|---|---|---|---|
| `bot.stopped` | 200 | `Stopped` | Normal exit (meeting ended, `remove_bot`, timeout) |
| `bot.kicked` | 200 | `Stopped` | A participant removed the bot |
| `bot.notallowed` | 500 | `NotAllowed` | Never admitted (lobby / waiting-room timeout) |
| `bot.denied` | 500 | `Denied` | Host refused entry or recording permission |
| `bot.failed` | usually 500 | `FAILED` / `ERROR` / `Failed` | The bot crashed or could not run |

Branch on `bot_event`, not `bot_status`: a kick and a clean exit both report `Stopped`, and failure casing varies. Compare `bot_status` case-insensitively if you use it at all.

### Failure reasons (`ErrorReason`)

A `bot.failed` terminal (status `Failed`) carries a specific reason in `bot_details.ErrorReason` on `GET /bots/{bot_id}/detail`. Google Meet `bot.failed` webhooks (and Teams for `sign_in_required`) also carry it as `failure_reason`. Treat unknown values as a generic failure. Reasons that matter most for join failures:

| `ErrorReason` | `failure_reason` | Platform | What happened | What to do |
|---|---|---|---|---|
| `MeetingRestricted` | `meeting_restricted` | Google Meet, Teams | The meeting admits only the host's organization or invited people, so the guest bot cannot ask to join. Message `Failed: Meeting access is restricted` | Use a signed-in bot from an allowed domain/tenant, or ask the organizer to allow the bot |
| `SignInRequired` | `sign_in_required` | Google Meet, Teams (new on Teams) | The meeting does not accept anonymous guests. Message `Failed: Sign in required` | Use a Google or Teams signed-in bot |
| `InvalidMeetingLink` | `invalid_meeting_link` | Google Meet, Teams (new on Teams) | The link is broken, cut off or not a meeting. Message `Failed: Invalid meeting link` | Copy the full join link from the invite |

A Zoom link with no meeting number (for example a `/my/` personal link) is refused earlier: `create_bot` returns 400 `invalid_meeting_link: ...` and no bot is created. Full list of reasons and messages: https://docs.meetstream.ai/guides/reference/bot-status-and-error-codes

### `status_code` is NOT always 200

`transcription.failed` and the failing terminals (`bot.notallowed`, `bot.denied`, most `bot.failed`) carry `status_code: 500`. All 466 captured `bot.done` deliveries were 200. Branch on `event`, then `bot_event`; use `status_code` only as a quick error indicator.

### Lifecycle internal states (visible via `bot_details.StatusTimeline`)

`StatusTimeline` on `/bots/{bot_id}/detail` shows every stage the bot passed through. Per live observation, the full set of stages is:

`Scheduled`, `Joining`, `WaitingRoom`, `InMeeting`, `Recording`, `Leaving`, `Stopped`, `BotNotAllowed`, `BotRejected`, `Error`, `AudioProcessing`, `VideoProcessing`, `TranscriptionReady`, `Done`, `MediaExpired`

Each entry is `{message, status, timestamp}`. `status: true` means that stage was reached; `false` means it wasn't (e.g. `BotRejected.status: false` if the bot wasn't rejected).

---

## Webhook Handler Requirements

- Must use **HTTPS** (use ngrok or cloudflared for local dev - see https://docs.meetstream.ai/guides/webhooks/local-webhook-server)
- Must resolve to a **public address**. Webhooks from post-call processing (`manifest.completed`, `audio.processed`, `transcription.processed` / `.failed`, `video.processed` and the other post-call events) are delivered only to public addresses, on every redirect hop. A `callback_url` or workspace webhook URL that resolves to a private, loopback or metadata address is not delivered. A tunnel (ngrok, cloudflared) gives a public address for local development.
- Every delivery sends `User-Agent: MeetStream-Webhook/1.0`.
- Must respond `2xx` quickly to acknowledge receipt
- **No automatic retries.** If your endpoint returns non-2xx, the webhook is **not** retried. Build your handler to never fail (catch errors, queue work, return 200). Exception: bots in a regional execution cell (outside the US) retry through a queue, up to 6 attempts, so the same event can arrive twice: dedupe.
- `bot.joining` may fire up to 3 times if join retries are configured, and `bot.inmeeting` can repeat. `bot.stopped`, `audio.processed`, `transcription.processed`, `video.processed`, `bot.done`, `data_deletion` are each sent **at most once**.
- Idempotency: dedupe on `{bot_id, bot_event or event, timestamp}`. Every event carries a `timestamp` (verified on all 4,139 captured deliveries, including lifecycle events).

### Webhook payload shape

**Lifecycle events** (`bot.joining`, `bot.in_waiting_room`, `bot.inmeeting`, `bot.recording`, `bot.leaving`, `bot.stopped`, `bot.done`):
```json
{
  "event": "bot.joining",
  "bot_event": "bot.joining",
  "bot_id": "dd451299-1471-49ae-b407-c91541242748",
  "bot_status": "Joining",
  "message": "Bot is joining the meeting",
  "status_code": 200,
  "custom_attributes": { "your_keys": "echoed back" },
  "timestamp": "2026-06-16T06:28:14.445Z"
}
```

**A terminal** (bot never admitted):
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

**Post-call events** (`manifest.completed`, `audio.processed`, `transcription.processed`, `transcription.failed`, `video.processed`, `data_deletion`) may include `status: "success"|"error"`:
```json
{
  "event": "transcription.failed",
  "bot_event": "transcription.failed",
  "bot_id": "...",
  "status": "error",
  "transcript_status": "Failed",
  "message": "Transcript processing error: Deepgram API error: 401",
  "status_code": 500,
  "custom_attributes": {...},
  "timestamp": "2026-05-26T10:11:25.781273+00:00"
}
```

**Verified against 4,139 captured webhook deliveries (Jun 2026):**
- Every event carries `timestamp`.
- `bot_event` is present on everything except `manifest.completed`, `manifest.skipped`, `bot.transcriptionready`, `bot.uploading` and `participant_events.*`. Read it with a fallback: `payload.bot_event ?? payload.event`.
- `status_code` is NOT always 200. `transcription.failed` and failing terminals use 500.
- `participant_events.*` payloads have a different structure: `bot_id` is nested under `data.bot.id`, with no top-level `bot_status`.
- `transcript_id` is never in a webhook payload.

### Event types

See the live-verified table in [Bot Lifecycle](#bot-lifecycle---live-verified-two-distinct-paths).

`bot.scheduled`, `bot.joining`, `bot.in_waiting_room`, `bot.inmeeting`, `bot.recording`, `participant_events.*`, `bot.leaving`, `bot.stopped` (reason in `bot_event`: `bot.stopped` / `bot.kicked` / `bot.notallowed` / `bot.denied` / `bot.failed`), `bot.uploading`, `manifest.completed`, `audio.processed`, `transcription.processed`, `transcription.failed`, `bot.transcriptionready`, `video.processed`, `audio.skipped` / `manifest.skipped` / `transcription.skipped`, `bot.done`, `data_deletion`, and `bot.error` (streaming-provider warning).

### `bot_status` values

| bot_status | Event(s) | Meaning |
|---|---|---|
| `Joining` | `bot.joining` | Bot is connecting |
| `InWaitingRoom` | `bot.in_waiting_room` | Waiting to be admitted |
| `InMeeting` | `bot.inmeeting` | Bot is in the meeting |
| `Recording` | `bot.recording` | Recording active |
| `Leaving` | `bot.leaving` | Bot is leaving in progress |
| `Stopped` | `bot.stopped` (`bot_event` `bot.stopped` or `bot.kicked`) | Normal exit, or removed by a participant. Use `bot_event` to tell them apart |
| `NotAllowed` | `bot.stopped` (`bot_event: bot.notallowed`) | Could not join (waiting-room / lobby timeout) |
| `Denied` | `bot.stopped` (`bot_event: bot.denied`) | Host denied join or recording permission |
| `FAILED` / `ERROR` / `Failed` | `bot.stopped` (`bot_event: bot.failed`) | Unexpected error. Casing varies, so match `bot_event` instead |
| `MediaProcessing` | (none) | Post-call processing after `Stopped` or `Kicked`. A poll can see `InMeeting` and then `MediaProcessing` or `Done` and never `Stopped` |
| `Done` | `bot.done` | All processing complete - **terminal**. Poll until `Done` (or another final status: `NotAllowed`, `Denied`, `Failed`, `Error`, `MediaExpired`, `Cancelled`), with a cap |

### `*.failed` events

Live-verified: `transcription.failed` is a real event with `status_code: 500`, `transcript_status: "Failed"`, and `message` carrying the upstream error (e.g. provider auth failure). Handle these in your router:

```python
elif event_type == "transcription.failed":
    log_error(f"Transcript failed for bot {bot_id}: {payload.get('message')}")
elif event_type == "bot.stopped" and payload.get("bot_event") == "bot.failed":
    log_error(f"Bot failed: {payload.get('message')}")
```

Symmetric `audio.failed` and `video.failed` events have NOT been observed in live testing. Don't assume they exist - handle failures by checking `bot_details.AudioStatus` and `bot_details.TranscriptStatus`, and by watching for `bot.stopped` with `bot_event: "bot.failed"`.

### Webhook signature verification

Only deliveries to **workspace webhook endpoints** (added in the MeetStream dashboard with
a signing secret) are signed. Per-bot `callback_url` deliveries are **not signed**: if you
need signatures, add the URL as a workspace webhook endpoint. Live transcript POSTs are never
signed; `realtime_endpoints` are signed only on Google Meet. Signed requests include:
- `X-MeetStream-Signature: sha256=<hex_digest>` - `HMAC-SHA256(secret, raw_body)`
- `X-MeetStream-Timestamp: <iso8601>`: an ISO 8601 UTC string such as `2026-11-19T14:30:00Z`. Parse it as a time, not as a number.

Verify by computing `HMAC-SHA256(secret, raw_request_body)`, comparing against the signature (strip the `sha256=` prefix), and optionally checking the timestamp is within an acceptable replay window.

---
