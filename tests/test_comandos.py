"""Comando `flask crear-usuario` (alta de cuentas en producción)."""
import pytest

from comandos import crear_usuario
from conftest import hacer_login
from Models.models import Usuario, Alumno, Profesor, Empresa, Auditoria

CLAVE = 'Temporal123'


@pytest.fixture
def ejecutar(app):
    """Ejecuta el comando con la contraseña por la entrada estándar y --si."""
    runner = app.test_cli_runner()

    def _ejecutar(*args, clave=CLAVE, confirmar=True):
        argumentos = list(args) + (['--si'] if confirmar else [])
        return runner.invoke(crear_usuario, argumentos, input=f'{clave}\n{clave}\n')
    return _ejecutar


def _usuario(app, email):
    with app.app_context():
        return Usuario.query.filter_by(email=email).first()


# --- Alta por rol ------------------------------------------------------------
def test_crea_alumno_con_su_perfil(app, ejecutar):
    resultado = ejecutar('--rol', 'Alumno', '--email', 'Luis@UTSC.edu.mx', '--nombre', 'Luis',
                         '--matricula', 'UTSC-001', '--carrera', 'Redes', '--semestre', '3° semestre')
    assert resultado.exit_code == 0, resultado.output
    with app.app_context():
        usuario = Usuario.query.filter_by(email='luis@utsc.edu.mx').one()   # correo en minúsculas
        assert usuario.rol == 'Alumno' and usuario.primer_login is True
        perfil = Alumno.query.filter_by(usuario_id=usuario.id).one()
        assert perfil.matricula == 'UTSC-001' and perfil.semestre == '3° semestre'


def test_crea_profesor_con_su_perfil(app, ejecutar):
    resultado = ejecutar('--rol', 'Profesor', '--email', 'eva@utsc.edu.mx', '--nombre', 'Eva',
                         '--num-empleado', 'E-01', '--departamento', 'Sistemas')
    assert resultado.exit_code == 0, resultado.output
    with app.app_context():
        usuario = Usuario.query.filter_by(email='eva@utsc.edu.mx').one()
        assert Profesor.query.filter_by(usuario_id=usuario.id, num_empleado='E-01').count() == 1


def test_crea_empresa_nueva_y_la_liga(app, ejecutar):
    resultado = ejecutar('--rol', 'Empresa', '--email', 'rh@tecnonova.mx', '--nombre', 'Carla',
                         '--empresa', 'TecnoNova')
    assert resultado.exit_code == 0, resultado.output
    with app.app_context():
        usuario = Usuario.query.filter_by(email='rh@tecnonova.mx').one()
        assert Empresa.query.get(usuario.empresa_id).nombre == 'TecnoNova'


def test_empresa_existente_se_reutiliza(app, ejecutar, crear_empresa):
    empresa_id = crear_empresa('TecnoNova')
    resultado = ejecutar('--rol', 'empresa', '--email', 'rh@tecnonova.mx', '--nombre', 'Carla',
                         '--empresa', 'tecnonova')
    assert resultado.exit_code == 0, resultado.output
    assert _usuario(app, 'rh@tecnonova.mx').empresa_id == empresa_id
    with app.app_context():
        assert Empresa.query.count() == 1


def test_crea_administrador_sin_perfiles(app, ejecutar):
    resultado = ejecutar('--rol', 'Administrador', '--email', 'admin@utsc.edu.mx', '--nombre', 'Ana')
    assert resultado.exit_code == 0, resultado.output
    usuario = _usuario(app, 'admin@utsc.edu.mx')
    with app.app_context():
        assert usuario.rol == 'Administrador' and usuario.empresa_id is None
        assert Alumno.query.count() == 0 and Profesor.query.count() == 0
        assert Auditoria.query.filter_by(accion='Alta de usuario (comando)').count() == 1


def test_la_cuenta_creada_inicia_sesion_y_debe_cambiar_contrasena(app, ejecutar, anon):
    ejecutar('--rol', 'Administrador', '--email', 'admin@utsc.edu.mx', '--nombre', 'Ana')
    respuesta = hacer_login(anon, 'admin@utsc.edu.mx', CLAVE)
    assert respuesta.status_code == 200
    assert respuesta.get_json()['forzar_cambio'] is True


