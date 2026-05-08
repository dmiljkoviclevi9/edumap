namespace EduMap.Api.Models;

public sealed record Country(
    string Iso2,
    string Name,
    string Capital,
    string FlagUrl,
    string? FunFact);
