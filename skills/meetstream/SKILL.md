---
name: meetstream
description: >
  Build meeting intelligence with MeetStream's bot API. Use this skill whenever a developer
  wants to: join a meeting with a bot, record or transcribe meetings, stream live audio/video,
  build AI coaching tools, note-taking agents, CRM auto-update pipelines, or anything that
  processes meeting data programmatically. Supports Zoom, Google Meet, and Microsoft Teams.
  When the user provides a MeetStream API key, Claude should generate complete, production-ready
  code — not just snippets. Activate on any mention of MeetStream, meeting bots, recording
  meetings via API, live meeting transcription, or "joining a meeting programmatically."
mcp_server: https://docs.meetstream.ai/_mcp/server
---

# MeetStream Developer Skill

You are a MeetStream integration expert. When a developer asks you to build anything involving meeting bots, transcription, or real-time meeting data, you write **complete working implementations** — not outlines or pseudocode. Ask for their API key if they haven't provided one, then build it.

## Setup: One Line of Config

All MeetStream API calls need this header:
```
Authorization: Token YOUR_API_KEY
```

API keys are created at https://app.meetstream.ai/api-keys.

Base URL: `https://api.meetstream.ai/api/v1/`

---

## What to Build and How

When a developer describes their use case, map it to one of these patterns and implement the full solution:

### Pattern 1: Record a Meeting and Get the Transcript
The most common starting point. Bot joins, records, transcript is fetched after the meeting ends.

See `references/code-patterns-node.md` and `references/code-patterns-python.md` for complete server implementations.

**Core request:**
```json
POST /bots/create_bot
{
  "meeting_link": "https://zoom.us/j/123456789",
  "bot_name": "Recorder",
  "audio_required": true,
  "video_required": false,
  "callback_url": "https://your-server.com/webhook",
  "recording_config": {
    "transcript": {
      "provider": { "deepgram": { "language": "en", "model": "nova-3" } }
    },
    "retention": { "type": "timed", "hours": 48 }
  }
}
```

Returns `{ "bot_id": "..." }`. Wait for `transcription.processed` webhook, then:
```
GET /bots/{bot_id}/get_bot_transcript
```

### Pattern 2: Real-Time Transcription (AI Agents, Live Coaching)
Bot streams transcript chunks to your server as words are spoken.

```json
POST /bots/create_bot
{
  "meeting_link": "...",
  "bot_name": "AI Coach",
  "audio_required": true,
  "video_required": false,
  "live_transcription_required": {
    "websocket_url": "wss://your-server.com/transcripts"
  },
  "live_audio_required": {
    "websocket_url": "wss://your-server.com/audio"
  }
}
```

Each transcript chunk arrives as:
```json
{
  "speakerName": "Alice",
  "timestamp": "2024-01-15T10:30:45Z",
  "transcript": "Can you walk me through the pricing?",
  "words": [{ "word": "Can", "start": 0.2, "end": 0.5, "confidence": 0.99, "speaker": "0" }]
}
```

### Pattern 3: Interactive Bot (Sends Messages or Audio)
Bot joins and can respond in the meeting chat or speak via TTS.

Set `socket_connection_url` at creation:
```json
{
  "socket_connection_url": { "url": "wss://your-server.com/bot-control" }
}
```

When bot joins, it sends `{ "type": "ready", "bot_id": "..." }` to your WebSocket. You then send:
```json
{ "command": "sendmsg", "message": "Meeting summary coming up!", "bot_id": "..." }
```
Or play audio:
```json
{ "command": "sendaudio", "audiochunk": "<base64 PCM audio>" }
```

### Pattern 4: Calendar-Automated Bot
Bot joins every meeting on a Google Calendar automatically — no per-meeting API calls.

```
POST /calendar/create-calendar
{ "refresh_token": "...", "client_id": "...", "client_secret": "..." }
```

After connecting, list upcoming events with `GET /calendar/events`, view scheduled bots with `GET /calendar/scheduled`.

### Pattern 5: Participant Tracking
Get participant join/leave events during the meeting in real-time:

```json
{
  "recording_config": {
    "realtime_endpoints": [{
      "type": "webhook",
      "url": "https://your-server.com/participants",
      "events": ["participant_events.join", "participant_events.leave"]
    }]
  }
}
```

---

## Bot Lifecycle (Know This Before Writing Code)

```
create_bot → bot.joining (102) → bot.inmeeting (200) → [live streams run] 
→ bot.stopped (500) → audio.processed → transcription.processed → ready to fetch
```

Never call `get_bot_transcript` until `transcription.processed` fires. Always set `callback_url` — it's how you know when processing is done.

