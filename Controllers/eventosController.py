"""Eventos (Hackathon, UT Canta, etc.): inscripción y revisión del administrador."""
import re

from flask import Blueprint, request, jsonify, session, current_app
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from Models.models import Evento, UsuarioEvento, Auditoria
from Database.database import db
from Controllers.vacantesController import usuario_en_sesion, es_administrador, _iso

eventos_bp = Blueprint('eventos', __name__)

# Largos de usuario_evento.nombre / .correo en Neon
LIMITE_NOMBRE = 150
LIMITE_CORREO = 254
CORREO_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


def _error(mensaje, codigo):
    return jsonify({'ok': False, 'mensaje': mensaje}), codigo


def _texto(data, campo):
    valor = data.get(campo)
    return valor.strip() if isinstance(valor, str) else ''


def _eventos_abiertos():
    return Evento.query.filter(Evento.publicado.is_(True), Evento.activo.is_(True))


# =========================================================================
# EVENTOS DISPONIBLES (cualquier usuario con sesión)
# =========================================================================
@eventos_bp.route('/api/eventos', methods=['GET'])
def listar_eventos():
    usuario_id = session.get('usuario_id')
    if not usuario_id:
        return _error('No autorizado', 401)

    eventos = _eventos_abiertos().order_by(Evento.fecha_inicio, Evento.id).all()
    inscritos = {
        evento_id for (evento_id,) in
        db.session.query(UsuarioEvento.evento_id).filter_by(usuario_id=usuario_id).all()
    }
    return jsonify({'ok': True, 'eventos': [{
        'id': e.id,
        'titulo': e.titulo,
        'descripcion': e.descripcion,
        'fecha_inicio': _iso(e.fecha_inicio),
        'inscrito': e.id in inscritos,
    } for e in eventos]}), 200


# =========================================================================
# INSCRIBIRSE A UN EVENTO
# =========================================================================
@eventos_bp.route('/api/eventos/<int:evento_id>/inscripcion', methods=['POST'])
def inscribirse(evento_id):
    usuario_id = session.get('usuario_id')
    if not usuario_id:
        return _error('No autorizado', 401)

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return _error('No se recibieron datos', 400)
    nombre = _texto(data, 'nombre')
    correo = _texto(data, 'correo')
    if not nombre or not correo:
        return _error('Escribe tu nombre y tu correo', 400)
    if len(nombre) > LIMITE_NOMBRE:
        return _error(f'El nombre excede {LIMITE_NOMBRE} caracteres', 400)
    if len(correo) > LIMITE_CORREO or not CORREO_RE.match(correo):
        return _error('Correo no válido', 400)

    evento = _eventos_abiertos().filter(Evento.id == evento_id).first()
    if not evento:
        return _error('El evento no existe o ya no acepta inscripciones', 404)

    if UsuarioEvento.query.filter_by(usuario_id=usuario_id, evento_id=evento.id).first():
        return _error('Ya estás inscrito en este evento', 409)

    try:
        inscripcion = UsuarioEvento(
            usuario_id=usuario_id, evento_id=evento.id, nombre=nombre, correo=correo,
        )
        db.session.add(inscripcion)
        db.session.flush()
        db.session.add(Auditoria(
            usuario_id=usuario_id,
            accion='Inscripción a evento',
            tabla_afectada='usuario_evento',
            registro_id=inscripcion.id,
            descripcion=f'Evento #{evento.id}: {evento.titulo}',
        ))
        db.session.commit()
        return jsonify({'ok': True, 'id': inscripcion.id}), 201
    except IntegrityError:
        # Dos envíos simultáneos: el segundo choca con uq_usuario_evento
        db.session.rollback()
        return _error('Ya estás inscrito en este evento', 409)
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Error al inscribir al usuario %s en el evento %s', usuario_id, evento_id)
        return _error('No fue posible guardar tu inscripción', 500)


# =========================================================================
# INSCRIPCIONES RECIBIDAS (solo Administrador)
# =========================================================================
def _solo_administrador():
    if not session.get('usuario_id'):
        return _error('No autorizado', 401)
    if not es_administrador():
        return _error('Solo un administrador puede ver las inscripciones', 403)
    return None


def _serializar_inscripcion(inscripcion, titulo):
    return {
        'id': inscripcion.id,
        'evento_id': inscripcion.evento_id,
        'evento': titulo,
        'nombre': inscripcion.nombre,
        'correo': inscripcion.correo,
        'inscrito_en': _iso(inscripcion.registrado_en),
        'confirmada': bool(inscripcion.confirmada),
        'confirmada_en': _iso(inscripcion.confirmada_en),
    }


@eventos_bp.route('/api/inscripciones-eventos', methods=['GET'])
def listar_inscripciones():
    error = _solo_administrador()
    if error:
        return error

    filas = (db.session.query(UsuarioEvento, Evento.titulo)
             .join(Evento, UsuarioEvento.evento_id == Evento.id)
             .order_by(UsuarioEvento.registrado_en.desc(), UsuarioEvento.id.desc())
             .all())
    inscripciones = [_serializar_inscripcion(i, t) for i, t in filas]
    return jsonify({
        'ok': True,
        'inscripciones': inscripciones,
        'pendientes': sum(1 for i in inscripciones if not i['confirmada']),
    }), 200


@eventos_bp.route('/api/inscripciones-eventos/<int:inscripcion_id>/ok', methods=['POST'])
def marcar_ok(inscripcion_id):
    """Marca (o desmarca) una inscripción como «OK»."""
    error = _solo_administrador()
    if error:
        return error

    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get('confirmada'), bool):
        return _error('Indica si la inscripción queda confirmada', 400)
    confirmada = data['confirmada']

    inscripcion = db.session.get(UsuarioEvento, inscripcion_id)
    if not inscripcion:
        return _error('Inscripción no encontrada', 404)

    administrador = usuario_en_sesion()
    try:
        inscripcion.confirmada = confirmada
        inscripcion.confirmada_por = administrador.id if confirmada else None
        inscripcion.confirmada_en = func.now() if confirmada else None
        db.session.add(Auditoria(
            usuario_id=administrador.id,
            accion='Inscripción a evento marcada OK' if confirmada else 'Inscripción a evento desmarcada',
            tabla_afectada='usuario_evento',
            registro_id=inscripcion.id,
        ))
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Error al marcar la inscripción %s', inscripcion_id)
        return _error('No fue posible actualizar la inscripción', 500)

    db.session.refresh(inscripcion)
    titulo = db.session.get(Evento, inscripcion.evento_id).titulo
    return jsonify({'ok': True, 'inscripcion': _serializar_inscripcion(inscripcion, titulo)}), 200
