# Errors, rate limits and validation

Moved from the core `meetstream` skill (3.3.1).

## Errors, Rate Limits and Validation

**Error body.** Most errors return `{"message": "..."}`. On the bot data endpoints (`get_audio`, `get_video`, `get_speaker_timeline`, `get_chats`, `get_participants`, screenshots), errors are `{"message": "..."}`, and so are errors from `remove_bot`, `stop_status` and `GET /bots/{bot_id}/transcriptions`. A few endpoints (in-meeting commands, the credit check, the 429 below) still send `error`. Read all shapes:

```python
def error_text(resp) -> str:
    try:
        body = resp.json()
    except ValueError:
        return resp.text
    if isinstance(body, dict):
        return body.get("message") or body.get("error") or str(body)
    return str(body)  # bare-string body
```

**Prepaid rate limit (429).** Prepaid (pay-as-you-go) accounts can create **5 bots per rolling minute and 50 per rolling hour**. Invoice accounts are not limited. Not counted: bots with `join_at` 10 minutes or more ahead, calendar bots for meetings 10+ minutes away, the scheduled join itself, and idempotent replays. Over the limit, no bot is created and the API returns:

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 37

{"error": "rate_limit_exceeded", "message": "...", "limit": 5, "window": "minute", "retry_after": 37}
```

Sleep for `Retry-After` seconds, then resend the same request (same `Idempotency-Key` or `deduplication_key` if you use one). Concurrent creates with the same key make one bot; a loser can get 409 with `Retry-After: 2` while the first request is still saving, so retry that 409 with the same key too. The SDKs (`@meetstream/sdk`, `meetstream-sdk`) retry 429 and in-progress 409 after `Retry-After` for you.

**Failed transcript (422).** `get_transcript` returns 422 with `message`, `transcript_status: "Failed"` and `transcript_id` when the run failed. It is final: never retry it. Show the reason, fix it (for example the provider key), then `POST /bots/{bot_id}/transcribe`.

**Prepaid balance.** The billing page https://app.meetstream.ai/billing shows it and adds credits. `GET /api/v1/billing/balance` (read only, API v1.10.0) may answer "not available" or 404 where it is not on yet: expected, use the billing page.

**`create_bot` requests that return 400:**

| Request | 400 message starts with |
|---|---|
| `audio_required: false` and `video_required: false` with no other job (no `realtime_endpoints`, live stream, `socket_connection_url`, `bot_message` or `agent_config_id`) | `audio_required and video_required are both false, so the bot would record nothing.` |
| Google Meet / Teams `video_separate_streams: true` without `video_required: true` | `video_separate_streams=true requires video_required=true for Google Meet and Microsoft Teams.` |
| `bot_image_url` that is not an https:// image URL (see `bot_image_url` in `skills/sending-bots/references/bot-config.md`) | `bot_image_url must be an https:// URL to a PNG, JPEG, GIF or WebP image;` |
| Zoom link with no meeting number (for example `/my/` personal links) | `invalid_meeting_link: this Zoom link has no meeting number,` |
| Zoom `meeting_captions` on a bot that uses the user's own Zoom app | `meeting_captions is not supported on Zoom.` |
| `zoom.use_own_app` not a boolean, or `false` with `zak_url` / `obf_url` | `zoom.use_own_app must be true or false` / `zoom.zak_url and zoom.obf_url cannot be used with zoom.use_own_app set to false` |
| `storage_id` not 1-80 letters, numbers, `_` or `-` | `storage_id must contain 1-80 letters, numbers, underscores or hyphens` |
| `bot_camera_stream` on another platform, a bad URL, `ws://` on Teams/Zoom, or with `agent_config_id` on Zoom | `bot_camera_stream is supported only for ...` / `... camera signaling requires wss://` / `bot_camera_stream cannot be combined with agent_config_id on Zoom` |
| `smallest` / `smallest_streaming` with an unknown `model` | `Invalid smallest model: ...` |
| `automatic_leave.recording_permission_denied_timeout` outside 60-600 | `recording_permission_denied_timeout must ...` |

A `meeting_link` that starts with `http://` is upgraded to `https://` (not a 400).

**Public addresses only.** Everything the bot or MeetStream connects to on your behalf must resolve to a public address: `callback_url` and workspace webhooks (post-call deliveries), `bot_image_url`, `send_image` / `sendimg_url` image URLs, `initial_audio.url`, and the `bot_camera_stream` signaling host. Private, loopback, link-local and cloud metadata addresses are refused at delivery or download time, usually with no 400. Use a public host or a tunnel.

Full error reference: https://docs.meetstream.ai/errors

---
