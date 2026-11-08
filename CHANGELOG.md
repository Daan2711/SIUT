# Changelog

Todos los cambios relevantes de SIUT se documentan en este archivo.

## [Sin publicar]

### Fase 3 — Funcionalidades: postulaciones y buzón de sugerencias (2026-11-08)

#### Agregado
- **Postulación con CV.** `POST /api/postulaciones` (multipart) recibe la vacante, habilidades, experiencia, mensaje, datos de contacto y el CV. — `Controllers/postulacionesController.py` (nuevo)
  - El CV debe ser PDF de hasta 5 MB. Además de la extensión se verifica el contenido real del archivo (que empiece con `%PDF-`).
  - El archivo se guarda en disco como `<uuid>.pdf` en `UPLOAD_DIR` (por defecto `instance/uploads/cv/`), fuera de `Frontend/`, así que no es accesible públicamente. Si falla la base de datos, el archivo se borra.
  - Solo pueden postularse usuarios con registro en `alumnos`. No se permite postularse dos veces a la misma vacante (409).
  - Teléfono, carrera y semestre se actualizan en el perfil del alumno. Nombre, correo y matrícula salen de la cuenta y no se pueden editar desde el formulario.
- **Postulaciones recibidas (reclutador).** — `Controllers/postulacionesController.py`, `Frontend/postulaciones-recibidas.html` y `Frontend/js/postulaciones-recibidas.js` (nuevos)
  - `GET /api/postulaciones` lista solo las postulaciones de las vacantes que publicó el usuario.
  - `GET /api/postulaciones/<id>/cv` descarga el PDF; solo el dueño de la vacante puede hacerlo y cada descarga queda en auditoría.
  - Página con filtro por vacante, enlazada desde `vacantes-publicadas.html`.
- **Buzón de sugerencias en página propia** (`sugerencias.html`), con el formulario original, SweetAlert2 desde cdnjs con SRI y límites de longitud iguales a los del servidor. Enlace "Buzón de sugerencias" en el menú de todas las páginas. — `Frontend/sugerencias.html` (nuevo), `Frontend/*.html`
- **`/usuario-actual`** devuelve también los datos del alumno (o `null`) y si el usuario puede cargar vacantes. — `Controllers/authController.py`
- Rutas que muestran el nombre real del usuario en `sugerencias.html`, `cargar-vacantes.html`, `vacantes-publicadas.html` y `postulaciones-recibidas.html`. — `app.py`
- Estilos para las páginas de vacantes y postulaciones, que no tenían CSS. — `Frontend/css/style.css`

#### Cambiado
- **Bolsa de empleo (`buzon.html`) carga las vacantes desde la API.** Se quitaron las 4 tarjetas de ejemplo, que no existían en la base de datos. Los favoritos se identifican por id de vacante. — `Frontend/buzon.html`, `Frontend/js/empleos.js`
- **Formulario de postulación**: datos de la cuenta precargados (solo lectura), campo de CV con validación de tipo y tamaño en el navegador, y envío como `multipart/form-data` con el `vacante_id`. — `Frontend/buzon.html`, `Frontend/js/empleos.js`

#### Configuración
- `MAX_CONTENT_LENGTH` = 6 MB; las peticiones más grandes responden 413 con mensaje JSON. — `app.py`
- Nueva variable opcional `UPLOAD_DIR` (carpeta de los CV). `instance/` añadida a `.gitignore` y `.dockerignore`.
- ⚠️ **Render**: el disco se borra en cada despliegue. Para conservar los CV hay que montar un *Persistent Disk* y apuntar `UPLOAD_DIR` a él. En Docker local, `docker-compose.yml` ya monta el proyecto, así que `instance/` se conserva.

### Fase 2 — Seguridad y consistencia (2026-11-08)

#### Seguridad
- **Páginas HTML protegidas.** Toda página `.html` exige sesión (redirige a `/login`), salvo `login.html` y `cambiar-password.html`. `cargar-vacantes.html` y `vacantes-publicadas.html` exigen además permiso para cargar vacantes (si no, redirigen a `/index.html`). La comprobación no distingue mayúsculas. — `app.py`
- **Permiso de vacantes leído de la base de datos.** `puede_cargar_vacantes()` consulta rol, correo y estado `activo` del usuario en cada llamada; un cambio de rol o una baja surten efecto de inmediato. — `Controllers/vacantesController.py`
- **Nombre escapado al insertarlo en el HTML** para evitar XSS. — `app.py`
- **Buzón sin fuga de errores internos**: los 500 devuelven un mensaje genérico en lugar del texto de la excepción. — `Controllers/buzonController.py`
- **SRI en html2pdf** (`integrity` + `crossorigin`), hash verificado contra el archivo de cdnjs. — `Frontend/horario.html`

