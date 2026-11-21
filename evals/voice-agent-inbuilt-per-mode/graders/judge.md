---
type: llm
weight: 2
---
PASS if the reply says inbuilt keys cover, in pipeline mode, OpenAI and Deepgram (Deepgram for speech-to-text, OpenAI for the LLM and the voice), and in realtime mode OpenAI only (OpenAI realtime models); any other provider needs the user's own key; tells the user to read `mia_managed` from `GET /api/v1/mia` (enabled and the sections) and use only the providers and models listed there with `"key_source": "meetstream"`, and to fall back to their own keys if a section is refused, without retrying in a loop.
FAIL if the reply names ElevenLabs, Anthropic, Google or xAI as inbuilt providers, says realtime mode has no inbuilt option at all without giving the OpenAI-only statement, or gives per-model catalog prices.
