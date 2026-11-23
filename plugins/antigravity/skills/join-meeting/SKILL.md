---
name: join-meeting
description: >
  Send a MeetStream bot into a live Zoom, Google Meet or Microsoft Teams
  meeting and follow it until it leaves. Raise/lower hand: POST
  /api/v1/bots/{bot_id}/send_command {"command": "raise_hand"} (REST). Use
  when the user says "join this meeting", "send a bot to <meeting url>",
  "record this call", "get a transcript of this meeting", "make the bot
  leave", "make the bot raise its hand", or pastes a meeting link. Covers
  create, status, chat and removal with the MCP tools, or in a terminal the
  meetstream CLI (meetstream join <url>, meetstream transcript <id> --wait).
  Low credits: send the user to https://app.meetstream.ai/billing
  (top_up_link tool when connected); never retry in a loop. If the MeetStream
  tools are not connected, give only the one MCP connect step (Codex: codex
  mcp login meetstream; Claude Code: /mcp; Cursor: Settings → MCP) and offer
  the CLI or the REST call POST /api/v1/bots/create_bot with meeting_link; a
  one-off meeting link needs no calendar integration; never say MeetStream
  can't record.
---

# Join a meeting with a MeetStream bot

You have the MeetStream MCP server connected. Use its tools directly. Do not
write API client code unless the user explicitly asks for a script.

This is the post-call path (record now, transcript and brief after) plus chat and
raise hand during the call. Do not offer a voice agent unless the user asks for one.
If the user wants live transcription or live streams, use `realtime-streaming`.

