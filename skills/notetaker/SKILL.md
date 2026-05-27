---
name: notetaker
description: >
  Build a complete MeetStream-powered meeting notetaker — bot joins, records,
  transcribes, generates an AI summary, and delivers to email/Slack/Notion/CRM.
  Use when the user says "build a notetaker", "meeting recorder with summaries",
  "auto-summarize my meetings", "Otter.ai alternative", "Fireflies clone",
  "Granola-style notetaker", "meeting recap to Slack", or any variant of a
  meeting-summary product. Walks through tech stack choice, scaffolds webhook
  handler, transcript fetch, LLM summary, and delivery layer end-to-end.
---

# Notetaker Scaffold

Build a production-ready meeting notetaker on the MeetStream API.

## What this skill does

When the user wants a notetaker, ask the 4 questions below, then scaffold a complete app — webhook server, bot creation, transcript fetch, LLM summary, delivery — using their tech stack of choice.

## Step 1: Requirements (4 questions)

Ask in one message, with sensible defaults pre-filled:

```
I'll build you a complete meeting notetaker. Quick config:

1. STACK?  Python (Flask/FastAPI) or Node.js (Express/Next.js)? [default: Python + FastAPI]

2. TRIGGER?  How do meetings start the bot?
   a) Manual API call (you POST /meetings/start with a link)
   b) Calendar auto-schedule (MeetStream watches Google Calendar)
   c) Slack slash command (/note <meeting-link>)
   [default: manual API call]

3. SUMMARY DELIVERY?  Where should the summary go?
   a) Email (SMTP / Resend / SendGrid)
   b) Slack DM or channel
   c) Notion page
   d) HubSpot / Salesforce CRM activity
   e) Webhook (you handle delivery yourself)
   [default: email via Resend]

4. PROVIDERS?  Which post-call transcription provider does your MeetStream account have keys for?
   Run /meetstream-verify-account first if you're not sure. Otherwise pick:
   - deepgram (highest accuracy, ~$0.26/hr)
   - assemblyai (best speaker diarization, ~$0.37/hr)
   - meetstream (in-house, depends on account config)
   [default: deepgram]
```

If they say "you decide" — use the defaults.

## Step 2: Scaffold the project

Create this exact structure (Python + FastAPI + Resend example shown; adapt to their stack):

```
notetaker/
├── .env.example          # MEETSTREAM_API_KEY, OPENAI_API_KEY, RESEND_API_KEY, etc.
├── requirements.txt      # or package.json
├── README.md             # quickstart for the user
├── app/
│   ├── main.py           # FastAPI app entrypoint
│   ├── meetstream.py     # MeetStream client wrapper
│   ├── webhook.py        # Webhook handler (returns 2xx fast, queues work)
│   ├── summary.py        # LLM summary generation
│   ├── delivery.py       # Send to email/Slack/Notion/CRM
│   └── queue.py          # Idempotency + async queue (use Redis or in-memory)
└── scripts/
    ├── start_bot.py      # CLI to send a bot to a meeting link
    └── reprocess.py      # Re-run summary on a bot_id (useful for testing)
```

## Step 3: Reference implementation (Python + FastAPI)

`app/main.py`:
```python
import os
from fastapi import FastAPI, Request, BackgroundTasks
from app.webhook import handle_webhook
from app.meetstream import create_bot

app = FastAPI(title="MeetStream Notetaker")

@app.post("/meetings/start")
async def start_meeting(meeting_link: str, user_email: str, tenant_id: str):
    """Trigger: send a bot to a meeting and tag it for delivery later."""
    bot_id = create_bot(
        meeting_link=meeting_link,
        callback_url=f"{os.environ['PUBLIC_URL']}/webhook/meetstream",
        custom_attributes={"user_email": user_email, "tenant_id": tenant_id},
    )
    return {"bot_id": bot_id, "status": "joining"}

@app.post("/webhook/meetstream")
async def webhook(request: Request, tasks: BackgroundTasks):
    # ALWAYS return 2xx fast — webhooks are NOT retried on non-2xx
    payload = await request.json()
    tasks.add_task(handle_webhook, payload)
    return {"status": "ok"}
```

