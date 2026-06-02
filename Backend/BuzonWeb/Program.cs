var builder = WebApplication.CreateBuilder(args);

// --- 1. ZONA DE SERVICIOS (Configuración antes de crear la app) ---


// Tus configuraciones para que funcione  API y Swagger UI
builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

// --- AQUÍ SE CONSTRUYE LA APP 
var app = builder.Build();

// --- 2. ZONA DE PIPELINE 

// Configuración para desarrollo
if (app.Environment.IsDevelopment())
{
    
    // Activamos Swagger UI 
    app.UseSwagger();
    app.UseSwaggerUI();
}

app.UseHttpsRedirection();
app.UseAuthorization();

// Tus controladores
app.MapControllers();

// --- 3. ZONA DE EJEMPLOS POR DEFECTO (WeatherForecast) 

var summaries = new[]
{
    "Freezing", "Bracing", "Chilly", "Cool", "Mild", "Warm", "Balmy", "Hot", "Sweltering", "Scorching"
};

app.MapGet("/weatherforecast", () =>
{
    var forecast = Enumerable.Range(1, 5).Select(index =>
        new WeatherForecast
        (
            DateOnly.FromDateTime(DateTime.Now.AddDays(index)),
            Random.Shared.Next(-20, 55),
            summaries[Random.Shared.Next(summaries.Length)]
        ))
        .ToArray();
    return forecast;
})
.WithName("GetWeatherForecast");

app.Run();

// Definición del record 
record WeatherForecast(DateOnly Date, int TemperatureC, string? Summary)
{
    public int TemperatureF => 32 + (int)(TemperatureC / 0.5556);
}