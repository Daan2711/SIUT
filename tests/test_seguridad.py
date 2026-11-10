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
    '/buzon.html', '/cargar-vacantes.html', '/sugerencias.html',
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


# --- Fase C: caché, menú en celular y limpieza ------------------------------
@pytest.mark.parametrize('recurso', ['/img/logo.png', '/img/3.jpg'])
def test_imagenes_se_guardan_en_cache_una_hora(anon, recurso):
    respuesta = anon.get(recurso)
    assert respuesta.status_code == 200
    assert respuesta.headers['Cache-Control'] == 'public, max-age=3600'


@pytest.mark.parametrize('recurso', ['/css/style.css', '/js/nav.js', '/js/login.js'])
def test_js_y_css_se_revalidan_en_cada_carga(anon, recurso):
    """Tras un despliegue el navegador debe recibir el JS/CSS nuevo al momento
    (con max-age=3600 un login.js corregido tardó hasta 1 hora en llegar)."""
    respuesta = anon.get(recurso)
    assert respuesta.status_code == 200
    assert respuesta.headers['Cache-Control'] == 'no-cache'
    # Sin validadores la revalidación descargaría el archivo completo
    assert respuesta.headers.get('ETag') or respuesta.headers.get('Last-Modified')


@pytest.mark.parametrize('recurso, politica', [
    ('/js/login.js', 'no-cache'),
    ('/css/style.css', 'no-cache'),
    ('/img/logo.png', 'public, max-age=3600'),
])
def test_respuesta_304_conserva_la_politica_del_recurso(anon, recurso, politica):
    etag = anon.get(recurso).headers['ETag']
    respuesta = anon.get(recurso, headers={'If-None-Match': etag})
    assert respuesta.status_code == 304
    assert respuesta.headers['Cache-Control'] == politica
    assert 'Pragma' not in respuesta.headers


def test_html_y_api_nunca_se_guardan_en_cache(alumno):
    for ruta in ('/login', '/index.html', '/api/vacantes', '/usuario-actual'):
        assert 'no-store' in alumno.get(ruta).headers['Cache-Control'], ruta


PAGINAS_CON_MENU = ['/index.html', '/horario.html', '/maestros.html', '/soporte.html',
                    '/buzon.html', '/sugerencias.html']


@pytest.mark.parametrize('pagina', PAGINAS_CON_MENU)
def test_paginas_con_menu_tienen_boton_para_celular(alumno, pagina):
    texto = alumno.get(pagina).get_data(as_text=True)
    assert 'id="menuToggle"' in texto and 'aria-controls="menuPrincipal"' in texto
    assert '<nav id="menuPrincipal"' in texto
    assert 'js/nav.js' in texto


@pytest.mark.parametrize('pagina', ['/contacto.html', '/js/usuario.js'])
def test_archivos_eliminados_ya_no_existen(alumno, pagina):
    assert alumno.get(pagina).status_code == 404


# --- Inscripción a eventos (restaurada desde la rama master) ----------------
def test_eventos_del_inicio_llevan_a_la_inscripcion(alumno):
    texto = alumno.get('/index.html').get_data(as_text=True)
    assert texto.count('href="inscripcion.html" target="_blank" rel="noopener"') == 3
    assert 'href="#"' not in texto


@pytest.mark.parametrize('pagina', ['/inscripcion.html', '/confirmacion_inscripciones.html'])
def test_paginas_de_inscripcion_exigen_sesion(anon, alumno, pagina):
    assert anon.get(pagina).headers['Location'].endswith('/login')
    assert alumno.get(pagina).status_code == 200


def test_inscripcion_no_envia_datos_personales_en_la_url(alumno):
    """El formulario es estático y usa GET: sin 'name', nombre y correo no viajan en la URL."""
    texto = alumno.get('/inscripcion.html').get_data(as_text=True)
    formulario = texto[texto.index('<form'):texto.index('</form>')]
    assert 'action="confirmacion.html"' in formulario
    assert 'name="' not in formulario
    assert formulario.count('required') == 2
    assert alumno.get('/confirmacion.html').status_code == 200


# --- Botón para mostrar la contraseña ------------------------------------------
@pytest.mark.parametrize('cliente, pagina, campos', [
    ('anon', '/login', 1),
    ('alumno', '/cambiar-password', 2),
    ('administrador', '/nueva-cuenta.html', 2),
])
def test_paginas_con_contrasena_cargan_el_ojito(request, cliente, pagina, campos):
    html = request.getfixturevalue(cliente).get(pagina).get_data(as_text=True)
    assert html.count('type="password"') == campos
    assert '<script src="js/mostrar-password.js"></script>' in html


def test_script_del_ojito_se_sirve(anon):
    respuesta = anon.get('/js/mostrar-password.js')
    assert respuesta.status_code == 200
    assert 'aria-pressed' in respuesta.get_data(as_text=True)
