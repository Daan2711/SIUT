document.addEventListener('DOMContentLoaded', function () {
    const loginForm = document.getElementById('loginForm');

    loginForm.addEventListener('submit', function (event) {
        // Evitamos que la página se recargue al dar clic en el botón
        event.preventDefault();

        // Obtenemos los valores de las cajas de texto
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;

        // Hacemos la petición al servidor de Python a la ruta /login
        fetch('/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ email: email, password: password })
        })
            .then(response => response.json())
            .then(data => {
                if (data.mensaje === 'Login exitoso') {

                    // Si entró con la contraseña temporal, le avisamos con el pop-up
                    if (data.sugerir_cambio) {
                        alert('Por seguridad, te sugerimos cambiar tu contraseña temporal lo antes posible. 🔒');
                    }

                    // Redirección inteligente según el rol que viene desde la base de datos
                    if (data.rol === 'admin') {
                        window.location.href = '/admin-dashboard';
                    } else if (data.rol === 'profesor') {
                        window.location.href = '/profesor-dashboard';
                    } else if (data.rol === 'alumno') {
                        window.location.href = '/alumno-dashboard';
                    } else {
                        window.location.href = '/';
                    }
                } else {
                    alert(data.error || 'Ocurrió un error al iniciar sesión');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error de conexión con el servidor');
            });
    });
});