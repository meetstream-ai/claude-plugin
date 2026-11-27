# MeetStream Getting Started - First-Time Setup: Build tracks

> Part of [`getting-started.md`](getting-started.md), split so each file stays under 20 KB.

## Build tracks

1. **Recording bot (default):** a bot joins Zoom, Google Meet or Microsoft Teams, records
   and transcribes. 1a non-realtime transcription (post-call: recordings, transcripts,
   participants, chat and webhooks after the call); 1b real-time transcription (live data
   during the call).
2. **Bridge server (your own stack, local; only when the user asks for an agent):** the
   bot opens two WebSockets to the user's server (meeting audio in; audio, chat and images
   out), exposed from a laptop with a local tunnel (ngrok, cloudflared). Free local models
   (whisper.cpp, Parakeet, Ollama, Piper and others) or the harness's own model as the
   LLM, for the bot price only (`streaming-live-data`,
   https://docs.meetstream.ai/guides/websockets/bridge-server-architecture).
3. **Agents API infra (voice agents, API name MIA, hosted by MeetStream):** 3a
   MeetStream's own, default keys (recommended for "just host it"); 3b bring your own
   agent infra (LiveKit): COMING SOON; 3c bring your own keys; 3d your coding agent as the
   brain (`meetstream setup` once the relay is live): COMING SOON, with a prompt-injection risk. Never offer
   3b or 3d as working (`building-voice-agents`).

When the user asks what MeetStream offers or which API to use, name the tracks in order:
the Recording bot (the "Bot API") first, then for agents the Bridge server before the
hosted "Agents API" (voice agents). Name the track in your answer.
Docs: https://docs.meetstream.ai/guides/introduction/integration-paths

## Your first reply

1. If the MeetStream tools are missing or not signed in, give the one step to connect
   (see below) and keep going in the same reply.
2. Ask one question first: do you want results **after the meeting** (recording,
   transcript, notes) or something **live, during the call** (live transcript, live
   audio or video, chat, raise hand)? Do not lead with a voice agent.
3. Then follow the answer: after the meeting → `meetstream-cli` and `meetstream-cli`; live →
   `streaming-live-data`. If they will write code, the API key steps below apply.

## Before the first bot

Say these in the first-bot steps, before the user sends a bot:

- **Supported platforms:** Zoom, Google Meet and Microsoft Teams, plus WhatsApp calls in
  Beta (enabled per workspace; `setting-up-platforms`). Links from other services, such as Webex
  or Slack huddles, are rejected with a 400.
- **Set up your Zoom app (recommended for reliable, fully supported Zoom).** Zoom bots join
  through the customer's own Zoom app with an OBF token (on behalf of a user who is in the
  meeting) or a ZAK token (a signed-in bot),
  the way Zoom asks Meeting SDK apps to join since 2 March 2026. Before the first Zoom bot,
  create a Zoom Meeting SDK app, save its Client ID and Secret under Integrations > Zoom
  in the dashboard, and host the `zoom.obf_url` or `zoom.zak_url` token URL.
  Guides: https://docs.meetstream.ai/guides/app-integrations/zoom-marketplace-app-setup and
  https://docs.meetstream.ai/guides/app-integrations/zoom-authenticated-bots
