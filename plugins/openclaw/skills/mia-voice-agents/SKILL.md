---
name: mia-voice-agents
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
  (system_prompt required).
---

# Agents in meetings (voice agents; Agents API, API name MIA)

A voice agent is an AI participant on a MeetStream bot: it hears the meeting and answers
by voice, in the chat, or with silent tool calls. Say "voice agent" or "agent in the
meeting" to users, and give "MIA" once as the API name of the hosted Agents API (track 3).

For recordings, transcripts and live data with no agent, use the Recording bot (track 1:
`join-meeting`, `meeting-brief`, `realtime-streaming`). Bring agents in only when the
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
**Install the CLI** (when this agent runs commands for the user): `npx -y @meetstream/cli <command>` works with no install; or `npm install -g @meetstream/cli`, `pipx install meetstream-cli`, `brew install meetstream-ai/tap/meetstream`. Sign in with `meetstream login` (it opens the browser and stores a key; never ask for the key in the chat) or set `MEETSTREAM_API_KEY`. Always pass `--json --no-input`. Exit codes: 0 ok, 1 API error, 2 usage or not signed in, 3 not ready yet, 4 transcript failed. JSON shapes: `skills/meetstream/references/meetstream-cli.md`.

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
       "live_audio_required": {"websocket_url": "wss://your-bridge.example/bridge/audio"},
       "socket_connection_url": {"websocket_url": "wss://your-bridge.example/bridge"}}'
