"""Recuperación de contraseña con código de 4 dígitos por correo (sin enviar correos reales)."""
import json
import urllib.error
from datetime import datetime, timedelta, timezone

import pytest

import Controllers.recuperacionController as recuperacion
import servicios.correo as correo
from conftest import hacer_login, PASSWORD
from Database.database import db
from Models.models import Auditoria, RecuperacionPassword, Usuario

SOLICITAR = '/recuperar-password/solicitar'
VERIFICAR = '/recuperar-password/verificar'
RESTABLECER = '/recuperar-password/restablecer'
NUEVA = 'NuevaClave9'


@pytest.fixture
def enviados(monkeypatch):
    """Brevo configurado; los correos se guardan en una lista en vez de enviarse."""
    monkeypatch.setenv('BREVO_API_KEY', 'clave-de-prueba')
    monkeypatch.setenv('CORREO_REMITENTE', 'siut@x.mx')
    lista = []

    def despachar(destinatario, nombre, codigo, usuario_id, logger):
        lista.append({'para': destinatario, 'nombre': nombre, 'codigo': codigo})

    monkeypatch.setattr(recuperacion, '_despachar', despachar)
    return lista


@pytest.fixture
def usuario(crear_usuario):
    return crear_usuario('alu@x.mx', nombre='Alu')


def solicitar(cliente, email='alu@x.mx'):
    return cliente.post(SOLICITAR, json={'email': email})


def verificar(cliente, codigo, email='alu@x.mx'):
    return cliente.post(VERIFICAR, json={'email': email, 'codigo': codigo})


def restablecer(cliente, nueva=NUEVA, confirmar=None):
    return cliente.post(RESTABLECER, json={'nueva_password': nueva,
                                           'confirmar_password': confirmar or nueva})


def codigo_incorrecto(codigo):
    return f'{(int(codigo) + 1) % 10000:04d}'


# --- Flujo completo -----------------------------------------------------------
def test_flujo_completo(app, anon, usuario, enviados):
    respuesta = solicitar(anon, 'ALU@x.mx ')
    assert respuesta.status_code == 200
    assert 'Si el correo está registrado' in respuesta.get_json()['mensaje']
    assert len(enviados) == 1
    assert enviados[0]['para'] == 'alu@x.mx' and enviados[0]['nombre'] == 'Alu'
    codigo = enviados[0]['codigo']
    assert len(codigo) == 4 and codigo.isdigit()

    assert verificar(anon, codigo).status_code == 200
    respuesta = restablecer(anon)
    assert respuesta.status_code == 200, respuesta.get_json()

    assert hacer_login(app.test_client(), 'alu@x.mx', NUEVA).status_code == 200
    assert hacer_login(app.test_client(), 'alu@x.mx', PASSWORD).status_code == 401
    with app.app_context():
        acciones = [a.accion for a in Auditoria.query.filter_by(usuario_id=usuario)]
        assert 'Código de recuperación solicitado' in acciones
        assert 'Contraseña restablecida con código por correo' in acciones
        assert RecuperacionPassword.query.one().usado_en is not None
    # El código ya se usó: no sirve otra vez
    assert restablecer(anon, 'OtraClave99').status_code == 400
    assert verificar(anon, codigo).status_code == 400


def test_el_codigo_se_guarda_cifrado(app, anon, usuario, enviados):
    solicitar(anon)
    with app.app_context():
        guardado = RecuperacionPassword.query.one()
        assert enviados[0]['codigo'] not in guardado.codigo_hash
        assert guardado.codigo_hash.startswith('$2')


def test_resuelve_el_cambio_pendiente_de_la_temporal(app, anon, crear_usuario, enviados):
    usuario_id = crear_usuario('nuevo@x.mx', primer_login=True)
    solicitar(anon, 'nuevo@x.mx')
    verificar(anon, enviados[0]['codigo'], 'nuevo@x.mx')
    assert restablecer(anon).status_code == 200
    with app.app_context():
        assert db.session.get(Usuario, usuario_id).primer_login is False
    assert hacer_login(app.test_client(), 'nuevo@x.mx', NUEVA).get_json()['forzar_cambio'] is False


# --- No revela si el correo existe -------------------------------------------
@pytest.mark.parametrize('email', ['nadie@x.mx', 'baja@x.mx'])
def test_misma_respuesta_si_el_correo_no_existe_o_esta_desactivado(
        anon, usuario, crear_usuario, enviados, email):
    crear_usuario('baja@x.mx', activo=False)
    existente = solicitar(anon)
    otro = solicitar(anon, email)
    assert otro.status_code == existente.status_code == 200
    assert otro.get_json() == existente.get_json()
    assert [e['para'] for e in enviados] == ['alu@x.mx']   # solo el activo recibe código


