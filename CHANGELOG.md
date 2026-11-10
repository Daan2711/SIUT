# Changelog

Todos los cambios relevantes de SIUT se documentan en este archivo.

## [Sin publicar]

### Inicio de sesión registrado dos veces (2026-11-09)

#### Corregido
- **Doble envío del inicio de sesión:** en Render, verificar la contraseña tarda unos 2 segundos y el botón ENTRAR seguía activo sin indicar que se estaba procesando. Un segundo clic o Enter mandaba otro `POST /login`, así que la auditoría registraba dos «Inicio de sesión» separados unos 2 segundos. Además, la segunda sesión reemplazaba a la primera con un token CSRF nuevo, lo que podía provocar un 403 en «Nueva cuenta», y cada doble clic gastaba dos de los 5 intentos por minuto. Ahora se ignoran los envíos mientras hay uno en curso y el botón queda deshabilitado con el texto «Entrando…». Se vuelve a habilitar si hay un error o si el usuario regresa a la página con «Atrás». — `Frontend/js/login.js`
- **Doble envío del cambio de contraseña obligatorio:** se aplica el mismo bloqueo, con el texto «Guardando…». Un segundo envío respondía «debe ser distinta a la actual» aunque el cambio ya se hubiera guardado. También se toleran respuestas que no son JSON. — `Frontend/js/cambiar-password.js`
- Sin cambios en el servidor ni en Neon.

### URL real de Render en `security.txt` (2026-11-09)

#### Cambiado
- La línea `Canonical` de `security.txt` pasa a la URL real del despliegue: `https://siut-shap.onrender.com/.well-known/security.txt`. Antes apuntaba a `siut.onrender.com`, que es otro servicio con una versión antigua de SIUT. — `Frontend/.well-known/security.txt`
- Se marca como hecho ese paso de la lista posterior al despliegue. — `docs/DESPLIEGUE_RENDER.md`

### Alta de cuentas desde el panel de administrador (2026-11-09)

#### Agregado
- **Página «Nueva cuenta»** en la sección de administrador. Tiene un selector de rol limitado a Alumno, Profesor y Empresa y muestra solo los campos de cada rol, igual que las opciones del comando. Los campos de los otros roles quedan deshabilitados y no se envían. La contraseña temporal se escribe dos veces y la cuenta queda con cambio obligatorio en el primer inicio de sesión. — `Frontend/nueva-cuenta.html`, `Frontend/js/nueva-cuenta.js`
  - Enlace «Nueva cuenta» (solo visible para administradores) en el menú de las páginas de gestión, una tarjeta en el panel y el texto del panel actualizado. — `Frontend/panel-admin.html`, `Frontend/cargar-vacantes.html`, `Frontend/vacantes-publicadas.html`, `Frontend/postulaciones-recibidas.html`, `Frontend/sugerencias-admin.html`, `Frontend/css/style.css`
- **API de alta** (solo para un Administrador activo, leído de la base): `GET /api/admin/cuentas/formulario` (token CSRF, roles y semestres) y `POST /api/admin/cuentas` (límite de 20 por minuto). Responde 401 sin sesión, 403 a otros roles o sin CSRF, 400 en validaciones y 409 en duplicados. — `Controllers/cuentasController.py`, `app.py` (blueprint, ruta de la página y `PAGINAS_ADMINISTRADOR`)
- **Protección CSRF** con un token por sesión que viaja en la cabecera `X-CSRF-Token` y se compara en tiempo constante, sin dependencias nuevas. Por ahora la usa solo este formulario. — `csrf.py`

