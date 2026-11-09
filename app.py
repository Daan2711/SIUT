# =========================================================================
# SECCIÓN 1: IMPORTACIONES DE LIBRERÍAS Y MÓDULOS CENTRALES
# =========================================================================
import logging
import os
from flask import Flask, send_from_directory, request, make_response, redirect, session, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix
from markupsafe import escape
from sqlalchemy import text


from dotenv import load_dotenv

# Conexión con la instancia de la base de datos y carga de modelos
from Database.database import db
import Models.models
from Models.models import Usuario
from extensions import limiter

# Importación del controlador de autenticación (Blueprint)
from Controllers.authController import auth_bp
from Controllers.buzonController import buzon_bp
from Controllers.vacantesController import vacantes_bp, puede_cargar_vacantes, es_administrador
from Controllers.postulacionesController import postulaciones_bp

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

# Logs: Flask escribe en stderr, que Render muestra en su panel de logs.
# Los errores capturados se registran con app.logger.exception (con traza).
app.logger.setLevel(getattr(logging, os.getenv('LOG_LEVEL', 'INFO').upper(), logging.INFO))

# Detrás de un proxy (Render / Cloudflare) la IP real llega en X-Forwarded-For.
# PROXY_HOPS = número de proxies de confianza (0 en local para que no se pueda falsear).
_proxy_hops = int(os.getenv("PROXY_HOPS", "0"))
if _proxy_hops > 0:
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=_proxy_hops, x_proto=_proxy_hops)

# Llave secreta obligatoria para encriptar y manejar las sesiones de usuario
app.secret_key = os.getenv("SECRET_KEY")

if not app.secret_key:
    raise RuntimeError("Falta configurar SECRET_KEY en las variables de entorno")

app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

app.config['SESSION_COOKIE_SECURE'] = (
    os.getenv("COOKIE_SECURE", "false").lower() == "true"
)
app.config['PERMANENT_SESSION_LIFETIME'] = 1800

# Carga de archivos (CV en PDF de hasta 5 MB + campos del formulario).
# Los CV se guardan en la base de datos (tabla postulacion_cv), no en disco.
app.config['MAX_CONTENT_LENGTH'] = 6 * 1024 * 1024

# =========================================================================
# SECCIÓN 4: CONFIGURACIÓN Y ENLACE DE LA BASE DE DATOS (ORM)
# =========================================================================
# Configuramos la conexión a Neon leyendo la variable de entorno
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Neon suspende la base tras unos minutos sin uso y cierra las conexiones:
# pool_pre_ping revisa cada conexión antes de usarla (y la reemplaza si murió)
# y pool_recycle las renueva antes de que Neon las corte.
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 280,
}

# Vinculamos la base de datos con nuestra aplicación de Flask
db.init_app(app)

# Límite de intentos (login). Ver extensions.py
app.config['RATELIMIT_STORAGE_URI'] = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
app.config['RATELIMIT_HEADERS_ENABLED'] = True
limiter.init_app(app)


@app.errorhandler(413)
def archivo_demasiado_grande(_error):
    return jsonify({
        'ok': False,
        'mensaje': 'El archivo es demasiado grande. El CV no puede pesar más de 5 MB.'
    }), 413


@app.errorhandler(429)
def demasiados_intentos(_error):
    return jsonify({
        'error': 'Demasiados intentos. Espera un minuto e intenta de nuevo.'
    }), 429

# =========================================================================
# SECCIÓN 5: REGISTRO DE BLUEPRINTS (CONTROLADORES DE LAS RUTAS)
# =========================================================================
# Conectamos las rutas del controlador de autenticación a la app principal
app.register_blueprint(auth_bp)
app.register_blueprint(buzon_bp)
app.register_blueprint(vacantes_bp)
app.register_blueprint(postulaciones_bp)

# Comandos de administración: `flask crear-usuario` (ver comandos.py)
from comandos import crear_usuario  # noqa: E402
app.cli.add_command(crear_usuario)


