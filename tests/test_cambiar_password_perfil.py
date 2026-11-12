"""Cambio de contraseña voluntario desde el menú de perfil."""
import pytest

from conftest import hacer_login, PASSWORD
from Models.models import Auditoria

PAGINAS_CON_SESION = [
    '/index.html', '/horario.html', '/maestros.html', '/buzon.html', '/sugerencias.html',
    '/soporte.html', '/vacantes-publicadas.html', '/cargar-vacantes.html',
    '/postulaciones-recibidas.html', '/panel-admin.html', '/sugerencias-admin.html',
    '/nueva-cuenta.html', '/inscripciones-eventos.html',
]


def cambiar(cliente, **datos):
    cuerpo = {'nueva_password': 'NuevaClave9', 'confirmar_password': 'NuevaClave9'}
    cuerpo.update(datos)
    return cliente.post('/cambiar-password', json=cuerpo)


# --- Servidor -----------------------------------------------------------------
def test_cambio_voluntario_con_contrasena_actual(app, alumno, anon):
    respuesta = cambiar(alumno, password_actual=PASSWORD)
    assert respuesta.status_code == 200
    # La sesión sigue abierta y la contraseña nueva funciona
    assert alumno.get('/api/vacantes').status_code == 200
    assert hacer_login(anon, 'alu@x.mx', 'NuevaClave9').status_code == 200
    with app.app_context():
        assert Auditoria.query.filter_by(accion='Cambio de contraseña voluntario').count() == 1


@pytest.mark.parametrize('datos', [{}, {'password_actual': ''}, {'password_actual': 123}])
def test_cambio_voluntario_exige_contrasena_actual(alumno, anon, datos):
    respuesta = cambiar(alumno, **datos)
    assert respuesta.status_code == 400
    assert respuesta.get_json()['error'] == 'Escribe tu contraseña actual'
    assert hacer_login(anon, 'alu@x.mx').status_code == 200    # no cambió


def test_cambio_voluntario_rechaza_contrasena_actual_incorrecta(alumno, anon):
    respuesta = cambiar(alumno, password_actual='NoEsLaMia1')
    assert respuesta.status_code == 400
    assert respuesta.get_json()['error'] == 'La contraseña actual no es correcta'
    assert hacer_login(anon, 'alu@x.mx').status_code == 200


def test_cambio_voluntario_no_permite_repetir_la_actual(alumno):
    respuesta = cambiar(alumno, password_actual=PASSWORD,
                        nueva_password=PASSWORD, confirmar_password=PASSWORD)
    assert respuesta.status_code == 400


def test_primer_inicio_no_pide_contrasena_actual(app, crear_usuario, cliente_de):
    crear_usuario('nuevo@x.mx', primer_login=True)
    cliente = cliente_de('nuevo@x.mx')
    assert cambiar(cliente).status_code == 200
    with app.app_context():
        assert Auditoria.query.filter_by(
            accion='Cambio de contraseña obligatorio completado').count() == 1


def test_limite_de_intentos_del_cambio(alumno):
    for _ in range(5):
        assert cambiar(alumno, password_actual='Mala12345').status_code == 400
    assert cambiar(alumno, password_actual=PASSWORD).status_code == 429


def test_cambio_sin_sesion(anon):
    assert cambiar(anon, password_actual=PASSWORD).status_code == 401


# --- Páginas --------------------------------------------------------------------
@pytest.mark.parametrize('ruta', ['/cambiar-password', '/cambiar-password.html'])
def test_pagina_sin_sesion_redirige_a_login(anon, ruta):
    respuesta = anon.get(ruta)
    assert respuesta.status_code == 302
    assert respuesta.headers['Location'].endswith('/login')


def test_pagina_trae_campo_de_contrasena_actual(alumno):
    texto = alumno.get('/cambiar-password').get_data(as_text=True)
    assert 'id="grupoActual" class="input-group" hidden' in texto
    assert 'autocomplete="current-password"' in texto
    assert 'id="volverCambio"' in texto


@pytest.mark.parametrize('pagina', PAGINAS_CON_SESION)
def test_menu_de_perfil_ofrece_cambiar_contrasena(administrador, pagina):
    texto = administrador.get(pagina).get_data(as_text=True)
    menu_perfil = texto.split('id="perfilMenu"')[1].split('</header>')[0]
    assert 'href="/cambiar-password"' in menu_perfil
    # «Cambiar contraseña» va antes de «Cerrar sesión»
    assert texto.index('href="/cambiar-password"') < texto.index('id="cerrarSesion"')


def test_icono_del_candado(anon):
    respuesta = anon.get('/img/iconos/candado.svg')
    assert respuesta.status_code == 200
