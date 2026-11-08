"""Restricciones UNIQUE de la base de datos (las mismas que existen en Neon)."""
import pytest
from sqlalchemy.exc import IntegrityError

import Controllers.postulacionesController as postulaciones
from conftest import postular, archivos_cv
from Database.database import db
from Models.models import Alumno, Postulacion


def test_correo_unico_sin_distinguir_mayusculas(app, crear_usuario):
    crear_usuario('ana@x.mx')
    with pytest.raises(IntegrityError):
        crear_usuario('ANA@x.mx')


def test_un_registro_de_alumno_por_usuario(app, crear_usuario, crear_alumno):
    usuario_id = crear_usuario('alu@x.mx')
    crear_alumno(usuario_id, matricula='A1')
    with pytest.raises(IntegrityError):
        crear_alumno(usuario_id, matricula='A2')


def test_matricula_unica(app, crear_usuario, crear_alumno):
    crear_alumno(crear_usuario('uno@x.mx'), matricula='A1')
    with pytest.raises(IntegrityError):
        crear_alumno(crear_usuario('dos@x.mx'), matricula='A1')


def test_postulacion_unica_por_alumno_y_vacante(app, alumno, vacante_id):
    postular(alumno, vacante_id)
    with app.app_context():
        original = Postulacion.query.one()
        db.session.add(Postulacion(
            vacante_id=original.vacante_id, alumno_id=original.alumno_id,
            habilidades='x', cv_storage_key='otra-clave', cv_nombre='cv.pdf',
            cv_content_type='application/pdf', cv_tamano_bytes=10,
        ))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()


def test_envio_simultaneo_devuelve_409_y_borra_el_cv(app, alumno, vacante_id, monkeypatch):
    """Simula la carrera: la verificación previa no ve la primera postulación,
    así que el segundo envío llega hasta la restricción de la base de datos."""
    assert postular(alumno, vacante_id).status_code == 201
    monkeypatch.setattr(postulaciones, '_ya_postulado', lambda *_: False)

    respuesta = postular(alumno, vacante_id)

    assert respuesta.status_code == 409
    assert len(archivos_cv()) == 1          # el CV del segundo envío se borró
    with app.app_context():
        assert Postulacion.query.count() == 1
        assert Alumno.query.count() == 1