# =========================================================================
# SECCIÓN 5.4: PÁGINAS HTML PROTEGIDAS
# =========================================================================
# Toda página .html exige sesión salvo estas. Las de reclutador exigen ser
# Empresa o Administrador; las de administración, ser Administrador.
PAGINAS_PUBLICAS = {'/login.html', '/cambiar-password.html'}
PAGINAS_RECLUTADOR = {
    '/cargar-vacantes.html', '/vacantes-publicadas.html', '/postulaciones-recibidas.html',
}
PAGINAS_ADMINISTRADOR = {'/panel-admin.html', '/sugerencias-admin.html'}


@app.before_request
def proteger_paginas_html():
    # .lower(): en Windows el sistema de archivos no distingue mayúsculas
    ruta = request.path.lower()
    if not ruta.endswith('.html') or ruta in PAGINAS_PUBLICAS:
        return None
    if 'usuario_id' not in session:
        return redirect('/login')
    if ruta in PAGINAS_RECLUTADOR and not puede_cargar_vacantes():
        return redirect('/index.html')
    if ruta in PAGINAS_ADMINISTRADOR and not es_administrador():
        return redirect('/index.html')
    return None


# =========================================================================
# SECCIÓN 5.5: CAMBIO DE CONTRASEÑA OBLIGATORIO (validado en servidor)
# =========================================================================
# Mientras el usuario tenga primer_login=True solo puede usar estas rutas.
RUTAS_PERMITIDAS_PRIMER_LOGIN = {
    'index', 'login_page', 'cambiar_password_page', 'security_txt', 'security_txt_legado',
    'healthz',
    'auth.login_usuario', 'auth.logout', 'auth.usuario_actual', 'auth.cambiar_password',
}


@app.before_request
def exigir_cambio_password():
    usuario_id = session.get('usuario_id')
    if not usuario_id or request.endpoint in RUTAS_PERMITIDAS_PRIMER_LOGIN:
        return None

    # CSS, JS e imágenes sí se sirven; las páginas .html no.
    if request.endpoint == 'static' and not request.path.endswith('.html'):
        return None

    pendiente = session.get('primer_login')
    if pendiente is None:
        # Sesiones creadas antes de este cambio: se consulta una vez y se guarda.
        usuario = db.session.get(Usuario, usuario_id)
        pendiente = bool(usuario and usuario.primer_login)
        session['primer_login'] = pendiente

    if not pendiente:
        return None

    if request.path.startswith('/api/') or request.method != 'GET':
        return jsonify({'error': 'Debes cambiar tu contraseña antes de continuar'}), 403
    return redirect('/cambiar-password')


# =========================================================================
# SECCIÓN 5.6: SECURITY HEADERS
# =========================================================================
@app.after_request
def set_security_headers(response):
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; "
        "img-src 'self' data:; "
        "font-src 'self' https://cdnjs.cloudflare.com; "
        "object-src 'none'; "
        "base-uri 'self';"
    )
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    # HSTS solo tiene sentido (y solo se envía) cuando el sitio va por HTTPS
    if app.config['SESSION_COOKIE_SECURE']:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    # Forzamos que Cloudflare NO cachee — así siempre pasa por Flask
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'

    if request.method == 'OPTIONS':
        # Un after_request debe devolver un objeto Response, no una tupla
        response.status_code = 405
        response.headers['Allow'] = 'GET, POST, HEAD'

    return response

# =========================================================================
# SECCIÓN 5.7: RUTAS HTML
# =========================================================================
@app.route('/')
def index():
    # Cuando entren a la raíz, los mandamos a su login por ahora
    return send_from_directory('Frontend', 'login.html')

@app.route('/login')
def login_page():
    # Ruta explícita para acceder al formulario de login
    return send_from_directory('Frontend', 'login.html')


