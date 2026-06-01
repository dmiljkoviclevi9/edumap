# Frontend Patterns

## File

`src/EduMap.Api/wwwroot/index.html` — a single self-contained HTML file.
Inline `<style>` and `<script>`. No build step, no framework.

## Map tech

- **d3-geo** + Equal Earth projection. Country polygons loaded from
  `wwwroot/data/countries.geojson` (self-hosted Natural Earth 50m, ~3 MB).
- UK nations (England, Scotland, Wales, NI) loaded separately from
  `wwwroot/data/uk-nations.geojson` for finer granularity.
- Custom zoom controls (not Leaflet). Pinch-zoom on mobile, scroll-wheel on desktop.
- Zoom range: `[1, 256]`. Deep zoom is intentional so Adi/Una can pinch into microstates on a phone and still land on a fat tap target. `non-scaling-stroke` keeps borders at 1 CSS px at any zoom level, so deep zoom doesn't make the map chunky.

## d3-geo winding bug

Polygons whose exterior ring is clockwise read as "everything except this shape"
on the sphere — covering the entire world instead of just the country. Fixed with
`rewindFeature()` applied **per polygon** inside each `MultiPolygon` feature.
**If you swap GeoJSON datasets, verify the rewind still catches mislabeled polygons.**

## Locale selection

```js
const LANG = new URLSearchParams(location.search).get('lang') || 'sr-Cyrl';
```

- Default: `sr-Cyrl`.
- Debug/parent mode: append `?lang=en`.
- **Never change the default to `"en"`.**

## tr() helper

```js
function tr(country, field) {
  const t = country.translations && country.translations[LANG];
  return (t && t[field]) || country[field];
}
```

Returns the localized field when truthy; falls back to the English top-level field.
Empty string `""` is falsy and falls through to English — **never write `""` in
translation data, always write `null` or omit the field.**

## UI_STRINGS

Per-locale chrome strings (loader, toast, aria-labels, close button text).
`applyUiStrings()` patches the DOM before the GeoJSON arrives so the UI is
localized from first paint.

When adding new locale-visible strings (new buttons, labels), add an entry to
both the `en` and `sr-Cyrl` blocks of `UI_STRINGS`.

## openModal() — country tap handler

1. Renders flag, localized name, capital, funFact into the modal.
2. If `translations[LANG].audioUrl` is set: creates an `Audio` object and calls
   `.play()` wrapped in `.catch()`.
3. Fires `fetch('/api/track/' + iso2, {method:'POST'})` fire-and-forget wrapped
   in `try/catch` — UI must never break if the telemetry call fails.

## Audio playback singleton

```js
if (window._edumapAudio) { window._edumapAudio.pause(); }
const audio = new Audio(localizedTrans.audioUrl);
window._edumapAudio = audio;
audio.play().catch(() => {});
```

The singleton prevents overlapping audio on rapid taps.

## Replay button

```html
<button class="replay-btn" id="replay-btn" hidden>&#128266;</button>
```

Hidden when no audio is available. Click replays `window._edumapAudio`. The
aria-label is localized from `UI_STRINGS.hearAgain`.

## "Coming soon" toast

Countries present in GeoJSON but absent from `/api/countries` response show a
toast (`UI_STRINGS.noData`) instead of a modal. **Never throw an error** for
unknown countries.

## Static assets

| Path | Source |
|---|---|
| `wwwroot/flags/` | Vendored `flag-icons` 4x3 SVGs (~250 files). Reference via `/flags/{iso2-lowercase}.svg`. |
| `wwwroot/audio/sr-Cyrl/` | ElevenLabs TTS MP3s. Reference via `/audio/sr-Cyrl/{iso2-lowercase}.mp3`. |
| `wwwroot/data/countries.geojson` | Natural Earth 50m, self-hosted. |
| `wwwroot/data/uk-nations.geojson` | UK nations sub-division, self-hosted. |

## prefers-reduced-motion

```css
@media (prefers-reduced-motion: reduce) {
  .loader .ring { animation: none; ... }
}
```

Respect this in any new animations you add.
