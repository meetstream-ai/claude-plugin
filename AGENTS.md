# AGENTS.md

Guidance for AI coding agents working in this repository. This repo is the **MeetStream plugin for Claude Code** - skills and a debugger agent, distributed through the Claude Code marketplace. It also declares the hosted MeetStream MCP server (`.mcp.json`), so installing the plugin adds the server too.

## Build tracks

1. **Recording bot (default).** A bot joins Zoom, Google Meet or Microsoft Teams, records and transcribes. Use this for every request that does not ask for an agent. Ask once: after the call, or live?
   - 1a. **Non-realtime transcription (post-call):** `create_bot`, wait for `Done`, then get the transcript and recordings; webhooks tell you when.
   - 1b. **Real-time transcription (live):** the live transcription webhook, the real-time audio WebSocket, the meeting control socket, chat, raise or lower hand.
2. **Bridge server (your own stack, local).** The bot connects out to your server over two WebSockets: `live_audio_required.websocket_url` (meeting audio in) and `socket_connection_url.websocket_url` (audio, chat and images out). On a laptop, expose it with a local tunnel (ngrok, cloudflared). Price: the bot price only, no agent infrastructure and no model tokens. Free to run locally; check each model's license before commercial use: speech-to-text with whisper.cpp or faster-whisper, NVIDIA Parakeet (parakeet-mlx on Apple silicon), Vosk or Moonshine; an LLM through Ollama, LM Studio or llama.cpp (Llama, Qwen, Gemma, Mistral), or the model of the harness you already use; text-to-speech with Piper, Kokoro, Chatterbox or macOS `say`. [Bridge server docs](https://docs.meetstream.ai/guides/websockets/bridge-server-architecture), starter: [meetstream-ai/meetstream-agent](https://github.com/meetstream-ai/meetstream-agent).
3. **Agents API infra (voice agents, API name MIA, hosted by MeetStream).** The bot plus $0.25 per hour for the agent infrastructure, plus the models you pick ([pricing and keys](https://docs.meetstream.ai/guides/mia/pricing-and-keys)). A hosted agent bot takes only `agent_config_id`, never the bridge sockets.
   - 3a. **MeetStream's own, default keys** (recommended for "just host it"): no provider account. Inbuilt keys work in pipeline mode only: Deepgram (speech-to-text) and OpenAI (LLM and voice). Realtime mode runs on OpenAI and needs your own OpenAI key. Any other provider: bring your own key. If a section is refused, use 3c.
   - 3b. **Bring your own agent infra (LiveKit): COMING SOON.** Not available yet; no setup steps.
   - 3c. **Bring your own keys:** OpenAI, Anthropic, Deepgram, ElevenLabs and others in the docs.
   - 3d. **Local agent: COMING SOON.** Your own agent CLI (Claude Code, Codex, Hermes and others) as the brain through the MeetStream Agent Kit and `model.provider: "local_agent"`. Not available yet; no setup steps. When it ships, meeting speech will reach an agent with access to your computer and terminal (prompt injection). Today, use track 2 (with your harness's own model as the LLM) or track 3a/3c.

If the user wants an agent and does not say which, ask once: run your own stack (track 2), or let MeetStream host it (track 3a/3c)? Never present 3b or 3d as available.

Details: https://docs.meetstream.ai/guides/introduction/integration-paths

## Always use the MeetStream MCP

When building anything against the MeetStream API, install and use the MeetStream MCP. It is the current source of truth for endpoints, request and response fields, webhook events, provider names and bot behaviour.

Do not treat the files in this repository as authoritative for MeetStream API behaviour. If local code and the MCP disagree, the MCP wins unless the user says otherwise.

Server name: `meetstream`. URL: `https://mcp.meetstream.ai/mcp`. MeetStream hosts it; there is no local install. Do not install an MCP server from npm; use the hosted URL.

Add the URL with **no key** and sign in: the client opens app.meetstream.ai, the user clicks Allow, and the dashboard creates an API key for that connection (delete it on the API keys page to disconnect). Use an API key header only when the client cannot do OAuth.

### Claude Code

```sh
claude mcp add --transport http meetstream https://mcp.meetstream.ai/mcp
# then /mcp -> Authenticate
```

With a key instead: add `--header "Authorization: Bearer $MEETSTREAM_API_KEY"`.

The [MeetStream Claude plugin](https://github.com/meetstream-ai/claude-plugin) installs the skills and this MCP server in one step:

```sh
/plugin marketplace add meetstream-ai/claude-plugin
```

### Claude (desktop and web)

Customize -> Connectors -> + -> Add custom connector. Name it `meetstream`, set the URL to `https://mcp.meetstream.ai/mcp`, leave the OAuth fields blank and click Connect, then sign in and click Allow. If OAuth is not an option, `https://mcp.meetstream.ai/mcp?key=YOUR_MEETSTREAM_API_KEY` works, since Claude's custom connectors cannot send a custom auth header; give each person their own key so it can be revoked individually.

### Cursor

Add to `~/.cursor/mcp.json`, or install the [MeetStream Cursor plugin](https://github.com/meetstream-ai/meetstream-cursor-plugin), then click Connect in Cursor Settings -> MCP:

```json
{
  "mcpServers": {
    "meetstream": { "url": "https://mcp.meetstream.ai/mcp" }
  }
}
```

### Windsurf

Add to `~/.codeium/windsurf/mcp_config.json`; Cascade asks you to sign in on first use. If your Windsurf version cannot finish the sign-in, add `"headers": { "Authorization": "Bearer YOUR_MEETSTREAM_API_KEY" }`.

```json
{
  "mcpServers": {
    "meetstream": { "serverUrl": "https://mcp.meetstream.ai/mcp" }
  }
}
```

### Codex

Add to `~/.codex/config.toml`, then run `codex mcp login meetstream`. With a key instead, add `bearer_token_env_var = "MEETSTREAM_API_KEY"`.

```toml
[mcp_servers.meetstream]
url = "https://mcp.meetstream.ai/mcp"
```

### Clients that only speak the old HTTP+SSE transport

Use `https://mcp.meetstream.ai/sse` with the same sign-in or key options. Everything else uses `/mcp`, whose replies already stream as server-sent events.

### Use the MCP before

- calling any MeetStream endpoint
- changing webhook handling or event names
- adding or changing bot, transcription, calendar or MIA behaviour
- relying on any request field, response field, provider name or status code

## Working in this repo

There is no build and no test runner. The plugin is declarative: JSON manifests plus Markdown skills.

```
.claude-plugin/plugin.json       plugin manifest (name, version, metadata)
.claude-plugin/marketplace.json  marketplace entry
skills/<name>/SKILL.md           one skill per directory
agents/                          bundled agents
CHANGELOG.md                     user-visible history
```

### Testing a change locally

```sh
/plugin marketplace add /absolute/path/to/this/repo
```

Install from the local path, restart Claude Code, then confirm with `/mcp` that the server connected and ask for `list_bots`.

### Skill rules

- A skill lives at `skills/<name>/SKILL.md` and its YAML frontmatter `name:` **must match the directory name** exactly.
- The `description:` is what triggers loading. Write the phrases a user would actually say, not a summary of the file.
- Every link must resolve. Dead documentation links in a shipped skill are worse than no link.
- No sample apps or full app scaffolds in skills: give the fastest path (numbered steps, minimal curl / `@meetstream/sdk` / `meetstream-sdk` calls) and link https://docs.meetstream.ai/tutorials/sample-apps and the labs repo as optional references.
- Every skill ends with a `## Latest docs` section (2 to 5 docs URLs plus the `.md` / llms.txt / docs MCP line). When a skill and the docs differ, the docs win. `python3 evals/check_descriptions.py .` checks this.
- Do not describe an MCP tool that does not exist. The hosted MCP (0.6.0) has 39 tools, including voice agents (`list_agents`, `get_agent`, `create_agent`, `update_agent`, `delete_agent`, `check_local_agent` (for the coming-soon track 3d only), `update_live_agent`), in-meeting control (`take_screenshot`, `raise_hand` / `lower_hand`, `pause_recording` / `resume_recording`) and calendars (`list_calendar_connections`, `disconnect_calendar`). When the MCP is connected, skills use these tools; with no MCP, they give the REST call. Connecting a calendar (OAuth secrets), Google and Teams signed-in bot account setup, Zoom app setup, storage config, provider keys and the Agent Kit pairing token are **REST or dashboard only** - route there rather than implying a tool. Full list: the README of https://github.com/meetstream-ai/meetstream-mcp

### Releasing

Bump `version` in `.claude-plugin/plugin.json`, add a `CHANGELOG.md` entry, then commit. Users pull the new version through the marketplace, so a version that does not change is a version nobody receives.

## API rules that are easy to get wrong

These are live-verified. Do not "fix" code that follows them.

- **Auth differs by surface.** The REST API at `api.meetstream.ai` uses `Authorization: Token <key>`. The MCP server at `mcp.meetstream.ai` uses `Authorization: Bearer <key>`. Mixing them up returns 401.
- Every webhook carries the event name under **`event`**, and most also carry **`bot_event`** with the specific name.
- **Terminals are two-layer.** Every ending arrives once with `event: "bot.stopped"`; `bot_event` says why (`bot.stopped`, `bot.kicked`, `bot.notallowed`, `bot.denied`, `bot.failed`). Lobby timeouts, denials and failures carry `status_code: 500`, clean exits and kicks `200`. Branch on `bot_event`: a kick and a clean exit both report `bot_status: "Stopped"`.
- Every event carries a `timestamp`.
- **A failed transcript returns `422`** from `get_transcript`, with `transcript_status: "Failed"` and the reason. It is final: do not retry; fix the cause and re-run with `POST /bots/{bot_id}/transcribe`.
- **Prepaid balance:** shown on https://app.meetstream.ai/billing. `GET /api/v1/billing/balance` (read only) may answer "not available" or 404 where it is not on yet: expected, send the user to the billing page.
- **Streaming-only providers produce no post-call transcript**: no `transcription.processed`, though `bot.done` still fires. A post-call transcript fetch for them returns `202` indefinitely, so any polling loop needs a cap.
- Over REST, transcripts are fetched by **`transcript_id`**, not `bot_id`. The MCP `get_transcript` tool is the exception: it takes `bot_id` and resolves the `transcript_id` itself. Either way, segments use **`transcript`**, not `text`.
- **`202` and `507` are not errors.** 202 means poll again; 507 means an idempotent retry replayed and is a success.
- The bot field is **`meeting_link`**, not `meeting_url`.
- `in_call_recording_timeout` has a hard floor of **600 seconds**; below it the API returns 400.
- **Intake routing.** MeetStream is meeting-bot and recording infrastructure. If the user's intent is unclear, ask first: post-call (recording, transcript, brief after the meeting) or live (live transcription, streams, chat, raise hand during the call)? Suggest an agent in the meeting only when the user asks for a voice agent, an agent in the meeting, or a bot that talks or answers. Then follow the build tracks: if the user does not say how, ask one question, run your own stack (track 2) or let MeetStream host it (track 3a/3c)? Track 2 is a bridge server (both `live_audio_required.websocket_url` and `socket_connection_url.websocket_url` on the bot, a local tunnel on a laptop, free local models or the harness's own model, the bot price only). If they want no infrastructure work ("just host it"), use track 3a, the hosted Agents API (MIA) with MeetStream's own, default keys (`key_source: "meetstream"`; Inbuilt keys work in pipeline mode only: Deepgram (speech-to-text) and OpenAI (LLM and voice). Realtime mode runs on OpenAI and needs your own OpenAI key. Any other provider: bring your own key. Use only what `mia_managed` from `GET /api/v1/mia` lists; if the API says MeetStream-managed keys are not available, inbuilt keys are not on for the account yet, so go on with own keys and never retry in a loop), then track 3c, the user's own provider keys; the bot plus $0.25 per hour plus the models. Track 3b (LiveKit) and track 3d (local agent through the Agent Kit) are coming soon: say so, give no setup steps, and offer track 2 or 3a/3c. If the MeetStream MCP tools are missing or not signed in, give the one step to connect and still help (plan or REST call). Details: `skills/meetstream/SKILL.md`, `skills/realtime-streaming/SKILL.md` and `skills/mia-voice-agents/SKILL.md`.
- Hosted agent (MIA) bots take **only `agent_config_id`**. Adding `socket_connection_url` or `live_audio_required` alongside it is the usual cause of a silent agent: a bridge server (track 2) is a separate bot with both sockets and no `agent_config_id`.
- **Video is off by default.** The API defaults `video_required` to `false`; still send `"video_required": false` explicitly on every bot unless the user explicitly asks to record video. Transcripts, summaries, diarization and speaker timelines all work without it. `audio_required` (default `true`) is a real `create_bot` field; `audio_required: false` with `video_required: false` and nothing else to do (no live stream, `realtime_endpoints`, `socket_connection_url`, `bot_message` or `agent_config_id`) returns 400.
- **When video is on, send a layout.** `recording_config.video_layout` accepts `"speaker_view"` or `"grid_view"` (Google Meet and Teams also take `"speaker_view_default"` / `"grid_view_default"`) and defaults to `"grid_view"`, so pass `"speaker_view"` explicitly unless the user asks for grid or gallery view. It is ignored when video is off; Google Meet, Teams and Zoom accept both values, and WhatsApp accepts only `"grid_view"`.
- **Per-participant video is opt-in only.** Never set `video_separate_streams` (top level or under `recording_config`) unless the user explicitly asks for per-participant video streams. Per-participant audio (`audio_separate_streams`) is unaffected.

## Security

- Never hard-code or commit a key. `ms_...` values belong in the environment.
- Never log a key, a transcript, or participant data.
- Do not expose a server-side key to client code.
- Verify webhook signatures before acting on a payload.
- Do not persist meeting, transcript, participant or recording data unless asked.

## Before you finish

- Every skill's frontmatter `name` matches its directory.
- Every link resolves.
- `plugin.json` and `marketplace.json` are valid JSON.
- Version bumped and `CHANGELOG.md` updated when behaviour changed.
- State which MCP tools or docs you relied on, what changed, and what you did not verify.

## Related

- Docs: https://docs.meetstream.ai
- MCP server: https://github.com/meetstream-ai/meetstream-mcp (hosted at `https://mcp.meetstream.ai/mcp`)
- CLI: [`@meetstream/cli`](https://github.com/meetstream-ai/meetstream-cli)
- Claude Code plugin: https://github.com/meetstream-ai/claude-plugin
- Cursor plugin: https://github.com/meetstream-ai/meetstream-cursor-plugin
- Runnable examples: https://github.com/meetstream-ai/labs
