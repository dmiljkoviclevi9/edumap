# Data Model

Source of truth: `src/EduMap.Api/Models/Country.cs` and `src/EduMap.Api/Data/countries.json`.

## C# Records

### Country

```csharp
// src/EduMap.Api/Models/Country.cs
public sealed record Country(
    string Iso2,
    string? Name,
    string? Capital,
    string FlagUrl,
    string? FunFact,
    Dictionary<string, CountryTranslation>? Translations = null);
```

- `Iso2` — uppercase ISO 3166-1 alpha-2 code (e.g. `"RS"`). The repository
  normalises lookups with `ToUpperInvariant()`.
- `FlagUrl` — relative path: `/flags/{iso2-lowercase}.svg`, served from `wwwroot/flags/`.
- `FunFact` — optional, kid-friendly one-sentence English text.
- `Translations` — keyed by BCP-47 tag (e.g. `"sr-Cyrl"`). `null` when no
  translations exist yet; the frontend falls back to the English top-level fields.

### CountryTranslation

```csharp
public sealed record CountryTranslation(
    string? Name,
    string? Capital,
    string? FunFact,
    string? AudioUrl);
```

- `AudioUrl` — relative path: `/audio/sr-Cyrl/{iso2-lowercase}.mp3`, served
  from `wwwroot/audio/sr-Cyrl/`. `null` when no audio has been generated.
- All fields are nullable. The frontend `tr(country, field)` helper falls back
  to the English top-level field when `null`.

## JSON shape (from countries.json)

```jsonc
[
  {
    "iso2": "RS",
    "name": "Serbia",
    "capital": "Belgrade",
    "flagUrl": "/flags/rs.svg",
    "funFact": "Home of Nikola Tesla.",
    "translations": {
      "sr-Cyrl": {
        "name": "Србија",
        "capital": "Београд",
        "funFact": "Домовина Николе Тесле.",
        "audioUrl": "/audio/sr-Cyrl/rs.mp3"
      }
    }
  },
  {
    "iso2": "DE",
    "name": "Germany",
    "capital": "Berlin",
    "flagUrl": "/flags/de.svg",
    "funFact": "Has over 1,500 different beers brewed here.",
    "translations": {
      "sr-Cyrl": {
        "name": "Немачка",
        "capital": "Берлин",
        "funFact": null,
        "audioUrl": null
      }
    }
  },
  {
    "iso2": "ID",
    "name": "Indonesia",
    "capital": "Jakarta",
    "flagUrl": "/flags/id.svg",
    "funFact": "Has more than 17,000 islands.",
    "translations": null
  }
]
```

## Serialization

`System.Text.Json` with `PropertyNameCaseInsensitive = true`. C# PascalCase
properties serialize to camelCase in the JSON response (e.g. `FlagUrl` → `"flagUrl"`).

## Mutation rules

- **Never write `""` (empty string)** for a missing translation — write `null`
  or omit the field. The frontend `tr()` helper checks truthiness: empty string
  falls through to English incorrectly.
- **Idempotency rule for scripts.** Translation scripts must check
  `translations.sr-Cyrl.X == null` before writing. Never overwrite an existing
  non-null value (protects hand-curated entries like the 12 starter countries).
- **12 hand-curated starter countries** (as of 2026-05): RS, MR, US, GB, DE,
  FR, IT, JP, AU, HR, HU, BG. These have all four translation fields filled by hand.

## Storage fallback

`CountryRepository.LoadJson()` in `src/EduMap.Api/Services/CountryRepository.cs`:
1. If `Storage:ConnectionString` and `Storage:CountriesBlobName` are set in config,
   download from Azure Blob Storage container `Storage:CountriesContainerName`
   (default: `"data"`).
2. Otherwise, read `Data/countries.json` from `AppContext.BaseDirectory`.

Local dev uses the embedded file. Production can override to Blob Storage via
App Service Configuration settings.