#### Corregido
- **Buzón: validación de entrada.** Límites de longitud alineados con las columnas (nombre 100, grupo 50, área "Otro" 100, descripción 2000), cuerpo JSON obligatorio, y todo el guardado (incluido el `flush`) dentro de la transacción. — `Controllers/buzonController.py`
- **Buzón: categorías controladas.** Solo existen Sistemas, Infraestructura, Mantenimiento, Escolares y Otro. El texto libre de "Otro" se guarda al inicio de la descripción (`[Área indicada: …]`) en vez de crear una categoría nueva. — `Controllers/buzonController.py`
- **La sesión ahora expira a los 30 minutos** (`session.permanent = True`); antes `PERMANENT_SESSION_LIFETIME` no se aplicaba. — `Controllers/authController.py`
- **Cerrar sesión maneja errores**: si el servidor falla se avisa al usuario en lugar de redirigir como si hubiera cerrado. — `Frontend/js/index.js`, `Frontend/js/usuario.js`

### Fase 1 — Correcciones críticas (2026-11-08)

#### Corregido
- **Alta de vacantes fallaba siempre (500).** `POST /api/vacantes` pasaba `empresa` (texto) al modelo `Vacante`, que no tiene esa columna, y no asignaba `empresa_id` (obligatorio). Ahora la empresa se busca por nombre (sin distinguir mayúsculas) o se crea en `empresas`, y todo el alta ocurre dentro de la transacción. — `Controllers/vacantesController.py`
- **Listado de vacantes** obtiene el nombre de la empresa con un join a `empresas`; antes leía `v.empresa`, que no existe. — `Controllers/vacantesController.py`
- **Fecha `publicada_en`** se enviaba mal formada (`+00:00Z`) y salía de `creado_en`; ahora es ISO 8601 válida y usa `publicada_en`. — `Controllers/vacantesController.py`
- **Peticiones `OPTIONS` devolvían 500**: el `after_request` regresaba una tupla en lugar de un objeto Response. Ahora responden 405 con cabecera `Allow`. — `app.py`
- **Cabeceras de seguridad duplicadas**: se unificaron los dos `after_request` en uno. HSTS solo se envía cuando `COOKIE_SECURE=true` (HTTPS). — `app.py`

#### Seguridad
- **Cambio de contraseña obligatorio validado en el servidor.** Mientras `primer_login` sea verdadero, solo se permiten login, logout, `/usuario-actual`, `/cambiar-password` y archivos CSS/JS/imagen; las APIs responden 403 y las páginas redirigen a `/cambiar-password`. — `app.py`, `Controllers/authController.py`
- **Contraseña temporal fuera del código.** Se eliminó `UTSC2026` del backend y del frontend. Se rechaza una nueva contraseña igual a la actual y, opcionalmente, igual a `TEMP_PASSWORD` (variable de entorno). — `Controllers/authController.py`, `Frontend/js/cambiar-password.js`
- **Límite de intentos en `/login`**: 5 por minuto por IP + correo (Flask-Limiter). Al exceder responde 429 con mensaje JSON. — `extensions.py` (nuevo), `app.py`, `Controllers/authController.py`, `requirements.txt`
- **Permiso para publicar vacantes**: se quitó el correo por defecto `cargar_vacantes@empresa.com`; sin `VACANTES_EMAILS` solo publica el rol `Reclutador`. — `Controllers/vacantesController.py`

#### Configuración nueva (variables de entorno)
| Variable | Obligatoria | Descripción |
|---|---|---|
| `VACANTES_EMAILS` | No | Correos (separados por coma) autorizados a publicar vacantes además del rol `Reclutador`. |
| `TEMP_PASSWORD` | No | Contraseña temporal institucional que no podrá elegirse como nueva. |
| `PROXY_HOPS` | No (recomendada en Render: `1`) | Proxies de confianza para leer la IP real del cliente. `0` en local. |
| `RATELIMIT_STORAGE_URI` | No | Almacenamiento del límite de intentos. Por defecto `memory://` (por worker); usar `redis://...` para un límite global. |

#### Dependencias
- Se agregó `flask-limiter`.
