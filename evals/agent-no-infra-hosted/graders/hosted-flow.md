---
type: llm
weight: 2
---
PASS if the reply gives the hosted Agents API (MIA) as track 3a (MeetStream's own, default keys): create the agent with `POST /api/v1/mia` (or in the dashboard) using MeetStream's inbuilt keys (`"key_source": "meetstream"` on the pipeline sections, no provider account; inbuilt keys cover OpenAI and Deepgram today), then send a bot with only `agent_config_id`. It says that if the API answers that MeetStream-managed keys are not available, inbuilt keys are not on for the account yet and the user continues with track 3c (bring your own keys), without retrying in a loop. Price, if given: the bot price plus $0.25 per hour for the agent infrastructure plus the models picked.
FAIL if the reply calls the own-keys fallback track 3b (3b is the coming-soon LiveKit track), presents LiveKit or a local agent as available, tells this user to run a bridge server or their own agent as the answer, requires an own provider key to start, adds `socket_connection_url` or `live_audio_required` to the agent bot, names ElevenLabs or Anthropic as inbuilt, or states a per-hour price for a specific model.
