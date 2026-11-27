---
name: building-voice-agents
description: >
  Agents that talk in a meeting ("voice agent", "bot that talks", "MIA").
  Stack not said: ask own stack (track 2) or hosted (3a/3c)? Track 2 bridge
  server: the bot opens live_audio_required + socket_connection_url to your
  server (local tunnel such as ngrok); free local whisper.cpp/Parakeet STT,
  Ollama/LM Studio LLM or your harness's own model, Piper/Kokoro TTS; bot
  price only. Track 3 Agents API (MIA, hosted), bot + $0.25 per hour + models:
  3a MeetStream's default keys (key_source "meetstream"; pipeline mode only:
  Deepgram STT, OpenAI LLM and voice), recommended for "just host it"; if a
  section is refused, use 3c, never retry. 3b own agent infra (LiveKit, COMING
  SOON). 3c bring your own keys. 3d your coding agent as the brain (Claude
  Code, Codex via meetstream setup) COMING SOON: no setup steps; warn of prompt
  injection (meeting speech reaches an agent with computer access). Hosted
  bot: only agent_config_id. Grok: xAI. MCP: list_agents, then create_agent
  (system_prompt required). Was mia-voice-agents.
---

# Agents in meetings (voice agents; Agents API, API name MIA)

A voice agent is an AI participant on a MeetStream bot: it hears the meeting and answers
by voice, in the chat, or with silent tool calls. Say "voice agent" or "agent in the
meeting" to users, and give "MIA" once as the API name of the hosted Agents API (track 3).

For recordings, transcripts and live data with no agent, use the Recording bot (track 1:
`meetstream-cli`, `meetstream-cli`, `streaming-live-data`). Bring agents in only when the
user asks for an agent, a voice agent or a bot that talks.

## With the MeetStream MCP connected: create and check agents from here

When the `meetstream` MCP tools are connected, create, check and change agents with them,
so the user never leaves the chat. With no MCP, give the REST call in each step below.

| Step | MCP tool | REST (no MCP) |
|---|---|---|
| 1. Read the account's agents and inbuilt keys first | `list_agents` (agent configs and `mia_managed`: `enabled`, then the providers and models per section; no prices) | `GET /api/v1/mia` |
| 2. Create the agent | `create_agent` (`agent_name`, `mode`, `model` with `system_prompt`; in pipeline mode also `transcriber` and `voice`) | `POST /api/v1/mia` |
| 4. Send it to the meeting | `create_bot` with only `meeting_link` and `agent_config_id` | `POST /api/v1/bots/create_bot` |
| Read one, change one | `get_agent`; `update_agent` (each section you send replaces that section; a `mode` change needs the full config) | `GET /api/v1/mia?agent_config_id=<id>`; `PUT /api/v1/mia` |
| Delete one | `delete_agent` with `confirm: true`, only after the user says yes | `DELETE /api/v1/mia?agent_config_id=<id>` |
| See what the bot sees | `take_screenshot` (`bot_id`; Google Meet and Teams), then `get_media_urls` with `kind: "screenshots"` | `POST /api/v1/bots/{bot_id}/send_command` `{"command": "screenshot"}`, then `GET /api/v1/bots/{bot_id}/screenshots` |
| Change a running agent | `update_live_agent` | `POST /api/v1/bots/{bot_id}/update_mia` |

**From a terminal, with the `meetstream` CLI** (no MCP): `meetstream mia list`, `mia get
<id>`, `mia apply -f agent.json` (creates, or updates when the file has `agent_config_id`;
`--dry-run` prints the body), `mia delete <id>` (only after the user says yes), then
`meetstream join <url> --agent-config <id>`; each with `--json --no-input`. `meetstream
setup --mode hosted` (3a) or `--mode byok` (3c) creates the agent in one step.
No install needed: `npx -y @meetstream/cli <command>`. Sign-in, exit codes, JSON: `meetstream-cli` (pass `--json --no-input`; never ask for the key).

Rules for all paths:

- **`model.system_prompt` is required** for every agent except `local_agent`. Without it
  the API answers `400` `Missing model.system_prompt.` Write a short prompt from what the
  user wants the agent to do.
