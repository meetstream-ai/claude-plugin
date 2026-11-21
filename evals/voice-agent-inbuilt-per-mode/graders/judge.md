---
type: llm
weight: 2
---
PASS if the reply says inbuilt keys work in pipeline mode only, with Deepgram for speech-to-text and OpenAI for the LLM and the voice; that realtime mode runs on OpenAI and needs the user's own OpenAI key (no inbuilt key in realtime; the API answers "MeetStream-managed keys are available only in pipeline mode."); that any other provider needs the user's own key; and tells the user to read `mia_managed` from `GET /api/v1/mia` (enabled and the sections), use only the providers and models listed there with `"key_source": "meetstream"`, and fall back to their own keys if a section is refused, without retrying in a loop.
FAIL if the reply says realtime mode can use MeetStream's inbuilt keys, names ElevenLabs, Anthropic, Google or xAI as inbuilt providers, or gives per-model catalog prices.
