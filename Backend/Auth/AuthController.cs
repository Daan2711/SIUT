using Microsoft.AspNetCore.Mvc;
using Microsoft.IdentityModel.Tokens;
using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using System.Text;
using BCrypt.Net; 

[Route("api/[controller]")]
[ApiController]
public class AuthController : ControllerBase
{
    private readonly IConfiguration _configuration;
    private readonly BuzonContext _context; // 1. Inyectamos tu DB real

    public AuthController(IConfiguration configuration, BuzonContext context)
    {
        _configuration = configuration;
        _context = context;
    }

    // LOGIN REAL
    [HttpPost("login")]
    public ActionResult Login(UsuarioDto request)
    {
        // 1. Buscamos al usuario en SQL Server por su correo
        var user = _context.Usuarios.FirstOrDefault(u => u.Email == request.Email);

        // 2. Si no existe el usuario, adiós
        if (user == null)
        {
            return BadRequest("Usuario o contraseña incorrectos.");
        }

        // 3. Verificamos la contraseña (el Hash de la BD vs lo que escribió)
        if (!BCrypt.Net.BCrypt.Verify(request.Password, user.Password))
        {
            return BadRequest("Usuario o contraseña incorrectos.");
        }

        // 4. Si todo bien, creamos el token con los datos de ESE usuario
        string token = CrearToken(user);
        
        return Ok(new { token = token });
    }

    // REGISTRO SIMPLE (Solo para que puedas crear usuarios de prueba)
    [HttpPost("registro")]
    public ActionResult Register(UsuarioDto request)
    {
        // Encriptamos la contraseña
        string passwordHash = BCrypt.Net.BCrypt.HashPassword(request.Password);

        var nuevoUsuario = new Usuario 
        { 
            Email = request.Email, 
            Password = passwordHash,
            Nombre = request.Nombre, // Asumo que tienes esto en tu DTO
            Rol = "Estudiante" // O lo que mandes en el request
        };

        _context.Usuarios.Add(nuevoUsuario);
        _context.SaveChanges();

        return Ok("Usuario creado con éxito ✨");
    }

    private string CrearToken(Usuario user)
    {
        // Aquí metemos la info que luego vas a leer
        var claims = new List<Claim>
        {
            // El ID del usuario es súper importante para saber quién es
            new Claim(ClaimTypes.NameIdentifier, user.Id.ToString()), 
            new Claim(ClaimTypes.Name, user.Email),
            new Claim(ClaimTypes.Role, user.Rol), // "Admin", "Estudiante", etc.
            new Claim("FullName", user.Nombre) // Un dato extra personalizado
        };

        var key = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(_configuration["Jwt:Key"]));
        var creds = new SigningCredentials(key, SecurityAlgorithms.HmacSha256);

        var token = new JwtSecurityToken(
            issuer: _configuration["Jwt:Issuer"],
            audience: _configuration["Jwt:Audience"],
            claims: claims,
            expires: DateTime.Now.AddHours(8), // Que dure 8 horitas para que no te saque a cada rato
            signingCredentials: creds
        );

        return new JwtSecurityTokenHandler().WriteToken(token);
    }
}
