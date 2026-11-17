---
name: troubleshooting
description: >
  Diagnose MeetStream errors and unexpected behaviour. Use when the user says
  "it's not working", "401", "403", "getting a 400", "429", "507", "stuck on
  202", "transcript never arrives", "duplicate bots", "the bot never joined",
  "rate limited", or pastes an error from the API. Read this before guessing
  at a cause.
---

# Troubleshooting MeetStream

Every error response carries a `message` field. Read it and show it to the user -
it usually names the exact problem.

## Status codes

| Code | Meaning | Action |
|---|---|---|
| `400` | Validation failed | Read `message`; fix the request. Never retry unchanged |
| `401` | **No** API key sent | The header is missing entirely |
| `403` | Key sent but **rejected** | Wrong, revoked, or truncated key |
| `404` | Unknown `bot_id` / `transcript_id` / route | Check the id, and that it was not deleted |
| `409` | Deduplication conflict | Same `deduplication_key`, different meeting |
| `429` | Rate limited | Honour `Retry-After`, then back off |
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

## Common validation errors

| `message` | Cause |
|---|---|
| `meeting_link is required.` | Sent `meeting_url` instead of `meeting_link` |
| `in_call_recording_timeout must be at least 600 seconds` | Below the 600s floor |
| `recording_permission_denied_timeout must not exceed 300 seconds` | Outside the 60-300 range |
| streaming provider required | Set `live_transcription_required.webhook_url` without a `*_streaming` provider |

## "The bot never joined"

Check the terminal webhook's `bot_event` (every ending arrives as `event: "bot.stopped"`),
not the HTTP response:

- `bot.notallowed` - waiting-room timeout. Nobody let it in.
- `bot.denied` - a host refused it.
- `bot.kicked` - a participant removed it.
- `bot.failed` - it crashed; create a fresh one.

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
