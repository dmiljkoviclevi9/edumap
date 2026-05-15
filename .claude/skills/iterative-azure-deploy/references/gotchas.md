# Specific error fixes

Failure modes encountered when building and shipping a .NET / Azure App Service / GitHub Actions project — with exact symptom, root cause, and verbatim fix. Load this file when a symptom from the main SKILL.md's "When something goes wrong" list appears.

Each entry is independent. Skip directly to the one you need.

## Build / runtime

### `dotnet build` fails with file lock on a .dll

**Symptom:**
```
error MSB3021: Unable to copy file "...\Azure.Core.dll" to "bin\...\Azure.Core.dll".
The process cannot access the file '...\<App>.Api\bin\Release\net10.0\Azure.Core.dll'
because it is being used by another process.
```

**Root cause:** A previous `dotnet run` didn't fully terminate. The dll is still loaded by an orphan process. Common after Ctrl-C in a terminal that ate the signal, or after Claude Preview was started and not explicitly stopped before the next build.

**Fix (Windows):**
```bash
powershell -NoProfile -Command "Get-Process <App>.Api -ErrorAction SilentlyContinue | Stop-Process -Force"
dotnet clean --configuration Release
dotnet build --configuration Release
```

**Prevention:** Pre-emptively kill the previous instance at the top of any rebuild step. Cheap, idempotent, no false positives.

---

### `Microsoft.ApplicationInsights.AspNetCore` 3.x throws on startup

**Symptom:** Unit tests pass at compile time but `WebApplicationFactory<Program>.CreateClient()` throws during fixture setup:
```
System.InvalidOperationException : A connection string was not found. Please set your connection string.
   at Azure.Monitor.OpenTelemetry.Exporter.Internals.AzureMonitorTransmitter.InitializeConnectionVars
```

**Root cause:** `Microsoft.ApplicationInsights.AspNetCore` versions 3.x are rebuilt on top of OpenTelemetry and refuse to initialize without a connection string. The classic 2.x line silently no-ops when none is configured — which is what tests and local dev need.

**Fix:** Pin to 2.22.0 (or whichever 2.x is current at the time):
```bash
dotnet add <project>.csproj package Microsoft.ApplicationInsights.AspNetCore --version 2.22.0
```

After pinning, `builder.Services.AddApplicationInsightsTelemetry()` can be called unconditionally — it auto-detects "no connection string configured" and does nothing.

**Bonus:** the classic 2.x SDK matches what most Microsoft Learn / AZ-204 course material still shows, so it's better for a training context.

---

### `dotnet test` fails with `FileNotFoundException` for `Data/<file>.json`

**Symptom:**
```
System.IO.FileNotFoundException: Could not find file
  'C:\...\tests\<App>.Api.Tests\bin\Debug\net10.0\Data\countries.json'.
```

**Root cause:** `WebApplicationFactory<Program>` uses the test project's bin directory as the content root, not the API project's. Files marked `Content` + `CopyToOutputDirectory=PreserveNewest` in the API csproj end up in the API's bin, but the test process runs from the test project's bin.

**Fix:** Link the file from the API project into the test project's output via the test csproj:
```xml
<ItemGroup>
  <None Include="..\..\src\<App>.Api\Data\countries.json" Link="Data\countries.json">
    <CopyToOutputDirectory>PreserveNewest</CopyToOutputDirectory>
  </None>
</ItemGroup>
```

The `Link="Data\..."` part is what places it at the expected relative path inside the test bin.

---

### `dotnet new webapi` restore fails with NU1301 / 401

**Symptom:**
```
error NU1301: Response status code does not indicate success: 401 (Unauthorized).
error NU1301: Unable to load the service index for source
  https://pkgs.dev.azure.com/<org>/_packaging/<feed>/nuget/v3/index.json
```

**Root cause:** A corporate Azure DevOps NuGet feed is configured globally (in `%APPDATA%\NuGet\NuGet.Config` or via VS) and requires authentication that the CLI doesn't have. The project template's post-action `dotnet restore` fails because it can't authenticate to a feed it doesn't actually need.

**Fix:** Add a project-local `NuGet.config` at the repo root that clears the global config and adds only the public feed:
```xml
<?xml version="1.0" encoding="utf-8"?>
<configuration>
  <packageSources>
    <clear />
    <add key="nuget.org" value="https://api.nuget.org/v3/index.json" />
  </packageSources>
</configuration>
```

This wins over the user-global config for everything inside the repo. Commit this file.

---

### csproj error NETSDK1022: Duplicate `Content` items

**Symptom:**
```
error NETSDK1022: Duplicate 'Content' items were included. The .NET SDK includes 'Content'
items from your project directory by default.
```