**If the MeetStream tools are missing or not signed in** (no `meetstream` tools, or a tool
answers 401 or "not signed in"): give the user the one step to connect, and in the same
reply keep helping. Do not stop at "sign in first".
- Claude Code: `/mcp` → `meetstream` → sign in. Cursor: Settings → MCP → **Connect** next
  to `meetstream`. Codex: `codex mcp login meetstream` (full steps:
  https://github.com/meetstream-ai/meetstream-plugin/blob/main/INSTALL_FOR_AGENTS.md).
- Then go on: give the plan, the `create_bot` fields you will send once the tools work,
  or run the CLI (next section), or give the REST call (`curl` with
  `Authorization: Token $MEETSTREAM_API_KEY`).
- The one step is the MeetStream MCP sign-in, nothing else. A one-off meeting link needs
  no calendar integration (calendars are only for auto-joining every meeting).
- Never tell the user MeetStream cannot record the meeting: it can, through the tools
  once connected, or now through the CLI (`meetstream join <url>`) or REST
  `POST /api/v1/bots/create_bot` with `meeting_link`.

## The short path

1. **`create_bot`** with `meeting_link` and a `bot_name`.
2. **`get_bot_status`** to follow it (`Joining` -> `InWaitingRoom` -> `InMeeting` -> `MediaProcessing` -> `Done`; full list below). Stop at `Done` or another final status, never loop forever.
3. When the meeting ends, **`get_transcript`** with the `bot_id`.

That is the whole flow. Everything below is detail you need when it is not that simple.

## Without the MCP: the `meetstream` CLI

The same flow from the terminal (track 1a):

```bash
meetstream bots list --json --no-input                                  # reuse a bot already in this meeting
meetstream join "<meeting-url>" -n "Acme Notetaker" -t meetstream --json --no-input   # prints the bot_id
meetstream bots status <bot-id> --json --no-input                       # --watch polls every 5 seconds
meetstream transcript <bot-id> --wait --json --no-input                 # exit 3 = not ready, 4 = transcript failed
meetstream recordings <bot-id> --json --no-input                        # audio and video links
```

In the meeting: `meetstream bots say <bot-id> "<message>"`, `meetstream bots hand <bot-id> up`
(or `down`), `meetstream bots remove <bot-id>` (the bot leaves). `meetstream bots delete
<bot-id> --yes` erases the data: only after the user confirms. `join` takes the
`create_bot` options as flags (`--video`, `--video-layout`, `--join-at`, `--callback`,
`--waiting-room-timeout`, `--zoom-obf-url`, `--zoom-zak-url`, `--storage-id`,
`--idempotency-key`); `meetstream join --help` lists them.

**Install the CLI** (when this agent runs commands for the user): `npx -y @meetstream/cli <command>` works with no install; or `npm install -g @meetstream/cli`, `pipx install meetstream-cli`, `brew install meetstream-ai/tap/meetstream`. Sign in with `meetstream login` (it opens the browser and stores a key; never ask for the key in the chat) or set `MEETSTREAM_API_KEY`. Always pass `--json --no-input`. Exit codes: 0 ok, 1 API error, 2 usage or not signed in, 3 not ready yet, 4 transcript failed. JSON shapes: `skills/meetstream/references/meetstream-cli.md`.

**Tell the user before the first bot:**
- **Someone must admit it.** The bot asks to join like a guest. The host (on Google Meet,
  the host or a co-host) admits it from the waiting room or lobby. It waits
  `automatic_leave.waiting_room_timeout` seconds (default 600 on Zoom and Google Meet,
  1200 on Teams), then ends as `NotAllowed`; `Denied` means a person declined it.
- **Zoom:** set up the user's Zoom app first (OBF or ZAK, below).
- **Platforms:** Zoom, Google Meet, Microsoft Teams, and WhatsApp calls (Beta: enabled per
  workspace, pair a number under Integrations > WhatsApp, `deepgram` post-call
  transcription only, no chat or per-participant files; `platform-setup`). Links from
  other services (Webex, Slack huddles and others) return 400; say they are not supported.

## Creating the bot

Ask for the meeting link if the user has not given one. Sensible defaults:

- `bot_name` - something recognisable to the humans in the call, e.g. "Acme Notetaker".
  Never leave this blank; a bot with no name looks like an intruder.
- `record_video` - default off. Turn it on only if the user explicitly asks for video,
  since it takes longer to process and transcripts, summaries and speaker timelines all
  work without it. On REST the field is `video_required`, which defaults to `false`;
  send `"video_required": false` explicitly anyway so the intent is visible.
- `video_layout` - only when video is on. Send `"speaker_view"` unless the user asks for
  grid or gallery view; the REST API defaults to `"grid_view"`. `"speaker_view"` and
  `"grid_view"` work on every platform. Google Meet and Teams also accept
  `"speaker_view_default"` / `"grid_view_default"` (the bot records the platform's own
  layout in the call as one finished file); Zoom returns 400 for them. It is ignored when
  video is off, and WhatsApp accepts only `"grid_view"`.
- `separate_video_streams` - leave unset. Per-participant video is opt-in only; set it
  only when the user explicitly asks for it. Per-participant audio is unaffected.
- Transcription provider - `meetstream` works on every account with no extra keys, so
  use it unless the user says they added their own Deepgram, AssemblyAI or Sarvam key in
  the MeetStream dashboard (then `deepgram` with model `nova-3` is a good English choice).
  A provider whose key is missing fails after the call with no transcript. See the
  `meeting-brief` skill for other languages and diarization.
- `bot_image_url` (REST) - a public `https://` PNG, JPEG, GIF or WebP URL. `http://` and
  `data:` URIs return 400.
- Zoom: the bot joins through the user's Zoom app with an OBF token (on behalf of a user
  in the meeting) or a ZAK token (a signed-in bot), the way Zoom asks Meeting SDK apps to
  join since 2 March 2026. Set it up once before the first Zoom bot (Meeting SDK app
  credentials under Integrations > Zoom, then `zoom.obf_url` or `zoom.zak_url` on REST):
  https://docs.meetstream.ai/guides/app-integrations/zoom-marketplace-app-setup and
  https://docs.meetstream.ai/guides/app-integrations/zoom-authenticated-bots
  (`platform-setup`).
- `storage_id` (REST) - one of the workspace's storage destinations from the dashboard
  (1-80 letters, numbers, `_` or `-`). Omit it for the default destination.