@pytest.mark.parametrize('email', ['', 'sin-arroba', 123, None])
def test_correo_invalido(anon, enviados, email):
    assert anon.post(SOLICITAR, json={'email': email}).status_code == 400
    assert not enviados


def test_sin_brevo_configurado_avisa(anon, usuario, monkeypatch):
    monkeypatch.delenv('BREVO_API_KEY', raising=False)
    monkeypatch.delenv('CORREO_REMITENTE', raising=False)
    respuesta = solicitar(anon)
    assert respuesta.status_code == 503
    assert 'no está disponible' in respuesta.get_json()['error']


# --- Código: errores, intentos, vencimiento ----------------------------------
def test_codigo_incorrecto_cuenta_intentos_y_se_anula_al_quinto(app, anon, usuario, enviados):
    solicitar(anon)
    codigo = enviados[0]['codigo']
    malo = codigo_incorrecto(codigo)
    for restantes in (4, 3, 2, 1):
        respuesta = verificar(anon, malo)
        assert respuesta.status_code == 400
        assert f'Te quedan {restantes}' in respuesta.get_json()['error']
    respuesta = verificar(anon, malo)
    assert respuesta.get_json()['agotado'] is True
    # Ni el código correcto sirve ya
    assert verificar(anon, codigo).get_json()['error'] == recuperacion.MENSAJE_CODIGO_INVALIDO
    with app.app_context():
        assert RecuperacionPassword.query.one().intentos == 5


def test_codigo_vencido(app, anon, usuario, enviados):
    solicitar(anon)
    with app.app_context():
        guardado = RecuperacionPassword.query.one()
        guardado.vence_en = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.session.commit()
    respuesta = verificar(anon, enviados[0]['codigo'])
    assert respuesta.status_code == 400
    assert respuesta.get_json()['error'] == recuperacion.MENSAJE_CODIGO_INVALIDO


def test_un_codigo_nuevo_anula_el_anterior(anon, usuario, enviados):
    solicitar(anon)
    solicitar(anon)
    primero, segundo = enviados[0]['codigo'], enviados[1]['codigo']
    if primero != segundo:   # 1 en 10 000 de que coincidan
        assert verificar(anon, primero).status_code == 400
    assert verificar(anon, segundo).status_code == 200


@pytest.mark.parametrize('codigo', ['123', '12345', 'abcd', 1234, None])
def test_formato_del_codigo(anon, usuario, enviados, codigo):
    solicitar(anon)
    assert anon.post(VERIFICAR, json={'email': 'alu@x.mx', 'codigo': codigo}).status_code == 400


def test_codigo_de_otro_correo_no_sirve(anon, usuario, crear_usuario, enviados):
    crear_usuario('otro@x.mx')
    solicitar(anon)
    assert verificar(anon, enviados[0]['codigo'], 'otro@x.mx').status_code == 400


# --- Restablecer ---------------------------------------------------------------
def test_restablecer_sin_verificar_el_codigo(anon, usuario, enviados):
    solicitar(anon)
    respuesta = restablecer(anon)
    assert respuesta.status_code == 400
    assert respuesta.get_json()['error'] == recuperacion.MENSAJE_SESION_VENCIDA
    assert hacer_login(anon, 'alu@x.mx').status_code == 200


def test_restablecer_desde_otro_navegador_no_sirve(app, anon, usuario, enviados):
    solicitar(anon)
    verificar(anon, enviados[0]['codigo'])
    assert restablecer(app.test_client()).status_code == 400


@pytest.mark.parametrize('nueva, confirmar, error', [
    ('Corta1', 'Corta1', 'al menos 8'),
    (NUEVA, 'Distinta99', 'no coinciden'),
    ('', '', 'ambos campos'),
    (PASSWORD, PASSWORD, 'distinta a la actual'),
])
def test_validaciones_de_la_nueva_contrasena(anon, usuario, enviados, nueva, confirmar, error):
    solicitar(anon)
    verificar(anon, enviados[0]['codigo'])
    respuesta = anon.post(RESTABLECER, json={'nueva_password': nueva, 'confirmar_password': confirmar})
    assert respuesta.status_code == 400
    assert error in respuesta.get_json()['error']
    # La verificación sigue valiendo para corregir y reintentar
    assert restablecer(anon).status_code == 200


def test_pedir_otro_codigo_invalida_la_verificacion(anon, usuario, enviados):
    solicitar(anon)
    verificar(anon, enviados[0]['codigo'])
    solicitar(anon)
    assert restablecer(anon).status_code == 400


def test_cuenta_desactivada_despues_de_verificar(app, anon, usuario, enviados):
    solicitar(anon)
    verificar(anon, enviados[0]['codigo'])
    with app.app_context():
        db.session.get(Usuario, usuario).activo = False
        db.session.commit()
    assert restablecer(anon).status_code == 400


