"""Alta de cuentas desde el panel de administrador («Nueva cuenta»).

Solo un Administrador activo puede usarlo y solo crea Alumno, Profesor o
Empresa: los administradores se crean únicamente con `flask crear-usuario`.
La lógica de alta es la misma del comando (servicios/cuentas.py).
"""
from flask import Blueprint, current_app, jsonify, request

from csrf import csrf_valido, token_csrf
from extensions import limiter
from servicios.cuentas import ROLES_WEB, ErrorCuenta, guardar_cuenta, preparar_cuenta
from Controllers.postulacionesController import SEMESTRES
from Controllers.vacantesController import PERFIL_ADMINISTRADOR, perfil_de_carga, usuario_en_sesion

cuentas_bp = Blueprint('cuentas', __name__)


def _error(mensaje, estado, campo=None):
    return jsonify({'ok': False, 'mensaje': mensaje, 'campo': campo}), estado


def _administrador_o_error():
    """(administrador, None) o (None, respuesta de error 401/403)."""
    usuario = usuario_en_sesion()
    if not usuario:
        return None, _error('Debes iniciar sesión.', 401)
    if perfil_de_carga(usuario) != PERFIL_ADMINISTRADOR:
        return None, _error('Solo un administrador puede crear cuentas.', 403)
    return usuario, None


@cuentas_bp.route('/api/admin/cuentas/formulario', methods=['GET'])
def datos_formulario():
    """Token CSRF y opciones del formulario «Nueva cuenta»."""
    _admin, error = _administrador_o_error()
    if error:
        return error
    return jsonify({
        'ok': True,
        'csrf_token': token_csrf(),
        'roles': list(ROLES_WEB),
        'semestres': list(SEMESTRES),  # en orden: 1° … 11°, Egresado(a)
    })


@cuentas_bp.route('/api/admin/cuentas', methods=['POST'])
@limiter.limit('20 per minute')
def crear_cuenta():
    admin, error = _administrador_o_error()
    if error:
        return error
    if not csrf_valido():
        return _error('La sesión del formulario expiró. Recarga la página e intenta de nuevo.', 403)

    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        return _error('Solicitud no válida.', 400)

    # Lista blanca: 'Administrador' (o cualquier otro rol) se rechaza aquí
    rol = datos.get('rol')
    if not isinstance(rol, str) or rol.strip().lower() not in {r.lower() for r in ROLES_WEB}:
        current_app.logger.warning(
            'Alta de cuenta rechazada: el administrador #%s pidió un rol no permitido (%r).',
            admin.id, str(rol)[:30])
        return _error('Rol no permitido. Desde la web solo se crean cuentas de Alumno, '
                      'Profesor o Empresa.', 400, 'rol')

    try:
        cuenta = preparar_cuenta(rol, datos, datos.get('password'), roles_permitidos=ROLES_WEB,
                                 password_confirmacion=datos.get('password_confirmacion', ''))
        usuario = guardar_cuenta(cuenta, creado_por=admin.id, origen='web')
    except ErrorCuenta as error_cuenta:
        if error_cuenta.detalle:
            # El texto de PostgreSQL solo va al log, nunca a la respuesta
            current_app.logger.warning('Alta de cuenta rechazada por la base de datos: %s',
                                       error_cuenta.detalle)
        estado = 409 if error_cuenta.duplicado else 400
        return _error(error_cuenta.mensaje, estado, error_cuenta.campo)
    except Exception:
        current_app.logger.exception('Error inesperado al crear una cuenta desde la web')
        return _error('No fue posible crear la cuenta. Intenta de nuevo más tarde.', 500)

    current_app.logger.info(
        'Alta de cuenta: el administrador #%s (%s) creó la cuenta #%s (%s, %s).',
        admin.id, admin.email, usuario.id, usuario.rol, usuario.email)
    return jsonify({
        'ok': True,
        'id': usuario.id,
        'mensaje': f'Cuenta de {usuario.rol} creada para {usuario.email}. '
                   'Deberá cambiar la contraseña en su primer inicio de sesión.',
    }), 201