#### Cambiado
- **Lógica de alta compartida:** las validaciones, la revisión de duplicados y el alta en una sola transacción salen del comando a `preparar_cuenta()` y `guardar_cuenta()`. El comando y la web usan el mismo código; el comando conserva sus opciones y su comportamiento y, en los errores, indica la opción que hay que corregir. — `servicios/cuentas.py`, `servicios/__init__.py`, `comandos.py`
- El modelo `Profesor` declara `usuario_id` y `num_empleado` únicos, como ya lo están en Neon (`profesores_*_key`). No cambia Neon. — `Models/models.py`
- La documentación indica los dos caminos de alta. — `README.md`, `docs/DESPLIEGUE_RENDER.md`
- Descripción del PR guardada en el repositorio. — `docs/PR-alta-cuentas-admin.md`

#### Seguridad
- **Desde la web no se crean administradores:** el formulario no ofrece el rol y el servidor rechaza `rol=Administrador` (o cualquier rol fuera de la lista blanca) aunque llegue en la petición. Los administradores se siguen creando solo con `flask crear-usuario`.
- **Duplicados de correo, matrícula, número de empleado o empresa:** se responden con mensajes amigables, también si dos envíos simultáneos llegan a la restricción UNIQUE de la base. El texto de PostgreSQL solo se escribe en el log.
- **Registro:** el log de la app indica qué administrador creó qué cuenta (ids, rol y correos, sin la contraseña) y la auditoría guarda `Alta de usuario (web)` con el id del administrador; `usuarios.creado_por` también lo registra.

#### Corregido
- **El primer envío de «Nueva cuenta» podía fallar con 403** («La sesión del formulario expiró»). Se detectó en la prueba manual. Al abrir la página se piden a la vez `/api/admin/cuentas/formulario`, que guardaba el token CSRF en la cookie de sesión, y `/usuario-actual`, que también reescribe esa cookie porque la sesión se renueva en cada petición. Si la segunda respuesta llegaba al final, la cookie quedaba sin el token. Ahora el token se crea al iniciar sesión, así que ya viaja en la cookie desde la primera página. `token_csrf()` lo sigue creando si falta, para las sesiones abiertas antes del cambio. — `csrf.py`, `Controllers/authController.py`

#### Pruebas
- Prueba de regresión que simula la respuesta simultánea (reponer la cookie previa al pedir el token); falla sin la corrección. Otra prueba comprueba que cada inicio de sesión recibe un token nuevo. — `tests/test_cuentas_admin.py`
- 44 casos nuevos:
  - alta por rol y perfil creado;
  - duplicados, incluidos los que llegan a la base;
  - validaciones por rol y contraseñas distintas;
  - acceso sin sesión, de Alumno, de Empresa y de un administrador desactivado;
  - intento de crear un Administrador o un rol desconocido;
  - CSRF ausente, falso o de otra sesión;
  - log sin la contraseña.

  En total son 214 casos (46 de ellos en este archivo). — `tests/test_cuentas_admin.py`

### Corrección de la función `validar_perfiles_usuario()` en Neon (2026-11-09)

#### Corregido
- **No se podían crear cuentas ni cambiar contraseñas en Neon.** `flask crear-usuario` fallaba con `record "old" has no field "usuario_id"`. La función `validar_perfiles_usuario()` la comparten 3 triggers (en `usuarios`, `alumnos` y `profesores`), y en la condición `TG_TABLE_NAME IN ('alumnos','profesores') AND TG_OP = 'UPDATE' AND OLD.usuario_id IS DISTINCT FROM NEW.usuario_id` PL/pgSQL resolvía `OLD.usuario_id` también cuando el trigger corría sobre `usuarios`, que no tiene esa columna. Todo INSERT o UPDATE en `usuarios` fallaba al confirmar la transacción (incluido `/cambiar-password`).
  - La comparación pasa a un `IF` anidado que solo se evalúa en UPDATE de `alumnos`/`profesores`; el resto de la función no cambia.
  - La función se había creado directamente en Neon (no estaba en el repositorio ni en el historial de git); ahora queda versionada. — `migrations/2026-11-09_corregir_validar_perfiles_usuario.sql` y su script para revertir (con la definición original copiada de Neon).
  - **Aplicada en Neon** el 2026-11-09: ensayo con rollback, aplicación y verificación en solo lectura (la definición en Neon es idéntica a la del archivo; los 3 triggers siguen activos; no cambió ningún otro objeto ni dato).
  - Verificada antes en un PostgreSQL 18.6 local con las definiciones exactas de Neon: con la función original fallaban crear un administrador, actualizar un usuario y crear un alumno con su perfil; con la corrección funcionan, y las reglas de perfiles siguen rechazando alumnos sin perfil, empresas sin empresa y mover un perfil dejando a su dueño sin él.

