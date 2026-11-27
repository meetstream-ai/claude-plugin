# MeetStream API Reference: MIA (MeetStream Infrastructure Agents) Endpoints

> Part of [`api-reference.md`](api-reference.md), split so each file stays under 20 KB.

## MIA (MeetStream Infrastructure Agents) Endpoints

All MIA operations use the same path `/api/v1/mia` (singular). The HTTP method distinguishes the operation.

MCP tools for the same operations (use them when the MeetStream MCP is connected): `list_agents` (`GET`, with `mia_managed`, no prices), `get_agent`, `create_agent` (`POST`), `update_agent` (`PUT`; a `mode` change needs the full config), `delete_agent` (`DELETE`, `confirm: true`), `check_local_agent` (`?check=local_agent`, for the coming-soon track 3d only). `create_agent` refuses `key_source: "meetstream"` in realtime mode.

### POST `/api/v1/mia` - Create

**Required:**
- `agent_name` (string)
- `mode` (string) - `"pipeline"` or `"realtime"`
- `model` (object) - see below. `model.system_prompt` is required except with `local_agent`: without it the API returns `400` `{"message": "Missing model.system_prompt."}`

**Optional:**
- `voice` (object, **pipeline only**; `voice.voice_id` is required in pipeline mode: `400` `{"message": "Missing voice.voice_id."}`)
- `transcriber` (object, **pipeline only**)
- `agent` (object) - `response_type` (`"voice"` / `"chat"` / `"action"`, default `"voice"`), `first_message` (string), `mcp_servers` (array), `tools` (`current_time`, `weather_now`, `screen`: Google Meet only, vision-capable model), `desktop` (Google Meet, with `screen`, opt-in), `chat_input`, `quiet_actions`, `speak_only_when_asked` (pipeline) - all default `false`
- `audio` (object) - `sample_rate`, `num_channels`
- `wake_word` (object, **pipeline only**) - `enabled` (bool), `words` (array or comma-separated string), `timeout` (seconds, default 30)
- `avatar` (object) - `enabled` (bool), `provider` (`"anam"`), `avatar_id` (required when provider is anam)

**Keys (`key_source`, pipeline sections `transcriber`, `model`, `voice`):** `"meetstream"` = MeetStream's inbuilt key (pipeline mode only, no `api_key` in that section; inbuilt keys cover OpenAI and Deepgram today); `"user"` or not sent = the user's own key from dashboard Integrations. `400 MeetStream-managed keys are not available for <section>. Use your own key.` means inbuilt keys are not on for the account yet: use own keys, do not retry. Price: bot + $0.25 per hour agent infrastructure + the models picked. https://docs.meetstream.ai/guides/mia/pricing-and-keys . This is track 3 (Agents API infra, hosted: 3a default keys, 3c own keys); an agent on the user's own stack uses a bridge server (track 2) instead (both `live_audio_required` and `socket_connection_url` on the bot, the bot price only): https://docs.meetstream.ai/guides/websockets/bridge-server-architecture

