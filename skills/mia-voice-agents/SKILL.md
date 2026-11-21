---
name: mia-voice-agents
description: >
  Agents that talk in a meeting ("voice agent", "AI agent in the call",
  "bot that talks", "MIA"). Stack not said: ask once, own stack or
  hosted? 2a) bridge server first: the bot opens
  live_audio_required.websocket_url + socket_connection_url.websocket_url to
  your server; any STT, LLM, TTS, local too; bot price only. 2b) Yes: your own agent (Claude Code, Codex, Hermes, OpenClaw and others) can be the voice agent's brain through `model.provider: "local_agent"` and the MeetStream Agent Kit, with a
  warning: meeting speech reaches an agent with access to their computer
  (prompt injection); readonly access; the computer must stay on for the
  whole call. 3) hosted Agents API (MIA), no infra: MeetStream's inbuilt keys
  (key_source "meetstream", OpenAI and Deepgram), then own provider keys; bot
  + $0.25 per hour + models. If managed keys are not available, go on with
  own keys, never retry. Hosted bot: only agent_config_id. Grok or Gemini:
  provider xai or google. Recipes: wake word, standup, interviewer, role-play.
---

# Agents in meetings (voice agents; Agents API, API name MIA)

A voice agent is an AI participant on a MeetStream bot: it hears the meeting and answers
by voice, in the chat, or with silent tool calls. Say "voice agent" or "agent in the
meeting" to users, and give "MIA" once as the API name of the hosted Agents API (flow 3).

For recordings, transcripts and live data with no agent, use the Bot API (flow 1:
`join-meeting`, `meeting-brief`, `realtime-streaming`). Bring agents in only when the
user asks for an agent, a voice agent or a bot that talks.

## Pick the flow first

If the user wants an agent but does not say how, ask one question: **run your own stack**
(a bridge server, any models, including local ones) **or let MeetStream host it** (the
Agents API)? If they want no infrastructure work, flow 3 is the answer. Otherwise
recommend flow 2 first. In every answer, table or comparison, list the bridge server
(2a) first and the hosted Agents API (3) last, even for a "build me an agent" request;
do not recommend the hosted flow over the bridge unless the user said they want no
infrastructure work.

| Flow | What the user does | Price per meeting hour |
|---|---|---|
| 2a. Bridge server (your own stack, recommended first) | Runs a server that the bot connects to with two WebSockets: live audio in (`live_audio_required.websocket_url`) and the control socket (`socket_connection_url.websocket_url`) to send audio, chat, images and interrupts back. Any speech-to-text, LLM and voice, local or hosted (for example Parakeet for local speech-to-text, a local LLM, a local TTS). | Bot price only. MeetStream charges no agent infrastructure and no model tokens. |
| 2b. Your own agent as the brain | Their own agent (Claude Code, Codex, Hermes, OpenClaw and others) writes what the voice agent says, through `model.provider: "local_agent"` and the MeetStream Agent Kit. Always with the warning below. | Bot price + $0.25 agent infrastructure. No model tokens for the agent's reasoning. |
| 3. Hosted Agents API (MIA) | MeetStream hosts the agent. 3a: MeetStream's inbuilt keys (OpenAI and Deepgram today, `"key_source": "meetstream"`). 3b: their own provider keys (OpenAI, Anthropic, Deepgram, ElevenLabs and the others in the docs). | Bot price + $0.25 agent infrastructure + the models picked (with own keys, the provider bills model usage). |

Bot price: $0.35 per recording hour ($0.25 at volume). The MeetStream transcription
add-on is $0.10 per hour and is waived with your own provider key. Give the price as these
parts; do not add them into a total or give any other price: for exact model rates, send
the user to the dashboard agent editor or https://docs.meetstream.ai/guides/mia/pricing-and-keys.

Flows 2a and 3 are separate bots: a bridge bot has the two sockets and no
`agent_config_id`; a hosted agent bot has only `agent_config_id`.

## Flow 2a: bridge server (your own stack)

The bot connects out to your server; you host both endpoints (`wss://`, publicly
reachable; a tunnel works for local development):

```bash
curl -X POST https://api.meetstream.ai/api/v1/bots/create_bot \
  -H "Authorization: Token $MEETSTREAM_API_KEY" -H "Content-Type: application/json" \
  -d '{"meeting_link": "https://meet.google.com/abc-defg-hij", "bot_name": "Assistant",
       "live_audio_required": {"websocket_url": "wss://your-bridge.example/bridge/audio"},
       "socket_connection_url": {"websocket_url": "wss://your-bridge.example/bridge"}}'
```

