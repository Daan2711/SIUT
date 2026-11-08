"""Alta y listado de vacantes, empresas y permisos."""
import pytest

from conftest import VACANTE
from Database.database import db
from Models.models import Empresa, Usuario


def test_alta_de_vacante(reclutador):
    respuesta = reclutador.post('/api/vacantes', json=VACANTE)
    assert respuesta.status_code == 201
    assert respuesta.get_json()['ok'] is True


def test_empresa_se_reutiliza_sin_distinguir_mayusculas(app, reclutador):
    reclutador.post('/api/vacantes', json=VACANTE)
    respuesta = reclutador.post('/api/vacantes', json=dict(VACANTE, empresa='tecnonova', titulo='QA'))
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


def test_sin_vacantes_emails_no_hay_correo_autorizado_por_defecto(crear_usuario, cliente_de):
    crear_usuario('cargar_vacantes@empresa.com')
    cliente = cliente_de('cargar_vacantes@empresa.com')
    assert cliente.post('/api/vacantes', json=VACANTE).status_code == 403


def test_correo_en_vacantes_emails_puede_publicar(crear_usuario, cliente_de, monkeypatch):
    monkeypatch.setenv('VACANTES_EMAILS', 'rh@x.mx, otro@x.mx')
    crear_usuario('rh@x.mx')
    assert cliente_de('rh@x.mx').post('/api/vacantes', json=VACANTE).status_code == 201


def test_permiso_se_lee_de_la_base_de_datos(app, reclutador):
    with app.app_context():
        usuario = Usuario.query.filter_by(email='rec@x.mx').first()
        usuario.rol = 'Alumno'
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
