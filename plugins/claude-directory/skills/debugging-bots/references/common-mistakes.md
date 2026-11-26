# Common mistakes

Moved from the core `meetstream` skill (3.3.1). Check this list before you guess at a cause.

## Common Mistakes

1. **Looking for `transcript_id` in the webhook** - it's not there. The webhook only signals timing. Get the `transcript_id` from the `create_bot` response, `GET /bots/{bot_id}/detail` (`bot_details.transcript_id`), or `GET /bots/{bot_id}/transcriptions`.
2. **Reading `seg["speaker"]` / `seg["transcript"]` only** - the response is a top-level array and, by default, participant-keyed: speaker `participant.name`, text `words[].text` joined. Reading only the segment-list fields prints an empty transcript (all four test harnesses hit this).
3. **`send_image` body using `image_url`** - the field is `img_url`.
4. **Fetching transcript before `transcription.processed`** - always wait for the webhook.
5. **HTTP callback URL** - must be HTTPS; use ngrok / cloudflared for local dev.
6. **Wrong calendar field names** - Calendar create requires `google_refresh_token` / `google_client_id` / `google_client_secret` (with the `google_` prefix).
7. **Turning off `audio_required` and `video_required` together** - `audio_required` (default `true`) is a real `create_bot` field. With both `false` and no other job (no `realtime_endpoints`, live stream, `socket_connection_url`, `bot_message` or `agent_config_id`), `create_bot` returns 400 because the bot would record nothing.
8. **Skipping `bot_name`** - it's required, not optional.
9. **Relying on the `video_required` default** - it defaults to `false` (audio only), but send it explicitly on every bot anyway (`false` unless the user asked to record video), so a copied example with `true` does not silently record video.
10. **Assuming `status_code` is always 200**: it's 500 for `transcription.failed` and for failing terminals (`bot.notallowed`, `bot.denied`, most `bot.failed`). Branch on `event`, then `bot_event`.
11. **Expecting webhook retries**: there are none. Always return 2xx and queue work asynchronously. Dedupe on `{bot_id, bot_event or event, timestamp}`.
12. **Using `websocket_url` for live transcription** - `live_transcription_required` accepts only `webhook_url` (HTTPS POST). The `websocket_url` field is for `live_audio_required`, `live_video_required`, and `socket_connection_url`.
13. **Sending WAV blobs over `sendaudio`** - bot expects raw PCM16 LE @ 48000 Hz mono, base64-encoded. No WAV header. Resample if your source isn't 48 kHz.
14. **`/calendar/toggle-recurring/{event_id}` path** - actual path is `POST /calendar/toggle-recurrence` with body `{event_id, recurring_enabled}`. No path param.
15. **MIA endpoint paths** - they are `/api/v1/mia` (singular) for CRUD; DELETE uses `?agent_config_id=...` query param, not a path id.
16. **Live video on Zoom** - not supported. Google Meet and Teams only.
17. **`in_call_recording_timeout` under 600** - live API rejects with HTTP 400. Minimum 600 seconds.
18. **Expecting `create_bot` to return HTTP 200** - it returns **HTTP 201 Created** (per OpenAPI and live-verified). `status` field is typically `"Active"`.
19. **Expecting a post-call transcript from a streaming-only provider** - streaming providers (`meetstream_streaming`, `assemblyai_streaming`, `deepgram_streaming`, `jigsawstack_streaming`, `smallest_streaming`, `meeting_captions`) return `transcript_id: null` and never populate `bot_details.transcript_id` or `/transcriptions`. The audio is saved but no transcript exists until you manually call `POST /bots/{bot_id}/transcribe`.
20. **Waiting for `transcription.processed` on a streaming-only bot**: it never fires for Path B. Use `bot.done`, which fires on both paths, as the "session finished" signal.
25. **Branching on `event == "bot.kicked"` or `"bot.notallowed"`**: those names only appear in `bot_event`. Every terminal's `event` is `bot.stopped`.
21. **Treating `bot.error` as a fatal event** - it's only a streaming-provider warning (upstream auth issue). The bot continues recording; only live transcription is impacted.
22. **Waiting for `bot.done` after `/transcribe`** - `/transcribe` is fire-and-forget. You get exactly one `transcription.processed`/`transcription.failed`, no `bot.done` follow-up.
23. **Relying on `custom_attributes` in `/transcribe`-triggered webhooks** - that field is missing from `/transcribe` events (present on original lifecycle events). Correlate by `bot_id` instead.
24. **Retrying a 422 or polling `/transcript/{tid}/get_transcript` without a bound** - a failed run returns 422 with the reason (final, do not retry); a streaming-only bot returns 202 forever. Cap every polling loop, and check `bot_details.TranscriptStatus` (`"Success"`/`"Failed"`/`None`) or the `transcription.failed` webhook.
25. **Sharing one Teams account across concurrent signed-in bots** - Teams allows one bot per account at a time; extra bots get 409/429. Register one account per concurrent bot. Also don't expect `bot_name` / `bot_image_url` to apply on a signed-in Teams join: the Microsoft account's name and picture are used.
26. **Using PUT or `GET /google-logins/{id}` for Google logins** - updates are PATCH (with `domain` in the body), deletes need `?domain=`, and there is no GET-by-id.
27. **Turning video on without a layout** - the API default is `grid_view`. Whenever `video_required: true`, send `recording_config.video_layout: "speaker_view"` unless the user explicitly asked for grid or gallery view. `"speaker_view"` and `"grid_view"` work on Google Meet, Teams and Zoom; Google Meet and Teams also accept `"speaker_view_default"` / `"grid_view_default"` (Zoom returns 400 for them); the field is ignored when video is off; WhatsApp accepts only `"grid_view"`.
28. **Setting `video_separate_streams` because it looked useful** - per-participant video is opt-in only. Never set it unless the user explicitly asked for per-participant video streams. Per-participant `audio_separate_streams` is not affected by this rule. On Google Meet and Teams it also needs `video_required: true`, else 400.
29. **Sending `raise_hand` before the bot is in the meeting** - `send_command` hand commands return 409 while the bot is joining or in the lobby. Wait for `bot.inmeeting`. Read `hand_raised` from the response; it is the real state in the meeting, not an echo.
30. **Waiting for hand events on the workspace webhook** - `participant_events.raise_hand` / `.lower_hand` go only to `recording_config.realtime_endpoints` entries that list them.
31. **Saying Zoom needs no setup** - recommend the user's own Zoom app for reliable, fully supported Zoom bots: they join through it with an OBF or a ZAK token, the way Zoom asks Meeting SDK apps to join since 2 March 2026. Without it, only a limited US-only fallback joins (no OBF or ZAK, no per-participant camera video). Never combine `use_own_app: false` with `zak_url` / `obf_url` (400). There is no fallback when Zoom refuses the user's app.
32. **Parsing `get_speaker_timeline` as the timeline every time** - large timelines return `{speaker_timeline_url, size_bytes, truncated}` instead. Check for `speaker_timeline_url` and download it (no API key, valid 1 hour).
33. **Reading only `error` from an error body** - most errors are `{"message": "..."}`, and remove_bot / stop_status / transcriptions errors moved from `error` to `message`. Read `message`, then `error`, then fall back to the raw text.
34. **Retrying `create_bot` in a tight loop on 429** - prepaid accounts get 5 creates per minute and 50 per hour. Sleep for the `Retry-After` seconds and resend with the same `Idempotency-Key` / `deduplication_key`.
35. **Pointing `callback_url`, `bot_image_url`, image URLs or `bot_camera_stream` at a private address** - they must resolve to public addresses. Private, loopback and metadata addresses are refused at delivery or download time, usually with no 400.
36. **Using Anthropic Claude as a transcription provider** - Claude is a MIA LLM (`model.provider: "anthropic"` in `POST /api/v1/mia`, pipeline mode). It is not a `recording_config.transcript.provider` key.

---
