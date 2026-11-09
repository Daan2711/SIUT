"""Fase B: health check, navegación por rol, bandeja de sugerencias y logs."""
import logging

import pytest

from conftest import VACANTE, hacer_login
from Database.database import db
from Models.models import Sugerencia, CategoriaSugerencia, Auditoria
from sqlalchemy.exc import IntegrityError

SUGERENCIA = {'nombre': 'Ana', 'grupo': '3A', 'departamento': 'Sistemas', 'descripcion': 'Falla el wifi'}


# --- Health check ------------------------------------------------------------
def test_healthz_sin_sesion_responde_ok(anon):
    respuesta = anon.get('/healthz')
    assert respuesta.status_code == 200
    assert respuesta.get_json() == {'ok': True}


def test_healthz_responde_503_si_la_base_falla(anon, monkeypatch, caplog):
    def falla(*_a, **_k):
        raise RuntimeError('conexión perdida')
    monkeypatch.setattr(db.session, 'execute', falla)
    with caplog.at_level(logging.ERROR):
        respuesta = anon.get('/healthz')
    assert respuesta.status_code == 503
    assert respuesta.get_json() == {'ok': False}
    assert 'conexión perdida' not in respuesta.get_data(as_text=True)   # sin detalles al cliente
    assert 'Health check' in caplog.text                                 # pero sí en el log


# --- Página de inicio por rol ------------------------------------------------
@pytest.mark.parametrize('fixture, destino', [
    ('alumno', '/index.html'),
    ('reclutador', '/vacantes-publicadas.html'),
    ('administrador', '/panel-admin.html'),
])
def test_login_indica_la_pagina_de_inicio_del_rol(request, app, fixture, destino):
    request.getfixturevalue(fixture)                     # crea la cuenta
    correo = {'alumno': 'alu@x.mx', 'reclutador': 'rec@x.mx', 'administrador': 'admin@x.mx'}[fixture]
    respuesta = hacer_login(app.test_client(), correo)
    assert respuesta.get_json()['destino'] == destino


# --- Páginas del administrador -----------------------------------------------
@pytest.mark.parametrize('pagina', ['/panel-admin.html', '/sugerencias-admin.html'])
def test_paginas_de_admin_solo_para_administrador(alumno, reclutador, administrador, anon, pagina):
    assert anon.get(pagina).headers['Location'].endswith('/login')
    assert alumno.get(pagina).headers['Location'].endswith('/index.html')
    assert reclutador.get(pagina).headers['Location'].endswith('/index.html')
    respuesta = administrador.get(pagina)
    assert respuesta.status_code == 200
    assert 'Admin Prueba' in respuesta.get_data(as_text=True)


@pytest.mark.parametrize('pagina', [
    '/cargar-vacantes.html', '/vacantes-publicadas.html', '/postulaciones-recibidas.html',
    '/panel-admin.html', '/sugerencias-admin.html',
])
def test_paginas_de_gestion_tienen_menu_y_cerrar_sesion(administrador, pagina):
    texto = administrador.get(pagina).get_data(as_text=True)
    assert 'id="cerrarSesion"' in texto
    assert 'js/gestion.js' in texto
    # Los enlaces de administrador vienen ocultos; gestion.js los muestra según el rol
    assert 'href="sugerencias-admin.html" data-solo-admin hidden' in texto or \
           'aria-current="page" data-solo-admin hidden' in texto


# --- Bandeja de sugerencias ------------------------------------------------
@pytest.fixture
def sugerencia_id(app, alumno):
    alumno.post('/guardar-sugerencia', json=SUGERENCIA)
    with app.app_context():
        return Sugerencia.query.one().id


def test_listar_sugerencias_solo_administrador(anon, alumno, reclutador, administrador, sugerencia_id):
    assert anon.get('/api/sugerencias').status_code == 401
    assert alumno.get('/api/sugerencias').status_code == 403
    assert reclutador.get('/api/sugerencias').status_code == 403
    datos = administrador.get('/api/sugerencias').get_json()
    assert [s['id'] for s in datos['sugerencias']] == [sugerencia_id]
    assert datos['sugerencias'][0]['categoria'] == 'Sistemas'
    assert datos['conteo'] == {'Recibida': 1, 'En revisión': 0, 'Atendida': 0, 'Rechazada': 0}


def test_filtrar_por_estado(administrador, sugerencia_id):
    assert len(administrador.get('/api/sugerencias?estado=Recibida').get_json()['sugerencias']) == 1
    assert administrador.get('/api/sugerencias?estado=Atendida').get_json()['sugerencias'] == []
    assert administrador.get('/api/sugerencias?estado=Inventado').status_code == 400


def test_atender_sugerencia(app, administrador, sugerencia_id):
    respuesta = administrador.post(f'/api/sugerencias/{sugerencia_id}',
                                   json={'estado': 'Atendida', 'respuesta': 'Se cambió el router.'})
    assert respuesta.status_code == 200
    sugerencia = respuesta.get_json()['sugerencia']
    assert sugerencia['estado'] == 'Atendida'
    assert sugerencia['respuesta'] == 'Se cambió el router.'
    assert sugerencia['atendida_por'] == 'Admin Prueba'
    assert sugerencia['atendida_en']
    with app.app_context():
        assert Auditoria.query.filter_by(accion='Atención de sugerencia').count() == 1


@pytest.mark.parametrize('cuerpo, codigo', [
    ({'estado': 'Pendiente'}, 400),                       # estado que Neon no admite
    ({'estado': 'Atendida', 'respuesta': 'x' * 2001}, 400),
    ({}, 400),
])
def test_validaciones_al_atender(administrador, sugerencia_id, cuerpo, codigo):
    assert administrador.post(f'/api/sugerencias/{sugerencia_id}', json=cuerpo).status_code == codigo


def test_atender_sugerencia_inexistente(administrador):
    assert administrador.post('/api/sugerencias/999', json={'estado': 'Atendida'}).status_code == 404


def test_solo_administrador_atiende(alumno, reclutador, sugerencia_id):
    assert alumno.post(f'/api/sugerencias/{sugerencia_id}', json={'estado': 'Atendida'}).status_code == 403
    assert reclutador.post(f'/api/sugerencias/{sugerencia_id}', json={'estado': 'Atendida'}).status_code == 403


def test_bd_rechaza_estado_de_sugerencia_invalido(app, sugerencia_id):
    """Réplica del CHECK chk_sugerencia_estado de Neon."""
    with app.app_context():
        db.session.get(Sugerencia, sugerencia_id).estado = 'Pendiente'
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()


# --- Registro de errores ---------------------------------------------------
def test_los_errores_500_quedan_en_el_log(reclutador, falla_commit, caplog):
    falla_commit()
    with caplog.at_level(logging.ERROR):
        respuesta = reclutador.post('/api/vacantes', json=VACANTE)
    assert respuesta.status_code == 500
    assert 'Error al guardar una vacante' in caplog.text
    assert 'SELECT secreto' in caplog.text                   # la traza completa va al log...
    assert 'secreto' not in respuesta.get_data(as_text=True)  # ...pero no al cliente
