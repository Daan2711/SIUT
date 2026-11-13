# Changelog

Todos los cambios relevantes de SIUT se documentan en este archivo.

## [Sin publicar]

### Corregido: el código de recuperación no salía desde Render (2026-11-12)

#### Corregido
- **El correo con el código no se enviaba en producción.** El log de Render mostró un error no capturado dentro de `_enviar`; la causa probable es que el valor de `BREVO_API_KEY` pegado en Render traía un carácter que no se puede mandar en una cabecera HTTP (por ejemplo, un salto de línea). La llamada fallaba antes de llegar a Brevo con un error que no se capturaba: el envío en segundo plano se detenía sin el mensaje «No se pudo enviar el código de recuperación». Con la misma clave en `.env` local el envío sí funcionaba. — `servicios/correo.py`, `Controllers/recuperacionController.py`
  - `BREVO_API_KEY`, `CORREO_REMITENTE` y `NOMBRE_REMITENTE` se usan sin espacios ni saltos de línea al inicio o al final.
  - Si la clave tiene caracteres no válidos en medio, no se llama a Brevo y el log dice «BREVO_API_KEY tiene caracteres no válidos (¿se copió con saltos de línea o espacios?)», sin mostrar la clave.
  - Cualquier otro error al llamar a Brevo, o al enviar en segundo plano, queda en el log con el prefijo «No se pudo enviar el código de recuperación (usuario N)» y solo el tipo de error, sin el código, el correo ni la clave.

#### Pruebas
- Variables con espacios y saltos de línea, clave con caracteres no válidos (salto de línea, espacio, carácter invisible o acento), solo espacios equivale a no configurado, error inesperado al llamar a Brevo, respuesta que no es 2xx y error inesperado en segundo plano sin datos sensibles en el log. — `tests/test_recuperar_password.py`

### Recuperación de contraseña con código por correo (2026-11-12)

#### Agregado
- **«¿Olvidaste tu contraseña?» en el login** abre una ventana: «¿Estás seguro de querer recuperar la contraseña?» con **Recuperar contraseña** y **En otro momento** (cierra y deja el login como estaba). Después pide el correo (rellenado con el del login), el **código de 4 dígitos** que llega por correo y la **nueva contraseña con su confirmación** (con el botón para mostrarla). «Reenviar código» se habilita a los 60 segundos. Al terminar vuelve al login con «Contraseña actualizada». — `Frontend/login.html`, `Frontend/js/recuperar.js`, `Frontend/css/style.css`
- **Endpoints** `POST /recuperar-password/solicitar`, `/verificar` y `/restablecer`. — `Controllers/recuperacionController.py`, `app.py`
  - El código vence a los 10 minutos, se anula con 5 intentos fallidos y pedir uno nuevo anula el anterior. Se guarda cifrado con bcrypt.
  - La respuesta de «solicitar» es la misma exista o no el correo (o esté desactivada la cuenta), y el correo se envía en segundo plano para que el tiempo de respuesta tampoco lo delate.
  - Límites: 3 códigos cada 15 minutos por correo (con respaldo en la base de datos, porque el límite en memoria cuenta por worker) y 10 por red; 10 verificaciones y 10 restablecimientos por minuto por red.
  - Tras validar el código, la sesión del navegador recuerda la verificación; restablecer desde otro navegador o después de pedir otro código no funciona.
  - La nueva contraseña no puede ser la actual ni la temporal (`TEMP_PASSWORD`). Si la cuenta tenía pendiente cambiar su contraseña temporal, queda resuelto.
  - Auditoría: «Código de recuperación solicitado» y «Contraseña restablecida con código por correo».
  - Las tres rutas están exentas de CSRF, como el login (se usan sin sesión y la página de login no tiene token), y permitidas durante el primer inicio de sesión.
- **Envío de correo con la API HTTPS de Brevo** (el plan gratis de Render bloquea SMTP), con la librería estándar: sin dependencias nuevas. Variables `BREVO_API_KEY`, `CORREO_REMITENTE` y opcional `NOMBRE_REMITENTE`. Sin configurar, la recuperación responde que no está disponible. Un envío fallido queda en el log con el motivo, sin el código ni el correo. — `servicios/correo.py`, `render.yaml`
- **Tabla `recuperaciones_password`** (usuario, código cifrado, vencimiento, intentos, usado/anulado, creación). Aplicada en Neon el 2026-11-12 con aprobación; quedan 20 tablas y el diagnóstico sigue sin problemas. — `Models/models.py`, `migrations/2026-11-12_recuperaciones_password.sql`, `migrations/2026-11-12_recuperaciones_password_revertir.sql`
- El diagnóstico cuenta la tabla nueva y revisa su secuencia. — `scripts/diagnostico_neon.py`