Your bridge decodes the audio frames, runs your speech-to-text, LLM and TTS, and sends
the reply back with `sendaudio` (plus `sendmsg`, `sendimg`, `interrupt` and
`resume_audio`) on the control socket. The full recipe (frames, commands, barge-in) is in
`realtime-streaming`. Starter: the MeetStream Bridge
(https://github.com/meetstream-ai/meetstream-agent), FastAPI with OpenAI Realtime by
default; swap in local models. Docs: https://docs.meetstream.ai/guides/websockets/bridge-server-architecture

## Flow 2b: your own agent (`local_agent`)

Yes: the user's own agent (Claude Code, Codex, Hermes, OpenClaw and others) can be the
voice agent's brain through `model.provider: "local_agent"` and the MeetStream Agent Kit.
It needs no API integration of its own: the agent keeps its own subscription and login.
Say yes first, then give the warning below in the same answer.

> **Warning:** what people say and type in the meeting reaches an agent that has access
> to your computer and your terminal. Someone in the call can try to make it run
> commands or read files (prompt injection). Use the lowest access level (`readonly`,
> the default), keep the activation code on, and keep your computer, your agent and the
> bridge running for the whole call.

Give this warning in the same answer whenever you offer flow 2b. Steps:

1. Install and run the MeetStream Agent Kit (https://github.com/meetstream-ai/agent-kit)
   on macOS or Linux with Python 3.10+: `uv tool install meetstream-agent-kit` (or
   `pipx install meetstream-agent-kit`), then `meetstream-agent-kit`. Pick the agent
   (Claude Code `claude`, Codex `codex`, Hermes `hermes`, Copilot CLI `copilot`, OpenClaw
   `openclaw` and others in the README).
2. Save the pairing token it shows once (`msak_...`) in the dashboard under
   Integrations > Models > Local agent.
3. Create the agent:
   ```json
   {
     "agent_name": "My agent in the meeting",
     "mode": "pipeline",
     "model": {
       "provider": "local_agent",
       "local_agent": { "url": "https://<your-bridge-host>", "label": "Claude Code",
                        "access": "readonly", "require_code": true }
     },
     "transcriber": { "provider": "deepgram", "model": "nova-3", "language": "en", "key_source": "meetstream" },
     "voice": { "provider": "openai", "model": "tts-1", "voice_id": "nova", "key_source": "meetstream" }
   }
   ```
   `transcriber` and `voice` are required (inbuilt or own keys); `model.model` and
   `system_prompt` are optional. If saving it fails with a message that `local_agent`
   is not available, the own-agent setup is not on for the account yet: say so and offer
   the bridge server (flow 2a) or the hosted agent (flow 3). Never retry in a loop.
4. Test the link before the call: `GET /api/v1/mia?agent_config_id=<id>&check=local_agent`
   (`status: "ok"`; others such as `login_expired`, `unreachable`, `token_rejected`).
5. Send the bot with `agent_config_id`. In the meeting, the owner pastes the 6-digit
   activation code that the bridge shows into the chat (single use, 5 minutes). The code
   works on Google Meet; on Zoom and Teams set `require_code: false` and use `owner_names`.

Access levels: `readonly` (default), `confirm` (you answer `y` in the bridge terminal for
each action), `full` (needs the activation code, or `owner_only` with `owner_ids`).
Nothing said in the meeting can raise the level. Details: "MIA Screen Sharing and Custom
Agents" (https://docs.meetstream.ai/guides/features/mia-screen-sharing-and-custom-agents).

## Flow 3: hosted Agents API (MIA)

MeetStream hosts the agent, so the user hosts nothing. Agent configs are REST-only (no MCP
tools): create the config with `POST /api/v1/mia`, then send a bot with only
`agent_config_id` (the `create_bot` MCP tool or REST).

### Fastest path (flow 3)

1. Create the agent (3a, inbuilt keys):
   ```bash
   curl -X POST https://api.meetstream.ai/api/v1/mia \
     -H "Authorization: Token $MEETSTREAM_API_KEY" -H "Content-Type: application/json" \
     -d '{"agent_name": "Meeting assistant", "mode": "pipeline",
          "transcriber": {"provider": "deepgram", "model": "nova-3", "language": "en", "key_source": "meetstream"},
          "model": {"provider": "openai", "model": "gpt-4o-mini", "key_source": "meetstream",
                    "system_prompt": "You are a concise meeting assistant."},
          "voice": {"provider": "openai", "model": "tts-1", "voice_id": "nova", "key_source": "meetstream"}}'
   ```
   Set `transcriber.language` to the meeting's language (`en`, `es`, `ru` and so on), or
   `multi` for automatic detection. For a job (name-addressed assistant, standup,
   interviewer, role-play, demo agent), add the fields from "Recipes by job" below.
2. Send a bot with only the `agent_config_id` from the response:
   ```bash
   curl -X POST https://api.meetstream.ai/api/v1/bots/create_bot \
     -H "Authorization: Token $MEETSTREAM_API_KEY" -H "Content-Type: application/json" \
     -d '{"meeting_link": "https://meet.google.com/abc-defg-hij", "bot_name": "Assistant", "agent_config_id": "<id>"}'
   ```
3. Join the meeting and talk to it. `remove_bot` when done.

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

### 3a. MeetStream's inbuilt keys

Set `"key_source": "meetstream"` on each pipeline section (`transcriber`, `model`,
`voice`) that uses an inbuilt key, and send no `api_key` in that section. Pipeline mode
only. Sections can mix: one section on an inbuilt key, another on the user's own key.
For any provider other than OpenAI and Deepgram, use 3b (own keys) for that section.

**If inbuilt keys are not on for the account.** The API answers `400`
`MeetStream-managed keys are not available for <section>. Use your own key.` (or, on
`create_bot` with a saved agent, `MeetStream-managed keys are turned off. Edit the agent
to use your own keys for: ...`). Tell the user that inbuilt keys are not on for their
account yet, then go on with 3b: add the provider key in the dashboard under
Configure > Integrations (Models, Voice, Transcription), remove `key_source` (or set it to
`"user"`) in that section, and save again. Never retry the same request in a loop: it
gets the same answer.

Other `400`s: `key_source: "meetstream"` in realtime mode; an `api_key` in a section with
`key_source: "meetstream"`; a provider or model with no inbuilt key (the message lists the
ones you can use).

### 3b. Your own provider keys

No `key_source` (or `"key_source": "user"`). The user saves each provider key in the
dashboard under Configure > Integrations; the agent config holds provider names and
settings, never the keys. Works in pipeline and realtime mode. A missing key returns
`400` `API key not configured for: ...`.

## Hosted agents on Grok (xAI) or Gemini (Google)

"Make Grok join my call" and "put Gemini in the meeting" are hosted voice agents (flow 3)
with the `xai` or `google` provider, or the model behind your own bridge server (flow 2a).
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
above (pipeline, inbuilt or own keys) and add these fields. List the flow choice first in
your answer: on a bridge server (2a) your code applies the same rule (for example, reply
only when the transcript contains the agent's name); on the hosted Agents API (3) the
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
bridge server flow (2a), where you host the audio yourself on a separate bot, and adding
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

Other operations: `GET /mia` (list, or one via `?agent_config_id=`),
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

`POST /api/v1/bots/{bot_id}/update_mia` (REST) with at least one of `agent_config_params`
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

1. Create the config, note the `agent_config_id`.
2. Use `create_bot` (MCP tool) with `meeting_link` + `agent_config_id`.
3. Follow with `get_bot_status` until `Recording`.
4. Join the meeting yourself and talk to it.
5. `remove_bot` when done.

If the agent joins but never speaks, check in this order: is `agent_config_id` actually
set on the bot; did you wrongly also pass `socket_connection_url` / `live_audio_required`;
is a wake word enabled that you are not saying; is `speak_only_when_asked` on (say its
name); is the provider key configured (3b) or are inbuilt keys on (3a).

## Latest docs

- Bridge server (flow 2a): https://docs.meetstream.ai/guides/websockets/bridge-server-architecture
- Your own agent (flow 2b): https://docs.meetstream.ai/guides/features/mia-screen-sharing-and-custom-agents
- Voice agent pricing and keys (flow 3): https://docs.meetstream.ai/guides/mia/pricing-and-keys
- MIA API guide (every config field, realtime providers, wake word, `update_mia`): https://docs.meetstream.ai/guides/mia/mia-api-guide
- Create an agent (xAI pipeline example): https://docs.meetstream.ai/guides/mia/create-an-agent

For the latest details, fetch the page with `.md` appended, read https://docs.meetstream.ai/llms.txt, or connect the docs MCP server at https://docs.meetstream.ai/_mcp/server.


