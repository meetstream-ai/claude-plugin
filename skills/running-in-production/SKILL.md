---
name: running-in-production
description: >
  Build MeetStream into your own SaaS so bots join your customers' meetings
  and the recordings and transcripts land in your app, per customer
  (multi-tenant). Use when the user says "our SaaS needs recording and
  transcripts", "bots joining our customers' calls", "per customer", "per
  tenant", "white-label notetaker", "our CRM schedules a bot for each client
  meeting", or "at scale". Covers: tag every bot with the tenant in
  custom_attributes and route webhooks on it (per-bot callback_url or signed
  workspace webhooks), list bots per tenant, one calendar connection per end
  user (create_calendar), a storage destination per customer (storage_id),
  per-speaker audio for your own transcription, Zoom for customer meetings
  (your Zoom app with OBF or ZAK), and scale: 429 with Retry-After, join_at
  10+ minutes ahead, Idempotency-Key and deduplication_key; retention
  (permanent unless set), usage, storage per provider, workspaces and key
  rotation. Bot API only; no voice agent unless asked. Formerly
  for-your-customers.
---

# Running in production (and for your customers)

Your product sends MeetStream bots into your customers' meetings and keeps each
customer's recordings and transcripts apart. This is the Recording bot (track 1, the Bot API): the same
`create_bot`, webhooks and transcript calls as a notetaker, plus a tenant tag on every
bot. Do not add a voice agent unless the user asks for one.

## Fastest path

1. **Tag every bot with the tenant.** Put your ids in `custom_attributes` (string values).
   MeetStream echoes them on every lifecycle and post-call webhook, on status and detail
   responses, and in the Usage dashboard.
   ```bash
   curl -X POST https://api.meetstream.ai/api/v1/bots/create_bot \
     -H "Authorization: Token $MEETSTREAM_API_KEY" -H "Content-Type: application/json" \
     -H "Idempotency-Key: meeting-sync-1234" \
     -d '{"meeting_link": "https://meet.google.com/abc-defg-hij", "bot_name": "Acme Notetaker",
          "video_required": false,
          "callback_url": "https://api.your-saas.example/meetstream/webhook",
          "custom_attributes": {"tenant_id": "cus_8842", "user_id": "u_17"},
          "deduplication_key": "cus_8842:event_5521",
          "recording_config": {"transcript": {"provider": {"meetstream": {"language": "auto"}}}}}'
   ```
   Node: `await ms.bots.create({ meeting_link, bot_name, callback_url, custom_attributes: { tenant_id } })`.
   Python: `ms.bots.create({"meeting_link": link, "callback_url": url, "custom_attributes": {"tenant_id": tid}})`.
2. **Route webhooks on the tag.** Either a per-bot `callback_url` (unsigned, every event
   for that bot) or workspace webhook endpoints in the dashboard under Configure >
   Webhooks (signed with `X-MeetStream-Signature` and `X-MeetStream-Timestamp`, pick the
   events, up to 10 endpoints). Both carry `custom_attributes`, so the handler dispatches
   on `tenant_id` with no lookup. Return 2xx at once and queue the work (`handling-webhooks`).
3. **Fetch per tenant.** On `transcription.processed`, fetch the transcript
   (`building-a-notetaker` steps 2-3). List a tenant's bots with
   `GET /api/v1/bots?custom_attr[tenant_id]=cus_8842`.

## Per-customer pieces

- **Calendar per end user.** Run the Google consent flow in your product, then connect
  each user's account with `POST /api/v1/calendar/create_calendar`
  (`google_client_id`, `google_client_secret`, `google_refresh_token`). Each call
  connects one account; scope later calls with `?provider=google&account_id=<email>`.
  Outlook has its own create endpoint. Auto-scheduling and recurring events:
  `scheduling-and-calendars`.
- **Storage per customer.** Save a storage destination per customer in the dashboard
  (Integrations > Storage: Amazon S3, Cloudflare R2, Alibaba Cloud OSS), then send its
  `storage_id` on `create_bot`. Omit it for the default destination. `write_only` mode
  keeps MeetStream from reading the files back (fetch endpoints return 403).
- **Per-speaker audio for your own transcription.** `audio_separate_streams: true`, then
  after `audio.processed` call `GET /api/v1/bots/{bot_id}/get_audio_streams` (one file
  per speaker, up to 16; links last 1 hour) (`getting-transcripts-and-media`). Or save your own
  transcription provider key in the dashboard and pick that provider.
- **Zoom meetings of your customers.** Recommend your own Zoom app for reliable, fully supported
  Zoom bots. For meetings outside your app's own Zoom account, Zoom requires a reviewed app and
  an OBF token (on behalf of your user who is in the meeting) or a ZAK token. Many Zoom apps and
  users: https://docs.meetstream.ai/guides/app-integrations/zoom-oauth-meeting-bots
  (`setting-up-platforms`). The no-app join is a limited US-only fallback (no OBF or ZAK).
