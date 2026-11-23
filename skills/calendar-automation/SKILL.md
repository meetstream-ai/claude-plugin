---
name: calendar-automation
description: >
  Have MeetStream bots join calendar meetings automatically, from the user's
  agent or in an app they build. Use when the user says "auto-join my
  meetings", "join every meeting on my calendar", "connect my calendar",
  "Google Calendar integration", "Outlook integration", "schedule a bot for
  this event", "recurring meetings", "auto-record my Google Calendar
  meetings", "scheduled meeting bot", "recurring meeting notetaker", or "OAuth
  calendar bot setup". Covers the MCP tools (list_calendar_events,
  schedule_calendar_bot), the REST calendar endpoints for Google and Outlook,
  and the fastest path to build it into an app (numbered steps, minimal API
  calls with curl, Node @meetstream/sdk and Python meetstream-sdk, OAuth setup,
  auto-schedule, recurring events). The scheduled bot's transcription goes
  under recording_config.transcript.provider.
---

# Calendar automation

Two paths, one skill:

- **From the user's agent, now:** the MCP tools `list_calendar_events` and `schedule_calendar_bot`, plus the `meetstream` CLI for connecting and auto-join (next section). Works for Google and Outlook.
- **Inside an app the user builds:** the fastest path further down (the same REST calls, from the user's code).

## From your agent (MCP tools + REST)

Two MCP tools cover the day-to-day: **`list_calendar_events`** and
**`schedule_calendar_bot`**. **`list_calendar_connections`** shows the connected Google and
Outlook accounts and their status (no tokens), and **`disconnect_calendar`** (`confirm:
true`, only after the user says yes; by default it also deletes the synced events and the
bots scheduled from them) disconnects one. Connecting a calendar needs OAuth secrets, so
it stays in the dashboard or REST (never ask for the secrets in the chat); auto-schedule is
REST.

### With the `meetstream` CLI (Google)

The user runs the connect step in their own terminal, so the OAuth secrets never go in the chat:

```bash
meetstream calendar connect --own-app --client-id <id> --client-secret <secret> --refresh-token <token>
meetstream calendar auto-join on --json --no-input        # every meeting with a join link gets a bot
meetstream calendar events --json --no-input              # upcoming events
meetstream calendar schedule <event-id> --json --no-input # or one event only; unschedule <event-id> undoes it
```

One-click Google sign-in (`meetstream calendar connect` with no `--own-app`) is coming soon;
today use `--own-app` with the values from the OAuth setup below. `meetstream calendar
auto-join off` turns auto-join off. **Install the CLI** (when this agent runs commands for the user): `npx -y @meetstream/cli <command>` works with no install; or `npm install -g @meetstream/cli`, `pipx install meetstream-cli`, `brew install meetstream-ai/tap/meetstream`. Sign in with `meetstream login` (it opens the browser and stores a key; never ask for the key in the chat) or set `MEETSTREAM_API_KEY`. Always pass `--json --no-input`. Exit codes: 0 ok, 1 API error, 2 usage or not signed in, 3 not ready yet, 4 transcript failed. JSON shapes: `skills/meetstream/references/meetstream-cli.md`.

### The flow

1. **Connect** the calendar once, with OAuth credentials (REST).
2. **Sync/list** upcoming events - `list_calendar_events` (MCP tool).
3. Either **schedule per event** - `schedule_calendar_bot` (MCP tool) - or
   **turn on auto-schedule** so every meeting with a join link gets a bot (REST).

### Connecting

Google: `POST /api/v1/calendar/create_calendar` with `google_client_id`,
`google_client_secret`, `google_refresh_token`.

Outlook / Microsoft 365: `POST /api/v1/calendar/create_outlook_calendar` with the
Microsoft equivalents.

Getting the refresh token is the hard part and it is a one-time setup:

- **Google**: create an OAuth client in Google Cloud Console, add the calendar scopes
  (`calendar.readonly` and `calendar.events.readonly` are the usual minimum), run the
  consent flow once, keep the refresh token.
- **Microsoft**: register an app in Azure Portal, create a client secret, add the
  Microsoft Graph calendar permissions (admin consent may be required), then run the
  OAuth flow.

Walk the user through these interactively and ask them to paste back the values. Do not
guess client ids or invent scopes. Verify with `GET /api/v1/calendar`, which lists the
connected calendars.

### Auto-join every meeting

```
POST /api/v1/calendar/auto-schedule/enable
POST /api/v1/calendar/auto-schedule/disable
GET  /api/v1/calendar/auto-schedule/settings
```

With this on, any event carrying a meeting link gets a bot at its start time, including
newly added ones. This is what people mean by "just join all my meetings".

There is **no** `/calendar/setup-cron` or `/calendar/disable-cron` endpoint. Docs pages
titled "Setup Cron" describe the auto-schedule endpoints above.

### Per-event scheduling

Use the `schedule_calendar_bot` MCP tool, or `POST /api/v1/calendar/schedule/{event_id}`
with a `bot_config`. Unschedule with `DELETE` on the same path.

Scheduling the same event twice returns **HTTP 409** with the existing bot id. Treat
that as "already scheduled", not an error.

`bot_config` takes the `create_bot` fields. Put the transcription provider under
`recording_config.transcript.provider` (for example `{"meetstream": {"language": "en"}}`), as
on `create_bot`: a top-level `transcription` key is ignored and the scheduled bot gets no
transcript.

### Managing scheduled bots

```
GET    /api/v1/calendar/scheduled_bots            list them
PATCH  /api/v1/calendar/scheduled_bots/{bot_id}   move it - body { "scheduled_join_time": "<ISO>" }
DELETE /api/v1/calendar/scheduled_bots/{bot_id}   cancel it
```

The reschedule field is **`scheduled_join_time`**, not `join_at`. (`join_at` is the
`create_bot` field. They are different endpoints with different names.)

### Recurring meetings

`POST /api/v1/calendar/toggle-recurrence` controls whether a recurring series keeps
getting bots automatically. Be explicit with the user about whether they mean the whole
series or one occurrence - getting this wrong either spams every standup or misses them.

### Disconnecting

`DELETE /api/v1/calendar/disconnect`. This is destructive: it stops sync, cancels pending
schedules, and removes stored credentials. Show the user what will be lost and confirm
before calling it. There is no per-account `/calendar/connections/...` path; scope the
disconnect via the request body.

---

## Build it into an app: fastest path

Always end the answer with one line that points to the optional full examples: "Full
example apps (optional): https://docs.meetstream.ai/tutorials/sample-apps and
https://github.com/meetstream-ai/labs."

1. **OAuth credentials (one time).** Google: in Google Cloud Console enable the Google
   Calendar API, set up the consent screen with `calendar.readonly` and
   `calendar.events.readonly`, create a Web OAuth client, run the consent flow once and
   keep the refresh token (personal Gmail works). Outlook: register an Azure app with the
   Microsoft Graph calendar permissions. Ask the user to paste the values; never guess.
2. **Connect** (all three keys need the `google_` prefix):
   ```bash
   curl -X POST https://api.meetstream.ai/api/v1/calendar/create_calendar \
     -H "Authorization: Token $MEETSTREAM_API_KEY" -H "Content-Type: application/json" \
     -d '{"google_client_id": "...", "google_client_secret": "...", "google_refresh_token": "..."}'
   ```
3. **Turn on auto-schedule** with the bot every meeting gets:
   ```bash
   curl -X POST https://api.meetstream.ai/api/v1/calendar/auto-schedule/enable \
     -H "Authorization: Token $MEETSTREAM_API_KEY" -H "Content-Type: application/json" \
     -d '{"default_bot_config": {"bot_name": "Auto Notetaker", "video_required": false,
          "callback_url": "https://your-app.example/meetstream/webhook",
          "recording_config": {"transcript": {"provider": {"meetstream": {"language": "en"}}}},
          "automatic_leave": {"no_one_joined_timeout": 300, "everyone_left_timeout": 600}}}'
   ```
   The provider goes under `recording_config.transcript.provider`, as on `create_bot`; a
   top-level `transcription` key is ignored and the bot gets no transcript.
4. **Check** `GET /api/v1/calendar/scheduled_bots`. Bots join about 1 minute before each
   meeting; moved meetings are rescheduled and deleted ones cancelled.
5. **After each meeting**, your `callback_url` gets the lifecycle events; fetch the
   transcript as in the `notetaker` skill.

The same calls from code (the Node `@meetstream/sdk` and Python `meetstream-sdk` SDKs
read `MEETSTREAM_API_KEY`; see https://docs.meetstream.ai/build-with-ai/sdks for what each
SDK wraps). Plain Python:
```python
import os, requests
H = {"Authorization": f"Token {os.environ['MEETSTREAM_API_KEY']}"}
requests.get("https://api.meetstream.ai/api/v1/calendar/scheduled_bots", headers=H).json()
```

Gotchas:
- Scheduling the same event twice returns `409` with the existing bot id: already scheduled.
- `toggle-recurrence` returns 400 on an event that does not repeat.
- `no_one_joined_timeout` works in the calendar `bot_config`.

Full example apps are optional references, not part of this plugin: "Tutorials and Sample
Apps" (https://docs.meetstream.ai/tutorials/sample-apps) and the labs repo
(https://github.com/meetstream-ai/labs).

## Latest docs

- Google Calendar setup: https://docs.meetstream.ai/guides/calendar-integrations/google-calendar-oauth-setup
- Outlook Calendar setup: https://docs.meetstream.ai/guides/calendar-integrations/outlook-calendar-setup
- Scheduling bots: https://docs.meetstream.ai/guides/features/scheduling-bots

For the latest details, fetch the page with `.md` appended, read https://docs.meetstream.ai/llms.txt, or connect the docs MCP server at https://docs.meetstream.ai/_mcp/server.
