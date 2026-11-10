"""Configuración compartida de las pruebas.

Las variables de entorno se fijan ANTES de importar la app: app.py llama a
db.create_all() al importarse y load_dotenv() no sobrescribe variables ya
definidas, así que las pruebas nunca tocan Neon ni dependen del .env local.
"""
import io
import os
import shutil
import sys
import tempfile

import pytest

_TMP = tempfile.mkdtemp(prefix='siut-tests-')

os.environ.update({
    'DATABASE_URL': 'sqlite:///' + os.path.join(_TMP, 'siut.db'),
    'SECRET_KEY': 'clave-solo-para-pruebas',
    'TEMP_PASSWORD': '',
    'PROXY_HOPS': '0',
    'COOKIE_SECURE': 'false',
    'RATELIMIT_STORAGE_URI': 'memory://',
})

# BigInteger → INTEGER en SQLite: lo resuelve Database/database.py
from sqlalchemy import text  # noqa: E402


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app as flask_app  # noqa: E402
from Database.database import db  # noqa: E402
from extensions import limiter  # noqa: E402
from Models.models import Usuario, Alumno, Empresa, PostulacionCV  # noqa: E402
from Controllers.authController import bcrypt  # noqa: E402

# Hash rápido: el costo real (12) solo hace lentas las pruebas
bcrypt._log_rounds = 4

PASSWORD = 'Segura123'
PDF = b'%PDF-1.4\n%prueba\n' + b'0' * 1000

VACANTE = {
    'titulo': 'Desarrollador', 'empresa': 'TecnoNova', 'area': 'Tecnología',
    'modalidad': 'Remoto', 'ubicacion': 'Remoto', 'experiencia': 'Junior',
    'jornada': 'Tiempo completo', 'descripcion': 'Descripción', 'requisitos': 'Requisitos',
}


def pytest_sessionfinish(session, exitstatus):
    shutil.rmtree(_TMP, ignore_errors=True)


# -------------------------------------------------------------------------
# Réplicas en SQLite de reglas que en Neon viven en la base de datos.
# SQLite no tiene los triggers de Neon ni respeta varchar(n); sin esto, las
# pruebas pasaban con código que en Neon falla. Solo se usan en las pruebas.
# -------------------------------------------------------------------------
_CONDICION_CREADOR_INVALIDO = """
    NOT EXISTS (SELECT 1 FROM usuarios WHERE id = NEW.creado_por)
    OR NOT (
        (SELECT rol FROM usuarios WHERE id = NEW.creado_por) = 'Administrador'
        OR ((SELECT rol FROM usuarios WHERE id = NEW.creado_por) = 'Empresa'
            AND (SELECT empresa_id FROM usuarios WHERE id = NEW.creado_por) = NEW.empresa_id)
    )"""
_CONDICION_AUDITORIA_LARGA = "length(NEW.accion) > 100 OR length(NEW.tabla_afectada) > 100"

REPLICAS_NEON = [
    # trg_validar_creador_vacante: solo Administrador (cualquier empresa) o Empresa (la suya)
    f"""CREATE TRIGGER trg_validar_creador_vacante_ins BEFORE INSERT ON vacantes
        WHEN {_CONDICION_CREADOR_INVALIDO}
        BEGIN SELECT RAISE(ABORT, 'La cuenta no tiene permiso para publicar vacantes de esta empresa.'); END""",
    f"""CREATE TRIGGER trg_validar_creador_vacante_upd BEFORE UPDATE OF empresa_id, creado_por ON vacantes
        WHEN {_CONDICION_CREADOR_INVALIDO}
        BEGIN SELECT RAISE(ABORT, 'La cuenta no tiene permiso para publicar vacantes de esta empresa.'); END""",
    # auditoria.accion y auditoria.tabla_afectada son varchar(100) en Neon
    f"""CREATE TRIGGER chk_auditoria_largo_ins BEFORE INSERT ON auditoria
        WHEN {_CONDICION_AUDITORIA_LARGA}
        BEGIN SELECT RAISE(ABORT, 'value too long for type character varying(100)'); END""",
    f"""CREATE TRIGGER chk_auditoria_largo_upd BEFORE UPDATE ON auditoria
        WHEN {_CONDICION_AUDITORIA_LARGA}
        BEGIN SELECT RAISE(ABORT, 'value too long for type character varying(100)'); END""",
]


# -------------------------------------------------------------------------
# Aplicación y base de datos
# -------------------------------------------------------------------------
@pytest.fixture
def app():
    """Base de datos y límite de intentos limpios en cada prueba."""
    with flask_app.app_context():
        db.drop_all()
        db.create_all()
        for sentencia in REPLICAS_NEON:
            db.session.execute(text(sentencia))
        db.session.commit()
    limiter.reset()
    yield flask_app
    with flask_app.app_context():
        db.session.remove()


