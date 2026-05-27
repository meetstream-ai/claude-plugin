---
name: calendar-automation
description: >
  Build Google Calendar-driven meeting automation on MeetStream — connect a
  Google Calendar once and a bot auto-joins every upcoming meeting, records,
  transcribes, and triggers your post-meeting workflow. Use when the user says
  "auto-record my Google Calendar meetings", "connect Google Calendar to
  MeetStream", "Google Calendar bot integration", "calendar automation for
  meetings", "join every meeting on my calendar automatically", "scheduled
  meeting bot", "recurring meeting notetaker", "Google Calendar meeting
  intelligence", or "OAuth calendar bot setup". Walks through Google Cloud
  OAuth setup, connects the calendar to MeetStream, enables auto-scheduling
  with a default bot config, and shows how to handle recurring events.
---

# Calendar Automation Scaffold (Google Calendar → MeetStream)

Build a hands-free meeting bot that auto-joins every Google Calendar meeting. Connect once, then forget — MeetStream watches the calendar, schedules bots 1 minute before each meeting, and runs your post-meeting pipeline.

## What this scaffolds

- Google Cloud OAuth client setup (one-time)
- `POST /calendar/create_calendar` — connect a Google account to MeetStream
- `POST /calendar/auto-schedule/enable` — turn on hands-free mode with default bot config
- Recurring event handling (`recurring_event: true`, `toggle-recurrence`)
- Disconnect flow

All endpoint paths and field names are verified against `docs.meetstream.ai`.

## Step 1: Requirements (ask in one message)

```
I'll set up Google Calendar auto-recording with MeetStream. Quick config:

1. STACK?  Python or Node.js? [default: Python]

2. CALENDAR SCOPE?  Personal or workspace?
   - Personal Gmail/Workspace: standard OAuth flow (this skill scaffolds it)
   - Multi-tenant SaaS (each user connects their own calendar):
     you'll need to run the OAuth flow per user; skill provides the helper

3. DEFAULT BOT BEHAVIOR for auto-scheduled bots:
   - Bot name? [default: "Your Auto Notetaker"]
   - Record video? [default: false — transcript-only]
   - Provider? deepgram / assemblyai / meetstream / meetstream_streaming
     [default: deepgram for post-call summaries]
   - Welcome message in chat? [default: none]

4. POST-MEETING WORKFLOW?
   a) AI summary to email (uses the notetaker scaffold)
   b) Slack notification with action items
   c) CRM activity log (HubSpot/Salesforce)
   d) Just store the transcript in Postgres
   [default: a]
```

## Step 2: Google Cloud OAuth setup (one-time, walk user through)

The user needs three things to give MeetStream:
1. `google_client_id`
2. `google_client_secret`
3. `google_refresh_token`

Step-by-step:

```
1. Go to https://console.cloud.google.com → create or pick a project
2. APIs & Services → Library → search "Google Calendar API" → Enable
3. APIs & Services → OAuth consent screen:
   - User type: External (or Internal if Workspace)
   - Scopes: add ".../auth/calendar.readonly" and ".../auth/calendar.events.readonly"
   - Add yourself as a test user
4. APIs & Services → Credentials → Create Credentials → OAuth client ID
   - Application type: Web application
   - Authorized redirect URIs: http://localhost:8080/oauth2callback
   - Save the client_id and client_secret
5. Run the helper script (below) to get the refresh_token
```

OAuth helper (Python, one-time use):

```python
# pip install google-auth google-auth-oauthlib
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly",
          "https://www.googleapis.com/auth/calendar.events.readonly"]

flow = InstalledAppFlow.from_client_secrets_file("client_secrets.json", SCOPES)
creds = flow.run_local_server(port=8080)
print("REFRESH TOKEN:", creds.refresh_token)
print("(Store this in MEETSTREAM env vars. It's long-lived.)")
```

## Step 3: Connect the calendar to MeetStream

```python
import os, requests

BASE = "https://api.meetstream.ai/api/v1"
HEADERS = {"Authorization": f"Token {os.environ['MEETSTREAM_API_KEY']}",
           "Content-Type": "application/json"}

def connect_calendar():
    """One-time call to link a Google Calendar to your MeetStream account."""
    resp = requests.post(f"{BASE}/calendar/create_calendar", headers=HEADERS, json={
        "google_refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
        "google_client_id":     os.environ["GOOGLE_CLIENT_ID"],
        "google_client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    })
    resp.raise_for_status()
    data = resp.json()
    # data: {calendar_id, platform, user_email, user_name, primary_calendar_id,
    #        message, calendars: [...], watch_setup: {...}}
    print(f"Connected calendar for {data['user_email']}")
    return data
```

