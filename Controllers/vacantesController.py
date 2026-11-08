from flask import Blueprint, request, jsonify, session
from sqlalchemy import func, true, false
from Models.models import Usuario, Vacante, Empresa, Auditoria
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

# Perfiles con permiso para publicar vacantes. Coinciden con el trigger
# trg_validar_creador_vacante de Neon: solo un Administrador (cualquier
# empresa) o una Empresa (la suya) pueden crear vacantes.
PERFIL_EMPRESA = 'empresa'              # publica a nombre de su propia empresa
PERFIL_ADMINISTRADOR = 'administrador'  # publica para cualquier empresa; ve todo


def usuario_en_sesion():
    """Usuario activo de la sesión, leído de la base de datos (o None)."""
    usuario_id = session.get('usuario_id')
    if not usuario_id:
        return None
    usuario = db.session.get(Usuario, usuario_id)
    return usuario if usuario and usuario.activo else None


def perfil_de_carga(usuario):
    """Perfil con el que el usuario puede publicar vacantes, o None.

    Rol y estado se leen de la base de datos (no de la sesión) para que un
    cambio de rol o una baja surtan efecto de inmediato.
    """
    if not usuario:
        return None
    rol = (usuario.rol or '').strip().lower()
    if rol == 'empresa' and usuario.empresa_id:
        return PERFIL_EMPRESA
    if rol == 'administrador':
        return PERFIL_ADMINISTRADOR
    return None


def puede_cargar_vacantes():
    """True si la sesión actual puede publicar vacantes y ver postulaciones."""
    return perfil_de_carga(usuario_en_sesion()) is not None


def filtro_vacantes_visibles(usuario, perfil):
    """Condición SQL de las vacantes cuyas postulaciones puede ver el usuario.

    - Empresa: las de su empresa (aunque las haya publicado un administrador).
    - Administrador: todas.
    - Cualquier otro perfil: ninguna.
    """
    if perfil == PERFIL_ADMINISTRADOR:
        return true()
    if perfil == PERFIL_EMPRESA:
        return Vacante.empresa_id == usuario.empresa_id
    return false()


def puede_ver_vacante(usuario, perfil, vacante):
    """Misma regla que filtro_vacantes_visibles, para una vacante concreta."""
    if perfil == PERFIL_ADMINISTRADOR:
        return True
    if perfil == PERFIL_EMPRESA:
        return vacante.empresa_id == usuario.empresa_id
    return False


def _iso(fecha):
    """Fecha ISO 8601 válida para el navegador (sin duplicar la zona horaria)."""
    if not fecha:
        return None
    texto = fecha.isoformat()
    return texto if fecha.tzinfo else texto + 'Z'


def _serializar(v, nombre_empresa):
    return {
        'id': v.id,
        'titulo': v.titulo,
        'empresa': nombre_empresa or '',
        'area': v.area,
        'modalidad': v.modalidad,
        'ubicacion': v.ubicacion,
        'experiencia': v.experiencia,
        'jornada': v.jornada,
        'descripcion': v.descripcion,
        'requisitos': v.requisitos,
        'publicada_en': _iso(v.publicada_en or v.creado_en),
    }


def _obtener_o_crear_empresa(nombre):
    """Busca la empresa por nombre (sin distinguir mayúsculas) o la crea."""
    empresa = (Empresa.query
               .filter(func.lower(Empresa.nombre) == nombre.lower())
               .order_by(Empresa.id)
               .first())
    if empresa:
        return empresa
    empresa = Empresa(nombre=nombre)
    db.session.add(empresa)
    db.session.flush()  # obtiene empresa.id antes del commit
    return empresa


# =========================================================================
# LISTAR VACANTES (cualquier usuario con sesión)
# =========================================================================
@vacantes_bp.route('/api/vacantes', methods=['GET'])
def listar_vacantes():
    if 'usuario_id' not in session:
        return jsonify({'ok': False, 'mensaje': 'No autorizado'}), 401

    filas = (db.session.query(Vacante, Empresa.nombre)
             .outerjoin(Empresa, Vacante.empresa_id == Empresa.id)
             .filter(Vacante.activo.is_(True))
             .order_by(Vacante.creado_en.desc())
             .all())
    return jsonify({
        'ok': True,
        'vacantes': [_serializar(v, nombre) for v, nombre in filas]
    }), 200


# =========================================================================
# CARGAR VACANTE (Empresa, Administrador o correo autorizado)
# =========================================================================
@vacantes_bp.route('/api/vacantes', methods=['POST'])
def crear_vacante():
    if 'usuario_id' not in session:
        return jsonify({'ok': False, 'mensaje': 'No autorizado'}), 401

    usuario = usuario_en_sesion()
    perfil = perfil_de_carga(usuario)
    if not perfil:
        return jsonify({'ok': False, 'mensaje': 'No tienes permiso para cargar vacantes'}), 403

    if not request.is_json:
        return jsonify({'ok': False, 'mensaje': 'Formato de solicitud inválido'}), 415

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'ok': False, 'mensaje': 'No se recibieron datos'}), 400

    # Una Empresa siempre publica a nombre propio: el campo 'empresa' se ignora
    requeridos = ['titulo', 'area', 'modalidad', 'ubicacion',
                  'experiencia', 'jornada', 'descripcion', 'requisitos']
    if perfil != PERFIL_EMPRESA:
        requeridos.insert(1, 'empresa')

    campos = {}
    for nombre in requeridos:
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

    nombre_empresa = campos.pop('empresa', None)

    try:
        if perfil == PERFIL_EMPRESA:
            empresa_id = usuario.empresa_id
        else:
            empresa_id = _obtener_o_crear_empresa(nombre_empresa).id
        vacante = Vacante(**campos, empresa_id=empresa_id, creado_por=usuario.id)
        db.session.add(vacante)
        db.session.flush()  # obtiene vacante.id antes del commit
        # 'accion' es varchar(100) en Neon: texto corto y fijo; el detalle
        # (que puede ser largo) va en 'descripcion', que es text.
        db.session.add(Auditoria(
            usuario_id=usuario.id,
            accion='Alta de vacante',
            tabla_afectada='vacantes',
            registro_id=vacante.id,
            descripcion=campos['titulo'],
        ))
        db.session.commit()
        return jsonify({'ok': True, 'id': vacante.id}), 201
    except Exception:
        db.session.rollback()
        return jsonify({'ok': False, 'mensaje': 'No fue posible guardar la vacante'}), 500