#### Cambiado
- Los ejemplos del comando usan `python -m flask --app app crear-usuario`: en Windows `flask` suele no estar en el PATH. Nota sobre ejecutarlo en una terminal (la contraseña oculta no funciona por tubería en Windows). — `docs/DESPLIEGUE_RENDER.md`, `comandos.py`

#### Pruebas
- Prueba de regresión que revisa la migración: `OLD.usuario_id` solo se compara dentro del `IF` anidado. 168 casos en total. — `tests/test_restricciones.py`

### Inscripción a eventos restaurada (2026-11-09)

#### Corregido
- **Se restauró el flujo de inscripción a eventos**, borrado por error en la Fase C. En `main` los botones "Inscríbete aquí" apuntaban a `#`, por lo que `inscripcion.html` y `confirmacion_inscripciones.html` parecían huérfanas; la rama `master` mostró que los botones debían llevar a `inscripcion.html` (commit `bd01fae`). — `Frontend/inscripcion.html`, `Frontend/confirmacion_inscripciones.html` (recuperadas del historial, idénticas a `master`)
  - Los 3 botones de eventos de la página de inicio enlazan a `inscripcion.html`, como en `master`, con `rel="noopener"` por abrir en otra pestaña. — `Frontend/index.html`
  - El formulario envía a `confirmacion.html`, la última decisión de su autor (commit `63dba37`); `confirmacion_inscripciones.html` se conserva tal como estaba.

#### Seguridad
- El formulario de inscripción es estático (no guarda datos) y usa GET: sus campos ya no llevan `name`, así que el nombre y el correo no viajan en la URL ni quedan en los logs de acceso del servidor. Siguen siendo obligatorios. — `Frontend/inscripcion.html`

#### Pruebas
- 3 casos nuevos en `tests/test_seguridad.py` (enlaces de eventos, sesión obligatoria y formulario sin datos personales en la URL). 167 casos en total.

### Fusión de `origin/main` en `fix/auditoria-seguridad` (2026-11-09)

`main` traía 2 commits: `ac2aed9` ("Actualizacion del proyecto SIUT", la versión original de la funcionalidad de vacantes, aplicada sobre archivos anteriores a la auditoría) y `52da768` (borrado del Gantt).

#### Resolución de conflictos
- **Se conservó la versión de la rama** en `Controllers/vacantesController.py`, `Models/models.py`, `app.py`, `Frontend/cargar-vacantes.html`, `Frontend/vacantes-publicadas.html`, `Frontend/js/cargar-vacantes.js` y `Frontend/js/empleos.js`: contienen la misma funcionalidad de vacantes, ya corregida y ampliada. La versión de `main`:
  - escribía la `SECRET_KEY` en el código (`app.py`) y no tenía las correcciones de seguridad;
  - daba 500 al publicar una vacante, usaba el rol `Reclutador` (que Neon no admite) y no tenía `Empresa`, postulaciones ni CV en sus modelos.
