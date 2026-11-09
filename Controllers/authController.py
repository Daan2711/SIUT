import os
from flask import Blueprint, request, jsonify, session, current_app
from flask_bcrypt import Bcrypt
from flask_limiter.util import get_remote_address
from Models.models import Usuario, Alumno, Empresa, Auditoria
from Database.database import db
from sqlalchemy import func
from extensions import limiter
from csrf import nuevo_token_csrf

bcrypt = Bcrypt()
auth_bp = Blueprint('auth', __name__)

# =========================================================================
# REGISTRO
# =========================================================================

@auth_bp.route('/registro', methods=['POST'])
def registrar_usuario():
    return jsonify({
        'error': 'El registro público está deshabilitado. Solicita tu cuenta al administrador de SIUT.'
    }), 403

# =========================================================================
# LOGIN
# =========================================================================
def _clave_intentos_login():
    """Cuenta intentos por IP + correo: frena fuerza bruta sobre una cuenta
    sin bloquear a otros usuarios que salen por la misma IP (p. ej. la red escolar)."""
    data = request.get_json(silent=True) or {}
    email = data.get('email') if isinstance(data, dict) else ''
    email = email.strip().lower() if isinstance(email, str) else ''
    return f"{get_remote_address()}|{email}"


@auth_bp.route('/login', methods=['POST'])
@limiter.limit("5 per minute", key_func=_clave_intentos_login)
def login_usuario():
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Solicitud inválida'}), 400

    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': 'Correo y contraseña son obligatorios'}), 400

    email = email.strip().lower()

    usuario = Usuario.query.filter(
        func.lower(Usuario.email) == email
    ).first()

    # No permitir el acceso a cuentas inexistentes o desactivadas
    if not usuario or not usuario.activo:
        return jsonify({
            'error': 'Usuario o contraseña incorrectos'
        }), 401

    if not bcrypt.check_password_hash(usuario.password_hash, password):
        return jsonify({
            'error': 'Usuario o contraseña incorrectos'
        }), 401

    try:
        # Limpiar cualquier sesión anterior
        session.clear()
        # Sin esto PERMANENT_SESSION_LIFETIME (30 min) no se aplica
        session.permanent = True

        session['usuario_id'] = usuario.id
        session['rol'] = usuario.rol
        session['nombre'] = usuario.nombre
        session['email'] = usuario.email
        session['primer_login'] = bool(usuario.primer_login)
        # El token CSRF se crea aquí y no al abrir el formulario: las peticiones
        # simultáneas de una página (p. ej. /usuario-actual) reescriben la cookie
        # de sesión y podían borrar un token creado a medio camino.
        nuevo_token_csrf()

        # Registrar inicio de sesión
        nuevo_log = Auditoria(
            usuario_id=usuario.id,
            accion='Inicio de sesión'
        )

        db.session.add(nuevo_log)
        db.session.commit()

        # Import local: vacantesController no debe cargarse antes que este módulo
        from Controllers.vacantesController import pagina_inicio

        return jsonify({
            'mensaje': 'Login exitoso',
            'nombre': usuario.nombre,
            'apellido': usuario.apellido,
            'email': usuario.email,
            'rol': usuario.rol,
            'forzar_cambio': usuario.primer_login,
            # Página de inicio según el rol (alumno, empresa o administrador)
            'destino': pagina_inicio(usuario),
        }), 200

    except Exception:
        db.session.rollback()
        session.clear()
        current_app.logger.exception('Error al iniciar sesión')

        return jsonify({
            'error': 'No fue posible iniciar sesión. Intenta nuevamente.'
        }), 500


# =========================================================================
# USUARIO ACTUAL
# =========================================================================