---

## Full Endpoint Map

See `references/api-reference.md` for the complete endpoint list with params and return types.

---

## Platform-Specific Notes

| Platform | Setup Required |
|----------|----------------|
| Google Meet | None — works immediately |
| Microsoft Teams | None — works immediately |
| Zoom | Need to register a Zoom app and add credentials to MeetStream dashboard. See: https://docs.meetstream.ai/guides/zoom/zoom-marketplace-app-setup |

**Zoom note:** In development mode, Zoom bots can only join meetings hosted by the account that owns the app. For production (joining any meeting), the Zoom app must be submitted and approved by Zoom.

---

## Transcription Providers

| Provider | Mode | Best For |
|----------|------|---------|
| `deepgram` + model `nova-3` | Post-processing | Accuracy, cost efficiency |
| `deepgram_streaming` | Real-time | Live coaching, live agents |
| `assemblyai` + model `universal` | Post-processing | High accuracy, speaker diarization |
| `assemblyai_streaming` | Real-time | Real-time pipelines |

---

## Automatic Leave Timeouts

Always configure these to avoid runaway bots:
```json
{
  "automatic_leave": {
    "waiting_room_timeout": 300,
    "everyone_left_timeout": 60,
    "in_call_recording_timeout": 7200,
    "recording_permission_denied_timeout": 10
  }
}
```

Set `recording_permission_denied_timeout` to `10` seconds — if permission is denied, the bot leaves immediately instead of sitting in the meeting.

---

## Webhook Handler Requirements

Your `callback_url` endpoint must:
- Use HTTPS (not HTTP)
- Be publicly accessible (use ngrok or similar for local dev)
- Return HTTP 200 within 5 seconds
- Handle idempotency (events may be retried)

---

## Data Retrieval After Meeting

After `transcription.processed` fires:

| What you want | Endpoint |
|--------------|---------|
| Full transcript with speaker labels | `GET /bots/{bot_id}/get_bot_transcript` |
| Who spoke when (timeline) | `GET /bots/{bot_id}/get_bot_speaker_timeline` |
| In-meeting chat | `GET /bots/{bot_id}/get_bot_chat` |
| Audio file | `GET /bots/{bot_id}/get_bot_audio` |
| Video file | `GET /bots/{bot_id}/get_bot_video` |
| Participant list | `GET /bots/{bot_id}/get_bot_participants` |
| Bot session metadata | `GET /bots/{bot_id}/get_bot_detail` |
| Screenshot | `GET /bots/{bot_id}/get_bot_screenshot` |

---

## Data Retention and Cleanup

Default: data is deleted after 7 days. To change:
```json
{
  "recording_config": {
    "retention": { "type": "timed", "hours": 24 }
  }
}
```

Delete manually: `DELETE /bots/{bot_id}/delete_bot_data`

A `data_deletion` callback fires when deletion completes.

---

## Common Mistakes to Avoid

**1. Calling get_bot_transcript before transcription.processed**
Always wait for the callback before fetching. The endpoint returns nothing or an error if called early.

**2. Callback URL not publicly accessible**
Use ngrok in development: `ngrok http 3000` → use the `https://` URL.

**3. Zoom bot can't join external meetings**
Zoom development mode restricts bots to the app owner's account. For external meetings, submit the Zoom app to production.

**4. Missing audio_required flag**
`audio_required: true` must be set explicitly for audio recording. `video_required` defaults vary.

**5. No timeout configured**
Always set `automatic_leave.everyone_left_timeout` — otherwise the bot stays in an empty meeting indefinitely.

---

## When the Developer Provides an API Key

Ask: "What are you building?" then write the complete implementation:

1. **If they say "record and transcribe"** → write a webhook server + bot creation call + transcript fetch, all in one runnable file
2. **If they say "real-time transcription"** → write the WebSocket server + bot creation call
3. **If they say "AI agent that joins meetings"** → write the WebSocket control server + bot creation + command loop
4. **If they say "auto-join calendar meetings"** → write the OAuth flow + calendar connect + event listing
5. **If they say "note-taker"** → write the full server: webhook handler + bot creation + transcript fetch + summary generation hook

Default language: **Python** unless they specify otherwise. Also offer Node.js/TypeScript.

Read `references/code-patterns-python.md` for complete Python implementations.
Read `references/code-patterns-node.md` for complete Node.js/TypeScript implementations.

---

## MCP Server

When you need to look up specific endpoint parameters, response schemas, or edge cases not covered here, query the MeetStream documentation MCP server:
```
https://docs.meetstream.ai/_mcp/server
```
