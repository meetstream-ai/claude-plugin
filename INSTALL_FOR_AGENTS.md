# Install for agents

You are an AI agent. The user asked you to install MeetStream. Follow these steps in order. Ask the user only where a step says so.

MeetStream sends a bot into the user's Zoom, Google Meet or Microsoft Teams call. You (the agent) do the note-taking with your own model. MeetStream bills the bot per hour from prepaid credits.

## Two ways to integrate

1. **Bot API (default): meeting bots and recording.** A bot joins Zoom, Google Meet or Microsoft Teams. You get recordings, transcripts, participants, chat and webhooks after the call, or live data during the call.
2. **Agents API (only on request): voice agents in the meeting.** A voice agent (API name MIA) on the bot listens and talks. Use it only when the user asks for a voice agent or a bot that talks. Price: the bot plus $0.25 per hour for the agent infrastructure, plus the models picked with MeetStream's inbuilt keys (OpenAI and Deepgram), or the user's own provider keys.

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

**OpenClaw, Muse Code (or any agent above as a fallback):** clone the repo once, then run `setup` for the agent:

```bash
git clone https://github.com/meetstream-ai/claude-plugin.git ~/.meetstream-plugin
~/.meetstream-plugin/setup --host <openclaw|muse|codex|claude|copilot>
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
| Cursor | Settings → MCP → **Connect** next to `meetstream` |

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

If they ask what MeetStream can do, ask one question: results after the meeting (recording, transcript, notes) or something live during the call (live transcript, chat)? Do not suggest a voice agent unless they ask for one. If `create_bot` answers `Low credits please recharge`, give them https://app.meetstream.ai/billing.

Do not explain the internals (paths, manifests) unless asked.
