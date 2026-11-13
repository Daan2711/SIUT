# Despliegue de SIUT en Render (plan gratis)

Guía para publicar SIUT en Render usando la base de datos de Neon.

| Pieza | Dónde |
|---|---|
| Aplicación (Flask + gunicorn en Docker) | Render, plan gratis, región Ohio |
| Base de datos (PostgreSQL) y CV en PDF | Neon, región AWS us-east-2 (Ohio) |
| Configuración del servicio | `render.yaml` (Blueprint) |

## Antes de empezar

1. **Fusionar el PR en `main`.** Render despliega desde la rama `main` (`render.yaml` → `branch: main`).
2. **Migraciones aplicadas en Neon.** Las tablas de Neon las controlan los scripts de `migrations/`, no la app.
   - `2026-11-08_postulacion_cv.sql` — **ya aplicada** el 2026-11-08 (tabla de CV).
   - `2026-11-09_corregir_validar_perfiles_usuario.sql` — **ya aplicada** el 2026-11-09 (sin ella no se pueden crear cuentas ni cambiar contraseñas).
   - `2026-11-12_recuperaciones_password.sql` — **ya aplicada** el 2026-11-12 (tabla de códigos para «¿Olvidaste tu contraseña?»).
3. **Cadena de conexión de Neon** a la mano (Neon → *Connection Details*). Usa la del endpoint con *pooler* (el host contiene `-pooler`) y con `sslmode=require`.

## 1. Crear el servicio

