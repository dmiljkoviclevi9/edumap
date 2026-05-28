# Developer Pitfalls

Persistent memory of common mistakes in this codebase.
Entries in reverse chronological order. Cap: 200 lines.

Format:
```
## [YYYY-MM-DD] Title
**Context**: What was happening
**Discovery**: What was learned
**Resolution**: What to do about it
```

---

## [2026-05-28] Translation fallback silently passes empty strings as English

**Context**: Script wrote `"funFact": ""` for countries without a Serbian fun fact instead of omitting the field.

**Discovery**: The `tr()` helper in `index.html` uses `(t && t[field]) || country[field]`. Empty string `""` is falsy in JS, so an empty translation falls through to English — but only until some future script or manual edit writes a non-empty value. In the meantime, `""` is silently "correct" even though no translation exists, masking coverage gaps.

**Resolution**: Translation scripts must write `null` or omit the field entirely when no translation is available. Never write `""`. The idempotency check is `== null` (or absent), not a truthiness check.

---

## [2026-05-28] ApplicationInsights v3.x breaks startup when connection string is absent

**Context**: Attempted to upgrade `Microsoft.ApplicationInsights.AspNetCore` from 2.22.0 to 3.x.

**Discovery**: v3.x throws a `NullReferenceException` at startup when `APPLICATIONINSIGHTS_CONNECTION_STRING` is not set in the environment. This breaks both local dev and xUnit tests (which use `WebApplicationFactory<Program>` and have no App Insights connection).

**Resolution**: Pin `Microsoft.ApplicationInsights.AspNetCore` to exactly `2.22.0` in `EduMap.Api.csproj`. v2.x is a no-op when unconfigured. Never upgrade without testing startup behavior and the full xUnit suite without a connection string set.

---

## [2026-05-28] Cyrillic encoding crashes on Windows without python -X utf8

**Context**: Running translation scripts on Windows without the `utf8` flag.

**Discovery**: Python on Windows defaults to cp1252, which cannot encode Cyrillic characters. Any script that prints or writes Serbian Cyrillic text throws `UnicodeEncodeError: 'charmap' codec can't encode character`.

**Resolution**: Always run Python scripts with `python -X utf8 scriptname.py` on Windows. Set `PYTHONUTF8=1` as an environment variable to make it automatic. All translation scripts in `scripts/` depend on this.

---

## [2026-05-28] az ad app create blocked by Levi9 tenant policy

**Context**: Attempting to set up GitHub Actions deployment.

**Discovery**: The Levi9 tenant blocks `az ad app create` for non-admin users. Using a Service Principal / app registration for deployment therefore fails silently or with a permissions error.

**Resolution**: Use a User-Assigned Managed Identity (UAMI) instead. `az identity create` is allowed. The UAMI is federated to the GitHub `production` environment via OIDC. See `ai/knowledge/infrastructure/azure-resources.md` for the full setup.

---

## [2026-05-28] d3-geo winding bug renders country as inverted polygon

**Context**: Some GeoJSON country features render as a filled global polygon (the whole world minus the country) instead of the country shape.

**Discovery**: GeoJSON exterior rings must be counter-clockwise for d3-geo. Features from Natural Earth 50m sometimes have clockwise exterior rings, which d3-geo interprets as "the complement of this polygon on the sphere".

**Resolution**: Apply `rewindFeature()` per polygon (not per feature — MultiPolygon features can have mixed winding between their member polygons). The rewind function is already in `index.html`. If you swap GeoJSON datasets, verify the rewind still catches all affected features.

---

## [2026-05-28] GitHub MCP configured — use it instead of curl for interactive sessions

**Context**: Previously had no GitHub tooling available; curl + python -X utf8 was the only option for checking Actions runs.

**Discovery**: GitHub MCP is now configured via `.mcp.json` (server `github`, URL `https://api.githubcopilot.com/mcp/`, auth via `GITHUB_PAT_EDUMAP` env var). It is available in Claude Code sessions — use its tools for listing runs, checking status, reading PRs, etc.

**Resolution**: In Claude Code interactive sessions, prefer the `github` MCP server over curl boilerplate. The curl polling pattern in `.claude/skills/iterative-azure-deploy/SKILL.md` is still valid and should be kept as the fallback for CI scripts or any context where MCP is unavailable (e.g. automated pipelines, scripts run outside Claude).
