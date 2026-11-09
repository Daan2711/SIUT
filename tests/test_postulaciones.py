"""Postulaciones con CV: envío (alumno), listado y descarga (reclutador)."""
import pytest

import os

from conftest import PDF, VACANTE, postular, cvs_guardados
from Database.database import db
from Models.models import Alumno, Postulacion, PostulacionCV

UN_MB = 1024 * 1024


# --- Envío -------------------------------------------------------------------
def test_postulacion_valida(app, alumno, vacante_id):
    respuesta = postular(alumno, vacante_id)
    assert respuesta.status_code == 201
    assert cvs_guardados() == 1

    with app.app_context():
        postulacion = db.session.get(Postulacion, respuesta.get_json()['id'])
        datos_alumno = Alumno.query.filter_by(matricula='A123').first()
        assert postulacion.cv_nombre == 'Mi_CV.pdf'          # nombre saneado
        assert postulacion.cv_tamano_bytes == len(PDF)
        assert datos_alumno.carrera == 'Desarrollo de Software'
        assert datos_alumno.semestre == '5° semestre'


def test_sin_registro_de_alumno_no_puede_postularse(reclutador, vacante_id):
    assert postular(reclutador, vacante_id).status_code == 403


def test_requiere_sesion(anon):
    assert postular(anon, 1).status_code == 401


@pytest.mark.parametrize('cv, codigo', [
    (None, 400),                                            # sin archivo
    ((PDF, 'cv.docx'), 400),                                # extensión
    ((b'MZ ejecutable', 'cv.pdf'), 400),                    # contenido no PDF
    ((b'', 'cv.pdf'), 400),                                 # vacío
    ((b'%PDF-' + b'0' * (5 * UN_MB), 'cv.pdf'), 413),       # > 5 MB
])
def test_validacion_del_cv(alumno, vacante_id, cv, codigo):
    assert postular(alumno, vacante_id, cv=cv).status_code == codigo
    assert cvs_guardados() == 0


def test_peticion_mayor_a_6_mb_devuelve_413_json(alumno, vacante_id):
    respuesta = postular(alumno, vacante_id, cv=(b'%PDF-' + b'0' * (7 * UN_MB), 'cv.pdf'))
    assert respuesta.status_code == 413
    assert respuesta.is_json


@pytest.mark.parametrize('extra', [
    {'semestre': '9° semestre'},
    {'telefono': 'abc'},
    {'habilidades': ''},
    {'carrera': 'x' * 121},
    {'vacante_id': 'no-es-numero'},
])
def test_validacion_de_campos(alumno, vacante_id, extra):
    assert postular(alumno, vacante_id, **extra).status_code == 400
    assert cvs_guardados() == 0


def test_vacante_inexistente(alumno):
    assert postular(alumno, 999).status_code == 404


def test_postulacion_duplicada(alumno, vacante_id):
    postular(alumno, vacante_id)
    assert postular(alumno, vacante_id).status_code == 409


def test_error_de_bd_no_deja_archivo_huerfano(alumno, vacante_id, falla_commit):
    falla_commit()
    respuesta = postular(alumno, vacante_id)
    assert respuesta.status_code == 500
    assert cvs_guardados() == 0


# --- Listado (reclutador) ----------------------------------------------------
def test_reclutador_ve_postulaciones_de_sus_vacantes(alumno, reclutador, vacante_id):
    postular(alumno, vacante_id)
    postulaciones = reclutador.get('/api/postulaciones').get_json()['postulaciones']
    assert len(postulaciones) == 1
    assert postulaciones[0]['matricula'] == 'A123'
    assert postulaciones[0]['vacante_titulo'] == VACANTE['titulo']


def test_otra_empresa_no_ve_postulaciones_ajenas(alumno, vacante_id, crear_usuario_empresa, cliente_de):
    postular(alumno, vacante_id)
    crear_usuario_empresa('rec2@x.mx', 'OtraEmpresa')
    respuesta = cliente_de('rec2@x.mx').get('/api/postulaciones')
    assert respuesta.status_code == 200
    assert respuesta.get_json()['postulaciones'] == []


def test_alumno_no_lista_postulaciones(alumno):
    assert alumno.get('/api/postulaciones').status_code == 403


# --- Descarga del CV ---------------------------------------------------------
@pytest.fixture
def postulacion_id(alumno, vacante_id):
    return postular(alumno, vacante_id).get_json()['id']


def test_dueno_descarga_el_cv(reclutador, postulacion_id):
    respuesta = reclutador.get(f'/api/postulaciones/{postulacion_id}/cv')
    assert respuesta.status_code == 200
    assert respuesta.data.startswith(b'%PDF-')
    assert 'attachment' in respuesta.headers['Content-Disposition']
    assert respuesta.mimetype == 'application/pdf'


def test_otra_empresa_no_descarga(postulacion_id, crear_usuario_empresa, cliente_de):
    crear_usuario_empresa('rec2@x.mx', 'OtraEmpresa')
    assert cliente_de('rec2@x.mx').get(f'/api/postulaciones/{postulacion_id}/cv').status_code == 403


def test_alumno_no_descarga(alumno, postulacion_id):
    assert alumno.get(f'/api/postulaciones/{postulacion_id}/cv').status_code == 403


def test_sin_sesion_no_descarga(anon, postulacion_id):
    assert anon.get(f'/api/postulaciones/{postulacion_id}/cv').status_code == 401


def test_cv_se_guarda_en_la_base_de_datos_y_no_en_disco(app, postulacion_id):
    with app.app_context():
        archivo = db.session.get(PostulacionCV, postulacion_id)
        assert archivo is not None
        assert archivo.contenido == PDF            # el mismo PDF, byte por byte
    # La app ya no crea la carpeta de CV en disco (Render gratis no la conserva)
    assert not os.path.exists(os.path.join(app.instance_path, 'uploads'))


def test_descarga_devuelve_el_pdf_original(reclutador, postulacion_id):
    respuesta = reclutador.get(f'/api/postulaciones/{postulacion_id}/cv')
    assert respuesta.data == PDF
    assert 'Mi_CV.pdf' in respuesta.headers['Content-Disposition']


def test_postulacion_sin_cv_guardado_devuelve_404(app, reclutador, postulacion_id):
    with app.app_context():
        db.session.delete(db.session.get(PostulacionCV, postulacion_id))
        db.session.commit()
    assert reclutador.get(f'/api/postulaciones/{postulacion_id}/cv').status_code == 404


def test_postulacion_inexistente(reclutador):
    assert reclutador.get('/api/postulaciones/999/cv').status_code == 404