- **`voice.voice_id` is required in pipeline mode** (`400` `Missing voice.voice_id.`), even
  on an inbuilt key: for example `nova` for OpenAI, or an ElevenLabs voice id from the
  dashboard agent editor's voice list.
- **Keys never go in the chat.** Prefer inbuilt keys (`"key_source": "meetstream"`, pipeline
  mode, only what `mia_managed` lists) or keys the user saved in the dashboard under
  Configure > Integrations. Never ask the user to paste a provider key; the tools never
  return key values. `create_agent` refuses `key_source: "meetstream"` in realtime mode:
  use pipeline mode, or realtime with the user's own OpenAI key saved in the dashboard.
- **Never probe undocumented or admin endpoints.** Use only the tools and REST calls in this
  table.
- If inbuilt keys are not on (`enabled: false`, or the API says MeetStream-managed keys
  are not available), say so and continue with the user's own keys (3c). Never retry the
  same request in a loop.

## Pick the track first

If the user wants an agent but does not say how, ask one question: **run your own stack**
(track 2, a bridge server with any models, including free local ones) **or let MeetStream
host it** (track 3a or 3c, the Agents API)? If they want no infrastructure work ("just host
it"), track 3a is the answer, with 3c as the fallback. In every answer, table or
comparison, list the bridge server (track 2) before the hosted Agents API (track 3). Name
the track in your answer.

| Track | What the user does | Price per meeting hour |
|---|---|---|
| 2. Bridge server (your own stack, local) | Runs a server that the bot connects to with two WebSockets: live audio in (`live_audio_required.websocket_url`) and the control socket (`socket_connection_url.websocket_url`) to send audio, chat, images and interrupts back. A local tunnel on a laptop. Any speech-to-text, LLM and voice: free local models, or the harness's own model as the LLM. | Bot price only. MeetStream charges no agent infrastructure and no model tokens. |
| 3a. Agents API, MeetStream's own, default keys (recommended for "just host it") | MeetStream hosts the agent with `"key_source": "meetstream"`. Inbuilt keys work in pipeline mode only: Deepgram (speech-to-text) and OpenAI (LLM and voice). Realtime mode runs on OpenAI and needs your own OpenAI key. Any other provider: bring your own key. | Bot price + $0.25 agent infrastructure + the models picked. |
| 3b. Bring your own agent infra (LiveKit) | COMING SOON. Not available yet; no setup steps. | - |
| 3c. Agents API, bring your own keys | MeetStream hosts the agent with the user's own provider keys (OpenAI, Anthropic, Deepgram, ElevenLabs and the others in the docs). | Bot price + $0.25 agent infrastructure; the provider bills model usage. |
| 3d. Your coding agent as the brain (`meetstream setup` and `meetstream agent serve` over the MeetStream relay) | COMING SOON. Not available yet; no setup steps. | - |

Bot price: $0.35 per recording hour ($0.25 at volume). The MeetStream transcription
add-on is $0.10 per hour and is waived with your own provider key. Give the price as these
parts; do not add them into a total or give any other price: for exact model rates, send
the user to the dashboard agent editor or https://docs.meetstream.ai/guides/mia/pricing-and-keys.

Tracks 2 and 3 are separate bots: a bridge bot has the two sockets and no
`agent_config_id`; a hosted agent bot has only `agent_config_id`.

## Track 2: bridge server (your own stack, local)

The bot connects out to your server; you host both endpoints (`wss://`, publicly
reachable). On a laptop, expose the server with a local tunnel (ngrok or cloudflared);
give the tunnel command for the user to run, and do not start it unless the user asks.

```bash
curl -X POST https://api.meetstream.ai/api/v1/bots/create_bot \
  -H "Authorization: Token $MEETSTREAM_API_KEY" -H "Content-Type: application/json" \
  -d '{"meeting_link": "https://meet.google.com/abc-defg-hij", "bot_name": "Assistant",
       "live_audio_required": {"websocket_url": "wss://your-bridge.example/audio"},
       "socket_connection_url": {"websocket_url": "wss://your-bridge.example/control"}}'
```

The same bot from the `meetstream` CLI: `meetstream join <url> -n "Assistant" --live-audio-ws
wss://your-bridge.example/audio --socket-ws wss://your-bridge.example/control --json --no-input`.

Models for the bridge, free to run locally; check each model's license before commercial use:

- Speech-to-text: whisper.cpp or faster-whisper (Whisper models), NVIDIA Parakeet
  (parakeet-mlx on Apple silicon), Vosk, Moonshine.
- LLM: a local model through Ollama, LM Studio or llama.cpp (Llama, Qwen, Gemma,
  Mistral), or the model of the harness you already use (for example Claude behind
  Claude Code, called from your bridge).
- Text-to-speech: Piper, Kokoro, Chatterbox, macOS `say`.

Your bridge decodes the audio frames, runs your speech-to-text, LLM and TTS, and sends
the reply back with `sendaudio` (plus `sendmsg`, `sendimg`, `interrupt` and
`resume_audio`) on the control socket. The full recipe (frames, commands, barge-in) is in
`streaming-live-data`. Starter: the MeetStream Bridge
(https://github.com/meetstream-ai/meetstream-agent), FastAPI with OpenAI Realtime by
default; swap in local models. Docs: https://docs.meetstream.ai/guides/websockets/bridge-server-architecture

## Coming soon: 3b (LiveKit) and 3d (your coding agent)

Not in production. Say they are coming soon, give no setup steps, and offer track 2 or
3a/3c instead. When you describe 3d (the user's coding agent as the brain), give the
prompt-injection warning in `references/agent-recipes.md`. For "Claude Code or Codex as the
brain" today: track 2 with the harness's model as the bridge LLM, or 3c with
`"provider": "anthropic"` and the user's own key.

## Track 3: Agents API infra (MIA, hosted)

MeetStream hosts the agent, so the user hosts nothing. With the MCP connected: `list_agents`,
then `create_agent`, then `create_bot` with only `agent_config_id`. From a terminal:
`meetstream setup --mode hosted --name "Meeting assistant" --json --no-input` (3a; `--mode
byok` for 3c, with the keys added in the dashboard; setup never asks for keys) returns the
`agent_config_id` and the price per hour from the API (report it as shown), then
`meetstream join <url> --agent-config <id> --json --no-input`. In app code, or with no MCP
and no CLI: create the config with `POST /api/v1/mia`, then send a bot with only `agent_config_id`.

### Fastest path (track 3a)

0. Check what inbuilt keys your account has: `list_agents` (MCP) or `GET /api/v1/mia`, and read `mia_managed`
   (`enabled`, then `sections.transcriber`, `sections.model`, `sections.voice` with their
   providers and models). Use only those with `"key_source": "meetstream"`. If
   `enabled` is false or a section is missing, use your own keys (3c) for it. The response
   also carries per-hour prices (`rates`, and a price per model): quote prices only from
   it, never from memory.
1. Create the agent (3a, default keys; swap in the providers `mia_managed` lists for your
   account). With the MCP, pass the same fields to `create_agent`:
   ```bash
   curl -X POST https://api.meetstream.ai/api/v1/mia \
     -H "Authorization: Token $MEETSTREAM_API_KEY" -H "Content-Type: application/json" \
     -d '{"agent_name": "Meeting assistant", "mode": "pipeline",
          "transcriber": {"provider": "deepgram", "model": "nova-3", "language": "en", "key_source": "meetstream"},
          "model": {"provider": "openai", "model": "gpt-4o-mini", "key_source": "meetstream",
                    "system_prompt": "You are a concise meeting assistant."},
          "voice": {"provider": "openai", "model": "tts-1", "voice_id": "nova", "key_source": "meetstream"},
          "wake_word": {"enabled": false}}'
   ```
   Pipeline agents start with a wake word on (`"hey assistant"`, `"hello bot"`), so an
   agent without `"wake_word": {"enabled": false}` greets and then ignores questions until
   someone says the wake word. Keep the wake word only on purpose (`references/agent-recipes.md`).
   Set `transcriber.language` to the meeting's language (`en`, `es`, `ru` and so on), or
   `multi` for automatic detection. For a job (name-addressed assistant, standup,
   interviewer, role-play, demo agent), add the fields from the recipes in `references/agent-recipes.md`.
2. Send a bot with only the `agent_config_id` from the response:
   ```bash
   curl -X POST https://api.meetstream.ai/api/v1/bots/create_bot \
     -H "Authorization: Token $MEETSTREAM_API_KEY" -H "Content-Type: application/json" \
     -d '{"meeting_link": "https://meet.google.com/abc-defg-hij", "bot_name": "Assistant", "agent_config_id": "<id>"}'
   ```
3. Join the meeting and talk to it. `remove_bot` when done (`POST /api/v1/bots/{bot_id}/remove_bot`;
   an app calls it on Ctrl-C or exit). Commands such as `update_mia`, chat and
   `send_command` need the bot `InMeeting` first; before that they return 409 or 503, so
   wait for `bot.inmeeting` (or poll the status) and retry a 503 a few times with a pause.

The same two calls from the SDKs (`@meetstream/sdk`, `meetstream-sdk`): `references/agent-recipes.md`.

### 3a. MeetStream's own, default keys (recommended for "just host it")

Inbuilt keys are the providers MeetStream runs in its own infrastructure.
Inbuilt keys work in pipeline mode only: Deepgram (speech-to-text) and OpenAI (LLM and voice). Realtime mode runs on OpenAI and needs your own OpenAI key. Any other provider: bring your own key.
(3c covers your own keys.)

Set `"key_source": "meetstream"` on each pipeline section that uses an inbuilt key
(`transcriber`, `model`, `voice`), and send no `api_key` in that section.
Sections can mix: one section on an inbuilt key, another on the user's own key.

**Your account's list is the source of truth.** Accounts can show a different set of
inbuilt providers and models. Read `mia_managed` from `GET /api/v1/mia` (`enabled` and
`sections`) and use only the providers and models listed there with
`"key_source": "meetstream"`. If the API refuses a section, the message lists what it
accepts: switch that section to a listed provider or to your own key. Never state the
catalog prices.

**If inbuilt keys are not on for the account.** The API answers `400`
`MeetStream-managed keys are not available for <section>. Use your own key.` (or, on
`create_bot` with a saved agent, `MeetStream-managed keys are turned off. Edit the agent
to use your own keys for: ...`). Tell the user that inbuilt keys are not on for their
account yet, then go on with 3c: add the provider key in the dashboard under
Configure > Integrations (Models, Voice, Transcription), remove `key_source` (or set it to
`"user"`) in that section, and save again. Never retry the same request in a loop: it
gets the same answer.

Other `400`s: `MeetStream-managed keys are available only in pipeline mode.` (realtime
mode needs your own OpenAI key; or switch to pipeline mode);
an `api_key` in a section with
`key_source: "meetstream"`; a provider or model with no inbuilt key (the message lists the
ones you can use).

### 3c. Bring your own keys

No `key_source` (or `"key_source": "user"`). The user saves each provider key in the
dashboard under Configure > Integrations; the agent config holds provider names and
settings, never the keys. Works in pipeline and realtime mode. A missing key returns
`400` `API key not configured for: ...`.

## The one rule people get wrong

To attach an agent to a bot you pass **only `agent_config_id`**.

```json
{ "meeting_link": "https://...", "bot_name": "Assistant", "agent_config_id": "<id>" }
```

Do **not** also pass `socket_connection_url` or `live_audio_required`. Those are for the
bridge server (track 2), where you host the audio yourself on a separate bot, and adding
them to a hosted agent bot is a common cause of a silent agent. MeetStream hosts the MIA
bridge.

## Two modes

| Mode | What it is | Pick it when |
|---|---|---|
| `pipeline` | Separate STT -> LLM -> TTS layers, each configurable | You want to choose each provider, use a wake word, or tune interruptions |
| `realtime` | One speech-to-speech model (e.g. OpenAI realtime) | You want the lowest latency and fewer moving parts |

Wake word is a pipeline feature. If the user wants "only answer when addressed",
that decides the mode for you.

## Creating an agent

`POST /api/v1/mia` returns `agent_config_id`. The config surface:

```json
{
  "agent_name": "Meeting Assistant",
  "mode": "pipeline",
  "model":       { "provider": "openai", "model": "gpt-4.1", "system_prompt": "...",
                   "first_message": "...", "temperature": 0.7 },
  "voice":       { "provider": "openai", "voice_id": "nova", "speed": 1.0 },
  "transcriber": { "provider": "deepgram", "model": "nova-3", "language": "en",
                   "boostwords": ["Acme", "MeetStream"] },
  "agent":       { "response_modality": "voice", "tools": [], "mcp_servers": [],
                   "enable_interruptions": true, "user_away_timeout": 30 },
  "wake_word":   { "enabled": true, "words": ["hey acme"], "timeout": 30 },
  "audio":       { "sample_rate": 48000, "num_channels": 1 }
}
```

`voice`, `transcriber` and `wake_word` are pipeline-only. In realtime mode the voice
lives inside `model`.

MCP tools for the same operations: `list_agents`, `get_agent`, `update_agent`,
`delete_agent` (`confirm: true`). REST: `GET /mia` (list, or one via `?agent_config_id=`),
`PUT /mia` (update, body includes `agent_config_id`),
`DELETE /mia?agent_config_id=...`. `GET` masks secrets (`****` + last four characters);
sending the mask back on `PUT` keeps the stored value.

### Changing a running agent

`update_live_agent` (MCP) or `POST /api/v1/bots/{bot_id}/update_mia` (REST) with at least one of `agent_config_params`
(merged), `system_prompt` (replaces the instructions), `wake_word_enabled`, `wake_words`.
A plain 200 `{"status": "accepted"}` means accepted for delivery, not applied. Add
`"wait_for_ack": true` to get the agent's answer: `status` is `applied`,
`partially_applied`, `failed` (with `errors: [{field, reason}]`) or `accepted` with
`ack_timeout: true` (the update may still apply). A non-boolean `wait_for_ack` returns 400.

To have the agent wait its turn, raise the bot's hand first:
`POST /api/v1/bots/{bot_id}/send_command` `{"command": "raise_hand"}`, then `lower_hand`
after it speaks (see `meetstream-cli`).

## Tools the agent can call (custom functions)

`agent.custom_functions` registers your HTTPS endpoints as tools. During the call the agent
sends `POST {"name", "bot": {"bot_id", "dynamic_vars", "agent_id"?}, "args": {...}}` with
header `X-Bot-ID` (always) and `X-Agent-ID` (when available). Read the arguments from
`args` and the meeting from `X-Bot-ID` or `bot.bot_id`. There is no signature: put a secret
in the function's `headers` and check it. Request body, every field and the response rules:
`references/custom-functions.md`.

Recipes by job (assistant, standup, interviewer, role-play, demo agent, other languages),
Grok and Gemini agents, Claude as the LLM, wake words and 3d details:
`references/agent-recipes.md`.

## More configuration

Agent options (API v1.10.0), settings people miss and how to test an agent: [`references/agent-config-details.md`](references/agent-config-details.md).
Every config field, custom functions, MCP tools and screen tools: https://docs.meetstream.ai/guides/mia/mia-custom-configurations . What the Agents API is: https://docs.meetstream.ai/guides/mia/what-is-mia .

## Latest docs

- Bridge server (track 2): https://docs.meetstream.ai/guides/websockets/bridge-server-architecture
- MIA API guide (config fields, custom functions, `update_mia`): https://docs.meetstream.ai/guides/mia/mia-api-guide
- Voice agent pricing and keys: https://docs.meetstream.ai/guides/mia/pricing-and-keys

For the latest details, fetch the page with `.md` appended, read https://docs.meetstream.ai/llms.txt, or connect the docs MCP server at https://docs.meetstream.ai/_mcp/server.
