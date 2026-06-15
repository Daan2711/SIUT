Arquitectura del Proyecto
👥 Capa de Usuario (Roles)
Alumno: Acceso a quejas, horarios, eventos y consulta de profesores.

Profesor: Acceso a quejas y gestión de su horario propio.

Admin: Encargado de subir horarios, gestionar eventos y administrar profesores.

🎨 Frontend a
Tecnologías: HTML + CSS + JS puro (Sin frameworks JS).

Framework de estilos: Bootstrap para el diseño responsivo.

Renderizado: Archivos .html servidos directamente por Flask desde la carpeta /templates, utilizando Jinja2 para renderizar los datos dinámicos en las páginas.

Comunicación: Uso de fetch() para realizar llamadas AJAX asíncronas donde sea necesario.

⚙️ Backend
Tecnología Principal: Flask (Python)

Módulos / Servicios:

Auth: Gestión de Login, sesiones y control de roles.

Quejas: Funcionalidades para crear, listar y ver el historial.

Horarios: Visualización y exportación a PDF (utilizando WeasyPrint).

Eventos / Prof.: Listar y crear (módulo exclusivo para el administrador).

🗄️ Base de Datos
Motores Soportados: SQL Server / PostgreSQL / MySQL.

Mapeo del Modelo: SQLAlchemy ORM — Los modelos se definen directamente en Python y las tablas se generan de forma automática.

Tablas principales:

usuarios

quejas

horarios

eventos

profesores

materias

grupos

horario_detalle (campos: hora, día, aula)