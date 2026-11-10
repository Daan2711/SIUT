// Lee la respuesta como JSON sin fallar si el servidor devuelve otra cosa
// (por ejemplo, una página de error HTML del proxy durante un despliegue).
async function leerJson(response) {
    try {
        return await response.json();
    } catch {
        return {};
    }
}

// Mensaje por código HTTP cuando la respuesta no trae un 'error' propio
function mensajePorEstado(status) {
    if (status === 401) return 'Usuario o contraseña incorrectos';
    if (status === 429) return 'Demasiados intentos. Espera un minuto e intenta de nuevo.';
    if (status >= 500) return 'El servidor no está disponible en este momento. Intenta en unos minutos.';
    return 'No fue posible iniciar sesión';
}

document.addEventListener('DOMContentLoaded', function () {
    const loginForm = document.getElementById('loginForm');
    const boton = loginForm.querySelector('button[type="submit"]');
    const textoBoton = boton.textContent;
    // En Render verificar la contraseña tarda unos segundos; sin este candado
    // un segundo clic (o Enter) mandaba otro inicio de sesión: dos registros en
    // la auditoría y una sesión nueva que reemplazaba a la primera.
    let enviando = false;

    function liberar() {
        enviando = false;
        boton.disabled = false;
        boton.textContent = textoBoton;
    }

    // Al volver con «Atrás» el navegador puede restaurar la página con el
    // botón aún bloqueado.
    window.addEventListener('pageshow', function (event) {
        if (event.persisted) liberar();
    });

    loginForm.addEventListener('submit', async function (event) {
        event.preventDefault();
        if (enviando) return;
        enviando = true;
        boton.disabled = true;
        boton.textContent = 'Entrando…';

        const email = document.getElementById('email').value.trim();
        const password = document.getElementById('password').value;

        try {
            const response = await fetch('/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    email: email,
                    password: password
                })
            });

            const data = await leerJson(response);

            if (!response.ok) {
                liberar();
                alert(data.error || mensajePorEstado(response.status));
                return;
            }

            if (data.mensaje === 'Login exitoso') {
                if (data.forzar_cambio) {
                    window.location.href = '/cambiar-password';
                } else {
                    // El servidor indica la página de inicio según el rol
                    // (alumno: index; empresa: sus vacantes; administrador: panel)
                    window.location.href = data.destino || '/index.html';
                }
                // El botón sigue bloqueado mientras el navegador cambia de página
            } else {
                liberar();
                alert('No fue posible iniciar sesión');
            }

        } catch (error) {
            // Solo llega aquí si no hubo respuesta (sin red, servidor caído, etc.)
            console.error('Error:', error);
            liberar();
            alert('Error de conexión con el servidor');
        }
    });
});
