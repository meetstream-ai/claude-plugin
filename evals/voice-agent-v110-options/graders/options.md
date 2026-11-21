---
type: llm
weight: 1
---
PASS if the reply sets `agent.chat_input: true`, `agent.speak_only_when_asked: true` (pipeline mode) and `agent.tools: ["screen"]`, and says the screen tools work on Google Meet with a model that can see images (vision-capable).
FAIL if it invents other field names for these behaviours, or says the screen works on every platform.
