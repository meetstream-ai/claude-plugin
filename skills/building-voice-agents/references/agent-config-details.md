# Voice agent configuration details

> Moved from the `mia-voice-agents` skill (3.3.1) to keep `building-voice-agents/SKILL.md` under 500 lines.

## Agent options (API v1.10.0)

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
