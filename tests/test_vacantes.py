"""Alta y listado de vacantes, empresas y permisos."""
import pytest

from conftest import VACANTE
from Database.database import db
from Models.models import Auditoria, Empresa, Usuario


def test_alta_de_vacante(reclutador):
    respuesta = reclutador.post('/api/vacantes', json=VACANTE)
    assert respuesta.status_code == 201
    assert respuesta.get_json()['ok'] is True


def test_empresa_se_reutiliza_sin_distinguir_mayusculas(app, administrador):
    administrador.post('/api/vacantes', json=VACANTE)
    respuesta = administrador.post('/api/vacantes', json=dict(VACANTE, empresa='tecnonova', titulo='QA'))
    assert respuesta.status_code == 201
    with app.app_context():
        assert Empresa.query.count() == 1


def test_listado_incluye_empresa_y_fecha_valida(reclutador):
    reclutador.post('/api/vacantes', json=VACANTE)
    reclutador.post('/api/vacantes', json=dict(VACANTE, titulo='QA'))
    vacantes = reclutador.get('/api/vacantes').get_json()['vacantes']

    assert len(vacantes) == 2
    assert vacantes[0]['empresa'] == 'TecnoNova'
    assert vacantes[0]['publicada_en']
    assert '+00:00Z' not in vacantes[0]['publicada_en']


def test_listado_requiere_sesion(anon):
    assert anon.get('/api/vacantes').status_code == 401


def test_alumno_no_puede_publicar(alumno):
    assert alumno.post('/api/vacantes', json=VACANTE).status_code == 403


def test_vacantes_emails_ya_no_da_permiso(crear_usuario, cliente_de, monkeypatch):
    """VACANTES_EMAILS se eliminó: Neon solo deja publicar a Empresa o Administrador."""
    monkeypatch.setenv('VACANTES_EMAILS', 'rh@x.mx')
    crear_usuario('rh@x.mx', rol='Profesor')
    cliente = cliente_de('rh@x.mx')
    assert cliente.post('/api/vacantes', json=VACANTE).status_code == 403
    assert cliente.get('/api/postulaciones').status_code == 403
    assert cliente.get('/usuario-actual').get_json()['puede_cargar_vacantes'] is False


def test_titulo_de_150_caracteres_se_guarda_y_se_audita(app, reclutador):
    """auditoria.accion es varchar(100) en Neon; el título va en 'descripcion'."""
    titulo = 'T' * 150
    respuesta = reclutador.post('/api/vacantes', json=dict(VACANTE, titulo=titulo))
    assert respuesta.status_code == 201
    with app.app_context():
        registro = Auditoria.query.filter_by(tabla_afectada='vacantes').one()
        assert registro.accion == 'Alta de vacante'
        assert registro.descripcion == titulo
        assert registro.registro_id == respuesta.get_json()['id']


def test_permiso_se_lee_de_la_base_de_datos(app, reclutador):
    with app.app_context():
        usuario = Usuario.query.filter_by(email='rec@x.mx').first()
        usuario.rol = 'Alumno'
        usuario.empresa_id = None   # chk_usuario_empresa: solo Empresa lleva empresa_id
        db.session.commit()
    assert reclutador.post('/api/vacantes', json=VACANTE).status_code == 403


@pytest.mark.parametrize('cambio, mensaje', [
    ({'titulo': ''}, 'Falta el campo'),
    ({'area': 'Cocina'}, 'Valor no válido'),
    ({'titulo': 'x' * 151}, 'excede'),
    ({'ubicacion': 'Remoto', 'modalidad': 'Presencial'}, 'Remoto'),
])
def test_validaciones_de_alta(reclutador, cambio, mensaje):
    respuesta = reclutador.post('/api/vacantes', json=dict(VACANTE, **cambio))
    assert respuesta.status_code == 400
    assert mensaje in respuesta.get_json()['mensaje']


def test_alta_requiere_json(reclutador):
    respuesta = reclutador.post('/api/vacantes', data='titulo=x', content_type='text/plain')
    assert respuesta.status_code == 415


def test_error_de_bd_no_expone_detalle(reclutador, falla_commit):
    falla_commit()
    respuesta = reclutador.post('/api/vacantes', json=VACANTE)
    assert respuesta.status_code == 500
    assert 'secreto' not in respuesta.get_data(as_text=True)
