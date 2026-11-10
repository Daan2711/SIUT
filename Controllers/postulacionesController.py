import io
import os
import re
import uuid

from flask import Blueprint, request, jsonify, session, send_file, current_app
from sqlalchemy.exc import IntegrityError
from werkzeug.utils import secure_filename

from Models.models import Postulacion, PostulacionCV, Vacante, Alumno, Usuario, Auditoria
from Database.database import db
from Controllers.vacantesController import (
    _iso, usuario_en_sesion, perfil_de_carga, filtro_vacantes_visibles, puede_ver_vacante,
)

postulaciones_bp = Blueprint('postulaciones', __name__)

MAX_CV_BYTES = 5 * 1024 * 1024  # 5 MB
FIRMA_PDF = b'%PDF-'

# Cuatrimestres válidos, en el orden en que se muestran. El nombre interno
# sigue siendo "semestre" (columna alumnos.semestre en Neon) por compatibilidad.
SEMESTRES = tuple(f'{n}° cuatrimestre' for n in range(1, 12)) + ('Egresado(a)',)
TELEFONO_RE = re.compile(r'^[0-9+() -]{8,30}$')

LIMITES = {
    'habilidades': 1200, 'experiencia': 2000, 'mensaje': 1500,
    'telefono': 30, 'carrera': 120,
}


def _error(mensaje, codigo):
    return jsonify({'ok': False, 'mensaje': mensaje}), codigo


def _texto(campo):
    valor = request.form.get(campo, '')
    return valor.strip() if isinstance(valor, str) else ''


def _ya_postulado(vacante_id, alumno_id):
    return Postulacion.query.filter_by(vacante_id=vacante_id, alumno_id=alumno_id).first() is not None


def _tamano(archivo):
    """Tamaño real del archivo recibido (no se confía en lo que diga el cliente)."""
    flujo = archivo.stream
    flujo.seek(0, os.SEEK_END)
    tamano = flujo.tell()
    flujo.seek(0)
    return tamano


# =========================================================================
# ENVIAR POSTULACIÓN (alumno)
# =========================================================================
@postulaciones_bp.route('/api/postulaciones', methods=['POST'])
def crear_postulacion():
    usuario_id = session.get('usuario_id')
    if not usuario_id:
        return _error('No autorizado', 401)

    alumno = Alumno.query.filter_by(usuario_id=usuario_id).first()
    if not alumno:
        return _error('Tu cuenta no tiene registro de alumno. Contacta a Servicios Escolares.', 403)

    # --- Vacante -----------------------------------------------------------
    try:
        vacante_id = int(request.form.get('vacante_id', ''))
    except ValueError:
        return _error('Vacante no válida', 400)

    vacante = db.session.get(Vacante, vacante_id)
    if not vacante or not vacante.activo:
        return _error('La vacante no existe o ya no está disponible', 404)

    # Verificación rápida; la garantía real es la restricción uq_alumno_vacante
    if _ya_postulado(vacante.id, alumno.id):
        return _error('Ya te postulaste a esta vacante', 409)

    # --- Campos de texto ---------------------------------------------------
    campos = {c: _texto(c) for c in ('habilidades', 'experiencia', 'mensaje',
                                     'telefono', 'carrera', 'semestre')}
    for obligatorio in ('habilidades', 'telefono', 'carrera', 'semestre'):
        if not campos[obligatorio]:
            return _error(f'Falta el campo: {obligatorio}', 400)
    for campo, limite in LIMITES.items():
        if len(campos[campo]) > limite:
            return _error(f'El campo {campo} excede {limite} caracteres', 400)
    if not TELEFONO_RE.match(campos['telefono']):
        return _error('Teléfono no válido', 400)
    if campos['semestre'] not in SEMESTRES:
        return _error('Cuatrimestre no válido', 400)

    # --- CV (PDF, máx. 5 MB) -----------------------------------------------
    cv = request.files.get('cv')
    if not cv or not cv.filename:
        return _error('Adjunta tu CV en PDF', 400)
    if not cv.filename.lower().endswith('.pdf'):
        return _error('El CV debe ser un archivo PDF', 400)

    tamano = _tamano(cv)
    if tamano == 0:
        return _error('El archivo del CV está vacío', 400)
    if tamano > MAX_CV_BYTES:
        return _error('El CV no puede pesar más de 5 MB', 413)
    contenido = cv.stream.read()
    if not contenido.startswith(FIRMA_PDF):
        # La extensión no basta: se valida el contenido real del archivo
        return _error('El archivo no es un PDF válido', 400)

    try:
        # Datos editables del alumno (los de identidad no se tocan)
        alumno.telefono = campos['telefono']
        alumno.carrera = campos['carrera']
        alumno.semestre = campos['semestre']

        postulacion = Postulacion(
            vacante_id=vacante.id,
            alumno_id=alumno.id,
            habilidades=campos['habilidades'],
            experiencia=campos['experiencia'] or None,
            mensaje=campos['mensaje'] or None,
            # Identificador único del CV (el contenido vive en postulacion_cv)
            cv_storage_key=uuid.uuid4().hex,
            cv_nombre=(secure_filename(cv.filename) or 'cv.pdf')[:255],
            cv_content_type='application/pdf',
            cv_tamano_bytes=tamano,
        )
        db.session.add(postulacion)
        db.session.flush()
        # El PDF se guarda en Neon en la misma transacción: si algo falla,
        # no queda ni la postulación ni el archivo (no hay disco en Render gratis)
        db.session.add(PostulacionCV(postulacion_id=postulacion.id, contenido=contenido))
        db.session.add(Auditoria(
            usuario_id=usuario_id,
            accion='Postulación a vacante',
            tabla_afectada='postulaciones',
            registro_id=postulacion.id,
            descripcion=f'Vacante #{vacante.id}: {vacante.titulo}',
        ))
        db.session.commit()
        return jsonify({'ok': True, 'id': postulacion.id}), 201

    except IntegrityError:
        # Dos envíos simultáneos: el segundo choca con uq_alumno_vacante
        db.session.rollback()
        return _error('Ya te postulaste a esta vacante', 409)

    except Exception:
        db.session.rollback()
        current_app.logger.exception('Error al guardar una postulación (usuario %s)', usuario_id)
        return _error('No fue posible guardar tu postulación', 500)


