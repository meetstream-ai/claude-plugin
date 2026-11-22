---
type: llm
weight: 2
---
PASS if the reply asks one main question before building: does the user want to run their own stack (a bridge server that receives the meeting audio and runs any speech-to-text, LLM and voice models, including local ones, for the bot price only), or let MeetStream host the agent (the Agents API, MIA, with MeetStream's inbuilt keys or their own provider keys, bot price plus $0.25 per hour plus the models)? The own-stack (bridge) option is listed first. It may also say that using their own agent (Claude Code, Codex and others) through the Agent Kit is coming soon.
FAIL if the reply goes straight to a hosted agent config (`POST /api/v1/mia`, `key_source`) without offering the bridge, lists the hosted Agents API before the bridge, asks several unrelated questions first (wake words, modes, providers), or presents the user's own local agent or LiveKit as available now. MeetStream's own hosted audio bridge ("MeetStream hosts the bridge, you host nothing") is not the bridge server and does not count.
