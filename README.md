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



##EXPLICACION DE ARQUITECTURA Y PREGUNTAS TECNICAS DEL PROYECTO

1. Modelo-Vista-Controlador (MVC)

Un matiz importante para tu explicación: Flask no impone MVC "puro", sino algo que se suele llamar MVT (Model-View-Template), igual que Django. La diferencia de nombres confunde mucho, así que aclara esto si te preguntan:

Tabla 1 — Mapeo MVC

| Concepto clásico MVC | En tu proyecto Flask | Dónde vive |
|---|---|---|
| **Modelo** | Clases SQLAlchemy (`Usuario`, `Queja`, `Horario`, `Evento`, `Profesor`, `Materia`, `Grupo`, `HorarioDetalle`) | Definen estructura de datos y reglas de negocio básicas (validaciones, relaciones) |
| **Controlador** | Funciones de ruta de Flask (`@app.route(...)` o Blueprints de Auth/Quejas/Horarios/Eventos) | Reciben la request, consultan/modifican el Modelo, deciden qué Vista renderizar |
| **Vista** | Archivos `.html` en `/templates` renderizados con Jinja2 | Solo presentan los datos que el Controlador les pasa |

En Flask, a lo que la mayoría llama "view function" (la función decorada con @app.route) en realidad cumple el rol de Controlador del MVC clásico; el verdadero "View" es la plantilla Jinja2. Explicar esta distinción de nomenclatura suele ganar puntos porque muestra que entiendes el patrón más allá de la terminología de Flask.

Flujo típico (ejemplo con Quejas):
1. Alumno llena formulario → petición POST a /quejas/crear (Controlador)
2. Controlador valida datos, crea instancia del Modelo Queja, la guarda vía SQLAlchemy
3. Controlador redirige o renderiza una plantilla (Vista) con render_template(), pasándole el contexto (ej. lista de quejas)
4. Jinja2 inyecta esos datos en el HTML y Flask lo devuelve al navegador

2. Patrones de diseño usados

- MVC/MVT — patrón arquitectónico general, ya explicado arriba.
- ORM (Data Mapper) — SQLAlchemy separa el objeto Python (Modelo) de su representación en la tabla SQL, mapeando ambos mundos sin que el Modelo "sepa" cómo se guarda. Esto es distinto al patrón Active Record (como en Rails), donde el propio objeto sabe guardarse/consultarse a sí mismo.
- Blueprint / Modularización — Flask usa Blueprints para separar Auth, Quejas, Horarios y Eventos en módulos independientes; conceptualmente es una aplicación del principio de separ
- Decorator — Python/Flask usan decoradores extensivamente: @app.route, y muy probablemente algo como @login_required o @role_required('admin') para controlar acceso por rol. Esto es literalmente el patrón de diseño Decorator aplicado a funciones.
- Factory Pattern — si tu app.py usa una función create_app() que instancia y configura la app Flask (común en proyectos con múltiples entornos: dev/prod), eso es el patrón Factory.
- Strategy Pattern — el control de acceso por rol (Alumno/Profesor/Admin viendo distintas vistas o teniendo distintos permisos sobre el mismo recurso, ej. "quejas") puede explicarse como una aplicación conceptual de Strategy: el comportamiento del sistema cambia según el "rol" activo.
- Singleton (implícito) — la instancia de db = SQLAlchemy() se crea una sola vez y se comparte en toda la app.

3. Frameworks y tecnologías usadas

Tabla 2 — Frameworks y tecnologías

| Capa | Tecnología | Rol |
|---|---|---|
| Backend | **Flask** (Python) | Micro-framework web: enrutamiento, manejo de sesiones/requests |
| Templating | **Jinja2** | Motor de plantillas incluido en Flask, renderiza HTML dinámico |
| ORM | **SQLAlchemy** | Mapea clases Python a tablas SQL, evita escribir SQL manual |
| Frontend CSS | **Bootstrap** | Framework de estilos para diseño responsivo |
| Frontend JS | JS puro + `fetch()` | Sin framework (no React/Vue/Angular); AJAX nativo para llamadas asíncronas |
| PDF | **WeasyPrint** | Librería (no framework) que convierte HTML/CSS a PDF, usada para exportar horarios |
| Base de datos | SQL Server / PostgreSQL / MySQL, alojada en **Neon** | Neon es un proveedor de PostgreSQL *serverless* en la nube — evitas mantener tu propio servidor SQL Server |

Punto clave para tu explicación de Neon: no es un framework ni un ORM, es un DBaaS (Database as a Service) de Postgres. Lo usaste para no pagar/mantener infraestructura de servidor SQL propia — SQLAlchemy simplemente apunta su connection string a Neon en vez de a un servidor local.
