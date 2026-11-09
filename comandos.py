"""Comandos de administración de SIUT (Flask CLI).

Uso (desde la raíz del proyecto, con DATABASE_URL apuntando a la base deseada;
en Windows se usa "python -m flask" porque "flask" suele no estar en el PATH):

    python -m flask --app app crear-usuario --rol Administrador --email admin@utsc.edu.mx --nombre Ana
    python -m flask --app app crear-usuario --rol Alumno --email a@utsc.edu.mx --nombre Luis \
        --matricula UTSC-001 --carrera "Desarrollo de Software" --semestre "3° semestre"
    python -m flask --app app crear-usuario --rol Profesor --email p@utsc.edu.mx --nombre Eva --num-empleado E-01
    python -m flask --app app crear-usuario --rol Empresa --email rh@tecnonova.mx --nombre Carla --empresa TecnoNova

La contraseña se pide de forma oculta (con confirmación) y la cuenta queda con
cambio de contraseña obligatorio en el primer inicio de sesión.

Es la ÚNICA vía para crear Administradores. Las cuentas de Alumno, Profesor y
Empresa también se pueden crear desde la web (panel de administrador →
«Nueva cuenta»); ambos caminos usan servicios/cuentas.py.

Neon exige que cada cuenta se cree junto con lo que su rol requiere (perfil
de alumno o de profesor, o empresa) en la MISMA transacción (ver
servicios/cuentas.py). El plan gratis de Render no tiene consola: se ejecuta desde un
equipo local con el DATABASE_URL de Neon.
"""
import click
from flask.cli import with_appcontext

from Database.database import db
from servicios.cuentas import ROLES, ErrorCuenta, preparar_cuenta, guardar_cuenta
from Controllers.postulacionesController import SEMESTRES


def _descripcion_bd():
    """Servidor y base de datos destino, sin usuario ni contraseña."""
    url = db.engine.url
    return f'{url.get_backend_name()} - {url.host or "local"} / {url.database}'


def _fallar(error):
    """Muestra el error con la opción del comando que lo corrige."""
    mensaje = error.mensaje
    if error.campo and error.campo not in ('password', 'password_confirmacion'):
        mensaje += f' (--{error.campo.replace("_", "-")})'
    if error.detalle:
        mensaje += f'\nDetalle de la base de datos: {error.detalle}'
    raise click.ClickException(mensaje)


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
def crear_usuario(rol, password, confirmado, **datos):
    """Crea una cuenta de SIUT con el perfil que exige su rol."""
    try:
        cuenta = preparar_cuenta(rol, datos, password)
    except ErrorCuenta as error:
        _fallar(error)

    click.echo(f'\nBase de datos destino: {_descripcion_bd()}')
    d = cuenta.datos
    click.echo(f'Cuenta: {cuenta.rol} - {d["email"]} - {d["nombre"]} {d["apellido"]}'.rstrip())
    if cuenta.rol == 'Empresa':
        accion = 'existente' if cuenta.empresa_existente else 'NUEVA'
        click.echo(f'Empresa ({accion}): {d["empresa"]}')
    if not confirmado:
        click.confirm('¿Crear la cuenta?', abort=True)

    try:
        usuario = guardar_cuenta(cuenta, creado_por=None, origen='comando')
    except ErrorCuenta as error:
        _fallar(error)

    click.echo(f'OK: cuenta creada (id {usuario.id}). Deberá cambiar la contraseña al primer inicio de sesión.')