Before creating a bot, call **`list_bots`**: if a bot is already joining or in that
meeting, reuse its `bot_id` instead of sending a second one.

If `create_bot` fails:

| Error | What to do |
|---|---|
| `Low credits please recharge` (403) | Call the `top_up_link` tool and give the user its link (`https://app.meetstream.ai/billing`). Do not retry `create_bot` until they say they added credits. |
| 401 / not signed in | Sign in to the `meetstream` MCP server again (Cursor: Settings → MCP → Connect; Claude Code: `/mcp` → Authenticate; Codex: `codex mcp login meetstream`), then retry once. |
| 400 with a field message | Fix that one field and retry once. |
| 429 `rate_limit_exceeded` | Prepaid accounts may create 5 bots per minute and 50 per hour. Wait the `Retry-After` seconds, then retry once. |

`get_balance` can answer that the balance is not available here and give the billing
link. That is normal, not an error to debug: give the user `https://app.meetstream.ai/billing`
(or the `top_up_link` result) and go on.

If the user wants the bot to arrive at a future time, pass `join_at` as an ISO 8601
timestamp rather than sleeping and creating it later.

## Following the bot

Statuses (`get_bot_status`, REST `GET /bots/{bot_id}/status`):

- In progress: `Scheduled` · `Joining` · `InWaitingRoom` · `InMeeting` (Zoom may show
  `RecordingPermissionAllowed`) · `Leaving` · `MediaProcessing`.
- Ended in the meeting: `Stopped` · `Kicked`, then `MediaProcessing` → `Done`.
- Never got in (final): `NotAllowed` · `Denied` · `Failed` / `FAILED` · `Error` / `ERROR`.
- Other final: `Done` (post-call processing finished; fetch the transcript now) ·
  `MediaExpired` · `Cancelled`.

A polling app must stop on any final status, not wait for `Stopped`: between two polls a
bot can go `InMeeting` → `MediaProcessing` → `Done` and you never see `Stopped`. Poll every
5-10 seconds with a time cap, or use the webhooks (`bot.stopped`, `transcription.processed`,
`bot.done`). Never loop forever. `Recording` appears in the timeline and webhooks, not as
the stored status.

**Listing bots** (duplicate checks, dashboards): never page through the whole history.
Filter: `GET /api/v1/bots?status=InMeeting&platform=GMeet&from=2026-11-21&limit=50`
(`status`, `platform` = `GMeet` / `Zoom` / `Teams`, `from` / `to` dates, `custom_attr[key]`).
`limit` is at most 50 (above it the API returns 400); follow `nextCursor` by sending it
back as `cursor` while `hasNextPage` is true. For one bot per meeting, prefer a
`deduplication_key` on `create_bot`.

These mean the bot never got in, and you should say so plainly rather than polling
forever:

