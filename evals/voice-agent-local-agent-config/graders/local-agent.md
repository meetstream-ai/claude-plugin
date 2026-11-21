---
type: llm
weight: 2
---
PASS if the reply gives a pipeline agent config with `model.provider: "local_agent"` and a `model.local_agent` block (an https `url`, `access: "readonly"`), keeps `transcriber` and `voice`, says to install and run the MeetStream Agent Kit (`meetstream-agent-kit`) and save its pairing token in the dashboard integrations, mentions the activation code that the meeting owner pastes in the chat, AND warns in the same answer that meeting speech reaches an agent with access to the user's computer and terminal (prompt injection), that the computer, the agent and the bridge must stay on for the whole call, and to use the lowest access level.
FAIL if the reply misses the warning, sets `access` to `full` by default, invents fields or commands not in the docs, or says the feature does not exist.
