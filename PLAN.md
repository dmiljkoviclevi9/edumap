# Edu-Map: Plan optimized for the Levi9 Azure & .NET course

## Context

You're starting the Levi9 4-week Azure & .NET course and need a hands-on project that exercises every checkpoint (App Service deploy, GitHub Actions CI/CD, Docker + ACR, Application Insights). The project doubles as something you can show your kids: an interactive world map where they tap a country and see its flag, name, and capital city. The map is colorful but text-free — discovery happens through interaction, which suits both a child's reading level and the "borders only" aesthetic you described.

The core design constraint is a **contract-first workflow**: Claude generates the frontend with a mock JSON structure → that structure becomes the C# DTO → the .NET API mirrors it exactly → the only frontend change to "go live" is swapping a `const data = {...}` for a `fetch()`. This keeps backend complexity minimal and lets you focus on Azure-side work, which is where the course points are.

This plan adds course-optimization choices that the bare app doesn't strictly need but that make each week's exercise meaningful: a unit test project (so GitHub Actions has something to run), structured logging (so Log Analytics looks alive), Application Insights custom events (so the click-tracking demo lands), and a multi-stage Dockerfile (so ACR isn't trivial).

## Tech stack & key decisions

| Layer | Choice | Why |
|---|---|---|
| Backend | .NET 8 Minimal API | Course is .NET-centric; minimal API keeps `Program.cs` short and demoable |
| Frontend | Vanilla JS + Leaflet.js (CDN) | No build step → trivially served from `wwwroot`; mobile pinch-zoom is built-in |
| Map polygons | `world-atlas` TopoJSON (CDN) | ~250KB, ISO-3166 codes, no licensing fuss |
| Country data | Static JSON in repo (`countries.json`) | "In-memory DB" the user wanted; ~250 rows fits in memory trivially |
| Flags | Bundled `flag-icons` SVGs, vendored into `wwwroot/flags/` | Self-hosted, renders identically on Windows/iOS/Android, no external CDN dependency at runtime. ~3MB of SVGs committed to the repo. |
| Tests | xUnit + `WebApplicationFactory<Program>` | Real HTTP-level test; gives CI workflow something substantive to run |
| Telemetry | `Microsoft.ApplicationInsights.AspNetCore` | Auto-instruments + custom events for clicks |
| Container | Multi-stage Dockerfile, `mcr.microsoft.com/dotnet/aspnet:8.0` runtime | Standard pattern; smaller final image than SDK-based |
| Hosting (W1–2) | Azure App Service, Free F1 (Linux) | Free tier; covers VS Code deploy and `az webapp` CLI |
| Hosting (W4) | Azure Container Apps | Modern; scale-to-zero saves money during course |

## Project layout

```
EduMap/
├── EduMap.sln
├── src/EduMap.Api/
│   ├── EduMap.Api.csproj
│   ├── Program.cs                  # Minimal API, ~80 lines
│   ├── Models/Country.cs           # DTO matching the locked JSON schema
│   ├── Services/CountryRepository.cs  # Loads countries.json on startup
│   ├── Data/countries.json         # ~250 rows (ISO2, name, capital, flag)
│   └── wwwroot/                    # Output of the Claude design prompt
│       ├── index.html
│       ├── app.js
│       ├── styles.css
│       └── flags/                  # Vendored from flag-icons (4x3 SVGs)
│           ├── rs.svg
│           ├── de.svg
│           └── ...                 # ~250 files, committed
├── tests/EduMap.Api.Tests/
│   ├── EduMap.Api.Tests.csproj
│   └── EndpointTests.cs            # GET /api/countries returns 200, has Serbia, etc.
├── .github/workflows/ci-cd.yml     # Week 3
├── Dockerfile                      # Week 4
├── .dockerignore
└── README.md
```

## API contract (the schema you'll lock)

The Claude design prompt below produces a frontend that consumes exactly this shape. Your C# `Country` DTO mirrors it verbatim.

```jsonc
// GET /api/countries
[
  {
    "iso2": "RS",
    "name": "Serbia",
    "capital": "Belgrade",
    "flagUrl": "/flags/rs.svg",                 // served by ASP.NET static files from wwwroot/flags/
    "funFact": "Home of Nikola Tesla."          // optional, kid-friendly
  },
  ...
]

// GET /api/countries/{iso2}    → single Country object, 404 if unknown
// GET /health                  → { "status": "Healthy" }    (App Service & alerts)
```

Telemetry — no separate clicks endpoint. The frontend POSTs `/api/track/{iso2}`, which **does nothing but emit an App Insights custom event** (`CountryClicked` with `iso2` property). Week 4 telemetry exercise pulls the "top countries" report from App Insights / Log Analytics with a KQL query — that's the more authentic Azure experience than rolling your own counter.

## Week-by-week mapping

### Week 1–2 — Foundation

1. `dotnet new sln -n EduMap`, `dotnet new webapi --use-minimal-apis -o src/EduMap.Api`
2. Drop the Claude-generated `index.html`/`app.js`/`styles.css` into `wwwroot`. Enable `app.UseDefaultFiles(); app.UseStaticFiles();`
3. **Vendor flag SVGs:** download the [flag-icons](https://github.com/lipis/flag-icons) latest release, copy `flags/4x3/*.svg` into `src/EduMap.Api/wwwroot/flags/`, commit. (Optionally script this in `scripts/fetch-flags.ps1` so it's reproducible.)
4. Add `countries.json`, `Country.cs`, `CountryRepository.cs` (singleton, loads JSON at startup).
5. Three endpoints: `GET /api/countries`, `GET /api/countries/{iso2}`, `GET /health`.
6. Swap the frontend's `const COUNTRIES = [...]` for `fetch('/api/countries')`. **This is the contract handover.**
7. Add `ILogger` calls (`logger.LogInformation("Loaded {Count} countries", ...)`) so Log Analytics has structure to surface in W4.
8. Deploy via VS Code "Deploy to Web App" → Azure App Service Free F1 Linux. Repeat once via `az webapp up` to cover the CLI path the course expects.
9. **Azure SDK for .NET checkpoint** (the third link in your Week 1–2 brief): wire `CountryRepository` to prefer Blob Storage when configured.
   - `dotnet add package Azure.Storage.Blobs`
   - On startup: if `Storage:ConnectionString` and `Storage:CountriesBlobName` are present in config, fetch the blob via `BlobClient.DownloadContentAsync()` and deserialize. Otherwise fall back to the embedded `Data/countries.json`.
   - Provision a Storage Account in Azure, upload the JSON, set the connection string in App Service Configuration.
   - This justifies the SDK link, gives you a second Azure resource, and demonstrates the config-driven swap pattern without breaking local dev.

**Verification:** Hit the public App Service URL on phone + desktop; tap a country; modal shows flag/name/capital. `curl https://<app>.azurewebsites.net/health` returns 200.

### Week 3 — CI/CD

`.github/workflows/ci-cd.yml`:

```yaml
on: [push, workflow_dispatch]
jobs:
  build-test-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-dotnet@v4
        with: { dotnet-version: '8.0.x' }
      - run: dotnet restore
      - run: dotnet test --no-restore --logger trx
      - run: dotnet publish src/EduMap.Api -c Release -o ./publish
      - uses: azure/webapps-deploy@v3
        with:
          app-name: ${{ secrets.AZURE_WEBAPP_NAME }}
          publish-profile: ${{ secrets.AZURE_PUBLISH_PROFILE }}
          package: ./publish
```

Add **at least 3 xUnit tests** in `EduMap.Api.Tests` so the test step is meaningful: countries list non-empty; known ISO2 returns 200 with expected capital; unknown ISO2 returns 404. Use `WebApplicationFactory<Program>` (requires `public partial class Program {}` at the bottom of `Program.cs`).

Then repeat the equivalent pipeline in Azure Pipelines (`azure-pipelines.yml`) to cover the third Week-3 link. Same stages, different YAML dialect — good comparison exercise.

**Verification:** Push a change to a country's capital → workflow runs → site updates within ~2 minutes.

### Week 4 — Containerization & Monitoring

**Containerize:**

```dockerfile
FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src
COPY *.sln .
COPY src/EduMap.Api/EduMap.Api.csproj src/EduMap.Api/
RUN dotnet restore src/EduMap.Api/EduMap.Api.csproj
COPY . .
RUN dotnet publish src/EduMap.Api -c Release -o /app

FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS runtime
WORKDIR /app
COPY --from=build /app .
EXPOSE 8080
ENV ASPNETCORE_URLS=http://+:8080
HEALTHCHECK CMD curl -f http://localhost:8080/health || exit 1
ENTRYPOINT ["dotnet", "EduMap.Api.dll"]
```

1. Build locally → `docker run` → confirm map renders.
2. Create ACR: `az acr create -n edumapacr ...`. Tag and push.
3. Deploy to **Azure Container Apps** (or App Service for Containers if you want continuity with Week 1). Update the Week-3 workflow to: build image → push to ACR → `az containerapp update --image ...`.

**Monitor:**

1. `dotnet add package Microsoft.ApplicationInsights.AspNetCore`. Add `builder.Services.AddApplicationInsightsTelemetry()` and pull the connection string from app settings.
2. In the `/api/track/{iso2}` endpoint, inject `TelemetryClient` and call `client.TrackEvent("CountryClicked", new Dictionary<string,string>{{"iso2", iso2}});`.
3. Frontend fires `fetch('/api/track/' + iso2, {method:'POST'})` after a country tap.
4. After exercising the app, run this KQL in Log Analytics:
   ```kusto
   customEvents
   | where name == "CountryClicked"
   | summarize clicks = count() by tostring(customDimensions.iso2)
   | top 10 by clicks
   ```
5. Configure one **Alert rule**: "fire when `requests/failed` > 0 over 5 min" — covers the alerts learning module link.

**Verification:** Container running on Container Apps; KQL shows clicks aggregated by country; an artificially-induced 500 triggers the alert email.

## The Claude Design prompt

Paste the block below into [claude.ai](https://claude.ai/) (Artifact mode). It produces a single self-contained HTML file. Drop the resulting `index.html`/JS/CSS into `wwwroot/` once you're happy.

````
Build a single self-contained HTML file (inline CSS + JS, no build step) called
"Edu-Map" — a children's interactive world map. Target audience: kids aged 5–10.
The page must work equally well on a desktop browser and on a phone in portrait.

VISUAL DESIGN
- Full-viewport map, no header, no footer, no menus. The map IS the page.
- Country fills are bright, child-friendly, saturated colors (think
  picture-book palette: coral, sunny yellow, leaf green, sky blue, lilac,
  peach). Adjacent countries must always have visibly different colors —
  use a graph-coloring approach or a deterministic hash of ISO2 → palette
  index, then nudge if neighbors collide.
- Country borders: 1px solid #222 (slightly thicker on touch devices).
- NO text labels anywhere on the map. No country names, no capitals, no
  legends. Discovery is purely by interaction.
- Ocean is a single calm color (#cfeaf6).
- On hover (desktop) or touch-press (mobile), the country fill darkens
  by ~15% as feedback.

MAP TECH
- Use Leaflet.js from CDN (unpkg).
- Use this country-polygons GeoJSON from CDN — pick one and stick to it:
  https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson
  (each feature has properties.ISO_A2 — that's the join key).
- Disable the default Leaflet tile layer; we want pure SVG polygons on a
  flat ocean color, not a street map.
- Default view: world-fit on load. Pinch-zoom on mobile, scroll-zoom on
  desktop. minZoom that still shows the whole world; maxZoom ~6.
- No attribution badge if licensing allows it; otherwise tiny and
  unobtrusive.

INTERACTION
- Tap/click a country → modal pops up centered, ~80% width on mobile,
  max 420px on desktop, with rounded corners and a soft shadow.
- Modal contents, in order: large flag (centered, ~200px wide), country
  name in big rounded sans-serif (e.g. "Nunito" from Google Fonts, weight
  800), capital city below in smaller weight, optional one-sentence
  funFact in italic if present. Big circular close button top-right.
- Tapping outside the modal or pressing Esc dismisses it.
- After a country is tapped, fire `fetch('/api/track/' + iso2, {method:'POST'})`
  and ignore the response (fire-and-forget; wrapped in try/catch so it
  never breaks the UI).

DATA — MOCK FOR NOW
Use this exact JSON shape, inline as `const COUNTRIES = [...]`. Include
~15 sample entries spanning continents (Serbia, Germany, Japan, Brazil,
Egypt, Australia, USA, etc.). The shape is the contract; do not deviate.

  [
    {
      "iso2": "RS",
      "name": "Serbia",
      "capital": "Belgrade",
      "flagUrl": "/flags/rs.svg",
      "funFact": "Home of Nikola Tesla."
    }
  ]

flagUrl is a relative path. The flags will be self-hosted at
/flags/{iso2-lowercase}.svg (vendored from the flag-icons npm package
into wwwroot/flags/). For your mock preview to actually show flags in
the artifact sandbox, fall back to the public flag-icons CDN when the
local path 404s — wrap the <img> with onerror that retries against
https://cdn.jsdelivr.net/npm/flag-icons/flags/4x3/{iso2-lowercase}.svg
so the mock looks right in the Claude artifact preview AND will Just
Work when the file is later served from the .NET wwwroot.

When a country in the GeoJSON has no matching entry in COUNTRIES, the
country still renders (colored, with border) but tapping it shows a
small "Coming soon!" toast instead of a modal — never an error.

LATER (do NOT implement, but leave a TODO comment): replace the inline
COUNTRIES constant with `const COUNTRIES = await fetch('/api/countries').then(r=>r.json());`

ACCESSIBILITY & POLISH
- Tap targets: countries are large polygons so this is fine, but ensure
  the modal close button is at least 44×44px.
- prefers-reduced-motion respected (no zoom animation if set).
- Loading state: a centered spinner while the GeoJSON downloads.
- Works offline once cached (no fancy service worker, just inline what
  you can; CDN deps are fine).

DELIVERABLE
One HTML file. Inline `<style>` and `<script>`. No frameworks (no React,
no build tools). Comments where non-obvious. End the file with a brief
comment block listing every external CDN URL used so I can audit.
````

## Critical files to create

- [src/EduMap.Api/Program.cs](src/EduMap.Api/Program.cs) — Minimal API host
- [src/EduMap.Api/Models/Country.cs](src/EduMap.Api/Models/Country.cs) — DTO locking the contract
- [src/EduMap.Api/Services/CountryRepository.cs](src/EduMap.Api/Services/CountryRepository.cs) — JSON loader, singleton
- [src/EduMap.Api/Data/countries.json](src/EduMap.Api/Data/countries.json) — Canonical data
- [src/EduMap.Api/wwwroot/index.html](src/EduMap.Api/wwwroot/index.html) — Claude output
- [tests/EduMap.Api.Tests/EndpointTests.cs](tests/EduMap.Api.Tests/EndpointTests.cs) — xUnit + WebApplicationFactory
- [.github/workflows/ci-cd.yml](.github/workflows/ci-cd.yml) — Week 3
- [Dockerfile](Dockerfile) — Week 4

## End-to-end verification per week

| Week | Pass criteria |
|---|---|
| 1–2 | Public App Service URL renders the map on iPhone Safari and desktop Chrome. Tapping Serbia shows flag + "Belgrade". `/health` returns 200. ILogger output visible in App Service log stream. |
| 3 | Editing `countries.json` and pushing → workflow goes green → live site updates in ≤ 3 min. Test step actually runs the 3 xUnit tests. Equivalent Azure DevOps pipeline runs in parallel. |
| 4 | Container image runs locally, runs in ACR, runs in Container Apps. KQL query in Log Analytics returns top-10 clicked countries. Alert fires on a forced 500. |

## Resolved choices

- **Flags:** Bundled `flag-icons` SVGs vendored into `wwwroot/flags/`. The Claude design prompt references `/flags/{iso2}.svg` with a CDN fallback so the artifact preview still renders correctly.
- **Azure SDK exercise:** Included in Week 1–2. `CountryRepository` prefers Blob Storage when configured, falls back to the embedded JSON.
