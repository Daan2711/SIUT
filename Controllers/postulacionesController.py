import os
import re
import uuid

from flask import Blueprint, request, jsonify, session, current_app, send_from_directory
from sqlalchemy.exc import IntegrityError
from werkzeug.utils import secure_filename

from Models.models import Postulacion, Vacante, Alumno, Usuario, Auditoria
from Database.database import db
from Controllers.vacantesController import puede_cargar_vacantes, _iso

postulaciones_bp = Blueprint('postulaciones', __name__)

MAX_CV_BYTES = 5 * 1024 * 1024  # 5 MB
FIRMA_PDF = b'%PDF-'

SEMESTRES = {
    '1° semestre', '2° semestre', '3° semestre', '4° semestre',
    '5° semestre', '6° semestre', 'Egresado(a)',
}
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


def _carpeta_cv():
    carpeta = current_app.config['UPLOAD_DIR']
    os.makedirs(carpeta, exist_ok=True)
    return carpeta


def _ya_postulado(vacante_id, alumno_id):
    return Postulacion.query.filter_by(vacante_id=vacante_id, alumno_id=alumno_id).first() is not None


def _borrar_archivo(ruta):
    try:
        os.remove(ruta)
    except OSError:
        pass


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
        return _error('Semestre no válido', 400)

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
    if cv.stream.read(len(FIRMA_PDF)) != FIRMA_PDF:
        # La extensión no basta: se valida el contenido real del archivo
        return _error('El archivo no es un PDF válido', 400)
    cv.stream.seek(0)

    clave = uuid.uuid4().hex
    ruta = os.path.join(_carpeta_cv(), f'{clave}.pdf')
    cv.save(ruta)

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
            cv_storage_key=clave,
            cv_nombre=(secure_filename(cv.filename) or 'cv.pdf')[:255],
            cv_content_type='application/pdf',
            cv_tamano_bytes=tamano,
        )
        db.session.add(postulacion)
        db.session.flush()
        db.session.add(Auditoria(
            usuario_id=usuario_id,
            accion=f'Postulación #{postulacion.id} a vacante #{vacante.id}',
            tabla_afectada='postulaciones',
            registro_id=postulacion.id,
        ))
        db.session.commit()
        return jsonify({'ok': True, 'id': postulacion.id}), 201

    except IntegrityError:
        # Dos envíos simultáneos: el segundo choca con uq_alumno_vacante
        db.session.rollback()
        _borrar_archivo(ruta)
        return _error('Ya te postulaste a esta vacante', 409)

    except Exception:
        db.session.rollback()
        # Sin registro en BD el archivo quedaría huérfano: se elimina
        _borrar_archivo(ruta)
        return _error('No fue posible guardar tu postulación', 500)


# =========================================================================
# POSTULACIONES RECIBIDAS (reclutador: solo de sus propias vacantes)
# =========================================================================
@postulaciones_bp.route('/api/postulaciones', methods=['GET'])
def listar_postulaciones():
    usuario_id = session.get('usuario_id')
    if not usuario_id:
        return _error('No autorizado', 401)
    if not puede_cargar_vacantes():
        return _error('No tienes permiso para ver postulaciones', 403)

    filas = (db.session.query(Postulacion, Vacante, Alumno, Usuario)
             .join(Vacante, Postulacion.vacante_id == Vacante.id)
             .join(Alumno, Postulacion.alumno_id == Alumno.id)
             .join(Usuario, Alumno.usuario_id == Usuario.id)
             .filter(Vacante.creado_por == usuario_id)
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
# DESCARGAR CV (reclutador dueño de la vacante)
# =========================================================================
@postulaciones_bp.route('/api/postulaciones/<int:postulacion_id>/cv', methods=['GET'])
def descargar_cv(postulacion_id):
    usuario_id = session.get('usuario_id')
    if not usuario_id:
        return _error('No autorizado', 401)
    if not puede_cargar_vacantes():
        return _error('No tienes permiso para descargar CV', 403)

    postulacion = db.session.get(Postulacion, postulacion_id)
    if not postulacion:
        return _error('Postulación no encontrada', 404)

    vacante = db.session.get(Vacante, postulacion.vacante_id)
    if not vacante or vacante.creado_por != usuario_id:
        return _error('Esta postulación no pertenece a tus vacantes', 403)

    # La clave la genera el servidor (uuid hex); se valida por si la BD se alteró
    if not re.fullmatch(r'[0-9a-f]{32}', postulacion.cv_storage_key or ''):
        return _error('Archivo no disponible', 404)

    carpeta = current_app.config['UPLOAD_DIR']
    if not os.path.isfile(os.path.join(carpeta, f'{postulacion.cv_storage_key}.pdf')):
        return _error('El archivo del CV ya no está disponible en el servidor', 404)

    try:
        db.session.add(Auditoria(
            usuario_id=usuario_id,
            accion=f'Descarga de CV de postulación #{postulacion.id}',
            tabla_afectada='postulaciones',
            registro_id=postulacion.id,
        ))
        db.session.commit()
    except Exception:
        db.session.rollback()

    return send_from_directory(
        carpeta, f'{postulacion.cv_storage_key}.pdf',
        as_attachment=True,
        download_name=postulacion.cv_nombre or 'cv.pdf',
        mimetype='application/pdf',
    )
