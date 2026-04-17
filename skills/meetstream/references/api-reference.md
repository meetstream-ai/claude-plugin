# MeetStream API Reference

Base URL: `https://api.meetstream.ai/api/v1/`
Auth: `Authorization: Token YOUR_API_KEY`

---

## Bot Endpoints

### POST `/bots/create_bot`
Creates a bot and sends it to a meeting.

**Required:**
- `meeting_link` (string) — Zoom, Google Meet, or Teams meeting URL
- `video_required` (bool) — set `false` unless video recording/streaming is needed

**Optional:**
- `bot_name` (string) — name shown in the meeting
- `audio_required` (bool) — set `true` to record audio
- `bot_message` (string) — message posted in meeting chat on join
- `bot_image` (string) — profile image URL (jpeg/png/gif); must be a **publicly accessible URL**, not base64
- `join_at` (string) — schedule future join: `YYYY-MM-DDTHH:MM:SSZ`
- `callback_url` (string) — HTTPS endpoint for lifecycle webhook events
- `socket_connection_url` (object) — `{ "url": "wss://..." }` for real-time bot control
- `live_transcription_required` (object) — `{ "webhook_url": "..." }` or `{ "websocket_url": "wss://..." }`
- `live_audio_required` (object) — `{ "websocket_url": "wss://..." }`
- `live_video_required` (object) — `{ "websocket_url": "wss://..." }`
- `agent_config_id` (string) — enables agentic features
- `custom_attributes` (object) — arbitrary key-value tags
- `recording_config` (object) — transcription provider + retention policy + realtime event webhooks
- `automatic_leave` (object) — timeout rules in seconds

**Returns:** `{ "bot_id": "...", "meeting_url": "...", "status": "..." }` — HTTP 201

---

### GET `/bots/{bot_id}/status`
Current bot status: `joining` → `InMeeting` → `Stopped`

---

### GET `/bots/{bot_id}/get_bot_detail`
Full session metadata. Use for debugging.

---

### GET `/bots/{bot_id}/get_bot_transcript`
Full post-processed transcript with speaker labels.
Only available after `transcription.processed` callback.

---

### GET `/bots/{bot_id}/get_bot_speaker_timeline`
Timeline of who spoke and when.

---

### GET `/bots/{bot_id}/get_bot_audio`
Recorded audio file URL or stream.
Available after `audio.processed` callback.

---

### GET `/bots/{bot_id}/get_bot_video`
Recorded video file URL or stream.
Available after `video.processed` callback.

---

### GET `/bots/{bot_id}/get_bot_chat`
In-meeting chat messages.

---

### GET `/bots/{bot_id}/get_bot_screenshot`
Screenshot captured during the meeting.

---

### GET `/bots/{bot_id}/get_bot_participants`
List of participants detected in the meeting.
Returns `[{ "name": "Alice", "displayName": "Alice Smith", ... }]` — not flat strings. Map with `p.name ?? p.displayName ?? 'Unknown'`.

---

### GET `/bots/{bot_id}/remove_bot`
Removes the bot from an active meeting.

---

### DELETE `/bots/{bot_id}/delete_bot_data`
Permanently deletes audio, video, and transcript for a bot.
Triggers `data_deletion` callback event.

---

### GET `/bots/list_bots`
Returns all bots for the account.

---

### PATCH `/bots/reschedule_bot`
Changes the scheduled join time for a future bot.

---

### DELETE `/bots/delete_scheduled_bot`
Deletes a bot that hasn't joined yet.

---

## Calendar Endpoints

### POST `/calendar/create-calendar`
Connects a Google Calendar using OAuth credentials.
Bots are auto-scheduled for all linked calendar events.

**Body:** `{ "refresh_token": "...", "client_id": "...", "client_secret": "..." }`

---

### GET `/calendar/events`
Lists upcoming events from the connected calendar.

---

### POST `/calendar/schedule`
Manually schedules a bot for a specific calendar event.

---

### GET `/calendar/scheduled`
Lists all scheduled bots (from calendar auto-scheduling).

---

### PATCH `/calendar/scheduled/{id}`
Updates a scheduled bot's configuration before the meeting.

---

### PATCH `/calendar/reschedule/{id}`
Reschedules a calendar bot to a different time.

---

### DELETE `/calendar/scheduled/{id}`
Removes a scheduled bot entry.

---

### DELETE `/calendar/disconnect`
Disconnects the linked Google Calendar.

---

## Callback Events (Webhook Payloads)

All events sent to your `callback_url` as HTTP POST. Your endpoint must return HTTP 200.

All payloads include: `bot_id`, `event`, `message`, `status_code`

| `event` | Meaning | `status_code` |
|---------|---------|---------------|
| `bot.joining` | Bot attempting to join | 102 |
| `bot.inmeeting` | Bot joined successfully | 200 |
| `bot.stopped` | Bot left the meeting | 500 |
| `audio.processed` | Audio ready to fetch | 200 |
| `audio.failed` | Audio processing error | 200 |
| `transcription.processed` | Transcript ready to fetch | 200 |
| `transcription.failed` | Transcription error | 200 |
| `video.processed` | Video ready to fetch | 200 |
| `video.failed` | Video processing error | 200 |
| `video.skipped` | No video data available | 404 |
| `data_deletion` | Data deleted | 200 |

---

## recording_config Schema

```json
{
  "recording_config": {
    "transcript": {
      "provider": {
        "deepgram": { "language": "en", "model": "nova-3" }
      }
    },
    "retention": {
      "type": "timed",
      "hours": 48
    },
    "realtime_endpoints": [
      {
        "type": "webhook",
        "url": "https://your-server.com/events",
        "events": ["participant_events.join", "participant_events.leave"]
      }
    ]
  }
}
```

Transcription providers: `deepgram` | `deepgram_streaming` | `assemblyai` | `assemblyai_streaming`

---

## automatic_leave Schema

```json
{
  "automatic_leave": {
    "waiting_room_timeout": 300,
    "everyone_left_timeout": 60,
    "in_call_recording_timeout": 14400,
    "recording_permission_denied_timeout": 60
  }
}
```

All values in seconds. Max recording duration default: 4 hours (14400s).
**`recording_permission_denied_timeout` minimum is 60.** Values under 60 return HTTP 400.

---

## Live Transcript Chunk Schema

```json
{
  "speakerName": "Alice",
  "timestamp": "2024-01-15T10:30:45Z",
  "transcript": "Can you walk me through pricing?",
  "words": [
    {
      "word": "Can",
      "start": 0.24,
      "end": 0.52,
      "confidence": 0.99,
      "speaker": "0",
      "punctuated_word": "Can",
      "speech_confidence": 0.98
    }
  ]
}
```

---

## WebSocket Control Commands

After bot joins, it sends `{ "type": "ready", "bot_id": "..." }` to your WSS server.

Send to bot:
```json
{ "command": "sendmsg", "message": "Hello from server!", "bot_id": "BOT_ID" }
{ "command": "sendaudio", "audiochunk": "<base64 PCM>" }
```