**Root cause:** The Web SDK auto-includes Content items from the project tree. Adding `<Content Include="Data\countries.json">` on top of that creates a duplicate.

**Fix:** Use `<Content Update=...>` (modify the auto-included item) instead of `<Content Include=...>`:
```xml
<ItemGroup>
  <Content Update="Data\countries.json">
    <CopyToOutputDirectory>PreserveNewest</CopyToOutputDirectory>
  </Content>
</ItemGroup>
```

---

## Azure CLI quirks

### `MissingSubscription` from `az role assignment`

**Symptom:**
```bash
az role assignment create --role "Website Contributor" \
  --assignee-object-id <guid> --assignee-principal-type ServicePrincipal \
  --scope "/subscriptions/<sub>/resourceGroups/<rg>/.../Microsoft.Web/sites/<app>"
```
```
ERROR: (MissingSubscription) The request did not have a subscription or
a valid tenant level resource provider.
```

The user has Owner on the subscription (verifiable in the portal under IAM). `az account show` returns the right subscription. The scope string contains the subscription ID. Yet the command errors as if no subscription is set.

**Root cause:** A regression in azure-cli 2.84.0. `az role assignment list/show/create` returns this misleading error on certain scopes. The error name implies a missing subscription parameter, but the actual cause is a bug in how the CLI constructs the request URL.

**Fix:** Bypass `az role assignment` entirely. Call the ARM REST API directly via `az rest`:

```powershell
$SUB        = az account show --query id -o tsv
$WEBAPP_ID  = az webapp show -g $RG -n $APP --query id -o tsv
$WEBSITE_CONTRIB = "/subscriptions/$SUB/providers/Microsoft.Authorization/roleDefinitions/de139f84-1756-47ae-9be6-808fbbe84772"
$GUID = [guid]::NewGuid().Guid
$body = @{
    properties = @{
        roleDefinitionId = $WEBSITE_CONTRIB
        principalId      = $PRINCIPAL_ID
        principalType    = "ServicePrincipal"
    }
} | ConvertTo-Json -Depth 4

az rest --method put `
  --url "https://management.azure.com${WEBAPP_ID}/providers/Microsoft.Authorization/roleAssignments/${GUID}?api-version=2022-04-01" `
  --body $body
```

**Useful built-in role definition IDs:**
- Website Contributor: `de139f84-1756-47ae-9be6-808fbbe84772`
- Contributor: `b24988ac-6180-42a0-ab88-20f7382dd24c`
- Reader: `acdd72a7-3385-48ef-bd42-f606fba81ae7`
- AcrPull: `7f951dda-4ed3-4680-a7ca-43fe172d538d`

To verify the assignment landed (the read-side also hits the same bug in the CLI, so use `az rest` to read too):
```bash
az rest --method get \
  --url "https://management.azure.com${WEBAPP_ID}/providers/Microsoft.Authorization/roleAssignments?api-version=2022-04-01&\$filter=atScope()"
```

---

### AD app creation blocked: "Insufficient privileges"

**Symptom:**
```bash
az ad app create --display-name "github-<app>-deploy"
```
```
ERROR: Directory permission is needed for the current user to register the application.
Original error: Insufficient privileges to complete the operation.
```

The user has subscription Owner. Their `az ad app list` works. But create fails.

**Root cause:** Most corporate tenants (Levi9 included) restrict Microsoft Entra ID app registration to admins via a tenant-wide policy. This is a *separate permission* from any subscription role — Owner on a subscription does not grant rights to create AD apps.

**Fix:** Don't create an AD application. Use a **User-Assigned Managed Identity (UAMI)** instead. UAMIs are resource group-scoped Azure resources, so subscription Contributor / RG Owner is sufficient to create one — no tenant-admin involvement needed.

```bash
# 1. Create the UAMI
az identity create -g <rg> -n mi-<app>-github -l <location>
# Note the clientId and principalId from the output

# 2. Grant it the Azure RBAC role it needs (use the az rest workaround above
#    if `az role assignment create` errors with MissingSubscription)

# 3. Create the federated credential (this is what makes it OIDC-able)
az identity federated-credential create \
  -g <rg> --identity-name mi-<app>-github \
  --name github-prod \
  --issuer "https://token.actions.githubusercontent.com" \
  --subject "repo:<owner>/<repo>:environment:production" \
  --audiences "api://AzureADTokenExchange"
```

In GitHub Actions, the `azure/login@v2` action authenticates against a UAMI exactly like it would against an AD app's service principal — same `client-id`, `tenant-id`, `subscription-id` inputs.