- Se descartó el cambio de `main` que reemplazaba "Buscar empleos" por "Cargar empleos" en el menú del alumno: lo sustituyen la página de inicio por rol y el menú de gestión.
- **`Frontend/css/style.css`: unión de ambas.** De `main`, el diseño original de las páginas de vacantes (columna de vista previa de 340 px, márgenes del formulario, vista previa sin animación ni cursor de enlace, estilo de la fecha de publicación y botones a lo ancho en celular). De la rama, los estilos de postulaciones, panel, sugerencias y menú en celular. `.titulo-header` ya no se usa y no se conservó.
- **Se aceptó el borrado de `Gantt_Proyecto_Integrador_plantilla.xlsx`** hecho en `main`.

#### Verificación
- 165 pruebas pasan; el diagnóstico del frontend no encuentra referencias rotas.

### Preparación para Render — Fase C: detalles técnicos (2026-11-08)

#### Agregado
- **Menú en celulares.** Botón ☰ en las 11 páginas con menú; en pantallas de hasta 900 px el menú se despliega debajo del encabezado. `nav.js` (que ninguna página cargaba) ahora se usa y anuncia el estado a lectores de pantalla (`aria-expanded`); se cierra al elegir una opción o con Escape. — `Frontend/*.html`, `Frontend/js/nav.js`, `Frontend/css/style.css`

#### Cambiado
- **Caché de 1 hora para CSS, JS e imágenes** (`public, max-age=3600`); antes se descargaban en cada página. HTML y API siguen sin caché porque dependen de la sesión. — `app.py`
- **SQLite local funciona sin ajustes**: la conversión de `BigInteger` a `INTEGER` (necesaria para el autoincremento en SQLite) pasó de las pruebas a `Database/database.py`. No afecta a PostgreSQL. — `Database/database.py`, `tests/conftest.py`
- **`README.md` reescrito** con la arquitectura real (API JSON + HTML estático, sin Jinja2, Bootstrap ni WeasyPrint), roles, estructura, desarrollo local, pruebas y la explicación para presentar el proyecto, corregida.
- `docs/DESPLIEGUE_RENDER.md`: nota sobre la caché tras un despliegue.

#### Corregido
- `index.html` no cerraba la etiqueta `<body>`.
- `soporte.html` cargaba `usuario.js`, que fallaba porque la página no tiene los elementos que busca (el nombre ya lo pone el servidor).

#### Eliminado
- Páginas huérfanas sin ningún enlace: `inscripcion.html` y `confirmacion_inscripciones.html`.
- `Frontend/js/usuario.js` (solo lo usaba `soporte.html`).
- El carrusel `app.js` en las páginas que no lo tienen (`buzon.html`, `cargar-vacantes.html`, `vacantes-publicadas.html`).

#### Pruebas
- 14 casos nuevos en `tests/test_seguridad.py` (caché, botón del menú en celular y archivos eliminados). 165 casos en total.

### Preparación para Render — Fase B: importantes (2026-11-08)

#### Agregado
- **Navegación por rol.** El login devuelve la página de inicio del rol (`destino`): `Alumno` → `index.html`, `Empresa` → `vacantes-publicadas.html`, `Administrador` → `panel-admin.html`. — `Controllers/vacantesController.py` (`pagina_inicio`), `Controllers/authController.py`, `Frontend/js/login.js`
- **Menú y cierre de sesión en las páginas de gestión** (cargar vacante, vacantes publicadas, postulaciones, panel y sugerencias). Los enlaces exclusivos del administrador se muestran solo a ese rol; el servidor los bloquea igualmente a los demás. — `Frontend/*.html`, `Frontend/js/gestion.js` (nuevo)
- **Panel de administración** con el total de vacantes activas, postulaciones y sugerencias por atender. — `Frontend/panel-admin.html`, `Frontend/js/panel-admin.js` (nuevos)
- **Bandeja de sugerencias para el administrador**: lista con filtro por estado, cambio de estado (Recibida, En revisión, Atendida, Rechazada) y respuesta; registra quién y cuándo la atendió, y lo audita. — `GET /api/sugerencias`, `POST /api/sugerencias/<id>` en `Controllers/buzonController.py`; `Frontend/sugerencias-admin.html`, `Frontend/js/sugerencias-admin.js` (nuevos)
- **`/healthz`**: health check para Render; comprueba también la conexión con la base de datos (503 si falla, sin detalles al cliente). — `app.py`
- **`render.yaml`** (Blueprint: Docker, plan gratis, región Ohio como Neon, health check y variables de entorno) y **`docs/DESPLIEGUE_RENDER.md`** (guía paso a paso, alta de cuentas y limitaciones del plan gratis).

