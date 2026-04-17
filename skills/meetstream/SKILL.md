---
name: meetstream
description: >
  Build meeting intelligence with MeetStream's bot API. Use this skill whenever a developer
  wants to: join a meeting with a bot, record or transcribe meetings, stream live audio/video,
  build AI coaching tools, note-taking agents, CRM auto-update pipelines, calendar automation,
  or anything that processes meeting data programmatically. Supports Zoom, Google Meet, and
  Microsoft Teams. Activate on any mention of MeetStream, meeting bots, recording meetings
  via API, live transcription, "joining a meeting programmatically", or "build me a notetaker".
  When the user asks to BUILD or CREATE an integration, always enter plan mode first using the
  superpowers:writing-plans skill before writing any code.
mcp_server: https://docs.meetstream.ai/_mcp/server
---

# MeetStream Developer Skill

You are a MeetStream integration expert. Your job is to build **complete, production-ready implementations** — not outlines or pseudocode.

---

## Step 0: Before Writing Any Code

**If the user asks you to BUILD, CREATE, IMPLEMENT, or SET UP a MeetStream integration:**

1. Invoke the `superpowers:writing-plans` skill first
2. Create the project folder if it doesn't exist
3. Read `references/code-patterns-node.md` or `references/code-patterns-python.md` for the relevant patterns
4. Write the full plan to `docs/superpowers/plans/YYYY-MM-DD-<feature-name>.md`
5. Offer subagent-driven vs inline execution

**Skip plan mode only if** the user explicitly says "quick snippet", "just show me", or "skip planning".

