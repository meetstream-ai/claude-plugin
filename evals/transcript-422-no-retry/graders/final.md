---
type: llm
weight: 2
---
PASS if the reply says a 422 from `get_transcript` is final (the transcript run failed; the body gives the status and the reason), so the code stops retrying on 422 and surfaces the `message`; it keeps polling only on 202 (still processing) and backs off only on 429 or 5xx; and to recover, the user fixes the cause (here the provider key) and then starts a new transcription (for example `POST /api/v1/bots/{bot_id}/transcribe`) instead of retrying the same call.
FAIL if the reply keeps retrying 422 (with or without backoff), treats it as a temporary server error, or invents endpoints.
