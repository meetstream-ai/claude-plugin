---
name: building-a-notetaker
description: >
  Build an AI meeting notetaker on the MeetStream Bot API: the bot joins,
  records and transcribes; your app fetches the transcript, summarizes it with
  your own model and delivers it (email, database, webhook). Use when the user
  says "build a notetaker", "AI meeting notetaker", "meeting recorder with AI
  summaries", "auto-summarize my meetings", "AI meeting summarizer", "meeting
  action items extractor", "meeting recap email", or any variant of a
  meeting-summary product. Gives the fastest path in numbered steps with the
  minimal API calls (curl, Node @meetstream/sdk, Python meetstream-sdk), the
  create_bot body (meetstream transcription by default, language set), and
  links the sample apps as optional references. Before the first Zoom bot: set up
  your Zoom app (recommended; OBF or ZAK token). The host must admit
  the bot (waiting room). Next step: calendar auto-join. If the request does
  not say post-call or live, ask that once first.
---

# Building a notetaker (post-call) or a live sales coach

A notetaker is a Bot API flow: send a bot, wait for the transcript, summarize it in your
app. MeetStream gives you the recording and the transcript; the summary and the delivery
(email, database, Slack and so on) are your app's job.

If the request does not already say which, ask once: should it work **after the meeting**
(transcript, notes, summary email) or **live, during the call** (live captions, coaching)?
Live goes to `streaming-live-data` (or `building-a-notetaker`). "Record my meetings" alone does not
say which, and neither does a request that names only the trigger ("a CLI that sends bots
to meeting links", "connect my calendar"). Do not suggest a voice agent unless asked.

No account or sign-in yet? Follow first-time setup in the `meetstream` router (`skills/meetstream/references/getting-started.md`). Everything below uses
`Authorization: Token $MEETSTREAM_API_KEY`.

**Before the first bot** (put both points in every notetaker answer, as a short "Before your first bot" list: the Zoom step when Zoom is in scope, and admission always):
- **Zoom:** set up your own Zoom app (recommended for reliable, fully supported Zoom). The
  bot then joins through it with an OBF token (on behalf of a user who is in the meeting) or a ZAK token (a signed-in bot), the way Zoom asks Meeting SDK
  apps to join since 2 March 2026. Set it up once before the first Zoom bot: create a
  Zoom Meeting SDK app, save its Client ID and Secret in the dashboard under
  Integrations > Zoom, and host the token URL (`zoom.obf_url` or `zoom.zak_url`).
  Guides: https://docs.meetstream.ai/guides/app-integrations/zoom-marketplace-app-setup and
  https://docs.meetstream.ai/guides/app-integrations/zoom-authenticated-bots
  (`setting-up-platforms` has the details). Google Meet and Teams guest bots need no app.
- **Admission:** the bot asks to join like a guest. Someone in the meeting (on Google Meet,
  the host or a co-host) must admit it from the waiting room or lobby. It waits
  `automatic_leave.waiting_room_timeout` seconds (default 600; Teams 1200), then ends as
  `NotAllowed`. `Denied` means a person declined it. Fixes: tell the host to expect the
  bot by name, open the meeting to guests, or use a signed-in bot (`setting-up-platforms`).
- **Supported platforms:** Zoom, Google Meet, Microsoft Teams, and WhatsApp calls (Beta;
  setup and limits in `setting-up-platforms`). Links from other services return 400.

## Fastest path

Always end the answer with one line that points to the optional full examples: "Full
example apps (optional): https://docs.meetstream.ai/tutorials/sample-apps and
https://github.com/meetstream-ai/labs."

1. **Send the bot** with a `callback_url` (your HTTPS webhook; use a tunnel for local dev).
2. **Wait for `transcription.processed`** on that webhook (it carries `bot_id`, not the
   transcript). Return 2xx at once, then do the work.
3. **Fetch the transcript:** `GET /bots/{bot_id}/detail` → `bot_details.transcript_id` →
   `GET /transcript/{transcript_id}/get_transcript` (a top-level array of segments; by
   default the speaker is `participant.name` and the text is `words[].text` joined).
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

- **Language:** set `language` to the meeting's language (`"es"`, `"ru"` and so on); the
  `meetstream` engine detects it when you send `"auto"` or omit it. Each provider has its
  own field and codes (`language_code` with `en_us` for AssemblyAI, `en-IN` style for
  Sarvam): https://docs.meetstream.ai/guides/transcription-recordings/languages-and-translation
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
    return lines(r.json())

def lines(segments: list) -> list[str]:
    """Default shape: {participant: {name}, words: [{text}]}; some providers: {speaker, transcript}."""
    out = []
    for seg in segments:
        name = (seg.get("participant") or {}).get("name") or seg.get("speaker") or "Unknown"
        words = seg.get("words") or []
        text = seg.get("transcript") or " ".join(
            (w.get("text") or w.get("punctuated_word") or w.get("word") or "").strip() for w in words)
        if text.strip():
            out.append(f"{name}: {text.strip()}")
    return out  # the meetstream engine can add a lone "Thank you." on silence: filler
```

- `transcription.failed` (or a 422 with `transcript_status: "Failed"` and the reason) is
  final. Fix the cause (for example the provider key), then re-run with
  `POST /bots/{bot_id}/transcribe`. Do not retry the same fetch.
- 202 means still processing: poll with a cap.
- **Polling instead of webhooks:** poll `GET /bots/{bot_id}/status` until `Done` (or a
  final failure: `NotAllowed`, `Denied`, `Failed`, `Error`, `MediaExpired`, `Cancelled`),
  with a time cap. Do not wait for `Stopped`: the bot can go `InMeeting` → `MediaProcessing`
  → `Done` between polls. Full list: `meetstream-cli`.
- **Shutdown:** on Ctrl-C or exit while the bot is still in the meeting, call
  `POST /api/v1/bots/{bot_id}/remove_bot`.
- Dedupe deliveries on `{bot_id, bot_event or event, timestamp}`; there are no
  redeliveries, so return 2xx first and queue the work. Signatures: `handling-webhooks` skill.

### 4. Summarize and deliver

Join the segments as `speaker: transcript` lines and give them to the user's model.
A good brief: decisions, action items with owners and dates, open questions. See
`meetstream-cli` for the format and talk-time.

**Who gets the email.** Meeting platforms do not give the bot participants' emails. With a
calendar connected to MeetStream, each participant the bot saw gets `calendar_email` from
the invite in `GET /bots/{bot_id}/get_participants` after the call (null when there is no
match). Otherwise use the invite list from your own calendar integration. MeetStream does
not send the email; your app does, with its own provider (Resend, SendGrid, SMTP).

From the user's own agent (no code): send the bot with the `create_bot` MCP tool, then
use `get_transcript` (takes `bot_id`) and summarize in the chat.

## Next step: calendar auto-join

Offer this after the first bot works: connect a Google or Outlook calendar once and a bot
joins every meeting on it with the same bot config, so nobody pastes links
(`scheduling-and-calendars`). It also fills `calendar_email` for the summary email.

## Options

- **WhatsApp group calls (Beta):** the same flow with a WhatsApp call link, `deepgram`
  post-call transcription only (`setting-up-platforms`).
- **Per-speaker audio:** `"audio_separate_streams": true`, then `get_audio_streams`
  (`getting-transcripts-and-media`).
- **Live notes during the call:** `streaming-live-data`.

Full example apps are optional references, not part of this plugin: "Tutorials and Sample
Apps" (https://docs.meetstream.ai/tutorials/sample-apps) and the labs repo
(https://github.com/meetstream-ai/labs).

## Live sales coach (was sales-coach)

A sales coach is the live Bot API path: the bot posts transcript updates to your server
during the call; your server runs your own model on them and pushes cards to the seller's
screen. MeetStream does not stream to the browser directly, and the API key must never
reach the browser. If the user wants a coach that speaks in the call, that is a voice
agent (`building-voice-agents`), only on request.

No account or sign-in yet? Follow first-time setup in the `meetstream` router (`skills/meetstream/references/getting-started.md`).

### Fastest path

Always end the answer with one line that points to the optional full examples: "Full
example apps (optional): https://docs.meetstream.ai/tutorials/sample-apps and
https://github.com/meetstream-ai/labs."

1. **Send a bot with a streaming provider** and your HTTPS live-transcript URL.
2. **Receive the POSTs** on that URL: each one has `speakerName`, `transcript`,
   `is_final` and `end_of_turn`. Return 2xx fast.
3. **On each finished turn** (`end_of_turn: true`), run your model on the recent turns
   (objections, buying signals, talk time, dodged questions).
4. **Push the card** to the seller's page over Server-Sent Events or a WebSocket that you
   host. Render card text with `textContent`, never `innerHTML` (model output is
   untrusted).
5. **Stop** with `POST /api/v1/bots/{bot_id}/remove_bot` (GET also works; MCP `remove_bot`)
   when the call ends, and on Ctrl-C or exit of your app; `bot.done` on the webhook says the call finished.

```bash
curl -X POST https://api.meetstream.ai/api/v1/bots/create_bot \
  -H "Authorization: Token $MEETSTREAM_API_KEY" -H "Content-Type: application/json" \
  -d '{
    "meeting_link": "https://us06web.zoom.us/j/84512345678",
    "bot_name": "Coach",
    "video_required": false,
    "callback_url": "https://your-app.example/meetstream/webhook",
    "live_transcription_required": {"webhook_url": "https://your-app.example/meetstream/live"},
    "recording_config": {"transcript": {"provider": {"meetstream_streaming": {}}}}
  }'
