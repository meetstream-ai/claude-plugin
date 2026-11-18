---
name: webhooks
description: >
  Handle MeetStream webhooks correctly - the full event lifecycle, signature
  verification, redelivery, and local tunnels. Use when the user says
  "webhook", "callback_url", "bot events", "how do I know when the meeting
  ended", "my webhook isn't firing", "verify the signature", "ngrok", or is
  writing any handler that reacts to bot state. Read this before writing a
  webhook handler.
---

# MeetStream webhooks

Call the **`webhook_events_guide`** MCP tool for the full event reference before writing
a handler. This skill covers the traps.

## The envelope

```json
{ "event": "bot.stopped", "bot_event": "bot.notallowed", "bot_id": "...",
  "bot_status": "NotAllowed", "message": "Failed: Not admitted to meeting",
  "status_code": 500, "timestamp": "...", "custom_attributes": {} }
```

Every delivery carries the event name under **`event`**. Most also carry **`bot_event`**
with the specific name. Route on `event`; read `bot_event` when you need the detail.
Every event, lifecycle ones included, carries a `timestamp`.

There is no global webhook endpoint. You set `callback_url` **per bot** on `create_bot`.

## The lifecycle

```
bot.joining -> bot.in_waiting_room -> bot.inmeeting -> bot.recording
            -> bot.leaving -> bot.stopped          (terminal, see below)
            -> manifest.completed -> audio.processed
            -> transcription.processed | transcription.failed | transcription.skipped
            -> video.processed -> bot.done -> data_deletion
```

You may also see `bot.scheduled`, `bot.uploading`, `bot.transcriptionready`,
`audio.skipped`, `manifest.skipped` and `participant_events.join` / `.leave`. On Zoom,
`bot.recording_permission_allowed` / `_denied` can fire before `bot.recording`.

Four things that break handlers:

1. **Terminals are two-layer.** Every ending arrives once with `event: "bot.stopped"`.
   `bot_event` says why:

   | `bot_event` | Meaning | `status_code` |
   |---|---|---|
   | `bot.stopped` | Clean exit | 200 |
   | `bot.kicked` | A participant removed the bot | 200 |
   | `bot.notallowed` | Waiting-room timeout, nobody admitted it | 500 |
   | `bot.denied` | A host refused entry | 500 |
   | `bot.failed` | Unexpected error | usually 500 |

   Branch on `bot_event`, not `bot_status`: a kick and a clean exit both report
   `bot_status: "Stopped"`, and failure statuses arrive as `FAILED`, `Failed` or `ERROR`.
2. **Do not read `status_code: 200` as success of the whole meeting.** A kicked bot
   sends 200. Check `bot_event`.
3. **Streaming-only providers produce no post-call transcript.** No
   `transcription.processed` fires, but `bot.done` still does. Do not wait on a
   transcript for those bots.
4. **`transcript_id` is not in any webhook.** Get it from the `create_bot` response or
   `get_bot_detail`, or let the `get_transcript` tool resolve it from the `bot_id`.

## Writing the handler

- **Return 2xx fast.** Acknowledge, then do the real work asynchronously.
- **Deduplicate.** Key on `bot_id` + `event` + `bot_event` + `timestamp`.
- **Capture the raw body before JSON parsing** if you plan to verify signatures -
  re-serializing the parsed object will not match the signature.
- **Do not assume ordering.** Treat lifecycle states as a forward-only ladder and
  ignore anything that moves backwards.

## Signature verification

Per-bot `callback_url` deliveries are **unsigned**; workspace-level endpoints are
signed with an HMAC signature. Verify when you are on a workspace endpoint, and when
you are not, protect the route another way: a secret path segment, an allowlist, or a
shared token in the query string. Never treat an unauthenticated public webhook route
as trusted input.

## Local development

`callback_url` must be a **public HTTPS URL**. Localhost will never receive anything.

```bash
ngrok http 3000          # then use the https URL + your path
cloudflared tunnel --url http://localhost:3000
```

Two failure modes to check before debugging your code:
- The tunnel returns an interstitial page and MeetStream sees a 200 that never reached
  your handler. Verify with a request that echoes a value your handler generated.
- The URL is `http`, not `https`.

## Quick triage

| Symptom | Likely cause |
|---|---|
| No events at all | `callback_url` not public HTTPS, or not set on that bot |
| No `transcription.processed` | Streaming-only provider: the transcript was live, there is no post-call one |
| Kicks treated as normal exits | Branching on `bot_status` instead of `bot_event` |
| Bot never joined | `bot.stopped` with `bot_event` `bot.notallowed` or `bot.denied` |
| Duplicate processing | No dedupe key, or a slow handler |

## Reference

- [Webhooks and events](https://docs.meetstream.ai/guides/webhooks/webhooks-and-events)
- [Webhook signature verification](https://docs.meetstream.ai/guides/webhooks/webhook-signature-verification)
- [Local webhook server](https://docs.meetstream.ai/guides/webhooks/local-webhook-server)
- [Workspace webhooks](https://docs.meetstream.ai/guides/webhooks/workspace-webhooks)
- [Errors](https://docs.meetstream.ai/errors)
