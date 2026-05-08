# Edu-Map: Azure Training Walkthrough

A single checklist for the 4-week Levi9 Azure & .NET training. Every line of code you'll need is already in this repo — your job is to perform the Azure-side actions and verify each result.

## How to use this doc

- Tick each `[ ]` → `[x]` as you complete it. (VS Code's preview will render checkboxes; you can click them in some renderers, or just edit the markdown.)
- Sections marked **Code (✅ done)** are review-only. The implementation is already in the repo at the file paths shown.
- Sections marked **Azure** need your hands on the portal or CLI.
- Each task has **Why** (what the course objective is), **Do** (exact command/click), and **Verify** (how to know it worked).

## Conventions

All commands assume you've set these shell variables. Pick **one** shell and stick with it. PowerShell example shown; bash equivalents in Cloud Shell are identical for `az` commands (just `$VAR` style).

```powershell
# Change these. Names that need to be globally unique have <suffix> placeholders.
$RG       = "rg-edumap"
$LOCATION = "westeurope"
$PLAN     = "plan-edumap"
$APP      = "edumap-<your-suffix>"      # globally unique, lowercase
$STORAGE  = "stedumap<your-suffix>"     # globally unique, lowercase, 3-24 chars, no dashes
$ACR      = "acredumap<your-suffix>"    # globally unique, lowercase, 5-50 chars, no dashes
$LAW      = "law-edumap"
$AI       = "ai-edumap"
$CAE      = "cae-edumap"
$CAPP     = "edumap-app"
```

## Prerequisites (one-time)

- [ ] **Install Azure CLI**
  - Do: `winget install Microsoft.AzureCLI` (Windows) — or use Cloud Shell
  - Verify: `az version` shows ≥ 2.60
- [ ] **Sign in**
  - Do: `az login` — pick the Levi9 subscription
  - Verify: `az account show --query name` returns the right subscription name
- [ ] **Create resource group**
  - Do: `az group create -n $RG -l $LOCATION`
  - Verify: `az group show -n $RG --query properties.provisioningState` → `"Succeeded"`
- [ ] **VS Code extensions installed:** Azure App Service, Azure Resources, C# Dev Kit, GitHub Actions
- [ ] **Docker Desktop** running (Week 4 only)

---

## Week 1–2: Foundation & Azure SDK

**Goal:** Deploy a working .NET app to App Service. Then swap its data source to Blob Storage to exercise the Azure SDK for .NET.

### 1.1 Code review (✅ done)

- [x] `.NET 10` Minimal API at [src/EduMap.Api/Program.cs](src/EduMap.Api/Program.cs)
- [x] 4 endpoints: `GET /health`, `GET /api/countries`, `GET /api/countries/{iso2}`, `POST /api/track/{iso2}`
- [x] Static frontend at [src/EduMap.Api/wwwroot/index.html](src/EduMap.Api/wwwroot/index.html) loads countries via `fetch('/api/countries')`
- [x] [CountryRepository.cs](src/EduMap.Api/Services/CountryRepository.cs) with Blob Storage primary / embedded JSON fallback
- [x] Structured logging via `ILogger` (visible in App Service log stream)
- [x] 271 country flag SVGs vendored into [wwwroot/flags/](src/EduMap.Api/wwwroot/flags/)
- [x] 17 sample countries in [Data/countries.json](src/EduMap.Api/Data/countries.json)

### 1.2 Local dev verification

- [ ] **Build & test**
  - Do: `dotnet build && dotnet test`
  - Verify: `Passed!  - Failed: 0, Passed: 4`
- [ ] **Run the app**
  - Do: `cd src/EduMap.Api; dotnet run`
  - Verify: log shows `Loaded 17 countries` and `Now listening on: http://localhost:5029`
- [ ] **Open in browser**
  - Do: navigate to <http://localhost:5029/>
  - Verify: world map renders with colorful borders, no text
- [ ] **Click a country (e.g., Serbia)**
  - Verify: modal appears with flag, name, capital, fun fact
- [ ] **Click a country not in the 17**
  - Verify: "Coming soon!" toast (no error)
- [ ] **Hit health endpoint**
  - Do: `curl http://localhost:5029/health`
  - Verify: `{"status":"Healthy"}`

### 1.3 Deploy to Azure App Service (Free tier)

- [ ] **Create App Service plan (Free F1, Linux)**
  - Do: `az appservice plan create -g $RG -n $PLAN --sku F1 --is-linux`
  - Verify: `az appservice plan show -g $RG -n $PLAN --query sku.name` → `"F1"`
- [ ] **Create Web App with .NET 10 runtime**
  - Do: `az webapp create -g $RG -p $PLAN -n $APP --runtime "DOTNETCORE:10.0"`
  - Verify: `az webapp show -g $RG -n $APP --query state` → `"Running"`
- [ ] **Deploy from VS Code (the GUI path)**
  - Do: Right-click `src/EduMap.Api` in the Explorer → "Deploy to Web App…" → pick `$APP`
  - Verify: VS Code shows "Deployment to '$APP' succeeded"
- [ ] **Repeat once via CLI (the second path your course wants you to know)**
  - Do:
    ```powershell
    cd src/EduMap.Api
    dotnet publish -c Release -o ./publish
    az webapp deploy -g $RG -n $APP --src-path ./publish --type zip
    ```
  - Verify: deployment succeeds
- [ ] **Hit the public URL**
  - Do: open `https://$APP.azurewebsites.net/` in phone + desktop browsers
  - Verify: map renders, click works on touch + click
- [ ] **Hit `/health` over the public URL**
  - Do: `curl https://$APP.azurewebsites.net/health`
  - Verify: `{"status":"Healthy"}` and HTTP 200
- [ ] **Watch the log stream**
  - Do: `az webapp log tail -g $RG -n $APP` (or VS Code → "Start Streaming Logs")
  - Verify: see `Loaded 17 countries` after each deploy/restart, see `Country clicked: XX` lines as you tap countries from a phone

### 1.4 Azure SDK for .NET exercise — Blob Storage

The repo's `CountryRepository` checks for `Storage:ConnectionString` + `Storage:CountriesBlobName` and prefers Blob Storage over the embedded JSON. This exercise activates that branch.

- [ ] **Create Storage Account**
  - Do: `az storage account create -g $RG -n $STORAGE -l $LOCATION --sku Standard_LRS --kind StorageV2`
  - Verify: `az storage account show -g $RG -n $STORAGE --query provisioningState` → `"Succeeded"`
- [ ] **Create container `data`**
  - Do:
    ```powershell
    $CONN = az storage account show-connection-string -g $RG -n $STORAGE --query connectionString -o tsv
    az storage container create -n data --connection-string $CONN
    ```
  - Verify: `az storage container show -n data --connection-string $CONN --query name` → `"data"`
- [ ] **Upload countries.json blob**
  - Do: `az storage blob upload -c data -n countries.json -f src/EduMap.Api/Data/countries.json --connection-string $CONN`
  - Verify: `az storage blob list -c data --connection-string $CONN --query "[].name"` shows `countries.json`
- [ ] **Wire connection string into App Service Configuration**
  - Do (note `__` for nesting in env-style settings):
    ```powershell
    az webapp config appsettings set -g $RG -n $APP --settings `
      "Storage__ConnectionString=$CONN" `
      "Storage__CountriesBlobName=countries.json" `
      "Storage__CountriesContainerName=data"
    ```
  - Verify: `az webapp config appsettings list -g $RG -n $APP --query "[?name=='Storage__CountriesBlobName'].value"` → `["countries.json"]`
- [ ] **Restart and confirm the data source switched**
  - Do: `az webapp restart -g $RG -n $APP`, then `az webapp log tail -g $RG -n $APP`
  - Verify: log shows `Loading countries from Blob Storage container=data blob=countries.json` instead of the file fallback line
- [ ] **Edit the blob, see the change live**
  - Do: change a capital in `countries.json` locally, re-upload with `--overwrite`, restart the app, refresh the page
  - Verify: the modal shows the new capital — proof the app is reading from Blob Storage

---

## Week 3: CI/CD

**Goal:** Stop deploying by hand. Wire up GitHub Actions to build → test → deploy on every push to `main`. Repeat in Azure Pipelines for comparison.

### 2.1 Code review (✅ done)

- [x] xUnit test project at [tests/EduMap.Api.Tests/](tests/EduMap.Api.Tests/) with 4 tests using `WebApplicationFactory<Program>`
- [x] [.github/workflows/ci-cd.yml](.github/workflows/ci-cd.yml) — restore, build, test, publish, deploy
- [x] [azure-pipelines.yml](azure-pipelines.yml) — same stages, Azure DevOps dialect
- [x] `public partial class Program {}` at the bottom of `Program.cs` so the test factory can find it

### 2.2 GitHub Actions path

- [ ] **First commit**
  - Do: `git add -A; git commit -m "Initial Edu-Map foundation"`
  - Verify: `git log --oneline` shows the commit
- [ ] **Create GitHub repo and push**
  - Do (with [`gh`](https://cli.github.com/)): `gh repo create edumap --public --source=. --push`
  - Or: create via github.com UI, then `git remote add origin …; git push -u origin main`
  - Verify: repo visible on GitHub, files present
- [ ] **Get the App Service publish profile**
  - Do: `az webapp deployment list-publishing-profiles -g $RG -n $APP --xml > publish-profile.xml`
  - Verify: file is non-empty XML — you'll paste this content into the GitHub secret next
- [ ] **Add GitHub secrets**
  - Do (`gh`): `gh secret set AZURE_PUBLISH_PROFILE < publish-profile.xml`
  - Do: `gh secret set AZURE_WEBAPP_NAME --body "$APP"`
  - Then **delete** `publish-profile.xml` — never commit it
  - Verify: `gh secret list` shows both
- [ ] **Set up the `production` GitHub environment** (referenced by the deploy job)
  - Do: GitHub → Settings → Environments → New environment → name `production`
  - Verify: workflow's deploy job runs (without protection rules)
- [ ] **Trigger a workflow run**
  - Do: `git commit --allow-empty -m "kick off CI"; git push`
  - Verify: `gh run watch` shows green checkmarks for build-test and deploy
- [ ] **Make a real change and watch it deploy**
  - Do: edit Serbia's `funFact` in `src/EduMap.Api/Data/countries.json`, commit, push
  - Verify: ~2 minutes later, refreshing the public site shows the new fun fact

### 2.3 Azure Pipelines (alternative path) — for comparison

- [ ] **Create or open an Azure DevOps organization & project**
  - Do: <https://dev.azure.com/>, create org, create project `edumap`
- [ ] **Connect GitHub repo to Azure DevOps**
  - Do: Pipelines → New pipeline → GitHub → pick `edumap` → "Existing Azure Pipelines YAML" → `azure-pipelines.yml`
  - Verify: pipeline appears in the list
- [ ] **Create a service connection to your Azure subscription**
  - Do: Project Settings → Service connections → New → Azure Resource Manager → workload identity → pick subscription
  - Verify: connection saved; note its name (e.g., `azure-subscription`)
- [ ] **Set pipeline variables**
  - Do: pipeline → Variables → add `AZURE_SERVICE_CONNECTION` (value = service connection name) and `AZURE_WEBAPP_NAME` (value = `$APP`)
  - Verify: both visible in Variables tab
- [ ] **Create the `edumap-prod` Environment**
  - Do: Pipelines → Environments → New → name `edumap-prod` → leave empty (no resources)
- [ ] **Run the pipeline**
  - Do: Run pipeline button → main branch
  - Verify: both stages green; deploy stage hits the same App Service the GitHub Actions one does
- [ ] **Reflection**: write down 1-2 differences you noticed between GitHub Actions YAML and Azure DevOps YAML (stages vs jobs, deployment job syntax, task types). The course wants you to be able to compare them.

---

## Week 4: Containerization & Monitoring

**Goal:** Package the app into a container, push it to ACR, run it on Azure Container Apps. Then turn on Application Insights and prove via KQL that you can answer "which countries do kids click most?".

### 3.1 Code review (✅ done)

- [x] Multi-stage [Dockerfile](Dockerfile) with `mcr.microsoft.com/dotnet/sdk:10.0` builder + `aspnet:10.0` runtime + curl-based HEALTHCHECK
- [x] [.dockerignore](.dockerignore) excluding bin/obj/.git/secrets
- [x] Application Insights v2.22.0 (the classic SDK that no-ops without a connection string) wired in [Program.cs](src/EduMap.Api/Program.cs)
- [x] `TelemetryClient.TrackEvent("CountryClicked", { iso2 })` in `POST /api/track/{iso2}`
- [x] Frontend fires `fetch('/api/track/' + iso2, {method: 'POST'})` on every country tap

### 3.2 Docker locally

- [ ] **Build the image**
  - Do: `docker build -t edumap:dev .`
  - Verify: `docker images edumap:dev` shows the image, ~250 MB
- [ ] **Run it**
  - Do: `docker run --rm -p 8080:8080 --name edumap edumap:dev`
  - Verify: `Now listening on: http://[::]:8080` in the docker logs
- [ ] **Open in browser**
  - Do: <http://localhost:8080/>
  - Verify: map renders, click works
- [ ] **Check container health status**
  - Do (in a second terminal): `docker ps --filter name=edumap --format "{{.Status}}"`
  - Verify: status shows `(healthy)` after ~30 seconds (HEALTHCHECK passes)
- [ ] **Stop the container**
  - Do: `docker stop edumap`

### 3.3 Azure Container Registry

- [ ] **Create ACR (Basic tier)**
  - Do: `az acr create -g $RG -n $ACR --sku Basic --admin-enabled false`
  - Verify: `az acr show -g $RG -n $ACR --query loginServer` → `<ACR>.azurecr.io`
- [ ] **Log in**
  - Do: `az acr login -n $ACR`
  - Verify: "Login Succeeded"
- [ ] **Tag and push**
  - Do:
    ```powershell
    $LOGIN_SERVER = az acr show -g $RG -n $ACR --query loginServer -o tsv
    docker tag edumap:dev $LOGIN_SERVER/edumap:v1
    docker push $LOGIN_SERVER/edumap:v1
    ```
  - Verify: `az acr repository list -n $ACR` includes `edumap`; `az acr repository show-tags -n $ACR --repository edumap` includes `v1`

### 3.4 Azure Container Apps

- [ ] **Create Log Analytics workspace** (Container Apps and App Insights both write here)
  - Do: `az monitor log-analytics workspace create -g $RG -n $LAW -l $LOCATION`
  - Verify: `az monitor log-analytics workspace show -g $RG -n $LAW --query provisioningState` → `"Succeeded"`
- [ ] **Create the Container Apps environment**
  - Do:
    ```powershell
    $LAW_ID = az monitor log-analytics workspace show -g $RG -n $LAW --query customerId -o tsv
    $LAW_KEY = az monitor log-analytics workspace get-shared-keys -g $RG -n $LAW --query primarySharedKey -o tsv
    az containerapp env create -g $RG -n $CAE -l $LOCATION `
      --logs-workspace-id $LAW_ID --logs-workspace-key $LAW_KEY
    ```
  - Verify: `az containerapp env show -g $RG -n $CAE --query properties.provisioningState` → `"Succeeded"`
- [ ] **Grant ACR pull rights to Container Apps**
  - Do (assigns the system-assigned identity below; for now use admin creds):
    ```powershell
    az acr update -n $ACR --admin-enabled true
    $ACR_USER = az acr credential show -n $ACR --query username -o tsv
    $ACR_PASS = az acr credential show -n $ACR --query "passwords[0].value" -o tsv
    ```
  - Verify: `$ACR_USER` and `$ACR_PASS` are non-empty
- [ ] **Deploy the container app**
  - Do:
    ```powershell
    az containerapp create -g $RG -n $CAPP --environment $CAE `
      --image "$LOGIN_SERVER/edumap:v1" `
      --target-port 8080 --ingress external `
      --registry-server $LOGIN_SERVER --registry-username $ACR_USER --registry-password $ACR_PASS `
      --min-replicas 0 --max-replicas 3
    ```
  - Verify: `az containerapp show -g $RG -n $CAPP --query properties.configuration.ingress.fqdn -o tsv` returns a `<name>.<region>.azurecontainerapps.io` URL
- [ ] **Hit the FQDN in a browser**
  - Verify: map renders, country clicks work
- [ ] **(optional) Update CI/CD to push image and bump container app**
  - Do: extend `.github/workflows/ci-cd.yml` with `azure/docker-login@v1`, `docker build/push`, then `az containerapp update --image ...`
  - Verify: a `git push` to main results in a new ACR tag and a new revision in Container Apps

### 3.5 Application Insights

- [ ] **Create Application Insights** (workspace-based, linked to LAW)
  - Do: `az monitor app-insights component create -g $RG -a $AI -l $LOCATION --workspace $LAW`
  - Verify: `az monitor app-insights component show -g $RG -a $AI --query connectionString` returns a string starting with `InstrumentationKey=…`
- [ ] **Wire connection string into the container app**
  - Do:
    ```powershell
    $AI_CONN = az monitor app-insights component show -g $RG -a $AI --query connectionString -o tsv
    az containerapp update -g $RG -n $CAPP --set-env-vars "APPLICATIONINSIGHTS_CONNECTION_STRING=$AI_CONN"
    ```
  - Verify: `az containerapp show -g $RG -n $CAPP --query "properties.template.containers[0].env[?name=='APPLICATIONINSIGHTS_CONNECTION_STRING'].name"` → `["APPLICATIONINSIGHTS_CONNECTION_STRING"]`
- [ ] **Generate traffic**
  - Do: open the FQDN, click ≥ 10 different countries — give it 2-3 minutes for telemetry to land
- [ ] **Run the KQL query** (Portal → your Log Analytics workspace → Logs)
  - Do: paste:
    ```kusto
    customEvents
    | where name == "CountryClicked"
    | summarize clicks = count() by tostring(customDimensions.iso2)
    | top 10 by clicks
    ```
  - Verify: result shows your most-clicked countries with counts. **This is the deliverable for the monitoring exercise.**
- [ ] **Bonus**: explore the Application Insights Failures and Performance blades. Find the request duration P95 for `/api/countries`.

### 3.6 Alerts

- [ ] **Create an alert rule**
  - Do (Portal): App Insights `$AI` → Alerts → Create → Alert rule
    - Signal: `requests/failed` (Failed requests count)
    - Condition: `Count > 0` over `5 minutes`, evaluation every `1 minute`
    - Action group: create new with email to yourself
    - Severity: 3
    - Name: `edumap-failed-requests`
  - Verify: alert shows up in `az monitor metrics alert list -g $RG`
- [ ] **Force a failure to test the alert**
  - Do: temporarily add `app.MapGet("/boom", () => { throw new InvalidOperationException("alert demo"); });` to `Program.cs`, push, wait for redeploy, then `curl https://<fqdn>/boom` 5 times
  - Verify: within ~5-10 minutes, you receive an alert email
  - **Don't forget**: remove `/boom`, push again to deactivate the alert path

---

## Final verification matrix

When all of the below are ticked, you have completed the full course practical track end-to-end:

| Week | Pass criterion | Status |
|---|---|---|
| 1–2 | Public App Service URL renders the map on phone + desktop. `/health` returns 200. | [ ] |
| 1–2 | Log line says "Loading countries from Blob Storage…" — proves Azure SDK exercise works. | [ ] |
| 3 | `git push` to main → GitHub Actions runs all 4 tests → site updates within 3 minutes. | [ ] |
| 3 | Equivalent Azure Pipelines run goes green and deploys. You can name 2 differences vs GitHub Actions. | [ ] |
| 4 | Container image runs locally, runs in ACR, runs in Container Apps with public FQDN. | [ ] |
| 4 | KQL query in Log Analytics returns top-N clicked countries by ISO2. | [ ] |
| 4 | Alert rule fires an email when you force a 500. | [ ] |

---

## Quick reference

### Local commands

```powershell
# Build & test
dotnet build
dotnet test

# Run the API
cd src/EduMap.Api; dotnet run         # http://localhost:5029

# Build & run the container
docker build -t edumap:dev .
docker run --rm -p 8080:8080 edumap:dev   # http://localhost:8080
```

### Tear-down (when the course is done)

```powershell
# Wipes everything in one shot
az group delete -n $RG --yes --no-wait
```

### Cost ballpark

- App Service Free F1: **$0** (with 60 min/day CPU limit, fine for the course)
- Storage: **<$0.10/month** for the tiny blob and traffic
- ACR Basic: **~$5/month** — delete the resource group when course is over
- Container Apps: **$0** with `min-replicas 0` and low traffic
- Application Insights / Log Analytics: **~$0** on the free 5GB ingest tier

### Known warning you can ignore

`NU1902: Package 'OpenTelemetry.Api' 1.15.1 has a known moderate severity vulnerability` — this came from the `Microsoft.ApplicationInsights.AspNetCore` 3.x package's transitive deps. We pinned to the classic 2.22.0 to avoid this; the warning should now be gone. If it ever reappears via another transitive, suppress with `<NoWarn>$(NoWarn);NU1902</NoWarn>` in the csproj or upgrade.
