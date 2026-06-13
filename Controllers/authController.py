from flask import Blueprint, request, jsonify
from flask_bcrypt import Bcrypt
from Models.models import Usuario
from Database.database import db
from flask import session
from Models.models import Auditoria

# Inicializamos bcrypt y nuestro blueprint de rutas
bcrypt = Bcrypt()
auth_bp = Blueprint('auth', __name__)

# RUTA DE REGISTRO PARA NUEVOS USUARIOS
@auth_bp.route('/registro', methods=['POST'])
def registrar_usuario():
    data = request.get_json()
    
    # Validamos que nos manden la info básica
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'mensaje': 'Faltan datos requeridos'}), 400

    # Aquí está la magia de BCrypt: encriptamos la contraseña
    hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
    
    # Creamos la instancia del modelo de SQLAlchemy
    nuevo_usuario = Usuario(
        nombre=data.get('nombre'),
        apellido=data.get('apellido'),
        email=data['email'],
        password_hash=hashed_password,
        rol=data.get('rol', 'Alumno') 
    )
    
    try:
        # Lo guardamos en la base de datos
        db.session.add(nuevo_usuario)
        db.session.commit()
        return jsonify({'mensaje': 'Usuario creado exitosamente'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
    
# RUTA DE LOGIN PARA USUARIOS EXISTENTES

@auth_bp.route('/login', methods=['POST'])
def login_usuario():
    data = request.get_json()

    email = data.get('email')
    password = data.get('password')
    if not email or not password:
        return jsonify({'error': 'Faltan credenciales'}), 400

    # 1. Buscamos directamente por el correo institucional
    usuario = Usuario.query.filter_by(email=email).first()

    # 2. Verificamos si existe el usuario y si la contraseña coincide
    if usuario and bcrypt.check_password_hash(usuario.password_hash, password):

        session['usuario_id'] = usuario.id
        session['rol'] = usuario.rol

        # Registrar auditoría
        nuevo_log = Auditoria(
            usuario_id=usuario.id,
            accion='Inicio de sesión'
        )

        db.session.add(nuevo_log)
        db.session.commit()

        # Detectamos si está usando la contraseña genérica temporal
        es_primer_login = (password == 'UTSC2026')

        return jsonify({
            'mensaje': 'Login exitoso',
            'rol': usuario.rol,
            'sugerir_cambio': es_primer_login
        }), 200


    return jsonify({'error': 'Usuario o contraseña incorrectos'}), 401