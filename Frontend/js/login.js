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
            body: JSON.stringify({ email: email, password: password })
        })
        .then(response => response.json())
        .then(data => {
            if (data.mensaje === 'Login exitoso') {
                // Si es primer login lo mandamos FORZADO a cambiar contraseña
                if (data.forzar_cambio) {
                    window.location.href = '/cambiar-password';
                    return;
                }
                // Redirección normal por rol
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
