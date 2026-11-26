---
name: setting-up-platforms
description: >
  Platform-specific setup and quirks for Zoom, Google Meet, Microsoft Teams
  and WhatsApp calls (Beta). Supported: those four; Webex, Slack huddles and
  other services return 400. Use when the user says "the bot can't join Zoom", "waiting room",
  "the host has to admit it", "recording permission", "Zoom setup", "do I need a Zoom app", "OBF",
  "use_own_app", "signed-in bots", "the bot shows as guest", "Teams lobby",
  "meeting access is restricted", "sign in required", "WhatsApp", "webinar", "Zoom app
  review", "Zoom OAuth app", "record Zoom without a bot" (Direct Connect, RTMS), or hits a
  platform-specific failure rather than an API error. Formerly platform-setup.
---

# Platform setup and quirks

Most "the bot didn't join" reports are platform behaviour, not API failures. Diagnose
from the terminal webhook first: every ending arrives with `event: "bot.stopped"`, and
**`bot_event`** says why.

| `bot_event` | Meaning | Fix |
|---|---|---|
| `bot.notallowed` | Sat in the waiting room until timeout | Have someone admit it, raise `waiting_room_timeout`, or use a signed-in bot |
| `bot.denied` | A host actively refused it | Human decision. Do not auto-retry |
| `bot.kicked` | A participant removed it | Human decision. Do not auto-retry |
| `bot.failed` | Join failed or the session crashed | Read `ErrorReason` (below); otherwise create a fresh bot |

`bot.failed` carries a specific reason in `bot_details.ErrorReason` (REST `GET /bots/{bot_id}/detail`).
Google Meet `bot.failed` webhooks also carry it as `failure_reason`. Treat unknown values as a generic failure.

| `ErrorReason` | Platform | Meaning | Fix |
|---|---|---|---|
| `MeetingRestricted` (`meeting_restricted`) | Google Meet, Teams | The meeting admits only the host's organization or invitees | Signed-in bot from an allowed domain/tenant, or ask the organizer to allow the bot |
| `SignInRequired` (`sign_in_required`) | Google Meet, Teams (new on Teams) | The meeting does not accept anonymous guests | Google or Teams signed-in bot |
| `InvalidMeetingLink` (`invalid_meeting_link`) | Google Meet, Teams (new on Teams) | Broken, cut-off or non-meeting link | Copy the full join link from the invite |

Reference: https://docs.meetstream.ai/guides/reference/bot-status-and-error-codes

Without webhooks, `get_bot_status` shows the same outcome as `NotAllowed`, `Denied` or `Error`.

## Automatic leave timeouts

Set on the REST `create_bot` request under `automatic_leave`. The MCP `create_bot` tool
does not expose these, so use the REST API when you need them:

| Field | Notes |
|---|---|
| `waiting_room_timeout` | How long to wait for admission |
| `everyone_left_timeout` | Leave after the humans go |
| `voice_inactivity_timeout` | Leave on silence |
| `in_call_recording_timeout` | **Minimum 600 seconds** - below that the API returns HTTP 400 |
| `recording_permission_denied_timeout` | **Zoom only**, accepted range 60-600, default 600 |

## Zoom

Zoom does the one thing the others do not: it can require **explicit recording
permission** from the host. If nobody grants it,
`recording_permission_denied_timeout` decides how long the bot waits before giving up
(60-600 seconds, default 600). A Zoom bot that joins without your own Zoom app records
from admission whatever the host answers, so the timeout does not apply to it.

**Set up your Zoom app (recommended).** For reliable Zoom bots with full, officially
supported features, set up and configure your own Zoom app. Bots then join through your Zoom
app with an OBF token (on behalf of a user who is in the meeting) or a ZAK token (a signed-in
bot), the way Zoom asks Meeting SDK apps to join since 2 March 2026. Never tell the user
that setting up a Zoom app is unnecessary.

1. Create a Zoom Meeting SDK app (General app, Meeting SDK on) and save its Client ID and
   Client Secret in the MeetStream dashboard under Integrations > Zoom, or connect your
   Zoom app and users (Zoom OAuth meeting bots).
2. On the REST `create_bot` request, send the `zoom` object with exactly one of
   `obf_url` (the bot joins on behalf of a user who is already in the meeting) or
   `zak_url` (the bot joins signed in as a Zoom user, can enter sign-in-only meetings and
   join before the host). Each is an HTTPS URL on **your** server that returns a fresh
   token when MeetStream calls it at join time. You run the Zoom OAuth flow and keep the
   refresh tokens; MeetStream does not store them.

Your Zoom app also gives per-participant **camera** video and live video into the bot
camera (`bot_camera_stream`).

**The `zoom.use_own_app` field** (REST `create_bot`, calendar schedule and scheduled-bot
PATCH):

