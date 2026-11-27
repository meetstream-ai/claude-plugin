# Use case patterns: Pattern 8: Live video (not available on meeting bots)

> Part of [`use-case-patterns.md`](use-case-patterns.md), split so each file stays under 20 KB.

### Pattern 8: Live video (not available on meeting bots)

Meeting bots on Google Meet, Zoom and Teams do not stream live video: `live_video_required` is accepted but ignored, and it still moves the bot to the larger video compute tier, so do not send it. For video, record it (`video_required: true`) and fetch it after the call, or use per-participant video streams. Live video frames exist only on Zoom Meeting Direct Connect (RTMS) sessions (`setting-up-platforms`).

### Pattern 9: MIA - AI Agent in a Meeting

MIA (MeetStream Infrastructure Agents) creates a server-configured AI agent that joins meetings via a hosted bridge. Two modes:

- **`pipeline`**: mix STT + LLM + TTS providers (configurable per layer)
- **`realtime`**: a single realtime model (OpenAI realtime, xAI, Google Gemini) - lower latency

This is track 3 (Agents API infra, hosted). Use it only when the user asks for a voice agent and wants MeetStream to host it; for their own stack, give the bridge server (track 2, `streaming-live-data`, bot price only). Keys in order: 3a MeetStream's own, default keys (`"key_source": "meetstream"` on each pipeline section; Deepgram and OpenAI, pipeline mode), then 3c the user's own keys. Price: bot + $0.25 per hour agent infrastructure + the models picked. 3b (LiveKit) and 3d (your coding agent through `meetstream setup`) are coming soon: no setup steps. Full guide: `building-voice-agents`.

**Create the agent config first** (in the dashboard at app.meetstream.ai, with the `create_agent` MCP tool after `list_agents`, or via the API; `model.system_prompt` is required):
```
POST /api/v1/mia
{
  "agent_name": "Meeting Assistant",
  "mode": "pipeline",
  "model": { "provider": "openai", "model": "gpt-4.1", "system_prompt": "..." },
  "voice": { "provider": "openai", "voice_id": "nova" },
  "transcriber": { "provider": "deepgram", "model": "nova-3", "language": "en" },
  "agent": { "response_type": "voice", "first_message": "Hello!" }
}
```

Returns `{ message, agent_config_id, agent_config: {...} }`.

**Then attach it to a bot - pass only `agent_config_id`:**
```json
POST /bots/create_bot
{
  "meeting_link": "https://meet.google.com/...",
  "bot_name": "Assistant",
  "agent_config_id": "<from above>"
}
```

That's all MIA needs - MeetStream runs the agent on its own hosted bridge. Do **not** pass `socket_connection_url` or `live_audio_required` for MIA (a silent agent); those are for the bridge server flow (2a) and Patterns 3, 7 and 8, point at *your* server, and go on a separate bot.

**Other MIA operations:**
- `GET /api/v1/mia` - list all (no params) or fetch one (`?agent_config_id=...`). Secrets come back masked (`****` + last four characters); sending the mask back on `PUT` keeps the stored value.
- `PUT /api/v1/mia` - update; body requires `agent_config_id` + fields to change
- `DELETE /api/v1/mia?agent_config_id=...` - delete (query param, not path)
- `POST /bots/{bot_id}/update_mia` - change a running agent's prompt, params or wake words mid-meeting. Add `"wait_for_ack": true` to get the result instead of a plain `accepted` (see In-Meeting Commands in `skills/sending-bots/references/bot-config.md`).

**Anthropic Claude as the MIA LLM** (`model.provider: "anthropic"`):
- Pipeline mode only. Uses the Anthropic API key saved in the dashboard under model integrations (provider `anthropic`).
- `model.model`: for example `claude-haiku-5-5` (fastest replies) or `claude-sonnet-5-5`, `claude-opus-5-5`.
- `temperature` must be 0 to 1. `reasoning_effort` is optional (`"low"` when omitted). `tool_choice` may only be `"auto"` or `"none"`.
- `top_p`, `frequency_penalty`, `presence_penalty` and `logit_bias` return 400 `Anthropic models do not support: ...`.
- Claude is an LLM for MIA only. It is **not** a transcription provider and is not a `create_bot` field.

Supported providers: see `skills/meetstream/references/api-reference.md` MIA section.
