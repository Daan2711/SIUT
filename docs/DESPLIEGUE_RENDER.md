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
3. **Cadena de conexión de Neon** a la mano (Neon → *Connection Details*). Usa la del endpoint con *pooler* (el host contiene `-pooler`) y con `sslmode=require`.

## 1. Crear el servicio

1. En Render: **New → Blueprint** y elige el repositorio `Daan2711/SIUT`.
2. Render lee `render.yaml` y propone el servicio `siut` (Docker, plan gratis, Ohio).
3. Te pedirá los valores marcados como secretos:
   - `DATABASE_URL`: la cadena de conexión de Neon.
   - `TEMP_PASSWORD`: opcional; contraseña temporal institucional que no se podrá elegir como nueva. Puede quedar vacía.
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

No definas `AUTO_CREATE_TABLES` en Render: la app no debe crear tablas en Neon.

## 2. Verificar el despliegue

- **Health check:** `https://<tu-servicio>.onrender.com/healthz` debe responder `{"ok": true}`. Comprueba la app y la conexión con Neon; Render lo usa para decidir si el servicio está sano.
- **Login:** `https://<tu-servicio>.onrender.com/login` debe mostrar la pantalla de inicio de sesión.
- **Logs:** en Render → *Logs* aparecen los accesos y, si algo falla, el error completo con su traza.

## 3. Crear las cuentas

No hay registro público. Las cuentas se crean con el comando `flask crear-usuario`, **desde tu equipo**, porque el plan gratis de Render no tiene consola. El comando usa el `DATABASE_URL` del `.env` local, que debe apuntar a Neon.

```bash
# Desde la raíz del proyecto (con las dependencias instaladas)
flask --app app crear-usuario --rol Administrador --email admin@utsc.edu.mx --nombre "Nombre" --apellido "Apellido"
```

Antes de escribir, el comando muestra la base de datos destino (debe decir `neondb`) y pide confirmación. La contraseña se pide oculta y la cuenta queda con **cambio obligatorio** en el primer inicio de sesión.

| Rol | Opciones obligatorias | Ejemplo |
|---|---|---|
| `Administrador` | — | `--rol Administrador --email admin@utsc.edu.mx --nombre Ana` |
| `Empresa` | `--empresa` | `--rol Empresa --email rh@tecnonova.mx --nombre Carla --empresa TecnoNova` |
| `Alumno` | `--matricula` | `--rol Alumno --email luis@utsc.edu.mx --nombre Luis --matricula UTSC-001 --carrera "Desarrollo de Software" --semestre "3° semestre"` |
| `Profesor` | `--num-empleado` | `--rol Profesor --email eva@utsc.edu.mx --nombre Eva --num-empleado E-01` |

Reglas que impone Neon (el comando las valida antes):

- Máximo **4** cuentas `Administrador`.
- Una sola cuenta `Empresa` por empresa.
- Correo único (sin distinguir mayúsculas) y matrícula / número de empleado únicos.
- Las cuentas no se borran: se desactivan (`activo = false`).

`flask crear-usuario --help` muestra todas las opciones.

## 4. Después del primer despliegue

- [ ] Actualizar `Canonical` en `Frontend/.well-known/security.txt` con la URL real del servicio (hoy dice `siut.onrender.com`).
- [ ] Prueba manual completa: login → cambio de contraseña → (Empresa) publicar vacante → (Alumno) postularse con PDF → (Empresa) descargar CV → (Administrador) atender una sugerencia.
- [ ] Probar la descarga del horario en PDF en el navegador (usa html2pdf desde cdnjs con la CSP actual).

## Limitaciones del plan gratis (a tener en cuenta)

- **El servicio se duerme** tras 15 minutos sin visitas; la siguiente visita tarda unos 30–60 s en responder mientras arranca (estimación según la documentación de Render).
- **Neon también se suspende** tras unos minutos sin uso; la app reconecta sola (`pool_pre_ping`), pero la primera consulta tarda un poco más.
- **Sin disco persistente**: por eso los CV se guardan en Neon (tabla `postulacion_cv`). El plan gratis de Neon tiene 0.5 GB en total.
- **Límite de intentos de login por worker**: con 2 workers de gunicorn cada uno lleva su propio conteo (5 por minuto cada uno). Para un límite global haría falta Redis (`RATELIMIT_STORAGE_URI`).

## Si algo falla

| Síntoma | Revisar |
|---|---|
| `/healthz` responde 503 | `DATABASE_URL` correcta y Neon activo; el error completo está en *Logs* |
| Error al iniciar: `Falta configurar SECRET_KEY` | La variable `SECRET_KEY` no está definida |
| Nadie puede iniciar sesión | Que existan cuentas (`flask crear-usuario`) |
| Una postulación falla con 500 | Que la migración `2026-11-08_postulacion_cv.sql` esté aplicada en Neon |
| La sesión no se mantiene | `COOKIE_SECURE=true` requiere HTTPS (Render lo da por defecto) |