**Field names matter:** all three keys MUST use the `google_` prefix. Plain `refresh_token` / `client_id` / `client_secret` will be rejected.

## Step 4: Enable hands-free auto-scheduling

```python
def enable_auto_schedule(callback_url: str):
    """Turn on hands-free mode. MeetStream now schedules bots for every
    upcoming meeting that has a meeting link.

    The background job runs daily at midnight UTC and schedules bots for the
    next 24h of meetings. Bots join 1 minute before each meeting start.
    """
    resp = requests.post(f"{BASE}/calendar/auto-schedule/enable", headers=HEADERS, json={
        "default_bot_config": {
            "bot_name": "Auto Notetaker",
            "audio_required": True,
            "video_required": False,
            "callback_url": callback_url,
            "transcription": {
                # NOTE: calendar bot_config uses "transcription" (not nested under recording_config).
                # This is different from create_bot's shape.
                "deepgram": {"model": "nova-3", "language": "en"}
            },
            "automatic_leave": {
                # calendar bot_config supports no_one_joined_timeout
                "no_one_joined_timeout": 300,
                "everyone_left_timeout": 600,
            },
        }
    })
    resp.raise_for_status()
    return resp.json()  # {message, auto_schedule_enabled, default_bot_config}


def disable_auto_schedule():
    resp = requests.post(f"{BASE}/calendar/auto-schedule/disable", headers=HEADERS, json={})
    resp.raise_for_status()
    return resp.json()


def get_auto_schedule_settings():
    resp = requests.get(f"{BASE}/calendar/auto-schedule/settings", headers=HEADERS)
    resp.raise_for_status()
    return resp.json()  # {auto_schedule_enabled, default_bot_config}
```

## Step 5: List + manage scheduled bots

```python
def list_calendars():
    """Live list from Google."""
    return requests.get(f"{BASE}/calendar/calendars", headers=HEADERS).json()

def list_events():
    """Sync from Google + list with pagination + bot info per event."""
    return requests.get(f"{BASE}/calendar/events", headers=HEADERS).json()

def list_events_fast():
    """Read MeetStream's local DB only (no Google API call)."""
    return requests.get(f"{BASE}/calendar/get_events", headers=HEADERS).json()

def list_scheduled_bots():
    """All upcoming scheduled bots across events."""
    return requests.get(f"{BASE}/calendar/scheduled_bots", headers=HEADERS).json()

def reschedule_bot(bot_id: str, new_join_time_iso: str):
    """Move a scheduled bot to a different time (e.g. user reschedules the
    meeting in Google Calendar — MeetStream usually handles this automatically
    via Google watch channels, but you can also trigger it explicitly)."""
    return requests.patch(
        f"{BASE}/calendar/scheduled_bots/{bot_id}",
        headers=HEADERS,
        json={"scheduled_join_time": new_join_time_iso}
    ).json()

def delete_scheduled_bot(bot_id: str):
    """Cancel a single scheduled bot that hasn't joined yet."""
    return requests.delete(f"{BASE}/calendar/scheduled_bots/{bot_id}", headers=HEADERS).json()
```

## Step 6: Per-event manual schedule (override default)

If you want different config for one specific meeting (e.g. video on for a presentation), schedule it manually with a custom `bot_config`:

```python
def schedule_one_event(event_id: str, bot_config: dict, recurring: bool = False):
    """Schedule a bot for ONE specific event from /calendar/events.

    For recurring options:
      - recurring_event: True   → auto-schedule next occurrence after this one
      - schedule_all_occurrences: True + occurrence_limit (default 52)
      - occurrence_date: ISO   → schedule one specific occurrence
    """
    body = {"bot_config": bot_config}
    if recurring:
        body["recurring_event"] = True
    resp = requests.post(f"{BASE}/calendar/schedule/{event_id}", headers=HEADERS, json=body)
    if resp.status_code == 409:
        # Already scheduled for this event
        print(f"Already scheduled: {resp.json().get('bot_id')}")
        return resp.json()
    resp.raise_for_status()
    return resp.json()


def unschedule_event(event_id: str, cancel_all_occurrences: bool = False):
    body = {"cancel_all_occurrences": cancel_all_occurrences}
    resp = requests.delete(f"{BASE}/calendar/schedule/{event_id}", headers=HEADERS, json=body)
    resp.raise_for_status()
    return resp.json()
```

