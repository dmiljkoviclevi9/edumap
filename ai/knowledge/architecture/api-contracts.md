# API Contracts

**LOCKED — do not change the response shape without a deliberate decision.**

The frontend was written against this exact contract. Changing any field name,
type, or nesting will break the live app for children.

Source of truth: `src/EduMap.Api/Program.cs` (routes) and
`src/EduMap.Api/Models/Country.cs` (DTO).

## Endpoints

### GET /api/countries

Returns the full country list.

```
200 OK
Content-Type: application/json

[Country, Country, ...]
```

### GET /api/countries/{iso2}

`iso2` is case-insensitive (normalised via `ToUpperInvariant()`).

```
200 OK
Content-Type: application/json

Country

--- or ---

404 Not Found   (iso2 unknown)
```

### GET /health

```
200 OK
Content-Type: application/json

{ "status": "Healthy" }
```

Used by App Service health probes and CI/CD verification.

### POST /api/track/{iso2}

Fire-and-forget telemetry. Never call this for side-effects — it emits an
Application Insights custom event only.

```
204 No Content
```

Payload logged: `customEvents | where name == "CountryClicked"` with dimension `iso2`.

## Country object shape

```jsonc
{
  "iso2": "RS",              // uppercase ISO-3166-1 alpha-2 string
  "name": "Serbia",          // English name (canonical)
  "capital": "Belgrade",     // English capital, nullable
  "flagUrl": "/flags/rs.svg",// relative URL, served from wwwroot/flags/
  "funFact": "Home of Nikola Tesla.", // English, nullable
  "translations": {          // nullable; absent when no translations exist
    "sr-Cyrl": {             // BCP-47 locale key
      "name": "Србија",      // nullable
      "capital": "Београд",  // nullable
      "funFact": "...",      // nullable
      "audioUrl": "/audio/sr-Cyrl/rs.mp3" // nullable
    }
  }
}
```

## Invariants

- The frontend reads **only** these fields. Adding new fields is safe; removing
  or renaming any existing field breaks the app.
- `flagUrl` is always `/flags/{iso2-lowercase}.svg`. Never use absolute URLs.
- `audioUrl` is always `/audio/{locale}/{iso2-lowercase}.mp3` when present.
- The `translations` key is absent (not `{}`) when a country has no translations.
  Avoid writing an empty object.