| Status | What actually happened | What to tell the user |
|---|---|---|
| `NotAllowed` | Sat in the waiting room until `waiting_room_timeout` ran out (on Zoom and Teams, also a meeting nobody started) | Nobody admitted the bot. Ask the host to watch for it by name and admit it, raise `automatic_leave.waiting_room_timeout` (Zoom up to 1200, Google Meet 600, Teams 1800), let guests in, or use a signed-in bot (`platform-setup`). Then send a new bot. |
| `Denied` | A host actively rejected it (on Zoom, also Zoom refusing the bot's account) | The host declined. Ask them to admit it next time; on Zoom check the meeting allows guests or join with `zoom.zak_url`. Nothing to retry automatically. |
| `Error` / `Failed` | The join failed or the session crashed | Check `ErrorReason` in `get_bot_detail`: `MeetingRestricted` (organization or invitees only) and `SignInRequired` (no anonymous guests) need a signed-in bot; `InvalidMeetingLink` needs the full join link. Otherwise create a fresh bot. |

Poll with a sensible interval (5-10s) and a cap. Do not busy-loop.

## While it is in the meeting

Commands (chat, image, raise hand, `send_command`, `update_mia`) need the bot to be
`InMeeting` first. Before admission they return 409 or 503 (`no command endpoint`). Wait for
the `bot.inmeeting` webhook or the `InMeeting` status, then send; retry a 503 two or three
times with a few seconds' pause, never in a tight loop.

- **`send_chat_message`** - post into the meeting chat, e.g. to announce the bot is
  recording. Good manners and often a legal requirement.
- **`send_image`** - show an image or GIF as the bot's video frame. The URL must be
  publicly reachable and resolve to a public address; MeetStream fetches it server side,
  so local paths, private hosts and `data:` URIs will not work.
- **Raise / lower hand** - with the MCP connected, call the `raise_hand` / `lower_hand`
  tool. From a terminal: `meetstream bots hand <bot_id> up --json --no-input`. With no MCP
  (or in app code), the bot can do it now with REST. Give the user (or run, when
  `MEETSTREAM_API_KEY` is set) this call, with the connect step only as a side note:
  ```bash
  curl -X POST "https://api.meetstream.ai/api/v1/bots/<bot_id>/send_command" \
    -H "Authorization: Token $MEETSTREAM_API_KEY" -H "Content-Type: application/json" \
    -d '{"command": "raise_hand"}'
  ```
  It is `POST /api/v1/bots/{bot_id}/send_command`
  with `{"command": "raise_hand"}` or `{"command": "lower_hand"}` (Google Meet, Zoom,
  Teams). The bot must be `InMeeting` or `Recording`, otherwise 409. Response:
  `{"status": "accepted", "bot_id": "...", "command": "raise_hand", "hand_raised": true}`,
  where `hand_raised` is the state read back from the meeting, not an echo. Repeats are
  no-ops. Allow up to 10 seconds. Bots outside the US region return 501. Guide:
  https://docs.meetstream.ai/guides/features/raise-lower-hand
- **`take_screenshot`** - capture the meeting (Google Meet and Teams; not Zoom bots that
  join through your own Zoom app), then `get_media_urls` with `kind: "screenshots"`.
- **`get_participants`** / **`get_chats`** - read who is present and what has been said in chat.

## Ending it

- **`remove_bot`** makes the bot leave now. Recorded data is kept. REST:
  `POST /api/v1/bots/{bot_id}/remove_bot` (GET also works). Every app that sends a bot
  calls it on shutdown or Ctrl-C, so the bot does not stay in the meeting.
- **`delete_bot_data`** permanently erases the recording and transcript. This is
  irreversible - always confirm with the user before calling it, and never call it
  speculatively.

## Getting the recording afterwards

Use **`get_transcript`** with the `bot_id`; it resolves the transcript for you.
For media files use **`get_media_urls`** (audio, video, per-participant streams,
screenshots).

If a transcript is not ready yet the tool will say so. Wait and retry a few times
rather than reporting failure. One exception: if the bot used a **streaming-only**
transcription provider, there is no post-call transcript at all and waiting will
never help - the transcript was delivered live during the meeting.

## Do not

- Do not invent endpoints or fields. The MCP tools are the API surface.
- Do not call `delete_bot_data` without explicit confirmation.
- Do not create a second bot for the same meeting because the first is slow to join;
  check its status first.

## Latest docs

- Create your first bot: https://docs.meetstream.ai/guides/get-started/create-your-first-bot
- Create Bot payload reference: https://docs.meetstream.ai/api-reference/create-bot-payload-reference
- Raise and lower hand: https://docs.meetstream.ai/guides/features/raise-lower-hand
- Automatic leave: https://docs.meetstream.ai/guides/features/automatic-leave-configuration
- Deduplication and idempotency: https://docs.meetstream.ai/guides/features/deduplication-idempotency-keys

For the latest details, fetch the page with `.md` appended, read https://docs.meetstream.ai/llms.txt, or connect the docs MCP server at https://docs.meetstream.ai/_mcp/server.
