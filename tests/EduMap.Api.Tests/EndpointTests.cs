using System.Net;
using System.Net.Http.Json;
using EduMap.Api.Models;
using Microsoft.AspNetCore.Mvc.Testing;

namespace EduMap.Api.Tests;

public class EndpointTests : IClassFixture<WebApplicationFactory<Program>>
{
    private readonly WebApplicationFactory<Program> _factory;

    public EndpointTests(WebApplicationFactory<Program> factory)
    {
        _factory = factory;
    }

    [Fact]
    public async Task Health_returns_200_with_status_healthy()
    {
        var client = _factory.CreateClient();
        var response = await client.GetAsync("/health");

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        var body = await response.Content.ReadAsStringAsync();
        Assert.Contains("Healthy", body);
    }

    [Fact]
    public async Task ListCountries_returns_non_empty_list_including_Serbia()
    {
        var client = _factory.CreateClient();
        var countries = await client.GetFromJsonAsync<List<Country>>("/api/countries");

        Assert.NotNull(countries);
        Assert.NotEmpty(countries);
        Assert.Contains(countries, c => c.Iso2 == "RS" && c.Capital == "Belgrade");
    }

    [Fact]
    public async Task GetCountry_with_unknown_iso_returns_404()
    {
        var client = _factory.CreateClient();
        var response = await client.GetAsync("/api/countries/ZZ");

        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
    }

    [Fact]
    public async Task GetCountry_is_case_insensitive()
    {
        var client = _factory.CreateClient();
        var upper = await client.GetFromJsonAsync<Country>("/api/countries/RS");
        var lower = await client.GetFromJsonAsync<Country>("/api/countries/rs");

        Assert.NotNull(upper);
        Assert.NotNull(lower);
        Assert.Equal(upper.Capital, lower.Capital);
    }
}
