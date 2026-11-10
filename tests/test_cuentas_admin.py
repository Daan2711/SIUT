"""Alta de cuentas desde el panel de administrador («Nueva cuenta»)."""
import logging

import pytest

import servicios.cuentas as servicio_cuentas
from conftest import hacer_login
from Models.models import Usuario, Alumno, Profesor, Empresa, Auditoria

CLAVE = 'Temporal123'
URL = '/api/admin/cuentas'
URL_FORMULARIO = '/api/admin/cuentas/formulario'

ALUMNO = {'rol': 'Alumno', 'email': 'Luis@UTSC.edu.mx', 'nombre': 'Luis', 'apellido': 'Pérez',
          'matricula': 'UTSC-001', 'carrera': 'Redes', 'semestre': '3° cuatrimestre',
          'telefono': '8112345678'}
PROFESOR = {'rol': 'Profesor', 'email': 'eva@utsc.edu.mx', 'nombre': 'Eva',
            'num_empleado': 'E-01', 'departamento': 'Sistemas', 'especialidad': 'Bases de datos'}
EMPRESA = {'rol': 'Empresa', 'email': 'rh@tecnonova.mx', 'nombre': 'Carla', 'empresa': 'TecnoNova'}


def token(cliente):
    respuesta = cliente.get(URL_FORMULARIO)
    assert respuesta.status_code == 200, respuesta.get_json()
    return respuesta.get_json()['csrf_token']


def enviar(cliente, datos, clave=CLAVE, confirmacion=None, csrf='auto'):
    cuerpo = dict(datos, password=clave,
                  password_confirmacion=clave if confirmacion is None else confirmacion)
    cabeceras = {}
    if csrf == 'auto':
        cabeceras['X-CSRF-Token'] = token(cliente)
    elif csrf is not None:
        cabeceras['X-CSRF-Token'] = csrf
    return cliente.post(URL, json=cuerpo, headers=cabeceras)


def total_usuarios(app):
    with app.app_context():
        return Usuario.query.count()


def sin_texto_de_base(respuesta):
    texto = respuesta.get_data(as_text=True).lower()
    return not any(marca in texto for marca in (
        'unique', 'constraint', 'duplicate key', 'integrity', 'psycopg', 'sqlite', 'insert into'))


# --- Alta por rol ------------------------------------------------------------
def test_crea_alumno_con_su_perfil(app, administrador):
    respuesta = enviar(administrador, ALUMNO)
    assert respuesta.status_code == 201, respuesta.get_json()
    with app.app_context():
        usuario = Usuario.query.filter_by(email='luis@utsc.edu.mx').one()   # correo en minúsculas
        admin = Usuario.query.filter_by(email='admin@x.mx').one()
        assert usuario.rol == 'Alumno' and usuario.primer_login is True and usuario.activo
        assert usuario.creado_por == admin.id and usuario.empresa_id is None
        perfil = Alumno.query.filter_by(usuario_id=usuario.id).one()
        assert (perfil.matricula, perfil.semestre, perfil.telefono) == \
            ('UTSC-001', '3° cuatrimestre', '8112345678')
        auditoria = Auditoria.query.filter_by(accion='Alta de usuario (web)').one()
        assert auditoria.usuario_id == admin.id and auditoria.registro_id == usuario.id


def test_crea_profesor_con_su_perfil(app, administrador):
    respuesta = enviar(administrador, PROFESOR)
    assert respuesta.status_code == 201, respuesta.get_json()
    with app.app_context():
        usuario = Usuario.query.filter_by(email='eva@utsc.edu.mx').one()
        assert usuario.rol == 'Profesor' and usuario.primer_login is True
        perfil = Profesor.query.filter_by(usuario_id=usuario.id).one()
        assert (perfil.num_empleado, perfil.departamento) == ('E-01', 'Sistemas')
        assert Alumno.query.count() == 0


def test_crea_empresa_y_la_liga(app, administrador):
    respuesta = enviar(administrador, EMPRESA)
    assert respuesta.status_code == 201, respuesta.get_json()
    with app.app_context():
        usuario = Usuario.query.filter_by(email='rh@tecnonova.mx').one()
        assert usuario.rol == 'Empresa' and usuario.primer_login is True
        assert db_empresa(usuario.empresa_id) == 'TecnoNova'


def db_empresa(empresa_id):
    return Empresa.query.get(empresa_id).nombre


