from flask import Blueprint, request, jsonify, session
from flask_bcrypt import Bcrypt
from Models.models import Usuario, Auditoria
from Database.database import db

bcrypt = Bcrypt()
auth_bp = Blueprint('auth', __name__)

# =========================================================================
# REGISTRO
# =========================================================================
@auth_bp.route('/registro', methods=['POST'])
def registrar_usuario():
    data = request.get_json()

    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'mensaje': 'Faltan datos requeridos'}), 400

    hashed_password = bcrypt.generate_password_hash(
        data['password']
    ).decode('utf-8')

    nuevo_usuario = Usuario(
        nombre=data.get('nombre'),
        apellido=data.get('apellido'),
        email=data['email'],
        password_hash=hashed_password,
        rol=data.get('rol', 'Alumno'),
        primer_login=True
    )

    try:
        db.session.add(nuevo_usuario)
        db.session.commit()
        return jsonify({'mensaje': 'Usuario creado exitosamente'}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# =========================================================================
# LOGIN
# =========================================================================
@auth_bp.route('/login', methods=['POST'])
def login_usuario():

    data = request.get_json()

    if not data:
        return jsonify({'error': 'No se recibieron datos'}), 400

    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': 'Faltan credenciales'}), 400

    usuario = Usuario.query.filter_by(email=email).first()

    if usuario and bcrypt.check_password_hash(
        usuario.password_hash,
        password
    ):

        session['usuario_id'] = usuario.id
        session['rol'] = usuario.rol
        session['nombre'] = usuario.nombre
        session['email'] = usuario.email

        nuevo_log = Auditoria(
            usuario_id=usuario.id,
            accion='Inicio de sesiÃ³n'
        )

        db.session.add(nuevo_log)
        db.session.commit()

        if usuario.primer_login:
            return jsonify({
                'mensaje': 'Login exitoso',
                'rol': usuario.rol,
                'nombre': usuario.nombre,        # â NUEVO
                'apellido': usuario.apellido,    # â NUEVO
                'forzar_cambio': True
            }), 200

        return jsonify({
            'mensaje': 'Login exitoso',
            'rol': usuario.rol,
            'nombre': usuario.nombre,            # â NUEVO
            'apellido': usuario.apellido,        # â NUEVO
            'forzar_cambio': False
        }), 200

    return jsonify({
        'error': 'Usuario o contraseÃ±a incorrectos'
    }), 401


# =========================================================================
# USUARIO ACTUAL
# =========================================================================
@auth_bp.route('/usuario-actual', methods=['GET'])
def usuario_actual():

    if 'usuario_id' not in session:
        return jsonify({'error': 'No autorizado'}), 401

    return jsonify({
        'nombre': session.get('nombre'),
        'email': session.get('email'),
        'rol': session.get('rol')
    })


# =========================================================================
# LOGOUT
# =========================================================================
@auth_bp.route('/logout', methods=['POST'])
def logout():

    session.clear()

    return jsonify({
        'mensaje': 'SesiÃ³n cerrada correctamente'
    }), 200


# =========================================================================
# CAMBIO DE CONTRASEÃA (primer login)
# =========================================================================
@auth_bp.route('/cambiar-password', methods=['POST'])
def cambiar_password():

    if 'usuario_id' not in session:
        return jsonify({'error': 'No autorizado'}), 401

    data = request.get_json()

    nueva_password = data.get('nueva_password')
    confirmar_password = data.get('confirmar_password')

    if not nueva_password or not confirmar_password:
        return jsonify({'error': 'Faltan datos'}), 400

    if nueva_password != confirmar_password:
        return jsonify({'error': 'Las contraseÃ±as no coinciden'}), 400

    if len(nueva_password) < 8:
        return jsonify({
            'error': 'La contraseÃ±a debe tener al menos 8 caracteres'
        }), 400

    if nueva_password == 'UTSC2026':
        return jsonify({
            'error': 'No puedes usar la contraseÃ±a temporal'
        }), 400

    usuario = Usuario.query.get(session['usuario_id'])

    usuario.password_hash = bcrypt.generate_password_hash(
        nueva_password
    ).decode('utf-8')

    usuario.primer_login = False

    nuevo_log = Auditoria(
        usuario_id=usuario.id,
        accion='Cambio de contraseÃ±a obligatorio completado'
    )

    db.session.add(nuevo_log)
    db.session.commit()
    return jsonify({'mensaje': 'ContraseÃ±a actualizada correctamente'}), 200