1. En Render: **New → Blueprint** y elige el repositorio `Daan2711/SIUT`.
2. Render lee `render.yaml` y propone el servicio `siut` (Docker, plan gratis, Ohio).
3. Te pedirá los valores marcados como secretos:
   - `DATABASE_URL`: la cadena de conexión de Neon.
   - `TEMP_PASSWORD`: opcional; contraseña temporal institucional que no se podrá elegir como nueva. Puede quedar vacía.
   - `BREVO_API_KEY` y `CORREO_REMITENTE`: para «¿Olvidaste tu contraseña?» (ver [Correo para recuperar la contraseña](#correo-para-recuperar-la-contraseña-brevo)). Si quedan vacías, la app funciona igual pero la recuperación responde que no está disponible.
4. Crea el servicio. El primer despliegue construye la imagen Docker (unos minutos).

### Variables de entorno

| Variable | Valor | Para qué |
|---|---|---|
| `DATABASE_URL` | cadena de Neon (secreto) | Conexión a la base de datos |
| `SECRET_KEY` | la genera Render | Firma de las sesiones. **No** debe ser la que aparece en el historial de git |
| `COOKIE_SECURE` | `true` | Cookie de sesión solo por HTTPS y cabecera HSTS |
| `PROXY_HOPS` | `1` | IP real del cliente detrás del proxy de Render (límite de intentos de login) |
| `LOG_LEVEL` | `INFO` | Nivel de los logs |
| `TEMP_PASSWORD` | opcional (secreto) | Contraseña temporal que no puede reutilizarse |
| `BREVO_API_KEY` | secreto | Clave de la API de Brevo para enviar el código de recuperación |
| `CORREO_REMITENTE` | correo verificado en Brevo | Remitente del correo de recuperación |
| `NOMBRE_REMITENTE` | opcional (por defecto `SIUT`) | Nombre que ve quien recibe el correo |

### Correo para recuperar la contraseña (Brevo)

«¿Olvidaste tu contraseña?» envía un código de 4 dígitos al correo del usuario. El plan gratis de Render bloquea el SMTP saliente, así que SIUT envía por la **API HTTPS de Brevo** (gratis, 300 correos al día).

1. **Remitente exclusivo:** crea un correo solo para SIUT (por ejemplo, un Gmail nuevo). No uses un correo personal.
2. **Cuenta de Brevo:** regístrate en [brevo.com](https://www.brevo.com) con ese correo.
3. **Verificar el remitente:** Brevo → *Senders, Domains & Dedicated IPs* → *Senders* → *Add a sender*. Escribe el correo y abre el enlace que Brevo le envía.
4. **Clave de la API:** Brevo → *SMTP & API* → *API Keys* → *Generate a new API key*. Cópiala: Brevo la muestra una sola vez.
5. **Render:** en el servicio → *Environment*, agrega `BREVO_API_KEY` (la clave) y `CORREO_REMITENTE` (el correo verificado) y guarda. Render vuelve a desplegar solo.
6. **Probar:** en `/login` → «¿Olvidaste tu contraseña?» con una cuenta cuyo correo sea real. Si no llega, revisa spam y los *Logs* de Render: un envío fallido aparece como `No se pudo enviar el código de recuperación (usuario N): Brevo respondió …` con el motivo.

- La clave es un secreto: no la subas al repositorio ni la compartas por chat. Para probar en local, ponla en `.env` (que no se sube).
- Algunas cuentas nuevas de Brevo quedan en revisión unas horas antes de poder enviar.
- Los correos desde un Gmail enviados por Brevo pueden llegar a spam; con un dominio propio verificado en Brevo llegan mejor.
- Requiere la migración `migrations/2026-11-12_recuperaciones_password.sql` en Neon.

No definas `AUTO_CREATE_TABLES` en Render: la app no debe crear tablas en Neon.

## 2. Verificar el despliegue

- **Health check:** `https://<tu-servicio>.onrender.com/healthz` debe responder `{"ok": true}`. Comprueba la app y la conexión con Neon; Render lo usa para decidir si el servicio está sano.
- **Login:** `https://<tu-servicio>.onrender.com/login` debe mostrar la pantalla de inicio de sesión.
- **Logs:** en Render → *Logs* aparecen los accesos y, si algo falla, el error completo con su traza.

## 3. Crear las cuentas

No hay registro público. Hay dos caminos, que usan la misma lógica (`servicios/cuentas.py`):

- **Administradores:** solo con el comando `flask crear-usuario`, **desde tu equipo**, porque el plan gratis de Render no tiene consola. El comando usa el `DATABASE_URL` del `.env` local, que debe apuntar a Neon.
- **Alumnos, profesores y empresas:** un administrador los crea desde la web, en **Panel → Nueva cuenta** (`/nueva-cuenta.html`). El formulario no ofrece el rol Administrador y el servidor lo rechaza aunque llegue en la petición. El comando también puede crearlos.

```bash
# Desde la raíz del proyecto (con las dependencias instaladas).
# Se usa "python -m flask" porque en Windows "flask" suele no estar en el PATH.
python -m flask --app app crear-usuario --rol Administrador --email admin@utsc.edu.mx --nombre "Nombre" --apellido "Apellido"
```

Antes de escribir, el comando muestra la base de datos destino (debe decir `neondb`) y pide confirmación. La contraseña se pide oculta y la cuenta queda con **cambio obligatorio** en el primer inicio de sesión.

| Rol | Opciones obligatorias | Ejemplo |
|---|---|---|
| `Administrador` | — | `--rol Administrador --email admin@utsc.edu.mx --nombre Ana` |
| `Empresa` | `--empresa` | `--rol Empresa --email rh@tecnonova.mx --nombre Carla --empresa TecnoNova` |
| `Alumno` | `--matricula` | `--rol Alumno --email luis@utsc.edu.mx --nombre Luis --matricula UTSC-001 --carrera "Desarrollo de Software" --cuatrimestre "3° cuatrimestre"` |
| `Profesor` | `--num-empleado` | `--rol Profesor --email eva@utsc.edu.mx --nombre Eva --num-empleado E-01` |

Reglas que impone Neon (el comando las valida antes):

- Máximo **4** cuentas `Administrador`.
- Una sola cuenta `Empresa` por empresa.
- Correo único (sin distinguir mayúsculas) y matrícula / número de empleado únicos.
- Las cuentas no se borran: se desactivan (`activo = false`).

`python -m flask --app app crear-usuario --help` muestra todas las opciones.

En Windows la contraseña se escribe de forma oculta: ejecuta el comando en una terminal (PowerShell o CMD), no desde un script ni una tubería.

## 4. Después del primer despliegue

- [x] Actualizar `Canonical` en `Frontend/.well-known/security.txt` con la URL real del servicio: `https://siut-shap.onrender.com` (hecho el 2026-11-09).
- [ ] Prueba manual completa: login → cambio de contraseña → (Empresa) publicar vacante → (Alumno) postularse con PDF → (Empresa) descargar CV → (Administrador) atender una sugerencia.
- [ ] Probar la descarga del horario en PDF en el navegador (usa html2pdf desde cdnjs con la CSP actual).

## Limitaciones del plan gratis (a tener en cuenta)

- **El servicio se duerme** tras 15 minutos sin visitas; la siguiente visita tarda unos 30–60 s en responder mientras arranca (estimación según la documentación de Render).
- **Neon también se suspende** tras unos minutos sin uso; la app reconecta sola (`pool_pre_ping`), pero la primera consulta tarda un poco más.
- **Sin disco persistente**: por eso los CV se guardan en Neon (tabla `postulacion_cv`). El plan gratis de Neon tiene 0.5 GB en total.
- **Caché de archivos estáticos**: las imágenes se guardan 1 hora en el navegador; tras un despliegue, una imagen cambiada puede tardar hasta 1 hora en verse (o hasta recargar con Ctrl+F5). CSS y JS se revalidan en cada carga (`no-cache`): el navegador recibe la versión nueva en cuanto termina el despliegue y, si no cambió, Render responde 304 sin reenviar el archivo. El HTML y la API nunca se guardan en caché.
- **Límite de intentos de login por worker**: con 2 workers de gunicorn cada uno lleva su propio conteo (5 por minuto cada uno). Para un límite global haría falta Redis (`RATELIMIT_STORAGE_URI`).

## Si algo falla

| Síntoma | Revisar |
|---|---|
| `/healthz` responde 503 | `DATABASE_URL` correcta y Neon activo; el error completo está en *Logs* |
| Error al iniciar: `Falta configurar SECRET_KEY` | La variable `SECRET_KEY` no está definida |
| Nadie puede iniciar sesión | Que existan cuentas (`flask crear-usuario`) |
| Una postulación falla con 500 | Que la migración `2026-11-08_postulacion_cv.sql` esté aplicada en Neon |
| La sesión no se mantiene | `COOKIE_SECURE=true` requiere HTTPS (Render lo da por defecto) |
