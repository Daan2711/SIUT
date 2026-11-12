"""Editar y borrar (baja lógica) vacantes; «Vacante cerrada» para el alumno."""
import pytest

from conftest import VACANTE, postular
from Database.database import db
from Models.models import Auditoria, Empresa, Postulacion, PostulacionCV, Vacante

EDICION = dict(VACANTE, titulo='Desarrollador backend', modalidad='Híbrido', ubicacion='Monterrey')


def editar(cliente, vid, datos=EDICION):
    return cliente.post(f'/api/vacantes/{vid}', json=datos)


def baja(cliente, vid):
    return cliente.post(f'/api/vacantes/{vid}/baja')


@pytest.fixture
def otra_empresa(crear_usuario_empresa, cliente_de):
    crear_usuario_empresa('rec2@x.mx', 'OtraEmpresa')
    return cliente_de('rec2@x.mx')


# --- Listado: quién ve los botones ------------------------------------------------
def test_listado_marca_editables_solo_para_su_empresa(reclutador, otra_empresa, alumno, administrador, vacante_id):
    def vacante(cliente):
        return cliente.get('/api/vacantes').get_json()['vacantes'][0]

    assert vacante(reclutador)['editable'] is True
    assert vacante(reclutador)['postulaciones'] == 0
    assert vacante(administrador)['editable'] is True
    assert 'editable' not in vacante(otra_empresa)
    assert 'editable' not in vacante(alumno)
    assert 'postulaciones' not in vacante(alumno)


# --- Editar ---------------------------------------------------------------------------
def test_empresa_edita_su_vacante(app, reclutador, vacante_id):
    assert reclutador.get(f'/api/vacantes/{vacante_id}').get_json()['vacante']['titulo'] == 'Desarrollador'

    respuesta = editar(reclutador, vacante_id)
    assert respuesta.status_code == 200
    with app.app_context():
        v = db.session.get(Vacante, vacante_id)
        assert (v.titulo, v.modalidad, v.ubicacion) == ('Desarrollador backend', 'Híbrido', 'Monterrey')
        assert Auditoria.query.filter_by(accion='Edición de vacante', registro_id=vacante_id).count() == 1


def test_empresa_no_puede_cambiar_de_empresa(app, reclutador, vacante_id):
    assert editar(reclutador, vacante_id, dict(EDICION, empresa='OtraEmpresa')).status_code == 200
    with app.app_context():
        v = db.session.get(Vacante, vacante_id)
        assert db.session.get(Empresa, v.empresa_id).nombre == 'TecnoNova'


def test_edicion_conserva_postulaciones(app, alumno, reclutador, vacante_id):
    postular(alumno, vacante_id)
    editar(reclutador, vacante_id)
    with app.app_context():
        assert Postulacion.query.filter_by(vacante_id=vacante_id).count() == 1


@pytest.mark.parametrize('cambio', [
    {'titulo': ''}, {'area': 'Cocina'}, {'titulo': 'x' * 151},
    {'ubicacion': 'Remoto', 'modalidad': 'Presencial'},
])
def test_edicion_valida_igual_que_el_alta(app, reclutador, vacante_id, cambio):
    assert editar(reclutador, vacante_id, dict(EDICION, **cambio)).status_code == 400
    with app.app_context():
        assert db.session.get(Vacante, vacante_id).titulo == 'Desarrollador'


def test_edicion_requiere_json(reclutador, vacante_id):
    respuesta = reclutador.post(f'/api/vacantes/{vacante_id}', data='x', content_type='text/plain')
    assert respuesta.status_code == 415


def test_otra_empresa_y_alumno_no_pueden_editar(otra_empresa, alumno, vacante_id):
    assert editar(otra_empresa, vacante_id).status_code == 403
    assert otra_empresa.get(f'/api/vacantes/{vacante_id}').status_code == 403
    assert editar(alumno, vacante_id).status_code == 403


