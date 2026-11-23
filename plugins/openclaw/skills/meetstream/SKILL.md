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

## Bot Configuration Decision Tree

Walk the user through these questions in order. Each answer pins down one field in the final `create_bot` payload. At the end, you'll have a complete, correct request body tailored to their use case.

> When the user is vague ("I want a meeting bot"), DO NOT guess defaults - actually walk them through this tree. The API defaults are not always what they want (e.g. `video_layout` defaults to `grid_view`, and the default retention may be longer or shorter than their policy). The one thing you do not need to ask about is the recording defaults above: video off unless the user mentioned video, speaker view when video is on, per-participant video only on request.

---

### STEP 1 - Bot identity (who is this bot in the meeting?)

```
Q1.1: What should the bot be called inside the meeting? [REQUIRED]
      └─→ "bot_name": "Acme Notetaker"     (visible to all participants)

Q1.2: Should it post a welcome message in the meeting chat on join?
      ├─ Yes → "bot_message": "Hi! I'm an AI notetaker recording this call."
      └─ No  → omit bot_message

Q1.3: Custom avatar / profile picture?
      ├─ Yes → "bot_image_url": "https://your-cdn.com/avatar.png"
      │        • MUST be a public https:// URL to a PNG, JPEG, GIF or WebP
      │          (no auth, no signed URLs, must resolve to a public address)
      │        • http:// and data: URIs return HTTP 400
      │        • Host it on S3 / Cloudflare R2 / public CDN
      └─ No  → omit bot_image_url

Q1.4: Did the user ask to record the meeting VIDEO file (archive, playback)?
      ├─ Yes → "video_required": true   → continue to Q1.4a for the layout
      └─ No  → "video_required": false  (DEFAULT for everything we build)
               • send it explicitly (the API default is also false, but an
                 explicit value keeps the intent visible)
               • saves storage + bandwidth; audio is still captured, and
                 transcript, summary, diarization and speaker timeline
                 all work without video

Q1.4a: (only when video_required is true) Which layout?
      ├─ User explicitly asked for grid / gallery
      │       → "recording_config": { "video_layout": "grid_view" }
      └─ Anything else
              → "recording_config": { "video_layout": "speaker_view" }  (RECOMMENDED)
               • the API default is "grid_view", so speaker view must be sent
               • "speaker_view" and "grid_view" work on Google Meet, Teams, Zoom;
                 Google Meet and Teams also take "speaker_view_default" /
                 "grid_view_default" (the platform's own in-call layout)
               • ignored when video_required is false
               • WhatsApp is grid only

Q1.5: Want per-participant audio tracks (one file per speaker)?
      ├─ Yes → "audio_separate_streams": true
      │        • Google Meet + Zoom only (NOT Teams)
      │        • Up to 16 concurrent speakers
      │        • Each track: WebM/Opus, 48kbps, 48kHz mono
      └─ No  → omit (default false; you get one mixed audio file)

Q1.6: Did the user EXPLICITLY ask for per-participant video tracks
      (one webcam stream per person)?
      ├─ Yes → "video_separate_streams": true
      │        • All 3 platforms
      │        • Google Meet + Teams: needs "video_required": true, else HTTP 400
      │        • Up to 6 concurrent webcams
      │        • WebM/VP8, 15 FPS, video-only
      └─ No  → omit (you get one composite video). Never set this implicitly:
               it multiplies storage and processing per participant.
               Per-participant AUDIO (Q1.5) is not affected by this rule.
```

> `audio_required` exists on `create_bot` (default `true`). Do not set it to `false` unless the bot has another job: `audio_required: false` with `video_required: false` and nothing else to do returns 400 ("the bot would record nothing").

---

### STEP 2 - Meeting platform

```
Q2.1: Which platform is the meeting on?
      ├─ Google Meet → "meeting_link": "https://meet.google.com/abc-defg-hij"
      │                continue Q2.2 (signed-in?)
      ├─ Microsoft Teams → "meeting_link": "https://teams.microsoft.com/l/meetup-join/..."
      │                    continue Q2.4 (signed-in?)
      └─ Zoom → "meeting_link": "https://zoom.us/j/123456789?pwd=..."
                continue Q2.3 (optional Zoom join type)

Q2.2: (Google Meet) Does the meeting require a signed-in Google identity?
      ├─ Yes → "google_meet": {
      │           "login_required": true,
      │           "google_login_domain": "your-company.com",
      │           "sign_in_email": "bot@your-company.com",   // optional: pin one account
      │           "strict_email": true                        // optional, default true
      │        }
      │        ⚠ Prerequisite: SSO + login cert registration via
      │        /google-login-domains and /google-logins. See Google Signed-In
      │        Bots section. Without this setup the bot will fail to join.
      └─ No  → omit google_meet (works for public Meet rooms)

Q2.3: (Zoom) How does the bot join through the user's Zoom app?
      Zoom bots join through the user's Zoom app with an OBF or a ZAK token,
      the way Zoom asks Meeting SDK apps to join since 2 March 2026. The user
      saves their Zoom Meeting SDK app in Dashboard > Integrations > Zoom (or
      connects their Zoom app and users) once.
      ├─ Joining as a signed-in Zoom user (ZAK)
      │  → "zoom": { "zak_url": "https://you.example.com/zoom/zak" }
      ├─ Joining On Behalf Of a user already in the meeting (OBF)
      │  → "zoom": { "obf_url": "https://you.example.com/zoom/obf" }
      │     Both URLs are HTTPS endpoints on YOUR server that return a fresh
      │     token when MeetStream calls them. Guide:
      │     https://docs.meetstream.ai/guides/app-integrations/zoom-authenticated-bots
      └─ Force the user's Zoom app → "zoom": { "use_own_app": true }
         (400 if no app is configured)
         Never write that Zoom needs no setup or that no Zoom app is needed.
         ⚠ zak_url and obf_url need the user's Zoom app, and cannot be
           combined with "use_own_app": false (HTTP 400).
         ⚠ Zoom links with no meeting number (for example /my/ personal
           links) return HTTP 400 invalid_meeting_link.
         ⚠ use_zoom_obf and zoom_oauth_connection_user_id are rejected by the
           API. Use zak_url / obf_url instead.

Q2.4: (Teams) Does the meeting block anonymous/guest join, or must the bot
      appear as a real Microsoft 365 user?
      ├─ Yes → "teams": {
      │           "login_required": true,
      │           "teams_login_domain": "bots.your-company.com",
      │           "sign_in_email": "bot1@bots.your-company.com", // optional
      │           "strict_email": true                            // optional, default true
      │        }
      │        ⚠ Prerequisite: a dedicated M365 tenant + accounts registered via
      │        /teams-login-domains and /teams-logins. ONE concurrent bot per
      │        account. Name/avatar come from the Microsoft account (bot_name and
      │        bot_image_url are ignored). See Microsoft Teams Signed-In Bots.
      └─ No  → omit teams (guest join; works when anonymous join is allowed)
```

---

### STEP 3 - Do you need a transcript? (this is the biggest decision)

```
Q3.1: Will any part of the system consume a transcript?
      ├─ No (audio-only, e.g. recording for human listening later)
      │  → Skip Steps 4 & 5 entirely. You can still call /transcribe later
      │    if you change your mind (audio is saved either way).
      └─ Yes → continue Q3.2

Q3.2: WHEN do you need the transcript?
      ├─ During the meeting (live captions, real-time AI coach, live dashboard)
      │  → STEP 4A (LIVE)
      ├─ After the meeting (summaries, CRM updates, archives)
      │  → STEP 4B (POST-CALL)
      └─ Both (live captions in the UI + complete transcript post-call)
         → STEP 4C (HYBRID - use streaming live + /transcribe after)
```

---

### STEP 4A - Live transcription path

```
Q4A.1: Where should live chunks be POSTed?
       → "live_transcription_required": { "webhook_url": "https://you/live" }
         (HTTPS, NOT a WebSocket; bot POSTs JSON chunks here every ~250ms)

Q4A.2: Which streaming provider?
       ├─ "I don't have any provider API keys" (most accounts)
       │  → "recording_config": {
       │       "transcript": { "provider": { "meetstream_streaming": {} } }
       │     }
       │     ✅ Free, no external key needed, works out of the box
       │     ✅ Returns speaker names from the meeting
       │     ❌ confidence/speech_confidence values are 0 (no per-word ML scores)
       │
       ├─ "I have a Deepgram account" (best for accuracy)
       │  → provider: {
       │       "deepgram_streaming": {
       │         "transcription_mode": "sentence",
       │         "model": "nova-2",
       │         "language": "en",
       │         "punctuate": true,
       │         "smart_format": true,
       │         "endpointing": 300,
       │         "vad_events": true,
       │         "utterance_end_ms": 1000,
       │         "encoding": "linear16",
       │         "channels": 1
       │       }
       │     }
       │     ⚠ ALL fields required per OpenAPI. Account needs Deepgram key.
       │
       ├─ "I have an AssemblyAI account"
       │  → provider: {
       │       "assemblyai_streaming": {
       │         "transcription_mode": "raw",
       │         "sample_rate": 48000,
       │         "speech_model": "universal-streaming-english",
       │         "format_turns": false,
       │         "encoding": "pcm_s16le",
       │         "vad_threshold": "0.4",
       │         "end_of_turn_confidence_threshold": "0.4",
       │         "inactivity_timeout": 300,
       │         "min_end_of_turn_silence_when_confident": "400",
       │         "max_turn_silence": "1280"
       │       }
       │     }
       │     ⚠ English-only. Account needs AssemblyAI key.
       │
       ├─ "I have an Interfaze (formerly JigsawStack) account"
       │  → provider: { "jigsawstack_streaming": {} }
       │     Account needs Interfaze key.
       │
       ├─ "I have a Smallest AI account"
       │  → provider: {
       │       "smallest_streaming": { "model": "pulse", "language": "en" }
       │     }
       │     • model: "pulse" (default) or "pulse-2" (English only)
       │     • Key saved in the dashboard under voice integrations (Smallest AI);
       │       without it: HTTP 400 "SmallestAPIKey not configured in user profile"
       │
       └─ "Just use the meeting's built-in captions" (Google Meet / Teams)
          → provider: { "meeting_captions": {} }
            ✅ Free, no provider needed at all
            ❌ Quality depends on the meeting platform's own captions
            ⚠ Zoom: only for bots that join WITHOUT the user's own Zoom app.
              With the user's Zoom app it returns HTTP 400.

Q4A.3: Need to also stream raw audio bytes (for your own ML model)?
       ├─ Yes → "live_audio_required": { "websocket_url": "wss://you/audio" }
       │        See Pattern 7 - binary frames over WebSocket, raw PCM16
       │        LE @ 48kHz mono with embedded speaker metadata.
       └─ No  → omit live_audio_required

Q4A.4: Need to also stream live video (fMP4)?
       ├─ Yes → "live_video_required": { "websocket_url": "wss://you/video" }
       │        ⚠ Google Meet + Teams only (NOT Zoom)
       │        See Pattern 8 - fMP4 over WebSocket with ping/pong contract.
       └─ No  → omit live_video_required

⚠ KEY LIMITATION OF STREAMING: No automatic post-call transcript.
   transcript_id will be null in the create_bot response.
   bot_details.transcript_id stays null.
   /transcriptions list is empty.
   You MUST manually call POST /bots/{bot_id}/transcribe after the meeting
   if you also want a post-call transcript (that's Step 4C).
```

---

### STEP 4B - Post-call transcription path

