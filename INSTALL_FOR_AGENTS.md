# Install for agents

You are an AI agent. The user asked you to install MeetStream. Follow these steps in order. Ask the user only where a step says so.

MeetStream sends a bot into the user's Zoom, Google Meet or Microsoft Teams call. You (the agent) do the note-taking with your own model. MeetStream bills the bot per hour from prepaid credits.

## Three flows

1. **Recording only (Bot API, default).** A bot joins Zoom, Google Meet or Microsoft Teams. You get recordings, transcripts, participants, chat and webhooks after the call, or live data during the call. Use this for every request that does not ask for an agent in the meeting.
2. **Agents in meetings on your own stack (recommended first when the user asks for an agent, a voice agent or a talking bot).**
   - 2a. **Bridge server.** The bot opens two WebSockets to your server: live audio in (`live_audio_required.websocket_url`) and the control socket (`socket_connection_url.websocket_url`) to send audio, chat, images and interrupts back. Run any speech-to-text, LLM and TTS, local or hosted (for example Parakeet for local speech-to-text). Price: the bot price only, no agent infrastructure and no model tokens. [Bridge server docs](https://docs.meetstream.ai/guides/websockets/bridge-server-architecture), starter: [meetstream-ai/meetstream-agent](https://github.com/meetstream-ai/meetstream-agent).
   - 2b. **Your own agent as the brain.** Claude Code, Codex, Hermes, OpenClaw and others through `model.provider: "local_agent"` and the MeetStream Agent Kit. The bot plus $0.25 per hour for the agent infrastructure, no model tokens. Warning: meeting speech reaches an agent that has access to your computer and terminal (prompt injection); keep the computer, the agent and the bridge on for the whole call, and use the lowest access level. [Your own agent](https://docs.meetstream.ai/guides/features/mia-screen-sharing-and-custom-agents).
3. **Managed agent infrastructure (Agents API, API name MIA).** MeetStream hosts the voice agent: MeetStream's inbuilt keys (no provider account; Inbuilt keys work in pipeline mode only: Deepgram (speech-to-text) and OpenAI (LLM and voice). Realtime mode runs on OpenAI and needs your own OpenAI key. Any other provider: bring your own key.) or your own provider keys. The bot plus $0.25 per hour for the agent infrastructure, plus the models you pick ([pricing and keys](https://docs.meetstream.ai/guides/mia/pricing-and-keys)). A hosted agent bot takes only `agent_config_id`, never the bridge sockets.

Details: https://docs.meetstream.ai/guides/introduction/integration-paths

## Step 1: install the plugin or the skills

Pick the user's agent.

**Claude Code**

```bash
claude plugin marketplace add meetstream-ai/claude-plugin
claude plugin install meetstream@meetstream-ai
```

Then ask the user to restart Claude Code.

**Codex**

```bash
codex plugin marketplace add meetstream-ai/claude-plugin
codex plugin add meetstream@meetstream-ai
```

If `codex plugin` is not available, clone the repo (below) and run `./setup --host codex`.

**Copilot CLI**

```bash
copilot plugin install meetstream-ai/claude-plugin
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
git clone https://github.com/meetstream-ai/claude-plugin.git ~/.meetstream-plugin
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

If they ask what MeetStream can do, ask one question: results after the meeting (recording, transcript, notes) or something live during the call (live transcript, chat)? Do not suggest a voice agent unless they ask for one; if they do, follow the three flows above (own stack on a bridge server first, the hosted Agents API when they want no infrastructure work). If `create_bot` answers `Low credits please recharge`, give them https://app.meetstream.ai/billing.

Do not explain the internals (paths, manifests) unless asked.
