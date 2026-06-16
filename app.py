# =========================================================================
# SECCIÓN 1: IMPORTACIONES
# =========================================================================
import os
from flask import Flask, send_from_directory, make_response, request
from dotenv import load_dotenv
from Database.database import db
import Models.models
from Controllers.authController import auth_bp

# =========================================================================
# SECCIÓN 2: CARGA DE ENTORNO
# =========================================================================
load_dotenv()

# =========================================================================
# SECCIÓN 3: INICIALIZACIÓN DE FLASK
# =========================================================================
app = Flask(__name__, static_folder='Frontend', static_url_path='')
app.secret_key = os.getenv("SECRET_KEY", "fallback_solo_para_dev")
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = True

# =========================================================================
# SECCIÓN 4: BASE DE DATOS
# =========================================================================
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# =========================================================================
# SECCIÓN 5: BLUEPRINTS
# =========================================================================
app.register_blueprint(auth_bp)

# =========================================================================
# SECCIÓN 5.5: SECURITY HEADERS
# =========================================================================
@app.after_request
def set_security_headers(response):
  response.headers['Content-Security-Policy'] = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "font-src 'self'; "
    "object-src 'none'; "
    "base-uri 'self';"
)
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    # Forzamos que Cloudflare NO cachee — así siempre pasa por Flask
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
if request.method == 'OPTIONS':
    response.headers['Allow'] = 'GET, POST, HEAD'
    return response, 405
    return response

# =========================================================================
# SECCIÓN 5.6: RUTAS HTML
# =========================================================================
@app.route('/')
def index():
    response = make_response(send_from_directory('Frontend', 'login.html'))
    return response

@app.route('/login')
def login_page():
    response = make_response(send_from_directory('Frontend', 'login.html'))
    return response
  
  @app.route('/.well-known/security.txt')
def security_txt():
    response = make_response(send_from_directory('Frontend/.well-known', 'security.txt'))
    response.headers['Content-Type'] = 'text/plain'
    return response

# =========================================================================
# SECCIÓN 6: INICIALIZACIÓN DE TABLAS
# =========================================================================
with app.app_context():
    db.create_all()

# =========================================================================
# SECCIÓN 7: ARRANQUE
# =========================================================================
if __name__ == '__main__':
    app.run(debug=False)