def test_empresa_existente_se_reutiliza(app, administrador, crear_empresa):
    empresa_id = crear_empresa('TecnoNova')
    respuesta = enviar(administrador, dict(EMPRESA, empresa='tecnonova'))
    assert respuesta.status_code == 201
    with app.app_context():
        assert Usuario.query.filter_by(email='rh@tecnonova.mx').one().empresa_id == empresa_id
        assert Empresa.query.count() == 1


def test_campos_de_otros_roles_se_ignoran(app, administrador):
    respuesta = enviar(administrador, dict(PROFESOR, matricula='X-1', empresa='Otra'))
    assert respuesta.status_code == 201
    with app.app_context():
        assert Alumno.query.count() == 0 and Empresa.query.count() == 0


def test_la_cuenta_creada_debe_cambiar_contrasena(app, administrador, anon):
    enviar(administrador, ALUMNO)
    respuesta = hacer_login(anon, 'luis@utsc.edu.mx', CLAVE)
    assert respuesta.status_code == 200
    assert respuesta.get_json()['forzar_cambio'] is True


# --- Registro en logs ----------------------------------------------------------
def test_registra_quien_creo_la_cuenta_sin_la_contrasena(app, administrador, caplog):
    with caplog.at_level(logging.INFO, logger=app.logger.name):
        respuesta = enviar(administrador, ALUMNO)
    assert respuesta.status_code == 201
    with app.app_context():
        admin_id = Usuario.query.filter_by(email='admin@x.mx').one().id
        nuevo_id = Usuario.query.filter_by(email='luis@utsc.edu.mx').one().id
    registros = [r.getMessage() for r in caplog.records if 'Alta de cuenta' in r.getMessage()]
    assert len(registros) == 1
    assert f'administrador #{admin_id}' in registros[0] and f'cuenta #{nuevo_id}' in registros[0]
    assert 'luis@utsc.edu.mx' in registros[0]
    assert all(CLAVE not in r.getMessage() for r in caplog.records)


# --- Duplicados ----------------------------------------------------------------
def test_correo_duplicado_sin_distinguir_mayusculas(app, administrador, crear_usuario):
    crear_usuario('luis@utsc.edu.mx')
    respuesta = enviar(administrador, dict(ALUMNO, email='LUIS@utsc.edu.mx'))
    assert respuesta.status_code == 409
    datos = respuesta.get_json()
    assert datos['campo'] == 'email' and 'Ya existe una cuenta' in datos['mensaje']
    assert sin_texto_de_base(respuesta)


def test_matricula_duplicada(app, administrador, crear_usuario, crear_alumno):
    crear_alumno(crear_usuario('otro@x.mx'), matricula='UTSC-001')
    respuesta = enviar(administrador, ALUMNO)
    assert respuesta.status_code == 409
    assert respuesta.get_json()['campo'] == 'matricula'
    assert 'ya está registrada' in respuesta.get_json()['mensaje']
    assert sin_texto_de_base(respuesta)
    assert total_usuarios(app) == 2   # admin + otro: no quedó una cuenta a medias


def test_numero_de_empleado_duplicado(app, administrador):
    assert enviar(administrador, PROFESOR).status_code == 201
    respuesta = enviar(administrador, dict(PROFESOR, email='otra@utsc.edu.mx'))
    assert respuesta.status_code == 409
    assert respuesta.get_json()['campo'] == 'num_empleado'
    assert 'ya está registrado' in respuesta.get_json()['mensaje']
    assert sin_texto_de_base(respuesta)


def test_una_cuenta_empresa_por_empresa(app, administrador, crear_usuario_empresa):
    crear_usuario_empresa('rh1@tecnonova.mx', 'TecnoNova')
    respuesta = enviar(administrador, EMPRESA)
    assert respuesta.status_code == 409 and respuesta.get_json()['campo'] == 'empresa'


