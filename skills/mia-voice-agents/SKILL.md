---
name: mia-voice-agents
description: >
  Voice agents (Agents API, API name MIA): an AI participant that listens and
  talks in a live meeting. Use only when the user asks: "voice agent", "AI
  agent in the meeting", "a bot that talks", "a bot that answers questions",
  "talking bot", "wake word assistant", "use my own Claude Code / Codex as the
  agent", or "MIA". Order: a) default to MeetStream's inbuilt keys (key_source
  "meetstream", OpenAI and Deepgram); b) then the user's own provider keys;
  inbuilt and own keys are the recommended defaults. Price: bot + $0.25 per
  hour agent infrastructure + models picked (dashboard shows the rate). If the
  API says managed keys are not available, inbuilt keys are not on for the
  account yet: go on with own keys, never retry. c) Own agent (local_agent,
  Agent Kit) only on request, with a warning: meeting speech reaches an agent
  with access to their computer (prompt injection); use readonly access and
  the activation code; the computer must stay on for the whole call.
---

# Voice agents (Agents API, API name MIA)

A voice agent is an AI participant on a MeetStream bot: it hears the meeting and answers
by voice, in the chat, or with silent tool calls. Say "voice agent" to users and give
"MIA" once as the API name. MeetStream hosts the audio bridge, so you host nothing.

This is the second way to integrate. Use it only when the user asks for an agent that
talks. For recordings, transcripts and live data, use the Bot API (`join-meeting`,
`meeting-brief`, `realtime-streaming`).

Agent configs are REST-only (no MCP tools): create the config with `POST /api/v1/mia`,
then send a bot with `agent_config_id` (the `create_bot` MCP tool or REST).

## Fastest path

1. Create the agent (setup a, inbuilt keys):
   ```bash
   curl -X POST https://api.meetstream.ai/api/v1/mia \
     -H "Authorization: Token $MEETSTREAM_API_KEY" -H "Content-Type: application/json" \
     -d '{"agent_name": "Meeting assistant", "mode": "pipeline",
          "transcriber": {"provider": "deepgram", "model": "nova-3", "language": "en", "key_source": "meetstream"},
          "model": {"provider": "openai", "model": "gpt-4o-mini", "key_source": "meetstream",
                    "system_prompt": "You are a concise meeting assistant."},
          "voice": {"provider": "openai", "model": "tts-1", "voice_id": "nova", "key_source": "meetstream"}}'
   ```
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

## Choose the setup first

