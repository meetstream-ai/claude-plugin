# MeetStream API endpoints: Teams signed-in bots

> Part of [`endpoints.md`](endpoints.md), split so each file stays under 20 KB.

## Teams signed-in bots

| Method and path | What it does | Request | Docs |
|---|---|---|---|
| `POST /api/v1/teams-login-domains` | Register the Microsoft 365 domain your Teams bot accounts sign in with. | body: **domain** + 2 optional; responses: 201, 400 | [Create Teams Domain](https://docs.meetstream.ai/api-reference/api-endpoints/teams-signed-in-bots/create-teams-domain) |
| `GET /api/v1/teams-login-domains` | List the Microsoft 365 domains registered for signed-in Teams bots, with how many accounts each has and how many are active. | responses: 200 | [List Teams Domains](https://docs.meetstream.ai/api-reference/api-endpoints/teams-signed-in-bots/list-teams-domains) |
| `GET /api/v1/teams-login-domains/{domain}` | Get one registered Teams login domain, including each of its bot accounts and whether it is currently in use. | responses: 200, 404 | [Get Teams Domain](https://docs.meetstream.ai/api-reference/api-endpoints/teams-signed-in-bots/get-teams-domain) |
| `PATCH /api/v1/teams-login-domains/{domain}` | Rename a registered Teams login domain or change its login mode. | body: name, login_mode; responses: 200, 404 | [Update Teams Domain](https://docs.meetstream.ai/api-reference/api-endpoints/teams-signed-in-bots/update-teams-domain) |
| `DELETE /api/v1/teams-login-domains/{domain}` | Remove a Teams login domain and every bot account registered under it. | responses: 200, 404 | [Delete Teams Domain](https://docs.meetstream.ai/api-reference/api-endpoints/teams-signed-in-bots/delete-teams-domain) |
| `POST /api/v1/teams-logins` | Register a Microsoft 365 bot account for signed-in Teams joins. | body: **domain**, **email**, **password** + 1 optional; responses: 201, 400 | [Create Teams Login](https://docs.meetstream.ai/api-reference/api-endpoints/teams-signed-in-bots/create-teams-login) |
| `GET /api/v1/teams-logins` | List the bot accounts registered under a Teams login domain, with whether each is active and currently in use. | query: domain; responses: 200, 400, 404 | [List Teams Logins](https://docs.meetstream.ai/api-reference/api-endpoints/teams-signed-in-bots/list-teams-logins) |
| `GET /api/v1/teams-logins/{login_id}` | Get one registered Teams bot account, including its lease status and the result of its last sign-in. | responses: 200, 404 | [Get Teams Login](https://docs.meetstream.ai/api-reference/api-endpoints/teams-signed-in-bots/get-teams-login) |
| `PATCH /api/v1/teams-logins/{login_id}` | Rotate a Teams bot account's password or turn the account on or off. | body: password, is_active; responses: 200, 404 | [Update Teams Login](https://docs.meetstream.ai/api-reference/api-endpoints/teams-signed-in-bots/update-teams-login) |
| `DELETE /api/v1/teams-logins/{login_id}` | Delete a registered Teams bot account so signed-in Teams bots stop using it. | responses: 200, 404 | [Delete Teams Login](https://docs.meetstream.ai/api-reference/api-endpoints/teams-signed-in-bots/delete-teams-login) |

## MIA voice agents

| Method and path | What it does | Request | Docs |
|---|---|---|---|
| `POST /api/v1/mia` | For more information on customizing the payload, please refer to [MIA Configurations](https://docs.meetstream.ai/guides/mia/mia-custom-configurations) in our guides. | body: **agent_name**, **mode**, **model** + 6 optional; responses: 201, 400 | [Create Agent Config](https://docs.meetstream.ai/api-reference/api-endpoints/mia/create-agent-config) |
| `PUT /api/v1/mia` | Update an in-meeting voice agent's configuration: its model, voice, transcriber, prompt, tools and interruption handling. | body: **agent_config_id** + 7 optional; responses: 200 | [Update Agent Config](https://docs.meetstream.ai/api-reference/api-endpoints/mia/update-agent-config) |
| `GET /api/v1/mia` | List the voice agent configurations in your workspace, with the model, voice, transcriber and tool settings of each. | responses: 200 | [Get Agent Configs](https://docs.meetstream.ai/api-reference/api-endpoints/mia/get-agent-configs) |
| `DELETE /api/v1/mia` | Delete a voice agent configuration by id. | query: agent_config_id; responses: 200 | [Delete Agent Config](https://docs.meetstream.ai/api-reference/api-endpoints/mia/delete-agent-config) |
| `POST /api/v1/bots/{bot_id}/update_mia` | Update a running MIA voice agent mid-call: its prompt variables, system prompt or wake words. | body: agent_config_params, system_prompt, wake_word_enabled, wake_words, wait_for_ack; responses: 200, 400, 403, 404, 409, 429, 503 | [Update Live Agent](https://docs.meetstream.ai/api-reference/api-endpoints/mia/update-live-agent) |

## Billing

| Method and path | What it does | Request | Docs |
|---|---|---|---|
| `GET /api/v1/billing/balance` | Available for all accounts. | responses: 200, 403, 404, 500 | [Get Balance](https://docs.meetstream.ai/api-reference/api-endpoints/billing/get-balance) |

## Guide-only routes

Public routes that are in the guides but not in the API spec.

| Method and path | What it does | Docs |
|---|---|---|
| `POST /api/v1/zoom/oauth/apps` | Register a Zoom OAuth app (client ID, client secret, webhook secret); returns a zoa_ id. Secrets are not returned later. | https://docs.meetstream.ai/guides/app-integrations/zoom-oauth-meeting-bots |
| `GET /api/v1/zoom/oauth/apps` | List registered Zoom OAuth apps. | https://docs.meetstream.ai/guides/app-integrations/zoom-oauth-meeting-bots |
| `GET /api/v1/zoom/oauth/apps/{app_id}` | Get one Zoom OAuth app. | https://docs.meetstream.ai/guides/app-integrations/zoom-oauth-meeting-bots |
| `DELETE /api/v1/zoom/oauth/apps/{app_id}` | Delete a Zoom OAuth app (delete its credentials first). | https://docs.meetstream.ai/guides/app-integrations/zoom-oauth-meeting-bots |
| `PATCH /api/v1/zoom/oauth/apps/{app_id}` | Update a Zoom OAuth app, for example its rtms block for Meeting Direct Connect. | https://docs.meetstream.ai/guides/app-integrations/zoom-meeting-direct-connect |
| `GET /api/v1/zoom/oauth/authorize-url` | Build the Zoom authorization URL (zoom_oauth_app_id, redirect_uri). | https://docs.meetstream.ai/guides/app-integrations/zoom-oauth-meeting-bots |
| `POST /api/v1/zoom/oauth/credentials` | Create a Zoom credential from an authorization_code (MeetStream-managed) or an access_token_callback_url (customer-managed); returns a zoc_ id. Also served as /zoom/oauth/connections. | https://docs.meetstream.ai/guides/app-integrations/zoom-oauth-meeting-bots |
| `GET /api/v1/zoom/oauth/credentials` | List Zoom credentials for an app (zoom_oauth_app_id). | https://docs.meetstream.ai/guides/app-integrations/zoom-oauth-meeting-bots |
| `DELETE /api/v1/zoom/oauth/credentials/{credential_id}` | Revoke a Zoom credential at Zoom and delete its meeting mappings. | https://docs.meetstream.ai/guides/app-integrations/zoom-oauth-meeting-bots |
| `POST /api/v1/zoom/oauth/credentials/{credential_id}/sync-meetings` | Map the user's PMI and upcoming scheduled meetings to this credential. | https://docs.meetstream.ai/guides/app-integrations/zoom-oauth-meeting-bots |
| `GET /api/v1/zoom/meetings-to-credentials` | List meeting-to-credential mappings (meeting_id, credential_id, oauth_app_id, is_pmi). | https://docs.meetstream.ai/guides/app-integrations/zoom-oauth-meeting-bots |
| `POST /api/v1/meeting_direct_connect` | Start a Zoom Meeting Direct Connect (RTMS) session with no bot (zoom_rtms block). US region; enabled per account. | https://docs.meetstream.ai/guides/app-integrations/zoom-meeting-direct-connect |
| `GET /api/v1/meeting_direct_connect/{id}` | Get a Direct Connect session: status, status_changes, recordings. | https://docs.meetstream.ai/guides/app-integrations/zoom-meeting-direct-connect |
| `POST /api/v1/meeting_direct_connect/{id}/leave` | End a Direct Connect session (idempotent). | https://docs.meetstream.ai/guides/app-integrations/zoom-meeting-direct-connect |
| `GET /api/v1/calendar/get_events` | Return calendar events already synced, without calling the calendar provider. | https://docs.meetstream.ai/guides/calendar-integrations/google-calendar-oauth-setup |

## Retired routes

| Method and path | Status | Note |
|---|---|---|
| `GET /api/v1/zoom/zak-token` | 410 | Retired 15 Sep 2026; send zoom.zak_url (a token URL you host) on create_bot. |
| `GET /api/v1/zoom/obf-token` | 410 | Retired 15 Sep 2026; send zoom.obf_url (a token URL you host) on create_bot. |

## Dashboard only, no API

| What | Note | Docs |
|---|---|---|
| Custom storage destinations (S3, OSS, R2) | Configure in the dashboard; pass storage_id on create_bot. | https://docs.meetstream.ai/guides/features/custom-storage-configurations/overview |
| Workspace webhook endpoints and their signing secrets | Configure > Webhooks; the secret is shown once. | https://docs.meetstream.ai/guides/webhooks/workspace-webhooks |
| API keys | Created by the dashboard, or by meetstream login / MCP sign-in. | https://docs.meetstream.ai/guides/get-started/dashboard-setup |