```
Q4B.1: Where should webhooks be delivered? [STRONGLY RECOMMENDED]
       → "callback_url": "https://you/webhook"
         You'll receive bot.joining → [bot.in_waiting_room] → bot.inmeeting → bot.recording → bot.leaving
         → bot.stopped → manifest.completed → audio.processed →
         transcription.processed → bot.done (full Path A lifecycle).
         Without callback_url you'd have to poll /bots/{id}/status repeatedly.

Q4B.2: Which post-call provider?
       ├─ "I don't have external keys, want lowest setup"
       │  → "recording_config": {
       │       "transcript": {
       │         "provider": {
       │           "meetstream": { "language": "en", "translate": false }
       │         }
       │       }
       │     }
       │     MeetStream in-house post-call. May require provider key in account.
       │
       ├─ "I want highest accuracy English" (most popular choice)
       │  → provider: { "deepgram": { "model": "nova-3", "language": "en" } }
       │     ⚠ Account needs Deepgram key. nova-3 is the only model enum.
       │
       ├─ "I want speaker diarization + PII redaction"
       │  → provider: {
       │       "assemblyai": {
       │         "speech_models": ["universal-2"],
       │         "language_code": "en_us",
       │         "speaker_labels": true,
       │         "punctuate": true,
       │         "format_text": true,
       │         "filter_profanity": false,
       │         "redact_pii": false,
       │         "auto_chapters": false,
       │         "entity_detection": false
       │       }
       │     }
       │     ⚠ 9 fields marked required per OpenAPI. Account needs AssemblyAI key.
       │
       ├─ "I have a Smallest AI account"
       │  → provider: {
       │       "smallest": { "model": "pulse", "language": "en", "diarize": true }
       │     }
       │     • model: "pulse" (default) or "pulse-pro" (English only)
       │     • diarize applies to "pulse" only (default true). Optional:
       │       keywords, redact_pii, redact_pci, emotion_detection,
       │       gender_detection
       │     • language is not checked at create time; a bad code arrives
       │       as transcription.failed
       │     Account needs a Smallest AI key (voice integrations).
       │
       ├─ "Indic languages (Hindi/Tamil/Telugu/etc.)"
       │  → provider: {
       │       "sarvam": {
       │         "model": "saaras:v3",
       │         "language_code": "en-IN",
       │         "mode": "transcribe",
       │         "with_diarization": true
       │       }
       │     }
       │     Account needs Sarvam key.
       │
       └─ "Auto-detect language + translate to English"
          → provider: {
              "jigsawstack": {
                "language": "auto",
                "translate": false,
                "by_speaker": true
              }
            }
            Account needs Interfaze key.

Q4B.3: How long should MeetStream keep the audio/transcript?
       ├─ 30 days / 720 hours (default if you omit retention)
       ├─ Custom window → "retention": { "type": "timed", "hours": 168 }  (7 days)
       └─ Per compliance policy → set the smallest window that meets your needs.
                                  After that, data is auto-deleted and
                                  data_deletion webhook fires.

✅ The transcript will be auto-fetched-able via the canonical flow:
   1. Wait for transcription.processed webhook
   2. GET /bots/{bot_id}/detail → bot_details.transcript_id
   3. GET /transcript/{transcript_id}/get_transcript
   No /transcribe call needed (Path A, the standard workflow).
```

---

### STEP 4C - Hybrid (live + post-call)

```
Configure the bot for LIVE only at create time (Step 4A), then:

After you receive bot.stopped, call:
  POST /bots/{bot_id}/transcribe
  {
    "provider": {"deepgram": {...}},        # any post-call provider
    "callback_url": "https://you/webhook"   # gets transcription.processed/.failed
  }

This:
  - Returns a new transcript_id
  - Overwrites bot_details.transcript_id (canonical fetch returns this one)
  - Fires exactly ONE transcription.processed or .failed (no bot.done follow-up)
  - Does NOT include custom_attributes in the /transcribe webhook
```

---

### STEP 5 - Other webhooks (beyond transcription)

```
Q5.1: Need to know when participants join/leave the meeting, or raise/lower
      their hand?
      ├─ Yes → add to recording_config:
      │   "realtime_endpoints": [{
      │     "type": "webhook",
      │     "url": "https://you/participants",
      │     "events": ["participant_events.join", "participant_events.leave",
      │                "participant_events.raise_hand", "participant_events.lower_hand"]
      │   }]
      │   ⚠ These webhooks have a DIFFERENT shape - nested under
      │   data.data.action / data.bot.id, no top-level bot_id or bot_status.
      │   ⚠ Hand events go ONLY to realtime_endpoints that list them, never to
      │   workspace webhooks. Google Meet and Zoom. Transitions only; the
      │   bot's own hand is never reported.
      └─ No → omit realtime_endpoints

Q5.2: Want your bot to interact in the meeting (send chat, play TTS audio,
      change its video frame)?
      ├─ Yes → "socket_connection_url": { "websocket_url": "wss://you/control" }
      │        See Pattern 3 - bot opens a WS to your server; you send the
      │        documented commands (sendaudio, sendmsg, interrupt, resume_audio,
      │        sendimg/sendimg_url) over it.
      └─ No → omit socket_connection_url

Q5.3: (Ask only if the user asked for an agent.) Own stack or hosted by MeetStream?
      ├─ Own stack (track 2, bridge server) → both
      │        "live_audio_required" and "socket_connection_url" on this bot,
      │        no agent_config_id (see `realtime-streaming`). Bot price only.
      ├─ Hosted (track 3a or 3c, MIA) → create the agent in the dashboard (app.meetstream.ai)
      │        or via POST /api/v1/mia (see Pattern 9; 3a default keys, then 3c own keys),
      │        then pass only its ID on create_bot, with no bridge sockets:
      │          "agent_config_id": "<from above>"
      └─ No agent → omit agent_config_id

Q5.4: Want to publish live video/audio INTO the bot's camera and mic (WebRTC)?
      ├─ Yes → "bot_camera_stream": { "websocket_url": "wss://you/camera" }
      │        • Google Meet (ws:// or wss://), Teams and Zoom (wss:// only)
      │        • The bot connects OUT to your signaling socket; the host must
      │          resolve to a public address
      │        • Zoom: cannot be combined with agent_config_id (HTTP 400)
      │        • Guide: https://docs.meetstream.ai/guides/websockets/bot-camera-streaming
      └─ No → omit bot_camera_stream

Q5.5: Should the bot raise its hand before it speaks (wait its turn)?
      ├─ Yes → after the bot is InMeeting/Recording, call
      │        POST /bots/{bot_id}/send_command  {"command": "raise_hand"}
      │        and {"command": "lower_hand"} when done. See "In-Meeting
      │        Commands" below. Nothing to add to create_bot.
      └─ No → nothing to do
```

---

### STEP 6 - Scheduling

```
Q6.1: When does the bot join?
      ├─ Right now → omit join_at; bot joins as soon as create_bot returns
      ├─ At a specific time → "join_at": "2026-04-22T15:00:00Z"  (ISO-8601)
      └─ Automatically for all calendar meetings →
         Skip create_bot. Use the Calendar API instead:
         POST /calendar/create_calendar (connect)
         POST /calendar/auto-schedule/enable (with default_bot_config)
         See "Pattern 6: Calendar Auto-Scheduling".
```

---

### STEP 7 - Metadata for routing/billing

```
Q7.1: Need to correlate webhooks back to your internal records (tenant ID,
      deal ID, user ID)?
      ├─ Yes → "custom_attributes": {
      │           "tenant_id": "acme-123",
      │           "deal_id": "hubspot-456",
      │           "internal_user_id": "u_789"
      │        }
      │        ⚠ Stringify all values defensively (live API has been observed
      │        to reject non-string values even though OpenAPI allows any).
      │        ⚠ custom_attributes is echoed on lifecycle events BUT NOT on
      │        /transcribe-triggered webhooks. Correlate by bot_id there.
      └─ No → omit custom_attributes (recommended only for trivial use cases)

Q7.2: Should recordings go to one of the user's own storage destinations?
      ├─ Yes → "storage_id": "<destination ID from the dashboard>"
      │        • 1-80 letters, numbers, underscores or hyphens, else HTTP 400
      │        • Destinations are set up in the dashboard (no public API)
      │        • An unknown ID or a destination that fails validation: HTTP 400
      │          with the storage error text
      └─ No → omit storage_id (workspace default destination, or MeetStream
               storage when none is configured)
```

---

### STEP 8 - Timeouts (use these defaults unless you have a reason not to)

```
"automatic_leave": {
  "waiting_room_timeout": 600,        // 10 min - long meetings start late
  "everyone_left_timeout": 600,       // 10 min - handle bio breaks
  "voice_inactivity_timeout": 600,    // 10 min - silent presentations
  "in_call_recording_timeout": 14400, // 4 hr - handle long workshops
  "recording_permission_denied_timeout": 600  // 10 min - Zoom-only, MAX is 600 (also the default)
}
```

Live-verified constraints:
- `in_call_recording_timeout` minimum 600s (API HTTP 400 below)
- `recording_permission_denied_timeout` range 60–600s, default 600 (API HTTP 400 outside)

---

### Final assembly - your complete `create_bot` payload

Combine every answer above. A realistic post-call notetaker for Google Meet might look like:

```json
POST https://api.meetstream.ai/api/v1/bots/create_bot
Authorization: Token YOUR_API_KEY

{
  "meeting_link": "https://meet.google.com/abc-defg-hij",
  "bot_name": "Acme Notetaker",
  "bot_message": "Hi! I'm an AI notetaker for Acme. Transcript will be emailed after.",
  "bot_image_url": "https://acme-cdn.com/bot-avatar.png",
  "video_required": false,
  "callback_url": "https://api.acme.com/webhooks/meetstream",
  "custom_attributes": {
    "tenant_id": "acme-prod-tenant-42",
    "user_id": "u_12345"
  },
  "recording_config": {
    "transcript": {
      "provider": { "deepgram": { "model": "nova-3", "language": "en" } }
    },
    "retention": { "type": "timed", "hours": 168 }
  },
  "automatic_leave": {
    "waiting_room_timeout": 600,
    "everyone_left_timeout": 600,
    "voice_inactivity_timeout": 600,
    "in_call_recording_timeout": 14400,
    "recording_permission_denied_timeout": 600
  }
}
```

A live AI-coach bot for the same meeting might look like:

```json
{
  "meeting_link": "https://meet.google.com/abc-defg-hij",
  "bot_name": "Sales Coach",
  "video_required": false,
  "callback_url": "https://api.acme.com/webhooks/meetstream",
  "live_transcription_required": {
    "webhook_url": "https://api.acme.com/live/transcript"
  },
  "recording_config": {
    "transcript": { "provider": { "meetstream_streaming": {} } },
    "retention": { "type": "timed", "hours": 24 }
  },
  "automatic_leave": {
    "waiting_room_timeout": 600,
    "everyone_left_timeout": 600,
    "voice_inactivity_timeout": 600,
    "in_call_recording_timeout": 14400,
    "recording_permission_denied_timeout": 600
  }
}
```

When in doubt, walk the user through every step above before sending `create_bot`. It's better to ask 3 extra questions than to ship a bot configured wrong for their use case.

---

## Use Case Patterns

Map the user's request to one of these. Each gives the calls and payloads; build them into the user's code.

### Pattern 1: Record + Transcript (most common)

Bot joins, records audio, transcript fetched post-meeting.

```json
POST /bots/create_bot
{
  "meeting_link": "https://zoom.us/j/123456789",
  "bot_name": "Recorder",
  "video_required": false,
  "callback_url": "https://your-server.com/webhook",
  "recording_config": {
    "transcript": {
      "provider": { "deepgram": { "language": "en", "model": "nova-3" } }
    },
    "retention": { "type": "timed", "hours": 48 }
  }
}
```

Returns **HTTP 201 Created** with `BotResponse`:
```json
{
  "bot_id": "...",
  "transcript_id": "..." | null,
  "meeting_url": "...",
  "status": "Active"
}
```

**How to fetch the transcript - canonical pattern:**

1. Wait for the `transcription.processed` webhook (signals readiness - but does **not** contain `transcript_id`)
2. Call `GET /bots/{bot_id}/detail` → read `bot_details.transcript_id`
3. Call `GET /transcript/{transcript_id}/get_transcript`

This is **stateless** - no need to store `transcript_id` from `create_bot`. The webhook gives you `bot_id`; you derive the rest.

```python
# The whole flow, after the transcription.processed webhook fires:
detail = requests.get(f"{BASE}/bots/{bot_id}/detail", headers=H).json()
tid = detail["bot_details"]["transcript_id"]
resp = requests.get(f"{BASE}/transcript/{tid}/get_transcript", headers=H)
if resp.status_code == 200:
    segments = resp.json()        # ← list (top-level array)
elif resp.status_code == 202:
    msg = resp.json()             # ← dict: {"message": "Transcript is still being processed. ..."}
    # transcript not ready yet - back off and retry, or wait for next webhook
```

> **Live-verified response shapes from `/transcript/{tid}/get_transcript`:**
> - **HTTP 200** → top-level JSON **array** of segment objects (success case)
> - **HTTP 202** → JSON **object** `{"message": "Transcript is still being processed. Current status: <state>"}` - transcript_id exists but isn't ready. Always check status code before iterating.
> - **HTTP 422** → the transcript run failed (API v1.10.0). The body gives the status and the reason: `{"message": "Transcript processing failed: <reason>", "transcript_status": "Failed", "transcript_id": "..."}` (for example the provider rejected the API key, or the usage limit was reached). It is final: do not retry it. Show the reason, fix the cause, then start a new run with `POST /bots/{bot_id}/transcribe`. Provider rejections are not retried by MeetStream either.
> - Streaming-only providers never make a post-call transcript; for them the fetch keeps returning 202, so every polling loop needs a cap.
>
> **Three status indicators disagree on failure** (live-verified, treat the first as authoritative):
> | Source | Value on transcript failure |
> |---|---|
> | `bot_details.TranscriptStatus` | `"Failed"` ← **authoritative** |
> | `/transcriptions[].status` | `"Not started"` (stale) |
> | `/transcript/{tid}/get_transcript` HTTP | `422` with the reason |
>
> **Always check `bot_details.TranscriptStatus` before retrying, or watch for the `transcription.failed` webhook** to break out of the polling loop:
>
> ```python
> def fetch_transcript_safely(bot_id: str, max_polls: int = 30):
>     for _ in range(max_polls):
>         detail = requests.get(f"{BASE}/bots/{bot_id}/detail", headers=H).json()
>         ts = detail["bot_details"].get("TranscriptStatus")
>         if ts == "Failed":
>             raise RuntimeError(f"Transcript failed for {bot_id}")
>         if ts == "Success":
>             tid = detail["bot_details"]["transcript_id"]
>             resp = requests.get(f"{BASE}/transcript/{tid}/get_transcript", headers=H)
>             if resp.status_code == 200:
>                 return resp.json()  # top-level array
>             if resp.status_code == 422:  # final failure: stop, show the reason
>                 raise RuntimeError(resp.json().get("message"))
>         time.sleep(2)
>     raise TimeoutError("Transcript not ready")
> ```