```

The same bot from the `meetstream` CLI: `meetstream join <url> -n "Assistant" --live-audio-ws
wss://your-bridge.example/bridge/audio --socket-ws wss://your-bridge.example/bridge --json --no-input`.

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
`realtime-streaming`. Starter: the MeetStream Bridge
(https://github.com/meetstream-ai/meetstream-agent), FastAPI with OpenAI Realtime by
default; swap in local models. Docs: https://docs.meetstream.ai/guides/websockets/bridge-server-architecture

## Coming soon: 3b (LiveKit) and 3d (your coding agent)

These tracks are not in production. Say they are coming soon. Give no setup steps and no
"do this now" steps for them, and never route a user to them as a working option. Offer
track 2 or track 3a/3c instead.

- **3b. Bring your own agent infra (LiveKit): COMING SOON.** MeetStream's Agents API will
  run with the user's own agent infrastructure. Today, put the user's own agent
  code behind a bridge server (track 2), or use 3c with their own keys.
- **3d. Your coding agent as the brain: COMING SOON.** The user's own agent CLI (Claude
  Code, Codex, Hermes, Copilot, OpenClaw and others) will be the voice agent's brain through
  `meetstream setup` and `meetstream agent serve` over the MeetStream relay (no tunnel).
  The relay is not in production yet. When you describe 3d, give this warning:

  > **Warning:** what people say and type in the meeting will reach an agent that has
  > access to your computer and your terminal. Someone in the call can try to make it run
  > commands or read files (prompt injection). The computer, the agent and the bridge must
  > stay on for the whole call, at the lowest access level.

  For "use Claude Code (or Codex) as the brain" today: track 2 with the harness's own
  model as the bridge LLM, or track 3a/3c (for example `"provider": "anthropic"` with the
  user's own Anthropic key, 3c). The `check_local_agent` MCP tool is for 3d only.

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
   `enabled` is false or a section is missing, use your own keys (3c) for it. Do not quote
   any prices from that response; the dashboard agent editor shows the rate.
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
   someone says the wake word. Keep the wake word only on purpose (recipes below).
   Set `transcriber.language` to the meeting's language (`en`, `es`, `ru` and so on), or
   `multi` for automatic detection. For a job (name-addressed assistant, standup,
   interviewer, role-play, demo agent), add the fields from "Recipes by job" below.
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

Node (`npm install @meetstream/sdk`):
```ts
import { MeetStream } from '@meetstream/sdk';
const ms = new MeetStream(); // reads MEETSTREAM_API_KEY
const agent = await ms.mia.create({ agent_name: 'Meeting assistant', mode: 'pipeline', /* transcriber, model, voice as above */ });
await ms.bots.create({ meeting_link, agent_config_id: agent.agent_config_id });
```
Python (`pip install meetstream-sdk`):
```python
from meetstream import MeetStream
ms = MeetStream()  # reads MEETSTREAM_API_KEY
agent = ms.mia.create({"agent_name": "Meeting assistant", "mode": "pipeline"})  # plus transcriber, model, voice as above
ms.bots.create({"meeting_link": meeting_link, "agent_config_id": agent["agent_config_id"]})
```

Optional references: the MIA templates in "Tutorials and Sample Apps"
(https://docs.meetstream.ai/tutorials/sample-apps) and the labs repo
(https://github.com/meetstream-ai/labs).

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

## Hosted agents on Grok (xAI) or Gemini (Google)

"Make Grok join my call" and "put Gemini in the meeting" are hosted voice agents (track 3c)
with the `xai` or `google` provider, or the model behind your own bridge server (track 2).
Grok is not a local agent. xAI and Google are not inbuilt keys: save the provider key in
the dashboard under Configure > Integrations and send no `key_source` in that section.

Realtime mode (one speech-to-speech model, lowest latency, answers every turn):

```json
{ "agent_name": "Grok in the meeting", "mode": "realtime",
  "model": { "provider": "xai", "voice": "Ara",
             "system_prompt": "You are Grok, a helpful participant. Answer briefly and out loud." } }
```

```json
{ "agent_name": "Gemini in the meeting", "mode": "realtime",
  "model": { "provider": "google", "model": "gemini-2.5-flash-native-audio-preview-12-2025",
             "voice": "Puck", "proactivity": true,
             "system_prompt": "You are a helpful participant. Answer only questions meant for you." } }
```

- xAI realtime: do not send `model`; MeetStream selects the xAI realtime model. Voices
  include `Ara` (default), `Eve`, `Leo`, `Rex`, `Sal`.
- Google realtime: `proactivity: true` lets the model skip input that is not for it.
- Wake words and `speak_only_when_asked` are pipeline-only. To have Grok answer only when
  someone says its name, use pipeline mode with xAI parts:
  `"model": {"provider": "xai", "model": "grok-3", ...}`, `"transcriber": {"provider": "xai"}`
  (or Deepgram), `"voice": {"provider": "xai", "voice_id": "ara"}`, plus
  `"agent": {"speak_only_when_asked": true}`. Google works the same way as a pipeline LLM
  (`"model": {"provider": "google", ...}`).
- Send the bot with only `agent_config_id`. On Zoom, the bot joins through your Zoom app
  with an OBF or ZAK token (`platform-setup`).

## Recipes by job

Each recipe is the job-specific part of an agent config. Start from the fastest-path config
above (pipeline, inbuilt or own keys) and add these fields. List the track choice first in
your answer: on a bridge server (track 2) your code applies the same rule (for example, reply
only when the transcript contains the agent's name); on the hosted Agents API (track 3) the
fields below do it.

Pipeline agents start with a wake word on by default (`"hey assistant"`, `"hello bot"`,
30 seconds). Set `wake_word` on purpose in every pipeline config: your own words, or
`"enabled": false` for an agent that must speak unprompted.

**Name-addressed assistant (wake word).** Silent until someone says its name.
```json
{ "mode": "pipeline",
  "agent": { "speak_only_when_asked": true, "chat_input": true },
  "wake_word": { "enabled": true, "words": ["hey nova", "ok nova", "nova"], "timeout": 30,
                 "bypass_below_participants": 1 },
  "transcriber": { "provider": "deepgram", "model": "nova-3", "boostwords": ["Nova"] } }
```
`speak_only_when_asked` lets the agent act (tools) but speak only when addressed by name;
the wake word gates listening. Use either or both. `bypass_below_participants: 1` turns the
gate off in a 1:1 call.

**Standup facilitator.** Runs the round and logs decisions; or, for "only talk when named",
use the assistant recipe above with a standup prompt.
```json
{ "model": { "system_prompt": "You run a 15-minute daily standup. Ask each person, by name, for yesterday, today and blockers. Keep each turn short. Repeat each decision back in one sentence.",
             "first_message": "Hi all, I'm the standup assistant (an AI). Who wants to start?" },
  "agent": { "speaker_aware_responses": true },
  "wake_word": { "enabled": false } }
```
`speaker_aware_responses` gives the model each speaker's name. After the call, wait for
`transcription.processed`, get the transcript, have your own model pull the decisions and
blockers, and post them with your own Slack (or Teams, email) integration. MeetStream does
not post to Slack. For a recurring standup, auto-join it from the calendar
(`calendar-automation`).

**AI interviewer.** Asks one question at a time and waits for the answer.
```json
{ "model": { "system_prompt": "You interview {{candidate_name}} for the {{role}} role. Ask one question at a time from this list: ... Wait for the full answer, ask at most one follow-up, then move on. Do not give feedback on answers.",
             "first_message": "Hi {{candidate_name}}, I'm an AI interviewer. This call is recorded and transcribed for the hiring team. Ready to start?" },
  "agent": { "enable_interruptions": true, "max_endpointing_delay": 5.0 },
  "wake_word": { "enabled": false } }
```
Per interview, send the bot with `agent_config_id`, `join_at` (or calendar auto-join),
`agent_config_params` (`{"candidate_name": "...", "role": "..."}`), and the normal recording
fields (`recording_config.transcript`, `video_required: true` if the team wants video).
After the call: `transcription.processed` → `get_transcript`, and the recording URLs
(`recordings-and-media`). A longer `max_endpointing_delay` gives candidates time to pause.

**Practice or role-play persona** (sales practice, exam practice, language partner).
Always on, so realtime mode (lowest latency) or pipeline with `"wake_word": {"enabled": false}`.
Put the persona, the scenario and the rules in `system_prompt`, and the opening line in
`first_message` (pipeline) or the prompt (realtime). For language practice, set
`transcriber.language` (pipeline) to the practice language, or `multi` for mixed speech.

**Demo or FAQ agent.** Answers product questions from your content.
```json
{ "agent": { "mcp_servers": [{ "url": "https://kb.example.com/mcp", "allowed_tools": ["search_docs"] }],
             "chat_input": true, "tools": ["screen"] },
  "model": { "provider": "openai", "model": "gpt-4o", "system_prompt": "You demo Acme. Answer from search_docs only; say when you do not know." } }
```
`agent.custom_functions` registers your own HTTPS endpoints as tools instead of an MCP
server. `tools: ["screen"]` (Google Meet only, with a model that can see images) lets the
agent present and work a live web page.

### Agents in other languages

Set `transcriber.language` to the meeting language (pipeline), write the `system_prompt`
in that language or tell the agent to answer in it, and pick a voice model that speaks it
(for example ElevenLabs `eleven_multilingual_v2`, with your own ElevenLabs key). Use `multi` or `auto` for automatic
detection or mixed-language meetings.

```json
{ "mode": "pipeline",
  "transcriber": { "provider": "deepgram", "model": "nova-3", "language": "ru" },
  "model": { "provider": "openai", "model": "gpt-4o-mini",
             "system_prompt": "Ты помощник на встрече. Отвечай только по-русски и коротко." },
  "voice": { "provider": "elevenlabs", "model": "eleven_multilingual_v2", "voice_id": "<your ElevenLabs voice id>" },
  "agent": { "speak_only_when_asked": true },
  "wake_word": { "enabled": true, "words": ["Нова", "эй Нова"] } }
```
Language support follows the provider you choose. For a decisions summary at the end of the
call, use the transcript after the call (`meeting-brief`) or ask the agent for a recap
before it leaves.

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

### Agent options (API v1.10.0)

All default `false` (or off); set them in the `agent` block, except `transcriber.language`.

| Field | What it does |
|---|---|
| `agent.chat_input: true` | The agent treats chat messages that name it as requests and answers in the chat. Google Meet, Teams and Zoom. |
| `agent.quiet_actions: true` | The agent does the task without talking through each step. |
| `agent.speak_only_when_asked: true` | Pipeline mode. The agent can still act, but speaks only when someone addresses it by name. |
| `agent.tools: ["screen"]` | Google Meet only, with a model that can see images (vision-capable). The bot presents a live web page; the agent opens, reads, clicks, types, scrolls and looks at it, and can post text or a screenshot to the chat. |
| `agent.desktop: true` (with `"screen"`) | Google Meet only, opt-in. The bot presents its own desktop (editor, terminal, spreadsheet); it is removed when the bot leaves. |
| `transcriber.language` | Speech recognition uses this language. Leave it unset, or use `multi` or `auto`, for automatic detection. |

```json
{ "agent": { "chat_input": true, "speak_only_when_asked": true, "tools": ["screen"] },
  "model": { "provider": "openai", "model": "gpt-4o", "system_prompt": "..." } }
```

### Anthropic Claude as the LLM

Pipeline mode only: `"model": { "provider": "anthropic", "model": "claude-haiku-5-5", ... }`
(`claude-haiku-5-5` for the fastest replies, `claude-sonnet-5-5` or `claude-opus-5-5` for
harder tasks). The Anthropic key is saved in the dashboard under model integrations
(provider `anthropic`).

- `temperature` must be 0 to 1. `reasoning_effort` is optional (`"low"` when omitted).
- `tool_choice` may only be `"auto"` or `"none"`.
- `top_p`, `frequency_penalty`, `presence_penalty` and `logit_bias` return 400
  `Anthropic models do not support: ...`.
- Claude is an LLM for MIA only, not a transcription provider and not a `create_bot` field.

### Changing a running agent

`update_live_agent` (MCP) or `POST /api/v1/bots/{bot_id}/update_mia` (REST) with at least one of `agent_config_params`
(merged), `system_prompt` (replaces the instructions), `wake_word_enabled`, `wake_words`.
A plain 200 `{"status": "accepted"}` means accepted for delivery, not applied. Add
`"wait_for_ack": true` to get the agent's answer: `status` is `applied`,
`partially_applied`, `failed` (with `errors: [{field, reason}]`) or `accepted` with
`ack_timeout: true` (the update may still apply). A non-boolean `wait_for_ack` returns 400.

To have the agent wait its turn, raise the bot's hand first:
`POST /api/v1/bots/{bot_id}/send_command` `{"command": "raise_hand"}`, then `lower_hand`
after it speaks (see `join-meeting`).

## Things worth configuring that people miss

- **`boostwords`** on the transcriber - feed it product names, people's names and
  jargon. This single field fixes most "it mishears our company name" complaints.
- **`mcp_servers` and `tools`** on `agent` - the agent can call tools mid-conversation.
  This is what turns a talking bot into something that can actually do work in the call.
- **Interruption handling** - `enable_interruptions`, `interruption_mode`,
  `false_interruption_timeout`, and VAD tuning (`vad_threshold`, `vad_eagerness`,
  endpointing delays). If the agent talks over people or cuts itself off, this is the
  knob, not the prompt.
- **`first_message`** - what it says on joining. Set it, and make it disclose that the
  bot is an AI participant.
- **`Avatar`** (`provider`, `enabled`, `avatar_id`) gives the agent a face in the meeting
  video rather than a static tile. Confirmed working end to end, so it is safe to offer.
  It also works on Zoom bots that join without the user's own Zoom app.

## Wake-word agents

With `wake_word.enabled`, the agent stays silent until someone says a trigger phrase,
then listens for `timeout` seconds. A pipeline agent with no `wake_word` block starts with
the gate on (`"hey assistant"`, `"hello bot"`); set `"enabled": false` for an always-on
agent. Give it phrase variants people will actually say
("hey acme", "ok acme", "acme"), and keep the timeout long enough for a full question
(20-40s is usually right; 5-10s cuts people off mid-sentence).

This is the right default for agents that sit in real customer calls. An always-on
agent in a sales call is usually a bad experience.

## Testing an agent

1. Create the config (`create_agent`, or `POST /api/v1/mia`), note the `agent_config_id`.
2. Use `create_bot` (MCP tool) with `meeting_link` + `agent_config_id`.
3. Follow with `get_bot_status` until `Recording`.
4. Join the meeting yourself and talk to it. To see what the bot sees, `take_screenshot`
   (Google Meet and Teams), then `get_media_urls` with `kind: "screenshots"`.
5. `remove_bot` when done.

If the agent joins but never speaks, check in this order: is `agent_config_id` actually
set on the bot; did you wrongly also pass `socket_connection_url` / `live_audio_required`;
is a wake word enabled that you are not saying; is `speak_only_when_asked` on (say its
name); is the provider key configured (3c) or are inbuilt keys on (3a).

## Latest docs

- Bridge server (track 2): https://docs.meetstream.ai/guides/websockets/bridge-server-architecture
- Voice agent pricing and keys (track 3): https://docs.meetstream.ai/guides/mia/pricing-and-keys
- Screen sharing and custom agents (3d, coming soon): https://docs.meetstream.ai/guides/features/mia-screen-sharing-and-custom-agents
- MIA API guide (every config field, realtime providers, wake word, `update_mia`): https://docs.meetstream.ai/guides/mia/mia-api-guide
- Create an agent (xAI pipeline example): https://docs.meetstream.ai/guides/mia/create-an-agent

For the latest details, fetch the page with `.md` appended, read https://docs.meetstream.ai/llms.txt, or connect the docs MCP server at https://docs.meetstream.ai/_mcp/server.


