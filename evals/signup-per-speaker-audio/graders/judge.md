---
type: llm
weight: 2
---
PASS if the reply sends the bot with `audio_separate_streams: true` and `video_required: false`, waits for `audio.processed`, then calls `GET /api/v1/bots/{bot_id}/get_audio_streams` and downloads each `download_url` (links last 1 hour; call again for fresh links; WebM/Opus, optional MP3 with `audio_separate_mp3`), notes up to 16 speakers and that Teams separates speakers from one mixed track so overlapping speech goes to one speaker, AND notes the Zoom bot joins through the user's Zoom app (OBF or ZAK).
FAIL if the reply turns on per-participant video, invents endpoints, says Zoom needs no setup, or suggests a voice agent.
