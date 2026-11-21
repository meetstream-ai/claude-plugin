---
type: llm
weight: 2
---
PASS if the reply gives an interviewer setup: an agent prompt that asks one question at a time and waits for the full answer, a `first_message` (or opening line) that says it is an AI and that the call is recorded, the agent speaks without being called by name (wake word turned off with `wake_word.enabled: false` in pipeline mode, or realtime mode; not `speak_only_when_asked`), scheduling with `join_at` or calendar auto-join, AND the recording and transcript for the hiring team (transcription.processed / get_transcript, recording or media URLs), AND it handles the flow (asks own stack or hosted once, or lists the bridge server before the hosted Agents API).
FAIL if the reply leaves a wake word or `speak_only_when_asked` on for the interviewer, adds bridge sockets to a hosted agent bot, or writes a full multi-file app.
