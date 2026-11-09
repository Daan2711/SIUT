from Database.database import db
from datetime import datetime

class Usuario(db.Model):
    __tablename__ = 'usuarios'
    # Igual que en Neon: correo único sin distinguir mayúsculas, roles válidos,
    # una Empresa siempre ligada a su empresa y un usuario Empresa por empresa.
    __table_args__ = (
        db.Index('uq_usuarios_email', db.func.lower(db.text('email')), unique=True),
        db.CheckConstraint(
            "rol IN ('Alumno', 'Profesor', 'Empresa', 'Administrador')",
            name='chk_usuarios_rol',
        ),
        db.CheckConstraint(
            "(rol = 'Empresa' AND empresa_id IS NOT NULL) "
            "OR (rol <> 'Empresa' AND empresa_id IS NULL)",
            name='chk_usuario_empresa',
        ),
        db.Index(
            'uq_usuario_empresa', 'empresa_id', unique=True,
            postgresql_where=db.text("rol = 'Empresa'"),
            sqlite_where=db.text("rol = 'Empresa'"),
        ),
    )

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String, nullable=False)
    apellido = db.Column(db.String, nullable=True)
    email = db.Column(db.String, nullable=False)
    password_hash = db.Column(db.String, nullable=False)
    rol = db.Column(db.String, nullable=False, default='Alumno')
    empresa_id = db.Column(db.BigInteger, db.ForeignKey('empresas.id'), nullable=True)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    primer_login = db.Column(db.Boolean, nullable=False, default=True)
    creado_por = db.Column(db.BigInteger, db.ForeignKey('usuarios.id'), nullable=True)
    modificado_por = db.Column(db.BigInteger, db.ForeignKey('usuarios.id'), nullable=True)
    creado_en = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())
    modificado_en = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.now(),
        onupdate=db.func.now()
    )


class Alumno(db.Model):
    __tablename__ = 'alumnos'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    # Un registro de alumno por usuario y matrícula única (como en Neon)
    usuario_id = db.Column(db.BigInteger, db.ForeignKey('usuarios.id'), nullable=False, unique=True)
    matricula = db.Column(db.String, nullable=False, unique=True)
    carrera = db.Column(db.String, nullable=True)
    semestre = db.Column(db.String, nullable=True)
    telefono = db.Column(db.String, nullable=True)
    creado_en = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())
    modificado_en = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.now(),
        onupdate=db.func.now()
    )


class Profesor(db.Model):
    __tablename__ = 'profesores'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    usuario_id = db.Column(db.BigInteger, db.ForeignKey('usuarios.id'), nullable=False)
    num_empleado = db.Column(db.String, nullable=False)
    departamento = db.Column(db.String, nullable=True)
    especialidad = db.Column(db.String, nullable=True)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    creado_en = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())
    modificado_en = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.now(),
        onupdate=db.func.now()
    )
class Materia(db.Model):
    __tablename__ = 'materias'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    clave = db.Column(db.String, nullable=False, unique=True)
    nombre = db.Column(db.String, nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    creado_en = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())
    modificado_en = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.now(),
        onupdate=db.func.now()
    )


class Grupo(db.Model):
    __tablename__ = 'grupos'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String, nullable=False)
    materia_id = db.Column(db.BigInteger, db.ForeignKey('materias.id'), nullable=False)
    profesor_id = db.Column(db.BigInteger, db.ForeignKey('profesores.id'), nullable=False)
    periodo = db.Column(db.String, nullable=False)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    creado_en = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())
    modificado_en = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.now(),
        onupdate=db.func.now()
    )
    
class Horario(db.Model):
    __tablename__ = 'horarios'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    grupo_id = db.Column(db.BigInteger, db.ForeignKey('grupos.id'), nullable=False)
    dia_semana = db.Column(db.String, nullable=False)
    hora_inicio = db.Column(db.Time, nullable=False)
    hora_fin = db.Column(db.Time, nullable=False)
    aula = db.Column(db.String, nullable=True)


