"""Recuperación de contraseña con un código de 4 dígitos enviado por correo.

Flujo (Frontend/js/recuperar.js, desde el login):
1. POST /recuperar-password/solicitar  {email}            → envía el código
2. POST /recuperar-password/verificar  {email, codigo}    → valida el código
3. POST /recuperar-password/restablecer {nueva_password, confirmar_password}

Un código de 4 dígitos es corto, así que:
- vence a los 10 minutos y se anula con 5 intentos fallidos;
- pedir uno nuevo anula el anterior;
- se guarda cifrado con bcrypt;
- la respuesta de «solicitar» es la misma exista o no el correo, y el correo
  se envía en segundo plano para que el tiempo de respuesta tampoco lo delate;
- hay límites de solicitudes por correo y por red (además de los 5 intentos,
  que viven en la base de datos y valen para todos los workers).

Estas rutas se usan sin sesión: están exentas de CSRF, igual que el login.
"""
import os
import secrets
import threading
from datetime import datetime, timedelta, timezone

from flask import Blueprint, request, jsonify, session, current_app
from flask_limiter.util import get_remote_address
from markupsafe import escape

from Controllers.authController import bcrypt
from Database.database import db
from extensions import limiter
from Models.models import Usuario, Auditoria, RecuperacionPassword
from servicios.correo import correo_configurado, enviar_correo, CorreoNoEnviado
from sqlalchemy import func

recuperacion_bp = Blueprint('recuperacion', __name__)

MINUTOS_VIGENCIA = 10
MAX_INTENTOS = 5
# Respaldo en la base de datos del límite por correo (el limiter en memoria
# cuenta por worker de gunicorn).
MAX_CODIGOS_POR_VENTANA = 3
VENTANA_CODIGOS = timedelta(minutes=15)
# Lo que el navegador recuerda tras validar el código (cookie de sesión firmada)
CLAVE_SESION = 'recuperacion'

MENSAJE_ENVIADO = ('Si el correo está registrado, te enviamos un código de 4 dígitos. '
                   'Revisa también la carpeta de spam.')
MENSAJE_NO_DISPONIBLE = ('La recuperación de contraseña no está disponible por ahora. '
                         'Pide ayuda al administrador de SIUT.')
MENSAJE_CODIGO_INVALIDO = 'El código no es válido o ya venció. Pide uno nuevo.'
MENSAJE_SESION_VENCIDA = 'La verificación venció. Vuelve a pedir un código.'


def _ahora():
    return datetime.now(timezone.utc)


def _utc(fecha):
    """SQLite (pruebas) devuelve fechas sin zona; Neon, con zona. Todas son UTC."""
    return fecha if fecha.tzinfo else fecha.replace(tzinfo=timezone.utc)


def _correo_de_la_peticion():
    data = request.get_json(silent=True)
    email = data.get('email') if isinstance(data, dict) else None
    return email.strip().lower() if isinstance(email, str) else ''


def _clave_por_correo():
    return f"recuperar|{_correo_de_la_peticion()}"


def _usuario_activo(email):
    if not email:
        return None
    usuario = Usuario.query.filter(func.lower(Usuario.email) == email).first()
    return usuario if usuario and usuario.activo else None


def _codigo_vigente(usuario_id):
    """El último código sin usar ni anular y que no ha vencido."""
    codigo = (RecuperacionPassword.query
              .filter_by(usuario_id=usuario_id, usado_en=None)
              .order_by(RecuperacionPassword.creado_en.desc(), RecuperacionPassword.id.desc())
              .first())
    if codigo and _utc(codigo.vence_en) > _ahora():
        return codigo
    return None


def _texto_del_correo(nombre, codigo):
    saludo = f'Hola, {nombre}:' if nombre else 'Hola:'
    texto = (
        f'{saludo}\n\n'
        f'Tu código para recuperar la contraseña de SIUT es: {codigo}\n\n'
        f'Vence en {MINUTOS_VIGENCIA} minutos. Si no lo pediste, ignora este mensaje: '
        'tu contraseña no cambia.\n'
    )
    html = (
        f'<p>{escape(saludo)}</p>'
        '<p>Tu código para recuperar la contraseña de SIUT es:</p>'
        f'<p style="font-size:28px;font-weight:bold;letter-spacing:6px">{codigo}</p>'
        f'<p>Vence en {MINUTOS_VIGENCIA} minutos. Si no lo pediste, ignora este mensaje: '
        'tu contraseña no cambia.</p>'
    )
    return texto, html


