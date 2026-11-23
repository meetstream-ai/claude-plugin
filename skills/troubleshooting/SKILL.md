---
name: troubleshooting
description: >
  Diagnose MeetStream errors and unexpected behaviour. Use when the user says
  "it's not working", "401", "403", "getting a 400", "409", "429", "507", "stuck
  on 202", "transcript never arrives", "duplicate bots", "the bot never joined",
  "rate limited", "Retry-After", or pastes an error from the API. Read this
  before guessing at a cause. Low credits: send the user to
  https://app.meetstream.ai/billing (top_up_link tool when connected); never
  retry in a loop. The balance is on the billing page; GET
  /api/v1/billing/balance (read only) may answer not available: expected, use
  the billing page. get_transcript 422 = the transcript run failed, with status and
  reason: final, do not retry; fix the cause (often the provider key) and
  re-run with POST /api/v1/bots/{bot_id}/transcribe. Polling loop hangs or
  waits for Stopped: the bot can go InMeeting -> MediaProcessing -> Done
  between polls; poll until a final status with a cap. Slow duplicate check:
  filter GET /bots (status, from, custom_attr, limit at most 50).
---

# Troubleshooting MeetStream

With the `meetstream` CLI, check the setup first: `meetstream auth status --json --no-input`
(key valid?), then `meetstream bots get <bot-id> --part detail --json --no-input` for one
bot. CLI exit codes: 1 API error (the JSON `error.message` is the API's), 2 usage or not
signed in, 3 not ready yet, 4 the transcript run failed (`transcript_failed` with the
reason). Run it with `npx -y @meetstream/cli` if it is not installed.

Most error responses are `{"message": "..."}`. Read it and show it to the user - it
usually names the exact problem. The bot data endpoints (audio, video, speaker timeline,
chats, participants, screenshots), `remove_bot`, `stop_status` and `/transcriptions`
also return `{"message": ...}`. In-meeting commands, the credit check and the
prepaid 429 still use `error`. Read `message`, then `error`, then the raw body.

## Status codes

| Code | Meaning | Action |
|---|---|---|
| `400` | Validation failed | Read `message`; fix the request. Never retry unchanged |
| `401` | **No** API key sent | The header is missing entirely |
| `403` | Key sent but **rejected**, or `Low credits please recharge` | Bad key: wrong, revoked or truncated. Low credits: give the user https://app.meetstream.ai/billing (and call the `top_up_link` tool when connected); never retry in a loop. The balance is on the billing page. `GET /api/v1/billing/balance` (read only) may answer "not available" or 404 on accounts where it is not on yet: expected, send the user to the billing page |
| `404` | Unknown `bot_id` / `transcript_id` / route | Check the id, and that it was not deleted |
| `422` | `get_transcript`: the transcript run failed. Body `{"message": "Transcript processing failed: <reason>", "transcript_status": "Failed", "transcript_id"}` | Final: never retry. Show the reason, fix it (often the provider key or its usage limit), then `POST /api/v1/bots/{bot_id}/transcribe` |
| `409` | Conflict | Same `deduplication_key` with a different meeting; same key still saving (`Retry-After: 2`, retry with the same key); or an in-meeting command (for example `raise_hand`) sent before the bot is in the meeting |
| `429` | Rate limited | Honour `Retry-After`, then back off. See below |
| `500` / `503` | Transient server error | Exponential backoff |
| **`202`** | **Not an error** - still processing | Poll again, with a cap |
| **`507`** | **Not an error** - idempotent replay | Treat as success |

`401` vs `403` is the most useful distinction in practice: 401 means your header never
made it (env var unset, header name typo), 403 means the key itself is bad.

## The two "not an error" codes

**202** - the resource exists but is not ready. Normal for transcripts and
per-participant streams. **But**: a bot that used a streaming-only provider returns 202
*forever*, because no post-call transcript will ever exist. Always cap retries and, on
timeout, say "this bot used a streaming provider, the transcript was delivered live"
rather than "the transcript failed".

**507** - you retried a `create_bot` with the same `Idempotency-Key` and got the
original bot back. No duplicate, no double charge. Accept `201` and `507` as success.

## Prepaid rate limit (429)

Prepaid (pay-as-you-go) accounts can create **5 bots per rolling minute and 50 per
rolling hour**; invoice accounts are not limited. Not counted: `join_at` 10+ minutes
ahead, calendar bots for meetings 10+ minutes away, the scheduled join itself, and
idempotent replays. Over the limit no bot is created:

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 37

{"error": "rate_limit_exceeded", "message": "...", "limit": 5, "window": "minute", "retry_after": 37}
```

Sleep `Retry-After` seconds and resend with the same `Idempotency-Key`. To schedule many
bots, set `join_at` 10 or more minutes ahead.

## Common validation errors

| `message` | Cause |
|---|---|
| `meeting_link is required.` | Sent `meeting_url` instead of `meeting_link` |
| `in_call_recording_timeout must be at least 600 seconds` | Below the 600s floor |
| `recording_permission_denied_timeout must not exceed 600 seconds` | Outside the 60-600 range (default 600) |
| streaming provider required | Set `live_transcription_required.webhook_url` without a `*_streaming` provider |
| `audio_required and video_required are both false, so the bot would record nothing. ...` | No recording and no other job (live stream, `realtime_endpoints`, `bot_message`, `agent_config_id`) |
| `video_separate_streams=true requires video_required=true for Google Meet and Microsoft Teams. ...` | Per-participant video on an audio-only Meet/Teams bot |
| `bot_image_url must be an https:// URL to a PNG, JPEG, GIF or WebP image; ...` | `http://`, `data:` or non-image URL |
| `invalid_meeting_link: this Zoom link has no meeting number, ...` | Zoom personal (`/my/`) or vanity link |
| `meeting_captions is not supported on Zoom. ...` | Bot uses your own Zoom app |
| `zoom.use_own_app must be true or false` / `zoom.zak_url and zoom.obf_url cannot be used with zoom.use_own_app set to false` | Bad Zoom join options |
| `storage_id must contain 1-80 letters, numbers, underscores or hyphens` | Bad `storage_id`; an unknown ID returns the storage error text |
| `SmallestAPIKey not configured in user profile` / `Invalid smallest model: ...` | Smallest AI key missing, or a model other than `pulse` / `pulse-pro` (`pulse` / `pulse-2` for `smallest_streaming`) |
| `bot_camera_stream ...` | Camera stream on an unsupported platform, `ws://` on Teams/Zoom, or with `agent_config_id` on Zoom |
| `Anthropic models do not support: ...` (MIA) | `top_p`, penalties or `logit_bias` with `model.provider: "anthropic"` |

## "Nothing arrives, and there was no 400"

Webhooks from post-call processing, image URLs the bot downloads (`bot_image_url`,
send-image URLs, `initial_audio.url`) and `bot_camera_stream` signaling hosts must
resolve to **public addresses**. A URL that resolves to a private, loopback or metadata
address is refused at delivery or download time. Use a public host, or a tunnel (ngrok,
cloudflared) for local development.

## "The bot never joined"

Check the terminal webhook's `bot_event` (every ending arrives as `event: "bot.stopped"`),
not the HTTP response:

- `bot.notallowed` (status `NotAllowed`) - nobody admitted it before
  `automatic_leave.waiting_room_timeout` ran out (default 600 seconds on Zoom and Google
  Meet, 1200 on Teams; on Zoom and Teams also a meeting nobody started). Fix: ask the
  host (on Google Meet, the host or a co-host) to watch for the bot by its name and admit
  it, let guests in (Teams: "Who can bypass the lobby" set to Everyone), raise the
  timeout, or use a signed-in bot (`platform-setup`). Then send a new bot.
- `bot.denied` (status `Denied`) - a person declined it (on Zoom, also Zoom refusing the
  bot's account). Ask the host to admit it next time; on Zoom join with `zoom.zak_url` as
  an allowed user. Do not auto-retry.
- Zoom `Unable to join external meeting` - the meeting is outside your Zoom app's account:
  join with `zoom.obf_url` or `zoom.zak_url` (`platform-setup`).
- `bot.kicked` - a participant removed it.
- `bot.failed` - read `ErrorReason`: `MeetingRestricted` (organization or invitees only),
  `SignInRequired` (no anonymous guests), `InvalidMeetingLink` (bad link). Use a
  signed-in bot or fix the link; otherwise create a fresh one. See `platform-setup`.

Without webhooks, `get_bot_status` shows `NotAllowed`, `Denied` or `Error`.

If there was no `bot.stopped` at all and no events ever arrived, the problem is your
webhook, not the bot. See the `webhooks` skill.

## "The transcript never arrives"

In order:

1. Did `transcription.processed` fire? If `transcription.failed` fired instead (or
   `get_transcript` returns 422), read the `message` - most often the provider rejected
   the API key or its usage limit was reached. Do not retry the fetch: fix the key, then
   start a new run with `POST /api/v1/bots/{bot_id}/transcribe`.
2. Right identifier? The MCP `get_transcript` tool takes the **`bot_id`**. The REST
   endpoint takes the **`transcript_id`**, not the `bot_id`.
3. Are you reading the right fields? By default the speaker is `participant.name` and the
   text is `words[].text` joined; only some providers return `speaker` / `transcript`.
   Reading the wrong format looks like an empty transcript. Check one real response with
   the MCP `get_transcript` tool (or `curl`) before you change the parser.
4. Was it a streaming-only provider? Then there is no post-call transcript. Use
   `transcribe_audio` to generate one from the stored audio.

## "The agent in the meeting is silent"

First find which build track the bot uses (track 1, the recording bot, has no agent):

- **Track 2, bridge server** (the bot has `live_audio_required` and
  `socket_connection_url`, no `agent_config_id`): both `wss://` URLs must be public (a
  tunnel for local development) and on your server; check that both sockets got the
  `ready` handshake. Send `resume_audio` before the first `sendaudio` of each reply: on
  Zoom and Teams audio stays held after an `interrupt` until you do. Google Meet plays
  `sendaudio` at 48 kHz only. Docs:
  https://docs.meetstream.ai/guides/websockets/bridge-server-architecture
- **Track 3d, your coding agent as the brain** (`model.provider: "local_agent"`, set up
  with `meetstream setup`): COMING SOON, not in production. Do not debug it as a working setup or give setup steps; offer track 2 or
  track 3a/3c. The `check_local_agent` MCP tool belongs to this coming-soon track only.
- **Track 3, hosted agent** (3a or 3c, `agent_config_id`): the bot must carry only
  `agent_config_id`. `socket_connection_url` or `live_audio_required` on the same bot is
  the usual cause of a silent agent: remove them (a bridge is a separate bot). Then check
  the wake word: pipeline agents have a wake word on by default (`"hey assistant"`,
  `"hello bot"`), so an agent that greets and then ignores questions needs
  `"wake_word": {"enabled": false}` (or the user says the wake word). Then
  `speak_only_when_asked`, and the keys: `MeetStream-managed keys are not
  available` means inbuilt keys are not on for the account yet, so use your own provider
  keys (3c); never retry in a loop. With the MCP connected, read the saved config with
  `get_agent` (or `list_agents`) and fix it with `update_agent`; `take_screenshot` shows
  what the bot sees (Google Meet and Teams). Details: `mia-voice-agents`.
- **Creating the agent fails** with `400` `Missing model.system_prompt.`: add a
  `system_prompt` to `model` (required for every agent except `local_agent`).

## "My polling loop hangs" or "the duplicate check takes minutes"

- Do not wait for `Stopped`. Between two polls the bot can go `InMeeting` →
  `MediaProcessing` → `Done`, so `Stopped` is never seen. Stop on any final status:
  `Done`, `NotAllowed`, `Denied`, `Failed` / `FAILED`, `Error` / `ERROR`, `MediaExpired`,
  `Cancelled` (in progress: `Scheduled`, `Joining`, `InWaitingRoom`, `InMeeting`,
  `Leaving`, `MediaProcessing`). Fetch the transcript at `Done`. Always cap the loop, or
  use the webhooks (`transcription.processed`, `bot.done`).
- Do not page through every bot to find a duplicate. Filter the list:
  `GET /api/v1/bots?status=InMeeting&from=2026-11-21&limit=50` (also `platform`,
  `custom_attr[key]`); `limit` is at most 50 (400 above); follow `nextCursor` as `cursor`.
  Better: send a `deduplication_key` (one bot per meeting) and an `Idempotency-Key`.

## "I'm getting duplicate bots"

You are retrying `create_bot` without an `Idempotency-Key`. Add one - generate the UUID
**once, outside** the retry loop, and persist it with the job so a redelivered queue
message reuses it. Generating a fresh UUID per attempt defeats the entire mechanism.

For "one bot per calendar event", use `deduplication_key` in the body instead.

## Verifying the basics

Ask the agent to call the **`list_bots`** MCP tool. If that returns cleanly, the key and
connection are fine and the problem is in the specific request. If it 401s or 403s, fix
auth first.

Auth differs by surface, which trips people up:
- **REST API** (`api.meetstream.ai`): `Authorization: Token <key>`
- **MCP server** (`mcp.meetstream.ai`): `Authorization: Bearer <key>`

Keys come from https://app.meetstream.ai/api-key.

## Latest docs

- Errors: https://docs.meetstream.ai/errors
- Bot statuses and error codes: https://docs.meetstream.ai/guides/reference/bot-status-and-error-codes
- Debugging bots: https://docs.meetstream.ai/guides/help/debugging-bots
- Authentication: https://docs.meetstream.ai/api-reference/authentication
- FAQ: https://docs.meetstream.ai/guides/help/faq

For the latest details, fetch the page with `.md` appended, read https://docs.meetstream.ai/llms.txt, or connect the docs MCP server at https://docs.meetstream.ai/_mcp/server.
