---
name: platform-setup
description: >
  Platform-specific setup and quirks for Zoom, Google Meet and Microsoft
  Teams. Use when the user says "the bot can't join Zoom", "waiting room",
  "the host has to admit it", "recording permission", "Zoom setup", "do I need a Zoom app", "OBF",
  "use_own_app", "signed-in bots", "the bot shows as guest", "Teams lobby",
  "meeting access is restricted", "sign in required", or hits a
  platform-specific failure rather than an API error.
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

**Zoom needs no setup.** A Zoom bot needs only the MeetStream API key and the meeting
link: no Zoom Marketplace app, no Zoom app credentials, no Meeting SDK keys, no Zoom OAuth
connection and no tokens. Omit `zoom` (or send `{}`) and the same `create_bot` request
works as it does for Google Meet and Teams. Do not tell the user to create a Zoom app
before their first bot.

Your own Zoom app is **optional**. Saving its Client ID and Client Secret in the MeetStream
dashboard (Integrations > Zoom) adds:

- **Authenticated joins** through the `zoom` object on the REST `create_bot` request, with
  exactly one of `zak_url` (the bot joins signed in as a Zoom user, can enter sign-in-only
  meetings and join before the host) or `obf_url` (the bot joins on behalf of a user who is
  already in the meeting). Each is an HTTPS URL on **your** server that returns a fresh
  token when MeetStream calls it at join time. You run the Zoom OAuth flow and keep the
  refresh tokens; MeetStream does not store them.
- Per-participant **camera** video (without your app, per-participant video contains
  screen shares only; per-participant audio works either way).
- Live video into the bot camera (`bot_camera_stream`). MIA agents can show images,
  video and an avatar with or without your app.

**Choosing the join with `zoom.use_own_app`** (REST `create_bot`, calendar schedule and
scheduled-bot PATCH; optional):

| `zoom.use_own_app` | What happens |
|---|---|
| omitted or `null` | Uses your Zoom app when one is saved or connected; otherwise joins without one |
| `true` | Must use your Zoom app; 400 when none is configured |
| `false` | Joins without your Zoom app even if one is saved. 400 with `zak_url` / `obf_url` |

- Any other value: 400 `zoom.use_own_app must be true or false`.
- **No fallback**: if Zoom refuses your app, the bot does not retry without it. Send
  `use_own_app: false` to avoid the app.
- No-setup join not offered for the account's region: 400 `Zoom bots are not available in this region right now`.
- `meeting_captions` and `initial_audio` work only on bots that join without your app
  (`meeting_captions` with your app: 400 `meeting_captions is not supported on Zoom. ...`).
- A Zoom link with no meeting number (for example a `/my/` personal link) returns 400
  `invalid_meeting_link: ...`. Use the `zoom.us/j/<number>` link.

With your own app, development mode restricts bots to meetings hosted by the app owner;
joining other accounts' meetings with your app needs Zoom's review and a ZAK or OBF token.

- `use_zoom_obf` and `zoom_oauth_connection_user_id` are **rejected** by the API. Do not use them
  or the `/zoom/oauth/*` connection endpoints.

Optional app walkthrough: https://docs.meetstream.ai/guides/app-integrations/zoom-marketplace-app-setup

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

## Before blaming the platform

Check these first - they look like platform problems and are not:

- Meeting link is expired, or is a calendar invite URL rather than a join URL.
- `in_call_recording_timeout` set below 600, so `create_bot` returned 400 and no bot
  was ever created.
- The bot did join, but a streaming-only provider means there is no post-call
  transcript to find.

## Reference

- Platform guides: [Zoom](https://docs.meetstream.ai/guides/platforms/zoom) · [Google Meet](https://docs.meetstream.ai/guides/platforms/google-meet) · [Microsoft Teams](https://docs.meetstream.ai/guides/platforms/microsoft-teams)
- [Google Meet lobby admission](https://docs.meetstream.ai/guides/app-integrations/gmeet-lobby-admission)
- Signed-in bots: [Google](https://docs.meetstream.ai/guides/app-integrations/google-signed-in-bots) · [Microsoft Teams](https://docs.meetstream.ai/guides/app-integrations/teams-signed-in-bots)
- [Zoom authenticated bots (ZAK and OBF)](https://docs.meetstream.ai/guides/app-integrations/zoom-authenticated-bots) · [Zoom app production submission](https://docs.meetstream.ai/guides/app-integrations/zoom-app-production-submission)
- [Automatic leave configuration](https://docs.meetstream.ai/guides/features/automatic-leave-configuration)
