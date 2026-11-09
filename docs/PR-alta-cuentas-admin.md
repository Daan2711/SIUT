# PR — Alta de cuentas desde el panel de administrador («Nueva cuenta»)

Rama `feat/alta-cuentas-admin` → `main`.

## Resumen
Los administradores pueden crear cuentas de **Alumno, Profesor y Empresa** desde la web, sin usar `flask crear-usuario`. Las cuentas de **Administrador** se siguen creando solo con el comando.

## Cambios
- **Página `nueva-cuenta.html`** (solo Administrador):
  - Selector de rol con Alumno, Profesor y Empresa; muestra solo los campos de cada rol, igual que las opciones del comando.
  - La contraseña temporal se escribe dos veces y la cuenta queda con cambio obligatorio en el primer inicio de sesión.
  - Enlace en el menú de gestión y tarjeta en el panel.
- **API:**
  - `GET /api/admin/cuentas/formulario` devuelve el token CSRF, los roles y los semestres.
  - `POST /api/admin/cuentas` crea la cuenta. Responde 401 sin sesión, 403 si no es administrador o falta el CSRF, 400 en validaciones o roles no permitidos, y 409 en duplicados. Límite de 20 por minuto.
- **CSRF** (`csrf.py`): un token por sesión en la cabecera `X-CSRF-Token`, comparado con `hmac.compare_digest`. No agrega dependencias. Por ahora solo lo usa este formulario.
  - El token se crea **al iniciar sesión** (`authController.py`), no al abrir el formulario. En la prueba manual, el primer envío a veces daba 403: la página pide a la vez el token y `/usuario-actual`, y si `/usuario-actual` respondía al final reescribía la cookie de sesión sin el token. Si a una sesión antigua le falta el token, se crea al pedirlo.
- **Lógica compartida** (`servicios/cuentas.py`): `preparar_cuenta()` valida y revisa duplicados, y `guardar_cuenta()` hace el alta en una sola transacción, como exige Neon. `comandos.py` queda como una capa delgada encima y conserva su comportamiento.
- **Duplicados:** mensajes amigables para correo, matrícula, número de empleado y empresa. Funcionan también cuando el duplicado llega a la restricción UNIQUE de la base (envíos simultáneos). El texto de PostgreSQL solo se escribe en el log.
- **Registro:** el log de la app indica qué administrador creó qué cuenta, sin la contraseña. La auditoría guarda `Alta de usuario (web)` con el id del administrador y `usuarios.creado_por` también lo registra.
- **Modelo `Profesor`:** `usuario_id` y `num_empleado` se declaran únicos, como ya lo están en Neon. **No hay cambios en Neon.**

## Pruebas
`tests/test_cuentas_admin.py` agrega 46 casos:
- alta por rol;
- duplicados, incluidos los que llegan a la base;
- validaciones;
- acceso sin sesión, de Alumno, de Empresa y de un administrador desactivado;
- intento de crear un Administrador por la web;
- CSRF ausente, falso o de otra sesión;
- log sin la contraseña;
- regresión del 403 en el primer envío (falla sin la corrección) y token nuevo en cada inicio de sesión.

**214 pruebas, todas pasan.**

## Prueba manual (servidor local con SQLite)
Ya probado en el navegador:
- **Formulario:** campos por rol; el rol Administrador no aparece.
- **Altas:** Alumno, Profesor y Empresa, con su perfil y su auditoría.
- **Rechazos:**
  - 4 duplicados (correo, matrícula, número de empleado y empresa), con mensaje amigable;
  - contraseñas que no coinciden;
  - `rol=Administrador` por consola (400);
  - envío sin CSRF (403).
- **Log:** indica qué administrador creó cada cuenta y no contiene contraseñas.
- **Cuenta nueva:** se le exige cambiar la contraseña al entrar.
- **Fallo encontrado:** el 403 intermitente en el primer envío, ya corregido en este PR.

## Pendiente (hacer en Render tras el despliegue)
- Crear una cuenta al primer intento con la corrección del token. Ya verificado con un script; falta probarlo en el navegador.
- Como Empresa o Alumno, abrir `/nueva-cuenta.html` y comprobar que redirige al inicio. Está cubierto por pruebas automáticas.
- Primera alta real de Alumno y Profesor en Neon. Funcionó en un PostgreSQL local con las mismas reglas de Neon. **Las cuentas en Neon no se pueden borrar, solo desactivar.**

🤖 Generated with [Claude Code](https://claude.com/claude-code)