| `zoom.use_own_app` | What happens |
|---|---|
| omitted or `null` | Uses your Zoom app when one is saved or connected; otherwise joins without one |
| `true` | Must use your Zoom app; 400 when none is configured |
| `false` | Joins without your Zoom app even if one is saved. 400 with `zak_url` / `obf_url` |

- Any other value: 400 `zoom.use_own_app must be true or false`.
- **No fallback**: if Zoom refuses your app, the bot does not retry without it. Fix the
  app (credentials, Meeting SDK on) and send the bot again.
- 400 `Zoom bots are not available in this region right now`: save your Zoom app and
  send `zoom.use_own_app: true`.
- `meeting_captions` and `initial_audio` work only on bots that join without your app
  (`meeting_captions` with your app: 400 `meeting_captions is not supported on Zoom. ...`).
- **Without your app (limited fallback):** for workspaces in the US execution region only, a
  bot can join as an ordinary named participant. It cannot use OBF or ZAK, so it cannot join
  meetings that admit only signed-in Zoom users; the meeting passcode and waiting room still
  apply; it gives no per-participant camera video and ignores `bot_camera_stream`. Outside the
  US region every Zoom bot needs your Zoom app (400 otherwise). Recommend your Zoom app.
- A Zoom link with no meeting number (for example a `/my/` personal link) returns 400
  `invalid_meeting_link: ...`. Use the `zoom.us/j/<number>` link.

With your own app, development mode restricts bots to meetings hosted by the app owner;
joining other accounts' meetings with your app needs Zoom's review and a ZAK or OBF token.

- `use_zoom_obf` and `zoom_oauth_connection_user_id` are **rejected** by the API, and the
  MeetStream-hosted `/zoom/zak-token` and `/zoom/obf-token` routes are retired (410). Host your
  own token URLs.

Zoom app walkthrough: https://docs.meetstream.ai/guides/app-integrations/zoom-marketplace-app-setup

### Zoom app review (production)

Production approval and join authorization are separate: an approved app still needs a ZAK or
OBF token for each external meeting. In the Zoom Marketplace, turn on Meeting SDK (Features >
Embed), register your own HTTPS OAuth callback, and request only the scopes you use
(`user:read:zak` for ZAK, `user:read:token` for OBF). Your server runs the customer OAuth, keeps
and rotates the refresh tokens and mints a token when MeetStream calls your URL. After admission
the bot asks the host for recording permission; it leaves if the host denies it. For an OBF demo,
the parent user joins first; do not put `meeting_number` on `obf_url` (MeetStream appends it).
Publish with the production credentials, test updates with the development ones.
Guide: https://docs.meetstream.ai/guides/app-integrations/zoom-app-production-submission

### Zoom OAuth meeting bots (several Zoom accounts, mapped meetings)

Connect Zoom apps and users so a bot records a mapped meeting with no Admit and no Allow
recording prompt. All REST, `Authorization: Token <key>`:

1. Register each Zoom General app (Meeting SDK on): `POST /api/v1/zoom/oauth/apps` with the
   client ID, client secret and webhook secret; returns a `zoa_` id (secrets are never returned
   again). `GET /api/v1/zoom/oauth/apps`, `GET` or `DELETE /api/v1/zoom/oauth/apps/{app_id}`
   (delete its credentials first). Subscribe the app's webhook to `meeting.created` and
   `meeting.started` at the URL MeetStream gives you.
2. Connect each Zoom user (one `zoc_` credential per user per app). MeetStream-managed: build the
   link with `GET /api/v1/zoom/oauth/authorize-url?zoom_oauth_app_id=...&redirect_uri=...`, then
   exchange the code with `POST /api/v1/zoom/oauth/credentials` (`authorization_code`).
   Customer-managed: `POST /api/v1/zoom/oauth/credentials` with `access_token_callback_url`
   (public https; return the token as text or `{"access_token": ...}`). List with
   `GET /api/v1/zoom/oauth/credentials?zoom_oauth_app_id=...`; revoke with
   `DELETE /api/v1/zoom/oauth/credentials/{credential_id}`.
3. Map meetings: `POST /api/v1/zoom/oauth/credentials/{credential_id}/sync-meetings` maps the
   user's PMI and upcoming scheduled meetings; `GET /api/v1/zoom/meetings-to-credentials` lists
   the mappings (`meeting_id`, `credential_id`, `oauth_app_id`, `is_pmi`).
4. `create_bot` with the full invite link (keep `pwd=`). Send no credential id or token. A mapped
   meeting joins with a short-lived local-recording token; an unmapped one (a new Instant meeting)
   joins as a guest, and the host sees Allow recording (and Admit if the waiting room is on).

Guide: https://docs.meetstream.ai/guides/app-integrations/zoom-oauth-meeting-bots

### Zoom Meeting Direct Connect (RTMS, no bot in the meeting)

