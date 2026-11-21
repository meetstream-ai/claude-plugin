---
type: llm
weight: 2
---
PASS if the reply says the bot joins Zoom through the user's own Zoom app (a Zoom Meeting SDK app whose credentials are saved in the MeetStream dashboard under Integrations > Zoom, or a connected Zoom app) with an OBF token (on behalf of a user who is in the meeting) or a ZAK token (a signed-in bot), the way Zoom asks Meeting SDK apps to join since 2 March 2026.
FAIL if the reply says Zoom needs no setup, that no Zoom app, SDK keys, OAuth or tokens are needed, that the Zoom app is optional, recommends joining without the user's Zoom app (`zoom.use_own_app: false`) as the way to start, or mentions `zoom.variant`.