- **Someone must admit the bot.** The bot joins like a guest and waits in the waiting room
  or lobby. The host (on Google Meet, the host or a co-host) admits it. It waits
  `automatic_leave.waiting_room_timeout` seconds (Zoom and Google Meet default 600, Teams
  1200), then ends as `NotAllowed`. `Denied` means a person declined it. Fix: tell the
  host to expect the bot by its `bot_name`, let guests in (Teams: "Who can bypass the
  lobby" set to Everyone), or use a signed-in bot (`setting-up-platforms`).

**Coming from another meeting-bot API** (MeetingBaaS, Attendee, an in-house bot): map your
create call to `POST /api/v1/bots/create_bot` (`meeting_link`, `bot_name`,
`callback_url`), your status handling to the `bot.*` webhook events, and your transcript
fetch to `get_transcript`. The automated migration kit covers Recall.ai only
(`migrating-from-recall`). For data location questions, contact support
(https://docs.meetstream.ai/guides/help/support).

**Building for your own customers** (bots in your customers' meetings, per-customer
data): `running-in-production`.

**When the MCP tools help, even in a build:** app code uses REST, but the MCP tools show
real data from the user's account. Before you write a parser, call `get_transcript` (or
`get_bot_detail`) on a real `bot_id` to see the actual response shape; this is how test
builds found the participant-keyed transcript format.

**Finish from this agent, with no dashboard trip:** with the MCP connected, the user can do
the whole build from here. Voice agents: `list_agents` (reads `mia_managed`, the inbuilt
keys on for the account), then `create_agent` (`model.system_prompt` is required), then
`create_bot` with `agent_config_id` (`check_local_agent` is for the coming-soon track 3d only).
In the meeting: `take_screenshot`, `raise_hand` / `lower_hand`, `pause_recording` /
`resume_recording`. Calendars: `list_calendar_connections`, `disconnect_calendar`. Provider
keys stay in the dashboard (or use inbuilt keys in pipeline mode). Never ask for a key in
the chat. With no MCP, give the REST call
(details in `building-voice-agents` and `meetstream`).

## Three ways in: pick by what the user wants

- **Use MeetStream from this agent** (send bots, get notes): no key needed. This plugin includes the hosted MeetStream MCP server. Sign in once: Claude Code `/mcp` → `meetstream` → **Authenticate**; Codex `codex mcp login meetstream`; Cursor Settings → MCP → **Connect**. The browser opens app.meetstream.ai; the user signs in or signs up and clicks **Allow**. Check with the `list_bots` tool, then ask the routing question below (after the meeting or live?) and hand over to `meetstream-cli` or `streaming-live-data`. New accounts start with $5 of credit.
- **Run commands from a terminal or this agent's shell** (no MCP, scripts, `listen`, `setup`): the `meetstream` CLI. `meetstream login` signs in through the browser and stores a key, so nothing is pasted in the chat; then `meetstream doctor --json --no-input` checks the key.
  **Install the CLI** (when this agent runs commands for the user): `npx -y @meetstream/cli <command>` works with no install; or `npm install -g @meetstream/cli`, `pipx install meetstream-cli`, `brew install meetstream-ai/tap/meetstream`. Sign in with `meetstream login` (it opens the browser and stores a key; never ask for the key in the chat) or set `MEETSTREAM_API_KEY`. Always pass `--json --no-input`. Exit codes: 0 ok, 1 API error, 2 usage or not signed in, 3 not ready yet, 4 transcript failed. JSON shapes: `skills/meetstream/references/meetstream-cli.md`. Every CLI workflow step by step: skill `meetstream-cli`.
- **Build an app on the API** (code, servers, CI): the code needs an API key. Follow the steps below.

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
3. **Agent tracks, in this order** (details in `streaming-live-data` and
   `building-voice-agents`). If the user does not say how, ask one question: run your own stack
   (track 2) or let MeetStream host it (track 3a/3c)? If they want no infrastructure work
   ("just host it"), track 3a is the answer, with 3c as the fallback.
   - Track 2, **Bridge server**: the bot opens `live_audio_required.websocket_url` and
     `socket_connection_url.websocket_url` to the user's server (a local tunnel on a
     laptop), which runs any speech-to-text, LLM and TTS: free local models or the
     harness's own model. The bot price only.
   - Track 3, **Hosted Agents API (MIA)**: bot price + $0.25 per hour agent infrastructure
     + the models picked. 3a MeetStream's own, default keys (`"key_source": "meetstream"`).
     Inbuilt keys work in pipeline mode only: Deepgram (speech-to-text) and OpenAI (LLM and voice). Realtime mode runs on OpenAI and needs your own OpenAI key. Any other provider: bring your own key. Read `mia_managed` from `list_agents` (MCP) or `GET /api/v1/mia` and use only what it lists; create the agent with `create_agent` (MCP) or `POST /api/v1/mia`. If the API says MeetStream-managed keys are not available, inbuilt
     keys are not on for the account yet: go on with 3c, the user's own provider keys
     (the provider bills model usage). Never retry in a loop. The hosted bot takes only
     `agent_config_id`, never the bridge sockets.
   - **Coming soon, never offered as working:** 3b bring your own agent infra (LiveKit,
     coming soon) and 3d your coding agent as the brain (Claude Code, Codex and others,
     through `meetstream setup` once the relay is live). Give no setup steps; for 3d, warn that meeting speech will reach an agent with
     access to the user's computer (prompt injection). Offer track 2 or 3a/3c instead.
4. **Version questions:** reply with only these two sentences, word for word, then
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
  or the CLI command (`meetstream join <url> --json --no-input`, run with
  `npx -y @meetstream/cli` if it is not installed).
- The one step is the MeetStream MCP sign-in, nothing else. A one-off meeting link needs
  no calendar integration (calendars are only for auto-joining every meeting).

## When to invoke this skill

**Always** invoke this skill first if any of these are true:

1. The user explicitly says they're new to MeetStream / don't have an account
2. The MeetStream MCP tools are not connected and `meetstream auth status` is not signed in
3. A different MeetStream skill (notetaker, building-a-notetaker, scheduling-and-calendars, meetstream-cli, meetstream-cli) was invoked and the API key check failed
4. A key check answers 401 or 403

**Skip** if:
- A MeetStream MCP tool (for example `list_bots`) already answers, or `meetstream auth status` shows a valid key
- The user explicitly says "I already have my key, just build X"

## Step 1: Check the connection

Nothing is pasted at any step. Check in this order:

