"""Protección CSRF central: toda petición con sesión que cambia datos exige X-CSRF-Token."""
import pytest

from conftest import hacer_login, PASSWORD, VACANTE

MENSAJE = 'La sesión del formulario expiró. Recarga la página e intenta de nuevo.'

# Todas las rutas POST con sesión (el id no importa: CSRF se valida antes)
RUTAS_POST = [
    '/logout',
    '/cambiar-password',
    '/guardar-sugerencia',
    '/api/sugerencias/1',
    '/api/admin/cuentas',
    '/api/eventos/1/inscripcion',
    '/api/inscripciones-eventos/1/ok',
    '/api/postulaciones',
    '/api/postulaciones/1/recibido',
    '/api/postulaciones/1/comentario',
    '/api/vacantes',
    '/api/vacantes/1',
    '/api/vacantes/1/baja',
]

PAGINAS_CON_CSRF = [
    '/index.html', '/horario.html', '/maestros.html', '/buzon.html', '/sugerencias.html',
    '/soporte.html', '/vacantes-publicadas.html', '/cargar-vacantes.html',
    '/postulaciones-recibidas.html', '/panel-admin.html', '/sugerencias-admin.html',
    '/nueva-cuenta.html', '/inscripciones-eventos.html', '/inscripcion.html',
    '/cambiar-password',
]


def sin_token_automatico(cliente):
    cliente.csrf_auto = False
    return cliente


@pytest.mark.parametrize('ruta', RUTAS_POST)
@pytest.mark.parametrize('token', [None, '', 'token-falso'])
def test_post_con_sesion_sin_token_valido_da_403(administrador, ruta, token):
    sin_token_automatico(administrador)
    cabeceras = {} if token is None else {'X-CSRF-Token': token}
    respuesta = administrador.post(ruta, json={}, headers=cabeceras)
    assert respuesta.status_code == 403
    assert respuesta.get_json()['error'] == MENSAJE


def test_logout_sin_token_no_cierra_la_sesion(alumno):
    sin_token_automatico(alumno)
    assert alumno.post('/logout').status_code == 403
    assert alumno.get('/usuario-actual').status_code == 200


def test_token_de_otra_sesion_no_sirve(alumno, administrador):
    ajeno = administrador.get('/api/csrf-token').get_json()['csrf_token']
    sin_token_automatico(alumno)
    assert alumno.post('/logout', headers={'X-CSRF-Token': ajeno}).status_code == 403


def test_con_token_valido_funciona(reclutador):
    token = reclutador.get('/api/csrf-token').get_json()['csrf_token']
    sin_token_automatico(reclutador)
    respuesta = reclutador.post('/api/vacantes', json=VACANTE, headers={'X-CSRF-Token': token})
    assert respuesta.status_code == 201
    assert reclutador.post('/logout', headers={'X-CSRF-Token': token}).status_code == 200


def test_login_no_exige_token(crear_usuario, anon):
    crear_usuario('alu@x.mx')
    assert hacer_login(anon, 'alu@x.mx', PASSWORD).status_code == 200


def test_sin_sesion_responde_401_y_no_403(anon):
    assert anon.post('/api/vacantes', json=VACANTE).status_code == 401
    assert anon.post('/logout').status_code == 401


# --- Endpoint del token ------------------------------------------------------
def test_endpoint_del_token(alumno):
    respuesta = alumno.get('/api/csrf-token')
    assert respuesta.status_code == 200
    assert len(respuesta.get_json()['csrf_token']) >= 32
    assert 'no-store' in respuesta.headers['Cache-Control']
    # El mismo token durante toda la sesión
    assert alumno.get('/api/csrf-token').get_json() == respuesta.get_json()


def test_endpoint_del_token_sin_sesion(anon):
    assert anon.get('/api/csrf-token').status_code == 401


def test_sesion_antigua_sin_token_recibe_uno(alumno):
    with alumno.session_transaction() as sesion:
        sesion.pop('_csrf_token')
    token = alumno.get('/api/csrf-token').get_json()['csrf_token']
    sin_token_automatico(alumno)
    assert alumno.post('/logout', headers={'X-CSRF-Token': token}).status_code == 200


def test_primer_inicio_puede_pedir_el_token(crear_usuario, cliente_de):
    crear_usuario('nuevo@x.mx', primer_login=True)
    cliente = cliente_de('nuevo@x.mx')
    assert cliente.get('/api/csrf-token').status_code == 200


# --- Frontend ------------------------------------------------------------------
@pytest.mark.parametrize('pagina', PAGINAS_CON_CSRF)
def test_paginas_cargan_csrf_js_antes_que_sus_scripts(administrador, pagina):
    texto = administrador.get(pagina).get_data(as_text=True)
    scripts = [linea.strip() for linea in texto.splitlines() if '<script src="js/' in linea]
    assert scripts[0] == '<script src="js/csrf.js"></script>'
    assert len([s for s in scripts if 'csrf.js' in s]) == 1


def test_script_csrf_se_sirve(anon):
    respuesta = anon.get('/js/csrf.js')
    assert respuesta.status_code == 200
    texto = respuesta.get_data(as_text=True)
    assert 'X-CSRF-Token' in texto and '/api/csrf-token' in texto
