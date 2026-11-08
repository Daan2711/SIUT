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

    loginForm.addEventListener('submit', async function (event) {
        event.preventDefault();

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
                alert(data.error || mensajePorEstado(response.status));
                return;
            }

            if (data.mensaje === 'Login exitoso') {
                if (data.forzar_cambio) {
                    window.location.href = '/cambiar-password';
                } else {
                    window.location.href = '/index.html';
                }
            } else {
                alert('No fue posible iniciar sesión');
            }

        } catch (error) {
            // Solo llega aquí si no hubo respuesta (sin red, servidor caído, etc.)
            console.error('Error:', error);
            alert('Error de conexión con el servidor');
        }
    });
});
