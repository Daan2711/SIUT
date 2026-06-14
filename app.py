# =========================================================================
# SECCIÓN 1: IMPORTACIONES DE LIBRERÍAS Y MÓDULOS CENTRALES
# =========================================================================
import os
from flask import Flask, send_from_directory
from dotenv import load_dotenv

# Conexión con la instancia de la base de datos y carga de modelos
from Database.database import db
import Models.models 

# Importación del controlador de autenticación (Blueprint)
from Controllers.authController import auth_bp

# =========================================================================
# SECCIÓN 2: CARGA DE CONFIGURACIONES DE ENTORNO
# =========================================================================
# Cargamos las variables del archivo .env local para proteger credenciales
load_dotenv()

# =========================================================================
# SECCIÓN 3: INICIALIZACIÓN Y CONFIGURACIÓN DE LA APP DE FLASK
# =========================================================================
# Configuramos 'Frontend' como la carpeta para estilos, imágenes y scripts
app = Flask(__name__, static_folder='Frontend', static_url_path='')

@app.after_request
def add_security_headers(response):
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    return response

# Llave secreta obligatoria para encriptar y manejar las sesiones de usuario
app.secret_key = 'una_clave_muy_secreta_para_myutsc'

app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# =========================================================================
# SECCIÓN 4: CONFIGURACIÓN Y ENLACE DE LA BASE DE DATOS (ORM)
# =========================================================================
# Configuramos la conexión a Neon leyendo la variable de entorno
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

print("DATABASE_URL =", os.getenv("DATABASE_URL"))

# Vinculamos la base de datos con nuestra aplicación de Flask
db.init_app(app)

# =========================================================================
# SECCIÓN 5: REGISTRO DE BLUEPRINTS (CONTROLADORES DE LAS RUTAS)
# =========================================================================
# Conectamos las rutas del controlador de autenticación a la app principal
app.register_blueprint(auth_bp)

# =========================================================================
# SECCIÓN 5.5: RUTAS PARA RENDERIZAR LAS VISTAS HTML
# =========================================================================
@app.route('/')
def index():
    # Cuando entren a la raíz, los mandamos a su login por ahora
    return send_from_directory('Frontend', 'login.html')

@app.route('/login')
def login_page():
    # Ruta explícita para acceder al formulario de login
    return send_from_directory('Frontend', 'login.html')

# =========================================================================
# SECCIÓN 6: VERIFICACIÓN E INICIALIZACIÓN DE TABLAS EN NEON
# =========================================================================
# Esto crea todas las tablas en Neon automáticamente si es que aún no existen
with app.app_context():
    db.create_all()

# =========================================================================
# SECCIÓN 7: ARRANQUE DEL SERVIDOR DE DESARROLLO
# =========================================================================
if __name__ == '__main__':
    app.run(debug=True)