**Where `transcript_id` lives - all four live-verified sources:**

| Source | When to use |
|---|---|
| `bot_details.transcript_id` on `GET /bots/{bot_id}/detail` | **Canonical / default path.** Stateless - `bot_id` from webhook is all you need. |
| `BotResponse.transcript_id` in `create_bot` response | Available immediately on bot creation if you want to log it; not required. |
| `GET /bots/{bot_id}/transcriptions` | Only when you've called `POST /bots/{bot_id}/transcribe` to re-transcribe with a different provider and need to list all runs. |
| `POST /bots/{bot_id}/transcribe` response | When triggering a fresh transcription run. |

For provider `meeting_captions`, all four give `transcript_id: null` - fetch the S3 caption file from `bot_details.caption_file` on `/detail` instead.

**`transcript_id` is NOT in any webhook payload.** The `transcription.processed` webhook contains only `bot_id`, `event`, `transcript_status`, `message`, `status_code`. Use the canonical `/detail` pattern above to resolve it.

Once you receive the `transcription.processed` webhook, fetch:
```
GET /transcript/{transcript_id}/get_transcript
```

The response is a **top-level JSON array** of segment objects (participant-keyed, the default):
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
The `meetstream` engine can add a lone "Thank you." segment on silence; treat it as filler. The response is the array itself, not `{transcript: [...]}`.

For raw provider output (unformatted), add `?raw=true`.

### Pattern 2: Real-Time Transcription (AI agents, live coaching)

Live transcription is delivered via **HTTPS webhook** (POST) - not WebSocket.

> **Live-verified prerequisite:** `live_transcription_required.webhook_url` REQUIRES a streaming provider in `recording_config.transcript.provider`. The live API returns `HTTP 400: "live_transcription_required.webhook_url is provided but no streaming provider found. Please provide at least one streaming provider (deepgram_streaming, assemblyai_streaming, jigsawstack_streaming, meetstream_streaming, or meeting_captions)."` if you set the webhook URL without one.

Five known streaming providers (live-verified from server error message):
- `deepgram_streaming` (requires external Deepgram API key in your MeetStream account)
- `assemblyai_streaming` (requires external AssemblyAI API key)
- `jigsawstack_streaming`
- `meetstream_streaming` - MeetStream in-house, no external key required (works on stock accounts)
- `meeting_captions` - Google Meet / Teams native captions (free)

```json
{
  "live_transcription_required": { "webhook_url": "https://your-server.com/live-transcript" },
  "recording_config": {
    "transcript": {
      "provider": {
        "deepgram_streaming": {
          "transcription_mode": "sentence",
          "model": "nova-2",
          "language": "en",
          "punctuate": true,
          "smart_format": true,
          "endpointing": 300,
          "vad_events": true,
          "utterance_end_ms": 1000,
          "encoding": "linear16",
          "channels": 1
        }
      }
    }
  }
}
```

For accounts without external provider keys, swap in `meetstream_streaming: {}` - empty config is accepted.

**Note:** Streaming-only providers (`meetstream_streaming`, `meeting_captions`, the `_streaming` variants) do NOT produce a post-call transcript via `/transcript/{tid}/get_transcript`. `create_bot` returns `transcript_id: null` (for `meeting_captions`) or a transcript_id that fetch returns HTTP 202 forever (for `meetstream_streaming`). Use the live webhook stream as the canonical record - don't expect a post-call fetch.

Each POST to your `webhook_url`:
```json
{
  "bot_id": "305e708e-...",
  "speakerName": "Alice",
  "timestamp": "2026-05-26T10:21:43.681Z",
  "transcript": "Can you walk me through",
  "utterance": "",
  "words": [{ "word": "Can", "start": 0.2, "end": 0.5, "confidence": 0.99, "speaker": "Alice", "punctuated_word": "Can", "speech_confidence": 0.99 }],
  "is_final": false,
  "end_of_turn": false,
  "turn_is_formatted": false,
  "transcription_mode": "raw",
  "custom_attributes": {}
}
```

For raw live audio bytes (binary frames over WebSocket), see Pattern 7 below. For raw live video (fMP4 over WebSocket), see Pattern 8.

### Pattern 3: Interactive Bot (chat, TTS audio, dynamic video frame)

Bot opens a WebSocket back to your server for two-way control:

```json
{ "socket_connection_url": { "websocket_url": "wss://your-server.com/bot-control" } }
```

On join the bot sends a JSON handshake:
```json
{ "type": "ready", "bot_id": "...", "message": "Ready to receive messages" }
```

Then you push **JSON commands** over that WebSocket (each carries `bot_id`). The documented commands:

| Command | Purpose |
|---|---|
| `sendaudio` | Play raw PCM16 LE audio (48 kHz mono, base64-encoded) through the bot's mic |
| `sendmsg` | Post a chat message (requires BOTH `message` AND `msg` fields with the same value, for cross-platform compat) |
| `interrupt` | Stop bot audio playback and clear the queue (`{action: "clear_audio_queue"}`). On Zoom and Teams it then holds further audio until `resume_audio` |
| `resume_audio` | Allow audio again after an interrupt (`resume_id`, any string). Google Meet ignores it, so send it before each new reply on every platform |
| `sendimg` / `sendimg_url` | Set bot's **video frame** to an image (base64 via `img`, or URL via `img_url`). Zoom and Teams; on Google Meet use `send_image` |

For chat / images **into the chat panel only** (not video frame), there are also REST endpoints:
```
POST /bots/{bot_id}/send_message    body: { "message": "...", "metadata": { "message_type": "text" } }
POST /bots/{bot_id}/send_image      body: { "img_url": "https://...", "display_duration": 5, "metadata": {...} }
POST /bots/{bot_id}/pause_recording   (empty body - suspend recording mid-meeting; bot stays in the call)
POST /bots/{bot_id}/resume_recording  (empty body - resume a paused recording)
```

> **`send_image` field is `img_url`** (not `image_url`). `display_duration` (integer seconds) is optional.

Image URLs the bot downloads (`img_url`, `sendimg_url`, `bot_image_url`, `initial_audio.url`) must resolve to public addresses on every redirect hop. A URL that resolves to a private, loopback or metadata address is refused when the bot fetches it (no 400 at request time, the image just never appears).

