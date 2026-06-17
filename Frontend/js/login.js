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

                if (data.sugerir_cambio) {
                    alert('Por seguridad, te sugerimos cambiar tu contraseña temporal lo antes posible. 🔒');
                }

                // Redirección directa al index
                window.location.href = '/index.html';

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