class Evento(db.Model):
    __tablename__ = 'eventos'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    titulo = db.Column(db.String, nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    fecha_inicio = db.Column(db.DateTime(timezone=True), nullable=False)
    fecha_fin = db.Column(db.DateTime(timezone=True), nullable=True)
    ubicacion = db.Column(db.String, nullable=True)
    imagen_url = db.Column(db.Text, nullable=True)
    publicado = db.Column(db.Boolean, nullable=False, default=False)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    creado_por = db.Column(db.BigInteger, db.ForeignKey('usuarios.id'), nullable=True)
    creado_en = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())
    modificado_en = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.now(),
        onupdate=db.func.now()
    )
    
class DirectorioMaestro(db.Model):
    __tablename__ = 'directorio_maestros'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    profesor_id = db.Column(db.BigInteger, db.ForeignKey('profesores.id'), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    fotografia_url = db.Column(db.Text, nullable=True)
    correo_contacto = db.Column(db.String, nullable=True)
    telefono = db.Column(db.String, nullable=True)
    publicado = db.Column(db.Boolean, nullable=False, default=True)
    modificado_en = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.now(),
        onupdate=db.func.now()
    )


class AlumnoGrupo(db.Model):
    __tablename__ = 'alumno_grupo'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    alumno_id = db.Column(db.BigInteger, db.ForeignKey('alumnos.id'), nullable=False)
    grupo_id = db.Column(db.BigInteger, db.ForeignKey('grupos.id'), nullable=False)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    fecha_inicio = db.Column(db.Date, nullable=False, server_default=db.func.current_date())
    fecha_fin = db.Column(db.Date, nullable=True)
    creado_en = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())
    
class CategoriaSugerencia(db.Model):
    __tablename__ = 'categorias_sugerencia'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    activo = db.Column(db.Boolean, nullable=False, server_default=db.text('true'))
    creado_por = db.Column(db.BigInteger, db.ForeignKey('usuarios.id'), nullable=True)
    creado_en = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.now()
    )
    modificado_en = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.now(),
        onupdate=db.func.now()
    )


class Sugerencia(db.Model):
    __tablename__ = 'sugerencias'
    # Igual que en Neon
    __table_args__ = (
        db.CheckConstraint(
            "estado IN ('Recibida', 'En revisión', 'Atendida', 'Rechazada')",
            name='chk_sugerencia_estado',
        ),
    )

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    usuario_id = db.Column(db.BigInteger, db.ForeignKey('usuarios.id'), nullable=False)
    nombre_remitente = db.Column(db.String(100), nullable=False)
    grupo_grado = db.Column(db.String(50), nullable=False)
    categoria_id = db.Column(
        db.BigInteger,
        db.ForeignKey('categorias_sugerencia.id'),
        nullable=False
    )
    descripcion = db.Column(db.Text, nullable=False)
    estado = db.Column(db.String(50), nullable=False, server_default=db.text("'Recibida'"))
    respuesta_admin = db.Column(db.Text, nullable=True)
    atendida_por = db.Column(db.BigInteger, db.ForeignKey('usuarios.id'), nullable=True)
    fecha_atencion = db.Column(db.DateTime(timezone=True), nullable=True)
    activo = db.Column(db.Boolean, nullable=False, server_default=db.text('true'))
    creado_por = db.Column(db.BigInteger, db.ForeignKey('usuarios.id'), nullable=True)
    creado_en = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.now()
    )
    modificado_en = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.now(),
        onupdate=db.func.now()
    )

    def soft_delete(self):
        self.activo = False
        db.session.commit()

class UsuarioEvento(db.Model):
    __tablename__ = 'usuario_evento'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    usuario_id = db.Column(db.BigInteger, db.ForeignKey('usuarios.id'), nullable=False)
    evento_id = db.Column(db.BigInteger, db.ForeignKey('eventos.id'), nullable=False)
    estado = db.Column(db.String, nullable=False, default='Inscrito')
    registrado_en = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.now()
    )


