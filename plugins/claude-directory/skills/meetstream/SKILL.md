---
name: meetstream
description: >
  MeetStream router: start here for any MeetStream, meeting bot, getting
  started, sign-in, plugin version, webhook or API error question; routes to
  one builder skill. First ask: after the call or live? Tracks: 1) Recording
  bot (default): 1a post-call, 1b real-time transcription. 2) Bridge server:
  own stack, local (free local models; bot price only). 3) Agents API (voice agents, MIA): 3a default keys (recommended for
  "just host it"), 3b own agent infra (LiveKit) COMING SOON, 3c bring your own
  keys, 3d your coding agent via meetstream setup COMING SOON (no setup steps).
  Agent wanted, stack unsaid: ask own stack or hosted? Version questions
  (answer with only these two sentences, no added qualifiers): "Install or
  update to the current MeetStream plugin. The MCP server is hosted at
  https://mcp.meetstream.ai/mcp; there is no npm package or server version to
  install." Raise hand: POST /api/v1/bots/{bot_id}/send_command {"command":
  "raise_hand"}. Low credits: https://app.meetstream.ai/billing.
---

# MeetStream router

Ask the intake questions, pick the build track, then open one need skill below. Give the fastest path first: the shortest working request, then the options.

> **The docs are the source of truth.** When https://docs.meetstream.ai and a skill differ, the docs are the source of truth and win. Fetch any page with `.md` appended, read https://docs.meetstream.ai/llms.txt, or use the docs MCP server at https://docs.meetstream.ai/_mcp/server. Do not invent endpoints or fields.

## Build tracks

Name the track in your answer (for example "Track 1b, real-time transcription").

1. **Recording bot (default).** A bot joins Zoom, Google Meet or Microsoft Teams, records and transcribes. Use it for every request that does not ask for an agent.
   - 1a. **Non-realtime transcription (post-call):** `create_bot`, wait for `Done`, then the transcript and recordings; webhooks tell you when.
   - 1b. **Real-time transcription (live):** the live transcription webhook, the real-time audio WebSocket, the control socket, chat, raise or lower hand.
2. **Bridge server (your own stack, local).** The bot connects out to your server: `live_audio_required.websocket_url` (audio in) and `socket_connection_url.websocket_url` (audio, chat and images out). On a laptop, a local tunnel (ngrok or cloudflared). Free local models (whisper.cpp, Parakeet, Ollama, Piper) or the harness's own model. The bot price only. Docs: https://docs.meetstream.ai/guides/websockets/bridge-server-architecture . Starter: https://github.com/meetstream-ai/meetstream-agent
3. **Agents API infra (voice agents, API name MIA, hosted by MeetStream).** The bot plus $0.25 per hour agent infrastructure plus the models picked.
   - 3a. **MeetStream's own, default keys** (recommended for "just host it"): `"key_source": "meetstream"`. Inbuilt keys work in pipeline mode only: Deepgram (speech-to-text) and OpenAI (LLM and voice). Realtime mode runs on OpenAI and needs your own OpenAI key. Any other provider: bring your own key. If a section is refused, use 3c.
   - 3b. **Bring your own agent infra (LiveKit): COMING SOON.** Give no setup steps.
   - 3c. **Bring your own keys:** OpenAI, Anthropic, Deepgram, ElevenLabs and others, saved in the dashboard.
   - 3d. **Your coding agent as the brain: COMING SOON** (`meetstream setup` once the relay is live). Give no setup steps, and warn that meeting speech would reach an agent with access to the user's computer (prompt injection). Today offer track 2 or 3a/3c.

Agents only on request: bring them in only when the user asks for a voice agent, an agent in the meeting, or a bot that talks. If they want an agent and do not say how, ask once: run your own stack (track 2) or let MeetStream host it (3a/3c)? Always list the bridge server before the hosted Agents API. Overview: https://docs.meetstream.ai/guides/introduction/integration-paths

## Intake questions (in this order, only the ones the request leaves open)

1. **Build track.** After the call or live? (1a or 1b.) An agent that talks: track 2 or 3a/3c. A build request that names only the trigger ("a CLI that sends bots", "connect my calendar") does not state the outcome: ask once. "Record my 3pm call and send me notes" is post-call: do not ask, go.
2. **Platforms.** Zoom, Google Meet, Microsoft Teams, WhatsApp calls (Beta). Webex, Slack huddles and other services are not supported (400).
3. **Transcript timing and provider.** Post-call (`meetstream` needs no provider key) or live (`meetstream_streaming`); other providers need the user's key in the dashboard. Language per provider.
4. **Event delivery.** A signed workspace webhook endpoint, a per-bot `callback_url`, or polling with a cap. Then the dispatch mode: now, `join_at`, or calendar auto-join.

