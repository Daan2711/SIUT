"""Alta de cuentas de SIUT: lógica compartida por el comando `crear-usuario`
y el formulario «Nueva cuenta» del panel de administrador.

Neon exige que cada cuenta se cree junto con lo que su rol requiere (perfil
de alumno o de profesor, o empresa) en la MISMA transacción; aquí se hace así.

Uso:
    cuenta = preparar_cuenta(rol, datos, password, roles_permitidos=ROLES_WEB)
    usuario = guardar_cuenta(cuenta, creado_por=admin_id, origen='web')

Ambas funciones lanzan ErrorCuenta con un mensaje apto para el usuario final;
el detalle técnico de la base de datos (si lo hay) va aparte, en `detalle`.
"""
import re
from dataclasses import dataclass

from sqlalchemy import func
from sqlalchemy.exc import DBAPIError, IntegrityError

from Database.database import db
from Models.models import Usuario, Alumno, Profesor, Empresa, Auditoria
from Controllers.authController import bcrypt
from Controllers.postulacionesController import SEMESTRES, TELEFONO_RE

ROLES = ('Alumno', 'Profesor', 'Empresa', 'Administrador')
# Desde la web nunca se crean administradores: solo con `flask crear-usuario`
ROLES_WEB = ('Alumno', 'Profesor', 'Empresa')

EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
LARGO_MINIMO_PASSWORD = 8

# Largos máximos de las columnas en Neon
LARGOS = {
    'email': 255, 'nombre': 100, 'apellido': 100, 'matricula': 50, 'carrera': 120,
    'telefono': 30, 'num_empleado': 50, 'departamento': 120, 'especialidad': 150,
    'empresa': 150,
}
CAMPOS = tuple(LARGOS) + ('semestre',)

# Restricciones únicas de Neon (y sus equivalentes en SQLite) → mensaje amigable
DUPLICADOS = (
    (('uq_usuarios_email', 'usuarios.email'), 'email',
     'Ya existe una cuenta con ese correo.'),
    (('alumnos_matricula_key', 'alumnos.matricula'), 'matricula',
     'Esa matrícula ya está registrada.'),
    (('profesores_num_empleado_key', 'profesores.num_empleado'), 'num_empleado',
     'Ese número de empleado ya está registrado.'),
    (('uq_usuario_empresa', 'usuarios.empresa_id'), 'empresa',
     'Esa empresa ya tiene una cuenta Empresa (se permite una por empresa).'),
)


class ErrorCuenta(Exception):
    """Error de validación o de alta. `mensaje` se puede mostrar al usuario;
    `detalle` (opcional) es el texto técnico de la base de datos, solo para logs
    o para la consola del comando. `duplicado` indica que el dato ya existe."""

    def __init__(self, mensaje, campo=None, detalle=None, duplicado=False):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.campo = campo
        self.detalle = detalle
        self.duplicado = duplicado


@dataclass
class CuentaPreparada:
    rol: str
    datos: dict
    password: str
    empresa_existente: Empresa = None


def _texto(valor):
    return (valor if isinstance(valor, str) else '').strip()


def normalizar_rol(rol, roles_permitidos):
    """Devuelve el rol con su capitalización oficial o lanza ErrorCuenta."""
    rol = _texto(rol).lower()
    for permitido in roles_permitidos:
        if permitido.lower() == rol:
            return permitido
    raise ErrorCuenta('Rol no permitido.', 'rol')


def _comprobar_duplicados(rol, datos):
    if Usuario.query.filter(func.lower(Usuario.email) == datos['email']).first():
        raise ErrorCuenta(f'Ya existe una cuenta con el correo {datos["email"]}.', 'email',
                          duplicado=True)
    if rol == 'Alumno' and Alumno.query.filter_by(matricula=datos['matricula']).first():
        raise ErrorCuenta(f'La matrícula {datos["matricula"]} ya está registrada.', 'matricula',
                          duplicado=True)
    if rol == 'Profesor' and Profesor.query.filter_by(num_empleado=datos['num_empleado']).first():
        raise ErrorCuenta(f'El número de empleado {datos["num_empleado"]} ya está registrado.',
                          'num_empleado', duplicado=True)


