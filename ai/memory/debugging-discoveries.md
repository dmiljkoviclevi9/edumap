# Debugging Discoveries

Persistent memory of bugs found, root causes, and resolution patterns.
Entries in reverse chronological order. Cap: 200 lines.

Format:
```
## [YYYY-MM-DD] Title
**Context**: What was happening
**Discovery**: Root cause
**Resolution**: What fixed it
```

---

## [2026-05-28] Countries with no translations show English even when sr-Cyrl is active

**Context**: ~240 countries in `countries.json` have no `translations` block after the initial i18n scaffolding commit.

**Discovery**: Expected behavior — `tr()` falls back to the English top-level fields when `translations` is absent. Not a bug, but can look like a bug if you assume full Cyrillic coverage.

**Resolution**: Run Chunk B (CLDR + Wikidata bulk translation) to fill names + capitals. Run Chunk C (Azure Translator) for fun facts. Run Chunk D (ElevenLabs) for audio. Track progress with: `curl /api/countries | python -X utf8 -c "import sys, json; d=json.load(sys.stdin); print(sum(1 for c in d if c.get('translations',{}).get('sr-Cyrl',{}).get('name')))"`.

---

## [2026-05-28] geojson 404 in local dev — .geojson not a registered MIME type

**Context**: Map failed to load `data/countries.geojson` locally with a 404.

**Discovery**: `app.UseStaticFiles()` refuses to serve files with unregistered extensions. `.geojson` is not in the default MIME type registry.

**Resolution**: Already fixed in `Program.cs`:
```csharp
var staticFileTypes = new FileExtensionContentTypeProvider();
staticFileTypes.Mappings[".geojson"] = "application/geo+json";
app.UseStaticFiles(new StaticFileOptions { ContentTypeProvider = staticFileTypes });
```
If you add other non-standard file types to `wwwroot/`, add their MIME types here too.

---

## [2026-05-28] iOS Safari blocks audio playback when not in sync task

**Context**: Refactoring `openModal()` to use async/await broke audio playback on iOS Safari.

**Discovery**: iOS Safari requires that `audio.play()` is called synchronously within the same task as the user gesture (the tap). Calling it after any `await` — even a trivially fast one — causes the browser to block autoplay.

**Resolution**: Keep the `Audio` construction and `.play()` call synchronous, before any `await`. The `.catch(() => {})` wrapper suppresses the DOMException silently in cases where autoplay is blocked. Do not restructure `openModal()` to be async unless you verify iOS Safari behavior first.

---

## [2026-05-28] WebApplicationFactory startup fails if CountryRepository can't find countries.json

**Context**: Running tests in an environment where `AppContext.BaseDirectory` doesn't include the `Data/` folder.

**Discovery**: `CountryRepository` calls `app.Services.GetRequiredService<CountryRepository>()` at startup for fail-fast behavior. If the JSON file is missing, the app throws before any test request can be made, and `WebApplicationFactory` surfaces a confusing exception.

**Resolution**: Ensure `countries.json` has `<CopyToOutputDirectory>Always</CopyToOutputDirectory>` in the `.csproj`. Check the `Data/` folder is present next to the DLL in the test output directory. This is already set correctly in `EduMap.Api.csproj`.
