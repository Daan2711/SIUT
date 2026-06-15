document.addEventListener('DOMContentLoaded', function () {
    const cambiarForm = document.getElementById('cambiarForm');

    cambiarForm.addEventListener('submit', function (event) {
        event.preventDefault();

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

        if (nueva_password === 'UTSC2026') {
            alert('No puedes usar la contraseña temporal como nueva contraseña');
            return;
        }

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
        .then(response => response.json())
        .then(data => {
            if (data.mensaje === 'Contraseña actualizada correctamente') {
                alert('Contraseña actualizada. Ahora puedes usar el sistema.');
                window.location.href = '/login';
            } else {
                alert(data.error || 'Ocurrió un error al cambiar la contraseña');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error de conexión con el servidor');
        });
    });
});
