from flask import Blueprint, request, jsonify
from flask_bcrypt import Bcrypt
from Models.models import Usuario
from Database.database import db

# Inicializamos bcrypt y nuestro blueprint de rutas
bcrypt = Bcrypt()
auth_bp = Blueprint('auth', __name__)

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