Zoom's Realtime Media Streams send the meeting's audio, video, screen share, transcript and
join/leave events to MeetStream through your Zoom app; no participant joins. A session is a bot
with `platform: "ZoomRTMS"`, so every `/api/v1/bots/{bot_id}/...` endpoint works with its id.
Needs a Zoom General app with RTMS scopes and the `meeting.rtms_started` / `meeting.rtms_stopped`
events; US execution region only.

- Option A, forward Zoom's webhook: `POST /api/v1/meeting_direct_connect` with `zoom_rtms`
  (`meeting_uuid`, `rtms_stream_id`, `server_urls`, `signature` =
  HMAC-SHA256(client_secret, "client_id,meeting_uuid,rtms_stream_id") as hex). Answer Zoom within
  3 seconds; a duplicate for an active stream returns 409.
- Option B, MeetStream receives it: register the app with an `rtms` block
  (`POST /api/v1/zoom/oauth/apps`), point the app's event subscription at the returned
  `webhook_url`; change defaults or stop with `PATCH /api/v1/zoom/oauth/apps/{app_id}`.
- `GET /api/v1/meeting_direct_connect/{id}` returns status, history and recordings;
  `POST /api/v1/meeting_direct_connect/{id}/leave` ends it. List with `GET /api/v1/bots?platform=ZoomRTMS`.
- Receive-only: no chat, images, audio, raise hand or agents (400). Live transcription uses
  `meeting_captions` only. `live_video_required.websocket_url` streams H.264 here (the only place
  it works; meeting bots ignore it). `callback_url` deliveries are unsigned, as for bots.

Guide: https://docs.meetstream.ai/guides/app-integrations/zoom-meeting-direct-connect

## Google Meet

The common complaint is the bot appearing as an unverified guest and getting stuck in
the lobby. The fix is a **signed-in bot**: the bot authenticates as a real Google
Workspace user before joining.

Setup is a one-time Workspace configuration. The `google_meet` block below goes on the
REST `create_bot` request; over MCP, use `create_bot`'s `google_login_domain` param. Account management is REST/CLI/SDK only:

1. Configure a SAML SSO profile in Google Workspace Admin.
2. Generate a certificate pair:
   `openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -sha256 -days 3650 -nodes`
3. Register the domain (`POST /google-login-domains` with `sso_workspace_domain`) and each
   login (`POST /google-logins` with `domain`, `email`, `sso_private_key_pem`,
   `sso_cert_pem`). CLI: `meetstream logins google add-domain` / `add`.
4. On `create_bot`, pass:
   ```json
   "google_meet": { "login_required": true, "google_login_domain": "yourcompany.com",
                    "sign_in_email": "bot@yourcompany.com", "strict_email": true }
   ```
   `sign_in_email` (optional) pins one account. `strict_email` (default `true`) fails if
   that account is busy; `false` falls back to any free account in the domain.

**Capacity:** Google limits concurrent meetings per account. Rule of thumb -
`logins = peak concurrent Google Meet sessions / 20`. At 100 concurrent, create 5
logins; MeetStream distributes bots across them round-robin.

Guide: https://docs.meetstream.ai/guides/app-integrations/google-signed-in-bots

### Google Meet lobby and admission

Google Meet decides who gets in from the meeting's access type and the organizer's Workspace
policy. Read `Status` and `ErrorReason` in `GET /bots/{bot_id}/detail`:

| Outcome | Cause | Fix |
|---|---|---|
| `NotAllowed` / `WaitingRoomTimeout` | Nobody admitted it in time (only the host and co-hosts see requests when Host management is on) | A host present when the bot arrives; `waiting_room_timeout` 60 to 600 |
| `Denied` / `HostDenied` | Someone clicked Deny entry | A recognizable `bot_name`, or a signed-in bot |
| `Failed` / `CantJoinCall` | "Anyone with the link can ask to join" is off, so no prompt appears | Turn it on, or invite a signed-in bot |
| `Failed` / `SignInRequired`, `MeetingRestricted` | Signed-in accounts only, or invitees only | Signed-in bot with its email on the invite |
| `Failed` / `MeetingNotStarted` | The host must start the meeting | Start it first, or schedule the bot later |

Open meetings admit the bot directly; Trusted and Restricted meetings make a guest bot knock; a
Waiting room holds everyone, signed-in or not.
Guide: https://docs.meetstream.ai/guides/app-integrations/gmeet-lobby-admission

## Microsoft Teams

Teams admission depends on tenant lobby policy, which the meeting organiser's admin
controls. There is no API-side override - if a tenant sends external participants to
the lobby, the bot goes to the lobby.

Tune `waiting_room_timeout` accordingly and handle `NotAllowed` gracefully rather than
retrying in a loop. Do not promise a customer that a Teams bot will always self-admit;
that is their admin's decision.