```

Node (`npm install @meetstream/sdk`):
```ts
import { MeetStream } from '@meetstream/sdk';
const ms = new MeetStream(); // reads MEETSTREAM_API_KEY
await ms.bots.create({
  meeting_link, bot_name: 'Coach', video_required: false,
  live_transcription_required: { webhook_url: `${PUBLIC_URL}/meetstream/live` },
  recording_config: { transcript: { provider: { meetstream_streaming: {} } } },
});
```

Python (`pip install meetstream-sdk`):
```python
from meetstream import MeetStream
ms = MeetStream()  # reads MEETSTREAM_API_KEY
ms.bots.create({
    "meeting_link": meeting_link, "bot_name": "Coach", "video_required": False,
    "live_transcription_required": {"webhook_url": f"{PUBLIC_URL}/meetstream/live"},
    "recording_config": {"transcript": {"provider": {"meetstream_streaming": {}}}},
})
```

A live chunk (one POST per transcript update):
```json
{"bot_id": "...", "speakerName": "Alice", "timestamp": "2026-05-26T10:21:43.681Z",
 "transcript": "Can you walk me through pricing", "is_final": true, "end_of_turn": true,
 "words": [], "custom_attributes": {}}
```

### Things that matter

- `live_transcription_required.webhook_url` needs a streaming provider, else 400.
  `meetstream_streaming` works with no provider key; `deepgram_streaming` and
  `assemblyai_streaming` need the user's own key.
- Streaming-only bots make no post-call transcript: no `transcription.processed`, and a
  post-call fetch keeps returning 202. Use `bot.done` as "call finished". For a transcript
  afterwards, call `POST /bots/{bot_id}/transcribe` with a post-call provider.
- `bot.error` is a streaming-provider warning: the bot keeps recording, only the live
  feed is hit. Show it to the seller as a warning card.
- Dedupe on `{bot_id, bot_event or event, timestamp}`.
- Talk time: sum turn durations per `speakerName`; flag a seller share over about 70%.
- Raise the bot's hand: `POST /api/v1/bots/{bot_id}/send_command` `{"command": "raise_hand"}`.

More on every live channel (raw audio, video, control socket): `streaming-live-data`.

Full example apps are optional references, not part of this plugin: "Tutorials and Sample
Apps" (https://docs.meetstream.ai/tutorials/sample-apps) and the labs repo
(https://github.com/meetstream-ai/labs).

## More use cases

Record and transcript, real-time transcription, interactive bot, calendar bot, full notetaker pipeline, participant tracking, live audio frames and agents, each as a fastest path: [`references/use-case-patterns.md`](references/use-case-patterns.md). A starter template (`meetstream init notetaker`) comes in the next CLI release; today build from the steps above.

## Latest docs

- Create your first bot: https://docs.meetstream.ai/guides/get-started/create-your-first-bot
- Post-call transcription: https://docs.meetstream.ai/guides/transcription-recordings/post-call-transcription
- Zoom setup (your Zoom app, OBF and ZAK): https://docs.meetstream.ai/guides/platforms/zoom
- Calendar emails on participants: https://docs.meetstream.ai/guides/features/calendar-emails-on-participants

For the latest details, fetch the page with `.md` appended, read https://docs.meetstream.ai/llms.txt, or connect the docs MCP server at https://docs.meetstream.ai/_mcp/server.
