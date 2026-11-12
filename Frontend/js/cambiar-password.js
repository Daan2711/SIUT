// Cambio de contraseña en dos modos (los decide el servidor con primer_login):
// - Primer inicio de sesión: reemplazar la contraseña temporal.
// - Voluntario (menú de perfil): pide además la contraseña actual.
document.addEventListener('DOMContentLoaded', function () {
    const cambiarForm = document.getElementById('cambiarForm');
    const boton = cambiarForm.querySelector('button[type="submit"]');
    const campoActual = document.getElementById('password_actual');
    // Mientras no se sepa el modo, se asume el primer inicio (comportamiento previo)
    let voluntario = false;
    // Evita un segundo envío mientras el primero está en curso: el segundo
    // respondería «debe ser distinta a la actual» aunque el cambio ya se guardó.
    let enviando = false;

    function liberar() {
        enviando = false;
        boton.disabled = false;
        boton.textContent = voluntario ? 'GUARDAR CAMBIOS' : 'GUARDAR CONTRASEÑA';
    }

    function modoVoluntario() {
        voluntario = true;
        document.title = 'MyUTSC - Cambiar contraseña';
        document.getElementById('tituloCambio').textContent = 'Cambiar contraseña';
        document.getElementById('textoCambio').textContent =
            'Escribe tu contraseña actual y elige una nueva de al menos 8 caracteres.';
        document.getElementById('grupoActual').hidden = false;
        document.getElementById('volverCambio').hidden = false;
        campoActual.required = true;
        liberar();
        campoActual.focus();
    }

    fetch('/usuario-actual', { credentials: 'same-origin' })
        .then(response => {
            if (response.status === 401) {
                window.location.href = '/login';
                return null;
            }
            return response.ok ? response.json() : null;
        })
        .then(usuario => {
            if (usuario && usuario.primer_login === false) modoVoluntario();
        })
        .catch(() => { /* sin conexión: se queda en el modo de primer inicio */ });

    // Al volver con «Atrás» el navegador puede restaurar la página con el
    // botón aún bloqueado.
    window.addEventListener('pageshow', function (event) {
        if (event.persisted) liberar();
    });

    cambiarForm.addEventListener('submit', function (event) {
        event.preventDefault();
        if (enviando) return;

        const password_actual = campoActual.value;
        const nueva_password = document.getElementById('nueva_password').value;
        const confirmar_password = document.getElementById('confirmar_password').value;

        // Validación en cliente antes de mandar al servidor
        if (voluntario && !password_actual) {
            alert('Escribe tu contraseña actual');
            return;
        }

        if (nueva_password.length < 8) {
            alert('La contraseña debe tener al menos 8 caracteres');
            return;
        }

        if (nueva_password !== confirmar_password) {
            alert('Las contraseñas no coinciden');
            return;
        }

        enviando = true;
        boton.disabled = true;
        boton.textContent = 'Guardando…';

        const cuerpo = { nueva_password: nueva_password, confirmar_password: confirmar_password };
        if (voluntario) cuerpo.password_actual = password_actual;

        fetch('/cambiar-password', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(cuerpo)
        })
        // Tolera respuestas que no son JSON (p. ej. un error HTML del proxy)
        .then(response => response.json().catch(() => ({})))
        .then(data => {
            if (data.mensaje === 'Contraseña actualizada correctamente') {
                if (voluntario) {
                    // La sesión sigue abierta: se regresa a Inicio
                    alert('Tu contraseña se cambió correctamente.');
                    window.location.href = '/';
                } else {
                    alert('Contraseña actualizada. Ahora puedes usar el sistema.');
                    window.location.href = '/login';
                }
            } else {
                liberar();
                alert(data.error || 'Ocurrió un error al cambiar la contraseña');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            liberar();
            alert('Error de conexión con el servidor');
        });
    });
});