## Step 7: Recurring events

```python
def toggle_recurring(event_id: str, enabled: bool):
    """Turn auto-rescheduling on/off for a recurring event.

    Returns 400 if the event isn't actually recurring (no RRULE).
    """
    resp = requests.post(f"{BASE}/calendar/toggle-recurrence", headers=HEADERS, json={
        "event_id": event_id,
        "recurring_enabled": enabled,
    })
    resp.raise_for_status()
    return resp.json()  # {event_id, recurring_enabled, recurrence_rule, message, summary, start_time, end_time}


def trigger_auto_reschedule(user_id: str, event_id: str, recurrence_rule: str):
    """Manually trigger the next-occurrence reschedule. Usually not needed —
    MeetStream auto-reschedules after each occurrence when recurring_event=True."""
    resp = requests.post(f"{BASE}/calendar/auto-reschedule", headers=HEADERS, json={
        "user_id": user_id,
        "event_id": event_id,
        "recurrence_rule": recurrence_rule,
    })
    resp.raise_for_status()
    return resp.json()
```

## Step 8: Disconnect (irreversible)

```python
def disconnect_calendar():
    """DELETE the calendar integration entirely. Irreversible.

    Stops watch channels, cancels all pending schedules, deletes all synced
    event data, and removes Google OAuth credentials from storage.
    """
    resp = requests.delete(f"{BASE}/calendar/disconnect", headers=HEADERS)
    resp.raise_for_status()
    return resp.json()  # {disconnected, user_id, watch_channel_stopped, events_deleted, schedules_cancelled, message}
```

> ⚠ This is a destructive operation. Require explicit user confirmation before calling. (The OpenAPI spec shows POST for this — that's a quirk; the docs guide, cURL example, and response example all use DELETE.)

## How auto-scheduling actually works (live behavior, not just docs)

- **Job cadence:** Every 24h at midnight UTC. The job picks up the next 24h of events with valid meeting links.
- **Pre-join window:** Bots are scheduled to join **1 minute before** the meeting's start time.
- **Dedup:** Events that already have a scheduled bot are skipped (no duplicate joins).
- **Real-time updates:** Google Calendar push notifications via watch channels — MeetStream auto-reschedules if a user moves a meeting, and auto-cancels if a meeting is deleted.
- **Watch channel renewal:** Daily background job renews any watch channel expiring within 2 days. Your real-time sync stays active indefinitely with zero maintenance.
- **Cancelled meetings:** Detected via Google watch → EventBridge schedule deleted, bot marked Cancelled. No bot is ever created for a cancelled meeting.

## End-to-end checklist

```
✅ Calendar automation scaffolded.

Next steps:
  1. Set MEETSTREAM_API_KEY, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN in .env
  2. Run python connect.py   (one-time, calls /calendar/create_calendar)
  3. Run python enable.py    (one-time, calls /calendar/auto-schedule/enable with default_bot_config)
  4. Verify with python list.py   (calls /calendar/scheduled_bots — should show upcoming bots)
  5. Your webhook server (callback_url from step 3) will receive lifecycle events for each meeting

📚 For the post-meeting workflow (transcript fetch → AI summary → delivery), use the `notetaker` skill.
🔧 To debug a failed scheduled bot, use the `meetstream-debugger` subagent.
```

## Common gotchas (live-verified)

- **Field name prefixes:** `create_calendar` requires `google_refresh_token` / `google_client_id` / `google_client_secret`. Without the `google_` prefix, the API rejects.
- **bot_config schema differs from create_bot:** calendar `bot_config` uses `transcription` (not `recording_config.transcript`), and supports `no_one_joined_timeout` (which doesn't exist on `create_bot`). The docs guide is authoritative here.
- **409 Conflict on duplicate schedule:** scheduling the same event twice returns `409` with the existing bot's ID. Don't error out — that's the API telling you the bot is already there.
- **`toggle-recurrence` returns 400** if you call it on a non-recurring event.
- **Disconnect is DELETE**, not POST (despite OpenAPI). Follow the docs guide.
- **Personal Gmail accounts work** — you don't need Google Workspace for this integration.