def _enviar(destinatario, nombre, codigo, usuario_id, logger):
    """Se ejecuta en segundo plano: no tiene contexto de Flask."""
    texto, html = _texto_del_correo(nombre, codigo)
    try:
        enviar_correo(destinatario, 'Tu código para recuperar la contraseña de SIUT', texto, html)
        logger.info('Código de recuperación enviado (usuario %s)', usuario_id)
    except CorreoNoEnviado as error:
        logger.error('No se pudo enviar el código de recuperación (usuario %s): %s',
                     usuario_id, error)
    except Exception as error:
        # Sin traza: podría incluir el código o el correo del destinatario
        logger.error('No se pudo enviar el código de recuperación (usuario %s): '
                     'error inesperado (%s)', usuario_id, type(error).__name__)


def _despachar(*args):
    """Envía el correo sin hacer esperar la respuesta (las pruebas lo reemplazan)."""
    threading.Thread(target=_enviar, args=args, daemon=True).start()


# =========================================================================
# 1. SOLICITAR EL CÓDIGO
# =========================================================================
@recuperacion_bp.route('/recuperar-password/solicitar', methods=['POST'])
@limiter.limit("3 per 15 minutes", key_func=_clave_por_correo)
@limiter.limit("10 per 15 minutes", key_func=get_remote_address)
def solicitar_codigo():
    email = _correo_de_la_peticion()
    if not email or '@' not in email or len(email) > 254:
        return jsonify({'error': 'Escribe un correo válido'}), 400

    if not correo_configurado():
        current_app.logger.error('Recuperación de contraseña: falta configurar Brevo')
        return jsonify({'error': MENSAJE_NO_DISPONIBLE}), 503

    usuario = _usuario_activo(email)
    if not usuario:
        # Mismo trabajo que con un usuario real (cifrar el código), para que
        # el tiempo de respuesta no delate si el correo existe.
        bcrypt.generate_password_hash('0000')
        return jsonify({'mensaje': MENSAJE_ENVIADO}), 200

    try:
        recientes = RecuperacionPassword.query.filter(
            RecuperacionPassword.usuario_id == usuario.id,
            RecuperacionPassword.creado_en > _ahora() - VENTANA_CODIGOS,
        ).count()
        if recientes >= MAX_CODIGOS_POR_VENTANA:
            current_app.logger.warning(
                'Recuperación: límite de códigos alcanzado (usuario %s)', usuario.id)
            bcrypt.generate_password_hash('0000')
            return jsonify({'mensaje': MENSAJE_ENVIADO}), 200

        ahora = _ahora()
        # Un código nuevo anula los anteriores
        RecuperacionPassword.query.filter_by(usuario_id=usuario.id, usado_en=None) \
            .update({'usado_en': ahora}, synchronize_session=False)
        # Limpieza: los códigos de hace más de un día ya no sirven para nada
        RecuperacionPassword.query.filter(
            RecuperacionPassword.usuario_id == usuario.id,
            RecuperacionPassword.creado_en < ahora - timedelta(days=1),
        ).delete(synchronize_session=False)

        codigo = f'{secrets.randbelow(10000):04d}'
        db.session.add(RecuperacionPassword(
            usuario_id=usuario.id,
            codigo_hash=bcrypt.generate_password_hash(codigo).decode('utf-8'),
            vence_en=ahora + timedelta(minutes=MINUTOS_VIGENCIA),
            creado_en=ahora,
        ))
        db.session.add(Auditoria(usuario_id=usuario.id, accion='Código de recuperación solicitado',
                                 tabla_afectada='recuperaciones_password'))
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Error al crear el código de recuperación (usuario %s)',
                                     usuario.id)
        return jsonify({'error': 'No fue posible enviar el código. Intenta nuevamente.'}), 500

    _despachar(usuario.email, (usuario.nombre or '').strip(), codigo, usuario.id,
               current_app.logger)
    return jsonify({'mensaje': MENSAJE_ENVIADO}), 200


