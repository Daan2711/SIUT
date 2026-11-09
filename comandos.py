"""Comandos de administración de SIUT (Flask CLI).

Uso (desde la raíz del proyecto, con DATABASE_URL apuntando a la base deseada):

    flask crear-usuario --rol Administrador --email admin@utsc.edu.mx --nombre Ana
    flask crear-usuario --rol Alumno --email a@utsc.edu.mx --nombre Luis \
        --matricula UTSC-001 --carrera "Desarrollo de Software" --semestre "3° semestre"
    flask crear-usuario --rol Profesor --email p@utsc.edu.mx --nombre Eva --num-empleado E-01
    flask crear-usuario --rol Empresa --email rh@tecnonova.mx --nombre Carla --empresa TecnoNova

La contraseña se pide de forma oculta (con confirmación) y la cuenta queda con
cambio de contraseña obligatorio en el primer inicio de sesión.

Neon exige que cada cuenta se cree junto con lo que su rol requiere (perfil
de alumno o de profesor, o empresa) en la MISMA transacción; este comando lo
hace así. El plan gratis de Render no tiene consola: se ejecuta desde un
equipo local con el DATABASE_URL de Neon.
"""
import re

import click
from flask.cli import with_appcontext
from sqlalchemy import func
from sqlalchemy.exc import DBAPIError

from Database.database import db
from Models.models import Usuario, Alumno, Profesor, Empresa, Auditoria
from Controllers.authController import bcrypt
from Controllers.postulacionesController import SEMESTRES, TELEFONO_RE

ROLES = ('Alumno', 'Profesor', 'Empresa', 'Administrador')
EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')

# Largos máximos de las columnas en Neon
LARGOS = {
    'email': 255, 'nombre': 100, 'apellido': 100, 'matricula': 50, 'carrera': 120,
    'telefono': 30, 'num_empleado': 50, 'departamento': 120, 'especialidad': 150,
    'empresa': 150,
}


def _texto(valor):
    return (valor or '').strip()


def _fallar(mensaje):
    raise click.ClickException(mensaje)


def _descripcion_bd():
    """Servidor y base de datos destino, sin usuario ni contraseña."""
    url = db.engine.url
    return f'{url.get_backend_name()} - {url.host or "local"} / {url.database}'


@click.command('crear-usuario')
@click.option('--rol', required=True, type=click.Choice(ROLES, case_sensitive=False),
              help='Rol de la cuenta.')
@click.option('--email', required=True, help='Correo (será el usuario para iniciar sesión).')
@click.option('--nombre', required=True)
@click.option('--apellido', default='')
@click.option('--matricula', help='Alumno: matrícula (obligatoria, única).')
@click.option('--carrera', help='Alumno: carrera.')
@click.option('--semestre', type=click.Choice(sorted(SEMESTRES)), help='Alumno: semestre.')
@click.option('--telefono', help='Alumno: teléfono.')
@click.option('--num-empleado', 'num_empleado', help='Profesor: número de empleado (obligatorio, único).')
@click.option('--departamento', help='Profesor: departamento.')
@click.option('--especialidad', help='Profesor: especialidad.')
@click.option('--empresa', help='Empresa: nombre de la empresa (se crea si no existe).')
@click.option('--password', prompt='Contraseña temporal', hide_input=True,
              confirmation_prompt=True,
              help='Mejor no pasarla aquí: si se omite se pide de forma oculta.')
