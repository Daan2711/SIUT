# SIUT — Sistema Integral de la UTSC

Portal web para la comunidad de la UTSC: bolsa de empleo con postulación y CV, buzón de sugerencias, horario, directorio de maestros y soporte.

- **Producción:** Render (plan gratis) + Neon (PostgreSQL). Guía: [`docs/DESPLIEGUE_RENDER.md`](docs/DESPLIEGUE_RENDER.md)
- **Esquema de la base de datos:** [`docs/ESQUEMA_BD.md`](docs/ESQUEMA_BD.md)
- **Historial de cambios:** [`CHANGELOG.md`](CHANGELOG.md)

## Roles

| Rol | Qué puede hacer | Página de inicio |
|---|---|---|
| **Alumno** | Buscar vacantes y postularse con su CV (PDF), enviar sugerencias, ver horario, maestros y soporte | `index.html` |
| **Empresa** | Publicar vacantes a nombre de su empresa, ver las postulaciones y descargar los CV | `vacantes-publicadas.html` |
| **Administrador** (máx. 4) | Todo lo de Empresa para cualquier empresa, ver todas las postulaciones y atender el buzón de sugerencias | `panel-admin.html` |
| **Profesor** | Existe en la base de datos; aún sin funciones propias en la web | `index.html` |

No hay registro público: las cuentas se crean con `flask crear-usuario` (ver la guía de despliegue). Toda cuenta nueva debe cambiar su contraseña en el primer inicio de sesión.

## Arquitectura

```
Navegador ──HTML/CSS/JS──▶ Flask (app.py) ──SQLAlchemy──▶ Neon (PostgreSQL)
            ◀──JSON (fetch)──   Controllers/                  tablas, triggers y CV (PDF)
```

| Capa | Tecnología | Dónde |
|---|---|---|
| Frontend | HTML + CSS + JavaScript puro (sin frameworks); llamadas `fetch()` a la API JSON | `Frontend/` |
| Backend | **Flask** con Blueprints; gunicorn en producción | `app.py`, `Controllers/` |
| Datos | **SQLAlchemy** (ORM) sobre **PostgreSQL** en **Neon** | `Models/models.py`, `Database/database.py` |
| Esquema | Scripts SQL versionados (la app no crea tablas en Neon) | `migrations/` |
| Seguridad | bcrypt, sesión con cookie segura, límite de intentos (Flask-Limiter), CSP y cabeceras, SRI en scripts de cdnjs | `app.py`, `extensions.py` |
| Despliegue | Docker (usuario sin privilegios), Blueprint de Render, health check `/healthz` | `Dockerfile`, `render.yaml` |
| Pruebas | **pytest** contra SQLite temporal | `tests/` |

Librerías de cdnjs (con SRI): **html2pdf** (descarga del horario en PDF) y **SweetAlert2** (mensajes del buzón).

### Estructura

```
app.py                  Configuración, seguridad, páginas protegidas, /healthz
comandos.py             Comando `flask crear-usuario`
extensions.py           Límite de intentos (Flask-Limiter)
Controllers/
  authController.py     Login, logout, cambio de contraseña, /usuario-actual
  vacantesController.py Vacantes y permisos por rol (Empresa / Administrador)
  postulacionesController.py  Postulaciones y CV (guardados en la base de datos)
  buzonController.py    Buzón de sugerencias y bandeja del administrador
Models/models.py        Modelos SQLAlchemy (con las restricciones de Neon)
Frontend/               Páginas HTML, css/, js/, img/
migrations/             Cambios de esquema en Neon (con su script para revertir)
docs/                   Despliegue, esquema de la base de datos, descripción del PR
tests/                  Pruebas automatizadas
```

## Desarrollo local

```bash
pip install -r requirements-dev.txt
```

Crea un archivo `.env` (no se sube a git):

```env
DATABASE_URL=postgresql://...      # Neon, o sqlite:///siut_local.db para una base local
SECRET_KEY=una-clave-larga-y-aleatoria
# Solo con una base local nueva: crea las tablas al arrancar
# AUTO_CREATE_TABLES=true
```

```bash
python app.py        # http://127.0.0.1:5000
```