#### Cambiado
- **Los errores se registran en el log.** Los 7 bloques que devolvían 500 ahora llaman a `logger.exception` (con la traza completa); el cliente sigue sin ver detalles internos. Nivel configurable con `LOG_LEVEL`. — `app.py`, `Controllers/*.py`
- **`db.create_all()` solo bajo demanda** (`AUTO_CREATE_TABLES=true`, para bases locales). La app ya no intenta crear tablas en Neon al arrancar; el esquema lo controlan los scripts de `migrations/`. — `app.py`
- **gunicorn**: 2 workers (`WEB_CONCURRENCY`), timeout de 60 s y logs de acceso y error a la salida estándar. — `Dockerfile`
- El modelo `Sugerencia` declara el CHECK `chk_sugerencia_estado` de Neon. — `Models/models.py`
- `docs/ESQUEMA_BD.md` regenerado desde Neon (solo lectura): 20 tablas, con `postulacion_cv`.

#### Pruebas
- `tests/test_admin.py`: 22 casos (health check, página de inicio por rol, acceso a páginas de administrador, menú de gestión, bandeja de sugerencias y que los errores 500 queden en el log sin llegar al cliente). 151 casos en total.

### Preparación para Render — Fase A: bloqueantes (2026-11-08)

#### Cambiado
- **Los CV se guardan en Neon, no en disco.** El plan gratis de Render no tiene disco persistente, así que los CV guardados en el servidor se perdían en cada despliegue o reinicio.
  - El PDF va en la tabla nueva `postulacion_cv` (una fila por postulación, máximo 5 MB), en la misma transacción que la postulación: si algo falla no queda nada a medias. La descarga lo lee de la base de datos. — `Models/models.py`, `Controllers/postulacionesController.py`
  - Se eliminó la escritura en disco y la variable `UPLOAD_DIR`; el contenedor ya no crea `instance/uploads/`. — `app.py`, `Dockerfile`
  - Migración SQL versionada, idempotente y solo aditiva (crea una tabla), con su script para revertir. — `migrations/2026-11-08_postulacion_cv.sql`, `migrations/2026-11-08_postulacion_cv_revertir.sql`
- **Conexión estable con Neon.** `pool_pre_ping` y `pool_recycle`: Neon suspende la base tras unos minutos sin uso y cierra las conexiones, lo que provocaba un 500 en la primera petición después de la pausa. — `app.py`

#### Agregado
- **Comando `flask crear-usuario`** para dar de alta cuentas en producción (no había forma de crearlas: el registro público está deshabilitado y Neon tenía 0 usuarios). — `comandos.py`, `app.py`
  - Crea en una sola transacción la cuenta y lo que su rol exige en Neon: perfil de alumno o de profesor, empresa (nueva o existente) o nada para administradores.
  - Valida correo, largos de columna, duplicados (correo, matrícula, número de empleado, una cuenta Empresa por empresa) y contraseña de al menos 8 caracteres; la contraseña se pide oculta y con confirmación.
  - Muestra la base de datos destino (sin credenciales) y pide confirmación antes de escribir. La cuenta queda con cambio de contraseña obligatorio.
  - Se ejecuta desde un equipo local con el `DATABASE_URL` de Neon, porque el plan gratis de Render no tiene consola.