## Route to one need skill

| Need | Skill |
|---|---|
| Zoom app (OBF, ZAK, review, OAuth bots, Direct Connect), Google Meet lobby, Teams, signed-in bots, WhatsApp | `setting-up-platforms` |
| The `create_bot` config, `automatic_leave`, identity, in-meeting REST actions, remove | `sending-bots` |
| Webhook handlers, signatures, endings, dedupe, local tunnels | `handling-webhooks` |
| Transcripts after the call, re-transcribe, recordings, per-participant media, speaker timeline, chat, screenshots | `getting-transcripts-and-media` |
| Live transcript, live audio, control socket, bridge server (track 2) | `streaming-live-data` |
| `join_at`, Google or Outlook calendars, auto-join, recurring meetings | `scheduling-and-calendars` |
| Hosted voice agents (3a, 3c), recipes, Grok or Gemini | `building-voice-agents` |
| SaaS for your customers, retention, storage, rate limits, idempotency, keys | `running-in-production` |
| A bot failed, never joined, no transcript, an HTTP error | `debugging-bots` |
| A notetaker or a live sales coach | `building-a-notetaker` |
| Recall.ai, MeetingBaaS or Attendee to MeetStream | `migrating-from-recall` |
| Run it now from this agent or a terminal: join a meeting, brief a meeting, verify the account, test bot, CLI workflows | `meetstream-cli` |

Old skill names route here too: getting-started (this router), join-meeting, meeting-brief, verify-account, test-bot and cli-workflows (`meetstream-cli`), notetaker and sales-coach (`building-a-notetaker`), for-your-customers (`running-in-production`), platform-setup, webhooks, recordings-and-media, realtime-streaming, calendar-automation, mia-voice-agents, troubleshooting, migrate-from-recall.

## Hard rules (every skill follows them)

