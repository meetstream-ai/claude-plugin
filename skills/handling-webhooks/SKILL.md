---
name: handling-webhooks
description: >
  Handle MeetStream webhooks correctly - the full event lifecycle, signature
  verification, redelivery, and local tunnels. Use when the user says "webhook",
  "callback_url", "bot events", "how do I know when the meeting ended", "my
  webhook isn't firing", "verify the signature", "ngrok", or is writing any
  handler that reacts to bot state (formerly the webhooks skill). Read this before
  writing a webhook handler. Route on bot_event, fall back to event; one delivery, no
  retry: reply 2xx fast and poll as the fallback.
  Signed deliveries (workspace endpoints only; callback_url is unsigned) carry
  X-MeetStream-Signature: sha256=<hex> (HMAC-SHA256 of the raw body with the
  endpoint secret) and X-MeetStream-Timestamp, an ISO 8601 UTC time such as
  2026-11-19T14:30:00Z, not a number.
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

Route on **`bot_event`** and fall back to **`event`**:
`name = payload.get("bot_event") or payload.get("event")`. `bot_event` is on lifecycle events,
the five endings, `bot.joining`, `bot.scheduled`, `bot.error`, `audio.*`, `transcription.*`,
`video.*`, `bot.done`, `manifest.*` and `data_deletion`. It is **missing** on
`participant_events.*` (the bot id is at `data.bot.id`, not top level), `agent_error`,
`usage.*`, `bot.uploading`, and every dashboard resend. A resend is rebuilt from the log:
`{"event": "bot.kicked", "status": "Stopped", ...}`, so `event` holds the specific name and the
field is `status`, not `bot_status`. Live transcript POSTs carry neither `event` nor `bot_event`.
Every lifecycle event carries a `timestamp`.

**Two ways to receive events:**

- **Workspace webhook endpoints** (dashboard): one URL for every bot in the workspace, signed,
  with a per-endpoint secret shown once at creation. Recommended for production.
  https://docs.meetstream.ai/guides/webhooks/workspace-webhooks
- **Per-bot `callback_url`** on `create_bot`: never signed. If it is the same URL as an active
  workspace endpoint that subscribes to the event, the event goes once, signed.

**Delivery:** one attempt per target, no automatic retry; a failure is only logged, and the user
can resend from the dashboard (up to 10 times). Bots in a regional execution cell (outside the
US) retry through a queue, up to 6 attempts, so an event can arrive more than once. Delivery is
sequential per bot: a slow endpoint delays the next events for that bot. MeetStream waits at
least 5 seconds (10 on most events). So: reply 2xx within 5 seconds, queue the work, dedupe, and
poll `GET /bots/{bot_id}/status` for any bot whose ending you have not seen (for example one that
stays `Joining` or `Scheduled`).

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

**Participant hand events** (`participant_events.raise_hand` / `participant_events.lower_hand`,
Google Meet and Zoom) are opt-in per bot: list them in
`recording_config.realtime_endpoints[].events` on the REST `create_bot`. They go **only**
to those endpoints, never to `callback_url` or workspace webhooks. Same nested shape as
`participant_events.join` (`data.data.action` is `raise_hand` / `lower_hand`, bot id at
`data.bot.id`). Transitions only; the bot's own hand is never reported; a participant who
leaves with a hand up gets no `lower_hand`.

A `bot.failed` terminal carries a reason in `bot_details.ErrorReason` (and, on Google
Meet, `failure_reason` in the webhook), for example `MeetingRestricted` /
`meeting_restricted`, `SignInRequired` / `sign_in_required` or `InvalidMeetingLink`.
See the `setting-up-platforms` skill.

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
- **Deduplicate.** Key on `bot_id` + (`bot_event` or `event`) + `timestamp`.
- **Capture the raw body before JSON parsing** if you plan to verify signatures -
  re-serializing the parsed object will not match the signature.
- **Do not assume ordering.** Treat lifecycle states as a forward-only ladder and
  ignore anything that moves backwards.

## Signature verification

