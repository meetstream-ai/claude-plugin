---
type: llm
weight: 2
---
PASS if the reply gives the fastest path as a few numbered steps with the minimal MeetStream calls (create the bot with the meeting link and a webhook or callback URL, wait for the transcript event, fetch the transcript, summarize in the user's app), shows at least one short copy-paste request (curl, `@meetstream/sdk` or `meetstream-sdk`), and points to the docs tutorials and sample apps as an optional reference.
FAIL if the reply writes or proposes a full multi-file application (project tree, framework server, email delivery layer, Dockerfile) as the answer, asks more than one question before giving the path, or suggests a voice agent.
