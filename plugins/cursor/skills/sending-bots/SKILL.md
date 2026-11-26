---
name: sending-bots
description: >
  Build the create_bot request in app code: required fields, recording defaults
  (audio only, speaker_view when video is on), identity (bot_name, bot_image_url,
  bot_message), automatic_leave timeouts, Idempotency-Key and deduplication_key,
  then follow the bot (status, detail, list with filters), act in the meeting
  over REST (send_message, send_image, send_command raise_hand / lower_hand /
  screenshot, pause_recording, resume_recording) and remove it (remove_bot,
  stop_status). Use when the user says "create_bot payload", "bot config",
  "send a bot from my app", "bot_name", "bot avatar", "join message",
  "automatic leave", "the bot stays too long", "pause the recording",
  "post in the meeting chat", "show an image", "make the bot leave", "one bot
  per meeting", or "list my bots". Formerly part of the meetstream core skill
  (decision tree) and join-meeting.
---

# Sending bots from app code

The bot is the unit of everything: one `create_bot` call, one `bot_id`, then status, artifacts and
in-meeting actions keyed on it. This skill is for the code the user builds. To send a bot right now
from this agent, use `meetstream-cli`. Platform setup (Zoom app, signed-in bots) is in
`setting-up-platforms`; events in `handling-webhooks`. Hard rules (auth header, retries, Zoom
wording) are in the `meetstream` router.

## Fastest path

```bash
curl -X POST https://api.meetstream.ai/api/v1/bots/create_bot \
  -H "Authorization: Token $MEETSTREAM_API_KEY" -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d '{"meeting_link": "https://meet.google.com/abc-defg-hij", "bot_name": "Acme Notetaker",
       "video_required": false, "callback_url": "https://your-server.example/webhook",
       "recording_config": {"transcript": {"provider": {"meetstream": {}}}}}'
```

```ts
import { MeetStream } from '@meetstream/sdk';            // npm install @meetstream/sdk
const ms = new MeetStream();                               // reads MEETSTREAM_API_KEY from the app's environment
const bot = await ms.bots.create({ meeting_link, bot_name: 'Acme Notetaker', video_required: false });
```

```python
from meetstream import MeetStream                          # pip install meetstream-sdk
ms = MeetStream()
bot = ms.bots.create({"meeting_link": meeting_link, "bot_name": "Acme Notetaker", "video_required": False})
```

The response is 201 `{"bot_id", "transcript_id", "meeting_url", "status"}`. Keep `bot_id`. A
production config walks the decision tree in
[`references/create-bot-decision-tree.md`](references/create-bot-decision-tree.md) (identity,
platform, transcript, live data, webhooks, scheduling, metadata, timeouts, final payload).

## Fields that matter on every bot

- **Required:** `meeting_link` (not `meeting_url`). `bot_name` is what people see; always set a
  recognizable name, or the host may deny it.
- **Audio only by default:** send `"video_required": false` explicitly unless the user asks for
  video. With video on, send `recording_config.video_layout: "speaker_view"` (the API default is
  `grid_view`). Never set `video_separate_streams` unless the user asks for per-participant video.
- **Transcript:** only `recording_config.transcript.provider` is read. `meetstream` (post-call) and
  `meetstream_streaming` (live) need no provider key. Details: `getting-transcripts-and-media`.
- **Identity:** `bot_image_url` (public `https://` PNG, JPG, GIF or WebP, shown as the bot's
  camera), `bot_message` (posted in chat once after joining, for example a recording notice).
- **Routing:** `custom_attributes` (your tenant or job ids, echoed on events) and `callback_url`.
- **Scheduling:** `join_at` (ISO 8601, up to 90 days ahead). Calendars: `scheduling-and-calendars`.
- **No-op bots are rejected:** `audio_required: false` with `video_required: false` and nothing
  else to do returns 400.

## Timeouts (`automatic_leave`)

Defaults that keep the bot in long meetings and stop it lingering (seconds):
`waiting_room_timeout` 600 (Google Meet 60 to 600), `everyone_left_timeout` 600,
`voice_inactivity_timeout` 600, `in_call_recording_timeout` 14400 (minimum 600, maximum 18000),
`recording_permission_denied_timeout` 600 (Zoom, 60 to 600). Bot time is billed from arrival,
including the wait in the lobby, so match `waiting_room_timeout` to when the host usually joins.
`bot_detection` leaves when another notetaker is present. Guide:
https://docs.meetstream.ai/guides/features/automatic-leave-configuration

## One bot per meeting

- `Idempotency-Key` header: a retry of the same request returns 507 with the original bot. Treat
  507 as success. One UUID per logical create, reused across its retries.
