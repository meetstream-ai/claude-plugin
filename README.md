<div align="center">

<img src="https://framerusercontent.com/images/qADooqa4mVlS7haEXkSI2cgaE.png" alt="MeetStream" width="80" />

# MeetStream for Claude Code

**Meeting bots for Zoom, Google Meet and Microsoft Teams: recordings, transcripts and live data from your agent or your app, plus agents that talk in the meeting, on your own stack or hosted.**

[![Plugin Version](https://img.shields.io/badge/plugin-v3.2.0-5C4EFF?style=for-the-badge)](https://github.com/meetstream-ai/meetstream-plugin)
[![Live-Tested](https://img.shields.io/badge/endpoints-live--tested-10B981?style=for-the-badge)](https://github.com/meetstream-ai/meetstream-plugin/commits/main)
[![MIT License](https://img.shields.io/badge/license-MIT-yellow?style=for-the-badge)](LICENSE)
[![Get API Key](https://img.shields.io/badge/get%20api%20key-app.meetstream.ai-0EA5E9?style=for-the-badge)](https://app.meetstream.ai/api-keys)

</div>

---

## Build tracks

1. **Recording bot (default).** A bot joins Zoom, Google Meet or Microsoft Teams, records and transcribes. Use this for every request that does not ask for an agent. Ask once: after the call, or live?
   - 1a. **Non-realtime transcription (post-call):** `create_bot`, wait for `Done`, then get the transcript and recordings; webhooks tell you when.
   - 1b. **Real-time transcription (live):** the live transcription webhook, the real-time audio WebSocket, the meeting control socket, chat, raise or lower hand.
2. **Bridge server (your own stack, local).** The bot connects out to your server over two WebSockets: `live_audio_required.websocket_url` (meeting audio in) and `socket_connection_url.websocket_url` (audio, chat and images out). On a laptop, expose it with a local tunnel (ngrok, cloudflared). Price: the bot price only, no agent infrastructure and no model tokens. Free to run locally; check each model's license before commercial use: speech-to-text with whisper.cpp or faster-whisper, NVIDIA Parakeet (parakeet-mlx on Apple silicon), Vosk or Moonshine; an LLM through Ollama, LM Studio or llama.cpp (Llama, Qwen, Gemma, Mistral), or the model of the harness you already use; text-to-speech with Piper, Kokoro, Chatterbox or macOS `say`. [Bridge server docs](https://docs.meetstream.ai/guides/websockets/bridge-server-architecture), starter: [meetstream-ai/meetstream-agent](https://github.com/meetstream-ai/meetstream-agent).
3. **Agents API infra (voice agents, API name MIA, hosted by MeetStream).** The bot plus $0.25 per hour for the agent infrastructure, plus the models you pick ([pricing and keys](https://docs.meetstream.ai/guides/mia/pricing-and-keys)). A hosted agent bot takes only `agent_config_id`, never the bridge sockets.
   - 3a. **MeetStream's own, default keys** (recommended for "just host it"): no provider account. Inbuilt keys work in pipeline mode only: Deepgram (speech-to-text) and OpenAI (LLM and voice). Realtime mode runs on OpenAI and needs your own OpenAI key. Any other provider: bring your own key. If a section is refused, use 3c.
   - 3b. **Bring your own agent infra (LiveKit): COMING SOON.** Not available yet; no setup steps.
   - 3c. **Bring your own keys:** OpenAI, Anthropic, Deepgram, ElevenLabs and others in the docs.
   - 3d. **Your coding agent as the brain: COMING SOON.** Your own agent CLI (Claude Code, Codex, Hermes and others) as MIA's brain through `meetstream setup` and `meetstream agent serve` over the MeetStream relay (no tunnel). Not available yet (the relay is not in production); no setup steps. When it ships, meeting speech will reach an agent with access to your computer and terminal (prompt injection). Today, use track 2 (with your harness's own model as the LLM) or track 3a/3c.

If the user wants an agent and does not say which, ask once: run your own stack (track 2), or let MeetStream host it (track 3a/3c)? Never present 3b or 3d as available.

**The `meetstream` CLI** is the local way in (terminal commands, scripts, `listen`, `setup`); the hosted MCP is the chat-style way in. Agents call it as `meetstream <command> --json --no-input`; `npx -y @meetstream/cli <command>` works with no install (or `npm install -g @meetstream/cli`, `pipx install meetstream-cli`, `brew install meetstream-ai/tap/meetstream`). `meetstream login` signs in through the browser. Per track: 1a `meetstream join <url>`, then `meetstream transcript <bot-id> --wait`; 1b `meetstream join <url> -t meetstream_streaming --live-transcript-webhook https://<public-url>/webhook` with `meetstream listen`; 2 `meetstream join <url> --live-audio-ws wss://<public-url>/audio --socket-ws wss://<public-url>/control`; 3a `meetstream setup --mode hosted`, then `meetstream join <url> --agent-config <id>`; 3c `meetstream setup --mode byok` (keys are added in the dashboard). Commands and JSON shapes: [`skills/meetstream/references/meetstream-cli.md`](skills/meetstream/references/meetstream-cli.md).

Overview: [Integration paths](https://docs.meetstream.ai/guides/introduction/integration-paths).

---

## 60-second quickstart

```bash
# 1. Install the plugin (adds the skills and the hosted MeetStream MCP server)
/plugin marketplace add meetstream-ai/meetstream-plugin
/plugin install meetstream@meetstream-ai

# 2. Sign in: /mcp -> meetstream -> Authenticate (no key to copy)
#    For your own code, set a key instead: export MEETSTREAM_API_KEY=ms_xxxxx

# 3. Ask
claude "send a bot to https://meet.google.com/abc-defg-hij and give me notes after the call"
```

The skills give the fastest path first: the shortest working request (curl, Node [`@meetstream/sdk`](https://www.npmjs.com/package/@meetstream/sdk), Python [`meetstream-sdk`](https://pypi.org/project/meetstream-sdk/)), then the options. They teach the API; they do not paste sample apps. For complete example apps, see [Tutorials and Sample Apps](https://docs.meetstream.ai/tutorials/sample-apps) and the [labs repo](https://github.com/meetstream-ai/labs).

---

## What you can ask

| Goal | Try in Claude | Skill |
|---|---|---|
| Notes after a call | *"record my 3pm call and send me notes"* | `join-meeting`, `meeting-brief` |
| Notetaker in your app | *"build a notetaker that puts summaries in my app"* | `notetaker` |
| Live captions or coaching | *"stream live captions from my Google Meet into my web app"* | `realtime-streaming`, `sales-coach` |
| Calendar auto-join | *"auto-record every meeting on my Google Calendar"* | `calendar-automation` |
| Recordings and per-speaker audio | *"download the recording and each speaker's audio"* | `recordings-and-media` |
| Agent on your own stack (on request) | *"build a voice agent on free local models on my laptop"* | `realtime-streaming` (track 2, bridge server) |
| Hosted voice agent (on request) | *"host a voice agent that answers questions in my Zoom calls"* | `mia-voice-agents` |
| Recording for your customers (SaaS) | *"bots join our customers' calls, recordings per customer in our app"* | `for-your-customers` |
| Agent recipes by job (on request) | *"an agent in our standup that only talks when someone says its name"* | `mia-voice-agents` |
| Move off Recall.ai | *"migrate this repo from Recall to MeetStream"* | `migrate-from-recall` |

---

## What's inside

```
skills/
├── meetstream/             <- Core skill: build tracks, routing, API reference, lifecycle, decision tree
├── getting-started/        <- First-time setup: sign in or API key, then post-call or live
├── join-meeting/           <- Send a bot to a meeting (now or later), chat, raise hand
├── meeting-brief/          <- After the call: notes, decisions, action items
├── notetaker/              <- Fastest path to a post-call notetaker in your app (API guide)
├── for-your-customers/     <- Multi-tenant: bots in your customers' meetings, per-customer routing, storage, scale
├── sales-coach/            <- Fastest path to live coaching from the live transcript (API guide)
├── calendar-automation/    <- Auto-join from Google or Outlook calendars
├── realtime-streaming/     <- Live captions, audio, video, control socket, bridge server for your own agent stack
├── recordings-and-media/   <- Recordings, per-participant audio/video, retention
├── webhooks/               <- Webhook events, signatures, local development
├── platform-setup/         <- Zoom (your Zoom app, OBF or ZAK), Google Meet, Teams, WhatsApp (Beta), signed-in bots
├── mia-voice-agents/       <- Agents in meetings: track picker, bridge (track 2), hosted Agents API (3a/3c; 3b, 3d coming soon), Grok and Gemini, recipes
├── migrate-from-recall/    <- Recall.ai to MeetStream
├── verify-account/         <- Read-only account check: key, balance, providers
├── test-bot/               <- Send a test bot + watch webhooks live
└── troubleshooting/        <- 401/403/422/202, missing transcripts, bots that never join

.mcp.json, mcp.json         <- Hosted MeetStream MCP server (browser sign-in, no key to copy): bots, transcripts,
                               voice agents (list_agents, create_agent), take_screenshot, calendars
.cursor-plugin/             <- Cursor manifest (same skills, same server) and marketplace (-> plugins/cursor)
gemini-extension.json       <- Gemini CLI extension (generated)
listing/                    <- Store listing text (listing.json) and icons (brand/)
scripts/build_stores.py     <- Writes the store builds in plugins/ (run with --check in CI)
plugins/                    <- Generated store builds: claude-directory, cursor, agent-plugin, antigravity,
                               openclaw; plus hermes (the native Hermes plugin, maintained by hand)

agents/
└── meetstream-debugger     <- Subagent for diagnosing bot failures
```

18 skills. Each one ends with a "Latest docs" section; when a skill and the docs differ, [the docs](https://docs.meetstream.ai) win. Agents can read https://docs.meetstream.ai/llms.txt, any page with `.md` appended, or the docs MCP server at https://docs.meetstream.ai/_mcp/server.

## Live-tested correctness

Every endpoint, field name, response shape, and webhook event in this plugin has been verified against the live API and the public docs.

- `create_bot` returns HTTP **201** Created
- `bot_details.transcript_id` is the canonical stateless fetch path (not in any webhook payload)
- A failed transcript returns **422** with the status and the reason; it is final, so do not retry it
- Streaming providers produce **no post-call** `transcription.processed` event
- `bot.error` fires mid-meeting for streaming-provider auth issues (bot keeps recording)
- `recording_permission_denied_timeout` range is **60-600** seconds (default 600)
- `in_call_recording_timeout` minimum is **600** seconds
- `POST /bots/{id}/transcribe` overwrites `bot_details.transcript_id` and fires exactly one webhook (no `bot.done` follow-up)
- The prepaid balance is on https://app.meetstream.ai/billing; the read-only `GET /api/v1/billing/balance` may answer "not available" where it is not on yet

---

## Installation

### Install in any harness

Every harness uses the same hosted MCP server, `https://mcp.meetstream.ai/mcp`, with browser sign-in (OAuth): the client opens app.meetstream.ai, you sign in and click **Allow**, and no key is copied. The skills come from this repository. Store builds live in `plugins/` and are generated from `skills/` and `listing/` by `scripts/build_stores.py`.

| Harness | Install | Sign in |
|---|---|---|
| Claude Code | `/plugin marketplace add meetstream-ai/meetstream-plugin`, then `/plugin install meetstream@meetstream-ai` | `/mcp` → `meetstream` → **Authenticate** |
| Claude (Directory) | Install **MeetStream** from the Claude plugin directory when it is listed (build: `plugins/claude-directory`) | Connect when asked |
| Codex | `codex plugin marketplace add meetstream-ai/meetstream-plugin`, then `/plugins` → **meetstream** | `codex mcp login meetstream` |
| ChatGPT | OpenAI plugin directory when it is listed (build: `plugins/agent-plugin`) | Connect when asked |
| Cursor | Cursor Marketplace when it is listed, or Settings → Plugins → Add marketplace `meetstream-ai/meetstream-plugin` (build: `plugins/cursor`) | Settings → MCP → **Connect** |
| Copilot CLI | `copilot plugin install meetstream-ai/meetstream-plugin` (full plugin), or `copilot plugin install meetstream-ai/meetstream-plugin:plugins/agent-plugin` (skills and MCP only) | `/mcp` → sign in to `meetstream` |
| Gemini CLI | `gemini extensions install https://github.com/meetstream-ai/meetstream-plugin` (reads `gemini-extension.json`, `skills/`, `agents/`) | `/mcp auth meetstream` |
| Antigravity | Copy `plugins/antigravity` to `~/.gemini/config/plugins/meetstream`, or run `agy plugin import claude` after the Claude Code install | Sign in when the first tool runs |
| OpenCode | Add the `opencode.json` snippet below; copy `skills/*` to `.opencode/skills/` (project) or `~/.config/opencode/skills/` | `opencode mcp auth meetstream` |
| Cline | Follow [`llms-install.md`](llms-install.md) (remote server by URL); skills from `.claude/skills/` or `.cline/skills/` | Sign in when Cline asks |
| Kiro | Powers panel → **Add Custom Power** → `https://github.com/meetstream-ai/meetstream-plugin/tree/main/plugins/agent-plugin` | Sign in when Kiro asks |
| Goose | Add the remote extension (Streamable HTTP) `https://mcp.meetstream.ai/mcp`, or pick it from the official MCP Registry; skills from `.agents/skills/` | Sign in when Goose asks |
| Hermes | `hermes plugins install meetstream-ai/hermes-meetstream --enable` (native plugin with live meeting chat; source in `plugins/hermes`) | Hermes asks for a MeetStream API key |
| OpenClaw | `openclaw plugins install meetstream --marketplace meetstream-ai/meetstream-plugin`, or `./setup --host openclaw` | `openclaw mcp login meetstream` |
| Warp | Settings → MCP → add the URL (Warp also reads a project `.mcp.json`) | One-click sign-in |
| Amp | `amp skill add https://github.com/meetstream-ai/meetstream-plugin`, then add the MCP URL in Amp's MCP settings | Sign in when Amp asks |
| Zed, VS Code | Add the server from the official MCP Registry (`io.github.meetstream-ai/meetstream-mcp`) or by URL (Zed: Settings → AI → MCP Servers) | Standard MCP OAuth prompt |

OpenCode `opencode.json`:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "meetstream": { "type": "remote", "url": "https://mcp.meetstream.ai/mcp" }
  }
}
```

### Claude Code (CLI)

```bash
# Add the marketplace + install
/plugin marketplace add meetstream-ai/meetstream-plugin
/plugin install meetstream@meetstream-ai
```

Restart Claude Code, run `/mcp`, pick `meetstream`, then **Authenticate** (sign in at app.meetstream.ai and click **Allow**). The plugin includes the hosted MeetStream MCP server, so there is no key to copy.

Then in any project:
```
"send a bot to <meeting link> and take notes"
"get the notes from my last meeting"
"verify my meetstream account"
"build me an AI meeting notetaker"
"build a real-time AI sales coach"
"set up Google Calendar auto-recording for my meetings"
"connect Google Calendar to MeetStream"
```

### Codex, Copilot CLI, OpenClaw, Muse Code

```bash
codex plugin marketplace add meetstream-ai/meetstream-plugin && codex plugin add meetstream@meetstream-ai   # Codex
copilot plugin install meetstream-ai/meetstream-plugin                                                      # Copilot CLI
git clone https://github.com/meetstream-ai/meetstream-plugin ~/.meetstream-plugin && ~/.meetstream-plugin/setup --host muse   # Muse, OpenClaw
```

Hermes has its own plugin: [hermes-meetstream](https://github.com/meetstream-ai/hermes-meetstream). An agent can install any of these by following [`INSTALL_FOR_AGENTS.md`](INSTALL_FOR_AGENTS.md).

### Cursor / Windsurf / VS Code (Claude extension)

Settings → Plugins → Add marketplace `meetstream-ai/meetstream-plugin` → Install **meetstream** → Reload.

Cursor Agent CLI (`cursor-agent`): the CLI cannot finish the MCP OAuth sign-in, so add a
project `.cursor/mcp.json` with the key header
(`"headers": {"Authorization": "Bearer ${env:MEETSTREAM_API_KEY}"}`). An old MeetStream
Claude plugin in `~/.claude` can shadow the Cursor skills; remove or update it.

### OpenCode

From the project folder:

```bash
git clone https://github.com/meetstream-ai/meetstream-plugin ~/.meetstream-plugin && ~/.meetstream-plugin/setup --host opencode
```

It links the skills into `.opencode/skills/` and adds the hosted MCP server to
`opencode.json` with `"headers": {"Authorization": "Bearer {env:MEETSTREAM_API_KEY}"}`.
If a `CLAUDE.md` in the folder conflicts, run OpenCode with `OPENCODE_DISABLE_CLAUDE_CODE=1`.

### Update to the latest version

```bash
claude plugin update meetstream-ai/meetstream
```

---

## Configuration

Set once in your shell:
```bash
export MEETSTREAM_API_KEY=ms_xxxxx   # get one at https://app.meetstream.ai/api-keys
```

Optional for local webhook development:
```bash
export PUBLIC_URL=https://your-ngrok-url.ngrok-free.app
```

---

## Supported meeting platforms

| Platform | Setup | Live video | Per-participant audio |
|----------|-------|------------|----------------------|
| Google Meet | None | ✅ | ✅ |
| Microsoft Teams | None | ✅ | ❌ |
| Zoom | Your Zoom app (Meeting SDK credentials in Dashboard > Integrations > Zoom); the bot joins with an OBF or ZAK token | ❌ | ✅ |

---

## The canonical post-call transcript flow

```
create_bot (with post-call provider + callback_url)
  ↓
bot.joining → bot.inmeeting → bot.recording
  ↓
[meeting runs]
  ↓
bot.leaving → bot.stopped → manifest.completed → audio.processed
  ↓
transcription.processed ← webhook fires when transcript is ready
  ↓
GET /bots/{bot_id}/detail → read bot_details.transcript_id
  ↓
GET /transcript/{transcript_id}/get_transcript → top-level array of segments
  ↓
bot.done ← terminal event
```

The skills walk you through every variant of this flow (live, post-call, hybrid, voice agent, calendar auto-scheduled) with the minimal calls for each.

---

## Links

- 🌐 [meetstream.ai](https://meetstream.ai) - product
- 📖 [docs.meetstream.ai](https://docs.meetstream.ai) - full API reference
- 🎛️ [app.meetstream.ai](https://app.meetstream.ai) - dashboard + API keys
- 🐙 [github.com/meetstream-ai/meetstream-plugin](https://github.com/meetstream-ai/meetstream-plugin) - this repo
- 💬 [hello@meetstream.ai](mailto:hello@meetstream.ai) - support

---

<!-- SEO keywords: meeting intelligence, AI notetaker, AI meeting assistant, AI sales coach,
     conversation intelligence, meeting transcription API, meeting bot API, real-time transcription,
     live transcription, speaker diarization, AI meeting summarizer, meeting recorder API,
     meeting summary generator, meeting bot SDK, AI conversation analytics, meeting AI platform,
     sales call analyzer, sales conversation intelligence, AI call coaching, real-time coaching,
     live meeting captions, meeting recap, meeting action items, AI meeting agent,
     Google Calendar integration, Google Calendar bot, Google Calendar meeting bot,
     calendar automation, calendar notetaker, scheduled meeting bot, recurring meeting bot,
     OAuth calendar integration, auto-record meetings, calendar API integration,
     Zoom bot API, Google Meet bot API, Microsoft Teams bot API,
     webhook, MCP server, Claude Code plugin, Anthropic plugin, MeetStream, MeetStream API -->

<div align="center">

Built by [MeetStream](https://meetstream.ai) · Made for [Claude Code](https://claude.ai/code)

</div>