#### Documentación
- Cómo configurar Brevo (remitente exclusivo, verificación, clave de la API y variables en Render). — `docs/DESPLIEGUE_RENDER.md`
- El esquema pasa a 20 tablas, con la sección de `recuperaciones_password`. — `docs/ESQUEMA_BD.md`

#### Pruebas
- 36 pruebas nuevas con el envío simulado: flujo completo, código cifrado, misma respuesta para correos inexistentes o desactivados, vencimiento, 5 intentos, código nuevo que anula el anterior, formato, validaciones de la nueva contraseña, límites (incluido el respaldo en la base de datos), uso con una sesión abierta sin token CSRF, la petición a Brevo, el log sin datos sensibles y la ventana del login. — `tests/test_recuperar_password.py`
- El login tiene ahora 3 campos de contraseña con el botón para mostrarla. — `tests/test_seguridad.py`

### Borrada la tabla de ejemplo `playing_with_neon` de Neon (2026-11-12)

#### Eliminado
- **Tabla `public.playing_with_neon`**, la que Neon crea de ejemplo al abrir un proyecto (10 filas de datos aleatorios). SIUT no la usaba: ningún modelo, controlador, llave foránea, vista, trigger ni función la referenciaba (revisado en solo lectura). Su secuencia `playing_with_neon_id_seq` se borró con ella. Aplicado en Neon con aprobación; quedan 19 tablas en `public` y el diagnóstico sigue sin problemas. — `migrations/2026-11-12_borrar_playing_with_neon.sql`
- El script para revertir recrea la tabla con sus 10 filas originales y el valor de la secuencia, copiados en solo lectura antes de borrarla. — `migrations/2026-11-12_borrar_playing_with_neon_revertir.sql`

#### Documentación
- El esquema pasa de 20 a 19 tablas y se quita la sección de la tabla. — `docs/ESQUEMA_BD.md`

### Script de diagnóstico de la base de datos (2026-11-12)

#### Agregado
- **`scripts/diagnostico_neon.py`:** diagnóstico general de Neon en solo lectura (`python scripts/diagnostico_neon.py`). Revisa espacio usado frente al límite del plan gratuito, esquema de Neon frente a los modelos, triggers, restricciones e índices, usuarios y perfiles, vacantes, postulaciones y CV, sugerencias, auditoría y secuencias de ids. Basado en el script usado en el diagnóstico del 2026-11-10, actualizado con:
  - Eventos e inscripciones: conteos, inscripciones repetidas o a eventos/usuarios inexistentes, marcadas OK sin quién o sin fecha, o por alguien que no es Administrador.
  - Seguimiento de postulaciones: estado fuera de la lista, revisión sin quién o sin fecha, revisada por alguien que no es la empresa dueña ni un Administrador, comentario sin fecha, resultado sin haberse marcado como recibida y vacantes dadas de baja con postulaciones sin revisar (aviso).
  - Sin fechas ni referencias a PRs fijas: los inicios de sesión dobles se revisan en los últimos 7 días.
  - La conexión se abre en solo lectura y se verifica antes de consultar; no imprime datos personales. Código de salida 0 sin problemas, 1 con problemas, 2 si no pudo ejecutarse.
  — `scripts/diagnostico_neon.py`, `README.md`
