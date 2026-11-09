# PR #14 — Auditoría: correcciones de seguridad, vacantes y postulaciones

Rama `fix/auditoria-seguridad` → `main` · https://github.com/Daan2711/SIUT/pull/14

## Resumen

Correcciones derivadas de la auditoría de SIUT, más pruebas automatizadas y la alineación del código con el esquema real de Neon. El detalle de cada cambio está en `CHANGELOG.md`.

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
- Postulación con CV (PDF ≤ 5 MB, contenido validado, guardado fuera de `Frontend/`).
- Página de postulaciones recibidas con descarga de CV.
- Buzón de sugerencias en página propia (`sugerencias.html`).
- La bolsa de empleo carga las vacantes desde la API.

### Fase 4 — Limpieza
- Archivos sin uso eliminados, `.gitignore` de Python, dependencias con versión fijada, Docker sin root y un solo `security.txt`.

### Alineación con el esquema de Neon
Un diagnóstico de **solo lectura** en Neon mostró restricciones y triggers que el código desconocía. **No se modificó la base de datos**; se ajustó el código:
- **Roles:** Neon solo admite `Alumno`, `Profesor`, `Empresa` y `Administrador`. El rol `Reclutador` que usaba el código no podía existir, así que nadie podía publicar vacantes por rol. Ahora:
  - `Empresa` publica a nombre de su propia empresa y ve las postulaciones de las vacantes de su empresa.
  - `Administrador` publica para cualquier empresa y ve todas las postulaciones.
- **`VACANTES_EMAILS` se eliminó:** el trigger `trg_validar_creador_vacante` de Neon solo acepta a `Empresa` o `Administrador` como creadores de vacantes, así que publicar por correo terminaba en 500.
- **Auditoría:** `auditoria.accion` es `varchar(100)` en Neon y ya no recibe el título de la vacante; los títulos de unos 78 caracteres o más rompían el alta. El detalle va ahora en `descripcion`.
- **Restricciones** declaradas en los modelos con los mismos nombres que en Neon: correo único sin distinguir mayúsculas, un alumno por usuario, matrícula única, una postulación por alumno y vacante, roles válidos y un usuario `Empresa` por empresa.
- Dos envíos simultáneos de la misma postulación ahora responden 409 (antes 500) y no dejan el CV huérfano.

### Otros
- Login: mensajes correctos según el código HTTP, incluso si el servidor no responde JSON.
- `CLAUDE.md` con las reglas del proyecto para Claude Code.
- Docker: el usuario de la app ya no puede modificar el código; solo escribe en `instance/`.
- `docs/ESQUEMA_BD.md`: esquema real de Neon con diagrama entidad-relación y reglas de negocio de la base.

## Pruebas
- **108 pruebas con pytest** (`python -m pytest`) contra SQLite temporal: todas pasan. Las restricciones de Neon están declaradas en los modelos, y las pruebas replican en SQLite el trigger de vacantes y el límite de 100 caracteres de la auditoría.
- **Docker:** la imagen se construye y corre como usuario sin privilegios (el código es de solo lectura para la app); las 108 pruebas pasan dentro del contenedor.
- **No probado:** contra Neon con datos reales ni en el navegador.

## Antes de desplegar
- [ ] Confirmar que la `SECRET_KEY` de Render no es la que aparece en el historial de git.
- [ ] En Render: `PROXY_HOPS=1` y `UPLOAD_DIR` en un Persistent Disk (sin él, los CV se pierden en cada despliegue). Si existe `VACANTES_EMAILS`, puede borrarse: ya no se usa.
- [ ] Crear en Neon las empresas y sus usuarios con `rol = 'Empresa'` y `empresa_id`, y los administradores con `rol = 'Administrador'` (Neon admite como máximo 4).
- [ ] Prueba manual: login → cambio de contraseña → publicar vacante como Empresa → postularse con PDF → descargar CV.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