@auth_bp.route('/usuario-actual', methods=['GET'])
def usuario_actual():
    usuario_id = session.get('usuario_id')

    if not usuario_id:
        return jsonify({
            'error': 'No has iniciado sesión'
        }), 401

    usuario = db.session.get(Usuario, usuario_id)

    if not usuario or not usuario.activo:
        session.clear()
        return jsonify({
            'error': 'La cuenta no está disponible'
        }), 401

    # Import local: vacantesController no debe cargarse antes que este módulo
    from Controllers.vacantesController import perfil_de_carga

    alumno = Alumno.query.filter_by(usuario_id=usuario.id).first()
    empresa = db.session.get(Empresa, usuario.empresa_id) if usuario.empresa_id else None

    return jsonify({
        'usuario_id': usuario.id,
        'nombre': usuario.nombre,
        'apellido': usuario.apellido,
        'email': usuario.email,
        'rol': usuario.rol,
        'primer_login': usuario.primer_login,
        'puede_cargar_vacantes': perfil_de_carga(usuario) is not None,
        # Usuarios con rol Empresa: publican siempre a nombre de esta empresa
        'empresa': {'id': empresa.id, 'nombre': empresa.nombre} if empresa else None,
        # Datos para precargar el formulario de postulación
        'alumno': {
            'matricula': alumno.matricula,
            'carrera': alumno.carrera,
            'semestre': alumno.semestre,
            'telefono': alumno.telefono,
        } if alumno else None
    }), 200



# =========================================================================
# LOGOUT
# =========================================================================

@auth_bp.route('/logout', methods=['POST'])
def logout():
    usuario_id = session.get('usuario_id')

    if not usuario_id:
        return jsonify({'error': 'No has iniciado sesión'}), 401

    try:
        nuevo_log = Auditoria(
            usuario_id=usuario_id,
            accion='Cierre de sesión'
        )

        db.session.add(nuevo_log)
        db.session.commit()

        session.clear()

        return jsonify({
            'mensaje': 'Sesión cerrada correctamente'
        }), 200

    except Exception:
        db.session.rollback()
        current_app.logger.exception('Error al cerrar sesión (usuario %s)', usuario_id)

        return jsonify({
            'error': 'No fue posible cerrar la sesión'
        }), 500


# =========================================================================
# CAMBIO DE CONTRASEÑA (primer login)
# =========================================================================

@auth_bp.route('/cambiar-password', methods=['POST'])
def cambiar_password():
    if 'usuario_id' not in session:
        return jsonify({'error': 'No has iniciado sesión'}), 401

    data = request.get_json()

    if not data:
        return jsonify({'error': 'Solicitud inválida'}), 400

    nueva_password = data.get('nueva_password')
    confirmar_password = data.get('confirmar_password')

    if not nueva_password or not confirmar_password:
        return jsonify({'error': 'Debes completar ambos campos'}), 400

    if nueva_password != confirmar_password:
        return jsonify({'error': 'Las contraseñas no coinciden'}), 400

    if len(nueva_password) < 8:
        return jsonify({'error': 'La contraseña debe tener al menos 8 caracteres'}), 400

    try:
        usuario = db.session.get(Usuario, session['usuario_id'])

        if not usuario or not usuario.activo:
            session.clear()
            return jsonify({'error': 'La cuenta no está disponible'}), 401

        # La contraseña temporal ya no vive en el código: se rechaza reutilizar
        # la contraseña actual (cubre la temporal) y, si está configurada,
        # la temporal institucional definida en TEMP_PASSWORD.
        temporal = os.getenv('TEMP_PASSWORD')
        if (bcrypt.check_password_hash(usuario.password_hash, nueva_password)
                or (temporal and nueva_password == temporal)):
            return jsonify({
                'error': 'La nueva contraseña debe ser distinta a la actual o a la temporal'
            }), 400

        usuario.password_hash = bcrypt.generate_password_hash(
            nueva_password
        ).decode('utf-8')

        usuario.primer_login = False

        nuevo_log = Auditoria(
            usuario_id=usuario.id,
            accion='Cambio de contraseña obligatorio completado'
        )

        db.session.add(nuevo_log)
        db.session.commit()
        # Solo tras confirmar en BD se libera el acceso en la sesión
        session['primer_login'] = False

        return jsonify({
            'mensaje': 'Contraseña actualizada correctamente'
        }), 200

    except Exception:
        db.session.rollback()
        current_app.logger.exception('Error al cambiar la contraseña (usuario %s)', session.get('usuario_id'))

        return jsonify({
            'error': 'No fue posible actualizar la contraseña'
        }), 500
