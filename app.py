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
load_dotenv()
# =========================================================================
# SECCIÓN 3: INICIALIZACIÓN Y CONFIGURACIÓN DE LA APP DE FLASK
# =========================================================================
app = Flask(__name__, static_folder='Frontend', static_url_path='')
app.secret_key = os.getenv("SECRET_KEY", "fallback_solo_para_dev")
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = True
# =========================================================================
# SECCIÓN 4: CONFIGURACIÓN Y ENLACE DE LA BASE DE DATOS (ORM)
# =========================================================================
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# =========================================================================
# SECCIÓN 5: REGISTRO DE BLUEPRINTS (CONTROLADORES DE LAS RUTAS)
# =========================================================================
app.register_blueprint(auth_bp)
# =========================================================================
# SECCIÓN 5.5: SECURITY HEADERS (parcha findings 1-4 del reporte)
# =========================================================================
@app.after_request
def set_security_headers(response):
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "font-src 'self'; "
        "object-src 'none';"
    )
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response
# =========================================================================
# SECCIÓN 5.6: RUTAS PARA RENDERIZAR LAS VISTAS HTML
# =========================================================================
@app.route('/')
def index():
    return send_from_directory('Frontend', 'login.html')

@app.route('/login')
def login_page():
    return send_from_directory('Frontend', 'login.html')
# =========================================================================
# SECCIÓN 6: VERIFICACIÓN E INICIALIZACIÓN DE TABLAS EN NEON
# =========================================================================
with app.app_context():
    db.create_all()
# =========================================================================
# SECCIÓN 7: ARRANQUE DEL SERVIDOR DE DESARROLLO
# =========================================================================
if __name__ == '__main__':
    app.run(debug=False)
