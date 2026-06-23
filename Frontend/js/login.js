document.addEventListener('DOMContentLoaded', function () {
    const loginForm = document.getElementById('loginForm');

    loginForm.addEventListener('submit', function (event) {
        event.preventDefault();

        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;

        fetch('/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                email: email,
                password: password
            })
        })
        .then(response => response.json())
        .then(data => {
            console.log("Respuesta del servidor:", data);

            if (data.mensaje === 'Login exitoso') {

                const nombreCompleto = (data.nombre || '') + ' ' + (data.apellido || '');
                localStorage.setItem('nombreUsuario', nombreCompleto.trim());

                if (data.forzar_cambio) {
                    window.location.href = '/cambiar-password.html';
                } else {
                    window.location.href = '/index.html';
                }

            } else {
                alert(data.error || 'Usuario o contraseña incorrectos');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error de conexión con el servidor');
        });
    });
});