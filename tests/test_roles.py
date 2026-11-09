"""Roles válidos en Neon (Alumno, Profesor, Empresa, Administrador) y permisos
de vacantes y postulaciones por rol."""
import pytest
from sqlalchemy.exc import IntegrityError

from conftest import VACANTE, postular
from Database.database import db
from Models.models import Empresa, Vacante


# --- Restricciones de rol (las mismas CHECK de Neon) ------------------------
def test_rol_inexistente_en_neon_es_rechazado(crear_usuario):
    with pytest.raises(IntegrityError):
        crear_usuario('rec@x.mx', rol='Reclutador')


def test_empresa_sin_empresa_id_es_rechazada(crear_usuario):
    with pytest.raises(IntegrityError):
        crear_usuario('emp@x.mx', rol='Empresa')


def test_rol_distinto_de_empresa_no_lleva_empresa_id(crear_usuario, crear_empresa):
    empresa_id = crear_empresa('TecnoNova')
    with pytest.raises(IntegrityError):
        crear_usuario('alu@x.mx', rol='Alumno', empresa_id=empresa_id)


def test_un_usuario_empresa_por_empresa(crear_usuario, crear_empresa):
    empresa_id = crear_empresa('TecnoNova')
    crear_usuario('uno@x.mx', rol='Empresa', empresa_id=empresa_id)
    with pytest.raises(IntegrityError):
        crear_usuario('dos@x.mx', rol='Empresa', empresa_id=empresa_id)


# --- Publicar vacantes ------------------------------------------------------
def test_empresa_publica_a_nombre_propio_aunque_envie_otro_nombre(app, reclutador):
    respuesta = reclutador.post('/api/vacantes', json=dict(VACANTE, empresa='Otra S.A.'))
    assert respuesta.status_code == 201
    with app.app_context():
        vacante = db.session.get(Vacante, respuesta.get_json()['id'])
        assert db.session.get(Empresa, vacante.empresa_id).nombre == 'TecnoNova'
        assert Empresa.query.count() == 1          # no se creó 'Otra S.A.'


def test_empresa_no_necesita_enviar_el_campo_empresa(reclutador):
    datos = {k: v for k, v in VACANTE.items() if k != 'empresa'}
    assert reclutador.post('/api/vacantes', json=datos).status_code == 201


def test_administrador_publica_para_cualquier_empresa(app, administrador):
    respuesta = administrador.post('/api/vacantes', json=dict(VACANTE, empresa='DataLytics'))
    assert respuesta.status_code == 201
    with app.app_context():
        assert Empresa.query.filter_by(nombre='DataLytics').count() == 1


def test_administrador_debe_indicar_la_empresa(administrador):
    datos = {k: v for k, v in VACANTE.items() if k != 'empresa'}
    respuesta = administrador.post('/api/vacantes', json=datos)
    assert respuesta.status_code == 400
    assert 'empresa' in respuesta.get_json()['mensaje']


@pytest.mark.parametrize('rol', ['Alumno', 'Profesor'])
def test_alumno_y_profesor_no_publican(crear_usuario, cliente_de, rol):
    crear_usuario('x@x.mx', rol=rol)
    assert cliente_de('x@x.mx').post('/api/vacantes', json=VACANTE).status_code == 403


# --- Ver postulaciones y descargar CV ---------------------------------------
def test_empresa_ve_postulaciones_de_vacantes_publicadas_por_admin_a_su_nombre(
        alumno, reclutador, administrador):
    respuesta = administrador.post('/api/vacantes', json=dict(VACANTE, empresa='TecnoNova'))
    postulacion = postular(alumno, respuesta.get_json()['id']).get_json()['id']

    lista = reclutador.get('/api/postulaciones').get_json()['postulaciones']
    assert [p['id'] for p in lista] == [postulacion]
    assert reclutador.get(f'/api/postulaciones/{postulacion}/cv').status_code == 200


def test_administrador_ve_y_descarga_todas(alumno, vacante_id, administrador):
    postulacion = postular(alumno, vacante_id).get_json()['id']
    lista = administrador.get('/api/postulaciones').get_json()['postulaciones']
    assert [p['id'] for p in lista] == [postulacion]
    assert administrador.get(f'/api/postulaciones/{postulacion}/cv').status_code == 200


def test_profesor_no_ve_postulaciones_ni_descarga(alumno, vacante_id, crear_usuario, cliente_de):
    postulacion = postular(alumno, vacante_id).get_json()['id']
    crear_usuario('prof@x.mx', rol='Profesor')
    profesor = cliente_de('prof@x.mx')
    assert profesor.get('/api/postulaciones').status_code == 403
    assert profesor.get(f'/api/postulaciones/{postulacion}/cv').status_code == 403


# --- Réplica del trigger trg_validar_creador_vacante de Neon ---------------
def _insertar_vacante(app, creado_por, empresa_id):
    datos = {k: v for k, v in VACANTE.items() if k != 'empresa'}
    with app.app_context():
        db.session.add(Vacante(**datos, empresa_id=empresa_id, creado_por=creado_por))
        try:
            db.session.commit()
        finally:
            db.session.rollback()


def test_bd_rechaza_vacante_creada_por_rol_sin_permiso(app, crear_usuario, crear_empresa):
    empresa_id = crear_empresa('TecnoNova')
    profesor = crear_usuario('prof@x.mx', rol='Profesor')
    with pytest.raises(IntegrityError):
        _insertar_vacante(app, profesor, empresa_id)


def test_bd_rechaza_vacante_de_empresa_ajena(app, crear_usuario_empresa, crear_empresa):
    usuario_id, _ = crear_usuario_empresa('rec@x.mx', 'TecnoNova')
    otra = crear_empresa('OtraEmpresa')
    with pytest.raises(IntegrityError):
        _insertar_vacante(app, usuario_id, otra)


def test_bd_acepta_vacante_de_admin_y_de_empresa_propia(app, crear_usuario, crear_usuario_empresa):
    usuario_id, empresa_id = crear_usuario_empresa('rec@x.mx', 'TecnoNova')
    admin = crear_usuario('admin@x.mx', rol='Administrador')
    _insertar_vacante(app, usuario_id, empresa_id)
    _insertar_vacante(app, admin, empresa_id)
    with app.app_context():
        assert Vacante.query.count() == 2


def test_usuario_actual_devuelve_empresa(reclutador, administrador):
    datos = reclutador.get('/usuario-actual').get_json()
    assert datos['rol'] == 'Empresa'
    assert datos['empresa']['nombre'] == 'TecnoNova'
    assert datos['puede_cargar_vacantes'] is True

    datos_admin = administrador.get('/usuario-actual').get_json()
    assert datos_admin['empresa'] is None
    assert datos_admin['puede_cargar_vacantes'] is True