**`model` schema (pipeline):**
- `provider` - `"openai"`, `"anthropic"`, `"google"`, `"xai"`, or `"local_agent"` (track 3d, COMING SOON, not in production: do not give it as a working option; the user's own coding agent through `meetstream setup` once the relay is live: `model.local_agent` = `url` (https, required), `label`, `access` (`readonly` default, `confirm`, `full`), `require_code` (default true), `owner_only` (default true), `owner_names` / `owner_ids`, `timeout_s` (10-600, default 120); `model.model` and `system_prompt` optional; test with `GET /api/v1/mia?agent_config_id=<id>&check=local_agent`)
- `model` - e.g. `"gpt-4.1"`, `"gpt-4.1-mini"`; for Anthropic e.g. `"claude-haiku-5-5"`, `"claude-sonnet-5-5"`, `"claude-opus-5-5"`
- `system_prompt` - defines personality
- `temperature` (optional, 0–2; 0–1 for Anthropic)
- `max_tokens` (optional)

**Anthropic (`provider: "anthropic"`) constraints:**
- Pipeline mode only. Uses the Anthropic key saved in the dashboard under model integrations (provider `anthropic`).
- `reasoning_effort` optional (`"low"` when omitted; `"low"`, `"medium"`, `"high"`, and `"xhigh"` / `"max"` on models that keep thinking on).
- `tool_choice` only `"auto"` or `"none"`.
- `top_p`, `frequency_penalty`, `presence_penalty`, `logit_bias` → 400 `Anthropic models do not support: ...`.
- Anthropic is a MIA LLM provider only, not a transcription provider.

**`model` schema (realtime):**
- `provider` - `"openai"`, `"xai"`, or `"google"`
- `model` - required for OpenAI only
- `system_prompt`
- `voice` - required; valid values:
  - OpenAI: `alloy, ash, ballad, coral, echo, fable, nova, onyx, sage, shimmer, verse`
  - xAI: `Ara, Eve, Leo, Rex, Sal`
  - Google: `Puck, Charon, Kore, Fenrir, Aoede, Leda, Orus, Zephyr`
- `temperature` (optional)
- `max_response_output_tokens` (optional, OpenAI only)
- `thinking_config` (Google Gemini, optional) - `{include_thoughts: bool, thinking_budget: int}`

**`voice` schema (pipeline TTS):**
- `provider` - `"openai"` or `"elevenlabs"`
- `voice_id` - required
- `model` - e.g. `"tts-1"`, `"eleven_turbo_v2_5"`

**`transcriber` schema (pipeline STT):**
- `provider` - `"openai"`, `"deepgram"`, or `"assemblyai"`
- `model` - e.g. `"nova-3"`, `"whisper-1"`
- `language` - e.g. `"en"`, `"es"`
- `boostwords` - array of strings

**`agent.mcp_servers[]`:**
- `url` (HTTPS, required)
- `headers` (object, e.g. `{Authorization: "Bearer ..."}`)
- `allowed_tools` (array, whitelist)
- `timeout` (seconds, default 10)

**Response (200):** `{ message, agent_config_id, agent_config: {...} }`

### GET `/api/v1/mia`
Lists all or returns one (`?agent_config_id=...` query param). Secrets in the response are masked (`****` + last four characters): `api_key`-like fields and header values in `mcp_servers` / custom functions. Sending a masked value back on `PUT` keeps the stored secret.

Returns `{ agent_configs: [...], count }` or `{ agent_config: {...} }`.

### PUT `/api/v1/mia` - Update
Body requires `agent_config_id` plus any subset of: `agent_name`, `mode`, `model`, `voice`, `transcriber`, `agent`, `wake_word`, `audio`, `avatar`. Only included fields are updated.

> Changing `mode` triggers full re-validation. Updating individual sections (model/voice/transcriber) only validates required API keys exist.

### DELETE `/api/v1/mia?agent_config_id=...`
**Query param**, not path id. Returns `{ message }`.

### Error codes
- `400` - missing required field, invalid value, unsupported provider, provider API key not configured
- `403` - not the owner
- `404` - not found
- `405` - method not allowed
- `500` - server error

### Using a MIA agent on a bot

Pass only the `agent_config_id` - MeetStream runs the agent on its own hosted bridge.

```json
POST /bots/create_bot
{
  "meeting_link": "...",
  "agent_config_id": "<id>"
}
```

Do **not** send `socket_connection_url` or `live_audio_required` for MIA (a silent agent); those are for the bridge server flow and the real-time patterns, point at your own server, and go on a separate bot.

---

## Webhook Events (sent to `callback_url`)

HTTP POST. Your endpoint MUST return 2xx - **webhooks are not retried on non-2xx**.

**Full event list (verified against 4,139 captured webhook deliveries, Jun 2026):**

Every delivery carries `event`, `bot_id` and `timestamp`. Most also carry `bot_event`, which equals `event` except on terminals.

| # | event | bot_status | status_code | When | Extra payload fields |
|---|---|---|---|---|---|
| 0 | `bot.scheduled` | | 200 | Created with a future `join_at` | |
| 1 | `bot.joining` | `Joining` | 200 | Bot is connecting | |
| 1a | `bot.in_waiting_room` | `InWaitingRoom` | 200 | Held in the lobby | |
| 1b | `bot.error` | `InMeeting` | omitted | Streaming-provider upstream error during the meeting (e.g. AssemblyAI insufficient funds). Bot continues; only live transcription is impacted. Seen in May 2026 testing. | `message` (upstream error) |
| 2 | `bot.inmeeting` | `InMeeting` | 200 | Bot joined the meeting | |
| 3 | `bot.recording` | `Recording` | 200 | Recording started | |
| 4 | `participant_events.join` / `.leave` | | | Participants join/leave (requires `recording_config.realtime_endpoints` with `events: [...]`) | Nested under `data.data.{action,participant,timestamp}` and `data.bot.{id,metadata}`. No top-level `bot_id`, `bot_status` or `bot_event`. |
| 4a | `participant_events.raise_hand` / `.lower_hand` | | | A participant raised or lowered their hand (Google Meet, Zoom). Sent **only** to `realtime_endpoints` entries that list the event; never to workspace webhooks or `callback_url`. Transitions only; the bot's own hand is never reported | Same nested shape as `participant_events.join`; `data.data.action` is `raise_hand` / `lower_hand` |
| 5 | `bot.leaving` | `Leaving` | 200 | Bot is leaving the meeting | |
| 6 | `bot.stopped` | varies | 200 or 500 | Bot exited or never got in (fires once per bot). **Reason is in `bot_event`**, see below | |
| 6a | `bot.uploading` | | 200 | Media upload in progress | |
| 7 | `manifest.completed` | | 200 | Platform manifest uploaded | `status: "success"`, `manifest_status: "Success"` |
| 8 | `audio.processed` | | 200 | Audio ready to fetch | `status: "success"`, `audio_status: "Success"` |
| 9 | `transcription.processed` | | 200 | Transcript ready. **Post-call providers only** | `transcript_status: "Success"` |
| 9a | `bot.transcriptionready` | | 200 | Follows `transcription.processed` | |
| 9b | `transcription.failed` | | **500** | Transcript run failed. **Post-call providers only** | `status: "error"`, `transcript_status: "Failed"`, `message` (error detail) |
| 9c | `audio.skipped` / `manifest.skipped` / `transcription.skipped` | | | That stage had nothing to process (e.g. the bot never recorded) | |
| 10 | `video.processed` | | 200 | Video ready (only when `video_required: true`) | `video_status: "Success"` |
| 11 | `bot.done` | `Done` | 200 | All processing complete. **Final event on every path**, streaming-only bots included | `message` |
| 12 | `data_deletion` | | 200 | Data deleted (manual `/delete` or retention expiry) | `status: "success"`, `deleted_objects: <int>`. No `custom_attributes` |

**Terminals are two-layer.** Every ending arrives once with `event: "bot.stopped"`; `bot_event` gives the reason:

| `bot_event` | `status_code` | `bot_status` |
|---|---|---|
| `bot.stopped` (clean exit) | 200 | `Stopped` |
| `bot.kicked` (removed by a participant) | 200 | `Stopped` |
| `bot.notallowed` (lobby timeout) | 500 | `NotAllowed` |
| `bot.denied` (host refused) | 500 | `Denied` |
| `bot.failed` | usually 500 | `FAILED` / `ERROR` / `Failed` |

Branch on `bot_event`. A kick and a clean exit both report `Stopped`, and failure casing varies.

> **Streaming-only providers (`meetstream_streaming`, `assemblyai_streaming`, `deepgram_streaming`, `jigsawstack_streaming`, `meeting_captions`) never fire events 9, 9a or 9b.** They still get `bot.done` (50 of 50 streaming bots that recorded, in the captures). Use `bot.done` as the "session finished" signal on both paths.

Each event fires **at most once** per bot, except `bot.joining` (up to 3× if server-side join retries kick in) and `bot.inmeeting`, which can repeat.

> **Common envelope**: `bot_id`, `event`, `bot_event`, `message`, `status_code`, `custom_attributes`, `timestamp`. Exceptions:
> - `participant_events.*` has a completely different shape (nested under `data.bot.id`, no top-level `bot_id`)
> - `manifest.completed`, `manifest.skipped`, `bot.transcriptionready` and `bot.uploading` have no `bot_event`; read `payload.bot_event ?? payload.event`
> - `data_deletion` has no `custom_attributes`
> - **`status_code` is 500** for `transcription.failed` and failing terminals (`bot.notallowed`, `bot.denied`, most `bot.failed`). All captured `bot.done` deliveries were 200.

### `transcript_id` is NOT in the webhook payload

`transcription.processed` only signals timing. Fetch `transcript_id` via the canonical path - `GET /bots/{bot_id}/detail` → `bot_details.transcript_id` (also available in the `create_bot` response and `GET /bots/{bot_id}/transcriptions`).

### Sample payloads (live-captured)

**Lifecycle (`bot.joining` / `bot.in_waiting_room` / `bot.inmeeting` / `bot.recording` / `bot.leaving` / `bot.done`):**
```json
{
  "event": "bot.joining",
  "bot_event": "bot.joining",
  "bot_id": "dd451299-1471-49ae-b407-c91541242748",
  "bot_status": "Joining",
  "message": "Bot is joining the meeting",
  "status_code": 200,
  "custom_attributes": {"your_keys": "echoed back"},
  "timestamp": "2026-06-16T06:28:14.445Z"
}
```

**Terminal (bot never admitted):**
```json
{
  "event": "bot.stopped",
  "bot_event": "bot.notallowed",
  "bot_id": "...",
  "bot_status": "NotAllowed",
  "status_code": 500,
  "message": "...",
  "custom_attributes": {...},
  "timestamp": "..."
}
```

**Recording:**
```json
{
  "event": "bot.recording",
  "bot_event": "bot.recording",
  "bot_id": "...",
  "bot_status": "Recording",
  "message": "Bot started recording",
  "status_code": 200,
  "custom_attributes": {...},
  "timestamp": "..."
}
```

**`participant_events.leave`** - different shape:
```json
{
  "event": "participant_events.leave",
  "timestamp": "2026-05-26T10:11:14.990Z",
  "data": {
    "data": {
      "action": "leave",
      "participant": {
        "id": "spaces/.../devices/290",
        "name": "Unknown",
        "full_name": "Skill Audit Bot",
        "platform": "gmeet"
      },
      "timestamp": {"relative": 50.792, "absolute": "2026-05-26T10:11:14.990Z"}
    },
    "bot": {"id": "...", "metadata": {}}
  },
  "custom_attributes": {...}
}
```

**Post-call (`manifest.completed`, `audio.processed`, `transcription.processed`, `video.processed`)** - includes `timestamp` and `status`:
```json
{
  "event": "audio.processed",
  "bot_id": "...",
  "status": "success",
  "audio_status": "Success",
  "message": "Audio processing completed successfully",
  "status_code": 200,
  "custom_attributes": {...},
  "timestamp": "2026-05-26T10:11:23.018672+00:00"
}
```

**Failure (`transcription.failed`)** - `status_code: 500`:
```json
{
  "event": "transcription.failed",
  "bot_id": "...",
  "status": "error",
  "transcript_status": "Failed",
  "message": "Transcript processing error: Deepgram API error: 401",
  "status_code": 500,
  "custom_attributes": {...},
  "timestamp": "2026-05-26T10:11:25.781273+00:00"
}
```

**Terminal (`bot.done`)** - fires last:
```json
{
  "event": "bot.done",
  "bot_id": "...",
  "bot_status": "Done",
  "message": "Error: Transcript processing failed: Deepgram API error: 401",
  "status_code": 500,
  "timestamp": "2026-05-26T10:11:26.248022+00:00",
  "custom_attributes": {...}
}
```

**Data deletion** - fires after manual `DELETE /bots/{id}/delete` or retention expiry:
```json
{
  "event": "data_deletion",
  "bot_id": "...",
  "status": "success",
  "message": "Successfully deleted 7 objects for bot ...",
  "deleted_objects": 7,
  "timestamp": "2026-05-26T10:12:31.488763+00:00",
  "status_code": 200
}
```

### Delivery rules

- Every delivery sends `User-Agent: MeetStream-Webhook/1.0`.
- Webhooks from post-call processing (`manifest.completed`, `audio.processed`, `transcription.*`, `video.processed` and the other post-call events) are delivered only to URLs that resolve to public addresses, on every redirect hop. A private, loopback or metadata address is not delivered to.

### Webhook signature (optional)

Only deliveries to **workspace webhook endpoints** (added in the MeetStream dashboard with
a signing secret) are signed. Per-bot `callback_url` deliveries are **not signed**: if you
need signatures, add the URL as a workspace webhook endpoint. Signed requests include:
- `X-MeetStream-Signature: sha256=<hex>` - `HMAC-SHA256(secret, raw_body)`
- `X-MeetStream-Timestamp: <iso8601>`: an ISO 8601 UTC string such as `2026-11-19T14:30:00Z`. Parse it as a time, not as a number.

### Idempotency

Dedupe on `{bot_id, bot_event ?? event, timestamp}`. Every event carries a `timestamp` (verified on all 4,139 captured deliveries, lifecycle events included).

---
