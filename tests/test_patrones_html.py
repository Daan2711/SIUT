"""Los atributos `pattern` de las páginas deben ser válidos en Edge y Chrome.

Esos navegadores compilan `pattern` con la bandera `v` de RegExp, más estricta:
dentro de [ ] hay que escapar ( ) - y otros signos. Si el patrón no compila,
el navegador ignora la validación y deja un error en la consola.
"""
import glob
import html
import json
import os
import re
import shutil
import subprocess

import pytest

from Controllers.postulacionesController import TELEFONO_RE

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND = os.path.join(RAIZ, 'Frontend')
PATRON_ATRIBUTO = re.compile(r'\bpattern="([^"]*)"')


def patrones_por_pagina():
    encontrados = []
    for ruta in sorted(glob.glob(os.path.join(FRONTEND, '*.html'))):
        with open(ruta, encoding='utf-8') as archivo:
            for patron in PATRON_ATRIBUTO.findall(archivo.read()):
                encontrados.append((os.path.basename(ruta), html.unescape(patron)))
    return encontrados


def patron_del_telefono(pagina):
    with open(os.path.join(FRONTEND, pagina), encoding='utf-8') as archivo:
        etiqueta = re.search(r'<input[^>]*name="telefono"[^>]*>', archivo.read()).group(0)
    return html.unescape(PATRON_ATRIBUTO.search(etiqueta).group(1))


def test_hay_patrones_que_revisar():
    paginas = {pagina for pagina, _ in patrones_por_pagina()}
    assert {'buzon.html', 'nueva-cuenta.html', 'login.html'} <= paginas


@pytest.mark.skipif(shutil.which('node') is None, reason='Node no está instalado')
def test_todos_los_patrones_compilan_con_la_bandera_v():
    """Se compilan con el mismo motor de Chrome y Edge (V8, vía Node)."""
    patrones = patrones_por_pagina()
    script = (
        'const ps = JSON.parse(process.argv[1]);'
        'const malos = ps.filter(([, p]) => { try { new RegExp(`^(?:${p})$`, "v"); return false; }'
        ' catch { return true; } });'
        'console.log(JSON.stringify(malos));'
    )
    resultado = subprocess.run(['node', '-e', script, json.dumps(patrones)],
                               capture_output=True, text=True, encoding='utf-8', check=True)
    assert json.loads(resultado.stdout) == []


@pytest.mark.parametrize('pagina', ['buzon.html', 'nueva-cuenta.html'])
@pytest.mark.parametrize('telefono', [
    '81 1234 5678', '+52 (81) 1234-5678', '8112345678', '81-12-34-56',
    'abc12345678', '1234567', '8' * 31, '81.1234.5678',
])
def test_el_telefono_se_valida_igual_que_en_el_servidor(pagina, telefono):
    navegador = re.fullmatch(patron_del_telefono(pagina), telefono) is not None
    assert navegador == bool(TELEFONO_RE.match(telefono))