@pytest.fixture
def anon(app):
    """Cliente sin sesión."""
    return app.test_client()


@pytest.fixture
def crear_usuario(app):
    def _crear(email, rol='Alumno', primer_login=False, password=PASSWORD,
               nombre='Usuario', apellido='Prueba', activo=True, empresa_id=None):
        with app.app_context():
            usuario = Usuario(
                nombre=nombre, apellido=apellido, email=email, rol=rol,
                password_hash=bcrypt.generate_password_hash(password).decode(),
                primer_login=primer_login, activo=activo, empresa_id=empresa_id,
            )
            db.session.add(usuario)
            db.session.commit()
            return usuario.id
    return _crear


@pytest.fixture
def crear_empresa(app):
    def _crear(nombre):
        with app.app_context():
            empresa = Empresa(nombre=nombre)
            db.session.add(empresa)
            db.session.commit()
            return empresa.id
    return _crear


@pytest.fixture
def crear_usuario_empresa(crear_usuario, crear_empresa):
    """Crea una empresa y su usuario con rol 'Empresa'. Devuelve (usuario_id, empresa_id)."""
    def _crear(email, nombre_empresa, nombre='Usuario'):
        empresa_id = crear_empresa(nombre_empresa)
        return crear_usuario(email, rol='Empresa', empresa_id=empresa_id, nombre=nombre), empresa_id
    return _crear


@pytest.fixture
def crear_alumno(app):
    def _crear(usuario_id, matricula='A123', carrera='TI',
               semestre='3° cuatrimestre', telefono='8110000000'):
        with app.app_context():
            alumno = Alumno(usuario_id=usuario_id, matricula=matricula,
                            carrera=carrera, semestre=semestre, telefono=telefono)
            db.session.add(alumno)
            db.session.commit()
            return alumno.id
    return _crear


def hacer_login(cliente, email, password=PASSWORD):
    return cliente.post('/login', json={'email': email, 'password': password})


@pytest.fixture
def cliente_de(app):
    """Devuelve un cliente con sesión iniciada para el correo indicado."""
    def _cliente(email, password=PASSWORD, ip='127.0.0.1'):
        cliente = app.test_client()
        cliente.environ_base['REMOTE_ADDR'] = ip
        respuesta = hacer_login(cliente, email, password)
        assert respuesta.status_code == 200, respuesta.get_json()
        return cliente
    return _cliente


# -------------------------------------------------------------------------
# Escenarios frecuentes
# -------------------------------------------------------------------------
@pytest.fixture
def alumno(crear_usuario, crear_alumno, cliente_de):
    """Alumno con registro en 'alumnos' y sesión iniciada."""
    usuario_id = crear_usuario('alu@x.mx', nombre='Alu')
    crear_alumno(usuario_id)
    return cliente_de('alu@x.mx')


@pytest.fixture
def reclutador(crear_usuario_empresa, cliente_de):
    """Usuario con rol 'Empresa' de la empresa TecnoNova (publica a su nombre)."""
    crear_usuario_empresa('rec@x.mx', 'TecnoNova', nombre='Rec')
    return cliente_de('rec@x.mx')


@pytest.fixture
def administrador(crear_usuario, cliente_de):
    crear_usuario('admin@x.mx', rol='Administrador', nombre='Admin')
    return cliente_de('admin@x.mx')


@pytest.fixture
def vacante_id(reclutador):
    """Vacante publicada por la empresa del fixture 'reclutador'."""
    respuesta = reclutador.post('/api/vacantes', json=VACANTE)
    assert respuesta.status_code == 201, respuesta.get_json()
    return respuesta.get_json()['id']


@pytest.fixture
def falla_commit(monkeypatch):
    """Hace que el siguiente commit falle con un mensaje 'interno'."""
    def _activar():
        def boom():
            raise RuntimeError('SELECT secreto FROM tabla_interna')
        monkeypatch.setattr(db.session, 'commit', boom)
    return _activar


def postular(cliente, vacante, cv=(PDF, 'Mi CV.pdf'), **extra):
    datos = {
        'vacante_id': str(vacante), 'habilidades': 'Python',
        'telefono': '8112345678', 'carrera': 'Desarrollo de Software',
        'semestre': '5° cuatrimestre',
    }
    datos.update(extra)
    if cv is not None:
        datos['cv'] = (io.BytesIO(cv[0]), cv[1])
    return cliente.post('/api/postulaciones', data=datos, content_type='multipart/form-data')


def cvs_guardados():
    """Cantidad de CV guardados en la base de datos (tabla postulacion_cv)."""
    with flask_app.app_context():
        return PostulacionCV.query.count()
