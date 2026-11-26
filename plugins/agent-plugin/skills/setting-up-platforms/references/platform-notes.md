# Platform notes

Moved from the core `meetstream` skill (3.3.1): per-feature platform notes, Zoom setup, Google and Teams signed-in bots.

## Contents

- [Zoom setup](#zoom-setup)
- [Google Signed-In Bots](#google-signed-in-bots)
- [Microsoft Teams Signed-In Bots](#microsoft-teams-signed-in-bots)

## Platform Notes (per-feature, not just per-bot)

| Feature | Google Meet | Zoom | Microsoft Teams |
|---|---|---|---|
| Basic bot (`create_bot`) | ✓ | ✓ (through your Zoom app, OBF or ZAK) | ✓ |
| Recording + post-call transcript | ✓ | ✓ | ✓ |
| Live transcription webhook | ✓ | ✓ | ✓ |
| Live audio (`live_audio_required`) | ✓ | ✓ | ✓ |
| **Live video (`live_video_required`)** | ✗ (ignored) | ✗ (ignored; RTMS sessions only) | ✗ (ignored) |
| **Per-participant audio streams** | ✓ | ✓ | **✗** |
| Per-participant video streams | ✓ | ✓ | ✓ |
| MIA agents | ✓ | ✓ | ✓ |
| `interrupt` WS command (clears audio queue) | ✓ | ✗ (accepted, no-op) | ✗ (accepted, no-op) |
| Raise / lower hand (`send_command`) | ✓ | ✓ | ✓ |
| Participant hand events (`participant_events.raise_hand` / `.lower_hand`) | ✓ | ✓ | not documented yet |
| Live video into the bot camera (`bot_camera_stream`) | ✓ (ws/wss) | ✓ (wss, with your own Zoom app) | ✓ (wss) |
| Native captions (`meeting_captions`) | ✓ | only without your own Zoom app (400 with it) | ✓ |
| `video_layout` `speaker_view_default` / `grid_view_default` | ✓ | ✗ (400) | ✓ |
| Signed-in bot (real account identity) | ✓ (`google_meet`) | ✓ (`zoom.zak_url` / `obf_url`) | ✓ (`teams`, M365 work/school only, 1 bot per account) |

### Zoom setup

**How a Zoom bot joins.** Recommend the user's own Zoom app for reliable, fully supported Zoom bots: they join through it with an OBF token (on behalf of a user who is in the meeting) or a ZAK token (a signed-in bot), the way Zoom asks Meeting SDK apps to join since 2 March 2026. Without it, a limited fallback joins as a named guest in the US execution region only (no OBF or ZAK, no per-participant camera video). Never write that Zoom needs no setup, that no Zoom app, SDK keys, OAuth or tokens are needed, or that the Zoom app is optional.

| Setup | What it does |
|---|---|
| Your Zoom app credentials (Client ID and Client Secret of a Zoom Meeting SDK app, saved in Dashboard > Integrations > Zoom) | The bot joins with your Zoom app. Needed for `zak_url` / `obf_url`, per-participant camera video and live video into the bot camera (`bot_camera_stream`) |
| Connected Zoom accounts (Zoom OAuth Meeting Bots) | Meetings you map can be recorded without an Admit or Allow recording prompt |
| `zoom.obf_url` (on-behalf-of bot) | Joins on behalf of a user who is already in the meeting |
| `zoom.zak_url` (signed-in bot) | Joins as a Zoom user: can join meetings that allow only signed-in users, and can join before the host |

Bots that join without the user's Zoom app (`use_own_app: false`) differ:
- Per-participant video (`video_separate_streams`) contains screen shares only. Per-participant audio works.
- The bot camera shows images (`bot_image_url`, Send Image). Live video into the bot camera (`bot_camera_stream`) is not available. MIA agents on this bot can show images, video and an avatar.
- The bot asks the host to allow recording, and records from the moment it is admitted. `recording_permission_denied_timeout` does not apply.
- Meetings that require Zoom sign-in cannot be joined. Use `zak_url`.
- `meeting_captions` and `initial_audio` work only on this bot. `screenshot` (via `send_command`) works here; the bot that uses your own Zoom app returns 400 for it.

**The `zoom.use_own_app` field** (`true`, `false` or omitted):

| `zoom.use_own_app` | What happens |
|---|---|
| omitted or `null` (default) | The bot uses the user's Zoom app when one is saved or a healthy Zoom account is connected, and joins without an app otherwise. |
| `true` | The bot must join with the user's Zoom app. With no app saved, `create_bot` returns 400. |
| `false` | The bot joins without the user's Zoom app, even when one is saved. Cannot be combined with `zak_url` / `obf_url`: 400 `zoom.zak_url and zoom.obf_url cannot be used with zoom.use_own_app set to false`. |

- Any other value returns 400 `zoom.use_own_app must be true or false`. The field is not echoed in bot details.
- There is **no fallback**: if Zoom refuses the user's own app, the bot does not retry without it. Fix the app and send the bot again.
- 400 `Zoom bots are not available in this region right now`: save the user's Zoom app and send `use_own_app: true`.
- `zoom.use_own_app` also works on `POST /calendar/schedule/{event_id}` and `PATCH /calendar/scheduled_bots/{bot_id}`. Optional setup guides: https://docs.meetstream.ai/guides/app-integrations/zoom-marketplace-app-setup and, for joining meetings outside the app's own account with your app, https://docs.meetstream.ai/guides/app-integrations/zoom-app-production-submission

For authenticated Zoom joins, pass `"zoom": { "zak_url": "https://..." }` (join as a signed-in user) or `"zoom": { "obf_url": "https://..." }` (join On Behalf Of a user who is already in the meeting). Each URL is an HTTPS endpoint on your server that returns a fresh token when MeetStream calls it. The older `use_zoom_obf` flag and `zoom_oauth_connection_user_id` are rejected by the API. Guide: https://docs.meetstream.ai/guides/app-integrations/zoom-authenticated-bots

### Google Signed-In Bots

To have the bot join Google Meet using a Google identity (meetings that block guests, or to show a real name instead of "Unknown"), configure SSO in your Google Workspace admin (Legacy SSO profile pointing at MeetStream's sign-in/sign-out URLs, plus an OpenSSL key + certificate), then register the domain and accounts. Guide: https://docs.meetstream.ai/guides/app-integrations/google-signed-in-bots

| Method | Path | Notes |
|---|---|---|
| POST | `/google-login-domains` | `{ "sso_workspace_domain": "your-company.com", "name": "...", "login_mode": "always" }` (`if_required` also accepted) |
| GET | `/google-login-domains` | `{ domains: [{ sso_workspace_domain, name, login_mode, max_concurrent_per_login, login_count, active_login_count, created_at }] }` |
| GET / PATCH / DELETE | `/google-login-domains/{domain}` | Path param is the workspace domain string. PATCH `{ name?, login_mode? }`. DELETE is refused while any login is active |
| POST | `/google-logins` | `{ domain, email, sso_private_key_pem, sso_cert_pem, is_active? }` (PEM contents of `key.pem` / `cert.pem`) |
| GET | `/google-logins?domain=<d>` | `{ logins: [...] }` |
| PATCH | `/google-logins/{login_id}` | Body must include `domain`; plus `is_active?`, `email?`, `sso_private_key_pem?`, `sso_cert_pem?` |
| DELETE | `/google-logins/{login_id}?domain=<d>` | |

There is **no** `GET /google-logins/{login_id}`; use the list endpoint or `GET /google-login-domains/{domain}`. Updates use PATCH, not PUT.

Then, on `create_bot`, pass the `google_meet` block:
```json
{
  "google_meet": {
    "login_required": true,
    "google_login_domain": "your-company.com",
    "sign_in_email": "bot@your-company.com",
    "strict_email": true
  }
}
```

- `sign_in_email` (optional) pins one registered account. `strict_email` (optional, default `true`): with `sign_in_email`, `true` fails if that account is busy or unhealthy; `false` falls back to any available account in the domain.
- Concurrency: a Google account can serve many meetings at once, but add logins as you scale (rule of thumb from the guide: one login per ~20 concurrent Meet sessions). MeetStream distributes bots across them.
- `google_meet` is not in the OpenAPI `CreateBotRequest` schema; the guide above is canonical.
- CLI: `meetstream logins google ...` and `meetstream join <link> --google-login-domain <d>` MCP: `create_bot`'s `google_login_domain` param. Account management is REST / CLI / SDK only.

### Microsoft Teams Signed-In Bots

By default a Teams bot joins as an anonymous guest and fails outright if the organizer disabled anonymous join. A signed-in bot joins as a real Microsoft 365 account. Guide: https://docs.meetstream.ai/guides/app-integrations/teams-signed-in-bots

**Setup requirements (once):**
1. A **dedicated Microsoft 365 tenant**, not your production one (Business Basic or higher).
2. One **standard, non-admin user per bot account**, with a Teams license. Set its display name and profile picture: that is what participants see.
3. In Entra ID: **disable security defaults** and set self-service password reset to **None** for these accounts (otherwise the first automated sign-in hits MFA registration).
4. Signed-in bot accounts must be Microsoft 365 work/school accounts. This applies only to signed-in bots: a guest bot also joins personal Teams meetings (`teams.live.com` links are accepted).

**Register the domain, then each account:**

| Method | Path | Body / notes |
|---|---|---|
| POST | `/teams-login-domains` | `{ "domain": "bots.your-company.com", "name": "Bot tenant", "login_mode": "always" }` (`if_required` is not supported for Teams yet) → 201 |
| GET | `/teams-login-domains` | `{ domains: [{ domain, name, login_mode, login_count, active_login_count, created_at }] }` |
| GET | `/teams-login-domains/{domain}` | Domain plus `logins: [{ login_id, email, is_active, lease_status, last_session_result }]`; 404 if unknown |
| PATCH | `/teams-login-domains/{domain}` | `{ name?, login_mode? }` |
| DELETE | `/teams-login-domains/{domain}` | Deletes the domain **and all its logins** |
| POST | `/teams-logins` | `{ "domain": "...", "email": "bot1@bots.your-company.com", "password": "<ACCOUNT_PASSWORD>", "is_active": true }` → 201 |
| GET | `/teams-logins?domain=<d>` | `domain` is required (400 without it); 404 if the domain isn't registered |
| GET | `/teams-logins/{login_id}` | Login object |
| PATCH | `/teams-logins/{login_id}` | `{ password?, is_active? }`. A new password also reactivates a deactivated account |
| DELETE | `/teams-logins/{login_id}` | |

Login object: `{ login_id, domain, email, is_active, lease_status, last_session_result, last_login_error, created_at, updated_at }`. The password is write-only and never returned. Load it from an env var or secret store in generated code; never hardcode it. If a bad password makes a join fail, MeetStream sets `is_active: false` until you rotate it.

**Create the bot:**
```json
{
  "meeting_link": "https://teams.microsoft.com/l/meetup-join/...",
  "bot_name": "Notetaker",
  "teams": {
    "login_required": true,
    "teams_login_domain": "bots.your-company.com",
    "sign_in_email": "bot1@bots.your-company.com",
    "strict_email": true
  }
}
```

- `teams_login_domain` is required when `login_required` is true. `sign_in_email` and `strict_email` behave as for Google (`strict_email` defaults to `true`).
- **One concurrent bot per account.** Teams merges same-email sign-ins into one attendee. For N concurrent signed-in Teams bots, register N accounts.
- **Name and avatar come from the Microsoft account.** `bot_name` and `bot_image_url` are not applied on a signed-in join.
- A malformed `teams` block is dropped silently and the bot joins as a guest. If a signed-in bot shows up as `(Guest)`, check that `login_required: true` is inside `teams`.
- CLI: `meetstream logins teams ...` and `meetstream join <link> --teams-login-domain <d>` MCP: `create_bot`'s `teams_login_domain` param. Account management is REST / CLI / SDK only.

**Errors on `create_bot`:**

| Status | Meaning | Fix |
|---|---|---|
| 400 `teams.teams_login_domain '<d>' is not registered...` | Domain not registered, or a typo | `POST /teams-login-domains` first |
| 403 | The domain or account belongs to another MeetStream account | Use a domain registered with this API key's account |
| 404 | `sign_in_email` isn't registered under the domain | Register it with `POST /teams-logins`, or fix the email |
| 409 | Pinned account busy or deactivated (`strict_email: true`), or no account is both active and free | Rotate the password (PATCH), set `strict_email: false`, or add accounts |
| 429 `all Teams logins ... in use` | Every account in the domain is leased to another bot | Register more accounts |

---
