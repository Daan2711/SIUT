# Usamos la imagen del SDK de .NET 9.0 para construir
FROM mcr.microsoft.com/dotnet/sdk:9.0 AS build
WORKDIR /src

# Copiamos el archivo de proyecto (BuzonWeb.csproj)
COPY ["BuzonWeb.csproj", "./"]
# Restauramos las dependencias
RUN dotnet restore "BuzonWeb.csproj"

# Copiamos todo el resto de los archivos
COPY . .
# Construimos y publicamos la aplicación en modo Release
RUN dotnet publish "BuzonWeb.csproj" -c Release -o /app/publish

# Usamos la imagen de ASP.NET Core 9.0 para ejecutar (es más ligera)
FROM mcr.microsoft.com/dotnet/aspnet:9.0
WORKDIR /app
COPY --from=build /app/publish .

# Le decimos que arranque con TU dll
ENTRYPOINT ["dotnet", "BuzonWeb.dll"]