To make the bot raise or lower its hand, use the REST `send_command` endpoint (see [In-Meeting Commands](#in-meeting-commands-send_command)), not the WebSocket.

Message formats for every command (chunked audio, barge-in, streaming chat): https://docs.meetstream.ai/guides/websockets/meeting-control-patterns

### Pattern 4: Calendar-Automated Bot

Connect Google Calendar so MeetStream auto-handles event sync, scheduling, recurring events, change detection, and watch channel renewal.

**Connect:**
```
POST /calendar/create_calendar
{
  "google_refresh_token": "...",
  "google_client_id": "...",
  "google_client_secret": "..."
}
```

Field names use the `google_` prefix. All three are required. Plain `refresh_token` / `client_id` / `client_secret` will be rejected by the OpenAPI schema.

**Endpoints (full list from docs):**

| Method | Path | Purpose |
|---|---|---|
| POST | `/calendar/create_calendar` | Connect a Google Calendar |
| GET | `/calendar/calendars` | List connected calendars (live from Google) |
| GET | `/calendar/events` | Sync + list events with pagination + bot info |
| GET | `/calendar/get_events` | List events from local DB only (faster, no Google call) |
| POST | `/calendar/schedule/{event_id}` | Schedule a bot for an event (body: `bot_config`, `occurrence_date`, `schedule_all_occurrences`, `occurrence_limit`, `recurring_event`) |
| DELETE | `/calendar/schedule/{event_id}` | Unschedule an event (body: `cancel_all_occurrences`, `from_date`) |
| GET | `/calendar/scheduled_bots` | List all upcoming scheduled bots |
| PATCH | `/calendar/scheduled_bots/{bot_id}` | Update a scheduled bot (`scheduled_join_time`, `bot_username`, `custom_attributes`) |
| DELETE | `/calendar/scheduled_bots/{bot_id}` | Delete a single scheduled bot |
| POST | `/calendar/auto-schedule/enable` | Enable auto-scheduling (body: `default_bot_config`) |
| POST | `/calendar/auto-schedule/disable` | Disable auto-scheduling |
| GET | `/calendar/auto-schedule/settings` | Read current auto-schedule settings |
| POST | `/calendar/auto-reschedule` | Trigger reschedule for next recurring occurrence |
| POST | `/calendar/toggle-recurrence` | Enable/disable auto-rescheduling per event (body: `{event_id, recurring_enabled}`) |

> **Disconnect:** use `DELETE /calendar/disconnect` - that's what the docs guide, cURL example, and response example all show. Returns `{disconnected, user_id, watch_channel_stopped, events_deleted, schedules_cancelled, message}`. Irreversible - stops watch channels, cancels pending schedules, deletes synced events, removes Google OAuth credentials. (The OpenAPI spec shows POST as a quirk; disregard.)

**Auto-scheduling behavior:** job runs every 24h at midnight UTC, schedules bots for the next 24h, joins 1 minute before meeting start. Real-time push notifications from Google Calendar handle reschedules and cancellations. Watch channels auto-renew every ~6 days (a daily background job renews any expiring within 2 days).

**Recurring events / RRULE:** standard iCalendar rules supported (DAILY/WEEKLY/MONTHLY, BYDAY, COUNT, UNTIL). Schedule with `recurring_event: true` to auto-reschedule after each occurrence, or `schedule_all_occurrences: true` (with optional `occurrence_limit`, default 52) to batch-schedule.

**Deduplication:** scheduling the same event twice returns **HTTP 409** with the existing bot's ID. Use `PATCH /calendar/scheduled_bots/{bot_id}` to update.

### Pattern 5: Note-Taker (full pipeline)

Webhook server + bot creation + transcript fetch + AI summary + email delivery.

Fastest path: Pattern 1 (create the bot with a `callback_url`, fetch the transcript after `transcription.processed`), then summarize in the user's app. The webhook handler returns 200 fast and is idempotent. Details in the `notetaker` skill. Full example apps (optional): https://docs.meetstream.ai/tutorials/sample-apps

### Pattern 6: Participant Tracking (real-time)

Real-time join/leave and raise/lower hand events during the meeting:

```json
{
  "recording_config": {
    "realtime_endpoints": [{
      "type": "webhook",
      "url": "https://your-server.com/participants",
      "events": [
        "participant_events.join",
        "participant_events.leave",
        "participant_events.raise_hand",
        "participant_events.lower_hand"
      ]
    }]
  }
}
```

**Hand events** (`participant_events.raise_hand` / `participant_events.lower_hand`, Google Meet and Zoom):
- Opt-in per bot: they go **only** to `realtime_endpoints` entries that list them. Workspace webhooks never receive them.
- Same nested shape as `participant_events.join`, with `data.data.action` set to `"raise_hand"` or `"lower_hand"`.
- Transitions only. The bot's own hand is never reported. "Lower all hands" sends one `lower_hand` per raised hand. A participant who leaves with a hand up gets no `lower_hand`, so clear their state on `participant_events.leave`.

### Pattern 7: Live Audio Streaming (binary frames)

Real-time PCM audio with embedded speaker metadata over a WebSocket you host:

```json
{ "live_audio_required": { "websocket_url": "wss://your-server.com/audio" } }
```

The bot connects to your WSS, sends a JSON `ready` handshake, then streams **binary frames** with this exact wire format:

Read byte 0 first; every platform can send either audio type (live Google Meet bots send
one `0x01` frame and then `0x04` frames):

| Type | Header | Speaker fields start at |
|---|---|---|
| `0x01` | `[type:1]`, PCM16 LE, 48 kHz mono | offset 1 |
| `0x04` | `[type:1][sample_rate:4, uint32 LE][channels:1]` | offset 6 |

Then `sid_length` (uint16 LE), `speaker_id`, `sname_length` (uint16 LE), `speaker_name`,
then raw PCM16 LE samples (no container). Skip any other type. Duration =
`len(pcm) / 2 / channels / sample_rate`.

```python
import struct
def decode(data: bytes):
    if data[0] == 0x01:
        rate, ch, off = 48000, 1, 1
    elif data[0] == 0x04:
        rate, ch, off = struct.unpack_from("<I", data, 1)[0], data[5], 6
    else:
        return None                      # unknown type: skip
    n = struct.unpack_from("<H", data, off)[0]; sid = data[off+2:off+2+n].decode(); off += 2 + n
    n = struct.unpack_from("<H", data, off)[0]; name = data[off+2:off+2+n].decode(); off += 2 + n
    return sid, name, rate, ch, data[off:]   # downmix if ch > 1, resample for your STT
```

`speaker_name` is `"NoSpeaker"` when MeetStream cannot attribute the audio (Google Meet
mixed audio often is), so you cannot drop the bot's own voice by name.

Decoders for Python, Node.js, Go and Java: https://docs.meetstream.ai/guides/websockets/real-time-audio-streaming

### Pattern 8: Live Video Streaming (fMP4 over WebSocket)

Supported on **Google Meet and Microsoft Teams only - not Zoom**.

```json
{
  "video_required": true,
  "live_video_required": { "websocket_url": "wss://your-server.com/video" },
  "recording_config": { "video_layout": "speaker_view" }
}
```

Protocol (all messages from MeetStream to you, except where noted):

| Message type | Direction | Description |
|---|---|---|
| `video_stream_start` (JSON text) | MS → you | Once on connect. Carries `codec`, `audio_codec`, `container: "fmp4"`, `width`, `height`, `framerate`, `audio_sample_rate`, `audio_bitrate`. |
| binary frames | MS → you | Raw fMP4 (fragmented MP4) bytes. **Append in order** to build the stream/file. |
| `video_latency_ping` (JSON text) | MS → you | Periodic. Carries `seq` and `sent_at_ms`. |
| `video_latency_pong` (JSON text) | **you → MS** | Echo `seq`, `sent_at_ms`, `bot_id`. Add `server_received_at_ms` (your wall-clock ms when you handled the ping). |
| `video_stream_end` (JSON text) | MS → you | Sent when stream stops. Carries `duration_seconds`. Connection closes after. |

Production tips: terminate TLS in front of your app (expose `wss://`), allow large WS frames, process writes sequentially per stream so chunk order is preserved.

### Pattern 9: MIA - AI Agent in a Meeting

MIA (MeetStream Infrastructure Agents) creates a server-configured AI agent that joins meetings via a hosted bridge. Two modes:

- **`pipeline`**: mix STT + LLM + TTS providers (configurable per layer)
- **`realtime`**: a single realtime model (OpenAI realtime, xAI, Google Gemini) - lower latency

This is track 3 (Agents API infra, hosted). Use it only when the user asks for a voice agent and wants MeetStream to host it; for their own stack, give the bridge server (track 2, `realtime-streaming`, bot price only). Keys in order: 3a MeetStream's own, default keys (`"key_source": "meetstream"` on each pipeline section; Deepgram and OpenAI, pipeline mode), then 3c the user's own keys. Price: bot + $0.25 per hour agent infrastructure + the models picked. 3b (LiveKit) and 3d (your coding agent through `meetstream setup`) are coming soon: no setup steps. Full guide: `mia-voice-agents`.

**Create the agent config first** (in the dashboard at app.meetstream.ai, with the `create_agent` MCP tool after `list_agents`, or via the API; `model.system_prompt` is required):
```
POST /api/v1/mia
{
  "agent_name": "Meeting Assistant",
  "mode": "pipeline",
  "model": { "provider": "openai", "model": "gpt-4.1", "system_prompt": "..." },
  "voice": { "provider": "openai", "voice_id": "nova" },
  "transcriber": { "provider": "deepgram", "model": "nova-3", "language": "en" },
  "agent": { "response_type": "voice", "first_message": "Hello!" }
}
```

Returns `{ message, agent_config_id, agent_config: {...} }`.

**Then attach it to a bot - pass only `agent_config_id`:**
```json
POST /bots/create_bot
{
  "meeting_link": "https://meet.google.com/...",
  "bot_name": "Assistant",
  "agent_config_id": "<from above>"
}
```

That's all MIA needs - MeetStream runs the agent on its own hosted bridge. Do **not** pass `socket_connection_url` or `live_audio_required` for MIA (a silent agent); those are for the bridge server flow (2a) and Patterns 3, 7 and 8, point at *your* server, and go on a separate bot.

**Other MIA operations:**
- `GET /api/v1/mia` - list all (no params) or fetch one (`?agent_config_id=...`). Secrets come back masked (`****` + last four characters); sending the mask back on `PUT` keeps the stored value.
- `PUT /api/v1/mia` - update; body requires `agent_config_id` + fields to change
- `DELETE /api/v1/mia?agent_config_id=...` - delete (query param, not path)
- `POST /bots/{bot_id}/update_mia` - change a running agent's prompt, params or wake words mid-meeting. Add `"wait_for_ack": true` to get the result instead of a plain `accepted` (see [In-Meeting Commands](#in-meeting-commands-send_command)).

**Anthropic Claude as the MIA LLM** (`model.provider: "anthropic"`):
- Pipeline mode only. Uses the Anthropic API key saved in the dashboard under model integrations (provider `anthropic`).
- `model.model`: for example `claude-haiku-5-5` (fastest replies) or `claude-sonnet-5-5`, `claude-opus-5-5`.
- `temperature` must be 0 to 1. `reasoning_effort` is optional (`"low"` when omitted). `tool_choice` may only be `"auto"` or `"none"`.
- `top_p`, `frequency_penalty`, `presence_penalty` and `logit_bias` return 400 `Anthropic models do not support: ...`.
- Claude is an LLM for MIA only. It is **not** a transcription provider and is not a `create_bot` field.

Supported providers: see `references/api-reference.md` MIA section.

### In-Meeting Commands (`send_command`)

`POST /bots/{bot_id}/send_command` runs one command on a live bot. Body: `{"command": "<name>", ...}`.

**Raise / lower hand** (Google Meet, Zoom, Microsoft Teams):

```bash
curl -X POST "https://api.meetstream.ai/api/v1/bots/$BOT_ID/send_command" \
  -H "Authorization: Token $MEETSTREAM_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"command": "raise_hand"}'
```

Response 200:

```json
{ "status": "accepted", "bot_id": "83acdd72-...", "command": "raise_hand", "hand_raised": true }
```

- **The bot must be in the meeting** (`InMeeting` or `Recording`). Joining, in the lobby, or already left: **409**. Wait for `bot.inmeeting` before you send it.
- `hand_raised` is the state the bot read back from the meeting **after** acting, not an echo of the request. Repeating a command is a no-op that returns the current state. The host (and, on Google Meet, the meeting itself once that person speaks) can lower the hand, so send `lower_hand` first if you are not sure of the state.
- `{"command": "lower_hand"}` returns `"hand_raised": false`. No other body fields are used.
- Allow up to 10 seconds for the response. Retry a 5xx once.
- WhatsApp bots and Zoom RTMS sessions return 400 (`unsupported_on_whatsapp` / `unsupported_on_zoom_rtms`). Bots that run outside the US region return 501.
- Guide: https://docs.meetstream.ai/guides/features/raise-lower-hand

**`update_mia` with `wait_for_ack`** (`POST /bots/{bot_id}/update_mia` with this body, or `send_command` with `"command": "update_mia"` added):

```json
{ "agent_config_params": { "customer_name": "Sarah" }, "wait_for_ack": true }
```

- Without `wait_for_ack`, 200 means "accepted for delivery", not "applied".
- With `"wait_for_ack": true`, the response carries the agent's result: `status` is `applied`, `partially_applied`, `failed` (with `errors: [{field, reason}]`) or `accepted` (with `ack_timeout: true` when the agent did not answer in time; the update may still apply). `applied` lists the fields that were applied.
- A non-boolean `wait_for_ack` returns 400 `wait_for_ack must be a boolean (true or false)`.

Other commands on the same endpoint: `screenshot` (Zoom: only on bots that join without your own Zoom app), `pause_recording`, `resume_recording`, and chat (`sendmsg`). On Zoom and Teams, chat is accepted while the bot waits in the lobby and is posted on admission; Google Meet returns 409 in the lobby.

---

## Bot Lifecycle - Live-Verified, Two Distinct Paths

**Lifecycle depends on whether you configured a post-call provider or a streaming-only provider.** This is the most important architectural distinction in the entire API - and it's not in the official docs.

### Path A: Post-call provider (`deepgram`, `assemblyai`, `sarvam`, `jigsawstack`, `meetstream`, `smallest`)

```
create_bot (returns transcript_id)
  → bot.joining              (Joining, 200)
  → bot.in_waiting_room      (InWaitingRoom, 200)   ← when the platform holds it in a lobby
  → bot.inmeeting            (InMeeting, 200)
  → bot.recording            (Recording, 200)
  → participant_events.*     (if realtime_endpoints configured)
  → bot.leaving              (Leaving, 200)
  → bot.stopped              (bot_event says why; see "Terminal events" below)
  → audio.processed / manifest.completed   (order varies)
  → transcription.processed  OR  transcription.failed
  → bot.transcriptionready
  → video.processed          (if video_required: true)
  → bot.done                 (Done, 200)            ← final event
  → data_deletion            (200), only after DELETE /bots/{id}/delete or retention expiry
```

### Path B: Streaming-only provider (`meetstream_streaming`, `assemblyai_streaming`, `deepgram_streaming`, `jigsawstack_streaming`, `smallest_streaming`, `meeting_captions`)

```
create_bot (returns transcript_id: null)
  → bot.joining → [bot.in_waiting_room] → bot.inmeeting → bot.recording
  → [live chunks stream to live_transcription_required.webhook_url]
  → bot.leaving
  → bot.stopped
  → manifest.completed, audio.processed
  → bot.done                 ← still fires
```

**Key difference (verified against 4,139 captured webhooks, Jun 2026):** streaming-only bots never receive `transcription.processed` or `transcription.failed`, because no post-call transcript is produced. They **do** receive `bot.done` (50 of 50 streaming bots that recorded). Use `bot.done` as the single "session finished" signal for both paths, and never block on `transcription.processed` for a streaming bot.

### Path C: Backup / fallback - `/transcribe`

> Use Path C only as a recovery / fallback. The primary post-call workflow is Path A (configure the post-call provider on `create_bot` up front). Reach for Path C when:
> - You used a streaming-only provider at meeting time and now want a post-call transcript too
> - The original `create_bot` provider failed (e.g. `transcription.failed`) and you want to retry with a different provider that has credit
> - You want to re-transcribe with a higher-quality / different-language provider

If you used a streaming-only provider at meeting time, **a post-call transcript does NOT exist automatically** - `transcript_id` stays `null`, `/transcriptions` is empty, `bot_details.transcript_id` is `None`. The audio recording IS saved (`AudioStatus: Success`), so you can request transcription whenever you want.

Call `POST /bots/{bot_id}/transcribe` with a post-call provider any time after `bot.stopped`:

```bash
POST /bots/{bot_id}/transcribe
{
  "provider": { "deepgram": { "model": "nova-3", "language": "en" } },
  "callback_url": "https://your-server.com/webhook"
}
```

Live-verified behavior:
- Returns immediately with a new `transcript_id` and starts processing in the background
- **Overwrites `bot_details.transcript_id`** with the new id (canonical fetch always returns the latest run)
- Adds an entry to `GET /bots/{bot_id}/transcriptions` with `status: "Processing"` → `"Success"` or `"Failed"`
- Fires **exactly one** `transcription.processed` or `transcription.failed` event on the `callback_url` you pass (single fire-and-forget - NOT a full lifecycle restart)
- The webhook payload shape is identical to a Path-A bot's transcription event (same `event` name, same `transcript_status`, same `status_code` 200/500)
- **Does NOT fire another `bot.done` after it**: the bot's lifecycle already ended
- **Does NOT include `custom_attributes`** in the payload (unlike original lifecycle events). Correlate by `bot_id` instead.

This is the recommended pattern when you need BOTH live and post-call output, or when your account only has streaming-capable providers configured at bot-creation time but you want to add a paid post-call transcript later.

Notes:
- `bot.joining` may fire up to 3 times if server-side join retries kick in.
- `bot.inmeeting`, `bot.recording`, `bot.leaving`, `bot.stopped`, `bot.done` each fire at most once per bot.
- If the bot never gets in, the sequence is typically `bot.joining` → `bot.in_waiting_room` → `bot.leaving` → `bot.stopped` (`bot_event: "bot.notallowed"`) → `bot.done`, with no `bot.inmeeting` or `bot.recording`.
- **`bot.done` is the final event on every path**, fired after all post-call processing completes (or fails). Use this, not `bot.stopped`, to mark a session fully done.
- **Never fetch the transcript before `transcription.processed` fires.** Always set `callback_url`.

### Full event reference

Every delivery carries `event`, `bot_id` and `timestamp`. Most also carry `bot_event`, which equals `event` except on terminals (see below).

| event | bot_status | status_code | When | Extra payload fields |
|---|---|---|---|---|
| `bot.scheduled` | | 200 | Bot created with a future `join_at` | |
| `bot.joining` | `Joining` | 200 | Bot is connecting | |
| `bot.in_waiting_room` | `InWaitingRoom` | 200 | Held in the lobby / waiting room | |
| `bot.error` | `InMeeting` | omitted | Streaming-provider upstream error during the meeting (e.g. AssemblyAI "Insufficient funds"). Not fatal: the bot keeps recording, only live transcription stops. Seen in May 2026 testing. | `message` (upstream error) |
| `bot.inmeeting` | `InMeeting` | 200 | Bot joined the meeting | |
| `bot.recording` | `Recording` | 200 | Recording started | |
| `participant_events.join` / `.leave` | | | Participants join/leave (requires `recording_config.realtime_endpoints`) | Nested: `data.data.action`, `data.data.participant.{id,name,full_name,platform}`, `data.data.timestamp.{relative,absolute}`, `data.bot.{id,metadata}`. No top-level `bot_id`, `bot_status` or `bot_event`. |
| `participant_events.raise_hand` / `.lower_hand` | | | A participant raised or lowered their hand (Google Meet, Zoom). Sent **only** to `realtime_endpoints` that list the event, never to workspace webhooks | Same nested shape as `participant_events.join`; `data.data.action` is `raise_hand` / `lower_hand` |
| `bot.leaving` | `Leaving` | 200 | Bot is leaving | |
| `bot.stopped` | varies | 200 or 500 | Bot exited or never got in. **Read `bot_event` for the reason** | see "Terminal events" |
| `bot.uploading` | | 200 | Media upload in progress | |
| `manifest.completed` | | 200 | Platform manifest uploaded | `status: "success"`, `manifest_status: "Success"` |
| `audio.processed` | | 200 | Audio ready to fetch | `status: "success"`, `audio_status: "Success"` |
| `transcription.processed` | | 200 | Transcript ready. **Post-call providers only** | `transcript_status: "Success"` |
| `transcription.failed` | | **500** | Transcript failed. **Post-call providers only** | `status: "error"`, `transcript_status: "Failed"`, `message` (error detail) |
| `bot.transcriptionready` | | 200 | Follows `transcription.processed` | |
| `video.processed` | | 200 | Video ready to fetch (`video_required: true`) | `video_status: "Success"` |
| `audio.skipped` / `manifest.skipped` / `transcription.skipped` | | | That stage had nothing to process (e.g. the bot never recorded) | |
| `bot.done` | `Done` | 200 | All post-call processing complete. **Final event on every path** | `message` |
| `data_deletion` | | 200 | Data deleted (manual `/delete` or retention) | `status: "success"`, `deleted_objects: <int>`. No `custom_attributes` |

### Terminal events: `event` vs `bot_event`

Every ending arrives **once**, with `event: "bot.stopped"`. `bot_event` carries the specific reason:

| `bot_event` | `status_code` | `bot_status` | Meaning |
|---|---|---|---|
| `bot.stopped` | 200 | `Stopped` | Normal exit (meeting ended, `remove_bot`, timeout) |
| `bot.kicked` | 200 | `Stopped` | A participant removed the bot |
| `bot.notallowed` | 500 | `NotAllowed` | Never admitted (lobby / waiting-room timeout) |
| `bot.denied` | 500 | `Denied` | Host refused entry or recording permission |
| `bot.failed` | usually 500 | `FAILED` / `ERROR` / `Failed` | The bot crashed or could not run |

Branch on `bot_event`, not `bot_status`: a kick and a clean exit both report `Stopped`, and failure casing varies. Compare `bot_status` case-insensitively if you use it at all.

### Failure reasons (`ErrorReason`)

A `bot.failed` terminal (status `Failed`) carries a specific reason in `bot_details.ErrorReason` on `GET /bots/{bot_id}/detail`. Google Meet `bot.failed` webhooks (and Teams for `sign_in_required`) also carry it as `failure_reason`. Treat unknown values as a generic failure. Reasons that matter most for join failures:

| `ErrorReason` | `failure_reason` | Platform | What happened | What to do |
|---|---|---|---|---|
| `MeetingRestricted` | `meeting_restricted` | Google Meet, Teams | The meeting admits only the host's organization or invited people, so the guest bot cannot ask to join. Message `Failed: Meeting access is restricted` | Use a signed-in bot from an allowed domain/tenant, or ask the organizer to allow the bot |
| `SignInRequired` | `sign_in_required` | Google Meet, Teams (new on Teams) | The meeting does not accept anonymous guests. Message `Failed: Sign in required` | Use a Google or Teams signed-in bot |
| `InvalidMeetingLink` | `invalid_meeting_link` | Google Meet, Teams (new on Teams) | The link is broken, cut off or not a meeting. Message `Failed: Invalid meeting link` | Copy the full join link from the invite |

A Zoom link with no meeting number (for example a `/my/` personal link) is refused earlier: `create_bot` returns 400 `invalid_meeting_link: ...` and no bot is created. Full list of reasons and messages: https://docs.meetstream.ai/guides/reference/bot-status-and-error-codes

### `status_code` is NOT always 200

`transcription.failed` and the failing terminals (`bot.notallowed`, `bot.denied`, most `bot.failed`) carry `status_code: 500`. All 466 captured `bot.done` deliveries were 200. Branch on `event`, then `bot_event`; use `status_code` only as a quick error indicator.

### Lifecycle internal states (visible via `bot_details.StatusTimeline`)

`StatusTimeline` on `/bots/{bot_id}/detail` shows every stage the bot passed through. Per live observation, the full set of stages is:

`Scheduled`, `Joining`, `WaitingRoom`, `InMeeting`, `Recording`, `Leaving`, `Stopped`, `BotNotAllowed`, `BotRejected`, `Error`, `AudioProcessing`, `VideoProcessing`, `TranscriptionReady`, `Done`, `MediaExpired`

Each entry is `{message, status, timestamp}`. `status: true` means that stage was reached; `false` means it wasn't (e.g. `BotRejected.status: false` if the bot wasn't rejected).

---

## `automatic_leave` Timeouts - Recommended Defaults

```json
{
  "automatic_leave": {
    "waiting_room_timeout": 600,
    "everyone_left_timeout": 600,
    "voice_inactivity_timeout": 600,
    "in_call_recording_timeout": 14400,
    "recording_permission_denied_timeout": 600
  }
}
```

All values in seconds. Use these defaults unless you have a specific reason to change them - they prevent the bot from dropping out of long real meetings.

- `waiting_room_timeout` - wait in waiting room before leaving - **600s (10 min)**
- `everyone_left_timeout` - stay after everyone else leaves - **600s (10 min)**
- `voice_inactivity_timeout` - wait if no audio detected (someone could be presenting silently) - **600s (10 min)**
- `in_call_recording_timeout` - max recording duration - **14400s (4 hours)**, the canonical default for full-length meetings
- `recording_permission_denied_timeout` - wait if recording permission denied (**Zoom-only**) - **600s (10 min)** - this is the max the API allows and also the API default (range is 60–600)

> **Live-tested constraints (not in OpenAPI spec):**
> - `in_call_recording_timeout` minimum is **600 seconds** - the live API returns `HTTP 400: "in_call_recording_timeout must be at least 600 seconds"` below that.
> - `recording_permission_denied_timeout` accepted range is **60–600 seconds**, default **600** (the limit was 300 and the default 60 before November 2026). Below 60 returns HTTP 400; above 600 returns `HTTP 400: "recording_permission_denied_timeout must not exceed 600 seconds (got N)"`. Use 600 (the max) for maximum patience.
> - A Zoom bot that joins without the user's own Zoom app records from admission whatever the host answers to the recording prompt, so this timeout does not apply to it.

**Why 14400 for `in_call_recording_timeout` specifically:** real meetings often run longer than 30 minutes. Defaulting to anything less risks the bot disconnecting while people are still talking. 4 hours is the canonical safe value for full-length sales / interview / workshop sessions.

Without these defaults, a stuck bot can sit in a meeting indefinitely.

---

## `bot_image_url`

Custom profile picture must be a **publicly accessible URL** - MeetStream fetches it externally. The image must be reachable without authentication.

```json
{ "bot_image_url": "https://your-server.com/avatar.png" }
```

- Must be `https://` and point to a PNG, JPEG, GIF or WebP image. A URL without one of those extensions is accepted only up to 2048 characters.
- `http://`, `data:` URIs and other unusable values return **400** `bot_image_url must be an https:// URL to a PNG, JPEG, GIF or WebP image; ...`.
- The host must resolve to a public address on every redirect hop. A private, loopback or metadata address is refused when the bot downloads the image (no 400; the bot just has no avatar).

---

## `custom_attributes`

The OpenAPI schema allows `additionalProperties: { description: Any type }`. Arbitrary key-value metadata; values are echoed back in webhook payloads.

> **Observed behavior:** in practice the server has been seen to reject non-string values. The OpenAPI doesn't enforce string-only, but stringifying values defensively is safer:
> ```json
> { "custom_attributes": { "deal_id": "12345", "active": "true", "score": "0.87" } }
> ```

---

## Platform Notes (per-feature, not just per-bot)

| Feature | Google Meet | Zoom | Microsoft Teams |
|---|---|---|---|
| Basic bot (`create_bot`) | ✓ | ✓ (through your Zoom app, OBF or ZAK) | ✓ |
| Recording + post-call transcript | ✓ | ✓ | ✓ |
| Live transcription webhook | ✓ | ✓ | ✓ |
| Live audio (`live_audio_required`) | ✓ | ✓ | ✓ |
| **Live video (`live_video_required`)** | ✓ | **✗** | ✓ |
| **Per-participant audio streams** | ✓ | ✓ | **✗** |
| Per-participant video streams | ✓ | ✓ | ✓ |
| MIA agents | ✓ | ✓ | ✓ |
| `interrupt` WS command (clears audio queue) | ✓ | ✗ (accepted, no-op) | ✗ (accepted, no-op) |
| Raise / lower hand (`send_command`) | ✓ | ✓ | ✓ |
| Participant hand events (`participant_events.raise_hand` / `.lower_hand`) | ✓ | ✓ | not documented yet |
| Live video into the bot camera (`bot_camera_stream`) | ✓ (ws/wss) | ✓ (wss, with your own Zoom app) | ✓ (wss) |
| Native captions (`meeting_captions`) | ✓ | only without your own Zoom app (400 with it) | ✓ |
| `video_layout` `speaker_view_default` / `grid_view_default` | ✓ | ✗ (400) | ✓ |
| Signed-in bot (real account identity) | ✓ (`google_meet`) | ✓ (`zoom.zak_url` / `obf_url`) | ✓ (`teams`, M365 work/school only, 1 bot per account) |

### Zoom setup

**How a Zoom bot joins.** Zoom bots join through the user's Zoom app with an OBF token (on behalf of a user who is in the meeting) or a ZAK token (a signed-in bot), the way Zoom asks Meeting SDK apps to join since 2 March 2026. Never write that Zoom needs no setup, that no Zoom app, SDK keys, OAuth or tokens are needed, or that the Zoom app is optional.

| Setup | What it does |
|---|---|
| Your Zoom app credentials (Client ID and Client Secret of a Zoom Meeting SDK app, saved in Dashboard > Integrations > Zoom) | The bot joins with your Zoom app. Needed for `zak_url` / `obf_url`, per-participant camera video and live video into the bot camera (`bot_camera_stream`) |
| Connected Zoom accounts (Zoom OAuth Meeting Bots) | Meetings you map can be recorded without an Admit or Allow recording prompt |
| `zoom.obf_url` (on-behalf-of bot) | Joins on behalf of a user who is already in the meeting |
| `zoom.zak_url` (signed-in bot) | Joins as a Zoom user: can join meetings that allow only signed-in users, and can join before the host |

Bots that join without the user's Zoom app (`use_own_app: false`) differ:
- Per-participant video (`video_separate_streams`) contains screen shares only. Per-participant audio works.
- The bot camera shows images (`bot_image_url`, Send Image). Live video into the bot camera (`bot_camera_stream`) is not available. MIA agents on this bot can show images, video and an avatar.
- The bot asks the host to allow recording, and records from the moment it is admitted. `recording_permission_denied_timeout` does not apply.
- Meetings that require Zoom sign-in cannot be joined. Use `zak_url`.
- `meeting_captions` and `initial_audio` work only on this bot. `screenshot` (via `send_command`) works here; the bot that uses your own Zoom app returns 400 for it.

**The `zoom.use_own_app` field** (`true`, `false` or omitted):

| `zoom.use_own_app` | What happens |
|---|---|
| omitted or `null` (default) | The bot uses the user's Zoom app when one is saved or a healthy Zoom account is connected, and joins without an app otherwise. |
| `true` | The bot must join with the user's Zoom app. With no app saved, `create_bot` returns 400. |
| `false` | The bot joins without the user's Zoom app, even when one is saved. Cannot be combined with `zak_url` / `obf_url`: 400 `zoom.zak_url and zoom.obf_url cannot be used with zoom.use_own_app set to false`. |

- Any other value returns 400 `zoom.use_own_app must be true or false`. The field is not echoed in bot details.
- There is **no fallback**: if Zoom refuses the user's own app, the bot does not retry without it. Fix the app and send the bot again.
- 400 `Zoom bots are not available in this region right now`: save the user's Zoom app and send `use_own_app: true`.
- `zoom.use_own_app` also works on `POST /calendar/schedule/{event_id}` and `PATCH /calendar/scheduled_bots/{bot_id}`. Optional setup guides: https://docs.meetstream.ai/guides/app-integrations/zoom-marketplace-app-setup and, for joining meetings outside the app's own account with your app, https://docs.meetstream.ai/guides/app-integrations/zoom-app-production-submission

For authenticated Zoom joins, pass `"zoom": { "zak_url": "https://..." }` (join as a signed-in user) or `"zoom": { "obf_url": "https://..." }` (join On Behalf Of a user who is already in the meeting). Each URL is an HTTPS endpoint on your server that returns a fresh token when MeetStream calls it. The older `use_zoom_obf` flag and `zoom_oauth_connection_user_id` are rejected by the API. Guide: https://docs.meetstream.ai/guides/app-integrations/zoom-authenticated-bots

### Google Signed-In Bots

To have the bot join Google Meet using a Google identity (meetings that block guests, or to show a real name instead of "Unknown"), configure SSO in your Google Workspace admin (Legacy SSO profile pointing at MeetStream's sign-in/sign-out URLs, plus an OpenSSL key + certificate), then register the domain and accounts. Guide: https://docs.meetstream.ai/guides/app-integrations/google-signed-in-bots

| Method | Path | Notes |
|---|---|---|
| POST | `/google-login-domains` | `{ "sso_workspace_domain": "your-company.com", "name": "...", "login_mode": "always" }` (`if_required` also accepted) |
| GET | `/google-login-domains` | `{ domains: [{ sso_workspace_domain, name, login_mode, max_concurrent_per_login, login_count, active_login_count, created_at }] }` |
| GET / PATCH / DELETE | `/google-login-domains/{domain}` | Path param is the workspace domain string. PATCH `{ name?, login_mode? }`. DELETE is refused while any login is active |
| POST | `/google-logins` | `{ domain, email, sso_private_key_pem, sso_cert_pem, is_active? }` (PEM contents of `key.pem` / `cert.pem`) |
| GET | `/google-logins?domain=<d>` | `{ logins: [...] }` |
| PATCH | `/google-logins/{login_id}` | Body must include `domain`; plus `is_active?`, `email?`, `sso_private_key_pem?`, `sso_cert_pem?` |
| DELETE | `/google-logins/{login_id}?domain=<d>` | |

There is **no** `GET /google-logins/{login_id}`; use the list endpoint or `GET /google-login-domains/{domain}`. Updates use PATCH, not PUT.

Then, on `create_bot`, pass the `google_meet` block:
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

- `sign_in_email` (optional) pins one registered account. `strict_email` (optional, default `true`): with `sign_in_email`, `true` fails if that account is busy or unhealthy; `false` falls back to any available account in the domain.
- Concurrency: a Google account can serve many meetings at once, but add logins as you scale (rule of thumb from the guide: one login per ~20 concurrent Meet sessions). MeetStream distributes bots across them.
- `google_meet` is not in the OpenAPI `CreateBotRequest` schema; the guide above is canonical.
- CLI: `meetstream logins google ...` and `meetstream join <link> --google-login-domain <d>` MCP: `create_bot`'s `google_login_domain` param. Account management is REST / CLI / SDK only.

### Microsoft Teams Signed-In Bots

By default a Teams bot joins as an anonymous guest and fails outright if the organizer disabled anonymous join. A signed-in bot joins as a real Microsoft 365 account. Guide: https://docs.meetstream.ai/guides/app-integrations/teams-signed-in-bots

**Setup requirements (once):**
1. A **dedicated Microsoft 365 tenant**, not your production one (Business Basic or higher).
2. One **standard, non-admin user per bot account**, with a Teams license. Set its display name and profile picture: that is what participants see.
3. In Entra ID: **disable security defaults** and set self-service password reset to **None** for these accounts (otherwise the first automated sign-in hits MFA registration).
4. Signed-in bot accounts must be Microsoft 365 work/school accounts. This applies only to signed-in bots: a guest bot also joins personal Teams meetings (`teams.live.com` links are accepted).

**Register the domain, then each account:**

| Method | Path | Body / notes |
|---|---|---|
| POST | `/teams-login-domains` | `{ "domain": "bots.your-company.com", "name": "Bot tenant", "login_mode": "always" }` (`if_required` is not supported for Teams yet) → 201 |
| GET | `/teams-login-domains` | `{ domains: [{ domain, name, login_mode, login_count, active_login_count, created_at }] }` |
| GET | `/teams-login-domains/{domain}` | Domain plus `logins: [{ login_id, email, is_active, lease_status, last_session_result }]`; 404 if unknown |
| PATCH | `/teams-login-domains/{domain}` | `{ name?, login_mode? }` |
| DELETE | `/teams-login-domains/{domain}` | Deletes the domain **and all its logins** |
| POST | `/teams-logins` | `{ "domain": "...", "email": "bot1@bots.your-company.com", "password": "<ACCOUNT_PASSWORD>", "is_active": true }` → 201 |
| GET | `/teams-logins?domain=<d>` | `domain` is required (400 without it); 404 if the domain isn't registered |
| GET | `/teams-logins/{login_id}` | Login object |
| PATCH | `/teams-logins/{login_id}` | `{ password?, is_active? }`. A new password also reactivates a deactivated account |
| DELETE | `/teams-logins/{login_id}` | |

Login object: `{ login_id, domain, email, is_active, lease_status, last_session_result, last_login_error, created_at, updated_at }`. The password is write-only and never returned. Load it from an env var or secret store in generated code; never hardcode it. If a bad password makes a join fail, MeetStream sets `is_active: false` until you rotate it.

**Create the bot:**
```json
{
  "meeting_link": "https://teams.microsoft.com/l/meetup-join/...",
  "bot_name": "Notetaker",
  "teams": {
    "login_required": true,
    "teams_login_domain": "bots.your-company.com",
    "sign_in_email": "bot1@bots.your-company.com",
    "strict_email": true
  }
}
```

- `teams_login_domain` is required when `login_required` is true. `sign_in_email` and `strict_email` behave as for Google (`strict_email` defaults to `true`).
- **One concurrent bot per account.** Teams merges same-email sign-ins into one attendee. For N concurrent signed-in Teams bots, register N accounts.
- **Name and avatar come from the Microsoft account.** `bot_name` and `bot_image_url` are not applied on a signed-in join.
- A malformed `teams` block is dropped silently and the bot joins as a guest. If a signed-in bot shows up as `(Guest)`, check that `login_required: true` is inside `teams`.
- CLI: `meetstream logins teams ...` and `meetstream join <link> --teams-login-domain <d>` MCP: `create_bot`'s `teams_login_domain` param. Account management is REST / CLI / SDK only.

**Errors on `create_bot`:**

| Status | Meaning | Fix |
|---|---|---|
| 400 `teams.teams_login_domain '<d>' is not registered...` | Domain not registered, or a typo | `POST /teams-login-domains` first |
| 403 | The domain or account belongs to another MeetStream account | Use a domain registered with this API key's account |
| 404 | `sign_in_email` isn't registered under the domain | Register it with `POST /teams-logins`, or fix the email |
| 409 | Pinned account busy or deactivated (`strict_email: true`), or no account is both active and free | Rotate the password (PATCH), set `strict_email: false`, or add accounts |
| 429 `all Teams logins ... in use` | Every account in the domain is leased to another bot | Register more accounts |

---

## Transcription Providers

Specified under `recording_config.transcript.provider`. Use **exactly one** provider per bot.

| Provider key | Mode | Notes |
|---|---|---|
| `meetstream` | Post-call | MeetStream's in-house post-call engine. OpenAPI marks `language` and `translate` as required. |
| `deepgram` | Post-call | `nova-3` is the only model enum. Requires Deepgram key in account. `language` defaults to `"en"` (free string per spec). |
| `assemblyai` | Post-call | Speaker diarization, redaction, chapters. Requires AssemblyAI key in account. 9 fields marked required per OpenAPI. |
| `sarvam` | Post-call | Indic languages, e.g. `model: "saaras:v3"`, `language_code: "en-IN"`. Requires Sarvam key. |
| `jigsawstack` | Post-call | Auto language detect, optional translation. Requires Interfaze key. |
| `meeting_captions` | Live, native | **Free** - uses Meet / Teams native captions. No external key needed. `transcript_id` is **null** - fetch captions via `bot_details.caption_file` on `/detail`. |
| `meetstream_streaming` | Live | MeetStream in-house streaming - **works without external keys**. Live-verified. Use this for live transcription on stock accounts. Empty config `{}` accepted. No post-call transcript fetch (returns HTTP 202 forever). |
| `deepgram_streaming` | Live | Real-time. All ~12 fields marked required per OpenAPI. Needs Deepgram key. |
| `assemblyai_streaming` | Live | Real-time English. All ~10 fields marked required per OpenAPI. Needs AssemblyAI key. |
| `jigsawstack_streaming` | Live | Live-verified existence (referenced in API error message); schema not yet documented in OpenAPI. |
| `smallest` | Post-call | Smallest AI Pulse. `model`: `pulse` (default) or `pulse-pro` (English only). `language` default `"en"`. Options: `diarize` (`pulse` only, default true), `keywords`, `redact_pii`, `redact_pci`, `emotion_detection`, `gender_detection`. Also accepted by `POST /bots/{bot_id}/transcribe`. |
| `smallest_streaming` | Live | Smallest AI streaming. `model`: `pulse` (default) or `pulse-2` (English only). Counts as a streaming provider for `live_transcription_required`. |

> **Smallest AI key:** one key, saved in the dashboard under voice integrations (Smallest AI), serves both `smallest` / `smallest_streaming` and MIA voice. Without it `create_bot` returns 400 `SmallestAPIKey not configured in user profile`. A bad `model` returns 400 `Invalid smallest model: ... Allowed values: ...`. An unsupported `language` is not caught at create time; it arrives as `transcription.failed`.

> **Account configuration matters.** Provider keys must be added to your MeetStream account dashboard before use. If a key is missing or invalid, the `transcription.failed` event fires with `status_code: 500` and a `message` describing the upstream auth failure (e.g. `"Deepgram API error: 401"` or `"Unauthorized Connection: Insufficient funds"`). **Test your account's provider configuration before relying on a post-call provider in production.**

> **Required-vs-default:** the OpenAPI marks many sub-fields as `required` even when they have natural defaults. Pass full provider configs when in doubt - see `references/api-reference.md` for the full schema of each provider.

---

## Webhook Handler Requirements

- Must use **HTTPS** (use ngrok or cloudflared for local dev - see https://docs.meetstream.ai/guides/webhooks/local-webhook-server)
- Must resolve to a **public address**. Webhooks from post-call processing (`manifest.completed`, `audio.processed`, `transcription.processed` / `.failed`, `video.processed` and the other post-call events) are delivered only to public addresses, on every redirect hop. A `callback_url` or workspace webhook URL that resolves to a private, loopback or metadata address is not delivered. A tunnel (ngrok, cloudflared) gives a public address for local development.
- Every delivery sends `User-Agent: MeetStream-Webhook/1.0`.
- Must respond `2xx` quickly to acknowledge receipt
- **No automatic retries.** If your endpoint returns non-2xx, the webhook is **not** retried. Build your handler to never fail (catch errors, queue work, return 200).
- `bot.joining` may fire up to 3 times if join retries are configured, and `bot.inmeeting` can repeat. `bot.stopped`, `audio.processed`, `transcription.processed`, `video.processed`, `bot.done`, `data_deletion` are each sent **at most once**.
- Idempotency: dedupe on `{bot_id, bot_event or event, timestamp}`. Every event carries a `timestamp` (verified on all 4,139 captured deliveries, including lifecycle events).

### Webhook payload shape

**Lifecycle events** (`bot.joining`, `bot.in_waiting_room`, `bot.inmeeting`, `bot.recording`, `bot.leaving`, `bot.stopped`, `bot.done`):
```json
{
  "event": "bot.joining",
  "bot_event": "bot.joining",
  "bot_id": "dd451299-1471-49ae-b407-c91541242748",
  "bot_status": "Joining",
  "message": "Bot is joining the meeting",
  "status_code": 200,
  "custom_attributes": { "your_keys": "echoed back" },
  "timestamp": "2026-06-16T06:28:14.445Z"
}
```

**A terminal** (bot never admitted):
```json
{
  "event": "bot.stopped",
  "bot_event": "bot.notallowed",
  "bot_id": "...",
  "bot_status": "NotAllowed",
  "status_code": 500,
  "message": "...",
  "custom_attributes": {...},
  "timestamp": "..."
}
```

**Post-call events** (`manifest.completed`, `audio.processed`, `transcription.processed`, `transcription.failed`, `video.processed`, `data_deletion`) may include `status: "success"|"error"`:
```json
{
  "event": "transcription.failed",
  "bot_event": "transcription.failed",
  "bot_id": "...",
  "status": "error",
  "transcript_status": "Failed",
  "message": "Transcript processing error: Deepgram API error: 401",
  "status_code": 500,
  "custom_attributes": {...},
  "timestamp": "2026-05-26T10:11:25.781273+00:00"
}
```

**Verified against 4,139 captured webhook deliveries (Jun 2026):**
- Every event carries `timestamp`.
- `bot_event` is present on everything except `manifest.completed`, `manifest.skipped`, `bot.transcriptionready`, `bot.uploading` and `participant_events.*`. Read it with a fallback: `payload.bot_event ?? payload.event`.
- `status_code` is NOT always 200. `transcription.failed` and failing terminals use 500.
- `participant_events.*` payloads have a different structure: `bot_id` is nested under `data.bot.id`, with no top-level `bot_status`.
- `transcript_id` is never in a webhook payload.

### Event types (see live-verified table in [Bot Lifecycle](#bot-lifecycle--live-verified))

`bot.scheduled`, `bot.joining`, `bot.in_waiting_room`, `bot.inmeeting`, `bot.recording`, `participant_events.*`, `bot.leaving`, `bot.stopped` (reason in `bot_event`: `bot.stopped` / `bot.kicked` / `bot.notallowed` / `bot.denied` / `bot.failed`), `bot.uploading`, `manifest.completed`, `audio.processed`, `transcription.processed`, `transcription.failed`, `bot.transcriptionready`, `video.processed`, `audio.skipped` / `manifest.skipped` / `transcription.skipped`, `bot.done`, `data_deletion`, and `bot.error` (streaming-provider warning).

### `bot_status` values

| bot_status | Event(s) | Meaning |
|---|---|---|
| `Joining` | `bot.joining` | Bot is connecting |
| `InWaitingRoom` | `bot.in_waiting_room` | Waiting to be admitted |
| `InMeeting` | `bot.inmeeting` | Bot is in the meeting |
| `Recording` | `bot.recording` | Recording active |
| `Leaving` | `bot.leaving` | Bot is leaving in progress |
| `Stopped` | `bot.stopped` (`bot_event` `bot.stopped` or `bot.kicked`) | Normal exit, or removed by a participant. Use `bot_event` to tell them apart |
| `NotAllowed` | `bot.stopped` (`bot_event: bot.notallowed`) | Could not join (waiting-room / lobby timeout) |
| `Denied` | `bot.stopped` (`bot_event: bot.denied`) | Host denied join or recording permission |
| `FAILED` / `ERROR` / `Failed` | `bot.stopped` (`bot_event: bot.failed`) | Unexpected error. Casing varies, so match `bot_event` instead |
| `MediaProcessing` | (none) | Post-call processing after `Stopped` or `Kicked`. A poll can see `InMeeting` and then `MediaProcessing` or `Done` and never `Stopped` |
| `Done` | `bot.done` | All processing complete - **terminal**. Poll until `Done` (or another final status: `NotAllowed`, `Denied`, `Failed`, `Error`, `MediaExpired`, `Cancelled`), with a cap |

### `*.failed` events

Live-verified: `transcription.failed` is a real event with `status_code: 500`, `transcript_status: "Failed"`, and `message` carrying the upstream error (e.g. provider auth failure). Handle these in your router:

```python
elif event_type == "transcription.failed":
    log_error(f"Transcript failed for bot {bot_id}: {payload.get('message')}")
elif event_type == "bot.stopped" and payload.get("bot_event") == "bot.failed":
    log_error(f"Bot failed: {payload.get('message')}")
```

Symmetric `audio.failed` and `video.failed` events have NOT been observed in live testing. Don't assume they exist - handle failures by checking `bot_details.AudioStatus` and `bot_details.TranscriptStatus`, and by watching for `bot.stopped` with `bot_event: "bot.failed"`.

### Webhook signature verification (optional)

Only deliveries to **workspace webhook endpoints** (added in the MeetStream dashboard with
a signing secret) are signed. Per-bot `callback_url` deliveries are **not signed**: if you
need signatures, add the URL as a workspace webhook endpoint. Signed requests include:
- `X-MeetStream-Signature: sha256=<hex_digest>` - `HMAC-SHA256(secret, raw_body)`
- `X-MeetStream-Timestamp: <iso8601>`: an ISO 8601 UTC string such as `2026-11-19T14:30:00Z`. Parse it as a time, not as a number.

Verify by computing `HMAC-SHA256(secret, raw_request_body)`, comparing against the signature (strip the `sha256=` prefix), and optionally checking the timestamp is within an acceptable replay window.

---

## Data Available After Meeting

After the relevant `*.processed` event fires:

| Data | Endpoint | Notes |
|---|---|---|
| Transcript (formatted) | `GET /transcript/{transcript_id}/get_transcript` | Response is a top-level array of segments |
| Raw transcript | `GET /transcript/{transcript_id}/get_transcript?raw=true` | Raw provider output |
| List transcripts for a bot | `GET /bots/{bot_id}/transcriptions` | Returns `{bot_id, transcriptions: [{transcript_id, provider, status, created_at, config, download_urls}]}` |
| Trigger a new transcription run | `POST /bots/{bot_id}/transcribe` | Body: `{provider: {<key>: {...}}, callback_url?}` |
| Speaker timeline | `GET /bots/{bot_id}/get_speaker_timeline` | Returns chunks with **byte offsets** into the audio file (not time). **Large timelines (about 5 MB or more) come back as a download link instead:** `{bot_id, speaker_timeline_url, size_bytes, truncated: false}`. The URL is pre-signed (no API key), valid 1 hour, and the file has the same format as the inline body. Always check for `speaker_timeline_url`. 404 `Manifest file not found. It may still be processing.` until the bot leaves |
| In-meeting chat | `GET /bots/{bot_id}/get_chats` | |
| Audio file | `GET /bots/{bot_id}/get_audio` | Pre-signed S3 URL, **valid 1 hour** |
| Video file | `GET /bots/{bot_id}/get_video` | Pre-signed URL, **valid 1 hour** |
| Per-participant audio streams | `GET /bots/{bot_id}/get_audio_streams` | Flat top-level array of items (`participant`, `download_url`, ...); URLs **valid 1 hour**; 202 while the bot is still in the meeting |
| Per-participant recording streams | `GET /bots/{bot_id}/get_recording_streams` | Same flat item shape plus `type` (`webcam` or `screenshare`); URLs **valid 1 hour** |
| Participant list | `GET /bots/{bot_id}/get_participants` | Returns a top-level array of `{deviceId, displayName, fullName, profilePicture, status, humanized_status, streamIds[], lastUpdated, parentDeviceId?}` |
| Session metadata | `GET /bots/{bot_id}/detail` | Returns `bot_details` with (live-verified): BotID, BotImageURL, BotMessage, BotProfile, BotUsername, CreatedAt, Duration, EndTime, LastUpdatedAt, ManifestStatus, MediaS3Bucket, MeetingLink, NativeSTT, OfferingType, Platform, PlatformCreatedAt, PlatformStatusCreatedAt, RequestPayload, StartTime, Status, StatusCreatedAt, **StatusTimeline** (per-stage `{message, status, timestamp}` map), AudioStatus, TranscriptStatus, UserID, caption_file (S3 link for native captions), participant_events, custom_attributes, **and `transcript_id`** (top-level - populated when a post-call provider is set, not enumerated in OpenAPI but returned live). |
| Screenshots | `GET /bots/{bot_id}/screenshots` | `{"screenshots": [{"id", "recorded_at", "url", "filename", "size_bytes"}]}`; one by id: `GET /bots/{bot_id}/screenshots/{id}` |
| Summary | not available | The API has no summary route; summarize the transcript yourself. |

Bot management:
- Status: `GET /bots/{bot_id}/status`
- List bots: `GET /bots` - returns `{bots: [...], hasNextPage: bool, nextCursor: string|null}` (note camelCase pagination keys)
- Remove from active meeting: `POST /bots/{bot_id}/remove_bot` (the GET form behaves the same). Call it when your app exits or gets Ctrl-C.
- Delete data: `DELETE /bots/{bot_id}/delete` → fires `data_deletion` webhook

### Per-participant audio/video - concurrency & platform limits

- **Per-participant audio** captures up to **16 concurrent speaker streams**. Supported on **Google Meet + Zoom only**, NOT Teams. Files: WebM container, Opus codec, 48 kbps, 48 kHz, mono.
- **Per-participant video** captures up to **6 concurrent webcam streams**. Supported on all 3 platforms. Files: WebM container, VP8 codec, 15 FPS, video-only (audio fetched separately).
- Both flags (`audio_separate_streams`, `video_separate_streams`) can be set at the top level of `create_bot` OR nested inside `recording_config`.
- **Never set `video_separate_streams` (at either level) unless the user explicitly asked for per-participant video.** Per-participant audio is unaffected by that rule.

---

## Data Retention

Default retention is **30 days (720 hours)**. Override on `create_bot`:

```json
{ "recording_config": { "retention": { "type": "timed", "hours": 168 } } }
```

### ⚠️ `DELETE /bots/{bot_id}/delete` - DESTRUCTIVE

**Do not call this casually.** It **permanently deletes** the recording data for a bot:

- The audio recording (MP3/WAV)
- The video recording (MP4)
- Per-participant audio/video streams
- The transcript
- Any associated S3 objects

**There is no recovery.** Once deleted, no API call (including the transcript endpoint) will return the data - every subsequent fetch will 404.

Live test response confirms scope: `{"message": "Successfully deleted 7 objects for bot ...", "bot_id": "...", "deleted_objects": 7}` - that "7 objects" includes audio, video, transcript, and metadata blobs.

**Rules:**

1. **Never call `/delete` automatically in webhook handlers, agents, or polling loops.** If you wire this into automated code, you will eventually wipe a session you needed.
2. **Never call `/delete` to "clean up" a test bot until you've verified you don't need its outputs.** Use `/delete` only for explicit test bots the user asked to remove.
3. **Prefer retention-based expiry.** Set `recording_config.retention` to the shortest acceptable window for your use case (default 30 days) and let MeetStream's scheduler clean up.
4. **Confirm with the user before running `/delete` interactively.** Treat it like `rm -rf` - if the user didn't explicitly ask to delete, don't.
5. **The `data_deletion` webhook fires after deletion** - receiving it means data is already gone, not "about to be deleted."

```python
# DESTRUCTIVE - only with explicit confirmation
def delete_bot_data(bot_id: str, confirmed: bool = False) -> dict:
    """Deletes audio, video, transcript permanently. Requires confirmed=True."""
    if not confirmed:
        raise ValueError("Refusing destructive delete without explicit confirmed=True flag")
    resp = requests.delete(f"{BASE_URL}/bots/{bot_id}/delete", headers=HEADERS)
    resp.raise_for_status()
    return resp.json()  # {message, bot_id, deleted_objects}
```

---

## Errors, Rate Limits and Validation

**Error body.** Most errors return `{"message": "..."}`. On the bot data endpoints (`get_audio`, `get_video`, `get_speaker_timeline`, `get_chats`, `get_participants`, screenshots), errors are `{"message": "..."}`, and so are errors from `remove_bot`, `stop_status` and `GET /bots/{bot_id}/transcriptions`. A few endpoints (in-meeting commands, the credit check, the 429 below) still send `error`. Read all shapes:

```python
def error_text(resp) -> str:
    try:
        body = resp.json()
    except ValueError:
        return resp.text
    if isinstance(body, dict):
        return body.get("message") or body.get("error") or str(body)
    return str(body)  # bare-string body
```

**Prepaid rate limit (429).** Prepaid (pay-as-you-go) accounts can create **5 bots per rolling minute and 50 per rolling hour**. Invoice accounts are not limited. Not counted: bots with `join_at` 10 minutes or more ahead, calendar bots for meetings 10+ minutes away, the scheduled join itself, and idempotent replays. Over the limit, no bot is created and the API returns:

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 37

{"error": "rate_limit_exceeded", "message": "...", "limit": 5, "window": "minute", "retry_after": 37}
```

Sleep for `Retry-After` seconds, then resend the same request (same `Idempotency-Key` or `deduplication_key` if you use one). Concurrent creates with the same key make one bot; a loser can get 409 with `Retry-After: 2` while the first request is still saving, so retry that 409 with the same key too. The SDKs (`@meetstream/sdk`, `meetstream-sdk`) retry 429 and in-progress 409 after `Retry-After` for you.

**Failed transcript (422).** `get_transcript` returns 422 with `message`, `transcript_status: "Failed"` and `transcript_id` when the run failed. It is final: never retry it. Show the reason, fix it (for example the provider key), then `POST /bots/{bot_id}/transcribe`.

**Prepaid balance.** The billing page https://app.meetstream.ai/billing shows it and adds credits. `GET /api/v1/billing/balance` (read only, API v1.10.0) may answer "not available" or 404 where it is not on yet: expected, use the billing page.

**`create_bot` requests that return 400:**

| Request | 400 message starts with |
|---|---|
| `audio_required: false` and `video_required: false` with no other job (no `realtime_endpoints`, live stream, `socket_connection_url`, `bot_message` or `agent_config_id`) | `audio_required and video_required are both false, so the bot would record nothing.` |
| Google Meet / Teams `video_separate_streams: true` without `video_required: true` | `video_separate_streams=true requires video_required=true for Google Meet and Microsoft Teams.` |
| `bot_image_url` that is not an https:// image URL (see [`bot_image_url`](#bot_image_url)) | `bot_image_url must be an https:// URL to a PNG, JPEG, GIF or WebP image;` |
| Zoom link with no meeting number (for example `/my/` personal links) | `invalid_meeting_link: this Zoom link has no meeting number,` |
| Zoom `meeting_captions` on a bot that uses the user's own Zoom app | `meeting_captions is not supported on Zoom.` |
| `zoom.use_own_app` not a boolean, or `false` with `zak_url` / `obf_url` | `zoom.use_own_app must be true or false` / `zoom.zak_url and zoom.obf_url cannot be used with zoom.use_own_app set to false` |
| `storage_id` not 1-80 letters, numbers, `_` or `-` | `storage_id must contain 1-80 letters, numbers, underscores or hyphens` |
| `bot_camera_stream` on another platform, a bad URL, `ws://` on Teams/Zoom, or with `agent_config_id` on Zoom | `bot_camera_stream is supported only for ...` / `... camera signaling requires wss://` / `bot_camera_stream cannot be combined with agent_config_id on Zoom` |
| `smallest` / `smallest_streaming` with an unknown `model` | `Invalid smallest model: ...` |
| `automatic_leave.recording_permission_denied_timeout` outside 60-600 | `recording_permission_denied_timeout must ...` |

A `meeting_link` that starts with `http://` is upgraded to `https://` (not a 400).

**Public addresses only.** Everything the bot or MeetStream connects to on your behalf must resolve to a public address: `callback_url` and workspace webhooks (post-call deliveries), `bot_image_url`, `send_image` / `sendimg_url` image URLs, `initial_audio.url`, and the `bot_camera_stream` signaling host. Private, loopback, link-local and cloud metadata addresses are refused at delivery or download time, usually with no 400. Use a public host or a tunnel.

Full error reference: https://docs.meetstream.ai/errors

---

## Common Mistakes

1. **Looking for `transcript_id` in the webhook** - it's not there. The webhook only signals timing. Get the `transcript_id` from the `create_bot` response, `GET /bots/{bot_id}/detail` (`bot_details.transcript_id`), or `GET /bots/{bot_id}/transcriptions`.
2. **Reading `seg["speaker"]` / `seg["transcript"]` only** - the response is a top-level array and, by default, participant-keyed: speaker `participant.name`, text `words[].text` joined. Reading only the segment-list fields prints an empty transcript (all four test harnesses hit this).
3. **`send_image` body using `image_url`** - the field is `img_url`.
4. **Fetching transcript before `transcription.processed`** - always wait for the webhook.
5. **HTTP callback URL** - must be HTTPS; use ngrok / cloudflared for local dev.
6. **Wrong calendar field names** - Calendar create requires `google_refresh_token` / `google_client_id` / `google_client_secret` (with the `google_` prefix).
7. **Turning off `audio_required` and `video_required` together** - `audio_required` (default `true`) is a real `create_bot` field. With both `false` and no other job (no `realtime_endpoints`, live stream, `socket_connection_url`, `bot_message` or `agent_config_id`), `create_bot` returns 400 because the bot would record nothing.
8. **Skipping `bot_name`** - it's required, not optional.
9. **Relying on the `video_required` default** - it defaults to `false` (audio only), but send it explicitly on every bot anyway (`false` unless the user asked to record video), so a copied example with `true` does not silently record video.
10. **Assuming `status_code` is always 200**: it's 500 for `transcription.failed` and for failing terminals (`bot.notallowed`, `bot.denied`, most `bot.failed`). Branch on `event`, then `bot_event`.
11. **Expecting webhook retries**: there are none. Always return 2xx and queue work asynchronously. Dedupe on `{bot_id, bot_event or event, timestamp}`.
12. **Using `websocket_url` for live transcription** - `live_transcription_required` accepts only `webhook_url` (HTTPS POST). The `websocket_url` field is for `live_audio_required`, `live_video_required`, and `socket_connection_url`.
13. **Sending WAV blobs over `sendaudio`** - bot expects raw PCM16 LE @ 48000 Hz mono, base64-encoded. No WAV header. Resample if your source isn't 48 kHz.
14. **`/calendar/toggle-recurring/{event_id}` path** - actual path is `POST /calendar/toggle-recurrence` with body `{event_id, recurring_enabled}`. No path param.
15. **MIA endpoint paths** - they are `/api/v1/mia` (singular) for CRUD; DELETE uses `?agent_config_id=...` query param, not a path id.
16. **Live video on Zoom** - not supported. Google Meet and Teams only.
17. **`in_call_recording_timeout` under 600** - live API rejects with HTTP 400. Minimum 600 seconds.
18. **Expecting `create_bot` to return HTTP 200** - it returns **HTTP 201 Created** (per OpenAPI and live-verified). `status` field is typically `"Active"`.
19. **Expecting a post-call transcript from a streaming-only provider** - streaming providers (`meetstream_streaming`, `assemblyai_streaming`, `deepgram_streaming`, `jigsawstack_streaming`, `smallest_streaming`, `meeting_captions`) return `transcript_id: null` and never populate `bot_details.transcript_id` or `/transcriptions`. The audio is saved but no transcript exists until you manually call `POST /bots/{bot_id}/transcribe`.
20. **Waiting for `transcription.processed` on a streaming-only bot**: it never fires for Path B. Use `bot.done`, which fires on both paths, as the "session finished" signal.
25. **Branching on `event == "bot.kicked"` or `"bot.notallowed"`**: those names only appear in `bot_event`. Every terminal's `event` is `bot.stopped`.
21. **Treating `bot.error` as a fatal event** - it's only a streaming-provider warning (upstream auth issue). The bot continues recording; only live transcription is impacted.
22. **Waiting for `bot.done` after `/transcribe`** - `/transcribe` is fire-and-forget. You get exactly one `transcription.processed`/`transcription.failed`, no `bot.done` follow-up.
23. **Relying on `custom_attributes` in `/transcribe`-triggered webhooks** - that field is missing from `/transcribe` events (present on original lifecycle events). Correlate by `bot_id` instead.
24. **Retrying a 422 or polling `/transcript/{tid}/get_transcript` without a bound** - a failed run returns 422 with the reason (final, do not retry); a streaming-only bot returns 202 forever. Cap every polling loop, and check `bot_details.TranscriptStatus` (`"Success"`/`"Failed"`/`None`) or the `transcription.failed` webhook.
25. **Sharing one Teams account across concurrent signed-in bots** - Teams allows one bot per account at a time; extra bots get 409/429. Register one account per concurrent bot. Also don't expect `bot_name` / `bot_image_url` to apply on a signed-in Teams join: the Microsoft account's name and picture are used.
26. **Using PUT or `GET /google-logins/{id}` for Google logins** - updates are PATCH (with `domain` in the body), deletes need `?domain=`, and there is no GET-by-id.
27. **Turning video on without a layout** - the API default is `grid_view`. Whenever `video_required: true`, send `recording_config.video_layout: "speaker_view"` unless the user explicitly asked for grid or gallery view. `"speaker_view"` and `"grid_view"` work on Google Meet, Teams and Zoom; Google Meet and Teams also accept `"speaker_view_default"` / `"grid_view_default"` (Zoom returns 400 for them); the field is ignored when video is off; WhatsApp accepts only `"grid_view"`.
28. **Setting `video_separate_streams` because it looked useful** - per-participant video is opt-in only. Never set it unless the user explicitly asked for per-participant video streams. Per-participant `audio_separate_streams` is not affected by this rule. On Google Meet and Teams it also needs `video_required: true`, else 400.
29. **Sending `raise_hand` before the bot is in the meeting** - `send_command` hand commands return 409 while the bot is joining or in the lobby. Wait for `bot.inmeeting`. Read `hand_raised` from the response; it is the real state in the meeting, not an echo.
30. **Waiting for hand events on the workspace webhook** - `participant_events.raise_hand` / `.lower_hand` go only to `recording_config.realtime_endpoints` entries that list them.
31. **Saying Zoom needs no setup** - Zoom bots join through the user's Zoom app with an OBF or a ZAK token, the way Zoom asks Meeting SDK apps to join since 2 March 2026. Never combine `use_own_app: false` with `zak_url` / `obf_url` (400). There is no fallback when Zoom refuses the user's app.
32. **Parsing `get_speaker_timeline` as the timeline every time** - large timelines return `{speaker_timeline_url, size_bytes, truncated}` instead. Check for `speaker_timeline_url` and download it (no API key, valid 1 hour).
33. **Reading only `error` from an error body** - most errors are `{"message": "..."}`, and remove_bot / stop_status / transcriptions errors moved from `error` to `message`. Read `message`, then `error`, then fall back to the raw text.
34. **Retrying `create_bot` in a tight loop on 429** - prepaid accounts get 5 creates per minute and 50 per hour. Sleep for the `Retry-After` seconds and resend with the same `Idempotency-Key` / `deduplication_key`.
35. **Pointing `callback_url`, `bot_image_url`, image URLs or `bot_camera_stream` at a private address** - they must resolve to public addresses. Private, loopback and metadata addresses are refused at delivery or download time, usually with no 400.
36. **Using Anthropic Claude as a transcription provider** - Claude is a MIA LLM (`model.provider: "anthropic"` in `POST /api/v1/mia`, pipeline mode). It is not a `recording_config.transcript.provider` key.

---

## SDKs, CLI and sample apps

- Node: `npm install @meetstream/sdk` (Node 18.17+). Python: `pip install meetstream-sdk` (Python 3.8+). Both read `MEETSTREAM_API_KEY`: https://docs.meetstream.ai/build-with-ai/sdks
- CLI: `npx -y @meetstream/cli <command>` (no install), `npm install -g @meetstream/cli`, `pipx install meetstream-cli` or `brew install meetstream-ai/tap/meetstream`; sign in with `meetstream login`. Commands and JSON shapes: `references/meetstream-cli.md`. Step-by-step CLI workflows: skill `cli-workflows`. Docs: https://docs.meetstream.ai/build-with-ai/meetstream-cli
- Endpoint map in this skill: `references/api-reference.md`.
- Full example apps are optional references, not part of this plugin: https://docs.meetstream.ai/tutorials/sample-apps and https://github.com/meetstream-ai/labs.

**Never invent endpoints or fields.** If the docs don't show it, don't put it in code. For exact paths, fields and types, use the OpenAPI spec: https://docs.meetstream.ai/openapi.json

---

## Latest docs

- Build tracks (integration paths): https://docs.meetstream.ai/guides/introduction/integration-paths
- API reference (base URL, groups): https://docs.meetstream.ai/api-reference/introduction
- Create Bot payload reference: https://docs.meetstream.ai/api-reference/create-bot-payload-reference
- Webhooks and events: https://docs.meetstream.ai/guides/webhooks/webhooks-and-events
- Errors: https://docs.meetstream.ai/errors

When this skill and the docs differ, the docs are the source of truth. For the latest details, fetch the page with `.md` appended, read https://docs.meetstream.ai/llms.txt, or connect the docs MCP server at https://docs.meetstream.ai/_mcp/server.
