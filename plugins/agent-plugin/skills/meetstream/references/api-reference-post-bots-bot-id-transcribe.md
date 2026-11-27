# MeetStream API Reference: POST `/bots/{bot_id}/transcribe`

> Part of [`api-reference.md`](api-reference.md), split so each file stays under 20 KB.

### POST `/bots/{bot_id}/transcribe`
Trigger a new post-call transcription run on the bot's stored audio. **Live-verified behaviors:**

- Works on any bot with stored audio - including bots that originally used a **streaming-only** provider (which have `transcript_id: null` and empty `/transcriptions`). This is the **only way** to get a post-call transcript from a streaming-only bot.
- Returns immediately with a new `transcript_id` and starts processing in the background
- **Overwrites `bot_details.transcript_id`** with the new id (canonical fetch always returns the latest run)
- Adds an entry to `GET /bots/{bot_id}/transcriptions` with `status: "Processing"` → `"Success"` or `"Failed"`
- Fires **exactly one** `transcription.processed` or `transcription.failed` event on the `callback_url` passed in the body
- Payload shape is identical to a Path-A bot's transcription event (same `event` name, `transcript_status`, `status_code` 200/500)
- **Does NOT fire `bot.done`** - `/transcribe` is single-event fire-and-forget, not a lifecycle restart
- **Does NOT include `custom_attributes`** in the webhook payload (unlike original lifecycle events). Correlate by `bot_id`.

Body (`TranscribeRequest`):

```json
{
  "provider": {
    "deepgram": { "model": "nova-3", "language": "en" }
  },
  "callback_url": "https://your-server.com/webhook"
}
```

- `provider` (object, **required**) - top-level. Pick exactly one sub-key: `deepgram`, `meetstream`, `jigsawstack`, `sarvam`, `assemblyai`, or `smallest`. (Same shape as `recording_config.transcript.provider` but `provider` is the top-level body key.)
- `callback_url` (string, optional) - where to send the transcription.processed/.failed webhook for this run.

Response (`TranscribeResponse`): `{ bot_id, transcript_id, provider, message }`.

