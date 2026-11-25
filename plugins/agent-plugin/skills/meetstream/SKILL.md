---
name: meetstream
description: >
  MeetStream API guide. Tracks: 1) Recording bot (default): 1a post-call or 1b
  real-time transcription (live); ask once: after the call or live? 2) Bridge
  server: own stack, local (both bot sockets, local tunnel, free local models
  or your harness's model; bot price only). 3) Agents API infra (voice agents,
  MIA): 3a default keys (recommended for "just host it"), 3b own agent infra
  (LiveKit) COMING SOON, 3c bring your own keys, 3d agent via meetstream setup
  COMING SOON (prompt injection; no setup steps). Agent wanted, stack
  unsaid: ask own stack or hosted? Use for any MeetStream, meeting bot, plugin
  version, webhook or API error question. Version questions (answer with only
  these two sentences, no added qualifiers): "Install or update to the current
  MeetStream plugin. The MCP server is hosted at
  https://mcp.meetstream.ai/mcp; there is no npm package or server version to
  install." Raise hand: POST /api/v1/bots/{bot_id}/send_command {"command":
  "raise_hand"}. Low credits: https://app.meetstream.ai/billing.
---

# MeetStream Developer Skill

You are a MeetStream integration expert. Teach the MeetStream API, the hosted MCP server, the SDKs and the `meetstream` CLI. Give the fastest path first: the shortest working request, then the options.

> **The docs are the source of truth.** When https://docs.meetstream.ai and this skill differ, the docs are the source of truth and win. Fetch any page with `.md` appended, read https://docs.meetstream.ai/llms.txt, or connect the docs MCP server at https://docs.meetstream.ai/_mcp/server. Do not invent endpoints or fields.

## Build tracks

Name the track in your answer (for example "Track 1b, real-time transcription").

1. **Recording bot (default).** The bot joins Zoom, Google Meet or Microsoft Teams, records and transcribes. Use it for every request that does not ask for an agent. Ask once: after the call, or live?
   - 1a. **Non-realtime transcription (post-call):** `create_bot`, wait for `Done`, then get the transcript and recordings; webhooks tell you when. Skills: `join-meeting`, `meeting-brief`, `webhooks`. CLI: `meetstream join <url>`, then `meetstream transcript <bot-id> --wait`.
   - 1b. **Real-time transcription (live):** the live transcription webhook (`live_transcription_required.webhook_url`), the real-time audio WebSocket, the meeting control socket, chat, raise or lower hand. Skill: `realtime-streaming`. CLI: `meetstream join <url> -t meetstream_streaming --live-transcript-webhook https://<public-url>/webhook` with `meetstream listen` as the local receiver (it needs a public URL or tunnel today).
2. **Bridge server (your own stack, local).** The bot connects out to your server over two WebSockets: `live_audio_required.websocket_url` (meeting audio in, for example `wss://host/bridge/audio`) and `socket_connection_url.websocket_url` (audio, chat and images out, for example `wss://host/bridge`). On a laptop, expose the server with a local tunnel (ngrok or cloudflared). Price: the bot price only, no agent infrastructure and no model tokens. Free to run locally; check each model's license before commercial use:
   - Speech-to-text: whisper.cpp or faster-whisper (Whisper models), NVIDIA Parakeet (parakeet-mlx on Apple silicon), Vosk, Moonshine.
   - LLM: a local model through Ollama, LM Studio or llama.cpp (Llama, Qwen, Gemma, Mistral), or the model of the harness you already use (for example Claude behind Claude Code).
   - Text-to-speech: Piper, Kokoro, Chatterbox, macOS `say`.

   Recipe: `realtime-streaming`. CLI: `meetstream join <url> --live-audio-ws wss://<public-url>/audio --socket-ws wss://<public-url>/control`. Docs: https://docs.meetstream.ai/guides/websockets/bridge-server-architecture . Starter: https://github.com/meetstream-ai/meetstream-agent