1. **MeetStream MCP connected?** Call the `list_bots` tool. A list (even an empty one) means the user is signed in: go to Step 6.
2. **CLI signed in?**

   ```bash
   npx -y @meetstream/cli auth status --json --no-input   # "signed_in": true and "valid": true = skip onboarding
   ```

If neither works, continue to Step 2.

## Step 2: Sign up for a MeetStream account (if needed)

Tell the user:

```
You'll need a MeetStream account to use this. Free tier includes credits to
get you started - no credit card needed up front.

👉 Open https://app.meetstream.ai in your browser

  1. Sign up with your work email (Google sign-in works too)
  2. Confirm your email if prompted
  3. You'll land on the dashboard

Reply "done" when you're signed in and I'll walk you through the API key.
```

Wait for the user to confirm before continuing.

## Step 3: Sign in (the key is created for you)

The user signs in once in the browser; MeetStream creates the key. Never ask for a key in the chat.

- **MCP (chat apps and this agent):** Claude Code `/mcp` → `meetstream` → **Authenticate**; Codex `codex mcp login meetstream`; Cursor Settings → MCP → **Connect**. The browser opens app.meetstream.ai; the user clicks **Allow**.
- **CLI (terminal, scripts, local apps):** run

  ```bash
  npx -y @meetstream/cli login --json   # opens the browser; the CLI stores a named key (mode 0600); --no-browser prints the link
  ```

## Step 4: Keys for app code

The user's own app code is the only thing that needs the key, and the agent never reads, prints or writes it.

- **On the user's laptop:** apps made with `meetstream init` call MeetStream through `meetstream api`, with the CLI sign-in, so no key goes into project files (CLI 1.1, coming with the next CLI release). Until then, or for other apps, the user creates a key at https://app.meetstream.ai/api-keys and adds it to the app's `.env` file (listed in `.gitignore`) themselves.
- **On a server or in CI:** the key goes in the server's secret store (AWS Secrets Manager, Doppler, Vault, the CI secret settings). With CLI 1.1, `meetstream env --with-key` writes the key and its API URL into a server `.env`.

> **Never commit a key to git.** If a key leaks, rotate it at https://app.meetstream.ai/api-keys.

## Step 5: Validate the sign-in

Call `list_bots` through the MeetStream MCP, or run `meetstream auth status --json --no-input` (`"valid": true`). For app code on a server, one request from the app checks its key: `GET https://api.meetstream.ai/api/v1/bots` with the header `Authorization: Token <key>`. Expected: `200`.

If `401` or `403`: sign in again (Step 3) or create a new key for the server.
If anything else: network issue, ask the user to retry.

## Step 6: Verify provider configuration (optional but recommended)

After a valid key, suggest:

```
✅ Your API key works.

One more recommended step: verify which transcription providers are configured
on your account. This catches "provider missing" errors before you build anything.

Run the `meetstream-cli` skill, or I can run it now - want me to?
```

If yes, hand off to the `meetstream-cli` skill.

## Step 7: Suggest next action

Based on what the user originally wanted, route them:

| User originally said | Hand off to |
|---|---|
| "build a notetaker" | `building-a-notetaker` skill |
| "bots in our customers' meetings", "per customer" | `running-in-production` skill |
| "an agent that talks", "standup bot", "AI interviewer" | `building-voice-agents` skill (recipes by job) |
| "build a sales coach" | `building-a-notetaker` skill |
| "auto-record my calendar" | `scheduling-and-calendars` skill |
| "test a bot" | `meetstream-cli` skill |
| "I just want to look around" | Suggest reading the `meetstream` core skill |

If they didn't originally have a goal, suggest the most common starting point:

```
You're all set. Most users start with one of these:

  🎙️  AI Meeting Notetaker         → "build me an AI notetaker"
  🎯  Real-Time AI Sales Coach     → "build a real-time sales coach"
  📅  Calendar Auto-Recording      → "auto-record every meeting on my calendar"
  🧪  Just send a test bot         → "send a test bot to https://meet.google.com/..."

Which one?
```

## Workspaces, environments and the API Playground

- **Workspaces.** Each account owns one workspace with its own API keys (`ms_...`), bots, webhook
  endpoints and usage; a key cannot reach another workspace's bots. Use one workspace per
  environment (staging, production), each with its own keys and webhook endpoints, and
  `custom_attributes` for finer routing inside one. Roles: Owner (all, including billing), Admin
  (keys, integrations, webhooks, members), Editor (viewer plus the Playground), Viewer (read).
  https://docs.meetstream.ai/guides/get-started/workspaces
- **API Playground** (https://app.meetstream.ai/api-playground): a no-code builder for the whole
  `create_bot` request in steps (core, identity, streams, record, transcribe, callback, timeouts,
  schedule, attributes, agents). The Code toggle shows the exact JSON to copy into the app. It sends
  real, billed bots. https://docs.meetstream.ai/guides/get-started/api-playground
- **Docs home:** https://docs.meetstream.ai/welcome (quickstart, how bots work, build tracks).