# --- Límites --------------------------------------------------------------------
def test_limite_de_codigos_por_correo(anon, usuario, enviados):
    for _ in range(3):
        assert solicitar(anon).status_code == 200
    respuesta = solicitar(anon)
    assert respuesta.status_code == 429
    assert '15 minutos' in respuesta.get_json()['error']
    assert len(enviados) == 3


def test_limite_en_la_base_de_datos_aunque_el_limiter_se_reinicie(anon, usuario, enviados):
    """Con 2 workers el limiter en memoria cuenta por separado: la BD es el respaldo."""
    from extensions import limiter
    for _ in range(3):
        solicitar(anon)
    limiter.reset()
    assert solicitar(anon).status_code == 200     # misma respuesta genérica...
    assert len(enviados) == 3                     # ...pero no se envía otro código


def test_limite_de_verificaciones_por_red(anon, usuario, enviados):
    solicitar(anon)
    codigos = [verificar(anon, '0000', 'nadie@x.mx').status_code for _ in range(11)]
    assert codigos[-1] == 429


# --- Sesiones abiertas y CSRF ------------------------------------------------
def test_funciona_con_una_sesion_abierta_sin_token_csrf(alumno, enviados):
    """La página de login no tiene token CSRF: las rutas están exentas."""
    alumno.csrf_auto = False
    assert solicitar(alumno).status_code == 200
    assert verificar(alumno, enviados[0]['codigo']).status_code == 200
    assert restablecer(alumno).status_code == 200


# --- Servicio de correo (Brevo) --------------------------------------------------
class RespuestaFalsa:
    status = 201

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_enviar_correo_usa_la_api_de_brevo(monkeypatch):
    monkeypatch.setenv('BREVO_API_KEY', 'clave-de-prueba')
    monkeypatch.setenv('CORREO_REMITENTE', 'siut@x.mx')
    monkeypatch.delenv('NOMBRE_REMITENTE', raising=False)
    peticiones = []

    def urlopen(peticion, timeout):
        peticiones.append((peticion, timeout))
        return RespuestaFalsa()

    monkeypatch.setattr(correo.urllib.request, 'urlopen', urlopen)
    correo.enviar_correo('alu@x.mx', 'Asunto', 'Texto', '<p>Texto</p>')
    peticion, timeout = peticiones[0]
    assert peticion.full_url == 'https://api.brevo.com/v3/smtp/email'
    assert peticion.get_method() == 'POST'
    assert peticion.get_header('Api-key') == 'clave-de-prueba'
    cuerpo = json.loads(peticion.data)
    assert cuerpo['sender'] == {'name': 'SIUT', 'email': 'siut@x.mx'}
    assert cuerpo['to'] == [{'email': 'alu@x.mx'}]
    assert cuerpo['textContent'] == 'Texto' and cuerpo['htmlContent'] == '<p>Texto</p>'
    assert timeout == correo.TIEMPO_ESPERA


def test_enviar_correo_error_de_brevo(monkeypatch):
    monkeypatch.setenv('BREVO_API_KEY', 'clave-de-prueba')
    monkeypatch.setenv('CORREO_REMITENTE', 'siut@x.mx')

    def urlopen(peticion, timeout):
        raise urllib.error.HTTPError(peticion.full_url, 400, 'Bad Request', {}, None)

    monkeypatch.setattr(correo.urllib.request, 'urlopen', urlopen)
    with pytest.raises(correo.CorreoNoEnviado) as error:
        correo.enviar_correo('alu@x.mx', 'Asunto', 'Texto')
    assert 'clave-de-prueba' not in str(error.value)


def test_fallo_al_enviar_queda_en_el_log_sin_el_codigo(monkeypatch, caplog):
    import logging

    def falla(*args, **kwargs):
        raise correo.CorreoNoEnviado('Brevo respondió 401')

    monkeypatch.setattr(recuperacion, 'enviar_correo', falla)
    logger = logging.getLogger('prueba-recuperacion')
    with caplog.at_level(logging.INFO, logger='prueba-recuperacion'):
        recuperacion._enviar('alu@x.mx', 'Alu', '4821', 7, logger)
    assert 'usuario 7' in caplog.text and '401' in caplog.text
    assert '4821' not in caplog.text and 'alu@x.mx' not in caplog.text


def test_el_correo_trae_el_codigo_y_escapa_el_nombre():
    texto, html = recuperacion._texto_del_correo('<b>Alu</b>', '0042')
    assert '0042' in texto and '0042' in html
    assert '<b>Alu</b>' not in html and '&lt;b&gt;' in html


