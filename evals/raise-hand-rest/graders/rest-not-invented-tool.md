---
type: llm
weight: 1
---
PASS if the reply gives the REST call POST /api/v1/bots/{bot_id}/send_command with body {"command": "raise_hand"} (for example a curl command with the Authorization: Token header) and does not claim it already raised the hand (the mock MCP server in this run has no `raise_hand` tool). Mentioning that the `raise_hand` MCP tool does it when the MCP is connected is fine.
FAIL if the reply says the bot cannot raise its hand, claims it raised the hand through a tool that does not exist, or invents a different endpoint.
