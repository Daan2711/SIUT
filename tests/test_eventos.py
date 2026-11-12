"""Inscripciones a eventos: alumno se inscribe, administrador revisa y marca «OK»."""
from datetime import datetime, timezone

import pytest

from Database.database import db
from Models.models import Auditoria, Evento, UsuarioEvento

DATOS = {'nombre': 'Ana López', 'correo': 'ana@correo.mx'}


@pytest.fixture
def crear_evento(app):
    def _crear(titulo='UT Canta 2026', publicado=True, activo=True):
        with app.app_context():
            evento = Evento(titulo=titulo, publicado=publicado, activo=activo,
                            fecha_inicio=datetime(2026, 12, 1, 6, tzinfo=timezone.utc))
            db.session.add(evento)
            db.session.commit()
            return evento.id
    return _crear


@pytest.fixture
def evento_id(crear_evento):
    return crear_evento()


def inscribir(cliente, evento, **cambios):
    return cliente.post(f'/api/eventos/{evento}/inscripcion', json=dict(DATOS, **cambios))


def marcar(cliente, inscripcion, confirmada=True):
    return cliente.post(f'/api/inscripciones-eventos/{inscripcion}/ok', json={'confirmada': confirmada})


# --- Alumno ----------------------------------------------------------------------
def test_lista_solo_eventos_publicados_y_activos(alumno, crear_evento):
    crear_evento('Hackathon')
    crear_evento('Borrador', publicado=False)
    crear_evento('Cancelado', activo=False)
    eventos = alumno.get('/api/eventos').get_json()['eventos']
    assert [e['titulo'] for e in eventos] == ['Hackathon']
    assert eventos[0]['inscrito'] is False


def test_inscripcion_valida(app, alumno, evento_id):
    respuesta = inscribir(alumno, evento_id)
    assert respuesta.status_code == 201
    with app.app_context():
        inscripcion = db.session.get(UsuarioEvento, respuesta.get_json()['id'])
        assert inscripcion.nombre == 'Ana López'
        assert inscripcion.correo == 'ana@correo.mx'
        assert inscripcion.confirmada is False
        assert Auditoria.query.filter_by(accion='Inscripción a evento').count() == 1
    assert alumno.get('/api/eventos').get_json()['eventos'][0]['inscrito'] is True


def test_inscripcion_duplicada(alumno, evento_id):
    inscribir(alumno, evento_id)
    assert inscribir(alumno, evento_id).status_code == 409


@pytest.mark.parametrize('cambios', [
    {'nombre': ''}, {'correo': ''}, {'correo': 'sin-arroba'},
    {'nombre': 'x' * 151}, {'correo': 'a@b.mx' + 'x' * 250},
])
def test_validacion(app, alumno, evento_id, cambios):
    assert inscribir(alumno, evento_id, **cambios).status_code == 400
    with app.app_context():
        assert UsuarioEvento.query.count() == 0


def test_evento_no_publicado_o_inexistente(alumno, crear_evento):
    borrador = crear_evento('Borrador', publicado=False)
    assert inscribir(alumno, borrador).status_code == 404
    assert inscribir(alumno, 999).status_code == 404


def test_requiere_sesion(anon, evento_id):
    assert anon.get('/api/eventos').status_code == 401
    assert inscribir(anon, evento_id).status_code == 401


# --- Administrador -----------------------------------------------------------------
def test_administrador_ve_inscripciones_y_marca_ok(app, alumno, administrador, evento_id):
    inscripcion_id = inscribir(alumno, evento_id).get_json()['id']

    datos = administrador.get('/api/inscripciones-eventos').get_json()
    assert datos['pendientes'] == 1
    fila = datos['inscripciones'][0]
    assert (fila['evento'], fila['nombre'], fila['correo']) == ('UT Canta 2026', 'Ana López', 'ana@correo.mx')

    respuesta = marcar(administrador, inscripcion_id)
    assert respuesta.status_code == 200
    assert respuesta.get_json()['inscripcion']['confirmada'] is True
    assert respuesta.get_json()['inscripcion']['confirmada_en']
    assert administrador.get('/api/inscripciones-eventos').get_json()['pendientes'] == 0

    # Se puede deshacer
    respuesta = marcar(administrador, inscripcion_id, confirmada=False)
    assert respuesta.get_json()['inscripcion']['confirmada'] is False
    assert respuesta.get_json()['inscripcion']['confirmada_en'] is None
    with app.app_context():
        assert Auditoria.query.filter_by(accion='Inscripción a evento marcada OK').count() == 1


@pytest.mark.parametrize('cuerpo', [{}, {'confirmada': 'si'}, {'confirmada': 1}])
def test_marcar_ok_exige_booleano(alumno, administrador, evento_id, cuerpo):
    inscripcion_id = inscribir(alumno, evento_id).get_json()['id']
    respuesta = administrador.post(f'/api/inscripciones-eventos/{inscripcion_id}/ok', json=cuerpo)
    assert respuesta.status_code == 400


def test_marcar_inscripcion_inexistente(administrador):
    assert marcar(administrador, 999).status_code == 404


def test_solo_el_administrador(alumno, reclutador, evento_id):
    inscripcion_id = inscribir(alumno, evento_id).get_json()['id']
    for cliente in (alumno, reclutador):
        assert cliente.get('/api/inscripciones-eventos').status_code == 403
        assert marcar(cliente, inscripcion_id).status_code == 403


def test_pagina_de_inscripciones_solo_administrador(anon, alumno, reclutador, administrador):
    assert anon.get('/inscripciones-eventos.html').headers['Location'].endswith('/login')
    assert alumno.get('/inscripciones-eventos.html').status_code == 302
    assert reclutador.get('/inscripciones-eventos.html').status_code == 302
    assert administrador.get('/inscripciones-eventos.html').status_code == 200


def test_panel_tiene_tarjeta_de_eventos(administrador):
    texto = administrador.get('/panel-admin.html').get_data(as_text=True)
    assert 'href="inscripciones-eventos.html"' in texto
    assert 'id="totalInscripciones"' in texto
