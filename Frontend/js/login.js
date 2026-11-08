
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

            const data = await response.json();

            if (!response.ok) {
                alert(data.error || 'Usuario o contraseña incorrectos');
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
            console.error('Error:', error);
            alert('Error de conexión con el servidor');
        }
    });
});
