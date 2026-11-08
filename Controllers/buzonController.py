from flask import Blueprint, request, jsonify, session
from Models.models import Sugerencia, CategoriaSugerencia
from Database.database import db

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
        # No se expone el detalle interno (SQL, esquema) al cliente
        return jsonify({'error': 'No fue posible guardar la sugerencia. Intenta nuevamente.'}), 500