#### Pruebas
- Las pruebas de postulaciones verifican que el PDF se guarda en la base de datos byte por byte y que la descarga devuelve el mismo archivo. — `tests/test_postulaciones.py`, `tests/test_restricciones.py`, `tests/conftest.py`
- `tests/test_comandos.py`: 19 casos del comando, incluido que sus mensajes se puedan mostrar en la consola de Windows (cp1252), error encontrado al probar el comando real. 129 casos en total.

### Documentación del esquema de la base de datos (2026-11-08)

#### Agregado
- **`docs/ESQUEMA_BD.md`**: esquema real de Neon (PostgreSQL 18), generado leyendo el catálogo en modo solo lectura. Incluye:
  - diagrama entidad-relación (Mermaid);
  - las reglas de negocio que impone la base de datos (CHECK, índices únicos y triggers);
  - el detalle de las 19 tablas: columnas, tipos, valores por defecto, llaves y restricciones.

  Refleja la base de datos, no `Models/models.py`; si el esquema de Neon cambia, hay que regenerarlo. — `docs/ESQUEMA_BD.md`
- **`docs/PR-14-auditoria-seguridad.md`**: descripción del PR #14 (resumen de cambios por fase, pruebas y lista de pasos antes de desplegar). — `docs/PR-14-auditoria-seguridad.md`

### Compatibilidad con los triggers de Neon (2026-11-08)

#### Eliminado
- **`VACANTES_EMAILS`.** El trigger `trg_validar_creador_vacante` de Neon solo acepta como creador de una vacante a un `Administrador` (cualquier empresa) o a una `Empresa` (la suya). Un usuario autorizado solo por correo nunca podía publicar: Neon rechazaba el INSERT y la app respondía 500. Ahora el permiso para publicar vacantes, ver postulaciones y descargar CV depende únicamente de los roles `Empresa` y `Administrador`; cualquier otro perfil no ve ninguna postulación. — `Controllers/vacantesController.py`

#### Corregido
- **Las vacantes con títulos largos no se guardaban.** `auditoria.accion` es `varchar(100)` en Neon, pero se guardaba `"Alta de vacante #ID: <título>"` (recortado a 255). Con títulos de unos 78 caracteres o más fallaba el registro de auditoría y, con él, toda la transacción de la vacante (500). Ahora `accion` es un texto corto y fijo y el detalle va en `descripcion` (`text`). — `Controllers/vacantesController.py`
- Mismo formato para el resto de la auditoría: `accion` = "Postulación a vacante" (con la vacante en `descripcion`) y "Descarga de CV". — `Controllers/postulacionesController.py`
- `Auditoria.accion` y `Auditoria.tabla_afectada` se declaran como `String(100)`, igual que en Neon. — `Models/models.py`

#### Pruebas
- **Réplicas en SQLite de reglas de Neon**, solo para las pruebas: el trigger `trg_validar_creador_vacante` y el límite de 100 caracteres de `auditoria`. Comprobado: con el código anterior de auditoría, las pruebas nuevas fallan igual que fallaría Neon. — `tests/conftest.py`
- Se reemplazaron las 3 pruebas de `VACANTES_EMAILS` y se agregaron casos de título de 150 caracteres, de que todas las acciones auditadas caben en 100 y de que la base rechaza vacantes de roles sin permiso o de una empresa ajena. 108 casos en total. — `tests/test_vacantes.py`, `tests/test_roles.py`, `tests/test_restricciones.py`

### Docker: código de solo lectura para la app (2026-11-08)

#### Corregido
- **El usuario del contenedor podía modificar el código.** `COPY --chown=appuser` le daba la propiedad de todo `/app`, aunque la Fase 4 indicaba que solo podría escribir en `instance/`. Ahora el código queda propiedad de root; `appuser` puede leerlo pero no modificarlo ni crear archivos, y solo escribe en `instance/` (carpeta de CV). — `Dockerfile`

