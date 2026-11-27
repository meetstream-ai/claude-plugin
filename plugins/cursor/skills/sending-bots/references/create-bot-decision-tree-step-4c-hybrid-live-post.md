# create_bot decision tree: STEP 4C - Hybrid (live + post-call)

> Part of [`create-bot-decision-tree.md`](create-bot-decision-tree.md), split so each file stays under 20 KB.

### STEP 4C - Hybrid (live + post-call)

```
Configure the bot for LIVE only at create time (Step 4A), then:

After you receive bot.stopped, call:
  POST /bots/{bot_id}/transcribe
  {
    "provider": {"deepgram": {...}},        # any post-call provider
    "callback_url": "https://you/webhook"   # gets transcription.processed/.failed
  }

This:
  - Returns a new transcript_id
  - Overwrites bot_details.transcript_id (canonical fetch returns this one)
  - Fires exactly ONE transcription.processed or .failed (no bot.done follow-up)
  - Does NOT include custom_attributes in the /transcribe webhook
```

---

### STEP 5 - Other webhooks (beyond transcription)

```
Q5.1: Need to know when participants join/leave the meeting, or raise/lower
      their hand?
      ├─ Yes → add to recording_config:
      │   "realtime_endpoints": [{
      │     "type": "webhook",
      │     "url": "https://you/participants",
      │     "events": ["participant_events.join", "participant_events.leave",
      │                "participant_events.raise_hand", "participant_events.lower_hand"]
      │   }]
      │   ⚠ These webhooks have a DIFFERENT shape - nested under
      │   data.data.action / data.bot.id, no top-level bot_id or bot_status.
      │   ⚠ Hand events go ONLY to realtime_endpoints that list them, never to
      │   workspace webhooks. Google Meet and Zoom. Transitions only; the
      │   bot's own hand is never reported.
      └─ No → omit realtime_endpoints

Q5.2: Want your bot to interact in the meeting (send chat, play TTS audio,
      change its video frame)?
      ├─ Yes → "socket_connection_url": { "websocket_url": "wss://you/control" }
      │        See Pattern 3 - bot opens a WS to your server; you send the
      │        documented commands (sendaudio, sendmsg, interrupt, resume_audio,
      │        sendimg/sendimg_url) over it.
      └─ No → omit socket_connection_url

Q5.3: (Ask only if the user asked for an agent.) Own stack or hosted by MeetStream?
      ├─ Own stack (track 2, bridge server) → both
      │        "live_audio_required" and "socket_connection_url" on this bot,
      │        no agent_config_id (see `streaming-live-data`). Bot price only.
      ├─ Hosted (track 3a or 3c, MIA) → create the agent in the dashboard (app.meetstream.ai)
      │        or via POST /api/v1/mia (see Pattern 9; 3a default keys, then 3c own keys),
      │        then pass only its ID on create_bot, with no bridge sockets:
      │          "agent_config_id": "<from above>"
      └─ No agent → omit agent_config_id

Q5.4: Want to publish live video/audio INTO the bot's camera and mic (WebRTC)?
      ├─ Yes → "bot_camera_stream": { "websocket_url": "wss://you/camera" }
      │        • Google Meet (ws:// or wss://), Teams and Zoom (wss:// only)
      │        • The bot connects OUT to your signaling socket; the host must
      │          resolve to a public address
      │        • Zoom: cannot be combined with agent_config_id (HTTP 400)
      │        • Guide: https://docs.meetstream.ai/guides/websockets/bot-camera-streaming
      └─ No → omit bot_camera_stream

Q5.5: Should the bot raise its hand before it speaks (wait its turn)?
      ├─ Yes → after the bot is InMeeting/Recording, call
      │        POST /bots/{bot_id}/send_command  {"command": "raise_hand"}
      │        and {"command": "lower_hand"} when done. See "In-Meeting
      │        Commands" below. Nothing to add to create_bot.
      └─ No → nothing to do
```

---

### STEP 6 - Scheduling

```
Q6.1: When does the bot join?
      ├─ Right now → omit join_at; bot joins as soon as create_bot returns
      ├─ At a specific time → "join_at": "2026-04-22T15:00:00Z"  (ISO-8601)
      └─ Automatically for all calendar meetings →
         Skip create_bot. Use the Calendar API instead:
         POST /calendar/create_calendar (connect)
         POST /calendar/auto-schedule/enable (with default_bot_config)
         See "Pattern 6: Calendar Auto-Scheduling".
```

