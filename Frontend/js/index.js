document.getElementById('btnLogout').addEventListener('click', async function () {
    try {
        const response = await fetch('/logout', { method: 'POST', credentials: 'same-origin' });
        // 401 = la sesión ya no existía: se trata como cierre exitoso
        if (!response.ok && response.status !== 401) {
            alert('No fue posible cerrar la sesión. Intenta nuevamente.');
            return;
        }
        localStorage.removeItem('nombreUsuario');
        window.location.href = '/login';
    } catch (error) {
        alert('Error de conexión con el servidor. Tu sesión sigue abierta.');
    }
});
