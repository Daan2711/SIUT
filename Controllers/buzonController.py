from flask import Blueprint, request, jsonify, session
from Models.models import Sugerencia, CategoriaSugerencia
from Database.database import db

buzon_bp = Blueprint('buzon', __name__)


# =========================================================================
# GUARDAR SUGERENCIA
# =========================================================================
@buzon_bp.route('/guardar-sugerencia', methods=['POST'])
def guardar_sugerencia():

    if 'usuario_id' not in session:
        return jsonify({'error': 'No autorizado'}), 401

    data = request.get_json()

    if not data:
        return jsonify({'error': 'No se recibieron datos'}), 400

    nombre_remitente = data.get('nombre')
    grupo_grado = data.get('grupo')
    departamento = data.get('departamento')
    descripcion = data.get('descripcion')

    if not nombre_remitente or not grupo_grado or not departamento or not descripcion:
        return jsonify({'error': 'Faltan datos requeridos'}), 400

    # Buscamos si la categoría ya existe (Sistemas, Infraestructura, etc.)
    # Si el usuario eligió "Otro" y escribió un valor nuevo, la creamos.
    categoria = CategoriaSugerencia.query.filter_by(
        nombre=departamento
    ).first()

    if not categoria:
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

    try:
        db.session.add(nueva_sugerencia)
        db.session.commit()
        return jsonify({'mensaje': 'Sugerencia guardada correctamente'}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
