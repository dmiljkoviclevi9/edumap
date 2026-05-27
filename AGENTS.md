# AGENTS.md

Kids' interactive world map. Tap a country → modal shows flag, name, capital, fun fact, plays the name aloud in Serbian. Deployed to Azure App Service via OIDC GitHub Actions. Serbian Cyrillic (`sr-Cyrl`) is the default locale; `?lang=en` is the parent/debug fallback.

**Primary users:** Una (7, reads Cyrillic) and Adi (4, learns via audio).

## Quick start

```powershell
dotnet build
dotnet test
dotnet run --project src/EduMap.Api   # http://localhost:5029
```

## Hard rules — every one has caused a real bug

1. **No `gh` CLI installed.** Use `curl + python -X utf8` for GitHub Actions API calls. Pattern: `.claude/skills/iterative-azure-deploy/SKILL.md`.
2. **Always `python -X utf8`** for any script touching Cyrillic. Windows cp1252 crashes: `UnicodeEncodeError: 'charmap' codec`.
3. **`Microsoft.ApplicationInsights.AspNetCore` pinned to 2.22.0.** v3.x throws on startup without a connection string; xUnit tests break. Never upgrade.
4. **Levi9 tenant blocks `az ad app create`.** Use UAMI (`az identity create`). Never suggest an AD app or service principal.
5. **`sr-Cyrl` is the hardcoded default locale.** Never change `const LANG = ... || "sr-Cyrl"` to `"en"`.
6. **Audio is first-class.** `translations.sr-Cyrl.audioUrl` drives audio playback for Adi (4). Broken audio = broken app for him.

## API contract (locked — do not change shape)

```json
[{
  "iso2": "RS", "name": "Serbia", "capital": "Belgrade",
  "flagUrl": "/flags/rs.svg", "funFact": "Home of Nikola Tesla.",
  "translations": {
    "sr-Cyrl": {
      "name": "Србија", "capital": "Београд",
      "funFact": "Домовина Николе Тесле.",
      "audioUrl": "/audio/sr-Cyrl/rs.mp3"
    }
  }
}]
```

Endpoints: `GET /api/countries`, `GET /api/countries/{iso2}`, `GET /health`, `POST /api/track/{iso2}`.

## Azure resources

| Resource | Name | Value |
|---|---|---|
| Subscription | Damir | `706589ae-fa0c-46d3-957f-e12535bc3deb` |
| Tenant | Levi9 | `40758481-7365-442c-ae94-563ed1606218` |
| Resource group | `rg-edumap` | westeurope |
| App Service | `edumap-miljkovici` | `edumap-miljkovici.azurewebsites.net` |
| UAMI | `mi-edumap-github` | clientId `fe9a3ff5-fbdb-431f-a5c8-3f0e1061f3f4` |
| GitHub repo | `dmiljkoviclevi9/EduMap` | main branch, OIDC-deployed |

## Stack

.NET 10 Minimal API · Vanilla JS + d3-geo (Equal Earth projection, zoom `[1, 32]`) · flag-icons SVGs vendored · GeoJSON self-hosted · xUnit + WebApplicationFactory · Application Insights · GitHub Actions OIDC

## Where to find things

| Task | File |
|---|---|
| Architecture | `PLAN.md` |
| Azure provisioning runbook | `WALKTHROUGH.md` |
| Deferred features (translations, audio) | `FUTURE.md` |
| AI tooling plan | `AI-SDLC-PLAN.md` |
| Deploy + CI/CD cycle + gotchas | `.claude/skills/iterative-azure-deploy/SKILL.md` |
| i18n schema, translation scripts, ElevenLabs audio | `.claude/skills/edumap-localization/SKILL.md` |
| Known error fixes | `.claude/skills/iterative-azure-deploy/references/gotchas.md` |