---

### STEP 7 - Metadata for routing/billing

```
Q7.1: Need to correlate webhooks back to your internal records (tenant ID,
      deal ID, user ID)?
      ├─ Yes → "custom_attributes": {
      │           "tenant_id": "acme-123",
      │           "deal_id": "hubspot-456",
      │           "internal_user_id": "u_789"
      │        }
      │        ⚠ Stringify all values defensively (live API has been observed
      │        to reject non-string values even though OpenAPI allows any).
      │        ⚠ custom_attributes is echoed on lifecycle events BUT NOT on
      │        /transcribe-triggered webhooks. Correlate by bot_id there.
      └─ No → omit custom_attributes (recommended only for trivial use cases)

Q7.2: Should recordings go to one of the user's own storage destinations?
      ├─ Yes → "storage_id": "<destination ID from the dashboard>"
      │        • 1-80 letters, numbers, underscores or hyphens, else HTTP 400
      │        • Destinations are set up in the dashboard (no public API)
      │        • An unknown ID or a destination that fails validation: HTTP 400
      │          with the storage error text
      └─ No → omit storage_id (workspace default destination, or MeetStream
               storage when none is configured)
```

---

### STEP 8 - Timeouts (use these defaults unless you have a reason not to)

```
"automatic_leave": {
  "waiting_room_timeout": 600,        // 10 min - long meetings start late
  "everyone_left_timeout": 600,       // 10 min - handle bio breaks
  "voice_inactivity_timeout": 600,    // 10 min - silent presentations
  "in_call_recording_timeout": 14400, // 4 hr - handle long workshops
  "recording_permission_denied_timeout": 600  // 10 min - Zoom-only, MAX is 600 (also the default)
}
```

Live-verified constraints:
- `in_call_recording_timeout` minimum 600s (API HTTP 400 below)
- `recording_permission_denied_timeout` range 60–600s, default 600 (API HTTP 400 outside)

---

### Final assembly - your complete `create_bot` payload

Combine every answer above. A realistic post-call notetaker for Google Meet might look like:

```json
POST https://api.meetstream.ai/api/v1/bots/create_bot
Authorization: Token YOUR_API_KEY

{
  "meeting_link": "https://meet.google.com/abc-defg-hij",
  "bot_name": "Acme Notetaker",
  "bot_message": "Hi! I'm an AI notetaker for Acme. Transcript will be emailed after.",
  "bot_image_url": "https://acme-cdn.com/bot-avatar.png",
  "video_required": false,
  "callback_url": "https://api.acme.com/webhooks/meetstream",
  "custom_attributes": {
    "tenant_id": "acme-prod-tenant-42",
    "user_id": "u_12345"
  },
  "recording_config": {
    "transcript": {
      "provider": { "deepgram": { "model": "nova-3", "language": "en" } }
    },
    "retention": { "type": "timed", "hours": 168 }
  },
  "automatic_leave": {
    "waiting_room_timeout": 600,
    "everyone_left_timeout": 600,
    "voice_inactivity_timeout": 600,
    "in_call_recording_timeout": 14400,
    "recording_permission_denied_timeout": 600
  }
}
```

A live AI-coach bot for the same meeting might look like:

```json
{
  "meeting_link": "https://meet.google.com/abc-defg-hij",
  "bot_name": "Sales Coach",
  "video_required": false,
  "callback_url": "https://api.acme.com/webhooks/meetstream",
  "live_transcription_required": {
    "webhook_url": "https://api.acme.com/live/transcript"
  },
  "recording_config": {
    "transcript": { "provider": { "meetstream_streaming": {} } },
    "retention": { "type": "timed", "hours": 24 }
  },
  "automatic_leave": {
    "waiting_room_timeout": 600,
    "everyone_left_timeout": 600,
    "voice_inactivity_timeout": 600,
    "in_call_recording_timeout": 14400,
    "recording_permission_denied_timeout": 600
  }
}
```

When in doubt, walk the user through every step above before sending `create_bot`. It's better to ask 3 extra questions than to ship a bot configured wrong for their use case.

---
