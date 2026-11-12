"""scripts/diagnostico_neon.py: solo lectura y sin datos personales (no se conecta a Neon)."""
import ast
import os
import re
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(RAIZ, 'scripts', 'diagnostico_neon.py')


def codigo():
    with open(SCRIPT, encoding='utf-8') as archivo:
        return archivo.read()


def textos_del_script():
    """Todas las cadenas del script (donde vive el SQL), sin el docstring del módulo."""
    arbol = ast.parse(codigo())
    docstring = ast.get_docstring(arbol, clean=False)
    return ' '.join(n.value for n in ast.walk(arbol)
                    if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value != docstring)


def test_no_contiene_instrucciones_de_escritura():
    texto = textos_del_script().lower()
    assert 'select' in texto          # sí revisa el SQL
    for palabra in ('insert', 'update', 'delete', 'alter', 'drop', 'truncate',
                    'create', 'grant', 'revoke', 'commit', 'vacuum', 'copy'):
        assert not re.search(rf'\b{palabra}\b', texto), palabra


def test_abre_la_conexion_en_solo_lectura_y_lo_verifica():
    texto = codigo()
    assert 'conn.set_session(readonly=True)' in texto
    assert "show transaction_read_only" in texto
    # La verificación ocurre antes de devolver la conexión
    conectar = texto[texto.index('def conectar'):texto.index('def main')]
    assert conectar.index('set_session(readonly=True)') < conectar.index('return conn, cur')
    assert "!= 'on'" in conectar


def test_no_consulta_columnas_con_datos_personales():
    """Ninguna consulta selecciona correos, nombres, hashes ni contenido de CV."""
    consultas = re.findall(r"select\s+(.*?)\s+from", textos_del_script(), re.I | re.S)
    columnas = ' '.join(consultas).lower()
    for sensible in ('email', 'correo', 'nombre', 'apellido', 'password_hash', 'contenido',
                     'telefono', 'matricula', 'descripcion', 'respuesta_admin', 'comentario_empresa'):
        assert sensible not in columnas.replace('lower(email)', ''), sensible


def test_sin_database_url_se_detiene_con_codigo_2(tmp_path):
    entorno = {k: v for k, v in os.environ.items() if k != 'DATABASE_URL'}
    # Se copia el script a una carpeta sin .env para que no lea el del repositorio
    destino = tmp_path / 'scripts'
    destino.mkdir()
    (destino / 'diagnostico_neon.py').write_text(codigo(), encoding='utf-8')
    resultado = subprocess.run([sys.executable, str(destino / 'diagnostico_neon.py')],
                               env=entorno, capture_output=True, text=True, encoding='utf-8')
    assert resultado.returncode == 2
    assert 'DATABASE_URL' in resultado.stderr
    assert 'No se revisó nada' in resultado.stderr
