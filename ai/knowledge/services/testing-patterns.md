# Testing Patterns

## Framework

xUnit + `Microsoft.AspNetCore.Mvc.Testing` (`WebApplicationFactory<Program>`).
Real HTTP-level tests — the full app pipeline runs, including `CountryRepository`
startup.

Test project: `tests/EduMap.Api.Tests/`

`public partial class Program {}` at the bottom of `src/EduMap.Api/Program.cs`
is required so `WebApplicationFactory<Program>` can reference the entry point.

## Running tests

```powershell
dotnet test                          # all tests
dotnet test --configuration Release  # as CI runs it
dotnet test --logger "trx;LogFileName=test-results.trx"  # CI output
```

Tests must pass before every deploy. CI fails loudly if they do not.

## Existing test coverage (EndpointTests.cs)

Current tests in `tests/EduMap.Api.Tests/EndpointTests.cs`:

1. `GET /api/countries` returns 200 with a non-empty list.
2. `GET /api/countries/RS` returns 200 with Serbia and correct capital.
3. `GET /api/countries/INVALID` returns 404.
4. `GET /health` returns 200 with `{"status":"Healthy"}`.

4/4 tests must pass after every change.

## Pattern for new endpoint tests

```csharp
public class EndpointTests : IClassFixture<WebApplicationFactory<Program>>
{
    private readonly HttpClient _client;

    public EndpointTests(WebApplicationFactory<Program> factory)
    {
        _client = factory.CreateClient();
    }

    [Fact]
    public async Task GetCountries_ReturnsNonEmptyList()
    {
        var response = await _client.GetAsync("/api/countries");
        response.EnsureSuccessStatusCode();
        var json = await response.Content.ReadAsStringAsync();
        var countries = JsonSerializer.Deserialize<List<JsonElement>>(json);
        Assert.NotEmpty(countries!);
    }
}
```

## Application Insights in tests

`Microsoft.ApplicationInsights.AspNetCore` 2.22.0 is a no-op when
`APPLICATIONINSIGHTS_CONNECTION_STRING` is not set — tests run cleanly
without mocking the TelemetryClient. **Do not upgrade this package**; v3.x
throws on startup when unconfigured and breaks the test suite.

## What NOT to test

- The `POST /api/track/{iso2}` endpoint fires an App Insights event; don't
  mock TelemetryClient unless you're specifically testing tracking behavior.
  A 204 response and no exception is sufficient.
- `CountryRepository`'s Blob Storage path: not exercised in tests (no Azure
  storage in CI). The fallback to the embedded JSON is the test path.
