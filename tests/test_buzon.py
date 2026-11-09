"""Buzón de sugerencias."""
from Models.models import Sugerencia, CategoriaSugerencia

SUGERENCIA = {'nombre': 'Ana', 'grupo': '3A', 'departamento': 'Sistemas', 'descripcion': 'Falla el wifi'}


def test_sugerencia_valida(alumno):
    respuesta = alumno.post('/guardar-sugerencia', json=SUGERENCIA)
    assert respuesta.status_code == 201


def test_requiere_sesion(anon):
    assert anon.post('/guardar-sugerencia', json=SUGERENCIA).status_code == 401


def test_otro_no_crea_categorias_y_conserva_el_area(app, alumno):
    alumno.post('/guardar-sugerencia', json=SUGERENCIA)
    respuesta = alumno.post('/guardar-sugerencia', json=dict(SUGERENCIA, departamento='Cafetería'))

    assert respuesta.status_code == 201
    with app.app_context():
        categorias = sorted(c.nombre for c in CategoriaSugerencia.query.all())
        ultima = Sugerencia.query.order_by(Sugerencia.id.desc()).first()
        assert categorias == ['Otro', 'Sistemas']
        assert ultima.descripcion.startswith('[Área indicada: Cafetería]')


def test_limites_de_longitud(alumno):
    assert alumno.post('/guardar-sugerencia', json=dict(SUGERENCIA, nombre='x' * 101)).status_code == 400
    assert alumno.post('/guardar-sugerencia', json=dict(SUGERENCIA, grupo='x' * 51)).status_code == 400
    assert alumno.post('/guardar-sugerencia', json=dict(SUGERENCIA, descripcion='x' * 2001)).status_code == 400


def test_campos_obligatorios(alumno):
    assert alumno.post('/guardar-sugerencia', json=dict(SUGERENCIA, descripcion='  ')).status_code == 400


def test_cuerpo_no_json(alumno):
    respuesta = alumno.post('/guardar-sugerencia', data='no-json', content_type='text/plain')
    assert respuesta.status_code == 400


def test_error_500_sin_detalle_interno(alumno, falla_commit):
    falla_commit()
    respuesta = alumno.post('/guardar-sugerencia', json=SUGERENCIA)
    assert respuesta.status_code == 500
    assert 'secreto' not in respuesta.get_data(as_text=True)
