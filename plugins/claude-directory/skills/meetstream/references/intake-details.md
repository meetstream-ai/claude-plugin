# Router details

Moved from the core `meetstream` skill (3.3.1). The router SKILL.md gives the short version; this file keeps the full text: build tracks with the CLI per track, the fastest path, intake routing, Step 0, setup and the SDKs.

## Contents

- [Build tracks](#build-tracks)
- [Intake routing](#intake-routing-read-this-first)
- [Step 0](#step-0-before-writing-any-code)
- [Setup](#setup)
- [SDKs, CLI and sample apps](#sdks-cli-and-sample-apps)

## Build tracks

Name the track in your answer (for example "Track 1b, real-time transcription").

1. **Recording bot (default).** The bot joins Zoom, Google Meet or Microsoft Teams, records and transcribes. Use it for every request that does not ask for an agent. Ask once: after the call, or live?
   - 1a. **Non-realtime transcription (post-call):** `create_bot`, wait for `Done`, then get the transcript and recordings; webhooks tell you when. Skills: `meetstream-cli`, `meetstream-cli`, `handling-webhooks`. CLI: `meetstream join <url>`, then `meetstream transcript <bot-id> --wait`.
   - 1b. **Real-time transcription (live):** the live transcription webhook (`live_transcription_required.webhook_url`), the real-time audio WebSocket, the meeting control socket, chat, raise or lower hand. Skill: `streaming-live-data`. CLI: `meetstream join <url> -t meetstream_streaming --live-transcript-webhook https://<public-url>/webhook` with `meetstream listen` as the local receiver (it needs a public URL or tunnel today).
2. **Bridge server (your own stack, local).** The bot connects out to your server over two WebSockets: `live_audio_required.websocket_url` (meeting audio in, for example `wss://host/bridge/audio`) and `socket_connection_url.websocket_url` (audio, chat and images out, for example `wss://host/bridge`). On a laptop, expose the server with a local tunnel (ngrok or cloudflared). Price: the bot price only, no agent infrastructure and no model tokens. Free to run locally; check each model's license before commercial use:
   - Speech-to-text: whisper.cpp or faster-whisper (Whisper models), NVIDIA Parakeet (parakeet-mlx on Apple silicon), Vosk, Moonshine.
   - LLM: a local model through Ollama, LM Studio or llama.cpp (Llama, Qwen, Gemma, Mistral), or the model of the harness you already use (for example Claude behind Claude Code).
   - Text-to-speech: Piper, Kokoro, Chatterbox, macOS `say`.

   Recipe: `streaming-live-data`. CLI: `meetstream join <url> --live-audio-ws wss://<public-url>/audio --socket-ws wss://<public-url>/control`. Docs: https://docs.meetstream.ai/guides/websockets/bridge-server-architecture . Starter: https://github.com/meetstream-ai/meetstream-agent
3. **Agents API infra (voice agents, API name MIA, hosted by MeetStream).** Bot price + $0.25 per hour agent infrastructure + the models picked. Details: `building-voice-agents`.
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
  **Install the meetstream CLI** (see https://docs.meetstream.ai/build-with-ai/meetstream-cli). Sign in with `meetstream login` (it opens the browser and stores a key; never ask for the key in the chat). Always pass `--json --no-input`. Exit codes: 0 ok, 1 API error, 2 usage or not signed in, 3 not ready yet, 4 transcript failed. JSON shapes: `skills/meetstream/references/meetstream-cli.md`.
- **REST and the SDKs** are for the app code the user builds (below).

### Fastest path (track 1a, Recording bot)

From a terminal or this agent's shell, with the `meetstream` CLI (the meetstream CLI (to install it, see https://docs.meetstream.ai/build-with-ai/meetstream-cli); `meetstream login` signs in):

```bash
meetstream join "https://meet.google.com/abc-defg-hij" -n "Notetaker" -t meetstream --json --no-input
meetstream transcript <bot-id> --wait --json --no-input
```

In app code, the API or the SDKs:

```bash
curl -X POST https://api.meetstream.ai/api/v1/bots/create_bot \
  -H "Authorization: Token YOUR_API_KEY" -H "Content-Type: application/json" \
  -d '{"meeting_link": "https://meet.google.com/abc-defg-hij", "bot_name": "Notetaker",
       "video_required": false, "callback_url": "https://your-server.example/webhook",
       "recording_config": {"transcript": {"provider": {"meetstream": {}}}}}'
```

```ts
import { MeetStream } from '@meetstream/sdk';           // npm install @meetstream/sdk
const ms = new MeetStream();                              // takes your API key
const bot = await ms.bots.create({ meeting_link, bot_name: 'Notetaker', video_required: false });
```

```python
from meetstream import MeetStream                          # pip install meetstream-sdk
ms = MeetStream()                                          # takes your API key
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
   - Post-call → `meetstream-cli`, then `meetstream-cli`; for apps also `handling-webhooks` and
     `getting-transcripts-and-media`.
   - Live → `streaming-live-data` (chat and raise hand are in `meetstream-cli`).
   - Build requests count too: if a build request names only the trigger (a CLI, a
     calendar, a list of links) and not the outcome, ask once.
   - If the request already says which ("record my 3pm call and send me notes" is
     post-call), do not ask. Go.
2. **Agents only on request.** Do not suggest a bot that talks. Bring in agents only when
   the user asks for a "voice agent", an "agent in the meeting", or a bot that talks,
   answers or speaks (or names MIA, the API name). In replies say "voice agent"; most
   users do not know the word MIA.
3. **Agent tracks, in this order** (details in `streaming-live-data` and `building-voice-agents`).
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
     with `agent_config_id`. With no MCP, `POST /api/v1/mia`. Details: `building-voice-agents`.
4. **Generic asks** ("help me get started", "help me use MeetStream", "set up
   MeetStream") → `meetstream`: one connect step if needed, then the post-call or
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
     languages): `building-voice-agents`.
   - **Bots in the user's customers' meetings** (SaaS, per customer, per tenant) →
     `running-in-production`.
   - **Platforms:** Zoom (recommend the user's own Zoom app with OBF or ZAK; set it up before the
     first Zoom bot), Google Meet, Microsoft Teams, and WhatsApp calls (Beta;
     `setting-up-platforms`). Webex, Slack huddles and other services are not supported (400).
   - **First bots:** someone must admit the bot from the waiting room
     (`automatic_leave.waiting_room_timeout`; `NotAllowed` or `Denied` otherwise).
5. **Raise or lower the bot's hand**: with the MCP connected, call the `raise_hand` /
   `lower_hand` tool. With no MCP (or in app code), do it now with REST:
   ```bash
   curl -X POST "https://api.meetstream.ai/api/v1/bots/<bot_id>/send_command" \
     -H "Authorization: Token YOUR_API_KEY" -H "Content-Type: application/json" \
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
  or the REST call (`curl` with `Authorization: Token YOUR_API_KEY`).
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


## Setup

All MeetStream API calls need this header:
```
Authorization: Token YOUR_API_KEY
```

API keys are created at https://app.meetstream.ai/api-keys.

### First-time users: sign in before anything else

If the MeetStream MCP tools are not connected, or a tool answers 401 or "not signed in", sign in
through the MeetStream MCP: the client opens app.meetstream.ai in the browser, the user signs in
(or signs up) and clicks **Allow**. No key is copied. From a terminal, `meetstream login` does the
same. For the user's own app code, the user creates an API key at
https://app.meetstream.ai/api-keys and keeps it in the app's own secret store; never ask for it in
the chat. The full first-time flow (signup, sign-in, keys for app code, validation, first bot) is in
`references/getting-started.md`. Then resume the original request.

Base URL: `https://api.meetstream.ai/api/v1` (no trailing slash in canonical examples).

Default language: **Python** unless the user specifies otherwise.

---

## SDKs, CLI and sample apps

- Node: `npm install @meetstream/sdk` (Node 18.17+). Python: `pip install meetstream-sdk` (Python 3.8+). Both read your MeetStream API key: https://docs.meetstream.ai/build-with-ai/sdks
- CLI: the meetstream CLI (to install it, see https://docs.meetstream.ai/build-with-ai/meetstream-cli), `npm install -g @meetstream/cli`, `pipx install meetstream-cli` or `brew install meetstream-ai/tap/meetstream`; sign in with `meetstream login`. Commands and JSON shapes: `references/meetstream-cli.md`. Step-by-step CLI workflows: skill `meetstream-cli`. Docs: https://docs.meetstream.ai/build-with-ai/meetstream-cli
- Endpoint map in this skill: `references/api-reference.md`.
- Full example apps are optional references, not part of this plugin: https://docs.meetstream.ai/tutorials/sample-apps and https://github.com/meetstream-ai/labs.

**Never invent endpoints or fields.** If the docs don't show it, don't put it in code. For exact paths, fields and types, use the OpenAPI spec: https://docs.meetstream.ai/openapi.json