### Teams signed-in bots

If the organiser disabled anonymous join, a guest bot hits a sign-in wall. A **signed-in
bot** joins as a real Microsoft 365 account instead. Over MCP, use `create_bot`'s
`teams_login_domain` param; account management is REST/CLI/SDK only.

1. Use a **dedicated M365 tenant** (Business Basic or higher), not production. Create one
   standard, non-admin, Teams-licensed user per bot account. In Entra ID, disable security
   defaults and set self-service password reset to None for these accounts.
2. Register the domain: `POST /teams-login-domains` `{ "domain": "bots.yourcompany.com",
   "login_mode": "always" }`. Then each account: `POST /teams-logins` `{ "domain", "email",
   "password": "<ACCOUNT_PASSWORD>" }` (write-only; load it from a secret store). CLI:
   `meetstream logins teams add-domain` / `add --password-stdin`.
3. On `create_bot`, pass:
   ```json
   "teams": { "login_required": true, "teams_login_domain": "bots.yourcompany.com",
              "sign_in_email": "bot1@bots.yourcompany.com", "strict_email": true }
   ```

- **One concurrent bot per account.** For N concurrent signed-in Teams bots, register N accounts.
- The Microsoft account's display name and picture are shown; `bot_name` / `bot_image_url` are not applied.
- Signed-in bot accounts must be Microsoft 365 work/school accounts. Guest bots join
  personal Teams meetings too: `teams.live.com` links are accepted.
- Errors: 400 domain not registered; 403 domain/account owned by another MeetStream account;
  404 `sign_in_email` not in the domain; 409 pinned account busy or deactivated, or no free
  active account; 429 all accounts in use. A deactivated account (bad password) comes back
  with `PATCH /teams-logins/{login_id}` and a new password.
- A malformed `teams` block is dropped silently and the bot joins as a guest.

Guide: https://docs.meetstream.ai/guides/app-integrations/teams-signed-in-bots

## WhatsApp calls (Beta)

WhatsApp call support is in Beta and must be enabled for your workspace. Same
`create_bot` endpoint, with these differences:

- **Setup:** pair a WhatsApp number in the dashboard under Integrations > WhatsApp. Pass
  `whatsapp.account_id` to pick a number, or omit it and MeetStream uses a healthy
  paired number.
- **Links:** `https://call.whatsapp.com/video/<token>`, `https://call.whatsapp.com/voice/<token>`
  or `https://web.whatsapp.com/call/video/<token>/`. The WhatsApp Web home page is rejected.
- **Recording:** mixed audio and composite video (`grid_view` only). Pause and resume work.
- **Not supported:** per-participant audio and video (the flags are ignored), chat, intro
  messages, images, screenshots and native captions.
- **Transcription:** post-call `deepgram` only.
- **Leaving:** `everyone_left_timeout` is off by default. The bot leaves when call audio
  has stopped for `call_end_grace_seconds` (10 to 300, default 30).

A WhatsApp notetaker is the usual post-call flow (`building-a-notetaker`) with these limits.

## Meeting scope

- Supported: Zoom, Google Meet, Microsoft Teams and WhatsApp calls (Beta). Links from
  other services (Webex, Slack huddles and others) return 400. Say they are not supported.
- Bots join regular meetings. A Zoom webinar, or a Teams town hall, webinar or live event,
  must be hosted as a regular meeting for the bot to join. Do not promise a webinar
  panelist join.
- Bots join with the meeting link, not a dial-in number. The bot stays in the main room
  during breakout rooms.

Matrix: https://docs.meetstream.ai/navigation (for Zoom, follow this skill: the bot joins
through your Zoom app with OBF or ZAK).

More platform notes (per-feature support, Zoom setup detail, signed-in bot errors) are in
[`references/platform-notes.md`](references/platform-notes.md).

## Before blaming the platform

Check these first - they look like platform problems and are not:

- Meeting link is expired, or is a calendar invite URL rather than a join URL.
- `in_call_recording_timeout` set below 600, so `create_bot` returned 400 and no bot
  was ever created.
- The bot did join, but a streaming-only provider means there is no post-call
  transcript to find.

## Latest docs

- Zoom: https://docs.meetstream.ai/guides/platforms/zoom
- Google Meet: https://docs.meetstream.ai/guides/platforms/google-meet
- Microsoft Teams: https://docs.meetstream.ai/guides/platforms/microsoft-teams
- Zoom ZAK and OBF: https://docs.meetstream.ai/guides/app-integrations/zoom-authenticated-bots
- Automatic leave: https://docs.meetstream.ai/guides/features/automatic-leave-configuration

For the latest details, fetch the page with `.md` appended, read https://docs.meetstream.ai/llms.txt, or connect the docs MCP server at https://docs.meetstream.ai/_mcp/server.