- **Environments.** Use separate workspaces (each with its own API keys, bots, webhooks
  and usage) for staging and production. Keys start with `ms_`, belong to one workspace and live
  in your secret store. Rotate by creating the new key, rolling it out, then revoking the old one
  (revocation is immediate).

## Scale

- Prepaid accounts can create 5 bots per minute and 50 per hour. Over the limit, the API
  returns 429 with a `Retry-After` header and `retry_after` in the body: wait that many
  seconds, then retry. Bots scheduled with `join_at` 10 or more minutes ahead (and
  calendar bots for meetings 10 or more minutes away) do not count. Invoice-billed
  accounts are not limited; ask support for higher limits.
- Make retries safe: the `Idempotency-Key` header for the same HTTP request, and
  `deduplication_key` in the body for one bot per meeting in your system. A concurrent
  duplicate gets 409 with `Retry-After: 2`; retry it with the same key.
- Retry 429, 500 and 503 with backoff. Never retry a 400 without fixing the request.
- Signed-in bots have per-login capacity (Google logins: 30 active sessions each; Teams:
  one bot per login). Register enough logins for your peak (`setting-up-platforms`).
- Admission: each bot still needs someone to admit it (`waiting_room_timeout`). Tell your
  customers to expect the bot by its `bot_name`.

## Storage destinations (dashboard only)

Destinations are created in the dashboard (Integrations > Storage); the public API and customer
keys cannot manage them. `create_bot` takes `storage_id` (1 to 80 letters, numbers, `_` or `-`),
looks it up in your own workspace and runs a live test write: bad credentials or an unknown id
give 400, a storage outage 503. Scheduled bots recheck the destination at join time.

| Provider | Setup notes | Guide |
|---|---|---|
| Amazon S3 (`aws`) | Access keys or an IAM role scoped to the bucket and prefix; `read_write` lets MeetStream serve download links, write-only makes fetch endpoints return 403 | https://docs.meetstream.ai/guides/features/custom-storage-configurations/amazon-s3 |
| Alibaba Cloud OSS (`alibaba_oss`) | RAM AccessKey pair with a bucket policy; default endpoint `https://s3.oss-<region>.aliyuncs.com` | https://docs.meetstream.ai/guides/features/custom-storage-configurations/alibaba-cloud-oss |
| Cloudflare R2 (`cloudflare_r2`) | R2 S3 token with Object Read & Write on one bucket, the 32-character account ID, region `auto`, `read_write` only | https://docs.meetstream.ai/guides/features/custom-storage-configurations/cloudflare-r2 |

Use a dedicated identity scoped to one bucket. Artifacts written before a change stay where they
were written.

## Retention and usage

- **Retention is per bot and permanent by default:** with no `recording_config.retention`,
  MeetStream keeps the media until you delete it. For customer conversations set a window:
  `"retention": {"type": "timed", "hours": 72}` (the clock starts after the call). There is no
  account-level retention setting. When it ends, or after `DELETE /bots/{bot_id}/delete`, the
  status becomes `MediaExpired`, artifact endpoints return 404 and a `data_deletion` webhook fires.
- **Usage** accrues on bot time, from arrival to leaving, including the wait in the lobby. Keep
  `waiting_room_timeout`, `everyone_left_timeout` and `voice_inactivity_timeout` tight and
  `in_call_recording_timeout` as the hard stop. Idempotent replays (507) and dedup replays (200)
  are not charged. The Usage dashboard (https://app.meetstream.ai/usage) breaks usage down per bot
  with the API key label and `custom_attributes`. Storage of permanent media and every price:
  https://meetstream.ai/pricing (never quote prices from memory).
- Guide: https://docs.meetstream.ai/guides/features/usage-and-retention (its "30 days" default
  is out of date: omitted retention is permanent).

## Idempotency in one place

`Idempotency-Key` (header, `create_bot` only): the same request replayed returns 507 with the
original bot. `deduplication_key` (body, `create_bot` and calendar schedule): your stable meeting
id; a replay returns 200, the same key with another `meeting_link` returns 409. Neither expires.
Guide: https://docs.meetstream.ai/guides/features/deduplication-idempotency-keys . Error and limit
details: [`references/errors-and-limits.md`](references/errors-and-limits.md).

## Latest docs

- Custom attributes: https://docs.meetstream.ai/guides/features/custom-attributes
- Workspace webhooks: https://docs.meetstream.ai/guides/webhooks/workspace-webhooks
- Custom storage: https://docs.meetstream.ai/guides/features/custom-storage-configurations/overview
- Rate limits (Create Bot payload reference): https://docs.meetstream.ai/api-reference/create-bot-payload-reference
- Google Calendar (connect end users with the API): https://docs.meetstream.ai/guides/calendar-integrations/google-calendar-oauth-setup

For the latest details, fetch the page with `.md` appended, read https://docs.meetstream.ai/llms.txt, or connect the docs MCP server at https://docs.meetstream.ai/_mcp/server.
