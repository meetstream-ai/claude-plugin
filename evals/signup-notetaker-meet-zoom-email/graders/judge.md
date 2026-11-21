---
type: llm
weight: 2
---
PASS if the reply gives the post-call notetaker path in a few steps (create_bot with the meeting link and a webhook or callback URL, wait for transcription.processed, fetch the transcript, summarize with the user's own model, send the email with the user's own email provider), AND says that before the first Zoom bot the user sets up their own Zoom app (Meeting SDK credentials in the dashboard, or a connected Zoom app) and that the bot joins Zoom with an OBF or ZAK token, AND says the host or someone in the meeting must admit the bot from the waiting room (or names waiting_room_timeout / a NotAllowed or Denied outcome), AND says where the invitee emails come from (the calendar invite: `calendar_email` on participants when a calendar is connected, or the user's own calendar or invite data), AND offers calendar auto-join as the next step.
FAIL if the reply says Zoom needs no setup or that the Zoom app is optional, claims MeetStream sends the email itself, writes a full multi-file app, or suggests a voice agent.
