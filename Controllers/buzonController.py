from flask import Blueprint, request, jsonify, session, current_app
from sqlalchemy import func
from sqlalchemy.orm import aliased
from Models.models import Sugerencia, CategoriaSugerencia, Usuario, Auditoria
from Database.database import db
from Controllers.vacantesController import usuario_en_sesion, es_administrador, _iso

buzon_bp = Blueprint('buzon', __name__)

# Categorías permitidas (las mismas opciones del formulario del buzón).
# Si el usuario elige "Otro", el área que escribió se guarda dentro de la
# descripción y la sugerencia queda en la categoría "Otro": así ningún
# usuario puede crear categorías nuevas.
CATEGORIAS = {'Sistemas', 'Infraestructura', 'Mantenimiento', 'Escolares', 'Otro'}

# Límites alineados con las columnas de la tabla 'sugerencias'
LIMITES = {
    'nombre': 100,        # sugerencias.nombre_remitente String(100)
    'grupo': 50,          # sugerencias.grupo_grado String(50)
    'otro_departamento': 100,
    'descripcion': 2000,
}


# Estados válidos (CHECK chk_sugerencia_estado en Neon)
ESTADOS = ('Recibida', 'En revisión', 'Atendida', 'Rechazada')
LIMITE_RESPUESTA = 2000


def _texto(data, campo):
    valor = data.get(campo)
    return valor.strip() if isinstance(valor, str) else ''


# =========================================================================
# GUARDAR SUGERENCIA
# =========================================================================
@buzon_bp.route('/guardar-sugerencia', methods=['POST'])
def guardar_sugerencia():

    if 'usuario_id' not in session:
        return jsonify({'error': 'No autorizado'}), 401

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({'error': 'No se recibieron datos'}), 400

    nombre_remitente = _texto(data, 'nombre')
    grupo_grado = _texto(data, 'grupo')
    departamento = _texto(data, 'departamento')
    descripcion = _texto(data, 'descripcion')

    if not nombre_remitente or not grupo_grado or not departamento or not descripcion:
        return jsonify({'error': 'Faltan datos requeridos'}), 400

    # Compatibilidad: el formulario manda directamente el texto escrito en
    # "Otro" como departamento. Si no es una categoría conocida, se trata
    # como "Otro" y el texto se conserva en la descripción.
    otro_departamento = ''
    if departamento not in CATEGORIAS:
        otro_departamento = departamento
        departamento = 'Otro'

    valores = {
        'nombre': nombre_remitente,
        'grupo': grupo_grado,
        'otro_departamento': otro_departamento,
        'descripcion': descripcion,
    }
    for campo, limite in LIMITES.items():
        if len(valores[campo]) > limite:
            return jsonify({'error': f'El campo {campo} excede {limite} caracteres'}), 400

    if otro_departamento:
        descripcion = f'[Área indicada: {otro_departamento}]\n{descripcion}'

    try:
        categoria = CategoriaSugerencia.query.filter_by(nombre=departamento).first()

        if not categoria:
            # Solo puede ocurrir con una de las categorías permitidas
            categoria = CategoriaSugerencia(
                nombre=departamento,
                creado_por=session['usuario_id']
            )
            db.session.add(categoria)
            db.session.flush()  # para obtener categoria.id antes del commit final

        nueva_sugerencia = Sugerencia(
            usuario_id=session['usuario_id'],
            nombre_remitente=nombre_remitente,
            grupo_grado=grupo_grado,
            categoria_id=categoria.id,
            descripcion=descripcion,
            # 'estado' se omite a propósito: la tabla tiene un CHECK
            # constraint puesto directo en Neon que rechaza 'Pendiente'.
            # Se deja que la columna use su DEFAULT en la base de datos.
            creado_por=session['usuario_id']
        )

        db.session.add(nueva_sugerencia)
        db.session.commit()
        return jsonify({'mensaje': 'Sugerencia guardada correctamente'}), 201

    except Exception:
        db.session.rollback()
        current_app.logger.exception('Error al guardar una sugerencia (usuario %s)', session.get('usuario_id'))
        # No se expone el detalle interno (SQL, esquema) al cliente
        return jsonify({'error': 'No fue posible guardar la sugerencia. Intenta nuevamente.'}), 500


