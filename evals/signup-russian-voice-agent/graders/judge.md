---
type: llm
weight: 2
---
PASS if the reply gives a voice agent setup in Russian: pipeline mode with `transcriber.language` set to `ru` (or `multi`), a system prompt that tells the agent to answer in Russian, a voice that can speak Russian (for example a multilingual model), name gating with `speak_only_when_asked: true` or a wake word with Russian name variants, AND the end-of-meeting decisions summary (from the transcript after the call with the user's own model, or the agent asked at the end), AND it says the Zoom bot joins through the user's Zoom app with OBF or ZAK, AND it handles the flow (asks own stack or hosted once, or lists the bridge server before the hosted Agents API).
FAIL if the reply leaves the transcriber language at `en`, puts a wake word on a realtime agent, says Zoom needs no setup, or adds bridge sockets to a hosted agent bot.