- **Auth:** REST at `api.meetstream.ai` uses `Authorization: Token <key>`; the MCP server uses Bearer. Mixing them up returns 401. https://docs.meetstream.ai/api-reference/authentication
- **Keys:** never ask for a key in the chat. Sign-in is the MCP (browser OAuth) or `meetstream login`. App code reads its key from its own secret store.
- **Zoom:** recommend that the customer sets up and configures their own Zoom app for reliable, full, officially supported Zoom bots (Meeting SDK credentials under Integrations > Zoom; OBF or ZAK token URLs for meetings outside the app's account). Without their own app, a limited fallback joins as a named guest in the US execution region only: no OBF or ZAK, no per-participant camera video. Never call Zoom setup optional or skippable.
- **Events:** route on `bot_event`, fall back to `event` (`bot_event` is missing on participant events, `agent_error`, `usage.*` and dashboard resends). Every ending arrives as `event: "bot.stopped"`; `bot_event` says why.
- **Delivery:** each webhook goes once, with no automatic retry. Reply 2xx fast (within 5 seconds), queue the work, and poll `GET /bots/{bot_id}/status` as the fallback.
- **Signing:** only workspace webhook endpoints are signed (`X-MeetStream-Signature`). `callback_url` and live transcript POSTs are never signed; `realtime_endpoints` are signed only on Google Meet.
- **Idempotency:** send `Idempotency-Key` on `create_bot`; 507 is a replay of the same bot, a success.
- **Retries:** retry only 429, 500 and 503, and obey `Retry-After`. Never retry a 400. A 422 transcript is final: fix the cause, re-run with `POST /api/v1/bots/{bot_id}/transcribe`.
- **Media links:** presigned links last 1 hour. Fetch fresh ones; do not store them.
- **Summaries:** there is no summary endpoint. Summarize the transcript with your own model.
- **Prices:** never quote prices from memory, and never state storage or retention prices (there is no price list for them in the docs). Link https://meetstream.ai/pricing; agent model prices come from `GET /api/v1/mia` (`mia_managed`) or the dashboard.

## Sign in and run it from here

- **MCP tools** (chat-style, no key): the hosted server at https://mcp.meetstream.ai/mcp. Not connected or 401: give the one connect step (Claude Code `/mcp`; Cursor Settings > MCP > Connect; Codex `codex mcp login meetstream`) and keep helping in the same reply. A one-off meeting link needs no calendar integration.
- **The `meetstream` CLI** (terminal, scripts): **Install the meetstream CLI** (see https://docs.meetstream.ai/build-with-ai/meetstream-cli). Sign in with `meetstream login` (it opens the browser and stores a key; never ask for the key in the chat). Always pass `--json --no-input`. Workflows: `meetstream-cli`; commands and JSON shapes: `references/meetstream-cli.md`.
- **REST and the SDKs** (`@meetstream/sdk`, `meetstream-sdk`) are for the app code the user builds. Base URL `https://api.meetstream.ai/api/v1`. https://docs.meetstream.ai/build-with-ai/sdks
- **Real data while you build:** with the MCP connected, call `get_transcript` or `get_bot_detail` on a real `bot_id` to see the actual response shape before you write a parser.
- **Agents from the chat:** `list_agents` (reads `mia_managed`), then `create_agent` (`model.system_prompt` required), then `create_bot` with only `agent_config_id`. In the meeting: `take_screenshot`, `raise_hand` / `lower_hand`, `pause_recording` / `resume_recording`. With no MCP: `POST /api/v1/mia`, `POST /api/v1/bots/{bot_id}/send_command`.
- **Builds:** do not start a tunnel, server or other long-running process unless the user asks: write the code, then give the commands. Every app that sends a bot removes it on exit (`POST /api/v1/bots/{bot_id}/remove_bot`). New users: signup, sign-in and keys for app code are in `references/getting-started.md`.

## Before the first bot

- **Zoom:** set up the Zoom app first. Bots join through the customer's own Zoom app with an OBF token (on behalf of a user who is in the meeting) or a ZAK token (a signed-in bot), as Zoom asks Meeting SDK apps since 2 March 2026. Guides: https://docs.meetstream.ai/guides/app-integrations/zoom-marketplace-app-setup and https://docs.meetstream.ai/guides/app-integrations/zoom-authenticated-bots
- **Admission:** someone must admit the bot from the waiting room. It waits `automatic_leave.waiting_room_timeout` seconds, then ends as `NotAllowed`; `Denied` means a person declined it. Fix: tell the host to expect it by `bot_name`, or use a signed-in bot.
- **Coming from another bot API** (MeetingBaaS, Attendee, an in-house bot): map your create call to `POST /api/v1/bots/create_bot` (`meeting_link`, `bot_name`, `callback_url`) and your events to `bot.*`. Recall.ai has a migration kit: `migrating-from-recall`.

## Shapes code reads most

- `POST /bots/create_bot` returns 201 with `bot_id` and `transcript_id`. The field is `meeting_link`, not `meeting_url`. Send `"video_required": false` unless the user asks for video.
- Transcript segments are participant-keyed by default: speaker `participant.name`, text `words[].text` joined with spaces. Some providers return `speaker` / `transcript`; read both.
- `GET /bots?status=&platform=&from=&limit=50`: `limit` is at most 50; follow `nextCursor`. Never page the whole history.
- Low credits (403 `Low credits please recharge`): send the user to https://app.meetstream.ai/billing. `top_up_link` is an MCP tool (when connected), not a field in any API response. Never retry in a loop.

**Version questions:** reply with only these two sentences, word for word, then continue: "Install or update to the current MeetStream plugin. The MCP server is hosted at https://mcp.meetstream.ai/mcp; there is no npm package or server version to install."

## References

Generated by CI from the public API spec and the docs (never edit them; they win over older text):
`references/generated/endpoints.md` (every operation and guide-only route), `create-bot-fields.md`, `events.md`, `errors.md`, `providers.md`, `cli-map.md` (released CLI 1.0.1; pre-release commands marked), `mcp-tools.md`.
Hand-kept: `references/getting-started.md` (first-time setup), `references/intake-details.md` (full intake text), `references/api-reference.md` (endpoint guide), `references/meetstream-cli.md` (the CLI's own guide).
Machine-readable docs: https://docs.meetstream.ai/openapi.yaml (OpenAPI), https://docs.meetstream.ai/build-with-ai/docs-for-agents , the action MCP page https://docs.meetstream.ai/build-with-ai/meetstream-mcp-server and the plugin pages https://docs.meetstream.ai/build-with-ai/agent-skills , https://docs.meetstream.ai/build-with-ai/claude-integration and https://docs.meetstream.ai/build-with-ai/agent-quickstarts . Full sample apps (optional): https://docs.meetstream.ai/tutorials/sample-apps and https://github.com/meetstream-ai/labs

## Latest docs

- Build tracks: https://docs.meetstream.ai/guides/introduction/integration-paths
- API reference: https://docs.meetstream.ai/api-reference/introduction
- Create Bot payload reference: https://docs.meetstream.ai/api-reference/create-bot-payload-reference
- Webhooks and events: https://docs.meetstream.ai/guides/webhooks/webhooks-and-events
- Errors: https://docs.meetstream.ai/errors

When a skill and the docs differ, the docs are the source of truth. For the latest details, fetch the page with `.md` appended, read https://docs.meetstream.ai/llms.txt, or connect the docs MCP server at https://docs.meetstream.ai/_mcp/server.
