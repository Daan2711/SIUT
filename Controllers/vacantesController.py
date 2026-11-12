from flask import Blueprint, request, jsonify, session, current_app
from sqlalchemy import func, true, false
from Models.models import Usuario, Vacante, Empresa, Postulacion, Auditoria
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


def es_administrador():
    """True si la sesión actual es de un Administrador activo (leído de la BD)."""
    return perfil_de_carga(usuario_en_sesion()) == PERFIL_ADMINISTRADOR


def pagina_inicio(usuario):
    """Página a la que se envía a cada rol después de iniciar sesión."""
    perfil = perfil_de_carga(usuario)
    if perfil == PERFIL_ADMINISTRADOR:
        return '/panel-admin.html'
    if perfil == PERFIL_EMPRESA:
        return '/vacantes-publicadas.html'
    return '/index.html'


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


def _serializar(v, nombre_empresa, editable=False, postulaciones=None):
    datos = {
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
    if editable:
        # Solo para quien puede editarla o darla de baja (su empresa o un administrador)
        datos['editable'] = True
        datos['postulaciones'] = postulaciones or 0
    return datos


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


def _validar_vacante(perfil):
    """Valida el JSON de una vacante (alta o edición). Devuelve (campos, None) o (None, respuesta de error)."""
    def _falla(mensaje, codigo=400):
        return None, (jsonify({'ok': False, 'mensaje': mensaje}), codigo)

    if not request.is_json:
        return _falla('Formato de solicitud inválido', 415)

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return _falla('No se recibieron datos')

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
            return _falla(f'Falta el campo: {nombre}')
        if nombre in LIMITES and len(valor) > LIMITES[nombre]:
            return _falla(f'El campo {nombre} excede {LIMITES[nombre]} caracteres')
        campos[nombre] = valor

    catalogos = {
        'area': AREAS, 'modalidad': MODALIDADES, 'ubicacion': UBICACIONES,
        'experiencia': EXPERIENCIAS, 'jornada': JORNADAS,
    }
    for nombre, permitidos in catalogos.items():
        if campos[nombre] not in permitidos:
            return _falla(f'Valor no válido en: {nombre}')

    # Coherencia: ubicación "Remoto" exige modalidad "Remoto"
    if campos['ubicacion'] == 'Remoto' and campos['modalidad'] != 'Remoto':
        return _falla('Si la ubicación es "Remoto", la modalidad debe ser "Remoto"')

    return campos, None


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

    usuario = usuario_en_sesion()
    perfil = perfil_de_carga(usuario)
    conteo = {}
    if perfil:
        conteo = dict(db.session.query(Postulacion.vacante_id, func.count(Postulacion.id))
                      .group_by(Postulacion.vacante_id).all())
    return jsonify({
        'ok': True,
        'vacantes': [
            _serializar(v, nombre,
                        editable=bool(perfil) and puede_ver_vacante(usuario, perfil, v),
                        postulaciones=conteo.get(v.id, 0))
            for v, nombre in filas
        ]
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

    campos, error = _validar_vacante(perfil)
    if error:
        return error

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
        current_app.logger.exception('Error al guardar una vacante (usuario %s)', usuario.id)
        return jsonify({'ok': False, 'mensaje': 'No fue posible guardar la vacante'}), 500


# =========================================================================
# EDITAR Y DAR DE BAJA (Empresa: las de su empresa; Administrador: todas)
# =========================================================================
def _vacante_gestionable(vacante_id):
    """(usuario, perfil, vacante) si la sesión puede gestionarla; si no, (None, None, respuesta de error)."""
    if 'usuario_id' not in session:
        return None, None, (jsonify({'ok': False, 'mensaje': 'No autorizado'}), 401)
    usuario = usuario_en_sesion()
    perfil = perfil_de_carga(usuario)
    if not perfil:
        return None, None, (jsonify({'ok': False, 'mensaje': 'No tienes permiso para modificar vacantes'}), 403)
    vacante = db.session.get(Vacante, vacante_id)
    if not vacante or not vacante.activo:
        return None, None, (jsonify({'ok': False, 'mensaje': 'La vacante no existe o ya fue dada de baja'}), 404)
    if not puede_ver_vacante(usuario, perfil, vacante):
        return None, None, (jsonify({'ok': False, 'mensaje': 'Esta vacante no pertenece a tu empresa'}), 403)
    return usuario, perfil, vacante


def _nombre_empresa(vacante):
    empresa = db.session.get(Empresa, vacante.empresa_id)
    return empresa.nombre if empresa else ''


@vacantes_bp.route('/api/vacantes/<int:vacante_id>', methods=['GET'])
def obtener_vacante(vacante_id):
    """Datos de una vacante para el formulario de edición."""
    usuario, perfil, vacante = _vacante_gestionable(vacante_id)
    if usuario is None:
        return vacante
    return jsonify({'ok': True, 'vacante': _serializar(vacante, _nombre_empresa(vacante))}), 200


@vacantes_bp.route('/api/vacantes/<int:vacante_id>', methods=['POST'])
def editar_vacante(vacante_id):
    usuario, perfil, vacante = _vacante_gestionable(vacante_id)
    if usuario is None:
        return vacante

    campos, error = _validar_vacante(perfil)
    if error:
        return error
    nombre_empresa = campos.pop('empresa', None)

    # Una Empresa no puede mover la vacante a otra empresa. El administrador sí,
    # salvo que la haya publicado una Empresa: el trigger trg_validar_creador_vacante
    # de Neon exige que el creador pertenezca a la empresa de la vacante.
    if perfil == PERFIL_ADMINISTRADOR and nombre_empresa.lower() != _nombre_empresa(vacante).lower():
        creador = db.session.get(Usuario, vacante.creado_por)
        if not creador or creador.rol != 'Administrador':
            return jsonify({
                'ok': False,
                'mensaje': 'Esta vacante la publicó la propia empresa; no se puede cambiar de empresa',
            }), 400

    try:
        if perfil == PERFIL_ADMINISTRADOR:
            vacante.empresa_id = _obtener_o_crear_empresa(nombre_empresa).id
        for campo, valor in campos.items():
            setattr(vacante, campo, valor)
        db.session.add(Auditoria(
            usuario_id=usuario.id,
            accion='Edición de vacante',
            tabla_afectada='vacantes',
            registro_id=vacante.id,
            descripcion=campos['titulo'],
        ))
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Error al editar la vacante %s (usuario %s)', vacante_id, usuario.id)
        return jsonify({'ok': False, 'mensaje': 'No fue posible guardar los cambios'}), 500
    return jsonify({'ok': True, 'id': vacante.id}), 200


@vacantes_bp.route('/api/vacantes/<int:vacante_id>/baja', methods=['POST'])
def dar_de_baja_vacante(vacante_id):
    """Baja lógica: deja de mostrarse, pero conserva sus postulaciones y CV."""
    usuario, perfil, vacante = _vacante_gestionable(vacante_id)
    if usuario is None:
        return vacante
    try:
        vacante.activo = False
        db.session.add(Auditoria(
            usuario_id=usuario.id,
            accion='Baja de vacante',
            tabla_afectada='vacantes',
            registro_id=vacante.id,
            descripcion=vacante.titulo,
        ))
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Error al dar de baja la vacante %s (usuario %s)', vacante_id, usuario.id)
        return jsonify({'ok': False, 'mensaje': 'No fue posible borrar la vacante'}), 500
    return jsonify({'ok': True}), 200
