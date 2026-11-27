# MeetStream API Reference: `recording_config` Schema

> Part of [`api-reference.md`](api-reference.md), split so each file stays under 20 KB.

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

Default when `retention` is omitted: media is kept permanently until you delete it. `{ "type": "timed", "hours": N }` deletes it automatically (`hours` defaults to 720 with `type: timed`).

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

## Live video (not available on meeting bots)

`live_video_required` is accepted but ignored by Google Meet, Zoom and Teams bots, and it still moves the bot to the larger video compute tier, so do not send it. Record video (`video_required: true`) and fetch it after the call. Live video frames exist only on Zoom Meeting Direct Connect (RTMS) sessions.
