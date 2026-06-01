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

1. **GitHub MCP configured** (`.mcp.json`). Use the `github` MCP server for GitHub API calls in interactive Claude sessions. In CI scripts or automated contexts, fall back to `curl + python -X utf8`. Pattern: `.claude/skills/iterative-azure-deploy/SKILL.md`.
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

.NET 10 Minimal API · Vanilla JS + d3-geo (Equal Earth projection, zoom `[1, 256]`) · flag-icons SVGs vendored · GeoJSON self-hosted · xUnit + WebApplicationFactory · Application Insights · GitHub Actions OIDC

## Knowledge layer

`ai/knowledge/` holds stable architecture facts. `ai/memory/` holds durable debugging lessons.
Read `ai/knowledge/INDEX.md` to route any task to the right file in ≤3 pre-reads.
For a compressed primer (context budget constrained): `ai/CHEATSHEET.md`.

After non-trivial work, run `ai/skills/update-repo-knowledge/SKILL.md` to write back
what you learned.

## Where to find things

| Task | File |
|---|---|
| Task → knowledge routing | `ai/knowledge/INDEX.md` |
| Compressed primer | `ai/CHEATSHEET.md` |
| Architecture | `ai/knowledge/architecture/system-overview.md`, `PLAN.md` |
| Data model (Country, CountryTranslation) | `ai/knowledge/architecture/data-model.md` |
| API contract | `ai/knowledge/architecture/api-contracts.md` |
| i18n / locale / audio system | `ai/knowledge/architecture/i18n-model.md` |
| Backend patterns | `ai/knowledge/services/backend-patterns.md` |
| Frontend patterns | `ai/knowledge/services/frontend-patterns.md` |
| Testing patterns | `ai/knowledge/services/testing-patterns.md` |
| Azure resources | `ai/knowledge/infrastructure/azure-resources.md` |
| Deploy + CI/CD cycle + gotchas | `ai/knowledge/infrastructure/deployment-guide.md`, `.claude/skills/iterative-azure-deploy/SKILL.md` |
| i18n scripts, ElevenLabs audio | `.claude/skills/edumap-localization/SKILL.md` |
| Developer pitfalls | `ai/memory/developer-pitfalls.md` |
| Debugging discoveries | `ai/memory/debugging-discoveries.md` |
| Environment / setup notes | `ai/memory/environment-notes.md` |
| Azure provisioning runbook | `WALKTHROUGH.md` |
| Deferred features (translations, audio) | `FUTURE.md` |
| AI tooling plan | `AI-SDLC-PLAN.md` |
| Known error fixes | `.claude/skills/iterative-azure-deploy/references/gotchas.md` |
