from Database.database import db

class Usuario(db.Model):

    __tablename__ = "Alumnos"

    id = db.Column(db.Integer, primary_key=True)

    nombre = db.Column(db.String(100))

    apellido = db.Column(db.String(100))

    correo = db.Column(db.String(255), unique=True)

    password = db.Column(db.String(255))

    rol = db.Column(db.String(20), default="alumno")