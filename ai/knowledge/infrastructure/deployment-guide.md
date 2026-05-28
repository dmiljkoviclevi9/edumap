# Deployment Guide

## CI/CD workflow

File: `.github/workflows/ci-cd.yml`

Two jobs:

### build-test (runs on every push + PR)

1. Checkout
2. `dotnet restore`
3. `dotnet build --configuration Release`
4. `dotnet test --configuration Release` — must pass before deploy
5. Upload test results artifact (`TestResults/test-results.trx`)
6. `dotnet publish src/EduMap.Api --configuration Release --output ./publish`
7. Upload publish artifact (`app`)

### deploy (runs only on push to `main` when `DEPLOY_ENABLED == 'true'`)

1. Download publish artifact
2. Azure login via OIDC (`azure/login@v2`) using repo variables (not secrets)
3. `azure/webapps-deploy@v3` → deploys to `edumap-miljkovici`

The `production` GitHub environment gates the deploy job. The OIDC token is
minted with `permissions: id-token: write`.

## OIDC authentication — how it works

```
GitHub Actions runner
  → mints an OIDC JWT (audience: api://AzureADTokenExchange)
  → azure/login action exchanges it for an Azure AD token
  → Azure validates the federation claim against UAMI mi-edumap-github
  → UAMI's Website Contributor role on App Service grants the deploy
```

Variables needed: `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`,
`AZURE_WEBAPP_NAME`. No secrets, no publish profiles.

## Deploy verification

The GitHub MCP (`github` server in `.mcp.json`) is available in Claude Code sessions — use it to check run status interactively. For scripted polling (CI, automation, or any context without MCP), use `curl` + `python -X utf8` against the public REST API:

```bash
SHA=$(git rev-parse HEAD | cut -c1-7)
for i in {1..30}; do
  curl -s "https://api.github.com/repos/dmiljkoviclevi9/EduMap/actions/runs?per_page=3" \
    | python -X utf8 -c "
import sys, json
for r in json.load(sys.stdin).get('workflow_runs', []):
    if r['head_sha'].startswith('$SHA'):
        print(f\"{r['status']}/{r['conclusion']}\"); break
else: print('not yet')"
  sleep 8
done
```

When `completed/success`, confirm the deploy landed:
```bash
curl https://edumap-miljkovici.azurewebsites.net/health
```

Full pattern with four verification checkpoints: `.claude/skills/iterative-azure-deploy/SKILL.md`.

## Local dev

```powershell
dotnet build
dotnet test
dotnet run --project src/EduMap.Api   # http://localhost:5029
```

Local dev uses the embedded `Data/countries.json` (Blob Storage is not configured).

## Pausing deploys

Set repo variable `DEPLOY_ENABLED = false` to skip the deploy job while Azure
resources are being bootstrapped. The build-test job still runs.

## F1 Free tier cold start

~28 s after idle. The deploy step warms the app. Don't flag a slow first
request after a quiet hour as a bug.

## .NET version

Pinned to .NET 10 (LTS, supported through November 2028). Both
`EduMap.Api.csproj` and `Dockerfile` target `10.0`. App Service is configured
for `DOTNETCORE:10.0`.
