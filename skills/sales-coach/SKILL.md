---
name: sales-coach
description: >
  Build real-time sales coaching on the MeetStream Bot API: live transcription
  streams to your server while the call happens, your model spots objections,
  buying signals and talk-time imbalance, and your app shows coach cards to the
  seller. Use when the user says "real-time AI sales coach", "AI cue cards
  during calls", "live objection detection", "AI copilot for sales calls",
  "live conversation intelligence", "live meeting assistant", "real-time
  meeting intelligence", "live sales call analyzer", or "real-time AI call
  coaching". Gives the fastest path in numbered steps with the minimal API
  calls (curl, Node @meetstream/sdk, Python meetstream-sdk): a bot with a
  streaming provider (meetstream_streaming, no key) and
  live_transcription_required.webhook_url; links the sample apps as optional
  references. A coach that talks in the meeting is a voice agent: only on
  request (bridge server in realtime-streaming first, or hosted in
  mia-voice-agents).
---

# Sales coach (live)

A sales coach is the live Bot API path: the bot posts transcript updates to your server
during the call; your server runs your own model on them and pushes cards to the seller's
screen. MeetStream does not stream to the browser directly, and the API key must never
reach the browser. If the user wants a coach that speaks in the call, that is a voice
agent (`mia-voice-agents`), only on request.

No API key yet? Run `getting-started` first.

## Fastest path

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

## Things that matter

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

More on every live channel (raw audio, video, control socket): `realtime-streaming`.

Full example apps are optional references, not part of this plugin: "Tutorials and Sample
Apps" (https://docs.meetstream.ai/tutorials/sample-apps) and the labs repo
(https://github.com/meetstream-ai/labs).

## Latest docs

- Live transcription: https://docs.meetstream.ai/guides/transcription-recordings/live-transcription
- Transcription providers: https://docs.meetstream.ai/guides/transcription-recordings/providers/transcription-providers
- Webhooks and events: https://docs.meetstream.ai/guides/webhooks/webhooks-and-events
- Tutorials and sample apps: https://docs.meetstream.ai/tutorials/sample-apps

For the latest details, fetch the page with `.md` appended, read https://docs.meetstream.ai/llms.txt, or connect the docs MCP server at https://docs.meetstream.ai/_mcp/server.
