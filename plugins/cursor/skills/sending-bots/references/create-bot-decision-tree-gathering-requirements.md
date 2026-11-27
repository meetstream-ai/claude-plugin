# create_bot decision tree: Gathering Requirements

> Part of [`create-bot-decision-tree.md`](create-bot-decision-tree.md), split so each file stays under 20 KB.

## Gathering Requirements

Start with the fastest path. When the user builds a production config, **walk the [Bot Configuration Decision Tree](#bot-configuration-decision-tree) section below in order**. Don't just ask the 4 top-level questions and guess defaults for everything else - the decision tree covers every field that affects behavior and cost.

Quick top-level questions to start with:
1. **Sign-in** - the MCP or `meetstream login`; app code keeps its key (created at https://app.meetstream.ai/api-keys) in its own secret store. Never ask for the key in the chat.
2. **Platform** - Google Meet, Teams, Zoom, or all? (recommend the user's own Zoom app with OBF or ZAK for reliable Zoom; see `setting-up-platforms`)
3. **Language** - Python or Node.js/TypeScript?
4. **Use case** - match to one of the patterns below

Then **walk Steps 1–8 of the decision tree** to fill in:
- Bot identity (name, avatar, message, video/audio config) - Step 1
- Platform-specific setup (Google / Teams signed-in, Zoom ZAK/OBF) - Step 2
- Transcription strategy (none / live / post-call / both) - Step 3
- Live transcription provider + webhooks - Step 4A
- Post-call transcription provider - Step 4B
- Hybrid (live + post-call via `/transcribe`) - Step 4C
- Participant events, interactive bot, agent in the meeting (only if asked) - Step 5
- Scheduling (now / future / calendar auto) - Step 6
- Custom metadata for routing/billing - Step 7
- Timeouts - Step 8

Each step's branch produces one or more fields in the final `create_bot` payload. Don't guess defaults - ask.

---

## Bot Configuration Decision Tree

Walk the user through these questions in order. Each answer pins down one field in the final `create_bot` payload. At the end, you'll have a complete, correct request body tailored to their use case.

> When the user is vague ("I want a meeting bot"), DO NOT guess defaults - actually walk them through this tree. The API defaults are not always what they want (e.g. `video_layout` defaults to `grid_view`, and the default retention may be longer or shorter than their policy). The one thing you do not need to ask about is the recording defaults above: video off unless the user mentioned video, speaker view when video is on, per-participant video only on request.

---

### STEP 1 - Bot identity (who is this bot in the meeting?)

```
Q1.1: What should the bot be called inside the meeting? [REQUIRED]
      └─→ "bot_name": "Acme Notetaker"     (visible to all participants)

Q1.2: Should it post a welcome message in the meeting chat on join?
      ├─ Yes → "bot_message": "Hi! I'm an AI notetaker recording this call."
      └─ No  → omit bot_message

Q1.3: Custom avatar / profile picture?
      ├─ Yes → "bot_image_url": "https://your-cdn.com/avatar.png"
      │        • MUST be a public https:// URL to a PNG, JPEG, GIF or WebP
      │          (no auth, no signed URLs, must resolve to a public address)
      │        • http:// and data: URIs return HTTP 400
      │        • Host it on S3 / Cloudflare R2 / public CDN
      └─ No  → omit bot_image_url

Q1.4: Did the user ask to record the meeting VIDEO file (archive, playback)?
      ├─ Yes → "video_required": true   → continue to Q1.4a for the layout
      └─ No  → "video_required": false  (DEFAULT for everything we build)
               • send it explicitly (the API default is also false, but an
                 explicit value keeps the intent visible)
               • saves storage + bandwidth; audio is still captured, and
                 transcript, summary, diarization and speaker timeline
                 all work without video

Q1.4a: (only when video_required is true) Which layout?
      ├─ User explicitly asked for grid / gallery
      │       → "recording_config": { "video_layout": "grid_view" }
      └─ Anything else
              → "recording_config": { "video_layout": "speaker_view" }  (RECOMMENDED)
               • the API default is "grid_view", so speaker view must be sent
               • "speaker_view" and "grid_view" work on Google Meet, Teams, Zoom;
                 Google Meet and Teams also take "speaker_view_default" /
                 "grid_view_default" (the platform's own in-call layout)
               • ignored when video_required is false
               • WhatsApp is grid only

Q1.5: Want per-participant audio tracks (one file per speaker)?
      ├─ Yes → "audio_separate_streams": true
      │        • Google Meet + Zoom only (NOT Teams)
      │        • Up to 16 concurrent speakers
      │        • Each track: WebM/Opus, 48kbps, 48kHz mono
      └─ No  → omit (default false; you get one mixed audio file)

Q1.6: Did the user EXPLICITLY ask for per-participant video tracks
      (one webcam stream per person)?
      ├─ Yes → "video_separate_streams": true
      │        • All 3 platforms
      │        • Google Meet + Teams: needs "video_required": true, else HTTP 400
      │        • Up to 6 concurrent webcams
      │        • WebM/VP8, 15 FPS, video-only
      └─ No  → omit (you get one composite video). Never set this implicitly:
               it multiplies storage and processing per participant.
               Per-participant AUDIO (Q1.5) is not affected by this rule.
```

> `audio_required` exists on `create_bot` (default `true`). Do not set it to `false` unless the bot has another job: `audio_required: false` with `video_required: false` and nothing else to do returns 400 ("the bot would record nothing").

---

### STEP 2 - Meeting platform

```
Q2.1: Which platform is the meeting on?
      ├─ Google Meet → "meeting_link": "https://meet.google.com/abc-defg-hij"
      │                continue Q2.2 (signed-in?)
      ├─ Microsoft Teams → "meeting_link": "https://teams.microsoft.com/l/meetup-join/..."
      │                    continue Q2.4 (signed-in?)
      └─ Zoom → "meeting_link": "https://zoom.us/j/123456789?pwd=..."
                continue Q2.3 (optional Zoom join type)

Q2.2: (Google Meet) Does the meeting require a signed-in Google identity?
      ├─ Yes → "google_meet": {
      │           "login_required": true,
      │           "google_login_domain": "your-company.com",
      │           "sign_in_email": "bot@your-company.com",   // optional: pin one account
      │           "strict_email": true                        // optional, default true
      │        }
      │        ⚠ Prerequisite: SSO + login cert registration via
      │        /google-login-domains and /google-logins. See Google Signed-In
      │        Bots section. Without this setup the bot will fail to join.
      └─ No  → omit google_meet (works for public Meet rooms)

Q2.3: (Zoom) How does the bot join through the user's Zoom app?
      Zoom bots join through the user's Zoom app with an OBF or a ZAK token,
      the way Zoom asks Meeting SDK apps to join since 2 March 2026. The user
      saves their Zoom Meeting SDK app in Dashboard > Integrations > Zoom (or
      connects their Zoom app and users) once.
      ├─ Joining as a signed-in Zoom user (ZAK)
      │  → "zoom": { "zak_url": "https://you.example.com/zoom/zak" }
      ├─ Joining On Behalf Of a user already in the meeting (OBF)
      │  → "zoom": { "obf_url": "https://you.example.com/zoom/obf" }
      │     Both URLs are HTTPS endpoints on YOUR server that return a fresh
      │     token when MeetStream calls them. Guide:
      │     https://docs.meetstream.ai/guides/app-integrations/zoom-authenticated-bots
      └─ Force the user's Zoom app → "zoom": { "use_own_app": true }
         (400 if no app is configured)
         Never write that Zoom needs no setup or that no Zoom app is needed.
         ⚠ zak_url and obf_url need the user's Zoom app, and cannot be
           combined with "use_own_app": false (HTTP 400).
         ⚠ Zoom links with no meeting number (for example /my/ personal
           links) return HTTP 400 invalid_meeting_link.
         ⚠ use_zoom_obf and zoom_oauth_connection_user_id are rejected by the
           API. Use zak_url / obf_url instead.

Q2.4: (Teams) Does the meeting block anonymous/guest join, or must the bot
      appear as a real Microsoft 365 user?
      ├─ Yes → "teams": {
      │           "login_required": true,
      │           "teams_login_domain": "bots.your-company.com",
      │           "sign_in_email": "bot1@bots.your-company.com", // optional
      │           "strict_email": true                            // optional, default true
      │        }
      │        ⚠ Prerequisite: a dedicated M365 tenant + accounts registered via
      │        /teams-login-domains and /teams-logins. ONE concurrent bot per
      │        account. Name/avatar come from the Microsoft account (bot_name and
      │        bot_image_url are ignored). See Microsoft Teams Signed-In Bots.
      └─ No  → omit teams (guest join; works when anonymous join is allowed)
```

---

### STEP 3 - Do you need a transcript? (this is the biggest decision)

```
Q3.1: Will any part of the system consume a transcript?
      ├─ No (audio-only, e.g. recording for human listening later)
      │  → Skip Steps 4 & 5 entirely. You can still call /transcribe later
      │    if you change your mind (audio is saved either way).
      └─ Yes → continue Q3.2

Q3.2: WHEN do you need the transcript?
      ├─ During the meeting (live captions, real-time AI coach, live dashboard)
      │  → STEP 4A (LIVE)
      ├─ After the meeting (summaries, CRM updates, archives)
      │  → STEP 4B (POST-CALL)
      └─ Both (live captions in the UI + complete transcript post-call)
         → STEP 4C (HYBRID - use streaming live + /transcribe after)
```

---

### STEP 4A - Live transcription path

```
Q4A.1: Where should live chunks be POSTed?
       → "live_transcription_required": { "webhook_url": "https://you/live" }
         (HTTPS, NOT a WebSocket; bot POSTs JSON chunks here every ~250ms)

Q4A.2: Which streaming provider?
       ├─ "I don't have any provider API keys" (most accounts)
       │  → "recording_config": {
       │       "transcript": { "provider": { "meetstream_streaming": {} } }
       │     }
       │     ✅ Free, no external key needed, works out of the box
       │     ✅ Returns speaker names from the meeting
       │     ❌ confidence/speech_confidence values are 0 (no per-word ML scores)
       │
       ├─ "I have a Deepgram account" (best for accuracy)
       │  → provider: {
       │       "deepgram_streaming": {
       │         "transcription_mode": "sentence",
       │         "model": "nova-2",
       │         "language": "en",
       │         "punctuate": true,
       │         "smart_format": true,
       │         "endpointing": 300,
       │         "vad_events": true,
       │         "utterance_end_ms": 1000,
       │         "encoding": "linear16",
       │         "channels": 1
       │       }
       │     }
       │     ⚠ ALL fields required per OpenAPI. Account needs Deepgram key.
       │
       ├─ "I have an AssemblyAI account"
       │  → provider: {
       │       "assemblyai_streaming": {
       │         "transcription_mode": "raw",
       │         "sample_rate": 48000,
       │         "speech_model": "universal-streaming-english",
       │         "format_turns": false,
       │         "encoding": "pcm_s16le",
       │         "vad_threshold": "0.4",
       │         "end_of_turn_confidence_threshold": "0.4",
       │         "inactivity_timeout": 300,
       │         "min_end_of_turn_silence_when_confident": "400",
       │         "max_turn_silence": "1280"
       │       }
       │     }
       │     ⚠ English-only. Account needs AssemblyAI key.
       │
       ├─ "I have an Interfaze (formerly JigsawStack) account"
       │  → provider: { "jigsawstack_streaming": {} }
       │     Account needs Interfaze key.
       │
       ├─ "I have a Smallest AI account"
       │  → provider: {
       │       "smallest_streaming": { "model": "pulse", "language": "en" }
       │     }
       │     • model: "pulse" (default) or "pulse-2" (English only)
       │     • Key saved in the dashboard under voice integrations (Smallest AI);
       │       without it: HTTP 400 "SmallestAPIKey not configured in user profile"
       │
       └─ "Just use the meeting's built-in captions" (Google Meet / Teams)
          → provider: { "meeting_captions": {} }
            ✅ Free, no provider needed at all
            ❌ Quality depends on the meeting platform's own captions
            ⚠ Zoom: only for bots that join WITHOUT the user's own Zoom app.
              With the user's Zoom app it returns HTTP 400.

Q4A.3: Need to also stream raw audio bytes (for your own ML model)?
       ├─ Yes → "live_audio_required": { "websocket_url": "wss://you/audio" }
       │        See Pattern 7 - binary frames over WebSocket, raw PCM16
       │        LE @ 48kHz mono with embedded speaker metadata.
       └─ No  → omit live_audio_required

Q4A.4: Need live video frames out of the meeting?
       └─ Not available on meeting bots: omit live_video_required (bots ignore it
          and it moves the bot to the larger video tier). Only Zoom Meeting Direct
          Connect (RTMS) sessions stream video (see setting-up-platforms).

⚠ KEY LIMITATION OF STREAMING: No automatic post-call transcript.
   transcript_id will be null in the create_bot response.
   bot_details.transcript_id stays null.
   /transcriptions list is empty.
   You MUST manually call POST /bots/{bot_id}/transcribe after the meeting
   if you also want a post-call transcript (that's Step 4C).
```

---

### STEP 4B - Post-call transcription path

```
Q4B.1: Where should webhooks be delivered? [STRONGLY RECOMMENDED]
       → "callback_url": "https://you/webhook"
         You'll receive bot.joining → [bot.in_waiting_room] → bot.inmeeting → bot.recording → bot.leaving
         → bot.stopped → manifest.completed → audio.processed →
         transcription.processed → bot.done (full Path A lifecycle).
         Without callback_url you'd have to poll /bots/{id}/status repeatedly.

Q4B.2: Which post-call provider?
       ├─ "I don't have external keys, want lowest setup"
       │  → "recording_config": {
       │       "transcript": {
       │         "provider": {
       │           "meetstream": { "language": "en", "translate": false }
       │         }
       │       }
       │     }
       │     MeetStream in-house post-call. May require provider key in account.
       │
       ├─ "I want highest accuracy English" (most popular choice)
       │  → provider: { "deepgram": { "model": "nova-3", "language": "en" } }
       │     ⚠ Account needs Deepgram key. nova-3 is the only model enum.
       │
       ├─ "I want speaker diarization + PII redaction"
       │  → provider: {
       │       "assemblyai": {
       │         "speech_models": ["universal-2"],
       │         "language_code": "en_us",
       │         "speaker_labels": true,
       │         "punctuate": true,
       │         "format_text": true,
       │         "filter_profanity": false,
       │         "redact_pii": false,
       │         "auto_chapters": false,
       │         "entity_detection": false
       │       }
       │     }
       │     ⚠ 9 fields marked required per OpenAPI. Account needs AssemblyAI key.
       │
       ├─ "I have a Smallest AI account"
       │  → provider: {
       │       "smallest": { "model": "pulse", "language": "en", "diarize": true }
       │     }
       │     • model: "pulse" (default) or "pulse-pro" (English only)
       │     • diarize applies to "pulse" only (default true). Optional:
       │       keywords, redact_pii, redact_pci, emotion_detection,
       │       gender_detection
       │     • language is not checked at create time; a bad code arrives
       │       as transcription.failed
       │     Account needs a Smallest AI key (voice integrations).
       │
       ├─ "Indic languages (Hindi/Tamil/Telugu/etc.)"
       │  → provider: {
       │       "sarvam": {
       │         "model": "saaras:v3",
       │         "language_code": "en-IN",
       │         "mode": "transcribe",
       │         "with_diarization": true
       │       }
       │     }
       │     Account needs Sarvam key.
       │
       └─ "Auto-detect language + translate to English"
          → provider: {
              "jigsawstack": {
                "language": "auto",
                "translate": false,
                "by_speaker": true
              }
            }
            Account needs Interfaze key.

Q4B.3: How long should MeetStream keep the audio/transcript?
       ├─ Kept permanently (default if you omit retention)
       ├─ Custom window → "retention": { "type": "timed", "hours": 168 }  (7 days)
       └─ Per compliance policy → set the smallest window that meets your needs.
                                  After that, data is auto-deleted and
                                  data_deletion webhook fires.

✅ The transcript will be auto-fetched-able via the canonical flow:
   1. Wait for transcription.processed webhook
   2. GET /bots/{bot_id}/detail → bot_details.transcript_id
   3. GET /transcript/{transcript_id}/get_transcript
   No /transcribe call needed (Path A, the standard workflow).
```

---