> **When to use `/transcribe` (it's a fallback, not the default):**
> - The bot used a streaming-only provider and you also want a post-call transcript
> - The original `create_bot` provider failed (out of credit, wrong config) and you want to retry with a different provider
> - You want to re-transcribe with a higher-quality / different-language provider
>
> For standard post-call transcripts, configure the provider on `create_bot` up front and use the canonical fetch flow - no `/transcribe` call needed.

---

## Transcription Endpoints

### GET `/transcript/{transcript_id}/get_transcript`
Returns the processed transcript by `transcript_id`. The `transcript_id` comes from any of four places:
1. The `create_bot` response (for assemblyai/deepgram/jigsawstack/sarvam/meetstream providers - null for `meeting_captions`)
2. **`GET /bots/{bot_id}/detail` → `bot_details.transcript_id`** (live-verified, not in OpenAPI schema)
3. `GET /bots/{bot_id}/transcriptions` (lists every run)
4. The `POST /bots/{bot_id}/transcribe` response

Query: `?raw=true` to retrieve raw unformatted provider output.

**Response is a top-level JSON array.** By default it is participant-keyed (`GetTranscriptionV2Schema`):
```json
[
  {
    "participant": { "id": 100, "name": "Alice", "platform": "desktop", "extra_data": {} },
    "words": [
      { "text": "Hello everyone, let's get started.",
        "start_timestamp": { "relative": 0.5, "absolute": null },
        "end_timestamp": { "relative": 3.2, "absolute": null } }
    ],
    "language_code": "en"
  }
]
```

Read it this way: the speaker is `participant.name`, the text is the `words[].text` values
joined with spaces, and the start time is `words[0].start_timestamp.relative` (seconds).
This participant-keyed format is the default whenever it exists. Some providers return the
segment-list format instead (`speaker`, `transcript`, `start_time`, `end_time`, `words`
with `word` / `punctuated_word`), so a parser should read both. Skip segments with no text.
The `meetstream` engine can add a lone "Thank you." segment on silence; treat it as filler.

The segment-list format (`GetTranscriptionSchema`), when a provider returns it:
`[{"speaker": "Alice", "transcript": "...", "start_time": 0.5, "end_time": 3.2, "absolute_start_time": "...", "words": [{"word", "punctuated_word", "start", "end", "confidence", "speaker"}]}]`.

- Response is the array itself, not `{transcript: [...]}`.

`?raw=true` returns a different shape (`GetRawTranscriptionSchema`) with `id` and provider-specific structure.

Other status codes:
- **202** `{"message": "Transcript is still being processed. ..."}`: poll again with a cap (a streaming-only bot never gets a post-call transcript).
- **422** (API v1.10.0): the run failed. Body `{"message": "Transcript processing failed: <reason>", "transcript_status": "Failed", "transcript_id": "..."}`, for example the provider rejected the API key or the usage limit was reached. Final: do not retry. Fix the cause, then `POST /bots/{bot_id}/transcribe`.

---

### GET `/bots/{bot_id}/transcriptions`
Lists every transcription run for a bot. Returns:

```json
{
  "bot_id": "...",
  "transcriptions": [
    {
      "transcript_id": "...",
      "provider": "deepgram",
      "status": "Success" | "Processing" | "Failed",
      "created_at": "2026-...",
      "config": { /* the provider config used */ },
      "download_urls": {
        "raw_transcript": "https://s3...",
        "processed_transcript": "https://s3..."
      }
    }
  ]
}
```

`download_urls` pre-signed S3 URLs are valid for 1 hour. `download_urls` can also be `null`.

---

## Calendar Endpoints

### POST `/calendar/create_calendar`
Connect a Google Calendar via OAuth credentials.

**Body (all three required per `CalendarCreateRequest`):**
```json
{
  "google_refresh_token": "...",
  "google_client_id": "...",
  "google_client_secret": "..."
}
```

Field names use the `google_` prefix. Plain `refresh_token` / `client_id` / `client_secret` are rejected.

**Response:** `{ calendar_id, platform, user_email, user_name, primary_calendar_id, message, calendars: [{id, summary, description, isPrimary, accessRole, timeZone, backgroundColor, foregroundColor, selected}], watch_setup: {...} }`.

---

### GET `/calendar/calendars`
List connected calendars (live from Google API). Returns `{ total, user_id, calendars: [...] }`.

---

### GET `/calendar`
List connected calendars (alternate path). Same shape as above.

---

### GET `/calendar/events`
Sync + list upcoming events. Paginated:
```json
{
  "next": "...",
  "previous": "...",
  "has_more": true,
  "results": [
    {
      "id": "evt_...",
      "start_time": "2026-...",
      "end_time": "2026-...",
      "calendar_id": "...",
      "platform": "google_calendar",
      "platform_id": "...",
      "ical_uid": "...",
      "meeting_platform": "google_meet|zoom|teams|...",
      "meeting_url": "...",
      "created_at": "...",
      "updated_at": "...",
      "is_deleted": false,
      "raw": { /* raw Google event */ },
      "bots": [ /* scheduled bots for this event */ ]
    }
  ]
}
```

---

### GET `/calendar/get_events`
Same as `/calendar/events` but reads from MeetStream's local DB only (no Google API call - faster).

---

### POST `/calendar/schedule/{event_id}`
Manually schedule a bot for a specific event. `event_id` is the `id` from `/calendar/events`.

**Body.** `bot_config` takes the `create_bot` fields. The transcript provider goes under `recording_config.transcript.provider`, as on `create_bot`; a top-level `transcription` key is ignored and the scheduled bot gets no transcript.
```json
{
  "bot_config": {
    "bot_name": "My Meeting Bot",
    "audio_required": true,
    "video_required": false,
    "bot_message": "Joining to record",
    "callback_url": "https://...",
    "automatic_leave": { "no_one_joined_timeout": 600, "everyone_left_timeout": 600 },
    "recording_config": { "transcript": { "provider": { "meetstream": { "language": "en" } } } }
  },
  "occurrence_date": "2026-04-14T10:00:00Z",
  "schedule_all_occurrences": false,
  "occurrence_limit": 52,
  "recurring_event": false
}
```

| Field | Type | Default | Description |
|---|---|---|---|
| `bot_config` | object | - | Same shape as `create_bot` body (`audio_required` IS valid here) |
| `occurrence_date` | ISO-8601 | - | Specific recurring occurrence to schedule |
| `schedule_all_occurrences` | bool | `false` | Batch-schedule all future occurrences |
| `occurrence_limit` | int | `52` | Max occurrences when batch-scheduling |
| `recurring_event` | bool | `false` | After this occurrence, auto-schedule the next one |

**Response:** `{ scheduled, schedule_id, bot_id, schedule_group, event_id, scheduled_time, bot_config: {...}, is_recurring_occurrence }`.

**Deduplication:** scheduling the same event twice returns **HTTP 409** with the existing bot's ID. To update, use `PATCH /calendar/scheduled_bots/{bot_id}`.

---

### DELETE `/calendar/schedule/{event_id}`
Unschedule the bot for an event.

**Body (optional):**
```json
{
  "cancel_all_occurrences": false,
  "from_date": "2026-05-01T00:00:00Z"
}
```

**Response:** `{ unscheduled, event_id, cancelled_schedules, schedules_cancelled, bots_deleted, cancel_all_occurrences, is_recurring_series }`.

---

### GET `/calendar/scheduled_bots`
List all upcoming scheduled bots.

---

### PATCH `/calendar/scheduled_bots/{bot_id}`
Reschedule / update a future bot.

**Body:**
```json
{
  "scheduled_join_time": "2026-04-22T15:00:00Z",
  "bot_username": "Updated Name",
  "custom_attributes": { "deal_id": "12345" }
}
```

**Response:** `{ message, bot_id, updated_fields: [...], schedule_updated: bool }`.

---

### DELETE `/calendar/scheduled_bots/{bot_id}`
Delete a single scheduled bot that hasn't joined yet.

---

### POST `/calendar/auto-schedule/enable`
Enable hands-free auto-scheduling.

**Body** (from docs guide; calendar `default_bot_config` schema not live-tested by this skill - see note on `/calendar/schedule/{event_id}` above for caveats):
```json
{
  "default_bot_config": {
    "bot_name": "MeetStream Auto Bot",
    "audio_required": true,
    "video_required": false,
    "callback_url": "https://...",
    "recording_config": { "transcript": { "provider": { "meetstream": { "language": "en" } } } },
    "automatic_leave": { "no_one_joined_timeout": 600, "everyone_left_timeout": 600 }
  }
}
```

How it works: background job every 24h at midnight UTC scans next 24h, schedules bots 1 min before each meeting, skips events with existing bots (dedup).

**Response:** `{ message, auto_schedule_enabled: true, default_bot_config: {...} }`.

---

### POST `/calendar/auto-schedule/disable`
Disable auto-scheduling. No body required.

---

### GET `/calendar/auto-schedule/settings`
Returns `{ auto_schedule_enabled, default_bot_config }`.

---

### POST `/calendar/auto-reschedule`
Trigger reschedule of the next occurrence of a recurring event.

---

### POST `/calendar/toggle-recurrence`
Enable/disable auto-rescheduling per event.

**Body:**
```json
{ "event_id": "evt_...", "recurring_enabled": true }
```

> No path param. The earlier docs referenced `/calendar/toggle-recurring/{event_id}` is wrong.

---

### DELETE `/calendar/disconnect`
Disconnects the calendar - irreversible. Stops Google Calendar watch channels, cancels pending bot schedules, deletes all synced event data, and removes stored Google OAuth credentials.

```bash
curl -X DELETE "https://api.meetstream.ai/api/v1/calendar/disconnect" \
  -H "Authorization: Token <YOUR_API_KEY>"
```

**Response:**
```json
{
  "disconnected": true,
  "user_id": "usr_abc123",
  "watch_channel_stopped": true,
  "events_deleted": 42,
  "schedules_cancelled": 5,
  "message": "Calendar disconnected successfully. All events and scheduled bots have been removed."
}
```

> The OpenAPI spec shows this as `POST` with a `CalendarCreateRequest` body - that's a quirk in the spec. The docs guide, cURL example, and response example all use `DELETE` with no body. Follow the docs guide.

---

## Google Signed-In Bot Endpoints

For bots that authenticate to Google Meet as a real user. Setup involves Google Workspace SSO (Legacy SSO profile) + an OpenSSL key/certificate; see https://docs.meetstream.ai/guides/app-integrations/google-signed-in-bots

### POST `/google-login-domains`
Register a Google Workspace domain. Body: `{ "sso_workspace_domain": "your-company.com", "name"?: "...", "login_mode"?: "always" | "if_required" }` (default `always`). Returns 201 `{ sso_workspace_domain, name, login_mode, max_concurrent_per_login, created_at }`; 409 if already registered.

### GET `/google-login-domains`
`{ domains: [{ sso_workspace_domain, name, login_mode, max_concurrent_per_login, login_count, active_login_count, created_at }] }`

### GET `/google-login-domains/{domain}`
Fetch one domain with its `logins`. **`{domain}` is the workspace domain string** (e.g. `your-company.com`), not an opaque id.

### PATCH `/google-login-domains/{domain}`
`{ name?, login_mode? }`

### DELETE `/google-login-domains/{domain}`
Deletes the domain and its logins. Refused (400) while any login is active; disable them first.

### POST `/google-logins`
`{ "domain": "your-company.com", "email": "bot@your-company.com", "sso_private_key_pem": "<contents of key.pem>", "sso_cert_pem": "<contents of cert.pem>", "is_active"?: true }` → 201 `{ login_id, domain, email, is_active, created_at }`

### GET `/google-logins?domain=<d>`
`{ logins: [{ login_id, email, is_active, active_sessions, last_test_status, last_tested_at, created_at }] }`. There is **no** `GET /google-logins/{login_id}`.

### PATCH `/google-logins/{login_id}`
Body **must include `domain`**, plus any of `is_active`, `email`, `sso_private_key_pem`, `sso_cert_pem`. Credential changes and deactivation are refused while the login has active sessions.

### DELETE `/google-logins/{login_id}?domain=<d>`
Refused while the login has active sessions.

### Then on `create_bot`, attach via:
```json
{
  "google_meet": {
    "login_required": true,
    "google_login_domain": "your-company.com",
    "sign_in_email": "bot@your-company.com",
    "strict_email": true
  }
}
```

(`google_meet` is documented in the Google Signed-In Bots guide; it isn't in the OpenAPI `CreateBotRequest` schema but is the canonical activation payload.)

---

## Microsoft Teams Signed-In Bot Endpoints

For bots that join Teams as a real Microsoft 365 account (meetings that block anonymous join). Requires a dedicated M365 tenant with security defaults disabled and self-service password reset set to None for the bot accounts. Microsoft 365 work/school Teams only (not `teams.live.com`). Guide: https://docs.meetstream.ai/guides/app-integrations/teams-signed-in-bots

### POST `/teams-login-domains`
`{ "domain": "bots.your-company.com", "name"?: "...", "login_mode": "always" }` (`domain` required; `if_required` is not supported for Teams yet) → 201 `{ domain, name, login_mode, created_at }`

### GET `/teams-login-domains`
`{ domains: [{ domain, name, login_mode, login_count, active_login_count, created_at }] }`

### GET `/teams-login-domains/{domain}`
`{ domain, name, login_mode, logins: [{ login_id, email, is_active, lease_status, last_session_result }], created_at, updated_at }`; 404 `{ "error": "Domain not found" }`

### PATCH `/teams-login-domains/{domain}`
`{ name?, login_mode? }` → `{ success, domain: { domain, name, login_mode, updated_at } }`

### DELETE `/teams-login-domains/{domain}`
Deletes the domain **and all associated logins** → `{ success, message }`

### POST `/teams-logins`
`{ "domain": "bots.your-company.com", "email": "bot1@bots.your-company.com", "password": "<ACCOUNT_PASSWORD>", "is_active"?: true }` → 201 login object. The password is write-only (never returned); load it from a secret store, never hardcode it.

### GET `/teams-logins?domain=<d>`
`domain` is required (400 without it) → `{ logins: [login] }`; 404 `{ "error": "Domain <d> not registered" }`

### GET `/teams-logins/{login_id}`
Login object; 404 `{ "error": "Login not found" }`

### PATCH `/teams-logins/{login_id}`
`{ password?, is_active? }` → `{ success, login }`. A new password also reactivates an account that was deactivated after a failed sign-in.

### DELETE `/teams-logins/{login_id}`
→ `{ success, message: "Login deleted successfully" }`

Login object: `{ login_id, domain, email, is_active, lease_status, last_session_result, last_login_error, created_at, updated_at }`

### Then on `create_bot`, attach via:
```json
{
  "teams": {
    "login_required": true,
    "teams_login_domain": "bots.your-company.com",
    "sign_in_email": "bot1@bots.your-company.com",
    "strict_email": true
  }
}
```

- **One concurrent bot per account.** Register N accounts for N concurrent signed-in Teams bots.
- `bot_name` / `bot_image_url` are not applied: the Microsoft account's display name and picture are used.

| `create_bot` error | Meaning |
|---|---|
| 400 `teams.teams_login_domain '<d>' is not registered...` | Register the domain first |
| 403 | Domain or account belongs to another MeetStream account |
| 404 | `sign_in_email` not registered under the domain |
| 409 | Pinned account busy/deactivated with `strict_email: true`, or no account both active and free |
| 429 `all Teams logins ... in use` | Every account in the domain is leased |

---