class Auditoria(db.Model):
    __tablename__ = 'auditoria'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    usuario_id = db.Column(db.BigInteger, db.ForeignKey('usuarios.id'), nullable=True)
    # Largos iguales a Neon: 'accion' es un texto corto y fijo; el detalle va en 'descripcion'
    accion = db.Column(db.String(100), nullable=False)
    tabla_afectada = db.Column(db.String(100), nullable=True)
    registro_id = db.Column(db.BigInteger, nullable=True)
    descripcion = db.Column(db.Text, nullable=True)
    creado_en = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.now()
    )
    
    
    
class Vacante(db.Model):
    __tablename__ = 'vacantes'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    empresa_id = db.Column(db.BigInteger, db.ForeignKey('empresas.id'), nullable=False)
    titulo = db.Column(db.String, nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    requisitos = db.Column(db.Text, nullable=False)
    area = db.Column(db.String, nullable=False)
    modalidad = db.Column(db.String, nullable=False)
    ubicacion = db.Column(db.String, nullable=False)
    experiencia = db.Column(db.String, nullable=False)
    jornada = db.Column(db.String, nullable=False)
    activo = db.Column(db.Boolean, nullable=False, server_default=db.text('true'))
    creado_por = db.Column(db.BigInteger, db.ForeignKey('usuarios.id'), nullable=False)
    creado_en = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())
    publicada_en = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())
    modificado_en = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.now(),
        onupdate=db.func.now()
    )
class Empresa(db.Model):
    __tablename__ = 'empresas'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String, nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    logo_url = db.Column(db.Text, nullable=True)
    sitio_web = db.Column(db.String, nullable=True)
    correo_contacto = db.Column(db.String, nullable=True)
    telefono = db.Column(db.String, nullable=True)
    activo = db.Column(db.Boolean, nullable=False, server_default=db.text('true'))
    creado_en = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())
    modificado_en = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.now(),
        onupdate=db.func.now()
    )


class Postulacion(db.Model):
    __tablename__ = 'postulaciones'
    # Una postulación por alumno y vacante (como en Neon)
    __table_args__ = (
        db.UniqueConstraint('alumno_id', 'vacante_id', name='uq_alumno_vacante'),
    )

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    vacante_id = db.Column(db.BigInteger, db.ForeignKey('vacantes.id'), nullable=False)
    alumno_id = db.Column(db.BigInteger, db.ForeignKey('alumnos.id'), nullable=False)
    habilidades = db.Column(db.String, nullable=False)
    experiencia = db.Column(db.String, nullable=True)
    mensaje = db.Column(db.String, nullable=True)
    cv_storage_key = db.Column(db.String, nullable=False, unique=True)
    cv_nombre = db.Column(db.String, nullable=False)
    cv_content_type = db.Column(db.String, nullable=False)
    cv_tamano_bytes = db.Column(db.BigInteger, nullable=False)
    estado = db.Column(db.String, nullable=False, server_default=db.text("'Recibida'"))
    creado_en = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())
    modificado_en = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.now(),
        onupdate=db.func.now()
    )


class PostulacionCV(db.Model):
    """Contenido del CV (PDF) de una postulación, guardado en la base de datos.

    Va en una tabla aparte para que listar postulaciones no cargue los PDF.
    Creada por migrations/2026-11-08_postulacion_cv.sql.
    """
    __tablename__ = 'postulacion_cv'
    __table_args__ = (
        # length() de bytea/blob = bytes, tanto en PostgreSQL como en SQLite
        db.CheckConstraint(
            'length(contenido) > 0 AND length(contenido) <= 5242880',
            name='chk_postulacion_cv_tamano',
        ),
    )

    postulacion_id = db.Column(db.BigInteger, db.ForeignKey('postulaciones.id'), primary_key=True)
    contenido = db.Column(db.LargeBinary, nullable=False)
    creado_en = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())


class Notificacion(db.Model):
    __tablename__ = 'notificaciones'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    usuario_id = db.Column(db.BigInteger, db.ForeignKey('usuarios.id'), nullable=False)
    postulacion_id = db.Column(db.BigInteger, db.ForeignKey('postulaciones.id'), nullable=True)
    tipo = db.Column(db.String, nullable=False)
    mensaje = db.Column(db.Text, nullable=False)
    leida = db.Column(db.Boolean, nullable=False, server_default=db.text('false'))
    creado_en = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())