- `deduplication_key` in the body (also on `POST /calendar/schedule/{event_id}`): your own id for
  "this meeting has one bot". A repeat returns 200 with the original bot; the same key with a
  different `meeting_link` returns 409. Neither key expires, and replays are not charged.
- Before you send a second bot because the first is slow, check its status.
  Guide: https://docs.meetstream.ai/guides/features/deduplication-idempotency-keys

## Follow the bot

- `GET /api/v1/bots/{bot_id}/status` returns `{"bot_id", "status", "custom_attributes"}`.
  `GET /api/v1/bots/{bot_id}/detail` (or `GET /api/v1/bots/{bot_id}`) returns `bot_details` with
  `Status`, `ErrorReason`, `StatusTimeline`, `TranscriptStatus` and `transcript_id`.
- Statuses: `Scheduled`, `Joining`, `InWaitingRoom`, `InMeeting`, `Leaving`, `Stopped`,
  `MediaProcessing`, `Done`; never got in: `NotAllowed`, `Denied`, `Failed`, `Error`. A poll can
  jump from `InMeeting` to `MediaProcessing` to `Done`: stop on any final status, poll every 5 to
  10 seconds with a cap, and prefer webhooks.
- List: `GET /api/v1/bots?status=InMeeting&platform=GMeet&from=2026-11-21&limit=50`
  (`platform` = `GMeet`, `Zoom`, `Teams`, `ZoomRTMS`; `custom_attr[key]`). `limit` is at most 50;
  send `nextCursor` back as `cursor` while `hasNextPage` is true.

## Act in the meeting (REST)

Every live command needs the bot `InMeeting`. Before admission they return 409, or 503
(`Bot has no command endpoint`) right after `create_bot`: wait for `bot.inmeeting`, then retry a
503 two or three times with a pause. Limit: 30 commands per minute per bot.

| Action | Call | Notes |
|---|---|---|
| Post in chat | `POST /api/v1/bots/{bot_id}/send_message` `{"message": "..."}` | Up to 2,000 characters; to everyone. Zoom and Teams hold a lobby message until admission |
| Show an image or GIF | `POST /api/v1/bots/{bot_id}/send_image` `{"img_url": "https://...", "display_duration": 30}` | `img_url` (public https) or `img` (base64, about 5 MB); duration up to 300 s |
| Raise or lower the hand | `POST /api/v1/bots/{bot_id}/send_command` `{"command": "raise_hand"}` | `hand_raised` in the reply is the real state; Google Meet, Zoom, Teams |
| Screenshot | `send_command` `{"command": "screenshot"}` | Google Meet and Teams; on Zoom only for the no-app join. Images: `getting-transcripts-and-media` |
| Pause, resume | `POST /api/v1/bots/{bot_id}/pause_recording`, `POST /api/v1/bots/{bot_id}/resume_recording` | The bot stays; recording and per-participant files get silence and black video of the same length, live audio and live transcripts stop. Google Meet `meeting_captions` keep going |
| Change a live voice agent | `POST /api/v1/bots/{bot_id}/update_mia` | `building-voice-agents` |

Chat log after the call (`get_chats`) and live chat events: `getting-transcripts-and-media` and
`handling-webhooks`. Zoom Direct Connect sessions and WhatsApp bots are receive-only for most of
these (400). Guides: https://docs.meetstream.ai/guides/features/chat-and-visuals ,
https://docs.meetstream.ai/guides/features/pause-resume-recording ,
https://docs.meetstream.ai/guides/features/raise-lower-hand

## Remove the bot

`POST /api/v1/bots/{bot_id}/remove_bot` (GET also works) makes the bot leave now; recorded data is
kept and post-call processing runs. Every app that sends a bot calls it on shutdown or Ctrl-C.
`GET /api/v1/bots/{bot_id}/stop_status` reports the stop request (requested, acknowledged,
stopped, force-stopped or failed) without stopping the bot again. Deleting data is
`DELETE /api/v1/bots/{bot_id}/delete`: irreversible, only after the user confirms.

More detail: required fields, recording defaults, `video_layout` values, `bot_image_url`,
`custom_attributes` and the `send_command` reference in
[`references/bot-config.md`](references/bot-config.md).

## Latest docs

- Create Bot payload reference: https://docs.meetstream.ai/api-reference/create-bot-payload-reference
- Create your first bot: https://docs.meetstream.ai/guides/get-started/create-your-first-bot
- Automatic leave: https://docs.meetstream.ai/guides/features/automatic-leave-configuration
- How bots work: https://docs.meetstream.ai/guides/introduction/how-bots-work

For the latest details, fetch the page with `.md` appended, read https://docs.meetstream.ai/llms.txt, or connect the docs MCP server at https://docs.meetstream.ai/_mcp/server.