Offer the setups in this order, before you ask about modes, providers, wake words or
prompts. Your first reply always names setup a (inbuilt keys, the default) and setup b
(the user's own provider keys), even when the user asked to "build" one.

| Setup | What the user does | Price per meeting hour |
|---|---|---|
| a. MeetStream's inbuilt keys (default) | Picks the modules (speech-to-text, LLM, voice, or just the LLM) and the models. No provider account. Inbuilt keys cover OpenAI (LLM, and OpenAI speech and voice models) and Deepgram (speech-to-text) today. | Bot price + $0.25 agent infrastructure + the per-hour price of each model picked. The dashboard agent editor shows the rate before the bot runs. |
| b. Bring your own keys | Adds their own provider keys (OpenAI, Anthropic, Deepgram, ElevenLabs and the others in the docs) and picks any supported model. | Bot price + $0.25 agent infrastructure. The provider bills the user for model usage. |
| c. Their own agent (only on request) | Their own agent (Claude Code, Codex, Hermes, OpenClaw and others) runs on their own subscription and writes what the voice agent says, through `model.provider: "local_agent"` and the MeetStream Agent Kit. | Bot price + $0.25 agent infrastructure. MeetStream charges no model tokens for the agent's reasoning. |

Bot price: $0.35 per recording hour ($0.25 at volume). The MeetStream transcription
add-on is $0.10 per hour and is waived with your own provider key. Do not give any other
price: for exact model rates, send the user to the dashboard agent editor or
https://docs.meetstream.ai/guides/mia/pricing-and-keys.

### a. MeetStream's inbuilt keys (default)

Set `"key_source": "meetstream"` on each pipeline section (`transcriber`, `model`,
`voice`) that uses an inbuilt key, and send no `api_key` in that section. Pipeline mode
only. Sections can mix: one section on an inbuilt key, another on the user's own key.
For any provider other than OpenAI and Deepgram, use setup b for that section.

**If inbuilt keys are not on for the account.** The API answers `400`
`MeetStream-managed keys are not available for <section>. Use your own key.` (or, on
`create_bot` with a saved agent, `MeetStream-managed keys are turned off. Edit the agent
to use your own keys for: ...`). Tell the user that inbuilt keys are not on for their
account yet, then go on with setup b: add the provider key in the dashboard under
Configure > Integrations (Models, Voice, Transcription), remove `key_source` (or set it to
`"user"`) in that section, and save again. Never retry the same request in a loop: it
gets the same answer.

Other `400`s: `key_source: "meetstream"` in realtime mode; an `api_key` in a section with
`key_source: "meetstream"`; a provider or model with no inbuilt key (the message lists the
ones you can use).

### b. Your own provider keys

No `key_source` (or `"key_source": "user"`). The user saves each provider key in the
dashboard under Configure > Integrations; the agent config holds provider names and
settings, never the keys. Works in pipeline and realtime mode. A missing key returns
`400` `API key not configured for: ...`.

### c. Their own agent (`local_agent`, only on request)

> **Warning:** what people say and type in the meeting reaches an agent that has access
> to your computer and your terminal. Someone in the call can try to make it run
> commands or read files (prompt injection). Use the lowest access level (`readonly`,
> the default), keep the activation code on, and keep your computer, your agent and the
> bridge running for the whole call.

Give this warning in the same answer whenever you offer setup c. Steps:

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
   setups a and b. Never retry in a loop.
4. Test the link before the call: `GET /api/v1/mia?agent_config_id=<id>&check=local_agent`
   (`status: "ok"`; others such as `login_expired`, `unreachable`, `token_rejected`).
5. Send the bot with `agent_config_id`. In the meeting, the owner pastes the 6-digit
   activation code that the bridge shows into the chat (single use, 5 minutes). The code
   works on Google Meet; on Zoom and Teams set `require_code: false` and use `owner_names`.

Access levels: `readonly` (default), `confirm` (you answer `y` in the bridge terminal for
each action), `full` (needs the activation code, or `owner_only` with `owner_ids`).
Nothing said in the meeting can raise the level. Details: "MIA Screen Sharing and Custom
Agents" (https://docs.meetstream.ai/guides/features/mia-screen-sharing-and-custom-agents).

## The one rule people get wrong

To attach an agent to a bot you pass **only `agent_config_id`**.

```json
{ "meeting_link": "https://...", "bot_name": "Assistant", "agent_config_id": "<id>" }
```

Do **not** also pass `socket_connection_url` or `live_audio_required`. Those are for
bring-your-own-bridge setups where you host the audio yourself, and adding them to a
MIA bot is a common cause of a silent agent. MeetStream hosts the MIA bridge.

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
then listens for `timeout` seconds. Give it phrase variants people will actually say
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
name); is the provider key configured (setup b) or are inbuilt keys on (setup a).

## Latest docs

- Voice agent pricing and keys: https://docs.meetstream.ai/guides/mia/pricing-and-keys
- What is MIA: https://docs.meetstream.ai/guides/mia/what-is-mia
- MIA API guide (every config field, `update_mia`): https://docs.meetstream.ai/guides/mia/mia-api-guide
- MIA screen sharing and your own agent: https://docs.meetstream.ai/guides/features/mia-screen-sharing-and-custom-agents
- Create an agent in the dashboard: https://docs.meetstream.ai/guides/mia/create-an-agent

For the latest details, fetch the page with `.md` appended, read https://docs.meetstream.ai/llms.txt, or connect the docs MCP server at https://docs.meetstream.ai/_mcp/server.