**If the user just has a question** (how does X work, what's the API for Y) — answer directly, no plan needed.

---

## Setup: One Line of Config

All MeetStream API calls need this header:
```
Authorization: Token YOUR_API_KEY
```

API keys are created at https://app.meetstream.ai/api-keys.

Base URL: `https://api.meetstream.ai/api/v1/`

Default language: **Python** unless the user specifies otherwise.

---

## Gathering Requirements

Before planning or building, ask:
1. **API key** — if not provided, ask. Link: https://app.meetstream.ai/api-keys
2. **Platform** — Google Meet, Teams, Zoom, or all? (Zoom needs extra setup)
3. **Language** — Python or Node.js/TypeScript?
4. **Use case** — see patterns below

---

## Use Case Patterns

Map the user's request to one of these, then read the relevant code pattern file for the full implementation.

### Pattern 1: Record + Transcript (most common)
Bot joins, records, transcript fetched post-meeting.

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

### Pattern 2: Real-Time Transcription (AI agents, live coaching)
Transcript chunks stream to your WebSocket server as words are spoken.

```json
{
  "live_transcription_required": { "websocket_url": "wss://your-server.com/transcripts" },
  "live_audio_required": { "websocket_url": "wss://your-server.com/audio" }
}
```

Each chunk:
```json
{
  "speakerName": "Alice",
  "timestamp": "2024-01-15T10:30:45Z",
  "transcript": "Can you walk me through the pricing?",
  "words": [{ "word": "Can", "start": 0.2, "end": 0.5, "confidence": 0.99, "speaker": "0" }]
}
```

### Pattern 3: Interactive Bot (chat messages or TTS audio)
Bot joins and can respond in meeting chat or speak.

```json
{ "socket_connection_url": { "url": "wss://your-server.com/bot-control" } }
```

On join, bot sends `{ "type": "ready", "bot_id": "..." }` to your WSS. You send back:
```json
{ "command": "sendmsg", "message": "Notes captured!", "bot_id": "..." }
{ "command": "sendaudio", "audiochunk": "<base64 PCM>" }
```

### Pattern 4: Calendar-Automated Bot
Bot auto-joins every Google Calendar meeting — no per-meeting API calls.

```
POST /calendar/create-calendar
{ "refresh_token": "...", "client_id": "...", "client_secret": "..." }
```

List upcoming: `GET /calendar/events` | Scheduled bots: `GET /calendar/scheduled`

### Pattern 5: Note-Taker (full pipeline)
Webhook server + bot creation + transcript fetch + AI summary + delivery (email/Slack/Notion).

Read `references/code-patterns-node.md` Pattern 4 for the complete Next.js implementation.
Build plan should include: webhook handler, transcript fetch, LLM summary, delivery layer.

### Pattern 6: Participant Tracking
Real-time join/leave events during the meeting:

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

## Bot Lifecycle

```
create_bot → bot.joining (102) → bot.inmeeting (200) → [streams run]
→ bot.stopped (500) → audio.processed → transcription.processed → fetch data
```

**Never call `get_bot_transcript` until `transcription.processed` fires.** The endpoint returns nothing or an error if called early. Always set `callback_url`.

---

## Always Include These Timeouts

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

**`recording_permission_denied_timeout` minimum is 60 seconds.** The API returns HTTP 400 for any value under 60. Without this field, a bot that gets its recording permission denied will sit in the meeting indefinitely.

---

## Bot Avatar (bot_image)

To show a custom profile picture in meetings, pass a **publicly accessible URL** via `bot_image`:

```json
{ "bot_image": "https://your-server.com/avatar.png" }
```

**Important:** MeetStream fetches this URL externally. You cannot pass base64 data. The image must be reachable without authentication. If you store images in a database (e.g., Firestore), serve them from a public HTTP endpoint on your own server.

---

## Platform Notes

| Platform | Extra Setup |
|----------|-------------|
| Google Meet | None |
| Microsoft Teams | None |
| Zoom | Register a Zoom app + add credentials to MeetStream dashboard → https://docs.meetstream.ai/guides/zoom/zoom-marketplace-app-setup |

**Zoom dev mode** restricts bots to meetings hosted by the app owner's account. For external meetings, submit the Zoom app to production.

---

## Transcription Providers

| Provider | Mode | Best For |
|----------|------|---------|
| `deepgram` + `nova-3` | Post-processing | Accuracy, cost efficiency — default |
| `deepgram_streaming` | Real-time | Live coaching, live agents |
| `assemblyai` + `universal` | Post-processing | Speaker diarization |
| `assemblyai_streaming` | Real-time | Real-time pipelines |

---

## Webhook Handler Requirements

- Must use HTTPS (use ngrok for local dev: `ngrok http 3000`)
- Must return HTTP 200 within 5 seconds — respond first, process async
- Handle idempotency — events may be retried

---

## Data Available After Meeting

After `transcription.processed`:

| Data | Endpoint |
|------|---------|
| Transcript with speaker labels | `GET /bots/{bot_id}/get_bot_transcript` |
| Speaker timeline | `GET /bots/{bot_id}/get_bot_speaker_timeline` |
| In-meeting chat | `GET /bots/{bot_id}/get_bot_chat` |
| Audio file | `GET /bots/{bot_id}/get_bot_audio` |
| Video file | `GET /bots/{bot_id}/get_bot_video` |
| Participant list | `GET /bots/{bot_id}/get_bot_participants` |
| Session metadata | `GET /bots/{bot_id}/get_bot_detail` |
| Screenshot | `GET /bots/{bot_id}/get_bot_screenshot` |

---

## Data Retention

Default: 7 days. Override:
```json
{ "recording_config": { "retention": { "type": "timed", "hours": 24 } } }
```

Delete manually: `DELETE /bots/{bot_id}/delete_bot_data` — fires `data_deletion` callback.

---

## Common Mistakes

1. **Fetching transcript too early** — always wait for `transcription.processed`
2. **HTTP callback URL** — must be HTTPS; use ngrok for local dev
3. **Zoom dev mode** — can only join app owner's meetings until app is approved
4. **Missing `audio_required: true`** — audio is not recorded without this flag
5. **No timeout** — always set `everyone_left_timeout` or the bot runs forever
6. **`recording_permission_denied_timeout` under 60** — API returns HTTP 400. Minimum is 60 seconds. The old default of 10 in docs was wrong.
7. **`bot_image` as base64** — must be a publicly accessible URL; MeetStream fetches it from your server
8. **Calendar endpoint typo** — it's `POST /calendar/create-calendar` (hyphen), not `create_calendar` (underscore)
9. **`remove_bot` as DELETE** — it's `GET /bots/{id}/remove_bot`, not a DELETE method
10. **`get_bot_participants` flat strings** — returns `[{ name, displayName, ... }]`; map with `p.name ?? p.displayName ?? 'Unknown'`
11. **Deepgram model without language** — `nova-3` requires `language: 'en'` to be set explicitly in the provider config
12. **`custom_attributes` with non-string values** — all values must be strings; don't pass numbers or booleans

---

## Code Reference Files

Read these when building:
- `references/code-patterns-node.md` — complete Node.js/TypeScript implementations
- `references/code-patterns-python.md` — complete Python implementations
- `references/api-reference.md` — full endpoint map with params and return types

---

## MCP Server

For specific endpoint parameters, response schemas, or edge cases not covered above:
```
https://docs.meetstream.ai/_mcp/server
```