**Federation subject patterns** (the `--subject` value must match exactly):
- For an environment-scoped workflow: `repo:<owner>/<repo>:environment:<env-name>`
- For a branch-scoped workflow: `repo:<owner>/<repo>:ref:refs/heads/<branch>`
- For pull requests: `repo:<owner>/<repo>:pull_request` (rarely a good idea — PRs from forks shouldn't deploy)

Use environment-scoped whenever the workflow has `environment: <name>` on the job. It's the most precise scope and matches GitHub's mental model of production.

---

## App Service deployment

### `az webapp deploy --type zip` fails with `Invalid argument (22)` rsync errors

**Symptom:** Upload succeeds but unpack on App Service fails. Logs show many lines like:
```
rsync: [generator] recv_generator: failed to stat "...wwwroot\flags\rs.svg": Invalid argument (22)
```

**Root cause:** PowerShell's `Compress-Archive` and `[System.IO.Compression.ZipFile]::CreateFromDirectory` write zip entries with **backslashes** on Windows. App Service runs on Linux. Linux's unzipper reads `wwwroot\flags\rs.svg` as one filename containing literal backslashes — confusing rsync.

**Fix #1 (build the zip with forward slashes):**
```powershell
Remove-Item ./publish.zip -ErrorAction SilentlyContinue
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip  = [System.IO.Compression.ZipFile]::Open((Join-Path (Get-Location) 'publish.zip'), 'Create')
$root = (Resolve-Path ./publish).Path
Get-ChildItem ./publish -Recurse -File | ForEach-Object {
  $rel = $_.FullName.Substring($root.Length + 1).Replace('\','/')
  [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, $_.FullName, $rel) | Out-Null
}
$zip.Dispose()

az webapp deploy -g $RG -n $APP --src-path ./publish.zip --type zip
```

Verify the zip is sane before deploying — entries should show forward slashes:
```powershell
[System.IO.Compression.ZipFile]::OpenRead((Resolve-Path ./publish.zip).Path).Entries |
  Where-Object { $_.FullName -match 'flags' } |
  Select-Object -First 3 -ExpandProperty FullName
# Expected: wwwroot/flags/ad.svg ... NOT wwwroot\flags\ad.svg
```

**Fix #2 (the actual right answer):** Don't deploy from Windows. Set up GitHub Actions with `azure/webapps-deploy@v3` from `ubuntu-latest`. The Linux runner's zipper writes correct paths natively, and you get OIDC auth + reproducibility for free. This is what the cycle in the main SKILL.md assumes you're doing — the only reason to deploy from Windows is bootstrap (the very first deploy, before CI/CD is wired up).

**Fix #3 (escape hatch):** `az webapp up` uses Microsoft's own (correct) zipper internally:
```bash
az webapp up -g $RG -n $APP --runtime "DOTNETCORE:10.0" --os-type Linux --plan $PLAN --sku F1
```
Less educational than the manual zip path; useful when you've already done the manual path once for learning and now just want it to work.

---

## Frontend / d3-geo

### Polygons paint the whole sphere — one country covers the world

**Symptom:** After switching from Leaflet to d3-geo with `geoEqualEarth()` (or any other projection), one or more countries' rendered paths cover the **entire SVG viewport** instead of their actual shape. Diagnostic test:
```javascript
const zt = document.querySelector('.zoom-target').getBBox();
const giants = [...document.querySelectorAll('path.country')]
  .map(p => ({ data: p.__data__?.properties?.ADMIN, bb: p.getBBox() }))
  .filter(o => (o.bb.width * o.bb.height) / (zt.width * zt.height) > 0.9);
// If `giants` has entries, you have this bug
```

**Root cause:** d3-geo follows RFC 7946: **counterclockwise rings are exteriors, clockwise rings are holes**. Many older GeoJSON files (notably some UK home-nations overlays, but also occasional Natural Earth subsets) ship clockwise exteriors. Under the new rule, a CW exterior is read as a hole **on the sphere** — which paints everything *except* the polygon. The polygon's bounding box is approximately the whole world.

**Critical insight: rewinding must be per polygon, not per feature.** A MultiPolygon can have a mix of correctly-wound and wrong-wound polygons. England's MultiPolygon, for example, had 565 correctly-wound polygons and 1 wrong-wound one. A per-feature rewind decision flips ALL of them — turning 1 wrong into 565 wrong. Per-polygon is the only correct approach.

**Fix:** Rewind per polygon, using `d3.geoArea` on each polygon individually:
```javascript
function rewindPolygon(rings){
  // rings = [outer, hole1, hole2, ...]
  const probe = { type: "Polygon", coordinates: rings };
  if (d3.geoArea(probe) > 2 * Math.PI) {
    rings.forEach(r => r.reverse());
  }
}

function rewindFeature(feature){
  if (!feature || !feature.geometry) return feature;
  if (feature.geometry.type === "Polygon") {
    rewindPolygon(feature.geometry.coordinates);
  } else if (feature.geometry.type === "MultiPolygon") {
    feature.geometry.coordinates.forEach(rewindPolygon);
  }
  return feature;
}

function rewindFeatures(geojson){
  if (geojson?.features) geojson.features.forEach(rewindFeature);
  return geojson;
}
```

Call `rewindFeatures(geojson)` immediately after each `fetch().then(r => r.json())` and before `d3.geoPath(projection)`. It's idempotent on correctly-wound polygons — safe to apply unconditionally to every GeoJSON the page loads.

---

### External GeoJSON fetch hangs on corporate proxy

**Symptom:** Page stuck on "Loading…" indefinitely. DevTools Network tab shows local API calls (`/api/countries`) completed in 250 ms, but a fetch to `https://raw.githubusercontent.com/...` is either missing or pending forever. The page loaded fine, d3 loaded fine, but the data fetch never completes.

**Root cause:** Corporate proxies (Levi9, many enterprise networks) aggressively rate-limit or block `raw.githubusercontent.com`, especially for large files (anything over a few MB). The page's `Promise.all` waits forever because the GeoJSON fetch never resolves.

**Fix:** Self-host the GeoJSON in `wwwroot/data/`. Same-origin, no CORS, no proxy interference. Use Natural Earth 50m for a good size/quality tradeoff:
```bash
curl -sL -o src/<App>.Api/wwwroot/data/countries.geojson \
  https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_50m_admin_0_countries.geojson
```

That gets you a ~3 MB file (vs 14.6 MB for 10m, vs 250 KB for 110m). 50m is the sweet spot — visually indistinguishable from 10m at world view, slightly smoothed at max zoom, but no Vatican/Monaco-disappears problem like 110m has.

In the frontend, change `GEO_URL` to `/data/countries.geojson`. Property names match what `resolveIso` already handles (`ISO_A2`, with name-based fallback for `-99` entries like Norway/Kosovo/France).

**Bonus:** the per-polygon rewind from the previous gotcha applies here too — apply it to the new dataset just in case.

---

## Python / cross-platform

### Python script crashes on Cyrillic / non-ASCII output

**Symptom:** Script processes non-ASCII strings fine internally, but crashes on `print()` or `json.dumps()` to stdout:
```
UnicodeEncodeError: 'charmap' codec can't encode characters in position N-N: character maps to <undefined>
```

**Root cause:** Windows Python defaults to the cp1252 console codec, which lacks Cyrillic, CJK, emoji, and most non-Latin scripts. Any data containing those breaks `print()`. This happens with translated country names, Wikidata SPARQL responses, GitHub commit messages with diacritics, and many other places.

**Fix:** Always run scripts that may emit non-ASCII with `-X utf8`:
```bash
python -X utf8 script.py
```

Or set it once per shell:
```powershell
$env:PYTHONUTF8 = "1"
```

For one-liners in bash:
```bash
echo '{...}' | python -X utf8 -c "import sys,json; print(json.dumps(json.load(sys.stdin), ensure_ascii=False, indent=2))"
```

**Prevention:** Use `-X utf8` *unconditionally* for any script in this project family — even ones you think don't touch non-ASCII. The cost of adding the flag is zero, the cost of debugging the encoding crash mid-deploy is high (we hit this exact bug twice in the same session before adding the flag everywhere).

---

### File paths: Windows backslashes vs forward slashes in scripts

**Symptom:** Bash + Python on Windows misbehave when paths mix `/c/REPOS/...` (Git Bash style) with `C:\REPOS\...` (Windows style). Python's `open()` and `os.path` accept both, but bash's `ls` and `cp` work better with the Git Bash style.

**Fix:** Inside Python scripts, use Windows-style raw paths:
```python
open(r'C:\REPOS\EduMap\src\EduMap.Api\Data\countries.json', encoding='utf-8')
```

Inside bash commands, use Git Bash style:
```bash
ls /c/REPOS/EduMap/src/EduMap.Api/Data/
```

Mixing the two within a single one-liner is what burns; pick one and stick with it for that command.

---

## Cross-references

The main `SKILL.md` references this file by symptom. If you hit a failure mode that's not listed here:

1. First check whether the symptom is a known surface-level form of one of the above — e.g. `MissingSubscription` from `az role assignment list` is the same root cause as the create variant.
2. If genuinely new, add it here in the same Symptom / Root cause / Fix format before moving on. Future-you will thank you.
