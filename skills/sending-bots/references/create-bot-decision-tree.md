# create_bot decision tree

Moved from the core `meetstream` skill (3.3.1). Walk these steps in order when you build a production `create_bot` config.

## Parts

This reference is split into files under 20 KB. Open the part you need:

- [`create-bot-decision-tree-gathering-requirements.md`](create-bot-decision-tree-gathering-requirements.md): Gathering Requirements; Bot Configuration Decision Tree; STEP 1 - Bot identity (who is this bot in the meeting?); STEP 2 - Meeting platform; STEP 3 - Do you need a transcript? (this is the biggest decision); STEP 4A - Live transcription path; STEP 4B - Post-call transcription path
- [`create-bot-decision-tree-step-4c-hybrid-live-post.md`](create-bot-decision-tree-step-4c-hybrid-live-post.md): STEP 4C - Hybrid (live + post-call); STEP 5 - Other webhooks (beyond transcription); STEP 6 - Scheduling; STEP 7 - Metadata for routing/billing; STEP 8 - Timeouts (use these defaults unless you have a reason not to); Final assembly - your complete `create_bot` payload
