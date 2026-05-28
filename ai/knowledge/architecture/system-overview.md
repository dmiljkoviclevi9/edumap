# System Overview

## What Edu-Map Is

A children's interactive world map. Tap a country → modal shows flag, name,
capital, fun fact, plays the country name aloud in Serbian. Primary audience:
Una (7, reads Cyrillic) and Adi (4, learns via audio).

Deployed live at `https://edumap-miljkovici.azurewebsites.net`.

## Architecture

Single-process .NET 10 Minimal API that:
1. Loads `countries.json` into memory at startup via `CountryRepository` (singleton).
2. Serves four HTTP endpoints (see `ai/knowledge/architecture/api-contracts.md`).
3. Serves the static frontend from `wwwroot/` via `app.UseStaticFiles()`.

No database. No background jobs. No message bus.

```
Browser
  └─ index.html + vanilla JS (d3-geo, Equal Earth projection)
       ├─ fetch /api/countries        → Country[] with translations
       ├─ POST  /api/track/{iso2}     → fire-and-forget App Insights event
       └─ GET   /audio/sr-Cyrl/*.mp3 → served as static files from wwwroot/audio/
Azure App Service (edumap-miljkovici, Free F1, Linux, westeurope)
  └─ EduMap.Api.dll
       ├─ CountryRepository (singleton, loads countries.json)
       ├─ Application Insights SDK (auto-instrumented + custom CountryClicked event)
       └─ wwwroot/
            ├─ index.html          (map + modal + i18n)
            ├─ flags/              (vendored flag-icons SVGs, ~250 files)
            ├─ audio/sr-Cyrl/      (ElevenLabs TTS MP3s, ~15 KB each)
            └─ data/               (world GeoJSON + UK nations GeoJSON, self-hosted)
```

## Data source

`src/EduMap.Api/Data/countries.json` — ~250 countries, English at top level,
`translations.sr-Cyrl` filled in incrementally. `CountryRepository` prefers
Azure Blob Storage when `Storage:ConnectionString` + `Storage:CountriesBlobName`
are configured; falls back to the embedded file otherwise.

## Key design decisions

- **Contract-first.** The JSON shape was locked before the C# DTO was written.
  Never change the API response shape without reading `ai/knowledge/architecture/api-contracts.md`.
- **Static JSON, no DB.** Country data fits in memory. SQL is unnecessary complexity.
- **`sr-Cyrl` default, English fallback.** The frontend `tr()` helper always
  falls back to English top-level fields. Write `null` / omit fields rather than `""`.
- **Audio is first-class.** `translations.sr-Cyrl.audioUrl` drives playback for
  a 4-year-old who cannot read. Broken audio is a UX regression for a specific child.
- **GitHub MCP configured** (`.mcp.json`). Use the `github` MCP server for GitHub API
  calls in interactive sessions. CI scripts fall back to `curl` + `python -X utf8`.
  See `.claude/skills/iterative-azure-deploy/SKILL.md`.
