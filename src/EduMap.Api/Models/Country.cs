namespace EduMap.Api.Models;

/// <summary>
/// Canonical country record. The top-level fields are in English (the
/// "source language" for the dataset). Translations into other locales
/// live under <see cref="Translations"/>, keyed by BCP-47 tag (e.g.
/// "sr-Cyrl" for Serbian Cyrillic). The frontend picks a locale via
/// the <c>?lang=</c> URL parameter and falls back to these English
/// fields when a translation is missing.
/// </summary>
public sealed record Country(
    string Iso2,
    string Name,
    string? Capital,
    string FlagUrl,
    string? FunFact,
    Dictionary<string, CountryTranslation>? Translations = null);

/// <summary>
/// Per-locale overrides for a country's display strings + an optional
/// audio clip URL for the localized country name (so kids who can't
/// read yet can hear it).
/// </summary>
public sealed record CountryTranslation(
    string? Name,
    string? Capital,
    string? FunFact,
    string? AudioUrl);
