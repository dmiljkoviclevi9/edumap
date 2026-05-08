# syntax=docker/dockerfile:1.7

# ---------- build ----------
FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /src

COPY NuGet.config ./
COPY *.slnx ./
COPY src/EduMap.Api/EduMap.Api.csproj src/EduMap.Api/
COPY tests/EduMap.Api.Tests/EduMap.Api.Tests.csproj tests/EduMap.Api.Tests/
RUN dotnet restore src/EduMap.Api/EduMap.Api.csproj

COPY src/EduMap.Api/ src/EduMap.Api/
RUN dotnet publish src/EduMap.Api/EduMap.Api.csproj \
    --no-restore --configuration Release \
    --output /app

# ---------- runtime ----------
FROM mcr.microsoft.com/dotnet/aspnet:10.0 AS runtime
WORKDIR /app

# curl is needed for the HEALTHCHECK below; trimmed image overhead is tiny.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=build /app .

ENV ASPNETCORE_URLS=http://+:8080
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -fsS http://localhost:8080/health || exit 1

ENTRYPOINT ["dotnet", "EduMap.Api.dll"]
