---
type: llm
weight: 2
---
PASS if the reply says pipeline agents start with a wake word turned on by default (for example "hey assistant", "hello bot"), so the agent only answers after the wake word; the fix is `"wake_word": {"enabled": false}` (or say the wake word or the agent's name), AND it says commands such as `update_mia` need the bot to be `InMeeting` first (wait for the `bot.inmeeting` event or the status, then send; retry a 503 a few times with a pause).
FAIL if the reply blames only the provider keys or the transcriber without naming the default wake word, or tells the user to add the bridge sockets to the hosted agent bot.
