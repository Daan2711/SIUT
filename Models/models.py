from Database.database import db
from datetime import datetime

class Usuario(db.Model):
    __tablename__ = 'usuarios'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    rol = db.Column(db.String(50), nullable=False) 
    activo = db.Column(db.Boolean, default=True)
    primer_login = db.Column(db.Boolean, default=True)
    
    creado_por = db.Column(db.Integer, nullable=True)
    modificado_por = db.Column(db.Integer, nullable=True)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)
    modificado_en = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def soft_delete(self):
        self.activo = False
        db.session.commit()

class Alumno(db.Model):
    __tablename__ = 'alumnos'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    matricula = db.Column(db.String(50), unique=True, nullable=False)
    carrera = db.Column(db.String(100))
    semestre = db.Column(db.Integer)
    
    creado_por = db.Column(db.Integer)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)
    modificado_en = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Profesor(db.Model):
    __tablename__ = 'profesores'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    num_empleado = db.Column(db.String(50), unique=True, nullable=False)
    departamento = db.Column(db.String(100))
    especialidad = db.Column(db.String(100))
    
    creado_por = db.Column(db.Integer)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)
    modificado_en = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Materia(db.Model):
    __tablename__ = 'materias'
    
    id = db.Column(db.Integer, primary_key=True)
    clave = db.Column(db.String(20), unique=True, nullable=False)
    nombre = db.Column(db.String(150), nullable=False)
    creditos = db.Column(db.Integer)
    
    creado_por = db.Column(db.Integer)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)
    modificado_en = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Grupo(db.Model):
    __tablename__ = 'grupos'
    
    id = db.Column(db.Integer, primary_key=True)
    materia_id = db.Column(db.Integer, db.ForeignKey('materias.id'), nullable=False)
    profesor_id = db.Column(db.Integer, db.ForeignKey('profesores.id'), nullable=False)
    periodo = db.Column(db.String(50))
    cupo_max = db.Column(db.Integer)
    activo = db.Column(db.Boolean, default=True)
    
    creado_por = db.Column(db.Integer)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)
    modificado_en = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def soft_delete(self):
        self.activo = False
        db.session.commit()

class Horario(db.Model):
    __tablename__ = 'horarios'
    
    id = db.Column(db.Integer, primary_key=True)
    grupo_id = db.Column(db.Integer, db.ForeignKey('grupos.id'), nullable=False)
    dia_semana = db.Column(db.String(20))
    hora_inicio = db.Column(db.Time)
    hora_fin = db.Column(db.Time)
    aula = db.Column(db.String(50))
    
    creado_por = db.Column(db.Integer)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)
    modificado_en = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Evento(db.Model):
    __tablename__ = 'eventos'
    
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(150), nullable=False)
    descripcion = db.Column(db.Text)
    fecha_inicio = db.Column(db.DateTime)
    fecha_fin = db.Column(db.DateTime)
    lugar = db.Column(db.String(150))
    tipo = db.Column(db.String(50))
    
    creado_por = db.Column(db.Integer)
    modificado_por = db.Column(db.Integer)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)
    modificado_en = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class DirectorioMaestro(db.Model):
    __tablename__ = 'directorio_maestros'
    
    id = db.Column(db.Integer, primary_key=True)
    profesor_id = db.Column(db.Integer, db.ForeignKey('profesores.id'), nullable=False)
    telefono_oficina = db.Column(db.String(20))
    correo_institucional = db.Column(db.String(150))
    cubiculo = db.Column(db.String(50))
    horario_atencion = db.Column(db.String(100))
    visible = db.Column(db.Boolean, default=True)
    
    creado_por = db.Column(db.Integer)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)
    modificado_en = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CategoriaSugerencia(db.Model):
    __tablename__ = 'categorias_sugerencia'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    activo = db.Column(db.Boolean, default=True)
    
    creado_por = db.Column(db.Integer)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)
    modificado_en = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Sugerencia(db.Model):
    __tablename__ = 'sugerencias'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    nombre_remitente = db.Column(db.String(100))
    grupo_grado = db.Column(db.String(50))
    categoria_id = db.Column(db.Integer, db.ForeignKey('categorias_sugerencia.id'))
    descripcion = db.Column(db.Text, nullable=False)
    estado = db.Column(db.String(50), default='Pendiente')
    respuesta_admin = db.Column(db.Text)
    atendida_por = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    fecha_atencion = db.Column(db.DateTime)
    activo = db.Column(db.Boolean, default=True)
    
    creado_por = db.Column(db.Integer)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)
    modificado_en = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def soft_delete(self):
        self.activo = False
        db.session.commit()

class AlumnoGrupo(db.Model):
    __tablename__ = 'alumno_grupo'
    
    id = db.Column(db.Integer, primary_key=True)
    alumno_id = db.Column(db.Integer, db.ForeignKey('alumnos.id'), nullable=False)
    grupo_id = db.Column(db.Integer, db.ForeignKey('grupos.id'), nullable=False)
    estado = db.Column(db.String(50))
    fecha_inscripcion = db.Column(db.DateTime, default=datetime.utcnow)
    
    creado_por = db.Column(db.Integer)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)
    modificado_en = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class UsuarioEvento(db.Model):
    __tablename__ = 'usuario_evento'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    evento_id = db.Column(db.Integer, db.ForeignKey('eventos.id'), nullable=False)
    rol_evento = db.Column(db.String(50))
    
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)

class Auditoria(db.Model):

    __tablename__ = 'auditoria'

    id = db.Column(db.Integer, primary_key=True)

    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey('usuarios.id')
    )

    accion = db.Column(
        db.String(255),
        nullable=False
    )

    fecha = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )
