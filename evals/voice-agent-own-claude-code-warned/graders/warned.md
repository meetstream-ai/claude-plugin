---
type: llm
weight: 2
---
PASS if the reply says yes, through the MeetStream Agent Kit (a bridge on the user's computer plus a tunnel, so their own agent writes what the voice agent says), AND warns that people in the meeting can try to make the agent run commands or read files on their computer (prompt injection), AND advises the least access (for example read-only) and that the computer and agent must stay running for the whole meeting. It may mention the bridge server (own stack, any models, bot price only) or the hosted Agents API as the other ways to run an agent.
FAIL if the reply says it is not possible, steers only to an Anthropic API key, misses any of the warnings, or invents command-line flags presented as required steps.
