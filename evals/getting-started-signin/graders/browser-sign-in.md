---
type: llm
weight: 2
---
PASS if the reply tells the user they can start without copying an API key by signing in to the MeetStream MCP server in the browser (for example Cursor Settings, MCP, Connect; Claude Code /mcp then sign in), and asks or offers the choice of results after the meeting (recording, transcript, notes) versus something live during the call.
FAIL if the reply says an API key is required before anything works, tells the user to install an MCP server from npm or run one locally, invents setup steps, or suggests a voice agent.
