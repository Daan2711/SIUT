import os
from flask import Flask
from dotenv import load_dotenv

# Importamos la instancia de la base de datos que ya tienes
from Database.database import db

# Importamos tus modelos para que SQLAlchemy los reconozca al crear las tablas
# (Asegúrate de que tu archivo models.py importe 'db' de Database.database)
import Models.models 

# Cargamos las variables de tu archivo .env
load_dotenv()

# Inicializamos la aplicación de Flask
app = Flask(__name__)

# Configuramos la conexión a Neon leyendo la variable de entorno
# Nota: Flask-SQLAlchemy busca específicamente esta variable de configuración
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("NEON_DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Vinculamos la base de datos con nuestra aplicación de Flask
db.init_app(app)

# Esto crea todas las tablas en Neon automáticamente si es que aún no existen
with app.app_context():
    db.create_all()

# Arrancamos el servidor
if __name__ == '__main__':
    app.run(debug=True)