Only workspace endpoints are signed. Per-bot `callback_url` deliveries and live transcript
POSTs are **never** signed; `recording_config.realtime_endpoints` are signed only on Google Meet
(with the secret of the account's first enabled workspace endpoint), unsigned on Zoom and Teams.
The timestamp header is a copy of the body's `timestamp`, which the HMAC covers. Verify when you are on a workspace endpoint, and when
you are not, protect the route another way: a secret path segment, an allowlist, or a
shared token in the query string. Never treat an unauthenticated public webhook route
as trusted input.

**Token pattern for unsigned URLs (`callback_url`, live transcript URL).** Use one env var,
`MEETSTREAM_WEBHOOK_SECRET`. When you create the bot, append `?token=<secret>` to each URL.
In the handler, compare the `token` query value with `hmac.compare_digest`, answer `200`
either way (so MeetStream does not see errors), and process only matching requests. When
the variable is **unset**, process every request and log one warning at startup
("MEETSTREAM_WEBHOOK_SECRET not set: webhook URLs are unauthenticated"). That keeps a local
test (`meetstream mock`, `meetstream trigger`) working; set the secret before the URL is public.
Also check that `bot_id` is one of your bots.

```python
SECRET = os.environ.get("MEETSTREAM_WEBHOOK_SECRET", "")
def authorized(path: str) -> bool:
    if not SECRET:
        return True  # local development; warned at startup
    token = parse_qs(urlsplit(path).query).get("token", [""])[0]
    return hmac.compare_digest(token, SECRET)
```

Signed requests carry two headers:

| Header | Value |
|---|---|
| `X-MeetStream-Signature` | `sha256=<hex>`: HMAC-SHA256 of the raw request body, keyed with the endpoint's signing secret |
| `X-MeetStream-Timestamp` | The send time as an ISO 8601 UTC string, for example `2026-11-19T14:30:00Z`. It is not a Unix number |

```python
import hashlib, hmac
from datetime import datetime, timezone

def verify(raw_body: bytes, headers, secret: str, max_age_s: int = 300) -> bool:
    sig = headers.get("X-MeetStream-Signature", "").removeprefix("sha256=")
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return False
    ts = headers.get("X-MeetStream-Timestamp")
    if ts:  # replay check: parse the ISO 8601 time
        sent = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if abs((datetime.now(timezone.utc) - sent).total_seconds()) > max_age_s:
            return False
    return True
```

## Local development

`callback_url` must be a **public HTTPS URL** that resolves to a public address.
Localhost will never receive anything. Post-call webhooks (`audio.processed`,
`transcription.*`, `video.processed` and the rest) are delivered only to public
addresses, on every redirect hop; a URL that resolves to a private, loopback or metadata
address is dropped. Every delivery sends `User-Agent: MeetStream-Webhook/1.0`.

```bash
ngrok http 3000          # then use the https URL + your path
cloudflared tunnel --url http://localhost:3000
```

No server yet? `meetstream listen --json` (the `meetstream` CLI; `npx -y @meetstream/cli
listen --json` with no install) receives on `127.0.0.1:3333/webhook` and prints one JSON
line per event; point the tunnel at port 3333.

Two failure modes to check before debugging your code:
- The tunnel returns an interstitial page and MeetStream sees a 200 that never reached
  your handler. Verify with a request that echoes a value your handler generated.
- The URL is `http`, not `https`.

Full lifecycle paths, terminal events, `ErrorReason` values and payload fields:
[`references/lifecycle-and-payloads.md`](references/lifecycle-and-payloads.md). The generated
event model is `skills/meetstream/references/generated/events.md`.

## Quick triage

| Symptom | Likely cause |
|---|---|
| No events at all | `callback_url` not public HTTPS, resolves to a private address, or not set on that bot |
| No hand events | `participant_events.raise_hand` / `.lower_hand` not listed in `realtime_endpoints`; they never reach `callback_url` |
| No `transcription.processed` | Streaming-only provider: the transcript was live, there is no post-call one |
| Kicks treated as normal exits | Branching on `bot_status` instead of `bot_event` |
| Bot never joined | `bot.stopped` with `bot_event` `bot.notallowed` or `bot.denied` |
| Duplicate processing | No dedupe key, or a slow handler |

## Latest docs

- Webhooks and events: https://docs.meetstream.ai/guides/webhooks/webhooks-and-events
- Webhook signature verification: https://docs.meetstream.ai/guides/webhooks/webhook-signature-verification
- Workspace webhook endpoints: https://docs.meetstream.ai/guides/webhooks/workspace-webhooks
- Local webhook server (tunnels): https://docs.meetstream.ai/guides/webhooks/local-webhook-server

For the latest details, fetch the page with `.md` appended, read https://docs.meetstream.ai/llms.txt, or connect the docs MCP server at https://docs.meetstream.ai/_mcp/server.
