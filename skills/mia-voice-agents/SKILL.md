---
name: mia-voice-agents
description: >
  Voice agents: an AI participant that listens and talks in a live meeting (API
  name MIA). Use only when the user asks for one: "voice agent", "AI agent in
  the meeting", "agent in my meeting", "a bot that talks", "a bot that answers
  questions", "a bot that speaks", "talking bot", "wake word assistant", "use my
  own Claude Code / Codex as the agent in the meeting", or "MIA". Default to
  MeetStream-managed keys (key_source "meetstream", no provider keys), then the
  user's own provider keys. The user's own agent through the MeetStream Agent
  Kit only on request, with a warning: meeting speech reaches an agent with
  access to their computer (prompt injection), use read-only access, and the
  computer must stay on for the whole meeting. Covers pipeline vs realtime mode,
  wake words, interruptions, tools and MCP servers on the agent.
---

# Voice agents (MIA)

A voice agent is a server-configured AI agent that joins a meeting and talks. Its API
name is MIA; say "voice agent" to users. MeetStream runs it
on its own hosted bridge, so you do not host any audio infrastructure.

**Important:** MIA management is **not** exposed as MCP tools. Create and manage agent
configs against the REST API, then attach the resulting id with the `create_bot` MCP tool.

## Choose the setup first

Offer these in this order, before you ask about modes, providers, wake words or
prompts. Use the user's words: "voice agent" (the API calls it MIA).

### 1. MeetStream-managed keys (default)

No provider accounts or keys to bring. Pipeline mode only. In each pipeline section
that MeetStream should run (`transcriber`, `model`, `voice`), set
`"key_source": "meetstream"` and send no `api_key`:

```json
{
  "agent_name": "Meeting Assistant",
  "mode": "pipeline",
  "transcriber": { "key_source": "meetstream" },
  "model":       { "key_source": "meetstream", "system_prompt": "..." },
  "voice":       { "key_source": "meetstream" }
}
```

- Only providers and models in the account's managed catalog work. `GET /api/v1/mia`
  returns it as `mia_managed`: `enabled`, `sections` (providers, models and per-hour
  prices) and `rates`. Omit `provider` / `model` to get the catalog default.
- The agent is billed per hour on the MeetStream account. There is no provider bill.
- 400s on save: `MeetStream-managed keys are not available for <section>. Use your own
  key.` (no managed catalog for the account: use setup 2), realtime mode, a provider or
  model that is not in the catalog (the message lists the allowed ones), an `api_key`
  sent with `"key_source": "meetstream"`, and accounts outside the US region.

### 2. Your own provider keys

`"key_source": "user"` (or no `key_source`). The user brings their own transcription,
LLM and voice provider keys, saved in the dashboard integrations or in the section's
`api_key` (masked on read), and sets up the providers, models and flow themselves. Works
in pipeline and realtime mode. The rest of this skill describes the config fields.

### 3. Your own agent on your own computer (MeetStream Agent Kit)

Yes, the user's own agent (for example their Claude Code or Codex subscription) can
write what the voice agent says, through the MeetStream Agent Kit
(https://github.com/meetstream-ai/agent-kit). Warn first, in the same answer: anyone in the meeting can try to make that agent run commands or read files on the user's computer (prompt injection); use the lowest access level (read-only) and the activation code, and keep the computer, the bridge and the tunnel running for the whole meeting. Offer it only when
the user asks for it; setups 1 and 2 stay the recommended ones. The Agent Kit runs a
bridge on the user's computer and a tunnel to it; the voice agent hears the meeting and
speaks, and the user's own agent CLI writes the answers. Point the user to the Agent Kit
README for setup. Repeat the warning in full:

> **Warning:** this connects your local agent, and through it your computer, to what
> anyone says in the meeting. Someone in the call can try to make your agent run
> commands or read files (prompt injection). Use the lowest access level that works
> (read-only), turn on the activation code so only you can talk to your agent, and keep
> your computer, the bridge and the tunnel running for the whole meeting.


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
is a wake word enabled that you are not saying; is the model provider key configured on
your MeetStream account.

## Reference

- [Create MIA](https://docs.meetstream.ai/guides/mia/create-an-agent)
- [MIA configurations](https://docs.meetstream.ai/guides/mia/mia-custom-configurations)
- [Create agent config API](https://docs.meetstream.ai/api-reference/api-endpoints/mia/create-agent-config)
- [Update](https://docs.meetstream.ai/api-reference/api-endpoints/mia/update-agent-config) · [List](https://docs.meetstream.ai/api-reference/api-endpoints/mia/get-agent-configs) · [Delete](https://docs.meetstream.ai/api-reference/api-endpoints/mia/delete-agent-config)
- [Bridge server architecture](https://docs.meetstream.ai/guides/websockets/bridge-server-architecture) (bring-your-own-bridge, not needed for MIA)