@pytest.mark.parametrize('datos, campo, mensaje', [
    (dict(ALUMNO, email='dup@x.mx'), 'email', 'Ya existe una cuenta con ese correo.'),
    (ALUMNO, 'matricula', 'Esa matrícula ya está registrada.'),
    (PROFESOR, 'num_empleado', 'Ese número de empleado ya está registrado.'),
])
def test_duplicado_que_llega_a_la_base_tambien_es_amigable(
        app, administrador, crear_usuario, crear_alumno, monkeypatch, datos, campo, mensaje):
    """Dos envíos simultáneos: la revisión previa no ve el duplicado y lo
    rechaza la restricción UNIQUE de la base. El mensaje sigue siendo amigable."""
    crear_alumno(crear_usuario('dup@x.mx'), matricula='UTSC-001')
    if campo == 'num_empleado':
        assert enviar(administrador, dict(PROFESOR, email='eva0@utsc.edu.mx')).status_code == 201
    monkeypatch.setattr(servicio_cuentas, '_comprobar_duplicados', lambda rol, datos: None)
    antes = total_usuarios(app)

    respuesta = enviar(administrador, datos)

    assert respuesta.status_code == 409, respuesta.get_json()
    assert respuesta.get_json() == {'ok': False, 'mensaje': mensaje, 'campo': campo}
    assert sin_texto_de_base(respuesta)
    assert total_usuarios(app) == antes


# --- Validaciones --------------------------------------------------------------
@pytest.mark.parametrize('datos, campo', [
    ({'rol': 'Alumno', 'email': 'a@x.mx', 'nombre': 'A'}, 'matricula'),
    ({'rol': 'Profesor', 'email': 'p@x.mx', 'nombre': 'P'}, 'num_empleado'),
    ({'rol': 'Empresa', 'email': 'e@x.mx', 'nombre': 'E'}, 'empresa'),
    (dict(ALUMNO, email='no-es-correo'), 'email'),
    (dict(ALUMNO, nombre='   '), 'nombre'),
    (dict(ALUMNO, nombre='x' * 101), 'nombre'),
    (dict(ALUMNO, semestre='12° cuatrimestre'), 'semestre'),
    (dict(ALUMNO, semestre='1° semestre'), 'semestre'),   # valor anterior al cambio
    (dict(ALUMNO, telefono='abc'), 'telefono'),
])
def test_validaciones_por_rol(app, administrador, datos, campo):
    respuesta = enviar(administrador, datos)
    assert respuesta.status_code == 400
    assert respuesta.get_json()['campo'] == campo
    assert total_usuarios(app) == 1


def test_contrasenas_que_no_coinciden(app, administrador):
    respuesta = enviar(administrador, ALUMNO, confirmacion='Otra12345')
    assert respuesta.status_code == 400
    assert respuesta.get_json()['campo'] == 'password_confirmacion'
    assert total_usuarios(app) == 1


def test_contrasena_corta(app, administrador):
    respuesta = enviar(administrador, ALUMNO, clave='corta')
    assert respuesta.status_code == 400 and '8 caracteres' in respuesta.get_json()['mensaje']


def test_cuerpo_no_json(administrador):
    respuesta = administrador.post(URL, data='rol=Alumno',
                                   headers={'X-CSRF-Token': token(administrador)})
    assert respuesta.status_code == 400


# --- Administradores: nunca desde la web -------------------------------------
@pytest.mark.parametrize('rol', ['Administrador', 'administrador', ' ADMINISTRADOR ',
                                 'Reclutador', '', None, ['Administrador']])
def test_no_se_crean_administradores_ni_roles_desconocidos(app, administrador, rol):
    respuesta = enviar(administrador, {'rol': rol, 'email': 'nuevo@x.mx', 'nombre': 'N'})
    assert respuesta.status_code == 400
    assert respuesta.get_json()['campo'] == 'rol'
    with app.app_context():
        assert Usuario.query.filter_by(email='nuevo@x.mx').count() == 0
        assert Usuario.query.filter_by(rol='Administrador').count() == 1


def test_el_formulario_no_ofrece_administrador(administrador):
    assert administrador.get(URL_FORMULARIO).get_json()['roles'] == ['Alumno', 'Profesor', 'Empresa']
    pagina = administrador.get('/nueva-cuenta.html').get_data(as_text=True)
    assert '<option>Administrador</option>' not in pagina
    assert 'value="Administrador"' not in pagina


def test_el_formulario_ofrece_cuatrimestres_en_orden(administrador):
    assert administrador.get(URL_FORMULARIO).get_json()['semestres'] == [f'{n}° cuatrimestre' for n in range(1, 12)] + ['Egresado(a)']
    pagina = administrador.get('/nueva-cuenta.html').get_data(as_text=True)
    assert 'Cuatrimestre' in pagina and 'Semestre' not in pagina


