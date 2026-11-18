---
name: mia-voice-agents
description: >
  Build MIA voice agents - AI participants that listen and speak in a live
  meeting. Use when the user says "voice agent", "AI agent in the meeting",
  "talking bot", "MIA", "agent that answers questions in the call", "wake word
  assistant", "conversational meeting bot", "AI avatar in a meeting", or wants
  the bot to respond rather than just record. Covers pipeline vs realtime mode,
  wake words, interruptions, tools and MCP servers on the agent.
---

# MIA: MeetStream Infrastructure Agents

MIA is a server-configured AI agent that joins a meeting and talks. MeetStream runs it
on its own hosted bridge, so you do not host any audio infrastructure.

**Important:** MIA management is **not** exposed as MCP tools. Create and manage agent
configs against the REST API, then attach the resulting id with the `create_bot` MCP tool.

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
`DELETE /mia?agent_config_id=...`.

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
is a wake word enabled that you are not saying; is the model provider key configured on
your MeetStream account.

## Reference

- [Create MIA](https://docs.meetstream.ai/guides/mia/create-an-agent)
- [MIA configurations](https://docs.meetstream.ai/guides/mia/mia-custom-configurations)
- [Create agent config API](https://docs.meetstream.ai/api-reference/api-endpoints/mia/create-agent-config)
- [Update](https://docs.meetstream.ai/api-reference/api-endpoints/mia/update-agent-config) · [List](https://docs.meetstream.ai/api-reference/api-endpoints/mia/get-agent-configs) · [Delete](https://docs.meetstream.ai/api-reference/api-endpoints/mia/delete-agent-config)
- [Bridge server architecture](https://docs.meetstream.ai/guides/websockets/bridge-server-architecture) (bring-your-own-bridge, not needed for MIA)
