# Azure Resources

All resources live in `rg-edumap`, westeurope. Damir is Owner — full RBAC.

## Subscription & tenant

| | Value |
|---|---|
| Subscription name | Damir |
| Subscription ID | `706589ae-fa0c-46d3-957f-e12535bc3deb` |
| Tenant | Levi9 |
| Tenant ID | `40758481-7365-442c-ae94-563ed1606218` |

## Provisioned resources

| Resource | Name | Notes |
|---|---|---|
| Resource group | `rg-edumap` | westeurope |
| App Service plan | `plan-edumap` | Free F1, Linux |
| App Service | `edumap-miljkovici` | DOTNETCORE:10.0 |
| UAMI | `mi-edumap-github` | clientId `fe9a3ff5-fbdb-431f-a5c8-3f0e1061f3f4` |
| GitHub repo | `dmiljkoviclevi9/EduMap` | main branch, OIDC-deployed |

## OIDC / authentication

Authentication uses **User-Assigned Managed Identity** (UAMI), not an AD app
registration. Levi9 tenant policy blocks `az ad app create` for non-admins.

The UAMI is federated to the GitHub `production` environment on the
`dmiljkoviclevi9/EduMap` repo. GitHub Actions mints an OIDC token;
Azure validates it and grants the UAMI's permissions (Website Contributor
on the App Service only).

**Never suggest** creating an AD app registration or service principal.
**Never use** publish profiles or long-lived secrets for deployment.

## GitHub Actions variables (not secrets)

| Variable | Value |
|---|---|
| `AZURE_CLIENT_ID` | `fe9a3ff5-fbdb-431f-a5c8-3f0e1061f3f4` |
| `AZURE_TENANT_ID` | `40758481-7365-442c-ae94-563ed1606218` |
| `AZURE_SUBSCRIPTION_ID` | `706589ae-fa0c-46d3-957f-e12535bc3deb` |
| `AZURE_WEBAPP_NAME` | `edumap-miljkovici` |
| `DEPLOY_ENABLED` | `true` (set to `false` to pause deploys during Azure bootstrapping) |

## Cognitive Services (Chunk C — Azure AI Translator)

Provisioned under `rg-edumap` when running the fun-fact translation script:

| Resource | Name | Kind | SKU |
|---|---|---|---|
| Cognitive Services | `cs-edumap-translator` | TextTranslation | F0 (free, 2M chars/month) |

Key is NOT committed. Pass via `TRANSLATOR_KEY` + `TRANSLATOR_REGION` env vars.

**F0 uniqueness:** one F0 per kind per region per subscription. Can't create a
second TextTranslation F0 in westeurope if one already exists.

## Future / optional resources

- **Azure Blob Storage** for countries.json: configure via `Storage:ConnectionString`
  + `Storage:CountriesBlobName` in App Service settings. No code change needed.
- **Azure Container Apps / ACR**: Week 4 course exercise. Not yet provisioned.

## az CLI gotcha — role assignments

`az role assignment create` with Azure CLI 2.84.0 returns a misleading
`MissingSubscription` error even on valid scopes. Workaround: use
`az rest --method put` against the ARM REST API directly. See `WALKTHROUGH.md`
section 2.2 for the full command.
