# CHEATSHEET — Cheap-Model Primer

**Use this primer when context budget is constrained. Capable models should follow the full [`AGENTS.md`](../AGENTS.md) flow.**

One file, ≤120 lines. Covers ~80% of small changes. For task-specific routing, read [`ai/knowledge/INDEX.md`](knowledge/INDEX.md) next.

## Service

| Entry point | Port (local) | Prod URL |
| --- | --- | --- |
| `src/EduMap.Api/Program.cs` | 5029 | `https://edumap-miljkovici.azurewebsites.net` |

Frontend is vanilla JS served as static files from `src/EduMap.Api/wwwroot/`.

## Data model — 2 C# records

| Type | File | Purpose |
| --- | --- | --- |
| `Country` | `src/EduMap.Api/Models/Country.cs` | Top-level DTO; English is canonical. |
| `CountryTranslation` | same file | Per-locale overrides: Name, Capital, FunFact, AudioUrl. |

Schema source: `src/EduMap.Api/Data/countries.json`. **Always** read the model before touching JSON or endpoints.

## API endpoints — 4 routes (LOCKED — do not change shape)

| Method | Route | Returns |
| --- | --- | --- |
| GET | `/api/countries` | `Country[]` |
| GET | `/api/countries/{iso2}` | `Country` or 404 |
| GET | `/health` | `{"status":"Healthy"}` |
| POST | `/api/track/{iso2}` | 204, fires App Insights event |

## i18n quick facts

- Default locale: `sr-Cyrl` (hardcoded `const LANG = ... || "sr-Cyrl"` — never change to `"en"`).
- `?lang=en` is the parent/debug fallback.
- `tr(country, field)` returns `country.translations[LANG][field] || country[field]` — empty string falls through to English.
- Write `null` or omit fields, never `""`, when no translation exists.
- Audio: `translations.sr-Cyrl.audioUrl` drives playback for Adi (4). Broken audio = broken app for him.

## Where do I look

- **Data contract / model change** → `ai/knowledge/architecture/data-model.md`, `ai/knowledge/architecture/api-contracts.md`
- **Translation / locale / audio work** → `ai/knowledge/architecture/i18n-model.md`, `.claude/skills/edumap-localization/SKILL.md`
- **Backend endpoint or repository change** → `ai/knowledge/services/backend-patterns.md`
- **Frontend / modal / UI** → `ai/knowledge/services/frontend-patterns.md`
- **Tests** → `ai/knowledge/services/testing-patterns.md`
- **Deploy / CI/CD** → `ai/knowledge/infrastructure/deployment-guide.md`, `.claude/skills/iterative-azure-deploy/SKILL.md`
- **Azure resources** → `ai/knowledge/infrastructure/azure-resources.md`
- **Debugging** → `ai/memory/debugging-discoveries.md`, `ai/memory/developer-pitfalls.md`

## Hard constraints (each has caused a real bug)

1. **GitHub MCP configured** (`.mcp.json`). Use the `github` MCP server for GitHub API calls. Fall back to `curl + python -X utf8` for CI scripts.
2. **Always `python -X utf8`** for any script touching Cyrillic. Windows cp1252 crashes.
3. **`Microsoft.ApplicationInsights.AspNetCore` pinned to 2.22.0.** v3.x breaks on startup and breaks xUnit.
4. **Levi9 tenant blocks `az ad app create`.** Use UAMI (`az identity create`). Never suggest an AD app.
5. **`sr-Cyrl` is the hardcoded default locale.** Never change `const LANG = ... || "sr-Cyrl"` to `"en"`.
6. **Audio is first-class.** `translations.sr-Cyrl.audioUrl` drives playback. Broken audio = broken app.
