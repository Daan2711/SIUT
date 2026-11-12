"""Encabezado común: menú por rol, perfil con nombre, rol e iniciales, y cierre de sesión."""
import re

import pytest

from conftest import PASSWORD  # noqa: F401  (fixtures de conftest)

PAGINAS_ALUMNO = ['/index.html', '/horario.html', '/maestros.html', '/buzon.html',
                  '/sugerencias.html', '/soporte.html']
PAGINAS_GESTION = ['/vacantes-publicadas.html', '/cargar-vacantes.html', '/postulaciones-recibidas.html']


def menu(texto):
    return texto.split('<nav id="menuPrincipal"')[1].split('</nav>')[0]


@pytest.mark.parametrize('pagina', PAGINAS_ALUMNO)
def test_paginas_del_alumno_tienen_perfil_y_cerrar_sesion(alumno, pagina):
    texto = alumno.get(pagina).get_data(as_text=True)
    assert '<body data-rol="alumno">' in texto
    assert 'id="cerrarSesion"' in texto           # antes solo existía en Inicio
    assert 'class="perfil-avatar" aria-hidden="true">AP<' in texto   # Alu Prueba
    assert '<span class="perfil-rol">Alumno</span>' in texto
    assert '{{' not in texto
    # Solo una opción activa y es la de la página actual
    activos = re.findall(r'<a href="([^"]+)"[^>]*class="activo" aria-current="page"', menu(texto))
    assert activos == [pagina.lstrip('/')]


def test_profesor_ve_el_mismo_menu_que_el_alumno(crear_usuario, cliente_de):
    crear_usuario('prof@x.mx', rol='Profesor', nombre='Laura', apellido='Ruiz')
    texto = cliente_de('prof@x.mx').get('/index.html').get_data(as_text=True)
    assert '<body data-rol="profesor">' in texto
    assert '<span class="perfil-rol">Profesor</span>' in texto
    assert '>LR<' in texto


@pytest.mark.parametrize('pagina', PAGINAS_GESTION)
def test_empresa_ve_su_rol_y_menu_directo(reclutador, pagina):
    texto = reclutador.get(pagina).get_data(as_text=True)
    assert '<body data-rol="empresa">' in texto
    assert '<span class="perfil-rol">Empresa · TecnoNova</span>' in texto
    assert 'data-solo-empresa>Publicar</a>' in texto


def test_rol_y_nombre_se_escapan(crear_usuario, cliente_de):
    crear_usuario('xss@x.mx', nombre='<b>x</b>', apellido='Y')
    texto = cliente_de('xss@x.mx').get('/index.html').get_data(as_text=True)
    assert '<b>x</b>' not in texto
    assert '&lt;b&gt;x&lt;/b&gt; Y' in texto


def test_css_oculta_opciones_segun_el_rol(alumno):
    css = alumno.get('/css/style.css').get_data(as_text=True)
    assert 'body:not([data-rol="administrador"]) [data-solo-admin]{display:none !important}' in css
    assert 'body[data-rol="administrador"] [data-solo-empresa]{display:none !important}' in css


@pytest.mark.parametrize('icono', ['inicio', 'empleos', 'panel', 'comunidad', 'salir', 'flecha'])
def test_iconos_disponibles(anon, icono):
    respuesta = anon.get(f'/img/iconos/{icono}.svg')
    assert respuesta.status_code == 200


@pytest.mark.parametrize('recurso', ['/js/gestion.js', '/js/index.js'])
def test_scripts_reemplazados_por_nav_js(alumno, recurso):
    assert alumno.get(recurso).status_code == 404
