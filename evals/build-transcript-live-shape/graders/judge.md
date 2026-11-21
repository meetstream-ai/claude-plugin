---
type: llm
weight: 2
---
PASS if the code reads the participant-keyed format (each segment's speaker from `participant.name`, the text by joining `words[].text`), and either also handles the segment-list format (`speaker` and `transcript`) or says the participant-keyed format is the default. A note about skipping empty or filler segments (for example a lone "Thank you." on silence) is a plus, not required.
FAIL if the code reads only `segment["speaker"]` and `segment["transcript"]` (or `text`) with no `participant`/`words` handling, or expects a `{"transcript": [...]}` wrapper.