# =========================================================================
# POSTULACIONES RECIBIDAS (Empresa: las de su empresa; Administrador: todas)
# =========================================================================
@postulaciones_bp.route('/api/postulaciones', methods=['GET'])
def listar_postulaciones():
    if not session.get('usuario_id'):
        return _error('No autorizado', 401)
    usuario = usuario_en_sesion()
    perfil = perfil_de_carga(usuario)
    if not perfil:
        return _error('No tienes permiso para ver postulaciones', 403)

    filas = (db.session.query(Postulacion, Vacante, Alumno, Usuario)
             .join(Vacante, Postulacion.vacante_id == Vacante.id)
             .join(Alumno, Postulacion.alumno_id == Alumno.id)
             .join(Usuario, Alumno.usuario_id == Usuario.id)
             .filter(filtro_vacantes_visibles(usuario, perfil))
             .order_by(Postulacion.creado_en.desc(), Postulacion.id.desc())
             .all())

    return jsonify({'ok': True, 'postulaciones': [{
        'id': p.id,
        'vacante_id': v.id,
        'vacante_titulo': v.titulo,
        'alumno': f'{u.nombre} {u.apellido or ""}'.strip(),
        'correo': u.email,
        'matricula': a.matricula,
        'carrera': a.carrera,
        'semestre': a.semestre,
        'telefono': a.telefono,
        'habilidades': p.habilidades,
        'experiencia': p.experiencia,
        'mensaje': p.mensaje,
        'cv_nombre': p.cv_nombre,
        'cv_tamano_bytes': p.cv_tamano_bytes,
        'estado': p.estado,
        'recibida_en': _iso(p.creado_en),
    } for p, v, a, u in filas]}), 200


# =========================================================================
# DESCARGAR CV (mismas reglas de visibilidad que el listado)
# =========================================================================
@postulaciones_bp.route('/api/postulaciones/<int:postulacion_id>/cv', methods=['GET'])
def descargar_cv(postulacion_id):
    if not session.get('usuario_id'):
        return _error('No autorizado', 401)
    usuario = usuario_en_sesion()
    perfil = perfil_de_carga(usuario)
    if not perfil:
        return _error('No tienes permiso para descargar CV', 403)
    usuario_id = usuario.id

    postulacion = db.session.get(Postulacion, postulacion_id)
    if not postulacion:
        return _error('Postulación no encontrada', 404)

    vacante = db.session.get(Vacante, postulacion.vacante_id)
    if not vacante or not puede_ver_vacante(usuario, perfil, vacante):
        return _error('Esta postulación no pertenece a tus vacantes', 403)

    archivo = db.session.get(PostulacionCV, postulacion.id)
    if not archivo:
        return _error('El CV de esta postulación no está disponible', 404)
    contenido = archivo.contenido

    try:
        db.session.add(Auditoria(
            usuario_id=usuario_id,
            accion='Descarga de CV',
            tabla_afectada='postulaciones',
            registro_id=postulacion.id,
        ))
        db.session.commit()
    except Exception:
        # La descarga continúa aunque no se pueda auditar, pero queda en el log
        db.session.rollback()
        current_app.logger.exception('No se pudo auditar la descarga del CV %s', postulacion.id)

    return send_file(
        io.BytesIO(contenido),
        as_attachment=True,
        download_name=postulacion.cv_nombre or 'cv.pdf',
        mimetype='application/pdf',
    )
