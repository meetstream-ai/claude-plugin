---
type: llm
weight: 2
---
PASS if the reply says WhatsApp calls are supported in Beta and must be enabled for the workspace, the user pairs a WhatsApp number in the dashboard under Integrations > WhatsApp (optionally `whatsapp.account_id`), the bot gets a WhatsApp call link (call.whatsapp.com/video|voice/<token> or web.whatsapp.com/call/...), post-call transcription is `deepgram` only, and per-participant audio, chat and captions are not available; then the minutes come from the transcript summarized by the user's own model and sent with the user's own channel.
FAIL if the reply says WhatsApp is not supported, uses `meetstream` transcription for the WhatsApp bot, promises chat or per-speaker files on WhatsApp, or suggests a voice agent.
