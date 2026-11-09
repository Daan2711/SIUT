"""Restricciones de la base de datos (las mismas que existen en Neon)."""
import pytest
from sqlalchemy.exc import IntegrityError

import Controllers.postulacionesController as postulaciones
from conftest import postular, cvs_guardados
from Database.database import db
from Models.models import Alumno, Auditoria, Postulacion


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


def test_envio_simultaneo_devuelve_409_sin_guardar_el_cv(app, alumno, vacante_id, monkeypatch):
    """Simula la carrera: la verificación previa no ve la primera postulación,
    así que el segundo envío llega hasta la restricción de la base de datos."""
    assert postular(alumno, vacante_id).status_code == 201
    monkeypatch.setattr(postulaciones, '_ya_postulado', lambda *_: False)

    respuesta = postular(alumno, vacante_id)

    assert respuesta.status_code == 409
    assert cvs_guardados() == 1             # el CV del segundo envío no se guardó
    with app.app_context():
        assert Postulacion.query.count() == 1
        assert Alumno.query.count() == 1


# --- auditoria.accion es varchar(100) en Neon --------------------------------
def test_bd_rechaza_accion_de_auditoria_mayor_a_100(app):
    with app.app_context():
        db.session.add(Auditoria(accion='x' * 101))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()


def test_todas_las_acciones_auditadas_caben_en_100(app, alumno, reclutador, vacante_id):
    """Recorre los flujos que escriben en auditoria con valores al máximo permitido."""
    largo = reclutador.post('/api/vacantes', json={
        'titulo': 'T' * 150, 'area': 'Tecnología', 'modalidad': 'Remoto', 'ubicacion': 'Remoto',
        'experiencia': 'Junior', 'jornada': 'Tiempo completo',
        'descripcion': 'd', 'requisitos': 'r'}).get_json()['id']
    postulacion = postular(alumno, largo).get_json()['id']
    assert reclutador.get(f'/api/postulaciones/{postulacion}/cv').status_code == 200
    assert alumno.post('/logout').status_code == 200

    with app.app_context():
        acciones = {a.accion for a in Auditoria.query.all()}
        assert acciones == {'Inicio de sesión', 'Alta de vacante', 'Postulación a vacante',
                            'Descarga de CV', 'Cierre de sesión'}
        assert max(len(a) for a in acciones) <= 100
