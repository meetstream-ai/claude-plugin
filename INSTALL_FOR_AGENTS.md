# Install for agents

You are an AI agent. The user asked you to install MeetStream. Follow these steps in order. Ask the user only where a step says so.

MeetStream sends a bot into the user's Zoom, Google Meet or Microsoft Teams call. You (the agent) do the note-taking with your own model. MeetStream bills the bot per hour from prepaid credits.

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

Details: https://docs.meetstream.ai/guides/introduction/integration-paths

## Step 1: install the plugin or the skills

Pick the user's agent.

**Claude Code**

```bash
claude plugin marketplace add meetstream-ai/meetstream-plugin
claude plugin install meetstream@meetstream-ai
```

Then ask the user to restart Claude Code.

**Codex**

```bash
codex plugin marketplace add meetstream-ai/meetstream-plugin
codex plugin add meetstream@meetstream-ai
```

If `codex plugin` is not available, clone the repo (below) and run `./setup --host codex`.

**Copilot CLI**

```bash
copilot plugin install meetstream-ai/meetstream-plugin
```

**Hermes:** use the Hermes plugin, which also answers in the meeting chat live:

```bash
hermes plugins install meetstream-ai/hermes-meetstream --enable
```

It asks for a MeetStream API key (create one at https://app.meetstream.ai/api-key). Then skip to Step 3.

**Cursor:** install the MeetStream plugin from the Cursor marketplace ([meetstream-cursor-plugin](https://github.com/meetstream-ai/meetstream-cursor-plugin)).

- **Cursor Agent CLI (`cursor-agent`):** the plugin's URL-only MCP entry needs OAuth, which
  the CLI cannot finish (it shows `needsAuth`). In the project, add `.cursor/mcp.json` with
  the key header (the key stays in the environment):

```json
{
  "mcpServers": {
    "meetstream": {
      "url": "https://mcp.meetstream.ai/mcp",
      "headers": { "Authorization": "Bearer ${env:MEETSTREAM_API_KEY}" }
    }
  }
}
```

- An old MeetStream Claude plugin in `~/.claude/plugins` (or skills in `~/.claude/skills`)
  can load in Cursor too and shadow the Cursor plugin's skills. Remove or update the old
  one so only the current skills load.

**OpenCode:** run `setup --host opencode` from a clone (below) in the project folder, or by
hand: link the skills into the project's `.opencode/skills/`, and add the MCP server to the
project's `opencode.json` (the key stays in the environment as `MEETSTREAM_API_KEY`):

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "meetstream": {
      "type": "remote",
      "url": "https://mcp.meetstream.ai/mcp",
      "headers": { "Authorization": "Bearer {env:MEETSTREAM_API_KEY}" },
      "oauth": false,
      "enabled": true
    }
  }
}
```

If OpenCode also loads a `CLAUDE.md` that conflicts with the task, start it with
`OPENCODE_DISABLE_CLAUDE_CODE=1`.

**OpenClaw, Muse Code (or any agent above as a fallback):** clone the repo once, then run `setup` for the agent:

```bash
git clone https://github.com/meetstream-ai/meetstream-plugin.git ~/.meetstream-plugin
~/.meetstream-plugin/setup --host <openclaw|muse|codex|claude|copilot|opencode>
```

`setup` links the skills into the agent's skills folder and adds the hosted MCP server `https://mcp.meetstream.ai/mcp` with OAuth. It is safe to run again. On Windows, run it from Git Bash or WSL.

**Any other agent with skills and MCP support:** add the skills from `skills/` with your agent's skill installer, and add the remote MCP server `meetstream` at `https://mcp.meetstream.ai/mcp` (streamable HTTP, OAuth).

## Step 2: sign in

Ask the user to sign in. A browser opens `app.meetstream.ai`; they sign in or create an account, then click **Allow**. MeetStream creates an API key for this agent; neither of you needs to copy it.

| Agent | Sign-in |
|---|---|
| Claude Code | `/mcp`, pick `meetstream`, **Authenticate** |
| Codex | `codex mcp login meetstream` |
| OpenClaw | `openclaw mcp login meetstream` |
| Muse Code | `muse mcp login meetstream` |
| Copilot CLI | `/mcp`, then sign in to `meetstream` |
| Cursor | Settings → MCP → **Connect** next to `meetstream` (CLI: key header in `.cursor/mcp.json`, no sign-in) |
| OpenCode | none: the key header in `opencode.json` signs in |

Wait until the user says the browser shows that sign-in finished.

## Step 3: verify with a real call

Call the MeetStream MCP tool **`list_bots`** (no arguments).

- Success looks like `{"bots": [...], "hasNextPage": false, ...}`. A new account has an empty `bots` list. That is a pass.
- `401`, `unauthorized` or "not signed in": repeat Step 2.
- No `meetstream` tools at all: the agent was not restarted, or the MCP server was not added. Re-run Step 1 for this agent, restart it, and try again.

Do not send a bot as a test unless the user gives you a meeting link and asks for it.

## Step 4: tell the user

Say, in two lines: MeetStream is installed and signed in, and they can now say things like:

- "Send a bot to <meeting link> and take notes."
- "Get the notes from my last meeting."
- "Create a hosted voice agent for my next call." (the agent uses `list_agents`, then `create_agent`, from the chat)

If they ask what MeetStream can do, ask one question: results after the meeting (recording, transcript, notes) or something live during the call (live transcript, chat)? Do not suggest a voice agent unless they ask for one; if they do, follow the build tracks above (track 2, a bridge server on their own stack, or track 3a/3c, the hosted Agents API, with 3a for "just host it"; 3b and 3d are coming soon). If `create_bot` answers `Low credits please recharge`, give them https://app.meetstream.ai/billing.

Do not explain the internals (paths, manifests) unless asked.
