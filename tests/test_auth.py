"""Login, cambio de contraseña obligatorio, límite de intentos y sesión."""
from conftest import hacer_login, PASSWORD


# --- Login -------------------------------------------------------------------
def test_login_correcto(crear_usuario, anon):
    crear_usuario('alu@x.mx')
    respuesta = hacer_login(anon, 'alu@x.mx')
    assert respuesta.status_code == 200
    assert respuesta.get_json()['forzar_cambio'] is False


def test_login_contrasena_incorrecta(crear_usuario, anon):
    crear_usuario('alu@x.mx')
    assert hacer_login(anon, 'alu@x.mx', 'mala').status_code == 401


def test_login_cuenta_inactiva(crear_usuario, anon):
    crear_usuario('baja@x.mx', activo=False)
    assert hacer_login(anon, 'baja@x.mx').status_code == 401


def test_registro_publico_deshabilitado(anon):
    assert anon.post('/registro', json={}).status_code == 403


# --- Cambio de contraseña obligatorio (Fase 1) -----------------------------
def test_primer_login_bloquea_api_y_paginas(crear_usuario, cliente_de):
    crear_usuario('nuevo@x.mx', primer_login=True)
    cliente = cliente_de('nuevo@x.mx')

    assert cliente.get('/api/vacantes').status_code == 403
    respuesta = cliente.get('/index.html')
    assert respuesta.status_code == 302
    assert respuesta.headers['Location'].endswith('/cambiar-password')


def test_primer_login_permite_recursos_y_cambio(crear_usuario, cliente_de):
    crear_usuario('nuevo@x.mx', primer_login=True)
    cliente = cliente_de('nuevo@x.mx')

    assert cliente.get('/css/style.css').status_code == 200
    assert cliente.get('/cambiar-password').status_code == 200
    assert cliente.get('/usuario-actual').status_code == 200


def test_login_indica_forzar_cambio(crear_usuario, anon):
    crear_usuario('nuevo@x.mx', primer_login=True)
    assert hacer_login(anon, 'nuevo@x.mx').get_json()['forzar_cambio'] is True


def test_no_permite_reutilizar_contrasena_actual(crear_usuario, cliente_de):
    crear_usuario('nuevo@x.mx', primer_login=True)
    cliente = cliente_de('nuevo@x.mx')
    respuesta = cliente.post('/cambiar-password', json={
        'nueva_password': PASSWORD, 'confirmar_password': PASSWORD})
    assert respuesta.status_code == 400


def test_no_permite_contrasena_temporal_configurada(crear_usuario, cliente_de, monkeypatch):
    monkeypatch.setenv('TEMP_PASSWORD', 'Temporal2026')
    crear_usuario('nuevo@x.mx', primer_login=True)
    cliente = cliente_de('nuevo@x.mx')
    respuesta = cliente.post('/cambiar-password', json={
        'nueva_password': 'Temporal2026', 'confirmar_password': 'Temporal2026'})
    assert respuesta.status_code == 400


def test_cambio_de_contrasena_libera_el_acceso(crear_usuario, cliente_de, anon):
    crear_usuario('nuevo@x.mx', primer_login=True)
    cliente = cliente_de('nuevo@x.mx')
    respuesta = cliente.post('/cambiar-password', json={
        'nueva_password': 'NuevaClave9', 'confirmar_password': 'NuevaClave9'})

    assert respuesta.status_code == 200
    assert cliente.get('/api/vacantes').status_code == 200
    assert hacer_login(anon, 'nuevo@x.mx', 'NuevaClave9').get_json()['forzar_cambio'] is False


def test_cambio_de_contrasena_valida_longitud_y_coincidencia(crear_usuario, cliente_de):
    crear_usuario('nuevo@x.mx', primer_login=True)
    cliente = cliente_de('nuevo@x.mx')
    corta = cliente.post('/cambiar-password', json={'nueva_password': 'abc', 'confirmar_password': 'abc'})
    distinta = cliente.post('/cambiar-password', json={'nueva_password': 'NuevaClave9', 'confirmar_password': 'Otra12345'})
    assert corta.status_code == 400
    assert distinta.status_code == 400


# --- Límite de intentos (Fase 1) -------------------------------------------
def test_sexto_intento_devuelve_429_en_json(crear_usuario, app):
    crear_usuario('alu@x.mx')
    cliente = app.test_client()
    codigos = [hacer_login(cliente, 'alu@x.mx', 'mala').status_code for _ in range(6)]

    assert codigos == [401] * 5 + [429]
    respuesta = hacer_login(cliente, 'alu@x.mx', 'mala')
    assert respuesta.is_json and 'error' in respuesta.get_json()


def test_limite_no_bloquea_otro_correo_desde_la_misma_ip(crear_usuario, app):
    crear_usuario('alu@x.mx')
    crear_usuario('otro@x.mx')
    cliente = app.test_client()
    for _ in range(6):
        hacer_login(cliente, 'alu@x.mx', 'mala')
    assert hacer_login(cliente, 'otro@x.mx').status_code == 200


# --- Sesión (Fase 2) ---------------------------------------------------------
def test_cookie_de_sesion_con_expiracion(crear_usuario, anon):
    crear_usuario('alu@x.mx')
    cookie = hacer_login(anon, 'alu@x.mx').headers.get('Set-Cookie', '')
    assert 'Expires=' in cookie
    assert 'HttpOnly' in cookie


def test_logout_cierra_la_sesion(crear_usuario, cliente_de):
    crear_usuario('alu@x.mx')
    cliente = cliente_de('alu@x.mx')
    assert cliente.post('/logout').status_code == 200
    assert cliente.get('/usuario-actual').status_code == 401


def test_usuario_actual_incluye_alumno_y_permiso(alumno, reclutador):
    datos_alumno = alumno.get('/usuario-actual').get_json()
    datos_reclutador = reclutador.get('/usuario-actual').get_json()

    assert datos_alumno['alumno']['matricula'] == 'A123'
    assert datos_alumno['puede_cargar_vacantes'] is False
    assert datos_reclutador['alumno'] is None
    assert datos_reclutador['puede_cargar_vacantes'] is True
