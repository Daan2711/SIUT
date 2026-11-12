"""Ícono del sitio (favicon) disponible y enlazado en todas las páginas."""
import glob
import os

import pytest

FRONTEND = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'Frontend')
PAGINAS = sorted(os.path.basename(p) for p in glob.glob(os.path.join(FRONTEND, '*.html')))


@pytest.mark.parametrize('ruta, tipo', [
    ('/favicon.ico', b'\x00\x00\x01\x00'),          # cabecera ICO
    ('/img/favicon-32.png', b'\x89PNG'),
    ('/img/apple-touch-icon.png', b'\x89PNG'),
])
def test_iconos_se_sirven_sin_sesion(anon, ruta, tipo):
    respuesta = anon.get(ruta)
    assert respuesta.status_code == 200
    assert respuesta.data.startswith(tipo)


def test_favicon_durante_primer_inicio(crear_usuario, cliente_de):
    crear_usuario('nuevo@x.mx', primer_login=True)
    assert cliente_de('nuevo@x.mx').get('/favicon.ico').status_code == 200


def test_todas_las_paginas_estan_cubiertas():
    assert len(PAGINAS) == 18


@pytest.mark.parametrize('pagina', PAGINAS)
def test_pagina_enlaza_los_iconos(pagina):
    with open(os.path.join(FRONTEND, pagina), encoding='utf-8') as archivo:
        cabecera = archivo.read().split('</head>')[0]
    assert '<link rel="icon" href="/favicon.ico" sizes="any">' in cabecera
    assert '<link rel="icon" href="/img/favicon-32.png" type="image/png" sizes="32x32">' in cabecera
    assert '<link rel="apple-touch-icon" href="/img/apple-touch-icon.png">' in cabecera