> **Cuidado:** si `DATABASE_URL` apunta a Neon, lo que hagas en local (incluido `flask crear-usuario`) escribe en la base de datos real.

## Pruebas automatizadas

Usan **pytest** y una base SQLite temporal: no tocan Neon ni leen el `.env`. Además de los modelos, replican en SQLite reglas que en Neon viven en la base de datos (el trigger de creadores de vacantes y el largo de la auditoría).

```bash
python -m pytest
```

| Archivo | Qué cubre |
|---|---|
| `test_auth.py` | Login, cambio de contraseña obligatorio, límite de intentos, sesión |
| `test_seguridad.py` | Cabeceras, OPTIONS, páginas protegidas, escape de HTML, `security.txt` |
| `test_vacantes.py` | Alta y listado de vacantes, empresas, auditoría |
| `test_roles.py` | Roles de Neon, permisos de Empresa y Administrador |
| `test_postulaciones.py` | Envío de CV, listado y descarga |
| `test_buzon.py` | Buzón de sugerencias: validaciones y categorías |
| `test_admin.py` | Health check, página de inicio por rol, panel y bandeja de sugerencias, logs |
| `test_restricciones.py` | Restricciones UNIQUE y CHECK de la base de datos |
| `test_comandos.py` | Comando `flask crear-usuario` |

Las fixtures comunes (usuarios por rol, vacante, clientes con sesión) están en `tests/conftest.py`. Cada prueba arranca con la base de datos vacía.

## Explicación de la arquitectura (para presentar el proyecto)

### Modelo–Vista–Controlador

Flask no impone un MVC "puro". En SIUT las piezas se reparten así:

| Concepto MVC | En SIUT | Dónde vive |
|---|---|---|
| **Modelo** | Clases SQLAlchemy (`Usuario`, `Alumno`, `Empresa`, `Vacante`, `Postulacion`, `PostulacionCV`, `Sugerencia`, `Auditoria`…) | `Models/models.py` |
| **Controlador** | Funciones de ruta de los Blueprints (`@vacantes_bp.route(...)`): reciben la petición, validan, usan el Modelo y responden | `Controllers/` |
| **Vista** | Páginas HTML estáticas + JavaScript que pide los datos a la API (`fetch`) y construye la página en el navegador | `Frontend/` |

SIUT **no** usa plantillas Jinja2: el servidor entrega HTML estático (solo reemplaza el nombre del usuario) y los datos viajan como JSON. Es una arquitectura de "API + frontend", donde la Vista vive en el navegador.

Flujo típico (postularse a una vacante):
1. El alumno llena el formulario; `empleos.js` envía un `POST /api/postulaciones` con el PDF.
2. El controlador valida sesión, rol, campos y que el archivo sea un PDF real de hasta 5 MB.
3. Crea la `Postulacion` y su `PostulacionCV` (el PDF) en una sola transacción y registra la auditoría.
4. Responde JSON; el navegador muestra el folio.

### Patrones de diseño

- **MVC** (adaptado a API + frontend), explicado arriba.
- **ORM / Data Mapper:** SQLAlchemy separa el objeto Python de su tabla; el modelo no sabe cómo se guarda.
- **Blueprints (modularización):** cada área (auth, vacantes, postulaciones, buzón) es un módulo independiente.
- **Decorator:** `@app.route`, `@app.before_request` (protección de páginas y cambio de contraseña obligatorio) y `@limiter.limit` (límite de intentos).
- **Singleton (implícito):** una sola instancia de `db = SQLAlchemy()` compartida por toda la app.
- **Control de acceso por rol:** el comportamiento cambia según el rol (Empresa ve las postulaciones de su empresa; Administrador, todas), y la base de datos lo refuerza con triggers y restricciones.

### ¿Qué es Neon?

Neon no es un framework ni un ORM: es un servicio de PostgreSQL en la nube (*Database as a Service*). SQLAlchemy solo apunta su cadena de conexión a Neon. Además de las tablas, Neon guarda reglas de negocio (roles válidos, máximo de administradores, quién puede publicar vacantes) y, en SIUT, también los CV en PDF.