# =========================================================================
# 2. VERIFICAR EL CÓDIGO
# =========================================================================
@recuperacion_bp.route('/recuperar-password/verificar', methods=['POST'])
@limiter.limit("10 per minute", key_func=get_remote_address)
def verificar_codigo():
    data = request.get_json(silent=True)
    codigo = data.get('codigo') if isinstance(data, dict) else None
    if not isinstance(codigo, str) or len(codigo.strip()) != 4 or not codigo.strip().isdigit():
        return jsonify({'error': 'El código tiene 4 dígitos'}), 400
    codigo = codigo.strip()

    usuario = _usuario_activo(_correo_de_la_peticion())
    vigente = _codigo_vigente(usuario.id) if usuario else None
    if not vigente:
        return jsonify({'error': MENSAJE_CODIGO_INVALIDO}), 400

    try:
        if bcrypt.check_password_hash(vigente.codigo_hash, codigo):
            session.pop(CLAVE_SESION, None)
            session[CLAVE_SESION] = {'id': vigente.id, 'usuario_id': usuario.id}
            return jsonify({'mensaje': 'Código correcto. Escribe tu nueva contraseña.'}), 200

        vigente.intentos = (vigente.intentos or 0) + 1
        restantes = MAX_INTENTOS - vigente.intentos
        if restantes <= 0:
            vigente.usado_en = _ahora()   # se anula
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Error al verificar el código de recuperación (usuario %s)',
                                     usuario.id)
        return jsonify({'error': 'No fue posible verificar el código. Intenta nuevamente.'}), 500

    if restantes <= 0:
        return jsonify({'error': 'Se agotaron los intentos. Pide un código nuevo.',
                        'agotado': True}), 400
    intento = 'intento' if restantes == 1 else 'intentos'
    return jsonify({'error': f'Código incorrecto. Te quedan {restantes} {intento}.'}), 400


# =========================================================================
# 3. GUARDAR LA NUEVA CONTRASEÑA
# =========================================================================
@recuperacion_bp.route('/recuperar-password/restablecer', methods=['POST'])
@limiter.limit("10 per minute", key_func=get_remote_address)
def restablecer_password():
    datos_sesion = session.get(CLAVE_SESION)
    if not isinstance(datos_sesion, dict):
        return jsonify({'error': MENSAJE_SESION_VENCIDA}), 400

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'error': 'Solicitud inválida'}), 400

    nueva = data.get('nueva_password')
    confirmar = data.get('confirmar_password')
    if not isinstance(nueva, str) or not isinstance(confirmar, str) or not nueva or not confirmar:
        return jsonify({'error': 'Debes completar ambos campos'}), 400
    if nueva != confirmar:
        return jsonify({'error': 'Las contraseñas no coinciden'}), 400
    if len(nueva) < 8:
        return jsonify({'error': 'La contraseña debe tener al menos 8 caracteres'}), 400

    recuperacion = db.session.get(RecuperacionPassword, datos_sesion.get('id'))
    usuario = db.session.get(Usuario, datos_sesion.get('usuario_id'))
    if (not recuperacion or not usuario or not usuario.activo
            or recuperacion.usuario_id != usuario.id
            or recuperacion.usado_en is not None
            or _utc(recuperacion.vence_en) <= _ahora()):
        session.pop(CLAVE_SESION, None)
        return jsonify({'error': MENSAJE_SESION_VENCIDA}), 400

    temporal = os.getenv('TEMP_PASSWORD')
    if bcrypt.check_password_hash(usuario.password_hash, nueva) or (temporal and nueva == temporal):
        return jsonify({
            'error': 'La nueva contraseña debe ser distinta a la actual o a la temporal'
        }), 400

    try:
        usuario.password_hash = bcrypt.generate_password_hash(nueva).decode('utf-8')
        # Si tenía pendiente cambiar la contraseña temporal, ya la eligió él mismo
        usuario.primer_login = False
        recuperacion.usado_en = _ahora()
        db.session.add(Auditoria(usuario_id=usuario.id,
                                 accion='Contraseña restablecida con código por correo',
                                 tabla_afectada='usuarios', registro_id=usuario.id))
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Error al restablecer la contraseña (usuario %s)', usuario.id)
        return jsonify({'error': 'No fue posible actualizar la contraseña'}), 500

    session.pop(CLAVE_SESION, None)
    if session.get('usuario_id') == usuario.id:
        session['primer_login'] = False
    return jsonify({'mensaje': 'Contraseña actualizada. Ya puedes iniciar sesión.'}), 200