def _render_con_nombre(nombre_archivo):
    """Sirve una vista del Frontend reemplazando 'Nombre del Alumno' por el nombre real."""
    if 'usuario_id' not in session:
        return redirect('/login')

    usuario = db.session.get(Usuario, session['usuario_id'])
    if usuario:
        # Se escapa para que un nombre con HTML no se ejecute en la página
        nombre = str(escape(f"{usuario.nombre} {usuario.apellido or ''}".strip()))
    else:
        nombre = 'Nombre del Alumno'

    with open(f'Frontend/{nombre_archivo}', 'r', encoding='utf-8') as f:
        html = f.read()

    html = html.replace('Nombre del Alumno', nombre)
    return html


@app.route('/index.html')
def pagina_principal():
    return _render_con_nombre('index.html')


@app.route('/buzon.html')
def buzon_page():
    return _render_con_nombre('buzon.html')


@app.route('/maestros.html')
def maestros_page():
    return _render_con_nombre('maestros.html')


@app.route('/horario.html')
def horario_page():
    return _render_con_nombre('horario.html')


@app.route('/soporte.html')
def soporte_page():
    return _render_con_nombre('soporte.html')


@app.route('/sugerencias.html')
def sugerencias_page():
    return _render_con_nombre('sugerencias.html')


# Páginas del reclutador (el permiso lo valida proteger_paginas_html)
@app.route('/cargar-vacantes.html')
def cargar_vacantes_page():
    return _render_con_nombre('cargar-vacantes.html')


@app.route('/vacantes-publicadas.html')
def vacantes_publicadas_page():
    return _render_con_nombre('vacantes-publicadas.html')


@app.route('/postulaciones-recibidas.html')
def postulaciones_recibidas_page():
    return _render_con_nombre('postulaciones-recibidas.html')


# Páginas del administrador (el permiso lo valida proteger_paginas_html)
@app.route('/panel-admin.html')
def panel_admin_page():
    return _render_con_nombre('panel-admin.html')


@app.route('/sugerencias-admin.html')
def sugerencias_admin_page():
    return _render_con_nombre('sugerencias-admin.html')


# =========================================================================
# SECCIÓN 5.8: HEALTH CHECK (Render)
# =========================================================================
@app.route('/healthz')
def healthz():
    """Render consulta esta ruta para saber si el servicio está sano.

    Comprueba también la conexión con la base de datos. No requiere sesión
    y no expone detalles del error (quedan en el log).
    """
    try:
        db.session.execute(text('SELECT 1'))
        return jsonify({'ok': True}), 200
    except Exception:
        db.session.rollback()
        app.logger.exception('Health check: la base de datos no responde')
        return jsonify({'ok': False}), 503


@app.route('/.well-known/security.txt')
def security_txt():
    response = make_response(send_from_directory('Frontend/.well-known', 'security.txt'))
    response.headers['Content-Type'] = 'text/plain; charset=utf-8'
    return response


@app.route('/security.txt')
def security_txt_legado():
    # Ubicación antigua: se redirige a la estándar (RFC 9116)
    return redirect('/.well-known/security.txt', code=301)

@app.route('/cambiar-password')
def cambiar_password_page():
    response = make_response(send_from_directory('Frontend', 'cambiar-password.html'))
    return response

# =========================================================================
# SECCIÓN 6: CREACIÓN DE TABLAS (solo bajo demanda)
# =========================================================================
# En Neon el esquema lo controlan los scripts de migrations/ (con sus
# triggers y restricciones). create_all() solo se usa en bases locales de
# desarrollo y únicamente si se pide con AUTO_CREATE_TABLES=true.
if os.getenv('AUTO_CREATE_TABLES', 'false').lower() == 'true':
    with app.app_context():
        db.create_all()

# =========================================================================
# SECCIÓN 7: ARRANQUE DEL SERVIDOR DE DESARROLLO
# =========================================================================
if __name__ == '__main__':
    app.run(debug=True)
