---
type: llm
weight: 2
---
PASS if the decoder reads byte 0 and handles both `0x01` (48 kHz mono, speaker fields at offset 1) and `0x04` (sample rate as 4-byte little-endian at bytes 1-4, channel count at byte 5, speaker fields at offset 6) for a Google Meet bot, skips unknown types, and the echo paragraph does not rely only on filtering the bot's own speaker name (Google Meet can tag audio `NoSpeaker`): it uses timing or the bridge's own playback state (for example ignore input while sending audio).
FAIL if the decoder assumes Google Meet sends only `0x01` frames or drops `0x04` frames on Meet, or if the only echo guard is skipping frames whose speaker name equals the bot name.
