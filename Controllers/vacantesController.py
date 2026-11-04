import os
from flask import Blueprint, request, jsonify, session
from Models.models import Vacante, Auditoria
from Database.database import db

vacantes_bp = Blueprint('vacantes', __name__)

# Valores permitidos (mismos que los filtros de buzon.html)
AREAS = {'Tecnología', 'Administración', 'Diseño', 'Operaciones', 'Soporte técnico'}
MODALIDADES = {'Presencial', 'Híbrido', 'Remoto'}
UBICACIONES = {'Santa Catarina', 'Monterrey', 'San Pedro', 'Remoto'}
EXPERIENCIAS = {'Prácticas', 'Junior', 'Intermedio'}
JORNADAS = {'Tiempo completo', 'Medio tiempo', 'Prácticas profesionales'}

LIMITES = {
    'titulo': 150, 'empresa': 150,
    'descripcion': 2000, 'requisitos': 1500,
}

ROLES_CARGA = {'reclutador'}


def puede_cargar_vacantes():
    """True si la sesión actual puede publicar vacantes.

    Criterios (cualquiera): rol 'Reclutador', o correo incluido en la variable
    de entorno VACANTES_EMAILS (separados por coma). Se lee en cada llamada
    porque load_dotenv() corre después de importar este módulo.
    """
    if 'usuario_id' not in session:
        return False
    correos = {
        c.strip().lower()
        for c in os.getenv('VACANTES_EMAILS', 'cargar_vacantes@empresa.com').split(',')
        if c.strip()
    }
    rol = (session.get('rol') or '').strip().lower()
    email = (session.get('email') or '').strip().lower()
    return rol in ROLES_CARGA or email in correos


def _serializar(v):
    return {
        'id': v.id,
        'titulo': v.titulo,
        'empresa': v.empresa,
        'area': v.area,
        'modalidad': v.modalidad,
        'ubicacion': v.ubicacion,
        'experiencia': v.experiencia,
        'jornada': v.jornada,
        'descripcion': v.descripcion,
        'requisitos': v.requisitos,
        'publicada_en': v.creado_en.isoformat() + 'Z' if v.creado_en else None,
    }


# =========================================================================
# LISTAR VACANTES (cualquier usuario con sesión)
# =========================================================================
@vacantes_bp.route('/api/vacantes', methods=['GET'])
def listar_vacantes():
    if 'usuario_id' not in session:
        return jsonify({'ok': False, 'mensaje': 'No autorizado'}), 401

    vacantes = (Vacante.query
                .filter_by(activo=True)
                .order_by(Vacante.creado_en.desc())
                .all())
    return jsonify({'ok': True, 'vacantes': [_serializar(v) for v in vacantes]}), 200


# =========================================================================
# CARGAR VACANTE (solo reclutador / correos autorizados)
# =========================================================================
@vacantes_bp.route('/api/vacantes', methods=['POST'])
def crear_vacante():
    if 'usuario_id' not in session:
        return jsonify({'ok': False, 'mensaje': 'No autorizado'}), 401

    if not puede_cargar_vacantes():
        return jsonify({'ok': False, 'mensaje': 'No tienes permiso para cargar vacantes'}), 403

    if not request.is_json:
        return jsonify({'ok': False, 'mensaje': 'Formato de solicitud inválido'}), 415

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'ok': False, 'mensaje': 'No se recibieron datos'}), 400

    campos = {}
    for nombre in ('titulo', 'empresa', 'area', 'modalidad', 'ubicacion',
                   'experiencia', 'jornada', 'descripcion', 'requisitos'):
        valor = data.get(nombre)
        valor = valor.strip() if isinstance(valor, str) else ''
        if not valor:
            return jsonify({'ok': False, 'mensaje': f'Falta el campo: {nombre}'}), 400
        if nombre in LIMITES and len(valor) > LIMITES[nombre]:
            return jsonify({'ok': False, 'mensaje': f'El campo {nombre} excede {LIMITES[nombre]} caracteres'}), 400
        campos[nombre] = valor

    catalogos = {
        'area': AREAS, 'modalidad': MODALIDADES, 'ubicacion': UBICACIONES,
        'experiencia': EXPERIENCIAS, 'jornada': JORNADAS,
    }
    for nombre, permitidos in catalogos.items():
        if campos[nombre] not in permitidos:
            return jsonify({'ok': False, 'mensaje': f'Valor no válido en: {nombre}'}), 400

    # Coherencia: ubicación "Remoto" exige modalidad "Remoto"
    if campos['ubicacion'] == 'Remoto' and campos['modalidad'] != 'Remoto':
        return jsonify({
            'ok': False,
            'mensaje': 'Si la ubicación es "Remoto", la modalidad debe ser "Remoto"'
        }), 400

    vacante = Vacante(**campos, creado_por=session['usuario_id'])

    try:
        db.session.add(vacante)
        db.session.flush()  # obtiene vacante.id antes del commit
        db.session.add(Auditoria(
            usuario_id=session['usuario_id'],
            accion=f"Alta de vacante #{vacante.id}: {campos['titulo']}"[:255]
        ))
        db.session.commit()
        return jsonify({'ok': True, 'id': vacante.id}), 201
    except Exception:
        db.session.rollback()
        return jsonify({'ok': False, 'mensaje': 'No fue posible guardar la vacante'}), 500
