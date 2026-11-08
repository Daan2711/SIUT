"""Cabeceras, OPTIONS, páginas protegidas, escape de HTML y security.txt."""
import pytest


# --- Cabeceras y OPTIONS (Fase 1) ------------------------------------------
def test_options_responde_405_y_no_500(anon):
    respuesta = anon.options('/login')
    assert respuesta.status_code == 405
    assert respuesta.headers['Allow'] == 'GET, POST, HEAD'


def test_hsts_no_se_envia_por_http(anon):
    assert 'Strict-Transport-Security' not in anon.get('/login').headers


def test_cabeceras_de_seguridad_unificadas(anon):
    headers = anon.get('/login').headers
    assert headers['Referrer-Policy'] == 'strict-origin-when-cross-origin'
    assert headers['X-Frame-Options'] == 'DENY'
    assert headers['X-Content-Type-Options'] == 'nosniff'
    assert "default-src 'self'" in headers['Content-Security-Policy']


# --- Páginas protegidas (Fase 2) -------------------------------------------
@pytest.mark.parametrize('pagina', [
    '/buzon.html', '/cargar-vacantes.html', '/inscripcion.html',
    '/CARGAR-VACANTES.HTML',  # en Windows el sistema de archivos ignora mayúsculas
])
def test_paginas_sin_sesion_redirigen_a_login(anon, pagina):
    respuesta = anon.get(pagina)
    assert respuesta.status_code == 302
    assert respuesta.headers['Location'].endswith('/login')


@pytest.mark.parametrize('ruta', ['/login.html', '/css/style.css', '/login'])
def test_recursos_publicos(anon, ruta):
    assert anon.get(ruta).status_code == 200


@pytest.mark.parametrize('pagina', [
    '/cargar-vacantes.html', '/vacantes-publicadas.html', '/postulaciones-recibidas.html',
])
def test_alumno_no_entra_a_paginas_de_reclutador(alumno, pagina):
    respuesta = alumno.get(pagina)
    assert respuesta.status_code == 302
    assert respuesta.headers['Location'].endswith('/index.html')


@pytest.mark.parametrize('pagina', [
    '/cargar-vacantes.html', '/vacantes-publicadas.html', '/postulaciones-recibidas.html',
])
def test_reclutador_entra_a_sus_paginas_con_nombre_real(reclutador, pagina):
    respuesta = reclutador.get(pagina)
    texto = respuesta.get_data(as_text=True)
    assert respuesta.status_code == 200
    assert 'Rec Prueba' in texto
    assert 'Nombre del Alumno' not in texto


def test_alumno_ve_bolsa_de_empleo_sin_tarjetas_de_ejemplo(alumno):
    respuesta = alumno.get('/buzon.html')
    assert respuesta.status_code == 200
    assert 'data-titulo=' not in respuesta.get_data(as_text=True)


def test_sugerencias_muestra_nombre_real(alumno):
    texto = alumno.get('/sugerencias.html').get_data(as_text=True)
    assert 'Alu Prueba' in texto
    assert 'Nombre del Alumno' not in texto


# --- XSS (Fase 2) ----------------------------------------------------------
def test_nombre_se_escapa_en_el_html(crear_usuario, cliente_de):
    crear_usuario('xss@x.mx', nombre='<img src=x onerror=alert(1)>', apellido='Z')
    texto = cliente_de('xss@x.mx').get('/index.html').get_data(as_text=True)
    assert '<img src=x' not in texto
    assert '&lt;img src=x' in texto


# --- security.txt (Fase 4) -------------------------------------------------
def test_security_txt_estandar(anon):
    respuesta = anon.get('/.well-known/security.txt')
    texto = respuesta.get_data(as_text=True)
    assert respuesta.status_code == 200
    assert respuesta.headers['Content-Type'].startswith('text/plain')
    assert 'Contact: mailto:soporte@virtual.utsc.edu.mx' in texto
    assert 'Expires: 2027-06-15T00:00:00.000Z' in texto


def test_security_txt_legado_redirige(anon):
    respuesta = anon.get('/security.txt')
    assert respuesta.status_code == 301
    assert respuesta.headers['Location'].endswith('/.well-known/security.txt')