# --- Página de login -------------------------------------------------------------
def test_login_tiene_la_ventana_de_recuperacion(anon):
    html = anon.get('/login').get_data(as_text=True)
    assert 'id="enlaceRecuperar"' in html and 'id="dialogoRecuperar"' in html
    assert '¿Estás seguro de querer recuperar la contraseña?' in html
    assert 'Recuperar contraseña</button>' in html and 'En otro momento</button>' in html
    assert html.index('src="js/recuperar.js"') > html.index('src="js/mostrar-password.js"')
    assert anon.get('/js/recuperar.js').status_code == 200


# --- Variables de Brevo pegadas con espacios o saltos de línea (Render) ---------
def capturar_peticiones(monkeypatch):
    peticiones = []

    def urlopen(peticion, timeout):
        peticiones.append(peticion)
        return RespuestaFalsa()

    monkeypatch.setattr(correo.urllib.request, 'urlopen', urlopen)
    return peticiones


def test_variables_con_espacios_y_saltos_de_linea_se_limpian(monkeypatch):
    monkeypatch.setenv('BREVO_API_KEY', '  xkeysib-clave-de-prueba\n')
    monkeypatch.setenv('CORREO_REMITENTE', ' siut@x.mx\r\n')
    monkeypatch.setenv('NOMBRE_REMITENTE', ' SIUT UTSC \n')
    peticiones = capturar_peticiones(monkeypatch)
    correo.enviar_correo('alu@x.mx', 'Asunto', 'Texto')
    assert peticiones[0].get_header('Api-key') == 'xkeysib-clave-de-prueba'
    assert json.loads(peticiones[0].data)['sender'] == {'name': 'SIUT UTSC', 'email': 'siut@x.mx'}


@pytest.mark.parametrize('clave', ['xkeysib-mitad\nmitad', 'xkeysib-con espacio',
                                   'xkeysib-invisible​', 'xkeysib-acentó'])
def test_clave_con_caracteres_no_validos_da_un_error_claro(monkeypatch, clave):
    monkeypatch.setenv('BREVO_API_KEY', clave)
    monkeypatch.setenv('CORREO_REMITENTE', 'siut@x.mx')
    peticiones = capturar_peticiones(monkeypatch)
    with pytest.raises(correo.CorreoNoEnviado) as error:
        correo.enviar_correo('alu@x.mx', 'Asunto', 'Texto')
    assert 'caracteres no válidos' in str(error.value)
    assert 'xkeysib' not in str(error.value)
    assert not peticiones                       # ni siquiera se intenta llamar a Brevo


def test_solo_espacios_cuenta_como_no_configurado(anon, usuario, monkeypatch):
    monkeypatch.setenv('BREVO_API_KEY', '  \n')
    monkeypatch.setenv('CORREO_REMITENTE', 'siut@x.mx')
    assert solicitar(anon).status_code == 503


def test_error_inesperado_de_la_llamada_se_convierte_en_correo_no_enviado(monkeypatch):
    monkeypatch.setenv('BREVO_API_KEY', 'xkeysib-clave-de-prueba')
    monkeypatch.setenv('CORREO_REMITENTE', 'siut@x.mx')

    def urlopen(peticion, timeout):
        raise ValueError('Invalid header value xkeysib-clave-de-prueba')

    monkeypatch.setattr(correo.urllib.request, 'urlopen', urlopen)
    with pytest.raises(correo.CorreoNoEnviado) as error:
        correo.enviar_correo('alu@x.mx', 'Asunto', 'Texto')
    assert 'ValueError' in str(error.value)
    assert 'xkeysib' not in str(error.value)


def test_respuesta_no_2xx_conserva_su_mensaje(monkeypatch):
    monkeypatch.setenv('BREVO_API_KEY', 'xkeysib-clave-de-prueba')
    monkeypatch.setenv('CORREO_REMITENTE', 'siut@x.mx')

    class Respuesta302(RespuestaFalsa):
        status = 302

    monkeypatch.setattr(correo.urllib.request, 'urlopen', lambda peticion, timeout: Respuesta302())
    with pytest.raises(correo.CorreoNoEnviado, match='Brevo respondió 302'):
        correo.enviar_correo('alu@x.mx', 'Asunto', 'Texto')


def test_error_inesperado_en_segundo_plano_queda_en_el_log_sin_datos(monkeypatch, caplog):
    import logging

    def falla(*args, **kwargs):
        raise RuntimeError('fallo con 4821 y alu@x.mx')

    monkeypatch.setattr(recuperacion, 'enviar_correo', falla)
    logger = logging.getLogger('prueba-recuperacion')
    with caplog.at_level(logging.INFO, logger='prueba-recuperacion'):
        recuperacion._enviar('alu@x.mx', 'Alu', '4821', 7, logger)
    assert 'No se pudo enviar el código de recuperación (usuario 7)' in caplog.text
    assert 'RuntimeError' in caplog.text
    assert '4821' not in caplog.text and 'alu@x.mx' not in caplog.text
