# i18n Model

## Locale keys

BCP-47 tags. Current locales:

| Key | Language | Status |
| --- | --- | --- |
| `sr-Cyrl` | Serbian Cyrillic | **Default** — hardcoded in frontend |
| `en` | English | Fallback (top-level fields in the JSON) |

To add a new locale, add a new key to `translations` in `countries.json` and
add entries to `UI_STRINGS` in `wwwroot/index.html`.

## Frontend — locale selection

```js
// src/EduMap.Api/wwwroot/index.html
const params = new URLSearchParams(location.search);
const LANG = params.get('lang') || 'sr-Cyrl';
```

- Default: `sr-Cyrl`.
- Debug/parent mode: `?lang=en`.
- **Never change the default to `"en"`.** Una and Adi see Cyrillic by default.

## Translation fallback helper — tr()

```js
function tr(country, field) {
  const t = country.translations && country.translations[LANG];
  return (t && t[field]) || country[field];
}
```

- Returns `translations[LANG][field]` if truthy.
- Falls back to the English top-level field otherwise.
- **Empty string is falsy** — always write `null` or omit a field when no
  translation exists. Never write `""`.

## UI_STRINGS table

`wwwroot/index.html` defines per-locale UI chrome (loader text, toast message,
aria-labels, alt text). Shape:

```js
const UI_STRINGS = {
  en: {
    loading: 'Loading map…',
    noData:  'Coming soon!',
    close:   'Close',
    hearAgain: 'Hear it again',
  },
  'sr-Cyrl': {
    loading: 'Учитавање…',
    noData:  'Ускоро!',
    close:   'Затвори',
    hearAgain: 'Чуј поново',
  },
};
```

`applyUiStrings()` runs at script start to localize chrome before GeoJSON arrives.

## Audio playback

Triggered in `openModal()` when `translations[LANG].audioUrl` is set:

```js
if (window._edumapAudio) { window._edumapAudio.pause(); }
const audio = new Audio(localizedTrans.audioUrl);
window._edumapAudio = audio;
audio.play().catch(() => {/* autoplay blocked — ignore silently */});
```

- Uses a singleton `window._edumapAudio` so rapid country-tapping does not
  overlap audio clips.
- Wrapped in `.catch()` because some browsers block autoplay even after a user
  gesture; failing silently is correct — the modal still renders.
- **iOS Safari constraint:** playback inside the click handler is allowed.
  Playback in setTimeout/async-after-await may be blocked. Keep the play call
  synchronous within the click dispatch chain.

## Replay button

```html
<button class="replay-btn" id="replay-btn" aria-label="..." hidden>&#128266;</button>
```

Hidden via `hidden` attribute when no audio is available. The aria-label is
localized from `UI_STRINGS.hearAgain`.

## Audio file conventions

- Path: `/audio/{locale}/{iso2-lowercase}.mp3`
- Served from `wwwroot/audio/sr-Cyrl/*.mp3` as static files (no backend change needed).
- ~15 KB per file. 240 files ≈ 3.5 MB total. Acceptable to commit to the repo.
  If ever > 50 MB, move to Azure Blob Storage with public-read and update
  `audioUrl` values to absolute URLs.
- ElevenLabs TTS script: `.claude/skills/edumap-localization/scripts/generate-audio-elevenlabs.py`.
  Idempotent — skips files that already exist (protects manual recordings).

## Translation scripts

All scripts in `scripts/` and `.claude/skills/edumap-localization/scripts/`:

| Script | Purpose | Source |
| --- | --- | --- |
| `scripts/translate-names-capitals.py` | Fill `sr-Cyrl.name` + `.capital` for all countries | CLDR + Wikidata SPARQL |
| `scripts/translate-fun-facts.py` | Fill `sr-Cyrl.funFact` | Azure AI Translator F0 |
| `generate-audio-elevenlabs.py` | Generate `sr-Cyrl.audioUrl` MP3s | ElevenLabs TTS API |

All scripts are idempotent: they check existing values before writing and never
overwrite non-null entries. Run with `python -X utf8` on Windows.
