"""Seguimiento de postulaciones (botón «Recibido» y comentario de la empresa),
«Mis vacantes postuladas» del alumno y notificaciones del buzón."""
import pytest

from conftest import postular
from Database.database import db
from Models.models import Auditoria, Postulacion

SUGERENCIA = {'nombre': 'Ana', 'grupo': '3A', 'departamento': 'Sistemas', 'descripcion': 'Falla el wifi'}


@pytest.fixture
def postulacion_id(alumno, vacante_id):
    return postular(alumno, vacante_id).get_json()['id']


def recibido(cliente, pid):
    return cliente.post(f'/api/postulaciones/{pid}/recibido')


def comentar(cliente, pid, **cuerpo):
    return cliente.post(f'/api/postulaciones/{pid}/comentario', json=cuerpo)


def mis_postulaciones(cliente):
    respuesta = cliente.get('/api/mis-postulaciones')
    assert respuesta.status_code == 200
    return respuesta.get_json()['postulaciones']


# --- Botón «Recibido» ----------------------------------------------------------
def test_recibido_pasa_a_en_revision_y_el_alumno_lo_ve(app, alumno, reclutador, postulacion_id):
    antes = mis_postulaciones(alumno)[0]
    assert antes['estado'] == 'Recibida' and antes['revisada_en'] is None

    respuesta = recibido(reclutador, postulacion_id)
    assert respuesta.status_code == 200
    assert respuesta.get_json()['postulacion']['estado'] == 'En revisión'

    despues = mis_postulaciones(alumno)[0]
    assert despues['estado'] == 'En revisión'
    assert despues['revisada_en']
    assert despues['empresa'] == 'TecnoNova'      # nombre que ve el alumno en el aviso

    with app.app_context():
        assert Auditoria.query.filter_by(accion='Postulación recibida por la empresa').count() == 1


def test_recibido_dos_veces_no_duplica_auditoria(app, reclutador, postulacion_id):
    assert recibido(reclutador, postulacion_id).status_code == 200
    assert recibido(reclutador, postulacion_id).status_code == 200
    with app.app_context():
        assert Auditoria.query.filter_by(accion='Postulación recibida por la empresa').count() == 1


def test_administrador_puede_marcar_recibido(administrador, postulacion_id):
    assert recibido(administrador, postulacion_id).status_code == 200


def test_otra_empresa_no_puede_marcar_ni_comentar(postulacion_id, crear_usuario_empresa, cliente_de):
    crear_usuario_empresa('rec2@x.mx', 'OtraEmpresa')
    otra = cliente_de('rec2@x.mx')
    assert recibido(otra, postulacion_id).status_code == 403
    assert comentar(otra, postulacion_id, comentario='Hola').status_code == 403


def test_alumno_no_puede_marcar_su_postulacion(alumno, postulacion_id):
    assert recibido(alumno, postulacion_id).status_code == 403
    assert comentar(alumno, postulacion_id, comentario='Me acepto solo').status_code == 403


def test_sin_sesion(anon):
    assert recibido(anon, 1).status_code == 401
    assert comentar(anon, 1, comentario='x').status_code == 401
    assert anon.get('/api/mis-postulaciones').status_code == 401


def test_postulacion_inexistente(reclutador):
    assert recibido(reclutador, 999).status_code == 404


# --- Comentario de la empresa --------------------------------------------------
def test_comentario_con_resultado_llega_al_alumno(alumno, reclutador, postulacion_id):
    recibido(reclutador, postulacion_id)
    texto = 'Felicidades, cuentas con todos los requisitos.'
    respuesta = comentar(reclutador, postulacion_id, comentario=texto, resultado='Aceptada')
    assert respuesta.status_code == 200

    p = mis_postulaciones(alumno)[0]
    assert p['comentario'] == texto
    assert p['comentario_en']
    assert p['estado'] == 'Aceptada'

    # La empresa también lo ve en su listado
    listado = reclutador.get('/api/postulaciones').get_json()['postulaciones'][0]
    assert listado['comentario'] == texto


def test_comentario_sin_resultado_queda_en_revision(alumno, reclutador, postulacion_id):
    comentar(reclutador, postulacion_id, comentario='Lo revisamos', resultado='Rechazada')
    comentar(reclutador, postulacion_id, comentario='Lo seguimos revisando')
    p = mis_postulaciones(alumno)[0]
    assert p['estado'] == 'En revisión'
    assert p['comentario'] == 'Lo seguimos revisando'


