# MeetStream Getting Started - First-Time Setup: Troubleshooting

> Part of [`getting-started.md`](getting-started.md), split so each file stays under 20 KB.

## Troubleshooting

### "I see the dashboard but no 'Create API Key' button"
Direct them to https://app.meetstream.ai/api-keys (deep link). Account may need email verification first - check inbox.

### "The key I created returns 401"
- Make sure they copied the WHOLE key (it's long - usually starts with `ms_` then 30+ characters)
- Make sure there are no leading/trailing whitespace characters
- Make sure the app loads the key from its secret store or `.env` file

### "I have no credits / billing question"
Direct to https://app.meetstream.ai/billing (balance and top-up). New accounts start with $5 of credit; prices at https://meetstream.ai/pricing. The billing page shows the balance (a read-only `GET /api/v1/billing/balance` may answer "not available" on some accounts; then use the billing page).

### "I want to use a team account / shared key"
- Each team member should create their own key from their own account
- For server-side production use, create a dedicated key (e.g. "production") and store in a secret manager (AWS Secrets Manager, Doppler, Vault)

### "Can I rotate my key without breaking my deployment?"
- Create a new key first (don't delete the old one)
- Deploy the new key to your environment
- Once the new key is in use, delete the old one from the dashboard

## Constraints

- **Never ask for, log or print the API key.** Sign-in happens in the browser (MCP or `meetstream login`).
- **Never commit the key to git.** Always insist on `.env` + `.gitignore`.
- **Never POST the key anywhere except api.meetstream.ai.**
- **Never proceed with any build skill until Step 5 succeeds.** Better to ask once more than to scaffold a broken app.

## Latest docs

- Build tracks (integration paths): https://docs.meetstream.ai/guides/introduction/integration-paths
- Bridge server for your own agent stack: https://docs.meetstream.ai/guides/websockets/bridge-server-architecture
- Dashboard setup and API key: https://docs.meetstream.ai/guides/get-started/dashboard-setup
- Create your first bot: https://docs.meetstream.ai/guides/get-started/create-your-first-bot
- Zoom bots through your Zoom app (OBF and ZAK): https://docs.meetstream.ai/guides/app-integrations/zoom-authenticated-bots

For the latest details, fetch the page with `.md` appended, read https://docs.meetstream.ai/llms.txt, or connect the docs MCP server at https://docs.meetstream.ai/_mcp/server.
