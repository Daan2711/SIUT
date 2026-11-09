# PR #14 — Auditoría: correcciones de seguridad, vacantes y postulaciones

Rama `fix/auditoria-seguridad` → `main` · https://github.com/Daan2711/SIUT/pull/14

## Resumen

Correcciones derivadas de la auditoría de SIUT, pruebas automatizadas, alineación del código con el esquema real de Neon y preparación completa para desplegar en **Render (plan gratis)**. El detalle de cada cambio está en `CHANGELOG.md`.

### Fase 1 — Correcciones críticas
- Alta de vacantes fallaba siempre (500): ahora asigna correctamente `empresa_id`.
- `OPTIONS` devolvía 500; cabeceras de seguridad unificadas; HSTS solo en HTTPS.
- Cambio de contraseña obligatorio validado en el servidor; contraseña temporal fuera del código.
- Límite de 5 intentos/minuto en `/login` (Flask-Limiter).

### Fase 2 — Seguridad y consistencia
- Páginas `.html` exigen sesión; las de vacantes y postulaciones, además, permiso.
- Permisos leídos de la base de datos; nombre escapado (XSS); SRI en scripts de cdnjs.
- Buzón: sin fuga de errores internos, límites de longitud y categorías controladas.
- La sesión expira a los 30 minutos.

### Fase 3 — Funcionalidades
- Postulación con CV (PDF ≤ 5 MB, contenido validado).
- Página de postulaciones recibidas con descarga de CV.
- Buzón de sugerencias en página propia (`sugerencias.html`).
- La bolsa de empleo carga las vacantes desde la API.

### Fase 4 — Limpieza
- Archivos sin uso eliminados, `.gitignore` de Python, dependencias con versión fijada, Docker sin root y un solo `security.txt`.

### Alineación con el esquema de Neon
Un diagnóstico de **solo lectura** en Neon mostró restricciones y triggers que el código desconocía. Se ajustó el código:
- **Roles:** Neon solo admite `Alumno`, `Profesor`, `Empresa` y `Administrador`. El rol `Reclutador` que usaba el código no podía existir, así que nadie podía publicar vacantes por rol. Ahora:
  - `Empresa` publica a nombre de su propia empresa y ve las postulaciones de las vacantes de su empresa.
  - `Administrador` publica para cualquier empresa y ve todas las postulaciones.
- **`VACANTES_EMAILS` se eliminó:** el trigger `trg_validar_creador_vacante` de Neon solo acepta a `Empresa` o `Administrador` como creadores de vacantes, así que publicar por correo terminaba en 500.
- **Auditoría:** `auditoria.accion` es `varchar(100)` en Neon y ya no recibe el título de la vacante; los títulos de unos 78 caracteres o más rompían el alta. El detalle va ahora en `descripcion`.
- **Restricciones** declaradas en los modelos con los mismos nombres que en Neon: correo único sin distinguir mayúsculas, un alumno por usuario, matrícula única, una postulación por alumno y vacante, roles válidos, un usuario `Empresa` por empresa y estados de sugerencia.
- Dos envíos simultáneos de la misma postulación ahora responden 409 (antes 500).

### Preparación para Render — Fase A: bloqueantes
- **CV en Neon:** el plan gratis de Render no tiene disco persistente. El PDF se guarda en la tabla nueva `postulacion_cv`, en la misma transacción que la postulación; se eliminó la escritura en disco y `UPLOAD_DIR`.
  - Migración versionada e idempotente con su script para revertir (`migrations/2026-11-08_postulacion_cv*.sql`). **Ya aplicada en Neon** (ensayo con rollback, aplicación y verificación en solo lectura); solo crea una tabla.
- **Alta de cuentas:** comando `flask crear-usuario` (no había forma de crearlas: registro deshabilitado y 0 usuarios en Neon). Crea la cuenta y el perfil que exige su rol en una sola transacción, valida duplicados, pide la contraseña oculta y confirma la base de datos destino.
- **Conexión estable con Neon:** `pool_pre_ping` y `pool_recycle`, para que las conexiones que Neon cierra al suspenderse no provoquen errores 500.

### Preparación para Render — Fase B: importantes
- **Navegación por rol:** tras el login, `Alumno` → inicio, `Empresa` → sus vacantes, `Administrador` → panel nuevo. Las páginas de gestión tienen menú y cierre de sesión.
- **Panel de administración** y **bandeja de sugerencias** (filtrar por estado, cambiarlo y responder; queda registrado quién y cuándo).
- **Logs:** los errores 500 se registran con su traza completa (`logger.exception`) sin mostrar detalles al cliente.
- **`db.create_all()` solo bajo demanda** (`AUTO_CREATE_TABLES=true`): la app ya no crea tablas en Neon al arrancar.
- **Despliegue:** `/healthz` (comprueba la base de datos), `render.yaml` (Docker, plan gratis, región Ohio como Neon), gunicorn con 2 workers y logs a la consola, y guía `docs/DESPLIEGUE_RENDER.md`.

### Preparación para Render — Fase C: detalles técnicos
- **Menú en celulares** (botón ☰) en las 11 páginas con menú.
- **Caché de 1 hora** para CSS, JS e imágenes; HTML y API sin caché.
- **Limpieza:** páginas huérfanas, `usuario.js` y el carrusel en páginas sin él; `index.html` sin `</body>`.
- SQLite local funciona sin ajustes; **README** reescrito con la arquitectura real.

### Otros
- Login: mensajes correctos según el código HTTP, incluso si el servidor no responde JSON.
- `CLAUDE.md` con las reglas del proyecto para Claude Code.
- Docker: el usuario de la app no puede modificar el código y la app no escribe en disco.
- `docs/ESQUEMA_BD.md`: esquema real de Neon (20 tablas) con diagrama entidad-relación y reglas de negocio de la base.

## Pruebas
- **165 pruebas con pytest** (`python -m pytest`) contra SQLite temporal: todas pasan. Las restricciones de Neon están declaradas en los modelos, y las pruebas replican en SQLite el trigger de vacantes y el límite de 100 caracteres de la auditoría.
- **Docker:** la imagen se construye y corre como usuario sin privilegios; las 165 pruebas pasan dentro del contenedor, y gunicorn (2 workers, puerto de Render) responde en `/healthz`.
- **Servidor local:** flujo completo probado (login por rol, postulación con PDF guardado en la base, descarga idéntica, bandeja de sugerencias).
- **No probado:** contra Neon con datos reales (la app) ni en un navegador real (menú en celular, páginas nuevas y PDF del horario).

## Antes de desplegar
- [ ] Fusionar este PR en `main` (Render despliega desde `main`).
- [ ] Render → **New → Blueprint** con este repositorio y capturar `DATABASE_URL` (Neon). `SECRET_KEY` la genera Render; confirmar que no es la del historial de git.
- [ ] Verificar `https://<servicio>.onrender.com/healthz` → `{"ok": true}`.
- [ ] Crear el primer administrador desde un equipo local: `flask --app app crear-usuario --rol Administrador ...` (Neon admite como máximo 4).
- [ ] Actualizar `Canonical` en `Frontend/.well-known/security.txt` con la URL real del servicio.
- [ ] Prueba manual: login → cambio de contraseña → publicar vacante como Empresa → postularse con PDF → descargar CV → atender una sugerencia como Administrador; menú en celular y PDF del horario.

Guía completa: `docs/DESPLIEGUE_RENDER.md`.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
