---
type: llm
weight: 2
---
PASS if the reply gives a concrete agent setup for the standup job: name gating with `agent.speak_only_when_asked: true` and/or `wake_word` with the agent's name as the trigger words (pipeline mode, not realtime), a system prompt or first message shaped for a standup (for example go round, keep it short, capture decisions and blockers), AND a post-call step that gets the transcript (transcription.processed / get_transcript) and has the user's own code or model extract decisions and post them with the user's own Slack integration, AND it handles the flow: either it asks once whether to run their own stack (bridge server) or let MeetStream host it, or it lists the bridge server option before the hosted Agents API.
FAIL if the reply puts a wake word on a realtime-mode agent, says MeetStream posts to Slack by itself, adds `socket_connection_url` or `live_audio_required` to a hosted agent bot, or recommends the hosted Agents API over the bridge without the user saying they want no infrastructure work.
