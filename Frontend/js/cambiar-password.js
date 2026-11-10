document.addEventListener('DOMContentLoaded', function () {
    const cambiarForm = document.getElementById('cambiarForm');
    const boton = cambiarForm.querySelector('button[type="submit"]');
    const textoBoton = boton.textContent;
    // Evita un segundo envío mientras el primero está en curso: el segundo
    // respondería «debe ser distinta a la actual» aunque el cambio ya se guardó.
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

    cambiarForm.addEventListener('submit', function (event) {
        event.preventDefault();
        if (enviando) return;

        const nueva_password = document.getElementById('nueva_password').value;
        const confirmar_password = document.getElementById('confirmar_password').value;

        // Validación en cliente antes de mandar al servidor
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

        fetch('/cambiar-password', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                nueva_password: nueva_password,
                confirmar_password: confirmar_password
            })
        })
        // Tolera respuestas que no son JSON (p. ej. un error HTML del proxy)
        .then(response => response.json().catch(() => ({})))
        .then(data => {
            if (data.mensaje === 'Contraseña actualizada correctamente') {
                alert('Contraseña actualizada. Ahora puedes usar el sistema.');
                window.location.href = '/login';
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