# --- Validaciones ------------------------------------------------------------
@pytest.mark.parametrize('args, mensaje', [
    (['--rol', 'Alumno', '--email', 'a@x.mx', '--nombre', 'A'], '--matricula'),
    (['--rol', 'Profesor', '--email', 'p@x.mx', '--nombre', 'P'], '--num-empleado'),
    (['--rol', 'Empresa', '--email', 'e@x.mx', '--nombre', 'E'], '--empresa'),
    (['--rol', 'Administrador', '--email', 'no-es-correo', '--nombre', 'A'], 'Correo no válido'),
    (['--rol', 'Administrador', '--email', 'a@x.mx', '--nombre', 'x' * 101], 'excede'),
])
def test_validaciones(app, ejecutar, args, mensaje):
    resultado = ejecutar(*args)
    assert resultado.exit_code != 0
    assert mensaje in resultado.output
    with app.app_context():
        assert Usuario.query.count() == 0


def test_rol_inexistente_es_rechazado(ejecutar):
    resultado = ejecutar('--rol', 'Reclutador', '--email', 'r@x.mx', '--nombre', 'R')
    assert resultado.exit_code != 0


def test_contrasena_corta(app, ejecutar):
    resultado = ejecutar('--rol', 'Administrador', '--email', 'a@x.mx', '--nombre', 'A', clave='corta')
    assert resultado.exit_code != 0 and '8 caracteres' in resultado.output


def test_correo_duplicado_sin_distinguir_mayusculas(ejecutar, crear_usuario):
    crear_usuario('ana@x.mx', rol='Administrador')
    resultado = ejecutar('--rol', 'Administrador', '--email', 'ANA@x.mx', '--nombre', 'Ana')
    assert resultado.exit_code != 0 and 'Ya existe' in resultado.output


def test_matricula_duplicada(ejecutar, crear_usuario, crear_alumno):
    crear_alumno(crear_usuario('uno@x.mx'), matricula='UTSC-001')
    resultado = ejecutar('--rol', 'Alumno', '--email', 'dos@x.mx', '--nombre', 'Dos',
                         '--matricula', 'UTSC-001')
    assert resultado.exit_code != 0 and 'ya está registrada' in resultado.output


def test_una_cuenta_empresa_por_empresa(ejecutar, crear_usuario_empresa):
    crear_usuario_empresa('rh@tecnonova.mx', 'TecnoNova')
    resultado = ejecutar('--rol', 'Empresa', '--email', 'otro@tecnonova.mx', '--nombre', 'Otro',
                         '--empresa', 'TecnoNova')
    assert resultado.exit_code != 0 and 'una por empresa' in resultado.output


def test_sin_confirmacion_no_crea_nada(app, ejecutar):
    runner = app.test_cli_runner()
    resultado = runner.invoke(crear_usuario, ['--rol', 'Administrador', '--email', 'a@x.mx',
                                              '--nombre', 'A'], input=f'{CLAVE}\n{CLAVE}\nn\n')
    assert resultado.exit_code != 0
    assert 'Base de datos destino' in resultado.output
    with app.app_context():
        assert Usuario.query.count() == 0


def test_no_muestra_credenciales_de_la_base(app, ejecutar):
    resultado = ejecutar('--rol', 'Administrador', '--email', 'a@x.mx', '--nombre', 'A')
    assert 'Base de datos destino: sqlite' in resultado.output
    assert 'password' not in resultado.output.lower()


def test_mensajes_se_pueden_mostrar_en_la_consola_de_windows(ejecutar):
    """La consola de Windows usa cp1252: caracteres como '✓' hacían fallar el comando."""
    resultado = ejecutar('--rol', 'Administrador', '--email', 'a@x.mx', '--nombre', 'A')
    assert resultado.exit_code == 0
    resultado.output.encode('cp1252')