# =========================================================================
# BANDEJA DE SUGERENCIAS (solo Administrador)
# =========================================================================
def _serializar_sugerencia(sugerencia, categoria, atendio):
    return {
        'id': sugerencia.id,
        'categoria': categoria,
        'remitente': sugerencia.nombre_remitente,
        'grupo': sugerencia.grupo_grado,
        'descripcion': sugerencia.descripcion,
        'estado': sugerencia.estado,
        'respuesta': sugerencia.respuesta_admin,
        'recibida_en': _iso(sugerencia.creado_en),
        'atendida_en': _iso(sugerencia.fecha_atencion),
        'atendida_por': f'{atendio.nombre} {atendio.apellido or ""}'.strip() if atendio else None,
    }


def _consulta_sugerencias():
    atendio = aliased(Usuario)
    return (db.session.query(Sugerencia, CategoriaSugerencia.nombre, atendio)
            .join(CategoriaSugerencia, Sugerencia.categoria_id == CategoriaSugerencia.id)
            .outerjoin(atendio, Sugerencia.atendida_por == atendio.id)
            .filter(Sugerencia.activo.is_(True))), atendio


@buzon_bp.route('/api/sugerencias', methods=['GET'])
def listar_sugerencias():
    if 'usuario_id' not in session:
        return jsonify({'ok': False, 'mensaje': 'No autorizado'}), 401
    if not es_administrador():
        return jsonify({'ok': False, 'mensaje': 'Solo un administrador puede ver las sugerencias'}), 403

    estado = (request.args.get('estado') or '').strip()
    if estado and estado not in ESTADOS:
        return jsonify({'ok': False, 'mensaje': 'Estado no válido'}), 400

    consulta, _ = _consulta_sugerencias()
    if estado:
        consulta = consulta.filter(Sugerencia.estado == estado)
    filas = consulta.order_by(Sugerencia.creado_en.desc(), Sugerencia.id.desc()).all()

    conteo = dict(db.session.query(Sugerencia.estado, func.count(Sugerencia.id))
                  .filter(Sugerencia.activo.is_(True))
                  .group_by(Sugerencia.estado).all())

    return jsonify({
        'ok': True,
        'sugerencias': [_serializar_sugerencia(s, c, a) for s, c, a in filas],
        'conteo': {e: conteo.get(e, 0) for e in ESTADOS},
    }), 200


@buzon_bp.route('/api/sugerencias/<int:sugerencia_id>', methods=['POST'])
def actualizar_sugerencia(sugerencia_id):
    """Cambia el estado de una sugerencia y guarda la respuesta del administrador."""
    if 'usuario_id' not in session:
        return jsonify({'ok': False, 'mensaje': 'No autorizado'}), 401
    if not es_administrador():
        return jsonify({'ok': False, 'mensaje': 'Solo un administrador puede atender sugerencias'}), 403

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'ok': False, 'mensaje': 'No se recibieron datos'}), 400

    estado = _texto(data, 'estado')
    respuesta = _texto(data, 'respuesta')
    if estado not in ESTADOS:
        return jsonify({'ok': False, 'mensaje': 'Estado no válido'}), 400
    if len(respuesta) > LIMITE_RESPUESTA:
        return jsonify({'ok': False, 'mensaje': f'La respuesta excede {LIMITE_RESPUESTA} caracteres'}), 400

    sugerencia = db.session.get(Sugerencia, sugerencia_id)
    if not sugerencia or not sugerencia.activo:
        return jsonify({'ok': False, 'mensaje': 'Sugerencia no encontrada'}), 404

    administrador = usuario_en_sesion()
    try:
        sugerencia.estado = estado
        sugerencia.respuesta_admin = respuesta or None
        sugerencia.atendida_por = administrador.id
        sugerencia.fecha_atencion = func.now()
        db.session.add(Auditoria(
            usuario_id=administrador.id,
            accion='Atención de sugerencia',
            tabla_afectada='sugerencias',
            registro_id=sugerencia.id,
            descripcion=f'Estado: {estado}',
        ))
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Error al actualizar la sugerencia %s', sugerencia_id)
        return jsonify({'ok': False, 'mensaje': 'No fue posible actualizar la sugerencia'}), 500

    consulta, atendio = _consulta_sugerencias()
    fila = consulta.filter(Sugerencia.id == sugerencia_id).one()
    return jsonify({'ok': True, 'sugerencia': _serializar_sugerencia(*fila)}), 200
