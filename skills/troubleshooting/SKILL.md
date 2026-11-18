---
name: troubleshooting
description: >
  Diagnose MeetStream errors and unexpected behaviour. Use when the user says
  "it's not working", "401", "403", "getting a 400", "409", "429", "507", "stuck on
  202", "transcript never arrives", "duplicate bots", "the bot never joined",
  "rate limited", "Retry-After", or pastes an error from the API. Read this before guessing
  at a cause.
---

# Troubleshooting MeetStream

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
| `403` | Key sent but **rejected**, or `Low credits please recharge` | Bad key: wrong, revoked or truncated. Low credits: call the `top_up_link` tool (or send the user to https://app.meetstream.ai/billing); never retry in a loop |
| `404` | Unknown `bot_id` / `transcript_id` / route | Check the id, and that it was not deleted |
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

- `bot.notallowed` - waiting-room timeout. Nobody let it in.
- `bot.denied` - a host refused it.
- `bot.kicked` - a participant removed it.
- `bot.failed` - read `ErrorReason`: `MeetingRestricted` (organization or invitees only),
  `SignInRequired` (no anonymous guests), `InvalidMeetingLink` (bad link). Use a
  signed-in bot or fix the link; otherwise create a fresh one. See `platform-setup`.

Without webhooks, `get_bot_status` shows `NotAllowed`, `Denied` or `Error`.

If there was no `bot.stopped` at all and no events ever arrived, the problem is your
webhook, not the bot. See the `webhooks` skill.

## "The transcript never arrives"

In order:

1. Did `transcription.processed` fire? If `transcription.failed` fired instead, read its
   `message` - most often a provider API key issue on your account.
2. Right identifier? The MCP `get_transcript` tool takes the **`bot_id`**. The REST
   endpoint takes the **`transcript_id`**, not the `bot_id`.
3. Are you reading `segment.transcript`, not `segment.text`? Wrong field looks like an
   empty transcript.
4. Was it a streaming-only provider? Then there is no post-call transcript. Use
   `transcribe_audio` to generate one from the stored audio.

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

## Reference

- [Errors](https://docs.meetstream.ai/errors)
- [Debugging bots](https://docs.meetstream.ai/guides/help/debugging-bots)
- [FAQ](https://docs.meetstream.ai/guides/help/faq) · [Support](https://docs.meetstream.ai/guides/help/support)
- [Authentication](https://docs.meetstream.ai/api-reference/authentication)