@click.option('--si', 'confirmado', is_flag=True, help='No pedir confirmación.')
@with_appcontext
def crear_usuario(rol, email, nombre, apellido, matricula, carrera, semestre, telefono,
                  num_empleado, departamento, especialidad, empresa, password, confirmado):
    """Crea una cuenta de SIUT con el perfil que exige su rol."""
    rol = next(r for r in ROLES if r.lower() == rol.lower())
    datos = {
        'email': _texto(email).lower(), 'nombre': _texto(nombre), 'apellido': _texto(apellido),
        'matricula': _texto(matricula), 'carrera': _texto(carrera), 'telefono': _texto(telefono),
        'num_empleado': _texto(num_empleado), 'departamento': _texto(departamento),
        'especialidad': _texto(especialidad), 'empresa': _texto(empresa),
    }

    # --- Validaciones -----------------------------------------------------
    if not EMAIL_RE.match(datos['email']):
        _fallar('Correo no válido.')
    if not datos['nombre']:
        _fallar('El nombre es obligatorio.')
    for campo, largo in LARGOS.items():
        if len(datos[campo]) > largo:
            _fallar(f'{campo} excede {largo} caracteres.')
    if len(password) < 8:
        _fallar('La contraseña debe tener al menos 8 caracteres.')
    if rol == 'Alumno' and not datos['matricula']:
        _fallar('Un Alumno necesita --matricula.')
    if rol == 'Alumno' and datos['telefono'] and not TELEFONO_RE.match(datos['telefono']):
        _fallar('Teléfono no válido.')
    if rol == 'Profesor' and not datos['num_empleado']:
        _fallar('Un Profesor necesita --num-empleado.')
    if rol == 'Empresa' and not datos['empresa']:
        _fallar('Una cuenta Empresa necesita --empresa.')

    if Usuario.query.filter(func.lower(Usuario.email) == datos['email']).first():
        _fallar(f'Ya existe una cuenta con el correo {datos["email"]}.')
    if rol == 'Alumno' and Alumno.query.filter_by(matricula=datos['matricula']).first():
        _fallar(f'La matrícula {datos["matricula"]} ya está registrada.')
    if rol == 'Profesor' and Profesor.query.filter_by(num_empleado=datos['num_empleado']).first():
        _fallar(f'El número de empleado {datos["num_empleado"]} ya está registrado.')

    empresa_existente = None
    if rol == 'Empresa':
        empresa_existente = (Empresa.query
                             .filter(func.lower(Empresa.nombre) == datos['empresa'].lower())
                             .order_by(Empresa.id).first())
        if empresa_existente and Usuario.query.filter_by(
                rol='Empresa', empresa_id=empresa_existente.id).first():
            _fallar(f'La empresa {empresa_existente.nombre} ya tiene una cuenta Empresa '
                    '(se permite una por empresa).')

    # --- Confirmación -----------------------------------------------------
    click.echo(f'\nBase de datos destino: {_descripcion_bd()}')
    click.echo(f'Cuenta: {rol} - {datos["email"]} - {datos["nombre"]} {datos["apellido"]}'.rstrip())
    if rol == 'Empresa':
        accion = 'existente' if empresa_existente else 'NUEVA'
        click.echo(f'Empresa ({accion}): {datos["empresa"]}')
    if not confirmado:
        click.confirm('¿Crear la cuenta?', abort=True)

    # --- Alta en una sola transacción -------------------------------------
    try:
        empresa_id = None
        if rol == 'Empresa':
            if not empresa_existente:
                empresa_existente = Empresa(nombre=datos['empresa'])
                db.session.add(empresa_existente)
                db.session.flush()
            empresa_id = empresa_existente.id

        usuario = Usuario(
            nombre=datos['nombre'], apellido=datos['apellido'] or None, email=datos['email'],
            password_hash=bcrypt.generate_password_hash(password).decode('utf-8'),
            rol=rol, empresa_id=empresa_id, activo=True, primer_login=True,
        )
        db.session.add(usuario)
        db.session.flush()

        if rol == 'Alumno':
            db.session.add(Alumno(
                usuario_id=usuario.id, matricula=datos['matricula'],
                carrera=datos['carrera'] or None, semestre=semestre,
                telefono=datos['telefono'] or None,
            ))
        elif rol == 'Profesor':
            db.session.add(Profesor(
                usuario_id=usuario.id, num_empleado=datos['num_empleado'],
                departamento=datos['departamento'] or None,
                especialidad=datos['especialidad'] or None,
            ))

        db.session.add(Auditoria(
            usuario_id=None, accion='Alta de usuario (comando)', tabla_afectada='usuarios',
            registro_id=usuario.id, descripcion=f'{rol}: {datos["email"]}',
        ))
        db.session.commit()
    except DBAPIError as error:
        db.session.rollback()
        # Los triggers de Neon explican el motivo (p. ej. máximo 4 administradores)
        detalle = str(getattr(error, 'orig', error)).strip().splitlines()[0]
        _fallar(f'La base de datos rechazó la cuenta: {detalle}')

    click.echo(f'OK: cuenta creada (id {usuario.id}). Deberá cambiar la contraseña al primer inicio de sesión.')