def preparar_cuenta(rol, datos, password, roles_permitidos=ROLES, password_confirmacion=None):
    """Valida los datos y revisa duplicados. No escribe en la base de datos.

    `datos` puede traer: email, nombre, apellido, matricula, carrera, semestre,
    telefono, num_empleado, departamento, especialidad, empresa. Se ignoran los
    campos que no corresponden al rol.
    """
    rol = normalizar_rol(rol, roles_permitidos)
    datos = {campo: _texto(datos.get(campo)) for campo in CAMPOS}
    datos['email'] = datos['email'].lower()
    password = password if isinstance(password, str) else ''

    if not EMAIL_RE.match(datos['email']):
        raise ErrorCuenta('Correo no válido.', 'email')
    if not datos['nombre']:
        raise ErrorCuenta('El nombre es obligatorio.', 'nombre')
    for campo, largo in LARGOS.items():
        if len(datos[campo]) > largo:
            raise ErrorCuenta(f'{campo} excede {largo} caracteres.', campo)
    if len(password) < LARGO_MINIMO_PASSWORD:
        raise ErrorCuenta(f'La contraseña debe tener al menos {LARGO_MINIMO_PASSWORD} caracteres.',
                          'password')
    if password_confirmacion is not None and password != password_confirmacion:
        raise ErrorCuenta('Las contraseñas no coinciden.', 'password_confirmacion')

    if rol == 'Alumno':
        if not datos['matricula']:
            raise ErrorCuenta('La matrícula es obligatoria para un Alumno.', 'matricula')
        if datos['telefono'] and not TELEFONO_RE.match(datos['telefono']):
            raise ErrorCuenta('Teléfono no válido.', 'telefono')
        if datos['semestre'] and datos['semestre'] not in SEMESTRES:
            raise ErrorCuenta('Semestre no válido.', 'semestre')
    if rol == 'Profesor' and not datos['num_empleado']:
        raise ErrorCuenta('El número de empleado es obligatorio para un Profesor.', 'num_empleado')
    if rol == 'Empresa' and not datos['empresa']:
        raise ErrorCuenta('El nombre de la empresa es obligatorio para una cuenta Empresa.',
                          'empresa')

    _comprobar_duplicados(rol, datos)

    empresa_existente = None
    if rol == 'Empresa':
        empresa_existente = (Empresa.query
                             .filter(func.lower(Empresa.nombre) == datos['empresa'].lower())
                             .order_by(Empresa.id).first())
        if empresa_existente and Usuario.query.filter_by(
                rol='Empresa', empresa_id=empresa_existente.id).first():
            raise ErrorCuenta(f'La empresa {empresa_existente.nombre} ya tiene una cuenta Empresa '
                              '(se permite una por empresa).', 'empresa', duplicado=True)

    return CuentaPreparada(rol, datos, password, empresa_existente)


def _error_de_integridad(error):
    texto = str(getattr(error, 'orig', error))
    for claves, campo, mensaje in DUPLICADOS:
        if any(clave in texto for clave in claves):
            return ErrorCuenta(mensaje, campo, detalle=texto.strip().splitlines()[0],
                               duplicado=True)
    return None


def guardar_cuenta(cuenta, creado_por=None, origen='comando'):
    """Crea la cuenta y su perfil en una sola transacción. Devuelve el Usuario.

    `creado_por`: id del administrador que da de alta la cuenta (None desde el
    comando). La cuenta queda con cambio de contraseña obligatorio.
    """
    rol, datos = cuenta.rol, cuenta.datos
    try:
        empresa_id = None
        if rol == 'Empresa':
            empresa = cuenta.empresa_existente
            if not empresa:
                empresa = Empresa(nombre=datos['empresa'])
                db.session.add(empresa)
                db.session.flush()
            empresa_id = empresa.id

        usuario = Usuario(
            nombre=datos['nombre'], apellido=datos['apellido'] or None, email=datos['email'],
            password_hash=bcrypt.generate_password_hash(cuenta.password).decode('utf-8'),
            rol=rol, empresa_id=empresa_id, activo=True, primer_login=True,
            creado_por=creado_por,
        )
        db.session.add(usuario)
        db.session.flush()

        if rol == 'Alumno':
            db.session.add(Alumno(
                usuario_id=usuario.id, matricula=datos['matricula'],
                carrera=datos['carrera'] or None, semestre=datos['semestre'] or None,
                telefono=datos['telefono'] or None,
            ))
        elif rol == 'Profesor':
            db.session.add(Profesor(
                usuario_id=usuario.id, num_empleado=datos['num_empleado'],
                departamento=datos['departamento'] or None,
                especialidad=datos['especialidad'] or None,
            ))

        db.session.add(Auditoria(
            usuario_id=creado_por, accion=f'Alta de usuario ({origen})', tabla_afectada='usuarios',
            registro_id=usuario.id, descripcion=f'{rol}: {datos["email"]}',
        ))
        db.session.commit()
        return usuario
    except IntegrityError as error:
        # Duplicado que se coló entre la revisión previa y el alta (envíos simultáneos)
        db.session.rollback()
        amigable = _error_de_integridad(error)
        if amigable:
            raise amigable from error
        raise ErrorCuenta('La base de datos rechazó la cuenta.',
                          detalle=str(getattr(error, 'orig', error)).strip().splitlines()[0]) from error
    except DBAPIError as error:
        # Triggers de Neon (p. ej. máximo 4 administradores) u otros rechazos
        db.session.rollback()
        raise ErrorCuenta('La base de datos rechazó la cuenta.',
                          detalle=str(getattr(error, 'orig', error)).strip().splitlines()[0]) from error