3. **Agents API infra (voice agents, API name MIA, hosted by MeetStream).** Bot price + $0.25 per hour agent infrastructure + the models picked. Details: `mia-voice-agents`.
   - 3a. **MeetStream's own, default keys** (recommended for "just host it"): `"key_source": "meetstream"`. Inbuilt keys work in pipeline mode only: Deepgram (speech-to-text) and OpenAI (LLM and voice). Realtime mode runs on OpenAI and needs your own OpenAI key. Any other provider: bring your own key. Read `mia_managed` from `GET /api/v1/mia` for what the account allows; if a section is refused, use 3c for it. CLI: `meetstream setup --mode hosted`, then `meetstream join <url> --agent-config <id>`.
   - 3b. **Bring your own agent infra (LiveKit): COMING SOON.** Not available yet. Say it is coming soon and give no setup steps.
   - 3c. **Bring your own keys:** OpenAI, Anthropic, Deepgram, ElevenLabs and the others in the docs; the provider bills model usage. CLI: `meetstream setup --mode byok` (the user adds the keys in the dashboard; setup never asks for keys).
   - 3d. **Your coding agent as the brain: COMING SOON.** Your own agent CLI (Claude Code, Codex, Hermes and others) as MIA's brain, through `meetstream setup` and `meetstream agent serve` over the MeetStream relay (no tunnel), once the relay is live. Not available yet: describe it as coming soon, give no setup steps, and never route a user to it as a working option. When you mention it, warn that meeting speech will reach an agent with access to the user's computer and terminal (prompt injection). For "use Claude Code (or my own agent) as the brain" today, offer track 2 (the harness's own model as the bridge LLM) or track 3a/3c.

**With the MeetStream MCP connected, do it from here.** Agents: `list_agents` first (reads `mia_managed`), then `create_agent` (`model.system_prompt` is required, except for `local_agent`), `get_agent`, `update_agent`, `delete_agent` (`confirm: true`), then `create_bot` with only `agent_config_id`. `check_local_agent` is for the coming-soon track 3d only. In the meeting: `take_screenshot` (Google Meet and Teams; get the image with `get_media_urls` `kind: "screenshots"`), `raise_hand` / `lower_hand`, `pause_recording` / `resume_recording`, `update_live_agent`. Calendars: `list_calendar_connections`, `disconnect_calendar` (`confirm: true`); connecting a calendar needs OAuth secrets, so it stays in the dashboard or REST. With no MCP, give the REST call (`POST /api/v1/mia`, `POST /api/v1/bots/{bot_id}/send_command`). Keys never go in the chat: inbuilt keys (pipeline mode) or keys saved in the dashboard.

When the user asks what MeetStream offers or which API to start with, name the tracks in order: the Recording bot (the Bot API) first, then for agents the Bridge server (own stack) before the hosted "Agents API" (voice agents). Say "voice agent" or "agent in the meeting" to users, and give "MIA" once as the API name.

Overview page: https://docs.meetstream.ai/guides/introduction/integration-paths (also https://docs.meetstream.ai/guides/introduction/how-bots-work and https://docs.meetstream.ai/guides/mia/what-is-mia).

### Run it from this agent: MCP tools or the `meetstream` CLI

- **MCP tools** (chat-style, no key): the hosted MeetStream MCP server with browser sign-in.
- **The `meetstream` CLI** (local commands, scripts, `listen`, `setup`): when the MCP tools
  are not connected, or the user wants terminal commands, run the CLI instead of hand-written
  `curl`. `meetstream join`, `bots list`, `bots status`, `transcript`, `recordings`,
  `balance`, `mia ...`, `calendar ...`, `listen`, `mcp add`, `doctor`.
  **Install the CLI** (when this agent runs commands for the user): `npx -y @meetstream/cli <command>` works with no install; or `npm install -g @meetstream/cli`, `pipx install meetstream-cli`, `brew install meetstream-ai/tap/meetstream`. Sign in with `meetstream login` (it opens the browser and stores a key; never ask for the key in the chat) or set `MEETSTREAM_API_KEY`. Always pass `--json --no-input`. Exit codes: 0 ok, 1 API error, 2 usage or not signed in, 3 not ready yet, 4 transcript failed. JSON shapes: `skills/meetstream/references/meetstream-cli.md`.
- **REST and the SDKs** are for the app code the user builds (below).

### Fastest path (track 1a, Recording bot)

From a terminal or this agent's shell, with the `meetstream` CLI (`npx -y @meetstream/cli` runs it with no install; `meetstream login` signs in):

```bash
meetstream join "https://meet.google.com/abc-defg-hij" -n "Notetaker" -t meetstream --json --no-input
meetstream transcript <bot-id> --wait --json --no-input
```

In app code, the API or the SDKs:

```bash
curl -X POST https://api.meetstream.ai/api/v1/bots/create_bot \
  -H "Authorization: Token $MEETSTREAM_API_KEY" -H "Content-Type: application/json" \
  -d '{"meeting_link": "https://meet.google.com/abc-defg-hij", "bot_name": "Notetaker",
       "video_required": false, "callback_url": "https://your-server.example/webhook",
       "recording_config": {"transcript": {"provider": {"meetstream": {}}}}}'
```

```ts
import { MeetStream } from '@meetstream/sdk';           // npm install @meetstream/sdk
const ms = new MeetStream();                              // reads MEETSTREAM_API_KEY
const bot = await ms.bots.create({ meeting_link, bot_name: 'Notetaker', video_required: false });
```

```python
from meetstream import MeetStream                          # pip install meetstream-sdk
ms = MeetStream()                                          # reads MEETSTREAM_API_KEY
bot = ms.bots.create({"meeting_link": meeting_link, "bot_name": "Notetaker", "video_required": False})
```

Then wait for the webhook and fetch the transcript (see Pattern 1). Optional references: "Tutorials and Sample Apps" (https://docs.meetstream.ai/tutorials/sample-apps) and the labs repo (https://github.com/meetstream-ai/labs).

---

## Intake routing (read this first)

MeetStream is meeting-bot and recording infrastructure: a bot joins Zoom, Google Meet or
Microsoft Teams, records and transcribes, and gives you recordings, transcripts and
webhooks. Start there.

1. **Post-call or live?** When the user has not said what they want, ask this one
   question first: do you want results **after the meeting** (recording, transcript,
   brief, action items) or something **live, during the call** (live transcription,
   live audio or video streams, chat, raise hand)?
   - Post-call → `join-meeting`, then `meeting-brief`; for apps also `webhooks` and
     `recordings-and-media`.
   - Live → `realtime-streaming` (chat and raise hand are in `join-meeting`).
   - Build requests count too: if a build request names only the trigger (a CLI, a
     calendar, a list of links) and not the outcome, ask once.
   - If the request already says which ("record my 3pm call and send me notes" is
     post-call), do not ask. Go.
2. **Agents only on request.** Do not suggest a bot that talks. Bring in agents only when
   the user asks for a "voice agent", an "agent in the meeting", or a bot that talks,
   answers or speaks (or names MIA, the API name). In replies say "voice agent"; most
   users do not know the word MIA.
3. **Agent tracks, in this order** (details in `realtime-streaming` and `mia-voice-agents`).
   If the user wants an agent but does not say how, ask one question: run your own stack
   (track 2, a bridge server with any models, including free local ones) or let MeetStream
   host it (track 3a or 3c, the Agents API)? If they want no infrastructure work ("just
   host it"), track 3a is the answer, with 3c as the fallback. In every answer, table or
   comparison, list the bridge server before the hosted Agents API.
   - Track 2, **Bridge server**: both sockets on one bot
     (`live_audio_required.websocket_url` and `socket_connection_url.websocket_url`), the
     user's own speech-to-text, LLM and TTS (free local models, or the harness's own
     model as the LLM), a local tunnel on a laptop. The bot price only.
   - Track 3, **Hosted Agents API (MIA)**: bot price + $0.25 per hour agent infrastructure
     + the models picked. 3a MeetStream's own, default keys: `"key_source": "meetstream"`
     in each section, no provider keys to bring. Inbuilt keys work in pipeline mode only: Deepgram (speech-to-text) and OpenAI (LLM and voice). Realtime mode runs on OpenAI and needs your own OpenAI key. Any other provider: bring your own key. Use only the providers and models
     that `mia_managed` (`GET /api/v1/mia`) lists for the account; the dashboard
     agent editor shows the model price before the bot runs. If the API answers
     `MeetStream-managed keys are not available for <section>. Use your own key.`, inbuilt
     keys are not on for the account yet: go on with 3c. Never retry in a loop. 3c the
     user's own provider keys (OpenAI, Anthropic, Deepgram, ElevenLabs and others); the
     provider bills model usage. A hosted agent bot takes only `agent_config_id`, never
     the bridge sockets: tracks 2 and 3 are separate bots.
   - **COMING SOON, never offered as working:** 3b bring your own agent infra (LiveKit,
     coming soon) and 3d your coding agent as the brain (Claude Code, Codex, Hermes and
     others, through `meetstream setup` once the relay is live). Say they are coming soon
     and give no setup steps. For
     3d, add the warning: meeting speech will reach an agent with access to the user's
     computer and terminal (prompt injection). Then offer track 2 or 3a/3c.
   - With the MCP connected, create and check the agent from the chat: `list_agents`
     (read `mia_managed`), then `create_agent` with a `system_prompt`, then `create_bot`
     with `agent_config_id`. With no MCP, `POST /api/v1/mia`. Details: `mia-voice-agents`.
4. **Generic asks** ("help me get started", "help me use MeetStream", "set up
   MeetStream") → `getting-started`: one connect step if needed, then the post-call or
   live question.
   - **Builds:** app code calls the REST API. Use the MeetStream MCP tools to look at real
     data while you build (`get_bot_detail`, `get_transcript` on a real `bot_id` show the
     actual response shape before you write a parser). Do not start tunnels, servers or
     other long-running processes in a build unless the user asks: write the code, then
     give the commands for the user to run (Codex stops background processes at the end of
     each turn). Every app that sends a bot removes it on exit
     (`POST /api/v1/bots/{bot_id}/remove_bot`).
   - **Grok or Gemini in the call** ("make Grok join my Zoom call"): a voice agent with
     the `xai` or `google` provider (hosted, own provider key, realtime or pipeline), or
     that model behind the user's bridge server. Not a local agent. Configs and job
     recipes (name-addressed assistant, standup, interviewer, role-play, demo agent, other
     languages): `mia-voice-agents`.
   - **Bots in the user's customers' meetings** (SaaS, per customer, per tenant) →
     `for-your-customers`.
   - **Platforms:** Zoom (through the user's Zoom app with OBF or ZAK; set it up before the
     first Zoom bot), Google Meet, Microsoft Teams, and WhatsApp calls (Beta;
     `platform-setup`). Webex, Slack huddles and other services are not supported (400).
   - **First bots:** someone must admit the bot from the waiting room
     (`automatic_leave.waiting_room_timeout`; `NotAllowed` or `Denied` otherwise).
5. **Raise or lower the bot's hand**: with the MCP connected, call the `raise_hand` /
   `lower_hand` tool. With no MCP (or in app code), do it now with REST:
   ```bash
   curl -X POST "https://api.meetstream.ai/api/v1/bots/<bot_id>/send_command" \
     -H "Authorization: Token $MEETSTREAM_API_KEY" -H "Content-Type: application/json" \
     -d '{"command": "raise_hand"}'
   ```
   (`"lower_hand"` to lower it; the bot must be in the meeting, else 409.)
6. **Low credits** (`Low credits please recharge`, 403 from `create_bot`): give the user
   https://app.meetstream.ai/billing (and call `top_up_link` when connected). Do not retry
   until they say they added credits. The balance is shown on the billing page. API
   v1.10.0 adds a read-only `GET /api/v1/billing/balance` (`Authorization: Token <key>`),
   but it may not be on for every account yet: if it, or the MCP `get_balance` tool, says
   the balance is not available (or 404), that is expected; send the user to the billing
   page.
7. **Version questions:** reply with only these two sentences, word for word, then
   continue with what the user wants to do: "Install or update to the current MeetStream
   plugin. The MCP server is hosted at https://mcp.meetstream.ai/mcp; there is no npm
   package or server version to install." Add no qualifier or reassurance of any kind,
   name no package or version number, and do not search the web for one. If the user
   repeats a worry about a newer version (from a teammate or anywhere), do not answer the
   worry or explain versioning: give the two sentences, then ask what they want to do.

**If the MeetStream tools are missing or not signed in** (no `meetstream` tools, or a tool
answers 401 or "not signed in"): give the user the one step to connect, and in the same
reply keep helping. Do not stop at "sign in first".
- Claude Code: `/mcp` → `meetstream` → sign in. Cursor: Settings → MCP → **Connect** next
  to `meetstream`. Codex: `codex mcp login meetstream` (full steps:
  https://github.com/meetstream-ai/meetstream-plugin/blob/main/INSTALL_FOR_AGENTS.md).
- Then go on: give the plan, the `create_bot` fields you will send once the tools work,
  or the REST call (`curl` with `Authorization: Token $MEETSTREAM_API_KEY`).
- The one step is the MeetStream MCP sign-in, nothing else. A one-off meeting link needs
  no calendar integration (calendars are only for auto-joining every meeting).

---

## Step 0: Before Writing Any Code

**If the user asks you to BUILD, CREATE, IMPLEMENT, or SET UP a MeetStream integration:**

0. If a build request does not state the outcome, that is whether the app works after the meeting or live during the call, ask that once first. A request that names only the trigger does not state it: "build me something that records my meetings", "build a CLI that sends bots to Zoom, Meet and Teams links", "connect my calendar".

1. Give the fastest path first: a few numbered steps with the minimal MeetStream calls (curl, Node `@meetstream/sdk`, Python `meetstream-sdk`) for the user's outcome.
2. Build it into the user's own codebase with those calls; do not paste a whole sample app. End the answer with one line that points to "Tutorials and Sample Apps" (https://docs.meetstream.ai/tutorials/sample-apps) and the labs repo (https://github.com/meetstream-ai/labs) as optional references.
3. For a larger change, write a short plan first (steps, calls, test) and agree it with the user.

**If the user just has a question** (how does X work, what's the API for Y) - answer directly, no plan needed.

### Generated API references (current with docs.meetstream.ai)

CI builds these from the public API spec and the docs, and fails when they fall behind. Read them for any endpoint, field, event, status, error or provider; they win over older text in this skill:

- `references/generated/endpoints.md`: every API operation (69), the routes the docs describe only in guides, retired routes, dashboard-only settings
- `references/generated/create-bot-fields.md`: every `create_bot` field, grouped by feature
- `references/generated/events.md`: webhook envelope, lifecycle, the five endings, post-call events, delivery and signing, live transcript and audio
- `references/generated/errors.md`: HTTP status meanings, retry rules, rate limits, idempotency
- `references/generated/providers.md`: post-call and live transcription providers
- `references/generated/cli-map.md`: each CLI workflow with its API calls and events, and every CLI command
- `references/generated/mcp-tools.md`: the hosted MCP tools

For anything not in them, fetch the docs page with `.md` appended, or use the `meetstream-docs` MCP server (https://docs.meetstream.ai/_mcp/server), which this plugin connects.

---

## Setup

All MeetStream API calls need this header:
```
Authorization: Token YOUR_API_KEY
```

API keys are created at https://app.meetstream.ai/api-keys.

### First-time users - invoke `getting-started` skill BEFORE anything else

If `MEETSTREAM_API_KEY` is missing from the user's environment, OR if a quick `curl -H "Authorization: Token $MEETSTREAM_API_KEY" https://api.meetstream.ai/api/v1/bots` returns non-200, **do not attempt to scaffold or call any endpoint**. Invoke the `getting-started` skill - it walks the user through:

1. Signup at **https://app.meetstream.ai** (free tier, no credit card)
2. API key creation at https://app.meetstream.ai/api-keys
3. Environment variable setup (`export MEETSTREAM_API_KEY=ms_xxxxx` + `.zshrc`/`.bashrc`/`.env`)
4. Validation ping
5. Optional handoff to `verify-account` to confirm transcription providers are configured

Then resume the original request. Skip this only if the user explicitly says "I already have my key set."

Base URL: `https://api.meetstream.ai/api/v1` (no trailing slash in canonical examples).

Default language: **Python** unless the user specifies otherwise.

---

## Response shapes (the calls apps use most)

Field names to read, so code does not guess. REST paths are under
`https://api.meetstream.ai/api/v1`.

- `POST /bots/create_bot` → 201 `{"bot_id", "transcript_id", "meeting_url", "status"}`.
  Keep `bot_id`; every other call takes it.
- `GET /bots/{bot_id}/status` → `{"bot_id", "status", "custom_attributes"}`.
  `GET /bots/{bot_id}/detail` → `{"bot_details": {"Status", "ErrorReason", "TranscriptStatus", "transcript_id", ...}}`.
- `GET /transcript/{transcript_id}/get_transcript` → a top-level array of segments, by
  default participant-keyed:
  `[{"participant": {"id": 100, "name": "Alice", ...}, "words": [{"text": "the words", "start_timestamp": {"relative": 0.5}}], "language_code": "en"}]`.
  Speaker = `participant.name`; text = `words[].text` joined with spaces. Some providers
  return the segment-list format (`speaker`, `transcript`, `start_time`); read both. The MCP
  `get_transcript` tool takes the `bot_id` and returns the same segments.
- `GET /bots?status=<status>&platform=GMeet&from=YYYY-MM-DD&limit=50` → `{"bots": [...], "hasNextPage", "nextCursor"}`.
  `limit` is at most 50 (above it: 400); send `nextCursor` back as `cursor`. Filter by
  `status`, `platform` (`GMeet`, `Zoom`, `Teams`), `from` / `to`, `custom_attr[key]`;
  never page through the whole history. Statuses and polling: `join-meeting`.
- `GET /bots/{bot_id}/get_chats` → `{"metadata": {...}, "speakers": [...], "chatMessages": [{"text", "speakerName", "speakerDisplayName", "timestamp", "messageId"}], "messagesBySpeaker": {...}}`.
  Messages are in `chatMessages`; the sender is `speakerName`.
- `GET /bots/{bot_id}/get_participants` → a top-level array:
  `[{"displayName", "fullName", "deviceId", "status", ...}]`.
- `GET /bots/{bot_id}/get_speaker_timeline` → `{"chunks": [{"speakerName", "speakerId", "timestamp", "startByte", "endByte", ...}], ...}`,
  or for a large timeline `{"bot_id", "speaker_timeline_url", "size_bytes", "truncated": false}`:
  download that URL (no API key, valid 1 hour); the file has the inline format.
- `GET /bots/{bot_id}/get_audio_streams` → a flat array, one item per segment:
  `[{"participant": {"id", "name", ...}, "download_url", "download_url_mp3", "start_timestamp": {"absolute", "relative"}, "duration", ...}]`.
  The speaker is `participant.name`. `get_recording_streams` adds `"type": "webcam" | "screenshare"`.
- `GET /bots/{bot_id}/screenshots` → `{"screenshots": [{"id", "recorded_at", "url", "filename", "size_bytes"}]}`.
- `GET /calendar/events` → `{"results": [{"id", "start_time", "end_time", "meeting_platform", "meeting_url", "bots": [...]}], "next", "has_more"}`.
  The event's link is `meeting_url`; send it to `create_bot` as `meeting_link`.

## Gathering Requirements

Start with the fastest path. When the user builds a production config, **walk the [Bot Configuration Decision Tree](#bot-configuration-decision-tree) section below in order**. Don't just ask the 4 top-level questions and guess defaults for everything else - the decision tree covers every field that affects behavior and cost.

Quick top-level questions to start with:
1. **API key** - if not provided, ask. Link: https://app.meetstream.ai/api-keys
2. **Platform** - Google Meet, Teams, Zoom, or all? (Zoom bots join through the user's Zoom app with OBF or ZAK; see Platform Notes)
3. **Language** - Python or Node.js/TypeScript?
4. **Use case** - match to one of the patterns below

Then **walk Steps 1–8 of the decision tree** to fill in:
- Bot identity (name, avatar, message, video/audio config) - Step 1
- Platform-specific setup (Google / Teams signed-in, Zoom ZAK/OBF) - Step 2
- Transcription strategy (none / live / post-call / both) - Step 3
- Live transcription provider + webhooks - Step 4A
- Post-call transcription provider - Step 4B
- Hybrid (live + post-call via `/transcribe`) - Step 4C
- Participant events, interactive bot, agent in the meeting (only if asked) - Step 5
- Scheduling (now / future / calendar auto) - Step 6
- Custom metadata for routing/billing - Step 7
- Timeouts - Step 8

Each step's branch produces one or more fields in the final `create_bot` payload. Don't guess defaults - ask.

---

## Required Fields on `create_bot`

Per the OpenAPI `CreateBotRequest` schema, only two fields are required:

- `meeting_link` (string) - Zoom, Google Meet, or Teams URL
- `bot_name` (string) - the display name shown in the meeting

`video_required` defaults to **`false`** in the API (an omitted field records audio only). **House policy: still send `video_required` explicitly on every bot** (`false` unless the user asked to record video), so the intent is visible in the request and does not depend on a default. Audio only is faster to process and smaller to store, and transcripts, summaries, diarization and speaker timelines all work without video.

When the user does want video, send `recording_config.video_layout: "speaker_view"` alongside it. The API default layout is `grid_view`, so speaker view only happens if you ask for it.

`audio_required` (bool, default **`true`**) is an optional `CreateBotRequest` field: whether the bot records the mixed meeting audio. Leave it at the default. It must be `true` when `audio_mixed_mp3` is `true`, and it also appears in calendar-scheduled `bot_config` / `default_bot_config`. (`audio_separate_streams` is a different feature that enables per-participant audio tracks.)

> **400 rule:** A bot with `audio_required: false` and `video_required: false` and nothing else to do (no `realtime_endpoints`, live audio/video/transcription stream, `socket_connection_url`, `bot_message` or `agent_config_id`) is rejected with 400 `audio_required and video_required are both false, so the bot would record nothing.`

---

## Recording Defaults - apply to every bot you build

These three rules are product policy, not API behaviour. The API defaults differ, which is exactly why each field has to be sent explicitly.

| Setting | What you send by default | When to change it |
|---|---|---|
| `video_required` | `false`, sent explicitly | Only `true` when the user explicitly asks to record video. The API default is also `false`; send it anyway so the request states the intent. |
| `recording_config.video_layout` | `"speaker_view"` whenever video is on | Only `"grid_view"` when the user explicitly asks for grid or gallery view. The API default is `grid_view`, so speaker view must be sent. |
| `video_separate_streams` | never set it | Only `true` when the user explicitly asks for per-participant (per-speaker) video streams. It multiplies storage and processing per participant. |

Per-participant **audio** (`audio_separate_streams`) is unaffected by this policy. Keep the existing guidance for it.

### `recording_config.video_layout`

- Values on every platform: `"speaker_view"` and `"grid_view"`. Google Meet and Microsoft Teams also accept `"speaker_view_default"` and `"grid_view_default"`: the bot records the platform's own speaker or grid view in the call as one finished file. Zoom accepts only `"speaker_view"` and `"grid_view"`. Any other value returns 400 `invalid video_layout value. Allowed values: ...` listing the values for that platform.
- `"grid_view"` is the API default when `video_required: true`, so send `"speaker_view"` explicitly to get it. Use a `_default` value only when the user asks for the platform's own layout.
- Ignored when `video_required` is `false`. An audio-only bot never runs the compositor.
- WhatsApp accepts only `"grid_view"`. Any other platform rejects `video_layout`.
- Speaker view follows the active speaker, which is what people want for review and clipping. Grid view is a composited mosaic of everyone. Teams `grid_view_default` shows at most 9 tiles.
- Google Meet speaker view recordings are 1600x900. Do not hard-code 1280x720 when you process the video.

Existing per-participant video templates and options stay as they are. They are explicit opt-ins by design.

---

## Recommended Implementation Strategy

Pick the pattern that matches what the user actually needs. The first two are the **primary** workflows; the third is a fallback for specific cases.

### Primary patterns

| Need | What to configure | Lifecycle terminal event | Where the transcript lives |
|---|---|---|---|
| **Post-call transcript** (notetaker, recordings, summaries) - the most common use case | `recording_config.transcript.provider` set to a post-call provider (`deepgram` / `assemblyai` / `sarvam` / `jigsawstack` / `meetstream`) + a `callback_url` for webhooks | `bot.done` (after `transcription.processed`) | `GET /transcript/{tid}/get_transcript` after `transcription.processed` fires - fetched via the canonical `bot_details.transcript_id` flow |
| **Live transcript chunks during the meeting** (AI coaching, live captions, real-time agents) | `live_transcription_required.webhook_url` + a streaming provider in `recording_config.transcript.provider` (`meetstream_streaming` works free on stock accounts; `*_streaming` for external providers) | `bot.done` (after `audio.processed`; no `transcription.processed` ever fires) | Each chunk POSTed to your webhook in real time; nothing is saved server-side for post-call fetch |

**For the standard post-call notetaker workflow (95% of integrations):**
1. `create_bot` with `recording_config.transcript.provider: {deepgram: {...}}` (or assemblyai, etc.) and `callback_url`
2. Wait for the `transcription.processed` webhook
3. `GET /bots/{bot_id}/detail` → read `bot_details.transcript_id`
4. `GET /transcript/{transcript_id}/get_transcript` → top-level array of segments

No `/transcribe` call needed. The bot was configured with a post-call provider up front, so the transcript is generated automatically.

### Backup / fallback pattern (`POST /bots/{bot_id}/transcribe`)

`/transcribe` is **not the primary path** - it's a backup option for these specific cases:

- **You used a streaming-only provider at meeting time** (live transcription) but now want a post-call transcript too. Audio is saved, so you can transcribe on demand.
- **The original post-call provider failed** (e.g. `transcription.failed` because credits ran out). Retry with a different provider that does have credit, without re-running the meeting.
- **You want to re-transcribe with a higher-quality / different-language provider** after the fact.

In all other cases, configure the right provider on `create_bot` up front. `/transcribe` is a recovery tool, not a default.

---

## More detail

The rest of this skill is in [`references/meetstream-guide.md`](references/meetstream-guide.md). Read the section you need:

- Bot Configuration Decision Tree
- Use Case Patterns
- Bot Lifecycle - Live-Verified, Two Distinct Paths
- `automatic_leave` Timeouts - Recommended Defaults
- `bot_image_url`
- `custom_attributes`
- Platform Notes (per-feature, not just per-bot)
- Transcription Providers
- Webhook Handler Requirements
- Data Available After Meeting
- Data Retention
- Errors, Rate Limits and Validation
- Common Mistakes
- SDKs, CLI and sample apps

## Latest docs

- Build tracks (integration paths): https://docs.meetstream.ai/guides/introduction/integration-paths
- API reference (base URL, groups): https://docs.meetstream.ai/api-reference/introduction
- Create Bot payload reference: https://docs.meetstream.ai/api-reference/create-bot-payload-reference
- Webhooks and events: https://docs.meetstream.ai/guides/webhooks/webhooks-and-events
- Errors: https://docs.meetstream.ai/errors

When this skill and the docs differ, the docs are the source of truth. For the latest details, fetch the page with `.md` appended, read https://docs.meetstream.ai/llms.txt, or connect the docs MCP server at https://docs.meetstream.ai/_mcp/server.
