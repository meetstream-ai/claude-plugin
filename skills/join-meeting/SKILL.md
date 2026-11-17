---
name: join-meeting
description: >
  Send a MeetStream bot into a live Zoom, Google Meet or Microsoft Teams
  meeting and follow it until it leaves. Use when the user says "join this
  meeting", "send a bot to <meeting url>", "record this call", "have the bot
  take notes on this meeting", "get a transcript of this meeting", "make the
  bot leave", or pastes a meeting link and asks for anything to happen to it.
  Covers create, status, live chat, and removal using the MeetStream MCP tools.
---

# Join a meeting with a MeetStream bot

You have the MeetStream MCP server connected. Use its tools directly. Do not
write API client code unless the user explicitly asks for a script.

## The short path

1. **`create_bot`** with `meeting_link` and a `bot_name`.
2. **`get_bot_status`** to follow it (`Joining` -> `InWaitingRoom` -> `InMeeting` -> `Recording`).
3. When the meeting ends, **`get_transcript`** with the `bot_id`.

That is the whole flow. Everything below is detail you need when it is not that simple.

## Creating the bot

Ask for the meeting link if the user has not given one. Sensible defaults:

- `bot_name` - something recognisable to the humans in the call, e.g. "Acme Notetaker".
  Never leave this blank; a bot with no name looks like an intruder.
- `record_video` - default off. Turn it on only if the user explicitly asks for video,
  since it takes longer to process and transcripts, summaries and speaker timelines all
  work without it. On REST the field is `video_required`, which defaults to `true`, so
  send `"video_required": false` explicitly.
- `video_layout` - only when video is on. Send `"speaker_view"` unless the user asks for
  grid or gallery view; the REST API defaults to `"grid_view"`. Those two are the only
  valid values, it is ignored when video is off, and WhatsApp accepts only `"grid_view"`.
- `separate_video_streams` - leave unset. Per-participant video is opt-in only; set it
  only when the user explicitly asks for it. Per-participant audio is unaffected.
- Transcription provider - `meetstream` works on every account with no extra keys, so
  use it unless the user says they added their own Deepgram, AssemblyAI or Sarvam key in
  the MeetStream dashboard (then `deepgram` with model `nova-3` is a good English choice).
  A provider whose key is missing fails after the call with no transcript. See the
  `meeting-brief` skill for other languages and diarization.

Before creating a bot, call **`list_bots`**: if a bot is already joining or in that
meeting, reuse its `bot_id` instead of sending a second one.

If `create_bot` fails:

| Error | What to do |
|---|---|
| `Low credits please recharge` (403) | Call `top_up_link` if the server has it, else send the user to `https://app.meetstream.ai/billing`. Do not retry. |
| 401 / not signed in | Sign in to the `meetstream` MCP server again (Cursor: Settings → MCP → Connect; Claude Code: `/mcp` → Authenticate; Codex: `codex mcp login meetstream`), then retry once. |
| 400 with a field message | Fix that one field and retry once. |

If the user wants the bot to arrive at a future time, pass `join_at` as an ISO 8601
timestamp rather than sleeping and creating it later.

## Following the bot

`get_bot_status` returns one of:

`Joining` · `InWaitingRoom` · `InMeeting` · `Recording` · `Leaving` · `Stopped` ·
`NotAllowed` · `Denied` · `Error` · `Done`

Three of those mean the bot never got in, and you should say so plainly rather than
polling forever:

| Status | What actually happened | What to tell the user |
|---|---|---|
| `NotAllowed` | Sat in the waiting room until it timed out | Nobody admitted the bot. Ask a participant to let it in, or raise the waiting-room timeout. |
| `Denied` | A host actively rejected it | The host declined. Nothing to retry automatically. |
| `Error` | The session crashed | Safe to create a fresh bot. |

Poll with a sensible interval (5-10s) and a cap. Do not busy-loop.

## While it is in the meeting

- **`send_chat_message`** - post into the meeting chat, e.g. to announce the bot is
  recording. Good manners and often a legal requirement.
- **`send_image`** - show an image or GIF as the bot's video frame. The URL must be
  publicly reachable; MeetStream fetches it server side, so local paths and
  `data:` URIs will not work.
- **`get_participants`** / **`get_chats`** - read who is present and what has been said in chat.

## Ending it

- **`remove_bot`** makes the bot leave now. Recorded data is kept.
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

## Reference

- [Create your first bot](https://docs.meetstream.ai/guides/get-started/create-your-first-bot)
- [How bots work](https://docs.meetstream.ai/guides/introduction/how-bots-work)
- [create_bot API](https://docs.meetstream.ai/api-reference/api-endpoints/bot-endpoints/create-bot)
- [Automatic leave configuration](https://docs.meetstream.ai/guides/features/automatic-leave-configuration)
- [Deduplication and idempotency keys](https://docs.meetstream.ai/guides/features/deduplication-idempotency-keys)
- [Custom attributes](https://docs.meetstream.ai/guides/features/custom-attributes)