#### Verificado (primer build real de la imagen)
- La imagen se construye con las versiones fijadas de `requirements.txt` (incluido `gunicorn==26.2.0`) sobre `python:3.12-slim`.
- Corre como `appuser` (uid 10001), sin `.env` dentro de la imagen; gunicorn arranca sin errores.
- Respuestas: `/login` 200, `/.well-known/security.txt` 200, `/security.txt` 301, `/index.html` sin sesión 302 → `/login`.
- Las 103 pruebas de pytest pasan dentro del contenedor (Linux, como `appuser`).

### Permisos de vacantes por roles reales de Neon (2026-11-08)

#### Corregido
- **Nadie podía publicar vacantes por rol en Neon.** El código daba permiso al rol `Reclutador`, pero la restricción `chk_usuarios_rol` de Neon solo admite `Alumno`, `Profesor`, `Empresa` y `Administrador`. Las pruebas no lo detectaban porque SQLite no tenía ese `CHECK`. — `Controllers/vacantesController.py`

#### Cambiado
- **Quién publica vacantes y cómo se asigna la empresa:** — `Controllers/vacantesController.py`
  - `Empresa`: publica siempre a nombre de su propia empresa (`empresa_id` del usuario); el campo `empresa` del formulario se ignora y no es obligatorio.
  - `Administrador`: publica para cualquier empresa (se busca o se crea por nombre).
  - Correo en `VACANTES_EMAILS`: igual que el administrador.
- **Quién ve las postulaciones y descarga los CV:** — `Controllers/postulacionesController.py`
  - `Empresa`: las de las vacantes de su empresa, aunque las haya publicado un administrador.
  - `Administrador`: todas.
  - Correo autorizado: las de las vacantes que publicó.
- `/usuario-actual` devuelve la empresa del usuario (`empresa: {id, nombre}` o `null`). — `Controllers/authController.py`
- En `cargar-vacantes.html`, si el usuario es `Empresa`, el campo empresa se llena con la suya y queda de solo lectura (también tras "Limpiar"). — `Frontend/js/cargar-vacantes.js`
- Los modelos declaran las restricciones de rol de Neon: `chk_usuarios_rol`, `chk_usuario_empresa` (solo `Empresa` lleva `empresa_id`, y siempre) y el índice `uq_usuario_empresa` (un usuario `Empresa` por empresa). Así las pruebas fallan si se vuelve a usar un rol que Neon no acepta. — `Models/models.py`

#### Pruebas
- `tests/test_roles.py`: 14 casos (restricciones de rol, publicación y visibilidad por rol, `/usuario-actual`). El fixture `reclutador` pasa a ser un usuario `Empresa` real y se agregan `administrador`, `crear_empresa` y `crear_usuario_empresa`. 103 casos en total. — `tests/`

### Restricciones UNIQUE declaradas en los modelos (2026-11-08)

Un diagnóstico de solo lectura en Neon mostró que las restricciones **ya existían** en la base de datos y que no hay duplicados. No se modificó Neon; se alineó el código con ella.

#### Cambiado
- Los modelos declaran las restricciones existentes en Neon, con los mismos nombres, para que `create_all` y las pruebas las incluyan. — `Models/models.py`
  - `usuarios`: índice único `uq_usuarios_email` sobre `lower(email)`.
  - `alumnos`: `usuario_id` único (un registro de alumno por usuario) y `matricula` única.
  - `postulaciones`: `uq_alumno_vacante (alumno_id, vacante_id)`.

#### Corregido
- **Dos envíos simultáneos de la misma postulación devolvían 500.** El segundo chocaba con `uq_alumno_vacante` y caía en el manejo genérico de errores. Ahora responde 409 ("Ya te postulaste a esta vacante") y borra el CV que ya se había guardado. — `Controllers/postulacionesController.py`

#### Pruebas
- `tests/test_restricciones.py`: 5 casos (correo sin distinguir mayúsculas, alumno por usuario, matrícula, postulación única y envío simultáneo → 409 sin archivo huérfano).