- Primera ejecución contra Neon (2026-11-12): sin problemas; 2 avisos ya conocidos (un alumno con el «semestre» antiguo e inicios de sesión dobles anteriores a la corrección del PR #16).

#### Pruebas
- El script no contiene instrucciones de escritura, abre y verifica la conexión en solo lectura, no consulta columnas con datos personales y sin `DATABASE_URL` se detiene con código 2. — `tests/test_diagnostico.py`

### Ícono del sitio (favicon) (2026-11-12)

#### Agregado
- **Favicon con el escudo de la UTSC** (león blanco sobre escudo naranja, recortado de `img/logo.png` con fondo transparente): `favicon.ico` con 16, 32 y 48 px (el navegador lo pide solo en `/favicon.ico`, que antes respondía 404), `favicon-32.png` para navegadores modernos y `apple-touch-icon.png` de 180 px con fondo blanco para la pantalla de inicio del celular. — `Frontend/favicon.ico`, `Frontend/img/favicon-32.png`, `Frontend/img/apple-touch-icon.png`
- Enlaces `<link rel="icon">` y `<link rel="apple-touch-icon">` en el `<head>` de las 18 páginas. — `Frontend/buzon.html`, `Frontend/cambiar-password.html`, `Frontend/cargar-vacantes.html`, `Frontend/confirmacion.html`, `Frontend/confirmacion_inscripciones.html`, `Frontend/horario.html`, `Frontend/index.html`, `Frontend/inscripcion.html`, `Frontend/inscripciones-eventos.html`, `Frontend/login.html`, `Frontend/maestros.html`, `Frontend/nueva-cuenta.html`, `Frontend/panel-admin.html`, `Frontend/postulaciones-recibidas.html`, `Frontend/soporte.html`, `Frontend/sugerencias.html`, `Frontend/sugerencias-admin.html`, `Frontend/vacantes-publicadas.html`

#### Pruebas
- Íconos servidos sin sesión y durante el primer inicio; las 18 páginas los enlazan. — `tests/test_favicon.py`

### Protección CSRF en todos los formularios (2026-11-12)

#### Seguridad
- **Validación central de CSRF:** toda petición POST, PUT, PATCH o DELETE con sesión debe traer en la cabecera `X-CSRF-Token` el token de su sesión; si falta o no coincide, responde 403 con «La sesión del formulario expiró. Recarga la página e intenta de nuevo.» y lo registra en el log. Cubre las 13 acciones con sesión (cerrar sesión, cambiar contraseña, enviar y responder sugerencias, crear cuentas, postularse, «Recibido» y comentario de postulaciones, publicar, editar y dar de baja vacantes, inscribirse a eventos y marcar inscripciones OK) y cualquier POST que se agregue después. Exentos: `/login` y `/registro`, porque antes de iniciar sesión no hay token. — `app.py`
- **Nuevo `GET /api/csrf-token`:** devuelve el token de la sesión (lo crea si una sesión antigua no lo tiene); sin sesión, 401. Se permite durante el primer inicio de sesión. — `Controllers/authController.py`, `app.py`
- **Nuevo `js/csrf.js`:** agrega la cabecera `X-CSRF-Token` a toda petición POST, PUT, PATCH o DELETE al propio sitio; pide el token una sola vez y respeta el que ya envía una página. Se carga antes que los demás scripts en las 15 páginas con sesión. — `Frontend/js/csrf.js`, `Frontend/index.html`, `Frontend/horario.html`, `Frontend/maestros.html`, `Frontend/buzon.html`, `Frontend/sugerencias.html`, `Frontend/soporte.html`, `Frontend/panel-admin.html`, `Frontend/vacantes-publicadas.html`, `Frontend/cargar-vacantes.html`, `Frontend/postulaciones-recibidas.html`, `Frontend/sugerencias-admin.html`, `Frontend/inscripciones-eventos.html`, `Frontend/nueva-cuenta.html`, `Frontend/inscripcion.html`, `Frontend/cambiar-password.html`

#### Pruebas
- Cada ruta POST con sesión rechaza peticiones sin token, con token vacío, falso o de otra sesión; con token válido funciona; login sin token; sin sesión sigue respondiendo 401; endpoint del token; sesión antigua sin token; primer inicio; `csrf.js` cargado primero en las 15 páginas. — `tests/test_csrf.py`
- El cliente de pruebas envía el token de su sesión automáticamente, como el navegador con `csrf.js`. — `tests/conftest.py`, `tests/test_cuentas_admin.py`

### «Cambiar contraseña» en el menú de perfil (2026-11-12)

#### Agregado
- **Opción «Cambiar contraseña» en el menú de perfil** de las 13 páginas con sesión, con ícono de candado, arriba de «Cerrar sesión» (que sigue en rojo; la nueva opción tiene color neutro). — `Frontend/index.html`, `Frontend/horario.html`, `Frontend/maestros.html`, `Frontend/buzon.html`, `Frontend/sugerencias.html`, `Frontend/soporte.html`, `Frontend/panel-admin.html`, `Frontend/vacantes-publicadas.html`, `Frontend/cargar-vacantes.html`, `Frontend/postulaciones-recibidas.html`, `Frontend/sugerencias-admin.html`, `Frontend/inscripciones-eventos.html`, `Frontend/nueva-cuenta.html`, `Frontend/css/style.css`, `Frontend/img/iconos/candado.svg`
- **Cambio voluntario de contraseña:** si la cuenta ya no está en su primer inicio de sesión, `POST /cambiar-password` exige `password_actual` y responde 400 si falta o no coincide. La nueva debe ser distinta de la actual y tener al menos 8 caracteres. La sesión sigue abierta y se audita como «Cambio de contraseña voluntario». El primer inicio de sesión funciona igual que antes. — `Controllers/authController.py`
- **Página `/cambiar-password` en dos modos:** en el cambio voluntario muestra «Cambiar contraseña», el campo «Contraseña actual» (con el botón para mostrarla) y un enlace «Volver sin cambiar»; al guardar regresa a Inicio. — `Frontend/cambiar-password.html`, `Frontend/js/cambiar-password.js`, `Frontend/css/style.css`

#### Seguridad
- Límite de 5 intentos por minuto por usuario en `POST /cambiar-password`, para que no se pueda adivinar la contraseña actual desde una sesión abierta. — `Controllers/authController.py`
- `/cambiar-password` y `/cambiar-password.html` sin sesión redirigen a `/login`. — `app.py`

#### Pruebas
- Cambio voluntario correcto y auditado; contraseña actual faltante, vacía, no textual o incorrecta; no repetir la actual; primer inicio sin contraseña actual; límite de intentos; redirección sin sesión; opción en el menú de las 13 páginas; ícono. — `tests/test_cambiar_password_perfil.py`, `tests/test_seguridad.py`
- Fuera del alcance: cambiar la contraseña no cierra las sesiones abiertas en otros dispositivos (las sesiones viven en la cookie firmada).

### Rediseño del menú superior para todos los roles (2026-11-12)

#### Cambiado
- **Encabezado nuevo, igual en las 13 páginas con sesión:** fondo blanco con sombra suave que se queda fijo arriba al hacer scroll. Cada opción lleva un ícono y una etiqueta corta («Directorio de Maestros» pasa a «Maestros», «Buscar empleos» a «Empleos», «Buzón de sugerencias» a «Buzón»). La página actual se marca con una píldora verde y una línea naranja, y al pasar el mouse hay una transición. — `Frontend/css/style.css`, `Frontend/index.html`, `Frontend/horario.html`, `Frontend/maestros.html`, `Frontend/buzon.html`, `Frontend/sugerencias.html`, `Frontend/soporte.html`, `Frontend/panel-admin.html`, `Frontend/vacantes-publicadas.html`, `Frontend/cargar-vacantes.html`, `Frontend/postulaciones-recibidas.html`, `Frontend/sugerencias-admin.html`, `Frontend/inscripciones-eventos.html`, `Frontend/nueva-cuenta.html`
- **Menú del administrador agrupado:** de 7 opciones pasa a 4: Panel, «Bolsa de empleo» (submenú con Vacantes publicadas, Cargar vacante y Postulaciones), «Comunidad» (submenú con Sugerencias e Inscripciones a eventos) y Cuentas. Los submenús se abren con el mouse o con un clic, y se cierran con Escape o con un clic fuera. La empresa ve sus 3 opciones directas: Vacantes, Publicar y Postulaciones. Alumno y profesor ven Inicio, Mi horario, Maestros, Empleos, Buzón y Soporte. — mismos archivos, `Frontend/js/nav.js`
- **Menú de perfil:** círculo con las iniciales, el nombre y el rol («Alumno», «Profesor», «Empresa · {empresa}», «Administrador»). Al hacer clic se despliega «Cerrar sesión». **Cerrar sesión ahora existe en todas las páginas;** antes, en las páginas del alumno solo aparecía en Inicio. — `Frontend/js/nav.js`, `app.py`
- **Celular:** el botón ☰ queda en la esquina, se convierte en ✕ y abre un panel lateral con animación y fondo oscurecido. En ese panel, los submenús del administrador se muestran como secciones. En pantallas medianas, las opciones se compactan y el perfil muestra solo las iniciales. — `Frontend/css/style.css`, `Frontend/js/nav.js`
- **El servidor indica el rol en `<body data-rol>`** junto con el nombre, el rol y las iniciales (escapados). Así cada rol ve su menú desde la primera carga, sin parpadeo. Ocultar opciones es solo presentación: los permisos se siguen validando en el servidor. — `app.py`
- Íconos SVG propios; su color lo controla el CSS. — `Frontend/img/iconos/`

#### Eliminado
- `Frontend/js/gestion.js` y `Frontend/js/index.js`: el cierre de sesión y el menú los maneja `Frontend/js/nav.js` en todas las páginas.

#### Pruebas
- Menú y perfil por rol (alumno, profesor, empresa, administrador); una sola opción activa por página; nombre y rol escapados; reglas CSS por rol; íconos disponibles; scripts eliminados. — `tests/test_encabezado.py`, `tests/test_admin.py`
- No se incluyó «Cambiar contraseña» en el menú de perfil: la página actual no pide la contraseña anterior y está pensada solo para el primer inicio de sesión.

### Editar y borrar vacantes, con «Vacante cerrada» para el alumno (2026-11-12)

#### Agregado
- **Botones «Editar» y «Borrar» en «Vacantes publicadas»:** una empresa los ve solo en las vacantes de su empresa; el administrador, en todas. El listado indica con `editable` cuáles puede modificar la sesión y cuántas postulaciones tiene cada una; esos datos no se envían a los alumnos. — `Controllers/vacantesController.py`, `Frontend/vacantes-publicadas.html`, `Frontend/js/vacantes-publicadas.js`, `Frontend/css/style.css`
- **Editar vacante:** usa el mismo formulario de «Cargar vacante» (`cargar-vacantes.html?editar=<id>`) con los datos precargados y las mismas validaciones del alta, compartidas en `_validar_vacante`. Las postulaciones se conservan y la edición se registra en la auditoría («Edición de vacante»). Una empresa no puede cambiar la empresa de la vacante. El administrador sí puede, salvo en las vacantes que publicó una empresa: el trigger `trg_validar_creador_vacante` de Neon lo rechazaría, así que se responde 400 con un mensaje claro. — `Controllers/vacantesController.py` (`GET` y `POST /api/vacantes/<id>`), `Frontend/cargar-vacantes.html`, `Frontend/js/cargar-vacantes.js`
- **Borrar vacante (baja lógica):** pide confirmación e indica cuántas postulaciones tiene. Marca `activo = false`: la vacante deja de mostrarse a los alumnos, pero sus postulaciones y CV se conservan y la empresa los sigue viendo en «Postulaciones recibidas». Se registra en la auditoría («Baja de vacante»). — `Controllers/vacantesController.py` (`POST /api/vacantes/<id>/baja`), `Frontend/js/vacantes-publicadas.js`
- **«Vacante cerrada» para el alumno:** si se borra una vacante a la que se postuló, la sigue viendo en «Mis vacantes postuladas» con la etiqueta «Vacante cerrada», y en el detalle se explica que ya no recibe postulaciones. También conserva el seguimiento y el comentario de la empresa. — `Controllers/postulacionesController.py` (`/api/mis-postulaciones` incluye `vacante_activa` y los datos de la vacante), `Frontend/js/empleos.js`, `Frontend/css/style.css`
- Sin cambios en Neon: la columna `vacantes.activo` ya existía.

#### Pruebas
- Permisos para editar y borrar (empresa dueña, otra empresa, alumno, administrador y sin sesión), validación igual a la del alta, cambio de empresa por el administrador, conservación de postulaciones y CV tras la baja, auditoría, error 500 sin detalle interno y «Vacante cerrada» en «Mis postulaciones». — `tests/test_editar_vacantes.py`

### Seguimiento de postulaciones, notificaciones del buzón e inscripciones a eventos (2026-11-12)

#### Agregado
- **Botón «Recibido» en las postulaciones (empresa y administrador):** aparece junto a «Descargar CV». Al presionarlo, la postulación pasa de «Recibida» a «En revisión», se registra en la auditoría (una sola vez) y se abre el cuadro de comentario. Después el botón cambia a «Comentar» o «Editar comentario». Una empresa solo puede marcar las postulaciones de sus vacantes. — `Controllers/postulacionesController.py` (`POST /api/postulaciones/<id>/recibido`), `Frontend/postulaciones-recibidas.html`, `Frontend/js/postulaciones-recibidas.js`
- **Comentario de la empresa para el alumno:** cuadro de texto (máx. 1500 caracteres) con un resultado opcional, «Aceptada» o «Rechazada». Sin resultado, la postulación queda «En revisión». Se registra en la auditoría. — `Controllers/postulacionesController.py` (`POST /api/postulaciones/<id>/comentario`), `Frontend/postulaciones-recibidas.html`, `Frontend/js/postulaciones-recibidas.js`
- **Seguimiento en «Buscar empleo» (alumno):** el detalle de cada vacante a la que se postuló muestra «La empresa *{nombre}* ha recibido tu información y la está revisando, en breve nos comunicaremos contigo», el resultado (si lo hay) y el comentario de la empresa. Para esas vacantes se oculta «Continuar con mi postulación». — `Controllers/postulacionesController.py` (`GET /api/mis-postulaciones`), `Frontend/buzon.html`, `Frontend/js/empleos.js`
- **Vacantes postuladas marcadas y botón «Mis vacantes postuladas»:** las tarjetas llevan la etiqueta «✓ Postulado», que se guarda en la base y se conserva entre sesiones. El nuevo botón, junto a «Mis favoritos», filtra solo esas vacantes; ambos botones son excluyentes. Al enviar una postulación, la tarjeta se marca sin recargar la página. — `Frontend/buzon.html`, `Frontend/js/empleos.js`
- **«Mis notificaciones» en el buzón de sugerencias:** cada usuario ve sus sugerencias con el estado (Recibida, En revisión, Atendida o Rechazada) y la respuesta del administrador. No se muestra qué administrador la atendió. — `Controllers/buzonController.py` (`GET /api/mis-sugerencias`), `Frontend/sugerencias.html`, `Frontend/js/mis-sugerencias.js`
- **Inscripciones a eventos guardadas en SIUT:** antes, el formulario «Inscríbete aquí» no guardaba nada. Ahora guarda el evento, el nombre y el correo (precargados con los datos de la cuenta y editables) mediante POST JSON, así que nada viaja en la URL. Solo se permite una inscripción por persona en cada evento. Cada tarjeta del inicio abre el formulario con su evento ya elegido. — `Controllers/eventosController.py` (nuevo: `GET /api/eventos`, `POST /api/eventos/<id>/inscripcion`), `Frontend/inscripcion.html`, `Frontend/js/inscripcion.js`, `Frontend/index.html`, `app.py`
- **Página «Inscripciones a eventos» (solo administrador):** muestra el evento, el nombre, el correo y la fecha de cada inscripción, con filtros por evento y por estado. El botón «Marcar OK» se puede deshacer y queda registrado en la auditoría. — `Controllers/eventosController.py` (`GET /api/inscripciones-eventos`, `POST /api/inscripciones-eventos/<id>/ok`), `Frontend/inscripciones-eventos.html`, `Frontend/js/inscripciones-eventos.js`, `app.py`
- **Atajo «EVENTOS» en el panel de administración** con el número de inscripciones por revisar, y el enlace «Inscripciones a eventos» en el menú de todas las páginas de gestión (visible solo para el administrador). — `Frontend/panel-admin.html`, `Frontend/js/panel-admin.js`, `Frontend/cargar-vacantes.html`, `Frontend/nueva-cuenta.html`, `Frontend/postulaciones-recibidas.html`, `Frontend/sugerencias-admin.html`, `Frontend/vacantes-publicadas.html`
- Estilos de las secciones nuevas. — `Frontend/css/style.css`

#### Base de datos (Neon)
- **Migración solo aditiva** `migrations/2026-11-12_seguimiento_postulaciones_eventos.sql` (se revierte con `…_revertir.sql`):
  - `postulaciones`: `revisada_en`, `revisada_por`, `comentario_empresa` varchar(1500) y `comentario_en`.
  - `usuario_evento`: `nombre`, `correo`, `confirmada` (por defecto `false`), `confirmada_por` y `confirmada_en`.
  - `eventos`: se insertan Hackathon, UT Canta 2026 y Club Música, publicados, con fecha provisional del 1 de diciembre de 2026.
- Modelos y documentación del esquema actualizados. — `Models/models.py`, `docs/ESQUEMA_BD.md`

#### Pruebas
- Recibido y comentario: permisos por empresa, alumno y anónimo; validación; auditoría sin duplicados; error 500 sin detalle interno. También «Mis postulaciones» (solo las propias), «Mis notificaciones» del buzón, inscripción a eventos (validación, duplicados, eventos no publicados), la página de administrador y el atajo del panel. — `tests/test_seguimiento.py`, `tests/test_eventos.py`
- Se actualizaron 2 pruebas de la inscripción a eventos, que comprobaban que el formulario era estático; ahora comprueban que no usa `action` ni `name` y que carga `js/inscripcion.js`. — `tests/test_seguridad.py`

### Cuatrimestres en lugar de semestres y botón para mostrar la contraseña (2026-11-10)

#### Cambiado
- **De «Semestre» a «Cuatrimestre»:** las opciones válidas pasan a «1° cuatrimestre» … «11° cuatrimestre» y «Egresado(a)», en ese orden. Antes eran 1° a 6° semestre, ordenadas alfabéticamente: con 11 opciones habría quedado «10°, 11°, 1°…». Los mensajes de error dicen «Cuatrimestre no válido». — `Controllers/postulacionesController.py`, `servicios/cuentas.py`, `Controllers/cuentasController.py`
  - En el formulario «Nueva cuenta» del administrador y en el formulario de postulación del alumno cambian la etiqueta y las opciones; en el detalle de las postulaciones recibidas, la etiqueta. — `Frontend/nueva-cuenta.html`, `Frontend/js/nueva-cuenta.js`, `Frontend/buzon.html`, `Frontend/js/postulaciones-recibidas.js`
  - El comando `flask crear-usuario` acepta `--cuatrimestre` y conserva `--semestre` por compatibilidad. — `comandos.py`, `docs/DESPLIEGUE_RENDER.md`
  - Por dentro, la columna sigue siendo `alumnos.semestre`; **no hay cambios en Neon**. Los alumnos ya guardados con un semestre (en Neon, uno con «1° semestre» y otro con «6° semestre») conservan ese valor hasta su próxima postulación, en la que deben elegir su cuatrimestre.

#### Agregado
- **Botón para mostrar u ocultar la contraseña («ojito»)** en todos los campos de contraseña: inicio de sesión, cambio de contraseña obligatorio y contraseña temporal de «Nueva cuenta». El botón indica a los lectores de pantalla si la contraseña está visible («Mostrar / Ocultar contraseña»). Al enviar o limpiar el formulario, la contraseña vuelve a ocultarse. Es un archivo propio, sin JavaScript dentro del HTML, así que cumple la CSP. — `Frontend/js/mostrar-password.js`, `Frontend/css/style.css`, `Frontend/login.html`, `Frontend/cambiar-password.html`, `Frontend/nueva-cuenta.html`

#### Pruebas
- Cuatrimestres en orden en ambos formularios; postulación con 1°, 11° y Egresado(a); rechazo de valores anteriores («1° semestre») y de «12° cuatrimestre»; opción `--semestre` del comando por compatibilidad; las tres páginas con contraseña cargan el ojito. — `tests/conftest.py`, `tests/test_cuentas_admin.py`, `tests/test_postulaciones.py`, `tests/test_comandos.py`, `tests/test_seguridad.py`

### JS y CSS nuevos sin esperar 1 hora tras un despliegue (2026-11-09)

#### Corregido
- **JS y CSS se revalidan en cada carga:** pasan de `Cache-Control: public, max-age=3600` a `no-cache`. Con la caché de 1 hora, un despliegue podía tardar hasta 1 hora en llegar al navegador de quien ya había entrado. Pasó con la corrección del doble inicio de sesión: después de desplegarla, un doble clic todavía registró 6 inicios de sesión porque el navegador siguió usando el `login.js` anterior. También podía mezclarse un HTML nuevo con un JS viejo. Ahora el navegador conserva los archivos, pero pregunta en cada carga si cambiaron; si no cambiaron, el servidor responde 304 sin reenviarlos. Las imágenes siguen guardándose 1 hora. — `app.py`
- **Respuestas 304 de archivos estáticos:** solo las respuestas 200 recibían la política de caché del recurso. Las 304 caían en la rama del HTML y recibían `no-store` y `Pragma: no-cache`, lo que podía hacer que el navegador descartara la copia que acababa de revalidar. Ahora las 304 llevan la misma política que las 200. — `app.py`
- Documentación de la caché actualizada. — `docs/DESPLIEGUE_RENDER.md`

#### Pruebas
- Cabeceras de caché de imágenes, JS y CSS, y de las respuestas 304. Las pruebas de JS, CSS y 304 fallan sin la corrección. — `tests/test_seguridad.py`

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