def test_comentar_sin_recibido_tambien_marca_revisada(alumno, reclutador, postulacion_id):
    assert comentar(reclutador, postulacion_id, comentario='Hola').status_code == 200
    assert mis_postulaciones(alumno)[0]['revisada_en']


@pytest.mark.parametrize('cuerpo', [
    {'comentario': ''},
    {'comentario': '   '},
    {'comentario': 'x' * 1501},
    {'comentario': 'Hola', 'resultado': 'Recibida'},
    {'comentario': 'Hola', 'resultado': 'Contratado'},
])
def test_validacion_del_comentario(app, reclutador, postulacion_id, cuerpo):
    assert comentar(reclutador, postulacion_id, **cuerpo).status_code == 400
    with app.app_context():
        assert db.session.get(Postulacion, postulacion_id).comentario_empresa is None


def test_comentario_no_json(reclutador, postulacion_id):
    respuesta = reclutador.post(f'/api/postulaciones/{postulacion_id}/comentario',
                                data='texto', content_type='text/plain')
    assert respuesta.status_code == 400


def test_error_de_bd_al_comentar_no_expone_detalle(reclutador, postulacion_id, falla_commit):
    falla_commit()
    respuesta = comentar(reclutador, postulacion_id, comentario='Hola')
    assert respuesta.status_code == 500
    assert 'SELECT' not in respuesta.get_data(as_text=True)


# --- Mis vacantes postuladas -----------------------------------------------------
def test_mis_postulaciones_solo_muestra_las_propias(alumno, vacante_id, crear_usuario,
                                                     crear_alumno, cliente_de):
    postular(alumno, vacante_id)
    otro_id = crear_usuario('otro@x.mx')
    crear_alumno(otro_id, matricula='B456')
    otro = cliente_de('otro@x.mx')
    assert mis_postulaciones(otro) == []

    propias = mis_postulaciones(alumno)
    assert [p['vacante_id'] for p in propias] == [vacante_id]
    assert propias[0]['vacante_titulo'] == 'Desarrollador'


def test_mis_postulaciones_sin_registro_de_alumno(reclutador):
    assert mis_postulaciones(reclutador) == []


def test_pagina_de_empleos_tiene_boton_de_postuladas(alumno):
    texto = alumno.get('/buzon.html').get_data(as_text=True)
    assert 'id="btnVerPostuladas"' in texto
    assert 'id="detalleSeguimiento"' in texto


def test_pagina_de_postulaciones_tiene_cuadro_de_comentario(reclutador):
    texto = reclutador.get('/postulaciones-recibidas.html').get_data(as_text=True)
    assert 'id="dialogoComentario"' in texto
    assert 'id="comentarioResultado"' in texto


# --- Notificaciones del buzón ----------------------------------------------------
def test_alumno_ve_estado_y_respuesta_de_sus_sugerencias(alumno, administrador):
    alumno.post('/guardar-sugerencia', json=SUGERENCIA)
    notificacion = alumno.get('/api/mis-sugerencias').get_json()['sugerencias'][0]
    assert notificacion['estado'] == 'Recibida'
    assert notificacion['respuesta'] is None

    sugerencia_id = notificacion['id']
    administrador.post(f'/api/sugerencias/{sugerencia_id}',
                       json={'estado': 'Atendida', 'respuesta': 'Ya se reparó el wifi'})

    notificacion = alumno.get('/api/mis-sugerencias').get_json()['sugerencias'][0]
    assert notificacion['estado'] == 'Atendida'
    assert notificacion['respuesta'] == 'Ya se reparó el wifi'
    assert notificacion['atendida_en']
    assert 'atendida_por' not in notificacion       # no se expone quién la atendió


def test_mis_sugerencias_no_muestra_las_de_otros(alumno, crear_usuario, cliente_de):
    alumno.post('/guardar-sugerencia', json=SUGERENCIA)
    crear_usuario('otro@x.mx')
    otro = cliente_de('otro@x.mx')
    assert otro.get('/api/mis-sugerencias').get_json()['sugerencias'] == []


def test_mis_sugerencias_requiere_sesion(anon):
    assert anon.get('/api/mis-sugerencias').status_code == 401


def test_pagina_del_buzon_tiene_notificaciones(alumno):
    texto = alumno.get('/sugerencias.html').get_data(as_text=True)
    assert 'id="listaNotificaciones"' in texto
    assert '<script src="js/mis-sugerencias.js"></script>' in texto
