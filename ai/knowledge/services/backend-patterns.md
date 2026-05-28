# Backend Patterns

## Minimal API — Program.cs

`src/EduMap.Api/Program.cs` is ~60 lines. Pattern:

```csharp
var builder = WebApplication.CreateBuilder(args);
builder.Services.AddSingleton<CountryRepository>();
builder.Services.AddApplicationInsightsTelemetry();

var app = builder.Build();
app.Services.GetRequiredService<CountryRepository>(); // eager init — fail fast at startup

app.UseDefaultFiles();
app.UseStaticFiles(new StaticFileOptions { ContentTypeProvider = ... }); // adds .geojson MIME type
app.MapGet("/health", ...);
app.MapGet("/api/countries", ...);
app.MapGet("/api/countries/{iso2}", ...);
app.MapPost("/api/track/{iso2}", ...);
app.Run();

public partial class Program { } // exposed for WebApplicationFactory in tests
```

Never add middleware between `UseStaticFiles` and endpoint routes without
checking impact on the static file pipeline.

## CountryRepository

`src/EduMap.Api/Services/CountryRepository.cs` — singleton, loads at startup.

Key behaviors:
- Deserializes `countries.json` into `IReadOnlyList<Country>` and a
  `Dictionary<string, Country>` keyed by uppercase ISO2.
- `GetAll()` returns the full list; `GetByIso2(iso2)` is O(1) dict lookup.
- `LoadJson()`: prefers Blob Storage when `Storage:ConnectionString` and
  `Storage:CountriesBlobName` are in config; falls back to
  `Path.Combine(AppContext.BaseDirectory, "Data", "countries.json")`.

**Always read the model before writing deserialisation code.** The JSON
field names are camelCase; deserialization uses `PropertyNameCaseInsensitive = true`.

## Static files — MIME types

`app.UseStaticFiles()` alone refuses `.geojson` files (unregistered extension).
The `FileExtensionContentTypeProvider` adds `".geojson" → "application/geo+json"` so
`wwwroot/data/*.geojson` serves correctly.

If you add new file types to `wwwroot/`, check whether ASP.NET Core will serve them
by default. Audio files (`.mp3`) are served without extra registration.

## Application Insights

`Microsoft.ApplicationInsights.AspNetCore` **pinned to 2.22.0**. v3.x throws
`NullReferenceException` on startup when `APPLICATIONINSIGHTS_CONNECTION_STRING`
is not set. v2.x is a no-op when unconfigured — correct behavior for local dev
and xUnit tests.

**Never upgrade this package** without verifying both startup and xUnit test behavior.

The `TrackEvent("CountryClicked")` call in `/api/track/{iso2}` is the only custom
telemetry. The TelemetryClient is injected via DI.

## Configuration

`appsettings.json` is the baseline. `appsettings.Development.json` is for local
overrides. Neither is committed with secrets.

App Service Configuration settings (env vars) override the JSON config at runtime.
The Blob Storage wiring uses `Storage:ConnectionString` and `Storage:CountriesBlobName`.