`app/meetstream.py`:
```python
import os, requests

BASE = "https://api.meetstream.ai/api/v1"
HEADERS = {
    "Authorization": f"Token {os.environ['MEETSTREAM_API_KEY']}",
    "Content-Type": "application/json",
}

def create_bot(meeting_link: str, callback_url: str, custom_attributes: dict) -> str:
    """Send a bot with a post-call provider — Path A lifecycle (bot.done is terminal)."""
    resp = requests.post(f"{BASE}/bots/create_bot", headers=HEADERS, json={
        "meeting_link": meeting_link,
        "bot_name": "Acme Notetaker",
        "video_required": False,
        "callback_url": callback_url,
        "custom_attributes": {k: str(v) for k, v in custom_attributes.items()},  # stringify
        "recording_config": {
            "transcript": {"provider": {"deepgram": {"model": "nova-3", "language": "en"}}},
            "retention": {"type": "timed", "hours": 168},
        },
        "automatic_leave": {
            "waiting_room_timeout": 600,
            "everyone_left_timeout": 600,
            "voice_inactivity_timeout": 600,
            "in_call_recording_timeout": 14400,
            "recording_permission_denied_timeout": 300,
        },
    })
    resp.raise_for_status()
    return resp.json()["bot_id"]


def get_transcript(bot_id: str) -> list[dict]:
    """Canonical stateless fetch via bot_details.transcript_id."""
    detail = requests.get(f"{BASE}/bots/{bot_id}/detail", headers=HEADERS).json()
    bd = detail["bot_details"]
    if bd.get("TranscriptStatus") == "Failed":
        raise RuntimeError(f"Transcript failed: {bd}")
    tid = bd.get("transcript_id")
    if not tid:
        raise RuntimeError(f"No transcript_id for {bot_id}")
    resp = requests.get(f"{BASE}/transcript/{tid}/get_transcript", headers=HEADERS)
    if resp.status_code == 202:
        raise RuntimeError("Not ready yet")
    return resp.json()  # top-level array of segments


def get_metadata(bot_id: str) -> dict:
    """Read custom_attributes + meeting info for delivery routing."""
    detail = requests.get(f"{BASE}/bots/{bot_id}/detail", headers=HEADERS).json()
    return detail["bot_details"]
```

`app/webhook.py`:
```python
from app.meetstream import get_transcript, get_metadata
from app.summary import generate_summary
from app.delivery import deliver
from app.queue import is_duplicate

def handle_webhook(payload: dict):
    bot_id = payload.get("bot_id")
    event = payload.get("event")
    # Dedupe with timestamp || message fallback (lifecycle events lack timestamp)
    dedupe = f"{bot_id}:{event}:{payload.get('timestamp') or payload.get('message','')}"
    if is_duplicate(dedupe):
        return

    if event == "transcription.processed":
        # Path A success — fetch + summarize + deliver
        segments = get_transcript(bot_id)
        meta = get_metadata(bot_id)
        custom = meta.get("custom_attributes", {})
        summary = generate_summary(segments, meeting_link=meta.get("MeetingLink"))
        deliver(
            summary=summary,
            transcript=segments,
            user_email=custom.get("user_email"),
            tenant_id=custom.get("tenant_id"),
        )
    elif event == "transcription.failed":
        # Log + alert (don't retry — transcript_id stays Failed; would need /transcribe with different provider)
        alert_ops(bot_id, payload.get("message"))
    elif event == "bot.stopped" and payload.get("bot_status") != "Stopped":
        # NotAllowed / Denied / Error — meeting never recorded
        alert_user(bot_id, f"Bot couldn't join: {payload.get('bot_status')}")
```

`app/summary.py`:
```python
import os
from openai import OpenAI

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

SYSTEM = """You are a meeting analyst. From the transcript, extract:
1. Key Decisions (bulleted)
2. Action Items (with owner + deadline if mentioned)
3. Open Questions
4. 3-sentence Executive Summary

Be concise. Use the speaker names as-is."""

def generate_summary(segments: list[dict], meeting_link: str | None = None) -> str:
    formatted = "\n".join(f"{s['speaker']}: {s['transcript']}" for s in segments)
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"Meeting transcript:\n\n{formatted}"},
        ],
    )
    return resp.choices[0].message.content
```

`app/delivery.py` (Resend email; swap for Slack/Notion/HubSpot as needed):
```python
import os, resend

resend.api_key = os.environ["RESEND_API_KEY"]

def deliver(summary: str, transcript: list[dict], user_email: str, tenant_id: str):
    resend.Emails.send({
        "from": "notes@acme.com",
        "to": user_email,
        "subject": "Your meeting summary is ready",
        "html": f"<h1>Meeting Summary</h1><pre>{summary}</pre>",
    })
```

## Step 4: Tell the user what to do next

After scaffolding, hand them this checklist:

```
✅ Notetaker scaffolded at ./notetaker/

Next steps:
  1. cp .env.example .env  (fill in MEETSTREAM_API_KEY, OPENAI_API_KEY, RESEND_API_KEY, PUBLIC_URL)
  2. pip install -r requirements.txt  (or npm install)
  3. uvicorn app.main:app --reload --port 3000
  4. In another terminal: ngrok http 3000   (note the https URL)
  5. Set PUBLIC_URL=<your ngrok url> in .env, restart server
  6. Test: python scripts/start_bot.py "https://meet.google.com/abc-defg-hij" you@email.com
  7. Watch your webhook logs — you should see lifecycle events, then a summary email after the meeting ends.

🔧 Verify your account first if any provider call fails:
   Use the verify-account skill to check which transcription providers are configured.

📚 Reference: see the `meetstream` skill for full API details, lifecycle events, and edge cases.
```

## Defaults that matter (live-verified)

- `automatic_leave` defaults: 600/600/600/14400/300 (don't shorten unless you have a reason)
- `recording_config.retention.hours: 168` (7 days) — enough for the user to re-run summary if needed
- Always set `callback_url` — without it you have to poll
- Always stringify `custom_attributes` values defensively
- Webhook handler returns 2xx FIRST, then queues — non-2xx means lost event

## If the user wants live transcripts instead of post-call

This is a different product (live captions / real-time agent). Defer to the `sales-coach` skill, or read the `meetstream` skill's "STEP 4A — Live transcription path" decision tree.
