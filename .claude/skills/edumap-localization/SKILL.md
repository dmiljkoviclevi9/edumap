---
name: edumap-localization
description: Use when adding translations, locales, or audio to the EduMap project — anything that touches the `Country.Translations` dictionary, the frontend's `tr()` helper, the `UI_STRINGS` table, the `?lang=` URL parameter, or the `wwwroot/audio/` directory. Triggers strongly on phrases like "add a Spanish locale", "translate the rest of the countries", "bulk translate fun facts", "generate audio for all countries", "why is country X still showing English", "add a new language", "extend the translations", or any user request to edit `countries.json` with locale-specific data. Also trigger when the user mentions Azure Translator, Azure Speech / TTS, CLDR, Wikidata, or BCP-47 in the EduMap context. Bias strongly toward triggering — the locale system has specific schema conventions (English-as-canonical-fallback, BCP-47 keys, idempotency-on-overwrite, per-locale UI strings) that are non-obvious and easy to get wrong, and the bundled scripts in this skill's `scripts/` directory are ready-to-run tools that save 1-2 hours of work per chunk versus rediscovering the API patterns from FUTURE.md.
---

# EduMap localization workflow

This skill captures everything specific to adding or extending locale support in EduMap — schema, frontend rendering, bulk translation pipelines, and audio playback. The locale system was designed for Serbian Cyrillic (the kids' first language) but the architecture supports any BCP-47 tag.

The canonical reference for the broader feature plan is `FUTURE.md` at the repo root. This skill is the **executable companion** to that plan: it has the scripts and the up-to-date conventions. If `FUTURE.md` and this skill ever disagree, the skill wins for tactics; the plan wins for strategy. Update both when something changes.

## When this applies

This skill is specific to EduMap (a .NET 10 Minimal API + d3-geo static frontend deployed to Azure App Service). Don't run it on other localization tasks — the schema shape is project-specific.

Apply it when:
- Adding a new locale (e.g., bilingual support for relatives — Spanish, English-as-default, Russian)
- Extending an existing locale's coverage (e.g., bringing `sr-Cyrl` from 12 hand-curated countries to all 251)
- Generating or replacing audio clips for country names
- Debugging "why is country X showing English instead of Serbian"
- Adjusting the locale-fallback behaviour or default

## The contract — `Country.Translations` schema

The canonical English fields stay at the top level. Translations live under `translations`, keyed by BCP-47 tag.

```jsonc
// src/EduMap.Api/Data/countries.json
{
  "iso2": "MR",
  "name": "Mauritania",                   // canonical English; never translated in place
  "capital": "Nouakchott",                // ditto
  "flagUrl": "/flags/mr.svg",
  "funFact": "Has trains 2 km long ...",  // ditto
  "translations": {                       // optional; null/absent = English-only
    "sr-Cyrl": {
      "name": "Мауританија",
      "capital": "Нуакшот",
      "funFact": "Има возове дугачке 2 km ...",
      "audioUrl": "/audio/sr-Cyrl/mr.mp3"  // optional; null until audio is generated
    }
  }
}
```

The C# DTO matches in `src/EduMap.Api/Models/Country.cs`:

```csharp
public sealed record Country(
    string Iso2, string Name, string? Capital, string FlagUrl, string? FunFact,
    Dictionary<string, CountryTranslation>? Translations = null);

public sealed record CountryTranslation(
    string? Name, string? Capital, string? FunFact, string? AudioUrl);
```

**Every field inside a translation block is optional.** Partial translations are expected — you might have a country's Serbian name but not its fun fact yet. The frontend's `tr()` helper handles that gracefully.

## Frontend rendering machinery

Three pieces in `src/EduMap.Api/wwwroot/index.html`:

### `LANG` constant + `?lang=` URL parameter

```javascript
const LANG = new URLSearchParams(location.search).get("lang") || "sr-Cyrl";
```

Default is `sr-Cyrl` because the kids are the primary audience. `?lang=en` is the debug / parent escape hatch. Adding a new locale means adding a `UI_STRINGS` entry plus translation blocks in `countries.json`.

### `UI_STRINGS` table

Static UI text (loader, toast, ARIA labels, alt text, error message) lives in a per-locale lookup:

```javascript
const UI_STRINGS = {
  "en":      { mapAria: "Interactive world map", loadingWorld: "Loading the world…", /*…*/ },
  "sr-Cyrl": { mapAria: "Интерактивна мапа света", loadingWorld: "Учитавам свет…", /*…*/ },
};
const T = UI_STRINGS[LANG] || UI_STRINGS["sr-Cyrl"] || UI_STRINGS["en"];
```

A new locale needs a full entry here. There are currently ~8 strings; check the source for the complete list because it grows.

### `tr()` helper for country fields

```javascript
function tr(country, field){
  const t = country && country.translations && country.translations[LANG];
  return (t && t[field]) || (country && country[field]);
}
```

Resolves to the localized value if present, otherwise falls back to canonical English at the top level. This is why partial translations are safe — a country with translated name but no translated fun fact will show Serbian name + English fun fact, never a broken modal.

### `applyUiStrings()` at startup

Runs immediately after `LANG` is set, before the GeoJSON arrives. Localizes the static HTML (loader text, close-button ARIA, etc.) so the loading state speaks the right language from the first paint.

## Adding a new locale (step by step)

Suppose you want to add Spanish (`es`):

1. **Add the `UI_STRINGS["es"]` block** in `index.html`. Match the existing `sr-Cyrl` block field-for-field — don't omit any keys. Use kid-friendly tone if the audience is children; formal Spanish if the audience is parents.

2. **Update `applyUiStrings`** if the BCP-47 → `<html lang>` mapping needs adjustment. The current code does `document.documentElement.lang = LANG.startsWith("sr") ? "sr" : LANG`; if `es-MX` should map to `es`, add that here.

3. **Hand-curate ~10 well-known countries first** before running the bulk scripts. The scripts don't overwrite existing entries, so a hand-curated starter set ensures the most-clicked countries have polished translations. The scripts then fill in the long tail.

4. **Run the translation scripts** in this order (each is idempotent and only fills gaps):
   ```bash
   python -X utf8 scripts/translate-names-capitals.py --locale es
   python -X utf8 scripts/translate-fun-facts.py --locale es        # requires Azure Translator
   ```

5. **Test** locally: `?lang=es` should render the whole UI in Spanish, including the modal for any country with a translation. Untranslated countries should fall back to English (visible via `tr()`).

6. **Generate audio** if desired:
   ```bash
   python -X utf8 scripts/generate-audio.py --locale es        # requires Azure Speech
   ```
   The script writes `wwwroot/audio/es/<iso2>.mp3` and updates `audioUrl` in the JSON.

7. **Commit**. One commit per locale chunk (UI strings + hand-curated countries first, then bulk-script outputs as a separate commit so the diff is reviewable).

## Extending an existing locale's coverage

This is the common case — `sr-Cyrl` already exists but only 12 countries are translated. The remaining 239 fall back to English. To fill the gap:

```bash
python -X utf8 scripts/translate-names-capitals.py --locale sr-Cyrl
python -X utf8 scripts/translate-fun-facts.py --locale sr-Cyrl     # needs Translator
python -X utf8 scripts/generate-audio.py --locale sr-Cyrl          # needs Speech
```

Each script is idempotent:
- It only writes to countries whose `translations.<locale>.<field>` is missing or empty.
- Hand-curated entries are never overwritten.
- For audio, an `.mp3` file that already exists at the target path (e.g., a manual recording you dropped in) is left untouched and the script just updates `audioUrl` to point at it.

After running, review the script output: it summarizes `N translated, M skipped (already present), K failed`. Spot-check 5-10 generated entries for quality before committing.

## Audio: hybrid TTS + manual recording

The plan is to use Azure Speech TTS as a baseline for every country, and let you replace any country's audio with your own voice over time. The frontend doesn't know or care which source produced the file — both are served from the same `/audio/<locale>/<iso2>.mp3` path.

### Generation workflow

1. Provision an Azure Speech account once (see Azure-resource skill or WALKTHROUGH.md).
2. Set env vars: `SPEECH_KEY` and `SPEECH_REGION`.
3. Run `scripts/generate-audio.py --locale sr-Cyrl`. It generates only files that don't already exist.
4. Commit the generated `.mp3` files. ~240 × 10-15 KB = ~3 MB — acceptable for the repo.

### Replacing TTS with a manual recording

To swap in your own voice for, say, Serbia:

1. Record `rs.mp3` (a few seconds of clearly saying "Србија") with phone or laptop mic.
2. Drop it at `src/EduMap.Api/wwwroot/audio/sr-Cyrl/rs.mp3`, overwriting the TTS file.
3. Commit. No code changes — the frontend was already serving from that path.

The script's idempotency means you can re-run it later without it clobbering your recording: it sees `rs.mp3` exists and skips.

### Wiring up the frontend audio playback (one-time)

If the page doesn't play audio yet, add this inside `openModal(c)`:

```javascript
const localizedTrans = c.translations && c.translations[LANG];
if (localizedTrans && localizedTrans.audioUrl) {
  // Singleton so a fast double-tap doesn't overlap audio.
  if (window._edumapAudio) { window._edumapAudio.pause(); }
  const audio = new Audio(localizedTrans.audioUrl);
  window._edumapAudio = audio;
  audio.play().catch(() => {/* autoplay blocked — silently ignore */});
}
```

Place it right after `flagImg.src = local;` — the modal-open click is the user gesture that unblocks autoplay on iOS Safari, so playing inside the same synchronous task works.

For a replay button (kid-friendly so they can hear it again), add to the modal HTML near the flag:

```html
<button class="replay-btn" id="replay-btn" aria-label="..." hidden>🔊</button>
```

Add the locale-appropriate `aria-label` to `UI_STRINGS` (e.g. `en: "Hear it again"`, `sr-Cyrl: "Чуј поново"`), unhide when `localizedTrans.audioUrl` exists, click handler re-runs the singleton audio play.

## Conventions

### Idempotency above all

Every script in `scripts/` must be safely re-runnable. The rules:
- Never overwrite a hand-curated entry. The way to detect "hand-curated" is conservative: if `translations.<locale>.<field>` is non-null/non-empty, don't touch it.
- For audio, don't overwrite an existing `.mp3` file. Period. Manual recordings are sacred.
- If a script needs to retry a failed batch, it can — re-running fills only the still-missing entries.

This is what enables the "fill bulk, then polish over time" workflow.

### Fallback chain

Frontend resolution order for any field:
1. `country.translations[LANG][field]` if present and non-empty
2. `country[field]` (canonical English) otherwise

Don't break this order. Specifically:
- Write `null` or omit a field rather than `""` — empty string is truthy-enough to pass the first check and produce a blank modal.
- Don't add tier-2 fallbacks (e.g., `sr-Cyrl → sr-Latn → en`) without explicit user agreement; the current two-tier chain is intentional.

### BCP-47 keys

Locale keys follow BCP-47. Specifically:
- `sr-Cyrl` for Serbian in Cyrillic (the kids' default)
- `sr-Latn` for Serbian in Latin script (different audience entirely)
- `en` for English (canonical source, no region suffix needed)
- `es-MX` if you specifically want Mexican Spanish (vs `es` for generic)

Don't use `sr` alone — it's ambiguous between scripts.

### Scripts go in the repo, not in env

The three Python scripts in this skill's `scripts/` directory are templates. Copy them to the project's `scripts/` directory. They read API keys from env vars only; never hardcode keys, never commit a config file with keys, never log keys.

## Scripts in this skill

The `scripts/` directory of this skill contains:

| File | Purpose | Azure deps | Time per locale |
|---|---|---|---|
| `translate-names-capitals.py` | Fetches CLDR territories + Wikidata capitals, fills `translations.<locale>.{name, capital}` | None | ~30 sec |
| `translate-fun-facts.py` | Batch-translates `funFact` via Azure Translator (free tier handles 2M chars/month) | Translator F0 | ~1 min |
| `generate-audio.py` | Generates one MP3 per translated country via Azure Speech TTS, writes to `wwwroot/audio/<locale>/<iso2>.mp3` | Speech F0 | ~3 min |

Each script reads `--help` for its full argument list. Default locale is `sr-Cyrl`.

### Provisioning the Azure resources

```powershell
# Translator (free tier, 2M chars/month — plenty)
az cognitiveservices account create `
  -g rg-edumap -n cs-edumap-translator `
  --kind TextTranslation --sku F0 -l westeurope --yes

# Speech (free tier, 500K chars/month TTS — plenty)
az cognitiveservices account create `
  -g rg-edumap -n cs-edumap-speech `
  --kind SpeechServices --sku F0 -l westeurope --yes
```

Capture the keys + regions, pass to scripts via env vars:
- `TRANSLATOR_KEY`, `TRANSLATOR_REGION` for `translate-fun-facts.py`
- `SPEECH_KEY`, `SPEECH_REGION` for `generate-audio.py`

## Common errors

**`UnicodeEncodeError: 'charmap' codec`** — Windows Python defaults to cp1252 which crashes on Cyrillic. Always run scripts with `python -X utf8`.

**`Translator: 401 Unauthorized`** — Either `TRANSLATOR_KEY` is wrong, or `Ocp-Apim-Subscription-Region` doesn't match the resource's actual region.

**`Speech: 400 Bad Request` with SSML errors** — Country names with `&` or apostrophes need XML-escaping. The bundled `generate-audio.py` handles this.

**`generate-audio.py` skips countries that should be translated** — Check `translations.<locale>.name` exists for those countries first.

**Voice name not found** — Check the current voice catalog at `https://learn.microsoft.com/azure/ai-services/speech-service/language-support#text-to-speech`.

**Frontend doesn't update after deploy** — Hard refresh (Ctrl+Shift+R). Or check the curl response for the file directly.

## Verification after each script run

```bash
curl -s https://edumap-miljkovici.azurewebsites.net/api/countries | python -X utf8 -c "
import sys, json
data = json.load(sys.stdin)
locale = 'sr-Cyrl'
counts = {
  'name':     sum(1 for c in data if c.get('translations',{}).get(locale,{}).get('name')),
  'capital':  sum(1 for c in data if c.get('translations',{}).get(locale,{}).get('capital')),
  'funFact':  sum(1 for c in data if c.get('translations',{}).get(locale,{}).get('funFact')),
  'audioUrl': sum(1 for c in data if c.get('translations',{}).get(locale,{}).get('audioUrl')),
}
print(f'Total countries: {len(data)}')
for k, v in counts.items():
    print(f'  {k:9s}: {v} ({round(100*v/len(data))}%)')
"
```

## Updating FUTURE.md after a chunk lands

When a chunk from FUTURE.md ships (B, C, or D), strike or delete that chunk and add a one-line summary under "What's been built". This keeps the file accurate for future sessions and prevents redo-work.
