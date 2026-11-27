# MeetStream API Reference

Base URL: `https://api.meetstream.ai/api/v1`
Auth: `Authorization: Token YOUR_API_KEY`

## Parts

This reference is split into files under 20 KB. Open the part you need:

- [`api-reference-bot-endpoints.md`](api-reference-bot-endpoints.md): Bot Endpoints; POST `/bots/create_bot`; GET `/bots/{bot_id}/status`; GET `/bots/{bot_id}/detail`; ~~GET `/bots/{bot_id}/summary`~~ (not available); GET `/bots/{bot_id}/get_audio`; GET `/bots/{bot_id}/get_video`; GET `/bots/{bot_id}/get_audio_streams`; GET `/bots/{bot_id}/get_recording_streams`; GET `/bots/{bot_id}/get_speaker_timeline`; GET `/bots/{bot_id}/get_chats`; GET `/bots/{bot_id}/screenshots`; GET `/bots/{bot_id}/get_participants`; POST (or GET) `/bots/{bot_id}/remove_bot`; DELETE `/bots/{bot_id}/delete`; GET `/bots`; POST `/bots/{bot_id}/send_message`; POST `/bots/{bot_id}/send_image`; POST `/bots/{bot_id}/pause_recording`; POST `/bots/{bot_id}/resume_recording`; POST `/bots/{bot_id}/send_command`; POST `/bots/{bot_id}/update_mia`
- [`api-reference-post-bots-bot-id-transcribe.md`](api-reference-post-bots-bot-id-transcribe.md): POST `/bots/{bot_id}/transcribe`; Transcription Endpoints; Calendar Endpoints; Google Signed-In Bot Endpoints; Microsoft Teams Signed-In Bot Endpoints
- [`api-reference-mia-meetstream-infrastructure-agents-endpoints.md`](api-reference-mia-meetstream-infrastructure-agents-endpoints.md): MIA (MeetStream Infrastructure Agents) Endpoints; Webhook Events (sent to `callback_url`)
- [`api-reference-recording-config-schema.md`](api-reference-recording-config-schema.md): `recording_config` Schema; `automatic_leave` Schema - Recommended Defaults; Errors and Rate Limits; Live Transcription Webhook Payload; WebSocket Control Commands; Live Audio Binary Frame Format; Live video (not available on meeting bots)
