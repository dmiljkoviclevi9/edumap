using EduMap.Api.Services;
using Microsoft.ApplicationInsights;
using Microsoft.AspNetCore.StaticFiles;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddSingleton<CountryRepository>();

// Application Insights auto-instruments requests/dependencies and reads its
// connection string from ApplicationInsights:ConnectionString or the
// APPLICATIONINSIGHTS_CONNECTION_STRING env var. The classic 2.x SDK is a
// no-op when neither is set, which is what we want for local dev and tests.
builder.Services.AddApplicationInsightsTelemetry();

var app = builder.Build();

// Eagerly initialise the repository so we fail fast at startup if data is missing.
app.Services.GetRequiredService<CountryRepository>();

app.UseDefaultFiles();

// Default UseStaticFiles refuses to serve files with unregistered extensions.
// Add the IANA media type for GeoJSON (RFC 7946) so wwwroot/data/*.geojson
// loads instead of 404-ing.
var staticFileTypes = new FileExtensionContentTypeProvider();
staticFileTypes.Mappings[".geojson"] = "application/geo+json";
app.UseStaticFiles(new StaticFileOptions { ContentTypeProvider = staticFileTypes });

app.MapGet("/health", () => Results.Ok(new { status = "Healthy" }))
    .WithName("Health");

app.MapGet("/api/countries", (CountryRepository repo) => Results.Ok(repo.GetAll()))
    .WithName("ListCountries");

app.MapGet("/api/countries/{iso2}", (string iso2, CountryRepository repo) =>
{
    var country = repo.GetByIso2(iso2);
    return country is null ? Results.NotFound() : Results.Ok(country);
})
    .WithName("GetCountry");

app.MapPost("/api/track/{iso2}", (
    string iso2,
    TelemetryClient telemetry,
    ILogger<Program> logger) =>
{
    var normalized = iso2.ToUpperInvariant();
    telemetry.TrackEvent("CountryClicked", new Dictionary<string, string>
    {
        ["iso2"] = normalized,
    });
    logger.LogInformation("Country clicked: {Iso2}", normalized);
    return Results.NoContent();
})
    .WithName("TrackClick");

app.Run();

// Exposed for WebApplicationFactory<Program> in the test project.
public partial class Program { }
