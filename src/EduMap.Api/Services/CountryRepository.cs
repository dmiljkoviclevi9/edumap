using System.Text.Json;
using Azure.Storage.Blobs;
using EduMap.Api.Models;

namespace EduMap.Api.Services;

public sealed class CountryRepository
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNameCaseInsensitive = true,
    };

    private readonly IReadOnlyList<Country> _countries;
    private readonly Dictionary<string, Country> _byIso2;

    public CountryRepository(IConfiguration config, ILogger<CountryRepository> logger)
    {
        var json = LoadJson(config, logger);
        _countries = JsonSerializer.Deserialize<List<Country>>(json, JsonOptions)
            ?? throw new InvalidOperationException("countries.json deserialized to null");
        _byIso2 = _countries.ToDictionary(c => c.Iso2.ToUpperInvariant());
        logger.LogInformation("Loaded {Count} countries", _countries.Count);
    }

    public IReadOnlyList<Country> GetAll() => _countries;

    public Country? GetByIso2(string iso2) =>
        _byIso2.TryGetValue(iso2.ToUpperInvariant(), out var country) ? country : null;

    private static string LoadJson(IConfiguration config, ILogger logger)
    {
        var blobConn = config["Storage:ConnectionString"];
        var blobName = config["Storage:CountriesBlobName"];
        var containerName = config["Storage:CountriesContainerName"] ?? "data";

        if (!string.IsNullOrWhiteSpace(blobConn) && !string.IsNullOrWhiteSpace(blobName))
        {
            try
            {
                logger.LogInformation(
                    "Loading countries from Blob Storage container={Container} blob={Blob}",
                    containerName, blobName);
                var serviceClient = new BlobServiceClient(blobConn);
                var containerClient = serviceClient.GetBlobContainerClient(containerName);
                var blobClient = containerClient.GetBlobClient(blobName);
                var response = blobClient.DownloadContent();
                return response.Value.Content.ToString();
            }
            catch (Exception ex)
            {
                logger.LogWarning(ex,
                    "Blob Storage load failed; falling back to embedded Data/countries.json");
            }
        }
        else
        {
            logger.LogInformation(
                "Storage:ConnectionString not configured; loading countries from Data/countries.json");
        }

        var path = Path.Combine(AppContext.BaseDirectory, "Data", "countries.json");
        return File.ReadAllText(path);
    }
}