# --- Acceso --------------------------------------------------------------------
def test_sin_sesion(app, anon):
    assert anon.get(URL_FORMULARIO).status_code == 401
    assert anon.post(URL, json=dict(ALUMNO, password=CLAVE, password_confirmacion=CLAVE)
                     ).status_code == 401
    assert anon.get('/nueva-cuenta.html').status_code == 302
    assert total_usuarios(app) == 0


@pytest.mark.parametrize('perfil', ['alumno', 'reclutador'])
def test_no_administrador_no_puede_ver_ni_enviar(app, request, perfil):
    cliente = request.getfixturevalue(perfil)
    antes = total_usuarios(app)
    assert cliente.get(URL_FORMULARIO).status_code == 403
    # Incluso con un token CSRF válido de su propia sesión
    with cliente.session_transaction() as sesion:
        sesion['_csrf_token'] = 'token-propio'
    respuesta = cliente.post(URL, json=dict(ALUMNO, password=CLAVE, password_confirmacion=CLAVE),
                             headers={'X-CSRF-Token': 'token-propio'})
    assert respuesta.status_code == 403
    pagina = cliente.get('/nueva-cuenta.html')
    assert pagina.status_code == 302 and pagina.headers['Location'].endswith('/index.html')
    assert total_usuarios(app) == antes


def test_administrador_desactivado_pierde_el_acceso(app, administrador):
    csrf = token(administrador)
    with app.app_context():
        from Database.database import db
        Usuario.query.filter_by(email='admin@x.mx').one().activo = False
        db.session.commit()
    respuesta = enviar(administrador, ALUMNO, csrf=csrf)
    assert respuesta.status_code == 401
    assert total_usuarios(app) == 1


def test_administrador_ve_la_pagina(administrador):
    assert administrador.get('/nueva-cuenta.html').status_code == 200


# --- CSRF ----------------------------------------------------------------------
@pytest.mark.parametrize('csrf', [None, '', 'token-falso'])
def test_sin_csrf_valido_se_rechaza(app, administrador, csrf):
    token(administrador)   # la sesión ya tiene token, pero la petición no lo trae bien
    respuesta = enviar(administrador, ALUMNO, csrf=csrf)
    assert respuesta.status_code == 403
    assert total_usuarios(app) == 1


def test_sin_token_en_la_sesion_se_rechaza(app, administrador):
    respuesta = enviar(administrador, ALUMNO, csrf='cualquiera')
    assert respuesta.status_code == 403
    assert total_usuarios(app) == 1


def test_token_de_otra_sesion_no_sirve(app, administrador, crear_usuario, cliente_de):
    crear_usuario('admin2@x.mx', rol='Administrador')
    otro = cliente_de('admin2@x.mx')
    propio = token(administrador)   # la sesión tiene su propio token...
    ajeno = token(otro)
    assert propio != ajeno
    respuesta = enviar(administrador, ALUMNO, csrf=ajeno)   # ...pero envía el de otra sesión
    assert respuesta.status_code == 403
    assert enviar(administrador, ALUMNO, csrf=propio).status_code == 201


def test_el_token_se_reutiliza_en_la_misma_sesion(administrador):
    assert token(administrador) == token(administrador)


def test_peticion_simultanea_no_borra_el_token(app, administrador):
    """Regresión: al abrir la página, /usuario-actual y /formulario van a la vez.
    Si la respuesta de /usuario-actual llegaba después, reescribía la cookie de
    sesión SIN el token y el primer envío fallaba con 403. El token se crea al
    iniciar sesión, así que la cookie previa ya lo trae."""
    cookie_previa = administrador.get_cookie('session').value   # la que usa /usuario-actual
    csrf = token(administrador)                                 # /formulario responde primero
    administrador.set_cookie('session', cookie_previa)          # /usuario-actual responde después
    respuesta = enviar(administrador, ALUMNO, csrf=csrf)
    assert respuesta.status_code == 201, respuesta.get_json()


def test_el_login_renueva_el_token(app, crear_usuario, cliente_de):
    """Cada inicio de sesión recibe un token nuevo (no se arrastra el de otra sesión)."""
    crear_usuario('admin@x.mx', rol='Administrador')
    cliente = cliente_de('admin@x.mx')
    primero = token(cliente)
    hacer_login(cliente, 'admin@x.mx')
    assert token(cliente) != primero