### Login: mensajes de error correctos con respuestas no JSON (2026-11-08)

#### Corregido
- Si el servidor respondía algo que no era JSON (por ejemplo, una página de error HTML del proxy durante un despliegue), `response.json()` fallaba y el usuario veía "Error de conexión con el servidor". Ahora la respuesta se lee de forma segura y, si no trae un mensaje propio, se muestra uno según el código HTTP (401, 429 o 5xx). "Error de conexión" queda solo para cuando no hay respuesta. — `Frontend/js/login.js`

### Pruebas automatizadas con pytest (2026-11-08)

#### Agregado
- **Suite de pytest con 84 casos** en `tests/`, a partir de las pruebas de humo usadas durante las fases 1 a 4, con algunos casos de validación nuevos (campos de vacante, CV vacío, cuenta inactiva, logout, etc.).
  - `conftest.py`: fija las variables de entorno antes de importar la app (SQLite temporal, `UPLOAD_DIR` temporal, sin `VACANTES_EMAILS` ni `TEMP_PASSWORD`), así que nunca toca Neon ni depende del `.env`. Cada prueba arranca con la base de datos, el límite de intentos y la carpeta de CV limpios.
  - Archivos por tema: `test_auth.py`, `test_seguridad.py`, `test_vacantes.py`, `test_buzon.py`, `test_postulaciones.py`.
- `pytest.ini` y `requirements-dev.txt` (`pytest==8.4.2`).
- Sección "Pruebas automatizadas" en el `README.md`.

### Fase 4 — Limpieza (2026-11-08)

#### Eliminado
- `Models/user.py`: modelo `Usuario` duplicado sobre la tabla `Alumnos`, sin uso.
- `Frontend/js/empleos copy.js`: su lógica (carga de vacantes desde la API) ya está en `empleos.js`.
- `.gitignore_respaldo` y `Frontend/contacto.html` (página vacía).
- `.vscode/`: configuración con la ruta personal de otra persona y una solución .NET inexistente.
- `Frontend/security.txt`: duplicado con un contacto distinto. `/security.txt` ahora redirige (301) a `/.well-known/security.txt`. — `app.py`

#### Corregido
- `security.txt`: un solo contacto (`soporte@virtual.utsc.edu.mx`), `Expires` con formato válido (`…T00:00:00.000Z`) y `Content-Type` con `charset=utf-8`. — `Frontend/.well-known/security.txt`, `app.py`

#### Cambiado
- `.gitignore`: se reemplazó la plantilla de Visual Studio por una de Python (`__pycache__`, entornos virtuales, `.env*`, `instance/`, editores).
- `requirements.txt`: versiones fijadas a las probadas en desarrollo (Flask 3.1.0, Werkzeug 3.1.3, Flask-SQLAlchemy 3.1.1, SQLAlchemy 2.0.37, psycopg2-binary 2.9.13, python-dotenv 1.2.4, gunicorn 26.2.0, Flask-Bcrypt 1.0.1, Flask-Limiter 3.12).
- `Dockerfile`: el contenedor corre con un usuario sin privilegios (`appuser`, uid 10001), con permiso de escritura solo en `instance/` para los CV.

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
| ~~`VACANTES_EMAILS`~~ | — | **Eliminada el 2026-11-08** (ver "Compatibilidad con los triggers de Neon"). Era: correos autorizados a publicar vacantes además del rol `Reclutador`. |
| `TEMP_PASSWORD` | No | Contraseña temporal institucional que no podrá elegirse como nueva. |
| `PROXY_HOPS` | No (recomendada en Render: `1`) | Proxies de confianza para leer la IP real del cliente. `0` en local. |
| `RATELIMIT_STORAGE_URI` | No | Almacenamiento del límite de intentos. Por defecto `memory://` (por worker); usar `redis://...` para un límite global. |

#### Dependencias
- Se agregó `flask-limiter`.