def test_sin_sesion(anon):
    assert editar(anon, 1).status_code == 401
    assert baja(anon, 1).status_code == 401


def test_vacante_inexistente(reclutador):
    assert editar(reclutador, 999).status_code == 404
    assert baja(reclutador, 999).status_code == 404


def test_administrador_edita_vacante_de_una_empresa(app, administrador, vacante_id):
    assert editar(administrador, vacante_id).status_code == 200
    # Publicada por la empresa: no se puede mover a otra (trigger de Neon)
    respuesta = editar(administrador, vacante_id, dict(EDICION, empresa='OtraEmpresa'))
    assert respuesta.status_code == 400
    assert 'no se puede cambiar de empresa' in respuesta.get_json()['mensaje']


def test_administrador_cambia_empresa_de_su_propia_vacante(app, administrador):
    vid = administrador.post('/api/vacantes', json=VACANTE).get_json()['id']
    assert editar(administrador, vid, dict(EDICION, empresa='NuevaEmpresa')).status_code == 200
    with app.app_context():
        v = db.session.get(Vacante, vid)
        assert db.session.get(Empresa, v.empresa_id).nombre == 'NuevaEmpresa'


def test_error_de_bd_al_editar_no_expone_detalle(reclutador, vacante_id, falla_commit):
    falla_commit()
    respuesta = editar(reclutador, vacante_id)
    assert respuesta.status_code == 500
    assert 'SELECT' not in respuesta.get_data(as_text=True)


# --- Borrar (baja lógica) ----------------------------------------------------------
def test_baja_logica_conserva_postulaciones_y_cv(app, alumno, reclutador, vacante_id):
    postular(alumno, vacante_id)
    assert baja(reclutador, vacante_id).status_code == 200

    assert alumno.get('/api/vacantes').get_json()['vacantes'] == []
    with app.app_context():
        v = db.session.get(Vacante, vacante_id)
        assert v is not None and v.activo is False
        assert Postulacion.query.filter_by(vacante_id=vacante_id).count() == 1
        assert PostulacionCV.query.count() == 1
        assert Auditoria.query.filter_by(accion='Baja de vacante', registro_id=vacante_id).count() == 1

    # La empresa sigue viendo la postulación
    assert len(reclutador.get('/api/postulaciones').get_json()['postulaciones']) == 1
    # Ya no se puede editar ni volver a borrar, y nadie se puede postular
    assert editar(reclutador, vacante_id).status_code == 404
    assert baja(reclutador, vacante_id).status_code == 404


def test_otra_empresa_y_alumno_no_pueden_borrar(app, otra_empresa, alumno, vacante_id):
    assert baja(otra_empresa, vacante_id).status_code == 403
    assert baja(alumno, vacante_id).status_code == 403
    with app.app_context():
        assert db.session.get(Vacante, vacante_id).activo is True


def test_administrador_puede_borrar(administrador, vacante_id):
    assert baja(administrador, vacante_id).status_code == 200


def test_alumno_ve_vacante_cerrada_en_sus_postulaciones(alumno, reclutador, vacante_id):
    postular(alumno, vacante_id)
    activa = alumno.get('/api/mis-postulaciones').get_json()['postulaciones'][0]
    assert activa['vacante_activa'] is True

    baja(reclutador, vacante_id)
    cerrada = alumno.get('/api/mis-postulaciones').get_json()['postulaciones'][0]
    assert cerrada['vacante_activa'] is False
    assert cerrada['vacante']['titulo'] == 'Desarrollador'
    assert cerrada['vacante']['empresa'] == 'TecnoNova'
    assert 'editable' not in cerrada['vacante']


def test_formulario_tiene_modo_edicion(reclutador):
    texto = reclutador.get('/cargar-vacantes.html?editar=1').get_data(as_text=True)
    assert 'id="tituloCarga"' in texto
    assert 'id="avisoCarga"' in texto
