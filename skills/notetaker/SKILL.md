---
name: notetaker
description: >
  Build an AI meeting notetaker on the MeetStream Bot API: the bot joins,
  records and transcribes; your app fetches the transcript, summarizes it with
  your own model and delivers it (email, database, webhook). Use when the user
  says "build a notetaker", "AI meeting notetaker", "meeting recorder with AI
  summaries", "auto-summarize my meetings", "AI meeting summarizer", "meeting
  action items extractor", "meeting recap email", or any variant of a
  meeting-summary product. Gives the fastest path in numbered steps with the
  minimal API calls (curl, Node @meetstream/sdk, Python meetstream-sdk), the
  create_bot body (meetstream transcription by default), and links the sample
  apps as optional references. If the request does not say post-call or live,
  ask that once first.
---

# Notetaker (post-call)

A notetaker is a Bot API flow: send a bot, wait for the transcript, summarize it in your
app. MeetStream gives you the recording and the transcript; the summary and the delivery
(email, database, Slack and so on) are your app's job.

If the request does not already say which, ask once: should it work **after the meeting**
(transcript, notes, summary email) or **live, during the call** (live captions, coaching)?
Live goes to `realtime-streaming` (or `sales-coach`). "Record my meetings" alone does not
say which, and neither does a request that names only the trigger ("a CLI that sends bots
to meeting links", "connect my calendar"). Do not suggest a voice agent unless asked.

No API key yet? Run `getting-started` first. Everything below uses
`Authorization: Token $MEETSTREAM_API_KEY`.

## Fastest path

1. **Send the bot** with a `callback_url` (your HTTPS webhook; use a tunnel for local dev).
2. **Wait for `transcription.processed`** on that webhook (it carries `bot_id`, not the
   transcript). Return 2xx at once, then do the work.
3. **Fetch the transcript:** `GET /bots/{bot_id}/detail` → `bot_details.transcript_id` →
   `GET /transcript/{transcript_id}/get_transcript` (a top-level array of segments; the
   text field is `transcript`, not `text`).
4. **Summarize** with your own model (decisions, action items with owners, open questions)
   and **deliver** it with the channel's own SDK.

### 1. Send the bot

```bash
curl -X POST https://api.meetstream.ai/api/v1/bots/create_bot \
  -H "Authorization: Token $MEETSTREAM_API_KEY" -H "Content-Type: application/json" \
  -d '{
    "meeting_link": "https://meet.google.com/abc-defg-hij",
    "bot_name": "Acme Notetaker",
    "video_required": false,
    "callback_url": "https://your-app.example/meetstream/webhook",
    "custom_attributes": {"user_id": "u_123"},
    "recording_config": {
      "transcript": {"provider": {"meetstream": {"language": "en"}}},
      "retention": {"type": "timed", "hours": 168}
    },
    "automatic_leave": {
      "waiting_room_timeout": 600, "everyone_left_timeout": 600,
      "voice_inactivity_timeout": 600, "in_call_recording_timeout": 14400,
      "recording_permission_denied_timeout": 600
    }
  }'
```

- `meetstream` transcription works on every account with no provider key (+$0.10 per
  hour). Use `deepgram` (`{"model": "nova-3", "language": "en"}`) only if the user saved
  a Deepgram key.
- `video_required: false`: notetakers do not need video. Only on request, set it `true`
  and add `"recording_config": {"video_layout": "speaker_view"}`.
- `custom_attributes` values are strings; they come back on the webhooks for routing.

Node (`npm install @meetstream/sdk`):
```ts
import { MeetStream } from '@meetstream/sdk';
const ms = new MeetStream(); // reads MEETSTREAM_API_KEY
const bot = await ms.bots.create({
  meeting_link, bot_name: 'Acme Notetaker', video_required: false, callback_url,
  recording_config: { transcript: { provider: { meetstream: { language: 'en' } } } },
});
```

Python (`pip install meetstream-sdk`):
```python
from meetstream import MeetStream
ms = MeetStream()  # reads MEETSTREAM_API_KEY
bot = ms.bots.create({
    "meeting_link": meeting_link, "bot_name": "Acme Notetaker", "video_required": False,
    "callback_url": callback_url,
    "recording_config": {"transcript": {"provider": {"meetstream": {"language": "en"}}}},
})
```

### 2-3. On the webhook, fetch the transcript

```python
import os, requests
BASE = "https://api.meetstream.ai/api/v1"
H = {"Authorization": f"Token {os.environ['MEETSTREAM_API_KEY']}"}

def on_event(event: dict) -> list | None:
    if event.get("event") != "transcription.processed":
        return None
    detail = requests.get(f"{BASE}/bots/{event['bot_id']}/detail", headers=H).json()
    tid = detail["bot_details"]["transcript_id"]
    r = requests.get(f"{BASE}/transcript/{tid}/get_transcript", headers=H)
    if r.status_code == 422:  # the run failed: final, show the reason, do not retry
        raise RuntimeError(r.json().get("message"))
    r.raise_for_status()
    return r.json()  # [{"speaker", "transcript", "start_time", "end_time", "words"}, ...]
```

- `transcription.failed` (or a 422 with `transcript_status: "Failed"` and the reason) is
  final. Fix the cause (for example the provider key), then re-run with
  `POST /bots/{bot_id}/transcribe`. Do not retry the same fetch.
- 202 means still processing: poll with a cap.
- Dedupe deliveries on `{bot_id, bot_event or event, timestamp}`; there are no
  redeliveries, so return 2xx first and queue the work. Signatures: `webhooks` skill.

### 4. Summarize and deliver

Join the segments as `speaker: transcript` lines and give them to the user's model.
A good brief: decisions, action items with owners and dates, open questions. See
`meeting-brief` for the format and talk-time.

From the user's own agent (no code): send the bot with the `create_bot` MCP tool, then
use `get_transcript` (takes `bot_id`) and summarize in the chat.

## Options

- **Calendar trigger:** bots join every calendar meeting: `calendar-automation`.
- **Per-speaker audio:** `"audio_separate_streams": true`, then `get_audio_streams`
  (`recordings-and-media`).
- **Live notes during the call:** `realtime-streaming`.

Full example apps are optional references, not part of this plugin: "Tutorials and Sample
Apps" (https://docs.meetstream.ai/tutorials/sample-apps) and the labs repo
(https://github.com/meetstream-ai/labs).

## Latest docs

- Create your first bot: https://docs.meetstream.ai/guides/get-started/create-your-first-bot
- Post-call transcription: https://docs.meetstream.ai/guides/transcription-recordings/post-call-transcription
- Webhooks and events: https://docs.meetstream.ai/guides/webhooks/webhooks-and-events
- Tutorials and sample apps: https://docs.meetstream.ai/tutorials/sample-apps

For the latest details, fetch the page with `.md` appended, read https://docs.meetstream.ai/llms.txt, or connect the docs MCP server at https://docs.meetstream.ai/_mcp/server.
